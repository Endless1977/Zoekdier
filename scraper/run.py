"""Zoekdier scraper: haalt alle bronnen op en schrijft data/dieren.json.

Gebruik:  python scraper/run.py
Omgeving: ZOEKDIER_MAX_DETAIL (standaard 350 nieuwe Verhuisdieren-detailpagina's per run)
          ZOEKDIER_VHD_DAGEN (standaard 180: alleen profielen die zo recent gewijzigd zijn)
          MP_CLIENT_ID / MP_CLIENT_SECRET (Marktplaats API, optioneel)
          ZOEKDIER_DELAY (seconden tussen verzoeken, standaard 1.2)
"""
import datetime as dt
import json
import os
import sys
import traceback

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HIER, os.path.join(HIER, "adapters")]

import generiek  # noqa: E402
import ikzoekbaas  # noqa: E402
import marktplaats_api  # noqa: E402
from rassen import vul_rassen_aan  # noqa: E402
import verhuisdieren  # noqa: E402
from common import bewaar_geocache, geocodeer  # noqa: E402
from scoring import beoordeel_alles  # noqa: E402

DATA = os.path.join(HIER, "..", "data")
UIT = os.path.join(DATA, "dieren.json")
STATUS = os.path.join(DATA, "bronstatus.json")
MAX_DETAIL = int(os.environ.get("ZOEKDIER_MAX_DETAIL", "350"))
VHD_DAGEN = int(os.environ.get("ZOEKDIER_VHD_DAGEN", "180"))
IKZB_DAGEN = int(os.environ.get("ZOEKDIER_IKZB_DAGEN", "365"))
IKZB_MAX_DETAIL = int(os.environ.get("ZOEKDIER_IKZB_MAX_DETAIL", "500"))


def laad_vorige():
    try:
        with open(UIT, encoding="utf-8") as f:
            return {d["id"]: d for d in json.load(f).get("dieren", [])}
    except (OSError, ValueError):
        return {}


def run_sitemap_bron(mod, vorige, status, max_dagen, max_detail, statussen=None):
    """Sitemap -> per profiel detail ophalen als het nieuw of gewijzigd is (lastmod).
    Profielen die weg/geplaatst zijn worden onthouden zodat ze niet opnieuw opgehaald worden."""
    weg_pad = os.path.join(DATA, f"weg_{mod.__name__}.json")
    try:
        with open(weg_pad, encoding="utf-8") as f:
            weg = json.load(f)
    except (OSError, ValueError):
        weg = {}
    statussen = statussen or {}
    uit, nieuw_opgehaald, overgeslagen = [], 0, 0
    for basis in mod.sitemap(max_dagen):
        if basis["id"] in statussen:
            basis["status"] = statussen[basis["id"]]
        oud = vorige.get(basis["id"])
        if oud and oud.get("lastmod") == basis["lastmod"]:
            if basis.get("status"):
                oud["status"] = basis["status"]
            uit.append(oud)
            continue
        if weg.get(basis["id"]) == basis["lastmod"]:
            continue
        if nieuw_opgehaald >= max_detail:
            overgeslagen += 1
            if oud:  # oude versie tonen tot de volgende run
                uit.append(oud)
            continue
        d = mod.detail(basis)
        nieuw_opgehaald += 1
        if d:
            d.pop("foto", None)
            d["lastmod"] = basis["lastmod"]
            uit.append(d)
        else:
            weg[basis["id"]] = basis["lastmod"]
    with open(weg_pad, "w", encoding="utf-8") as f:
        json.dump(weg, f, separators=(",", ":"))
    status.append({"bron": mod.NAAM, "aantal": len(uit), "nieuw_detail": nieuw_opgehaald,
                   "nog_te_doen": overgeslagen, "ok": len(uit) > 0})
    return uit


def run_generiek(status):
    with open(os.path.join(HIER, "bronnen.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    uit = []
    for bron in cfg["bronnen"]:
        if not bron.get("actief"):
            continue
        try:
            urls = generiek.links(bron)
            gevonden = [d for d in (generiek.detail(bron, u) for u in urls) if d]
            uit += gevonden
            status.append({"bron": bron["naam"], "aantal": len(gevonden), "links": len(urls), "ok": len(gevonden) > 0})
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            status.append({"bron": bron["naam"], "aantal": 0, "ok": False, "fout": str(e)[:200]})
    return uit


def main():
    vorige = laad_vorige()
    status = []
    dieren = []
    bronnen = [
        (verhuisdieren, VHD_DAGEN, MAX_DETAIL, lambda: {b["id"]: b["status"] for b in verhuisdieren.lijst(1)}),
        (ikzoekbaas, IKZB_DAGEN, IKZB_MAX_DETAIL, dict),
    ]
    for mod, dagen, maxd, statusf in bronnen:
        try:
            dieren += run_sitemap_bron(mod, vorige, status, dagen, maxd, statusf())
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            status.append({"bron": mod.NAAM, "aantal": 0, "ok": False, "fout": str(e)[:200]})
            # bij een fout de vorige gegevens van deze bron behouden
            dieren += [d for d in vorige.values() if d.get("bron") == mod.NAAM]
    dieren += run_generiek(status)
    try:
        mp = marktplaats_api.ophalen()
        if mp is None:
            status.append({"bron": marktplaats_api.NAAM, "aantal": 0, "ok": False, "fout": "Geen API-sleutels (MP_CLIENT_ID/MP_CLIENT_SECRET)"})
        else:
            dieren += mp
            status.append({"bron": marktplaats_api.NAAM, "aantal": len(mp), "ok": len(mp) > 0})
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        status.append({"bron": marktplaats_api.NAAM, "aantal": 0, "ok": False, "fout": str(e)[:200]})
        dieren += [d for d in vorige.values() if d.get("bron") == marktplaats_api.NAAM]

    vul_rassen_aan(dieren)

    for d in dieren:
        if d.get("plaats") and not d.get("coord"):
            d["coord"] = geocodeer(d["plaats"])
    bewaar_geocache()
    beoordeel_alles(dieren)

    nu = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    aantallen = {}
    for d in dieren:
        aantallen[d["soort"]] = aantallen.get(d["soort"], 0) + 1
    os.makedirs(DATA, exist_ok=True)
    with open(UIT, "w", encoding="utf-8") as f:
        json.dump({"gegenereerd": nu, "aantallen": aantallen, "dieren": dieren}, f, ensure_ascii=False, separators=(",", ":"))
    with open(STATUS, "w", encoding="utf-8") as f:
        json.dump({"gegenereerd": nu, "bronnen": status}, f, ensure_ascii=False, indent=1)
    print(f"Klaar: {len(dieren)} dieren {aantallen}")
    for s in status:
        print("  ", s)


if __name__ == "__main__":
    main()
