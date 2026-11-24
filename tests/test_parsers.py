"""Snelle offline tests: python tests/test_parsers.py"""
import os, sys
HIER = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HIER, "..", "scraper"), os.path.join(HIER, "..", "scraper", "adapters")]
from bs4 import BeautifulSoup
import verhuisdieren, common
from scoring import beoordeel_alles, classificeer_aanbieder

# slug-ontleding
assert verhuisdieren._uit_slug("/plaatsprofiel/255201-adoptiekat-zoekt-baasje-cypers-geleen", "Geleen") == ("255201", "adoptie", "kat", "cypers")
assert verhuisdieren._uit_slug("/plaatsprofiel/245139-adoptiehond-zoekt-baasje-bullterier-miniatur-s-gravenhage", "'s-Gravenhage")[3] == "bullterier miniatur"
assert verhuisdieren._uit_slug("/plaatsprofiel/256936-oppashond-zoekt-gastgezin-mix-roemenie", "Roemenië")[1] == "oppas"

# label/waarde
soup = BeautifulSoup("<div><dt>Ras</dt><dd>Miniature poodle</dd><dt>Leeftijd</dt><dd>1 jaar</dd><p>Prijs: € 1.250,-</p></div>", "html.parser")
v = common.label_waarden(soup, ["Ras", "Leeftijd", "Prijs"])
assert v == {"Ras": "Miniature poodle", "Leeftijd": "1 jaar", "Prijs": "€ 1.250,-"}, v
assert common.lees_prijs("€ 1.250,-") == 1250 and common.lees_prijs("gratis") == 0 and common.lees_prijs("n.o.t.k.") is None
assert common.lees_gegadigden("Er zijn al 12 gegadigden") == 12
assert common.herken_soort("Jonge grasparkieten") == "vogel" and common.herken_soort("Lieve kater") == "kat"
assert classificeer_aanbieder("Cattery Maine Coon FIFe", soort="kat") == "cattery"
assert classificeer_aanbieder("Dierenasiel Apeldoorn") == "asiel"

# scoring
d = [
  {"id":"a","soort":"hond","ras":"Labrador","naam":"Pups","leeftijd":"6 weken","beschrijving":"Direct mee te nemen, kunnen bezorgd worden","fotos":["x"],"prijs":300,"aanbieder":{"naam":"Hans","type":"particulier"}},
  {"id":"b","soort":"hond","ras":"Labrador","naam":"Nestje","leeftijd":"9 weken","beschrijving":"Met stamboom Raad van Beheer, UBN 123, ouders HD-vrij, moeder aanwezig","fotos":["x"],"prijs":1400,"aanbieder":{"naam":"Kennel van de Veluwe","type":"kennel"}},
  {"id":"c","soort":"kat","ras":"Scottish fold","naam":"Kitten","beschrijving":"","fotos":[],"aanbieder":{"naam":"X","type":"particulier"}},
  {"id":"d","soort":"hond","ras":"Mix","naam":"Ben","beschrijving":"Gecastreerd, gechipt","fotos":["x"],"aanbieder":{"naam":"Dierenasiel","type":"asiel"}},
]
beoordeel_alles(d)
for x in d: print(x["id"], x["betrouwbaarheid"]["score"], x["broodfokker_verdacht"], x["broodfokker_signalen"])
assert d[0]["broodfokker_verdacht"] and not d[1]["broodfokker_verdacht"] and d[2]["broodfokker_verdacht"] and not d[3]["broodfokker_verdacht"]
assert d[1]["betrouwbaarheid"]["score"] > 80 > d[0]["betrouwbaarheid"]["score"]
print("alle tests ok")

