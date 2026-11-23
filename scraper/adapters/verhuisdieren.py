"""Adapter voor Verhuisdieren.nl (stichting, herplaatsing van honden, katten en konijnen).

Overzicht:  https://verhuisdieren.nl/alle-dieren/?type=adopt&page=N  (24 per pagina)
Detail:     https://verhuisdieren.nl/plaatsprofiel/{id}-adoptie{hond|kat|konijn}-zoekt-baasje-{ras}-{plaats}/
Oppasdieren (gastgezin/logeren) worden overgeslagen: die zijn niet te adopteren.
Contactgegevens zijn op de site alleen zichtbaar voor ondersteuners (eenmalig €25).
"""
import re

from common import haal, kort, label_waarden, lees_gegadigden, lees_prijs, meta

BASIS = "https://verhuisdieren.nl"
NAAM = "Verhuisdieren.nl"
SLUG_RE = re.compile(r"/plaatsprofiel/(\d+)-(adoptie|verhuis|oppas)(hond|kat|konijn)[a-z]*-zoekt-[a-z]+-(.+?)/?$")
LABELS = ["Ras", "Leeftijd", "Woonplaats", "Geslacht", "Formaat", "Vacht", "Gecastreerd", "Oorsprong",
          "Adoptiekosten", "Vergoeding", "Adoptiebedrag", "Reden herplaatsing", "Laatste update"]
SOORT = {"hond": "hond", "kat": "kat", "konijn": "overig"}


def _slug_naar_tekst(s):
    return s.replace("-", " ").strip()


def _uit_slug(href, plaats):
    m = SLUG_RE.search(href)
    if not m:
        return None
    pid, soort_type, dier, rest = m.groups()
    ras = rest
    if plaats:
        pslug = re.sub(r"[^a-z0-9]+", "-", plaats.lower()).strip("-")
        if ras.endswith(pslug):
            ras = ras[: -len(pslug)].rstrip("-")
    return pid, soort_type, SOORT[dier], _slug_naar_tekst(ras)


def _foto_uit(el):
    for img in el.find_all("img"):
        for attr in ("data-src", "src", "data-lazy-src"):
            u = img.get(attr)
            if u and "cdn.verhuisdieren.nl" in u:
                return u
    m = re.search(r"url\(['\"]?(https://cdn\.verhuisdieren\.nl[^'\")]+)", str(el))
    return m.group(1) if m else None


def lijst(max_paginas=120):
    """Leest overzichtspagina's. Levert dicts met basisgegevens per dier."""
    gezien = set()
    for p in range(1, max_paginas + 1):
        soup = haal(f"{BASIS}/alle-dieren/?type=adopt&page={p}")
        if not soup:
            break
        nieuw = 0
        for a in soup.select('a[href*="/plaatsprofiel/"]'):
            href = a.get("href", "")
            delen = [s for s in a.stripped_strings]
            if not delen:
                continue
            plaats = delen[-1] if len(delen) > 1 else ""
            info = _uit_slug(href, plaats)
            if not info:
                continue
            pid, soort_type, soort, ras = info
            if soort_type == "oppas" or pid in gezien:
                continue
            tekst = " ".join(delen)
            if re.search(r"\b(gastgezin|logeren)\b", tekst, re.I):
                continue
            gezien.add(pid)
            nieuw += 1
            datum = re.search(r"\d{2}-\d{2}-\d{4}", tekst)
            yield {
                "id": f"vhd-{pid}",
                "url": href if href.startswith("http") else BASIS + href,
                "naam": delen[0],
                "soort": soort,
                "ras": ras,
                "plaats": plaats,
                "status": "gereserveerd" if re.search(r"gereserveerd", tekst, re.I) else "beschikbaar",
                "geplaatst": datum.group(0) if datum else None,
                "foto": _foto_uit(a),
            }
        print(f"  verhuisdieren pagina {p}: {nieuw} dieren")
        if nieuw == 0:
            break


def detail(basis):
    """Haalt detailpagina op en vult het dier aan. Geeft None als het dier weg is."""
    soup = haal(basis["url"])
    if not soup:
        return None
    tekst = soup.get_text(" ")
    if re.search(r"niet meer beschikbaar", tekst, re.I):
        return None
    v = label_waarden(soup, LABELS)
    fotos = []
    for img in soup.find_all("img"):
        u = img.get("data-src") or img.get("src") or ""
        if "cdn.verhuisdieren.nl" in u and u not in fotos and not re.search(r"logo|icon|avatar", u, re.I):
            fotos.append(u)
    if not fotos and basis.get("foto"):
        fotos = [basis["foto"]]
    prijs_tekst = v.get("Adoptiekosten") or v.get("Vergoeding") or v.get("Adoptiebedrag") or ""
    if re.search(r"doneren", prijs_tekst, re.I):
        prijs_tekst = "Vrijwillige donatie aan Verhuisdieren"
    beschrijving = meta(soup, "og:description") or meta(soup, "description")
    return {
        **basis,
        "ras": v.get("Ras") or basis.get("ras"),
        "leeftijd": v.get("Leeftijd"),
        "geslacht": v.get("Geslacht"),
        "plaats": v.get("Woonplaats") or basis.get("plaats"),
        "herkomst": v.get("Oorsprong"),
        "prijs_tekst": prijs_tekst or None,
        "prijs": lees_prijs(prijs_tekst) if "donatie" not in prijs_tekst.lower() else 0.0,
        "fotos": fotos[:8],
        "gegadigden": lees_gegadigden(tekst),
        "beschrijving": kort(beschrijving),
        "bijgewerkt": v.get("Laatste update"),
        "aanbieder": {"naam": "Particulier via Verhuisdieren", "type": "herplaatsing"},
        "bron": NAAM,
    }
