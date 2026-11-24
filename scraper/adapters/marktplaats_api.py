"""Marktplaats via de officiële API (https://api.marktplaats.nl/docs/v1/).

Werkt alleen met eigen API-sleutels van Marktplaats, als GitHub-secrets:
  MP_CLIENT_ID, MP_CLIENT_SECRET
Zonder sleutels wordt deze bron overgeslagen.

Aanpak:
  1. token via client_credentials (24 uur geldig)
  2. categorieën ophalen, binnen 'Dieren en Toebehoren' de subcategorieën voor
     honden, katten, vogels en overige dieren kiezen (toebehoren/oppas/gezocht overslaan)
  3. per categorie /v1/search (max. 5000 resultaten volgens de API)
  4. optioneel detail per advertentie voor de plaats (MP_MAX_DETAIL)
"""
import os
import re
import time

import requests

from common import UA, kort
from scoring import classificeer_aanbieder

NAAM = "Marktplaats (API)"
API = os.environ.get("MP_API_BASE", "https://api.marktplaats.nl")
TOKEN_URL = os.environ.get("MP_TOKEN_URL", "https://auth.marktplaats.nl/accounts/oauth/token")
MAX_PER_CAT = int(os.environ.get("MP_MAX_PER_CATEGORIE", "600"))
MAX_DETAIL = int(os.environ.get("MP_MAX_DETAIL", "400"))
LIMIT = 100

OVERSLAAN = re.compile(r"toebehoren|benodigdheden|voer|oppas|gezocht|uitlaat|diensten|trim|hokken|kooien|aquari|terrari|ruitersport|stalling|accessoires", re.I)


class MarktplaatsAPI:
    def __init__(self, cid, secret):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept": "application/json"})
        r = self.s.post(TOKEN_URL, data={"grant_type": "client_credentials", "client_id": cid, "client_secret": secret}, timeout=30)
        r.raise_for_status()
        self.s.headers["Authorization"] = "Bearer " + r.json()["access_token"]

    def get(self, pad, **params):
        time.sleep(0.4)
        r = self.s.get(API + pad, params=params, timeout=30)
        if r.status_code == 400:
            return None
        r.raise_for_status()
        return r.json()


def _naam(cat):
    return (cat.get("labels") or {}).get("nl-NL") or cat.get("name") or ""


def _kinderen(data):
    emb = (data or {}).get("_embedded") or {}
    return emb.get("mp:category") or []


def soort_van(naam):
    n = naam.lower()
    if re.search(r"\bhond|pup", n):
        return "hond"
    if re.search(r"\bkat|kitten|poes", n):
        return "kat"
    if re.search(r"vogel|parkiet|papegaai|kip|duif|duiven|pluimvee|kanarie", n):
        return "vogel"
    return "overig"


def categorieen(api):
    """[(categoryId, naam, soort)] binnen Dieren en Toebehoren."""
    top = api.get("/v1/categories")
    dieren = next((c for c in _kinderen(top) if re.search(r"^dieren", _naam(c), re.I)), None)
    if not dieren:
        raise RuntimeError("Categorie 'Dieren en Toebehoren' niet gevonden")
    sub = _kinderen(api.get(f"/v1/categories/{dieren['categoryId']}"))
    uit = []
    for c in sub:
        n = _naam(c)
        if c.get("status", "open") != "open" or OVERSLAAN.search(n):
            continue
        uit.append((c["categoryId"], n, soort_van(n)))
    return uit


def _prijs(pm):
    pm = pm or {}
    t = (pm.get("modelType") or "").lower()
    bedrag = pm.get("askingPrice")
    if t in ("free", "gratis"):
        return 0.0, "Gratis"
    if bedrag:
        euro = bedrag / 100  # API geeft centen
        return euro, f"€ {euro:,.0f}".replace(",", ".") + (" (bieden)" if "bid" in t else "")
    return None, {"bidding": "Bieden", "see_description": "Zie omschrijving", "notk": "N.o.t.k.", "exchange": "Ruilen"}.get(t, t or None)


def _fotos(item):
    uit = []
    for img in ((item.get("_embedded") or {}).get("mp:advertisement-image") or []):
        for k, v in (img.get("_links") or {}).items():
            href = v.get("href") if isinstance(v, dict) else None
            if href and "blob" in k.lower():
                uit.append(href.replace("{size}", "82").replace("{id}", str(img.get("mediaId", ""))) if href.startswith("http") else API + href)
    return uit[:8]


def _web_url(item):
    for k, v in (item.get("_links") or {}).items():
        if isinstance(v, dict) and v.get("href", "").startswith("http") and "marktplaats.nl" in v["href"] and "api." not in v["href"]:
            return v["href"]
    return f"https://www.marktplaats.nl/v/a/{item.get('itemId')}"


def _plaats(api, item_id):
    """Zoekt in de advertentiedetails naar een plaatsnaam/postcode (veldnamen zijn niet gedocumenteerd)."""
    try:
        d = api.get(f"/v1/advertisements/{item_id}")
    except requests.RequestException:
        return None
    gevonden = []

    def zoek(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and re.search(r"city|plaats|town|postcode|postCode|zipCode", k):
                    gevonden.append(v)
                else:
                    zoek(v)
        elif isinstance(o, list):
            for v in o:
                zoek(v)
    zoek(d or {})
    stad = next((g for g in gevonden if not re.match(r"^\d{4}", g)), None)
    return stad or (gevonden[0][:4] if gevonden else None)


def ophalen():
    cid, secret = os.environ.get("MP_CLIENT_ID"), os.environ.get("MP_CLIENT_SECRET")
    if not cid or not secret:
        return None  # geen sleutels: bron overslaan
    api = MarktplaatsAPI(cid, secret)
    dieren, details, gezien = [], 0, set()
    for cat_id, cat_naam, soort in categorieen(api):
        n = 0
        for offset in range(0, min(MAX_PER_CAT, 5000), LIMIT):
            res = api.get("/v1/search", categoryId=cat_id, limit=LIMIT, offset=offset, locale="nl-NL")
            items = ((res or {}).get("_embedded") or {}).get("mp:search-result") or []
            for it in items:
                if it.get("itemId") in gezien:
                    continue
                gezien.add(it.get("itemId"))
                prijs, prijs_tekst = _prijs(it.get("priceModel"))
                seller = it.get("seller") or {}
                titel = it.get("title") or ""
                oms = it.get("description") or ""
                plaats = None
                if details < MAX_DETAIL:
                    plaats = _plaats(api, it.get("itemId"))
                    details += 1
                dieren.append({
                    "id": f"mp-{it.get('itemId')}",
                    "url": _web_url(it),
                    "naam": titel,
                    "soort": soort,
                    "ras": None,
                    "categorie": cat_naam,
                    "plaats": plaats,
                    "prijs": prijs,
                    "prijs_tekst": prijs_tekst,
                    "fotos": _fotos(it),
                    "status": "gereserveerd" if re.search(r"\bgereserveerd\b", titel, re.I) else "beschikbaar",
                    "gegadigden": None,
                    "beschrijving": kort(oms),
                    "_tekst": f"{titel} {oms}",
                    "aanbieder": {"naam": seller.get("sellerName") or "Onbekend",
                                  "id": seller.get("sellerId"),
                                  "type": classificeer_aanbieder(f"{seller.get('sellerName', '')} {titel} {oms}", soort=soort)},
                    "bron": NAAM,
                })
            n += len(items)
            if len(items) < LIMIT:
                break
        print(f"  marktplaats {cat_naam}: {n}")
    return dieren