# ---- verhuisdieren sitemap ----
import datetime as dt
nu = dt.datetime.now(dt.timezone.utc)
xml = f"""<urlset><url><loc>https://verhuisdieren.nl/plaatsprofiel/9286-adoptiehond-zoekt-baasje-dwergkeesje-helmond/</loc><lastmod>2022-10-27T12:18:45+02:00</lastmod></url>
<url><loc>https://verhuisdieren.nl/plaatsprofiel/257441-adoptiekat-zoekt-baasje-shorthair-mix-dubai/</loc><lastmod>{nu.isoformat()}</lastmod></url>
<url><loc>https://verhuisdieren.nl/plaatsprofiel/257460-oppashond-zoekt-gastgezin-mix-veles/</loc><lastmod>{nu.isoformat()}</lastmod></url>
<url><loc>https://verhuisdieren.nl/plaatsprofiel/257500-adoptiecavia-zoekt-baasje-rex-ede/</loc><lastmod>{nu.isoformat()}</lastmod></url></urlset>"""
verhuisdieren.haal = lambda url, timeout=25: BeautifulSoup(xml, "html.parser")
sm = verhuisdieren.sitemap(180)
assert [x["id"] for x in sm] == ["vhd-257441", "vhd-257500"], sm
assert sm[1]["soort"] == "overig"

# ---- marktplaats API (nagebootst) ----
import marktplaats_api as mpa, rassen
class Nep:
    def get(self, pad, **p):
        if pad == "/v1/categories":
            return {"_embedded": {"mp:category": [{"categoryId": 1, "labels": {"nl-NL": "Auto's"}}, {"categoryId": 395, "labels": {"nl-NL": "Dieren en Toebehoren"}}]}}
        if pad == "/v1/categories/395":
            return {"_embedded": {"mp:category": [{"categoryId": 400, "name": "Honden | Retrievers"}, {"categoryId": 401, "name": "Honden en Toebehoren"}, {"categoryId": 402, "name": "Vogels | Parkieten"}]}}
        if pad == "/v1/search":
            if p["offset"] > 0: return {"_embedded": {"mp:search-result": []}}
            soort = "hond" if p["categoryId"] == 400 else "vogel"
            return {"_embedded": {"mp:search-result": [
                {"itemId": "m1", "title": "Labrador pups direct mee te nemen", "description": "Kunnen bezorgd worden", "priceModel": {"modelType": "fixed", "askingPrice": 45000},
                 "seller": {"sellerId": 7, "sellerName": "Puppyhuis"}, "_links": {"mp:advertisement-website-link": {"href": "https://www.marktplaats.nl/v/dieren/m1"}},
                 "_embedded": {"mp:advertisement-image": [{"mediaId": 5, "_links": {"mp:image-blob": {"href": "https://images.marktplaats.com/5.jpg"}}}]}},
                {"itemId": "m2" + soort, "title": "Jonge grasparkieten" if soort == "vogel" else "Beagle pup", "description": "", "priceModel": {"modelType": "bidding"},
                 "seller": {"sellerId": 7, "sellerName": "Puppyhuis"}}]}}
        if pad.startswith("/v1/advertisements/"):
            return {"location": {"cityName": "Apeldoorn", "postCode": "7311AA"}}
mpa.MarktplaatsAPI = lambda a, b: Nep()
os.environ.update(MP_CLIENT_ID="x", MP_CLIENT_SECRET="y")
cats = mpa.categorieen(Nep()); assert [c[0] for c in cats] == [400, 402], cats
mp = mpa.ophalen()
rassen.vul_rassen_aan(mp)
beoordeel_alles(mp)
for x in mp: print(x["id"], x["soort"], x["ras"], x["plaats"], x["prijs"], x["prijs_tekst"], x["fotos"], x["betrouwbaarheid"]["score"], x["broodfokker_verdacht"], x["broodfokker_signalen"])
assert mp[0]["prijs"] == 450 and mp[0]["plaats"] == "Apeldoorn" and mp[0]["ras"] == "Labrador" and mp[0]["broodfokker_verdacht"]
assert mp[2]["ras"] == "Grasparkiet" and mp[2]["soort"] == "vogel"
print("marktplaats + sitemap tests ok")

