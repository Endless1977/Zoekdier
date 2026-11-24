"""Maakt de schermafbeeldingen voor de README (docs/screenshots/*.png).

Gebruik:  pip install playwright && playwright install chromium
          python tools/screenshots.py            (start zelf een lokale webserver)
Draait ook automatisch in de GitHub Action 'Schermafbeeldingen' na elke wijziging van de app.
"""
import functools
import http.server
import os
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UIT = os.path.join(ROOT, "docs", "screenshots")
POORT = 8799

# Voorbeeldprofielen (neutrale plaats, niet je eigen adres)
PROFIELEN = """[
 {"id":"demo1","naam":"Kat dichtbij Utrecht","tab":"kat","zoek":"","rassen":[],"kleuren":[],"vacht":[],"kenmOnbekend":true,
  "gezond":"geenmed","gezOnbekend":true,"locatie":"Utrecht","coord":[52.0907,5.1214],"afstand":50,"status":"beschikbaar",
  "gegMax":"","gegOnbekend":true,"prijsMin":"","prijsMax":"","types":[],"minScore":0,"foto":true,"geenBrood":true},
 {"id":"demo2","naam":"Herder, gezond","tab":"hond","zoek":"","rassen":["herder"],"kleuren":[],"vacht":[],"kenmOnbekend":true,
  "gezond":"geenprob","gezOnbekend":true,"locatie":"","coord":null,"afstand":305,"status":"",
  "gegMax":"","gegOnbekend":true,"prijsMin":"","prijsMax":"","types":[],"minScore":0,"foto":false,"geenBrood":true}
]"""


def server():
    class Stil(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Stil, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", POORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main():
    os.makedirs(UIT, exist_ok=True)
    httpd = server()
    url = f"http://127.0.0.1:{POORT}/"
    fouten = []
    with sync_playwright() as p:
        exe = os.environ.get("CHROME_PATH")
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

        def pagina(breedte, hoogte, mobiel=False):
            ctx = b.new_context(viewport={"width": breedte, "height": hoogte}, device_scale_factor=2 if mobiel else 1,
                                is_mobile=mobiel, has_touch=mobiel, locale="nl-NL")
            ctx.add_init_script(f"localStorage.setItem('zoekdier:profielen', {PROFIELEN!r});")
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: fouten.append(str(e)))
            pg.goto(url)
            pg.wait_for_selector(".kaart", timeout=20000)
            pg.wait_for_timeout(2500)  # foto's laden
            return pg

        pg = pagina(1400, 900)
        pg.screenshot(path=f"{UIT}/1-overzicht.png")

        pg.click(".kaart >> nth=0")
        pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{UIT}/2-detail.png")
        pg.keyboard.press("Escape")

        pg.click("#nieuwProfiel")
        pg.fill("#pNaam", "Kleine hond, geen medicatie")
        pg.select_option("#pTab", "hond")
        pg.click('#pKleur input[data-kleur="zwart"]')
        pg.click('#pKleur input[data-kleur="wit"]')
        pg.click('#pVacht input[data-vacht="kort"]')
        pg.select_option("#pGezond", "geenmed")
        pg.fill("#pLoc", "Utrecht")
        pg.fill("#pAfstand", "40")
        pg.wait_for_timeout(300)
        pg.screenshot(path=f"{UIT}/3-zoekprofiel.png")
        pg.keyboard.press("Escape")

        pg.click('.pknop[data-pid="demo1"]')
        pg.wait_for_timeout(2000)
        pg.screenshot(path=f"{UIT}/4-profiel-resultaten.png")

        pg.click("#broodSchakel")
        pg.evaluate("document.querySelector('#filters').scrollTop = 99999")
        pg.wait_for_timeout(300)
        pg.locator("#filters").screenshot(path=f"{UIT}/5-filters.png")

        mob = pagina(390, 844, mobiel=True)
        mob.screenshot(path=f"{UIT}/6-mobiel.png")
        b.close()
    httpd.shutdown()
    if fouten:
        print("JavaScript-fouten:", fouten)
        sys.exit(1)
    print("Schermafbeeldingen gemaakt in", UIT)


if __name__ == "__main__":
    main()
