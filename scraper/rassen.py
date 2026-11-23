"""Ras afleiden uit de titel als een bron geen rasveld heeft (zoals Marktplaats)."""
import re

BEKEND = {
    "hond": ["Labrador Retriever", "Labrador", "Golden Retriever", "Duitse Herder", "Mechelse Herder", "Hollandse Herder",
             "Australian Shepherd", "Border Collie", "Franse Bulldog", "Engelse Bulldog", "Bulldog", "Teckel", "Beagle",
             "Chihuahua", "Jack Russell", "Yorkshire Terrier", "Maltezer", "Shih Tzu", "Cavalier King Charles", "Pomeranian",
             "Dwergkees", "Keeshond", "Poedel", "Dwergpoedel", "Toypoedel", "Labradoodle", "Goldendoodle", "Cavapoo", "Maltipoo",
             "Husky", "Siberian Husky", "Rottweiler", "Dobermann", "Boxer", "Berner Sennen", "Sint Bernard", "Newfoundlander",
             "Cocker Spaniel", "Springer Spaniel", "Kooikerhondje", "Stabyhoun", "Drentsche Patrijs", "Friese Stabij",
             "Weimaraner", "Vizsla", "Dalmatiër", "Shiba Inu", "Akita", "Chow Chow", "Mopshond", "Mops", "Bichon Frisé",
             "Bordeaux Dog", "Cane Corso", "Amerikaanse Stafford", "Staffordshire Bull Terrier", "Bull Terrier",
             "Whippet", "Greyhound", "Galgo", "Podenco", "Lagotto Romagnolo", "Samojeed", "Havanezer", "Boomer", "Mix"],
    "kat": ["Maine Coon", "Britse Korthaar", "Brits Korthaar", "Britse Langhaar", "Ragdoll", "Perzische", "Pers", "Siamees",
            "Bengaal", "Bengal", "Noorse Boskat", "Siberische", "Sphynx", "Devon Rex", "Cornish Rex", "Abessijn", "Birmaan",
            "Heilige Birmaan", "Exotic", "Russisch Blauw", "Scottish Fold", "Savannah", "Europese Korthaar", "Huiskat"],
    "vogel": ["Grasparkiet", "Valkparkiet", "Agapornis", "Kanarie", "Zebravink", "Rosella", "Grijze Roodstaart",
              "Ara", "Kaketoe", "Halsbandparkiet", "Mandarijneend", "Kwartel", "Kriel", "Kip", "Duif", "Spitsstaartamadine"],
    "overig": ["Konijn", "Dwergkonijn", "Hangoor", "Cavia", "Hamster", "Rat", "Muis", "Chinchilla", "Degoe", "Fret",
               "Schildpad", "Gekko", "Baardagaam", "Slang", "Python", "Geit", "Schaap", "Varken", "Paard", "Pony", "Ezel"],
}


def vul_rassen_aan(dieren):
    lijsten = {s: sorted(set(l) | {d["ras"] for d in dieren if d.get("soort") == s and d.get("ras") and len(d["ras"]) > 2},
                         key=len, reverse=True) for s, l in BEKEND.items()}
    for d in dieren:
        if d.get("ras"):
            continue
        titel = f"{d.get('naam', '')} {d.get('beschrijving', '')[:120]}"
        for r in lijsten.get(d.get("soort"), []):
            if re.search(r"\b" + re.escape(r) + r"(en|s|'s|jes)?\b", titel, re.I):
                d["ras"] = r.title() if r.islower() else r
                break
