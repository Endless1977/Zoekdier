"""Gedeelde hulpfuncties: beleefd ophalen, soort herkennen, prijs lezen, geocoderen."""
import json
import os
import re
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

UA = "ZoekdierBot/1.0 (+https://github.com/Endless1977/Zoekdier; persoonlijk zoekprogramma)"
VERTRAGING = float(os.environ.get("ZOEKDIER_DELAY", "1.2"))  # seconden tussen verzoeken per host

_sessie = requests.Session()
_sessie.headers.update({"User-Agent": UA, "Accept-Language": "nl-NL,nl;q=0.9"})
_laatste = {}


def haal(url, timeout=25):
    """GET met vertraging per host. Geeft BeautifulSoup of None."""
    host = urllib.parse.urlparse(url).netloc
    wacht = VERTRAGING - (time.time() - _laatste.get(host, 0))
    if wacht > 0:
        time.sleep(wacht)
    _laatste[host] = time.time()
    try:
        r = _sessie.get(url, timeout=timeout)
        if r.status_code != 200:
            print(f"  ! {r.status_code} {url}")
            return None
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        print(f"  ! fout {url}: {e}")
        return None


SOORT_WOORDEN = [
    ("hond", r"\b(hond|honden|pup|pups|puppy|reu|teef|kennel)\b|adoptiehond|verhuishond|oppashond"),
    ("kat", r"\b(kat|katten|poes|poezen|kater|kitten|kittens|cattery)\b|adoptiekat|verhuiskat|oppaskat"),
    ("vogel", r"\b(vogels?|duif|duiven|kip|kippen|kriel|krielen|agapornis\w*|kaketoes?|ara'?s?|rosella'?s?)\b|(parkiet|papegaai|kanarie|vink|amadine)"),
]


def herken_soort(*teksten, standaard="overig"):
    t = " ".join(x or "" for x in teksten).lower()
    for soort, pat in SOORT_WOORDEN:
        if re.search(pat, t):
            return soort
    return standaard


def lees_prijs(tekst):
    """'€ 1.250,-' -> 1250.0 ; 'gratis' -> 0 ; anders None."""
    if not tekst:
        return None
    t = tekst.lower()
    if "gratis" in t:
        return 0.0
    bereik = re.search(r"€?\s*(\d[\d.]*)\s*(?:-|tot|t/m)\s*€?\s*(\d[\d.]*)", tekst)
    if bereik:  # '€400-€575' of '100-275 euro': ondergrens (vanaf-prijs)
        laag = bereik.group(1).replace(".", "")
        if laag.isdigit():
            return float(laag)
    m = re.search(r"€\s*([\d.]+)(?:,(\d{1,2}))?", tekst) or re.search(r"([\d.]+)(?:,(\d{1,2}))?\s*(euro|eur)\b", t)
    if not m:
        return None
    heel = m.group(1).replace(".", "")
    if not heel.isdigit():
        return None
    return float(heel) + (float("0." + m.group(2)) if m.group(2) else 0)


def lees_gegadigden(tekst):
    if not tekst:
        return None
    m = re.search(r"(\d+)\s*(gegadigden|geïnteresseerden|geinteresseerden|reacties|aanvragen|kandidaten|keer bewaard)", tekst.lower())
    return int(m.group(1)) if m else None


def label_waarden(soup, labels):
    """Zoekt 'Label' gevolgd door waarde in de tekstregels van een pagina."""
    regels = [r.strip() for r in soup.get_text("\n").split("\n") if r.strip()]
    uit = {}
    lab_lc = {l.lower(): l for l in labels}
    for i, r in enumerate(regels):
        key = r.rstrip(":").lower()
        if key in lab_lc and lab_lc[key] not in uit and i + 1 < len(regels):
            uit[lab_lc[key]] = regels[i + 1]
        else:
            m = re.match(r"^([A-Za-zë ]{2,20}):\s*(.+)$", r)
            if m and m.group(1).lower() in lab_lc and lab_lc[m.group(1).lower()] not in uit:
                uit[lab_lc[m.group(1).lower()]] = m.group(2)
    return uit


