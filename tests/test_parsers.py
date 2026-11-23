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
