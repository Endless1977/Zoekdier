# Zoekdier – werkafspraken

Na **elke** wijziging aan het programma (app, scraper of workflows):
1. `python tests/test_parsers.py` moet slagen.
2. **README.md bijwerken:** de functielijst, de bestandstabel en een regel in de tabel **Wijzigingen** (datum + wat er veranderd is).
3. **Schermafbeeldingen vernieuwen:** `python tools/screenshots.py` (lokaal `CHROME_PATH` zetten als Playwright geen eigen Chromium heeft). Komt er een nieuw scherm of een nieuwe functie bij, voeg die stap toe aan `tools/screenshots.py` en zet de afbeelding in de README. De Action *Schermafbeeldingen* doet dit ook automatisch na een push, met echte foto's.
4. De repobeschrijving (About) aanpassen als de app iets nieuws kan.

Overig:
- Taal van de app en de README: Nederlands.
- De app blijft één bestand (`index.html`) zonder build. Opslag in de browser verloopt via `opslag` (try/catch).
- Gebruik in schermafbeeldingen en voorbeelden een neutrale plaats (bijv. Utrecht), niet het adres van de eigenaar.
- Marktplaats alleen via de officiële API, nooit scrapen.
- Het wapen (`assets/wapen.svg`) staat in de kop van de app.
