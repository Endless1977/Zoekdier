"""Betrouwbaarheid en broodfokker-signalen voor Zoekdier.

Alles is heuristiek op basis van wat er in een advertentie staat. Een score is
een indicatie, geen oordeel: controleer altijd zelf (bezoek, papieren, ouderdieren).
"""
import re
from collections import defaultdict

# Aanbiedertype -> startscore
BASIS = {
    "asiel": 75,          # erkend asiel / dierenopvang
    "herplaatsing": 65,   # particuliere herplaatsing via stichting (bv. Verhuisdieren)
    "kennel": 55,         # hondenfokker met kennelnaam
    "cattery": 55,        # kattenfokker met catterynaam
    "kwekerij": 50,       # vogelkweker
    "particulier": 45,
    "handelaar": 30,
    "onbekend": 40,
}

# (regex, punten, uitleg)  — positief
PLUS = [
    (r"\b(stamboom|nhsb|raad van beheer|fci)\b", 15, "Stamboom / Raad van Beheer genoemd"),
    (r"\b(fife|felikat|tica|wcf|cfa|stamboomkat)\b", 15, "Kattenstamboom (FIFe/Felikat/TICA) genoemd"),
    (r"\brasvereniging\b|\bverenigingsfokreglement\b", 10, "Lid van rasvereniging"),
    (r"\bubn\b", 10, "UBN-nummer genoemd (wettelijk verplicht voor fokkers)"),
    (r"\b(gechipt|chipnummer|528\d{6,})\b", 5, "Chip genoemd"),
    (r"\b(eu-?)?(dieren)?paspoort\b", 5, "EU-paspoort genoemd"),
    (r"\b(hd|ed)[- ]?(vrij|a|b|uitslag)\b|\bdna[- ]?(test|getest|vrij)\b|\b(pkd|hcm)[- ]?(vrij|getest|negatief)\b|\bgezondheidsonderzoek", 10, "Gezondheidsonderzoeken ouderdieren genoemd"),
    (r"\b(moeder|ouderdieren|beide ouders)\b.{0,40}\b(aanwezig|te zien|bekijken|kennismaken)", 5, "Ouderdieren te zien"),
    (r"\b(gevaccineerd|ingeënt|geent|ontwormd|dierenarts gecontroleerd)\b", 5, "Vaccinatie / ontworming / dierenartscheck"),
    (r"\b(correct |gesloten )?geringd\b|\bnbvv\b|\bkweekring", 5, "Vogel geringd (NBvV/kweekring)"),
    (r"\b(gecastreerd|gesteriliseerd)\b", 3, "Gecastreerd/gesteriliseerd"),
    (r"\b(kennismaking|huisbezoek|adoptiecontract|plaatsingsovereenkomst)\b", 5, "Kennismaking / contract"),
]

# Broodfokker-signalen: (regex, punten, uitleg). Punten gaan van de score af.
SIGNALEN = [
    (r"\b(direct|meteen|vandaag) (mee ?te nemen|meenemen|ophalen)\b", 15, "‘Direct meenemen’"),
    (r"\b(bezorg(en|d)|thuisbezorg|afleveren|wij brengen|kunnen gebracht)\b", 15, "Bezorging aan huis aangeboden"),
    (r"\b(parkeerplaats|tankstation|afspreken halverwege)\b", 20, "Overdracht op neutrale plek"),
    (r"\b(meerdere|diverse|verschillende) (rassen|nestjes|nesten)\b", 20, "Meerdere rassen/nesten tegelijk"),
    (r"\b(import|uit (hongarije|slowakije|roemenie|roemenië|polen|bulgarije|servië|tsjechie|tsjechië))\b", 10, "Importpup/kitten"),
    (r"\b(geen stamboom|zonder stamboom|stamboom niet nodig)\b", 5, "Bewust zonder stamboom"),
    (r"\b(doodle|labradoodle|goldendoodle|maltipoo|cavapoo|pomsky|teacup|mini ?toy|micro)\b", 5, "Modieuze kruising / ‘teacup’"),
    (r"\b(scottish ?fold|vouwoor|vouworen)\b", 40, "Vouwoorkat: in NL verboden te houden sinds 2026"),
    (r"\b(geen papieren|zonder papieren|papieren volgen)\b", 15, "Geen/later papieren"),
    (r"\b(aanbetaling|vooruitbetal|reserveringsgeld)\b.{0,30}\b(overmaken|tikkie|vooraf)\b", 10, "Vooruitbetaling zonder bezoek"),
    (r"\b(fokkerij|kennel|cattery)\b.{0,40}\b(\d{2,}) (pups|kittens) per jaar\b", 15, "Veel nesten per jaar"),
]

# Minimale verkoopleeftijd in weken
MIN_WEKEN = {"hond": 7, "kat": 12}

BROODFOKKER_DREMPEL = 25  # som signaalpunten waarboven 'verdacht'


def _weken(leeftijd_tekst):
    if not leeftijd_tekst:
        return None
    t = leeftijd_tekst.lower()
    m = re.search(r"(\d+)\s*(week|weken|wk)", t)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*(maand|maanden|mnd)", t)
    if m:
        return int(m.group(1)) * 4.3
    m = re.search(r"(\d+)\s*(jaar|jr)", t)
    if m:
        return int(m.group(1)) * 52
    return None


