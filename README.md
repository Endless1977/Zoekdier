# 🐾 Zoekdier

Zoekprogramma voor honden, katten, vogels en overige dieren. Het haalt herplaatsings- en asieldieren op en toont ze per tab, met filters en een indicatie van hoe betrouwbaar elke aanbieder is.

**Spelen/gebruiken:** https://endless1977.github.io/Zoekdier/

## Wat kan het
- Tabs: **Honden · Katten · Vogels · Overig**, met het aantal dieren per tab
- Filters: zoekwoord, **ras**, **afstand** (postcode/plaats via PDOK, of 📍 je eigen locatie), **beschikbaar/gereserveerd**, **max. aantal gegadigden**, prijs van–tot, alleen met foto's, type aanbieder (asiel, herplaatsing, **kennel**, **cattery/katterie**, kwekerij, particulier, handelaar), minimale betrouwbaarheid
- Knop **🚫 Broodfokkers uitsluiten**
- Een kaart per dier met foto's, prijs, plaats en afstand, gegadigden en de betrouwbaarheidsmeter. Het detailvenster toont de fotogalerij en hoe de score is opgebouwd.
- ☆ Bewaren (blijft in je browser), sorteren op betrouwbaarheid, afstand, nieuwste, prijs of gegadigden
- Doorlinks naar Verhuisdieren, Ik zoek baas, Raad van Beheer en Marktplaats voor je zoekopdracht

## Hoe het werkt
```
GitHub Action (elke 6 uur)  →  scraper/run.py  →  data/dieren.json  →  index.html (GitHub Pages)
```
- `scraper/adapters/verhuisdieren.py`: uitlezer voor Verhuisdieren.nl (adoptiedieren; oppasdieren worden overgeslagen)
- `scraper/adapters/generiek.py` + `scraper/bronnen.json`: asielen, kennels en catteries toevoegen **zonder code**. Je geeft per bron de overzichts-URL's en een regex voor dierpagina's op.
- `scraper/scoring.py`: betrouwbaarheid, broodfokkersignalen en het type aanbieder
- `data/bronstatus.json`: per bron hoeveel dieren de laatste run opleverde (te zien onder ℹ️ Bronnen in de app)

## Betrouwbaarheid (0–100)
Startscore per aanbieder: asiel 75, herplaatsing 65, kennel/cattery 55, kwekerij 50, particulier 45, handelaar 30.
- **Pluspunten:** stamboom (Raad van Beheer/NHSB, FIFe/Felikat), rasvereniging, UBN, chip/paspoort, gezondheidsonderzoeken van de ouderdieren, ouderdieren te zien, vaccinaties, geringde vogels
- **Broodfokkersignalen (minpunten):** “direct meenemen”, bezorgen, overdracht op een parkeerplaats, meerdere rassen of nesten, importpups, te jong (hond < 7 wk, kat < 12 wk), vouwoorkat (verboden sinds 2026), geen papieren, vooruitbetalen, prijs ver onder de mediaan van het ras, dezelfde aanbieder met ≥ 3 rassen

Vanaf 25 signaalpunten, of bij een handelaar, krijgt de advertentie het label **broodfokker?** en verdwijnt ze met de knop. Het blijft een indicatie: kijk altijd zelf.

## Instellen (eenmalig)
1. **Settings → Pages:** Source = *Deploy from a branch*, branch `main`, map `/ (root)`
2. **Settings → Actions → General → Workflow permissions:** *Read and write*
3. **Actions → Dieren ophalen → Run workflow.** De eerste run duurt ongeveer 10 minuten. Daarna gaat het elke 6 uur vanzelf.

Lokaal draaien: `pip install -r requirements.txt && python scraper/run.py`, en dan `python -m http.server` in de repomap.

## Beperkingen
- **Gegadigden:** de meeste sites tonen dit niet. Dan staat er "onbekend", en met een vinkje kies je of die dieren meetellen in het filter.
- **Marktplaats** wordt niet uitgelezen, want hun voorwaarden verbieden dat. De app opent wel je zoekopdracht daar.
- Een site die zijn opbouw verandert, levert 0 dieren op in de bronstatus. Pas dan het patroon aan in `bronnen.json` of in de adapter.
