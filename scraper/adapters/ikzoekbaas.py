"""Adapter voor Ik zoek baas (Dierenbescherming), alle aangesloten asielen.

Profielen: https://ikzoekbaas.dierenbescherming.nl/sitemap-ikzoekbaas.xml (sitemap-index)
  -> sitemap-ikzoekbaas-dierprofielen-N.xml -> /asieldier/{honden|katten|vogels|konijnen-en-knagers|...}/{id}-{naam}
Op de overzichtspagina's worden de kaartjes met JavaScript geladen, de detailpagina's niet.
"""
import datetime as dt
import re

from common import alle_kenmerken, haal, hoofdtekst, kort, label_waarden, meta

BASIS = "https://ikzoekbaas.dierenbescherming.nl"
NAAM = "Ik zoek baas (Dierenbescherming)"
URL_RE = re.compile(r"/asieldier/([a-z-]+)/(\d+)-([a-z0-9-]*)")
SOORT = {"honden": "hond", "katten": "kat", "vogels": "vogel"}
LABELS = ["Soort", "Ras", "Geslacht", "Geboortedatum", "Leeftijd", "Plaatsbaar vanaf", "Beschikbaarheid",
          "Kan bij kinderen", "Kan bij honden", "Kan bij katten", "Speciale zorg", "Gecastreerd / Gesteriliseerd",
          "Schofthoogte", "Adoptieprijs", "Adoptiekosten"]
MAANDEN = {m: i + 1 for i, m in enumerate(["januari", "februari", "maart", "april", "mei", "juni", "juli",
                                            "augustus", "september", "oktober", "november", "december"])}


def sitemap(max_dagen=365):
    index = haal(f"{BASIS}/sitemap-ikzoekbaas.xml", timeout=60)
    if not index:
        return []
    subs = [l.get_text(strip=True) for l in index.find_all("loc") if "dierprofielen" in l.get_text()]
    grens = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max_dagen)
    uit = []
    for sub in subs:
        soup = haal(sub, timeout=60)
        if not soup:
            continue
        for u in soup.find_all("url"):
            loc = u.find("loc").get_text(strip=True) if u.find("loc") else ""
            lm = u.find("lastmod").get_text(strip=True) if u.find("lastmod") else ""
            m = URL_RE.search(loc)
            if not m:
                continue
            try:
                t = dt.datetime.fromisoformat(lm)
            except ValueError:
                continue
            if t < grens:
                continue
            uit.append({"id": f"ikzb-{m.group(2)}", "url": loc, "soort": SOORT.get(m.group(1), "overig"),
                        "categorie": m.group(1), "lastmod": lm, "_t": t})
    uit.sort(key=lambda d: d["_t"], reverse=True)
    for d in uit:
        d.pop("_t")
    print(f"  ikzoekbaas sitemap: {len(uit)} profielen van de laatste {max_dagen} dagen")
    return uit


def leeftijd_uit(geboortedatum):
    m = re.search(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", (geboortedatum or "").lower())
    if not m or m.group(2) not in MAANDEN:
        return None
    geb = dt.date(int(m.group(3)), MAANDEN[m.group(2)], int(m.group(1)))
    dagen = (dt.date.today() - geb).days
    if dagen < 0:
        return None
    if dagen < 120:
        return f"{dagen // 7} weken"
    if dagen < 730:
        return f"{dagen // 30} maanden"
    return f"{dagen // 365} jaar"


def _uniek_grootste(fotos):
    """cms-URL's bevatten '_330x285_crop...' per formaat; per bestandsnaam alleen het grootste houden."""
    beste = {}
    for u in fotos:
        naam = re.sub(r"\?.*$", "", u).rsplit("/", 1)[-1]
        m = re.search(r"/_(\d+)x(\d+)_", u)
        opp = int(m.group(1)) * int(m.group(2)) if m else 10**9
        if naam not in beste or opp > beste[naam][0]:
            beste[naam] = (opp, u)
    volgorde = []
    for u in fotos:
        naam = re.sub(r"\?.*$", "", u).rsplit("/", 1)[-1]
        if beste[naam][1] not in volgorde:
            volgorde.append(beste[naam][1])
    return volgorde


def detail(basis):
    soup = haal(basis["url"])
    if not soup:
        return None
    v = label_waarden(soup, LABELS)
    beschikbaar = (v.get("Beschikbaarheid") or "").lower()
    if re.search(r"geplaatst|niet (meer )?beschikbaar|overleden|teruggeplaatst bij eigenaar", beschikbaar):
        return None
    h1 = soup.find("h1")
    naam = (h1.get_text(" ", strip=True) if h1 else "") or meta(soup, "og:title")
    tekst = soup.get_text("\n")
    # asiel: regel met asielwoord, gevolgd door adres met postcode
    asiel, plaats = None, None
    m = re.search(r"([^\n]*(?:asiel|dierentehuis|dierenopvang|opvang|dierencentrum|schuthok|kattenhuis|vogelopvang)[^\n]*)[,\n]+\s*([^\n]*?)\s*(\d{4}\s?[A-Z]{2})\s+([A-Z][^\n,]+)", tekst, re.I)
    if m:
        asiel = m.group(1).strip(" ,")
        plaats = m.group(4).strip()
    else:
        m = re.search(r"\b\d{4}\s?[A-Z]{2}\s+([A-Z][a-zA-Z' -]+)", tekst)
        plaats = m.group(1).strip() if m else None
    fotos = []
    og = meta(soup, "og:image")
    if og:
        fotos.append(og)
    for img in soup.find_all("img"):
        u = img.get("data-src") or img.get("src") or ""
        if "cms.dierenbescherming.nl/assets" in u and u not in fotos and not re.search(r"logo|icon|header|banner", u, re.I):
            fotos.append(u)
    fotos = _uniek_grootste(fotos)
    prijs_tekst = v.get("Adoptieprijs") or v.get("Adoptiekosten") or "Zie tarieven van het asiel"
    beschrijving = meta(soup, "og:description") or meta(soup, "description")
    extra = "; ".join(f"{k}: {v[k]}" for k in ("Kan bij kinderen", "Kan bij honden", "Kan bij katten") if v.get(k))
    return {
        "id": basis["id"],
        "url": basis["url"],
        "lastmod": basis["lastmod"],
        "naam": naam or "Onbekend",
        "soort": basis["soort"],
        "ras": v.get("Ras") or v.get("Soort"),
        "leeftijd": v.get("Leeftijd") or leeftijd_uit(v.get("Geboortedatum")),
        "geslacht": v.get("Geslacht"),
        "plaats": plaats,
        "prijs": None,
        "prijs_tekst": prijs_tekst,
        "fotos": fotos[:8],
        "status": "gereserveerd" if "gereserveerd" in beschikbaar else "beschikbaar",
        "gegadigden": None,
        "beschrijving": kort(" ".join(x for x in (beschrijving, extra) if x)),
        "kenmerken": alle_kenmerken(soup),
        "_tekst": hoofdtekst(soup, basis["url"]),
        "aanbieder": {"naam": asiel or "Asiel (Dierenbescherming)", "type": "asiel"},
        "bron": NAAM,
    }
