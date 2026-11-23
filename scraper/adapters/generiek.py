"""Generieke adapter, ingesteld via scraper/bronnen.json.

Per bron: overzichtspagina's -> links die op `link_patroon` passen -> detailpagina.
Op de detailpagina wordt gezocht naar: JSON-LD, og:-tags, label/waarde-regels
(Ras, Leeftijd, Prijs, Locatie, ...), het woord 'gereserveerd' en aantallen gegadigden.
Zo kun je een nieuw asiel toevoegen zonder code te schrijven.
"""
import hashlib
import json
import re
import urllib.parse

from common import haal, herken_soort, kort, label_waarden, lees_gegadigden, lees_prijs, meta
from scoring import classificeer_aanbieder

LABELS = ["Naam", "Ras", "Soort", "Diersoort", "Leeftijd", "Geboortedatum", "Geslacht", "Locatie", "Plaats",
          "Woonplaats", "Asiel", "Opvang", "Prijs", "Vraagprijs", "Adoptieprijs", "Adoptiekosten",
          "Adoptiebijdrage", "Vergoeding", "Status", "Fokker", "Kennel", "Cattery", "Kennelnaam", "Aanbieder"]


def links(bron):
    pat = re.compile(bron["link_patroon"])
    gezien = []
    for start in bron["lijst_urls"]:
        paginas = bron.get("paginas", 1)
        for p in range(1, paginas + 1):
            url = start.replace("{pagina}", str(p))
            soup = haal(url)
            if not soup:
                break
            voor = len(gezien)
            for a in soup.find_all("a", href=True):
                href = urllib.parse.urljoin(url, a["href"]).split("#")[0]
                if pat.search(href) and href not in gezien:
                    gezien.append(href)
            print(f"  {bron['naam']} {url}: {len(gezien) - voor} links")
            if "{pagina}" not in start or len(gezien) == voor:
                break
    return gezien[: bron.get("max_detail", 200)]


def _jsonld(soup):
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except ValueError:
            continue
        for d in data if isinstance(data, list) else [data]:
            if isinstance(d, dict):
                return d
    return {}


def detail(bron, url):
    soup = haal(url)
    if not soup:
        return None
    tekst = soup.get_text(" ")
    if re.search(r"(niet meer beschikbaar|is geplaatst|heeft een nieuw thuis|al geadopteerd)", tekst, re.I):
        return None
    ld = _jsonld(soup)
    v = label_waarden(soup, LABELS)
    titel = v.get("Naam") or ld.get("name") or meta(soup, "og:title") or (soup.title.string if soup.title else "")
    titel = re.split(r"\s[|\-–]\s", titel or "")[0].strip()
    beschrijving = meta(soup, "og:description") or ld.get("description") or ""
    fotos = []
    og = meta(soup, "og:image")
    if og:
        fotos.append(og)
    for img in soup.find_all("img"):
        u = img.get("data-src") or img.get("src") or ""
        if not u or u.startswith("data:"):
            continue
        u = urllib.parse.urljoin(url, u)
        if re.search(r"logo|icon|sprite|avatar|banner|footer|header", u, re.I):
            continue
        if bron.get("foto_patroon") and not re.search(bron["foto_patroon"], u):
            continue
        if u not in fotos:
            fotos.append(u)
    prijs_tekst = next((v[k] for k in ("Prijs", "Vraagprijs", "Adoptieprijs", "Adoptiekosten", "Adoptiebijdrage", "Vergoeding") if k in v), None)
    soort = bron.get("soort") or herken_soort(v.get("Soort"), v.get("Diersoort"), url, titel, v.get("Ras"))
    status_t = (v.get("Status") or "") + " " + " ".join(soup.find_all(string=re.compile(r"gereserveerd", re.I))[:1])
    aanbieder_naam = v.get("Kennelnaam") or v.get("Kennel") or v.get("Cattery") or v.get("Fokker") or v.get("Asiel") or v.get("Opvang") or v.get("Aanbieder") or bron["naam"]
    atype = bron.get("aanbieder_type") or classificeer_aanbieder(f"{aanbieder_naam} {beschrijving}", soort=soort)
    return {
        "id": bron["sleutel"] + "-" + hashlib.sha1(url.encode()).hexdigest()[:10],
        "url": url,
        "naam": titel or "Onbekend",
        "soort": soort,
        "ras": v.get("Ras"),
        "leeftijd": v.get("Leeftijd") or v.get("Geboortedatum"),
        "geslacht": v.get("Geslacht"),
        "plaats": v.get("Locatie") or v.get("Plaats") or v.get("Woonplaats") or bron.get("plaats"),
        "prijs_tekst": prijs_tekst,
        "prijs": lees_prijs(prijs_tekst),
        "fotos": fotos[:8],
        "status": "gereserveerd" if re.search(r"gereserveerd", status_t, re.I) else "beschikbaar",
        "gegadigden": lees_gegadigden(tekst),
        "beschrijving": kort(beschrijving),
        "aanbieder": {"naam": aanbieder_naam, "type": atype},
        "bron": bron["naam"],
    }