# ---- ikzoekbaas detail (nagebootst) ----
import ikzoekbaas
html = """<html><head><meta property="og:title" content="Balou"><meta property="og:image" content="https://cms.dierenbescherming.nl/assets/x/_330x285/DSC2981.jpg"></head><body>
<h1>Balou</h1><div>Dierenasiel 't schuthok<br>Rijksweg 4<br>1785 PA Den Helder</div>
<table><tr><td>Soort</td><td>Herdershonden (Mechels, Duits, etc.)</td></tr><tr><td>Geslacht</td><td>Vrouwelijk</td></tr>
<tr><td>Geboortedatum</td><td>30 mei 2018</td></tr><tr><td>Kan bij kinderen</td><td>Vanaf 12 jaar</td></tr><tr><td>Beschikbaarheid</td><td>{status}</td></tr></table>
<img src="https://cms.dierenbescherming.nl/assets/x/DSC2965-2.jpg"></body></html>"""
ikzoekbaas.haal = lambda url, timeout=25: BeautifulSoup(html.replace("{status}", "Gereserveerd"), "html.parser")
d = ikzoekbaas.detail({"id": "ikzb-1", "url": "u", "soort": "hond", "lastmod": "x"})
print(d)
assert d["naam"] == "Balou" and d["plaats"] == "Den Helder" and d["status"] == "gereserveerd" and "schuthok" in d["aanbieder"]["naam"] and len(d["fotos"]) == 2 and d["leeftijd"].endswith("jaar")
ikzoekbaas.haal = lambda url, timeout=25: BeautifulSoup(html.replace("{status}", "Geplaatst"), "html.parser")
assert ikzoekbaas.detail({"id": "ikzb-1", "url": "u", "soort": "hond", "lastmod": "x"}) is None
print("ikzoekbaas tests ok")

# ---- kenmerken ----
from kenmerken import extraheer
k = extraheer({"ras": "Europese korthaar", "naam": "Tijger", "kenmerken": {"Speciale zorg": "Nee"}},
              "Tijger is een cypers katertje met witte sokjes. Hij is FIV negatief en kerngezond, heeft geen medicatie nodig.")
print(k["kleuren"], k["vacht"], k["gezondheid"], k["medicatie"], k["gezondheid_info"])
assert "cypers" in k["kleuren"] and k["vacht"][0] == "kort" and k["gezondheid"] == "gezond" and k["medicatie"] is False
k = extraheer({"ras": "Maine Coon", "kenmerken": {"Kleur": "zwart-zilver"}}, "Lieve kat met diabetes, krijgt 2x per dag insuline. Lange vacht.")
print(k["kleuren"], k["vacht"], k["gezondheid"], k["medicatie"], k["gezondheid_info"])
assert k["kleuren"] == ["zwart", "zilver"] and "lang" in k["vacht"] and k["gezondheid"] == "aandacht" and k["medicatie"] and "diabetes" in k["gezondheid_info"]
k = extraheer({"ras": "Mix"}, "Getest op leishmania en ehrlichia: negatief. Blonde reu met ruwhaar vacht.")
print(k["kleuren"], k["vacht"], k["gezondheid"], k["medicatie"], k["gezondheid_info"])
assert "bloedparasieten" not in k["gezondheid_info"] and "crème/blond" in k["kleuren"] and "ruw/draadhaar" in k["vacht"]
k = extraheer({"ras": "Labrador", "beschrijving": "Pup"}, "")
assert k["gezondheid"] == "onbekend" and k["medicatie"] is None and k["vacht"] == ["kort"] and k["schema"] == 1
from common import lees_prijs
assert lees_prijs("€400-€575") == 400 and lees_prijs("100-275 euro") == 100
from ikzoekbaas import _uniek_grootste
f = _uniek_grootste(["https://c/a/_330x285_crop/X.png?s=1", "https://c/a/_800x550_crop/X.png?s=1", "https://c/a/_519x453_crop/Y.jpg"])
assert f == ["https://c/a/_800x550_crop/X.png?s=1", "https://c/a/_519x453_crop/Y.jpg"], f
print("kenmerken tests ok")