def meta(soup, prop):
    t = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return t.get("content", "").strip() if t else ""


def kort(tekst, n=320):
    tekst = re.sub(r"\s+", " ", tekst or "").strip()
    return tekst if len(tekst) <= n else tekst[: n - 1].rsplit(" ", 1)[0] + "…"


# ---------- geocoderen via PDOK Locatieserver (gratis, overheid) ----------
GEOCACHE_PAD = os.path.join(os.path.dirname(__file__), "..", "data", "geocache.json")
try:
    with open(GEOCACHE_PAD, encoding="utf-8") as f:
        _geocache = json.load(f)
except (OSError, ValueError):
    _geocache = {}


def geocodeer(plaats):
    if not plaats:
        return None
    sleutel = plaats.strip().lower()
    if sleutel in _geocache:
        return _geocache[sleutel]
    url = ("https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?rows=1&fl=centroide_ll,weergavenaam"
           "&fq=type:(woonplaats OR postcode OR gemeente)&q=" + urllib.parse.quote(plaats))
    res = None
    try:
        time.sleep(0.2)
        r = _sessie.get(url, timeout=15)
        docs = r.json().get("response", {}).get("docs", [])
        if docs:
            m = re.match(r"POINT\(([\d.]+) ([\d.]+)\)", docs[0]["centroide_ll"])
            if m:
                res = [round(float(m.group(2)), 4), round(float(m.group(1)), 4)]  # lat, lon
    except Exception as e:  # noqa: BLE001
        print(f"  ! geocode {plaats}: {e}")
        return None
    _geocache[sleutel] = res
    return res


def bewaar_geocache():
    os.makedirs(os.path.dirname(GEOCACHE_PAD), exist_ok=True)
    with open(GEOCACHE_PAD, "w", encoding="utf-8") as f:
        json.dump(_geocache, f, ensure_ascii=False, indent=0, sort_keys=True)


def alle_kenmerken(soup, max_aantal=40):
    """Alle korte label/waarde-paren van een pagina (tabelrijen, dt/dd, 'Label: waarde')."""
    uit = {}

    def zet(k, v):
        k = re.sub(r"\s+", " ", k or "").strip(" :")
        v = re.sub(r"\s+", " ", v or "").strip()
        if 1 < len(k) <= 40 and 0 < len(v) <= 160 and k not in uit and not k.isdigit():
            uit[k] = v

    for tr in soup.find_all("tr"):
        cellen = tr.find_all(["td", "th"])
        if len(cellen) == 2:
            zet(cellen[0].get_text(" "), cellen[1].get_text(" "))
    for dt_ in soup.find_all("dt"):
        dd = dt_.find_next_sibling("dd")
        if dd:
            zet(dt_.get_text(" "), dd.get_text(" "))
    for el in soup.find_all(["li", "p", "span", "div"]):
        if el.find(["li", "p", "div", "table"]):
            continue
        m = re.match(r"^\s*([A-Za-zÀ-ÿ/ ]{2,40}):\s*(.{1,160})$", el.get_text(" ").strip())
        if m:
            zet(m.group(1), m.group(2))
        if len(uit) >= max_aantal:
            break
    return dict(list(uit.items())[:max_aantal])


def hoofdtekst(soup, eigen_url=""):
    """Paginatekst zonder menu/voet en zonder kaartjes van ándere dieren (die vervuilen kleur/gezondheid)."""
    import copy
    s = copy.copy(soup)
    for el in s.find_all(["nav", "header", "footer", "script", "style", "noscript", "form"]):
        el.decompose()
    for a in s.find_all("a", href=True):
        if re.search(r"/(plaatsprofiel|asieldier)/", a["href"]) and (not eigen_url or a["href"].rstrip("/") not in eigen_url):
            a.decompose()
    return re.sub(r"\s+", " ", s.get_text(" ")).strip()