def beoordeel(dier, verkoper_stats=None):
    """Voegt dier['betrouwbaarheid'], dier['broodfokker_verdacht'] en signalen toe."""
    tekst = " ".join(str(dier.get(k) or "") for k in ("naam", "ras", "beschrijving", "prijs_tekst", "leeftijd"))
    tekst += " " + (dier.get("aanbieder", {}).get("naam") or "")
    tekst = tekst.lower()
    soort = dier.get("soort")
    atype = dier.get("aanbieder", {}).get("type", "onbekend")

    score = BASIS.get(atype, 40)
    redenen = [{"tekst": f"Basis voor aanbieder: {atype}", "punten": score}]

    for pat, pnt, uitleg in PLUS:
        if re.search(pat, tekst):
            score += pnt
            redenen.append({"tekst": uitleg, "punten": pnt})

    signalen = []
    sig_punten = 0
    for pat, pnt, uitleg in SIGNALEN:
        # import/buitenland is bij asiel en herplaatsing normaal (zwerfdieren)
        if "Import" in uitleg and atype in ("asiel", "herplaatsing"):
            continue
        if re.search(pat, tekst):
            signalen.append(uitleg)
            sig_punten += pnt

    # te jong
    w = _weken(dier.get("leeftijd"))
    if w is not None and soort in MIN_WEKEN and w < MIN_WEKEN[soort] and atype not in ("asiel", "herplaatsing"):
        signalen.append(f"Aangeboden jonger dan {MIN_WEKEN[soort]} weken")
        sig_punten += 30

    # verkoper die veel verschillende rassen / advertenties heeft
    if verkoper_stats:
        if verkoper_stats.get("rassen", 0) >= 3:
            signalen.append(f"Zelfde aanbieder biedt {verkoper_stats['rassen']} verschillende rassen aan")
            sig_punten += 25
        if verkoper_stats.get("advertenties", 0) >= 6:
            signalen.append(f"Zelfde aanbieder heeft {verkoper_stats['advertenties']} advertenties")
            sig_punten += 10

    if not dier.get("fotos"):
        score -= 10
        redenen.append({"tekst": "Geen foto's", "punten": -10})

    if dier.get("prijs_laag"):
        signalen.append("Prijs ver onder het gemiddelde voor dit ras")
        sig_punten += 10

    if sig_punten:
        score -= sig_punten
        redenen.append({"tekst": "Broodfokker-/handelsignalen", "punten": -sig_punten})

    score = max(0, min(100, score))
    dier["betrouwbaarheid"] = {"score": score, "redenen": redenen}
    dier["broodfokker_signalen"] = signalen
    dier["broodfokker_verdacht"] = sig_punten >= BROODFOKKER_DREMPEL or atype == "handelaar"
    return dier


def _verkoper_sleutel(d):
    a = d.get("aanbieder") or {}
    if a.get("id"):
        return f"{d.get('bron')}:{a['id']}"
    return (a.get("naam") or "").strip().lower() or None


def beoordeel_alles(dieren):
    """Twee rondes: eerst statistiek per aanbieder en prijs per ras, dan scoren."""
    per_verkoper = defaultdict(lambda: {"rassen": set(), "advertenties": 0})
    prijzen = defaultdict(list)
    for d in dieren:
        naam = _verkoper_sleutel(d)
        if naam and d["aanbieder"].get("type") not in ("asiel", "herplaatsing"):
            v = per_verkoper[naam]
            v["advertenties"] += 1
            if d.get("ras"):
                v["rassen"].add(d["ras"].lower())
        if d.get("prijs") and d.get("ras") and d["aanbieder"].get("type") not in ("asiel", "herplaatsing"):
            prijzen[(d["soort"], d["ras"].lower())].append(d["prijs"])

    for d in dieren:
        key = (d.get("soort"), (d.get("ras") or "").lower())
        lijst = sorted(prijzen.get(key, []))
        if len(lijst) >= 4 and d.get("prijs"):
            mediaan = lijst[len(lijst) // 2]
            d["prijs_laag"] = d["prijs"] < 0.4 * mediaan
        naam = _verkoper_sleutel(d)
        stats = None
        if naam in per_verkoper:
            v = per_verkoper[naam]
            stats = {"rassen": len(v["rassen"]), "advertenties": v["advertenties"]}
        beoordeel(d, stats)
        d.pop("prijs_laag", None)
    return dieren


def classificeer_aanbieder(tekst, standaard="particulier", soort=None):
    t = (tekst or "").lower()
    if re.search(r"\b(dierenasiel|asiel|dierenopvang|dierentehuis|dierencentrum|dierenbescherming|opvangcentrum)\b", t):
        return "asiel"
    if re.search(r"\b(dierenspeciaalzaak|dierenwinkel|handelaar|groothandel|inkoop|wij kopen)\b", t):
        return "handelaar"
    if re.search(r"\b(cattery|katterie|kattery)\b", t) or (soort == "kat" and re.search(r"\b(fife|felikat)\b", t)):
        return "cattery"
    if re.search(r"\b(kennel|fokkerij|van huize|nhsb)\b", t) and soort in (None, "hond"):
        return "kennel"
    if soort == "vogel" and re.search(r"\b(kwekerij|kweker|eigen kweek|vogelpark|nbvv)\b", t):
        return "kwekerij"
    return standaard
