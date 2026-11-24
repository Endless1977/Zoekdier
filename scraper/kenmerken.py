"""Kleur, vacht en gezondheid afleiden uit de kenmerken en de tekst van een advertentie.

Eerst wordt gekeken naar velden zoals 'Kleur', 'Vacht' of 'Speciale zorg'. Daarna naar de volledige
beschrijving, met ontkenningen ('geen medicatie', 'leishmania negatief'). Het blijft heuristiek.
"""
import re

SCHEMA = 2  # verhogen als er nieuwe velden bijkomen: profielen worden dan opnieuw opgehaald

KLEUREN = [
    ("zwart", r"zwart\w*|black"),
    ("wit", r"wit(te)?|white"),
    ("bruin", r"bruin\w*|choco\w*|brown|lever\w*"),
    ("rood", r"rood|rode|rossig\w*|ginger|oranje\w*|red\b|rossige"),
    ("crème/blond", r"cr[eè]me\w*|cream|blond\w*|fawn|goud\w*|gold\w*|beige|zand\w*|apricot|abrikoos"),
    ("grijs/blauw", r"grijs|grijze|blauw\w*|blue|lilac|lila"),
    ("zilver", r"zilver\w*|silver"),
    ("cypers", r"cyper\w*|tabby|gestreept\w*|getijgerd"),
    ("lapjes/schildpad", r"lapjes\w*|schildpad\w*|calico|tortie|tortoiseshell"),
    ("driekleur", r"driekleur\w*|tricolou?r|tri-colou?r"),
    ("gestroomd", r"gestroomd\w*|brindle|gestroomde"),
    ("merle", r"merle|blue merle"),
    ("gevlekt", r"gevlekt\w*|spotted|bont\w*|gespikkeld\w*"),
    ("point", r"colou?r ?point|seal ?point|blue ?point|maskertje"),
]

VACHT = [
    ("kort", r"kort ?haar\w*|kortharig\w*|korte vacht|short ?hair|gladhaar\w*"),
    ("halflang", r"half ?lang ?haar\w*|halflanghaar\w*|semi ?langhaar\w*|halflange vacht"),
    ("lang", r"lang ?haar\w*|langharig\w*|lange vacht|long ?hair"),
    ("ruw/draadhaar", r"ruw ?haar\w*|draad ?haar\w*|wire ?hair\w*|ruwharig\w*"),
    ("krullend", r"krul\w*|curly|poedelvacht|wolvacht"),
    ("haarloos", r"haarloos|naakt\w*|sphynx|hairless"),
    ("weinig verharen", r"verhaart (bijna )?(niet|weinig)|hypoallerge\w*|niet[- ]verharend\w*"),
]

# ras -> vachttype als er niets over de vacht staat
RAS_VACHT = [
    (r"korthaar|labrador|beagle|boxer|dalmati|teckel korthaar|staff|pitbull|bulldog|mops|chihuahua korthaar|weimaraner|vizsla|dobermann|rottweiler|bengaal|siamees|sphynx", "kort"),
    (r"langhaar|maine ?coon|noorse boskat|ragdoll|pers(ische|ian)?\b|siberische|birmaan|golden retriever|collie|berner|sint bernard|newfoundlander|shih ?tzu|yorkshire|maltezer|chow", "lang"),
    (r"poedel|poodle|doodle|cavapoo|maltipoo|bichon|lagotto|boomer|devon rex|cornish rex|selkirk", "krullend"),
    (r"ruwhaar|draadhaar|schnauzer|jack russell ruw|border terrier|griffon", "ruw/draadhaar"),
]

AANDOENINGEN = [
    ("FIV", r"\bfiv\b|kattenaids"),
    ("FeLV", r"\bfelv\b|kattenleukemie"),
    ("diabetes", r"diabet\w*|suikerziek\w*|insuline"),
    ("epilepsie", r"epilep\w*|toevallen"),
    ("nieren", r"nier(probl\w*|falen|ziekte|insuffici\w*|dieet|waarden)|\bckd\b"),
    ("hart", r"hart(probl\w*|ruis|ziekte|falen|afwijking\w*)|\bhcm\b(?!.{0,15}(vrij|negatief|getest))"),
    ("gewrichten", r"artrose|heupdysplasie|elleboogdysplasie|\bhd\b(?!.{0,6}(vrij|a\b|-?a\b))|patella\w*|hernia"),
    ("schildklier", r"schildklier\w*|hyperthyre\w*|hypothyre\w*"),
    ("allergie/dieet", r"allergi\w*|dieetvoer\w*|speciaal (dieet|voer)|hypoallergeen voer|voedselintoleran\w*"),
    ("zicht/gehoor", r"\bblind\w*|\bdoof\b|\bdove\b|slechtziend\w*|slechthorend\w*"),
    ("handicap", r"drie poten|3 poten|driepoot|amputatie|verlam\w*|rolstoel\w*"),
    ("bloedparasieten", r"leishman\w*|ehrlich\w*|babesi\w*|anaplasm\w*|dirofilari\w*|hartworm"),
    ("luchtwegen", r"astma\w*|kattenniesziekte chronisch|chronische niesziekte|brachyce\w*|benauwd\w*"),
    ("darmen", r"\bibd\b|chronische darm\w*|darmprobl\w*"),
    ("chronisch", r"chronisch\w* (zie\w*|aandoening\w*|probl\w*)|levenslang (dieet|medicatie|medicijnen)"),
]
ONTKENNING_VOOR = r"(geen|niet|zonder|vrij van|negatief voor|getest op)\s+(\w+\s+){0,3}$"
ONTKENNING_NA = r"^\W{0,3}(\w+\W+){0,3}(negatief|vrij|uitgesloten|getest negatief|niet aanwezig|is niet)"

MEDICATIE = r"\b(medicatie|medicijn(en)?|pillen|tabletten|insuline|spuitjes|druppels)\b"
GEZOND = r"\b(kern)?gezond(e)?\b|geen (bekende )?(medische|gezondheids)\s?(problemen|klachten|aandoeningen)|medisch (in orde|gezond)"


def _zoek(patroon, tekst):
    return [m for m in re.finditer(patroon, tekst, re.I)]


def _ontkend(tekst, m):
    voor = tekst[max(0, m.start() - 40):m.start()]
    na = tekst[m.end():m.end() + 35]
    return bool(re.search(ONTKENNING_VOOR, voor, re.I) or re.search(ONTKENNING_NA, na, re.I))


def _veld(kenmerken, *woorden):
    for k, v in (kenmerken or {}).items():
        if any(w in k.lower() for w in woorden):
            yield k, v


def extraheer(dier, tekst=""):
    """Zet dier['kleuren'], dier['vacht'], dier['gezondheid'], dier['medicatie'], dier['gezondheid_info']."""
    km = dier.get("kenmerken") or {}
    basis = " ".join(str(dier.get(k) or "") for k in ("naam", "ras", "beschrijving"))
    alles = f"{basis} {tekst}"

    # ---- kleur ----
    kleurveld = " ".join(v for _, v in _veld(km, "kleur", "color", "colour", "tekening"))
    bron = kleurveld or f"{dier.get('ras') or ''} {dier.get('naam') or ''} {tekst or dier.get('beschrijving') or ''}"
    kleuren = [k for k, pat in KLEUREN if re.search(r"\b(" + pat + r")", bron, re.I)]
    # 'zwart-wit' en 'wit' in 'witte sokjes': pas als er weinig kleurinformatie is
    dier["kleuren"] = kleuren[:4]

    # ---- vacht ----
    vachtveld = " ".join(v for _, v in _veld(km, "vacht", "haar", "coat"))
    vbron = f"{vachtveld} {dier.get('ras') or ''} {tekst or dier.get('beschrijving') or ''}"
    vacht = [k for k, pat in VACHT if re.search(r"\b(" + pat + r")", vbron, re.I)]
    if not any(v in vacht for v in ("kort", "halflang", "lang", "ruw/draadhaar", "krullend", "haarloos")):
        for pat, v in RAS_VACHT:
            if re.search(pat, dier.get("ras") or "", re.I):
                vacht.insert(0, v)
                break
    if "halflang" in vacht and "lang" in vacht:
        vacht.remove("lang")
    dier["vacht"] = vacht

    # ---- gezondheid ----
    info = []
    for naam, pat in AANDOENINGEN:
        if any(not _ontkend(alles, m) for m in _zoek(pat, alles)):
            info.append(naam)
    medicatie = None
    meds = _zoek(MEDICATIE, alles)
    if meds:
        medicatie = any(not _ontkend(alles, m) for m in meds)
    zorg = [v.lower() for _, v in _veld(km, "speciale zorg", "medisch", "gezondheid", "medicatie", "medicijn")]
    if any(re.match(r"^(ja|yes)\b", z) or len(z) > 12 and not re.match(r"^(nee|geen|goed|gezond)", z) for z in zorg):
        info.append("speciale zorg")
    if any(re.search(r"medicatie|medicijn", k.lower()) and re.match(r"^(ja|yes)", v.lower()) for k, v in km.items()):
        medicatie = True
    if any(re.search(r"medicatie|medicijn", k.lower()) and re.match(r"^(nee|geen|no)", v.lower()) for k, v in km.items()):
        medicatie = False if medicatie is None else medicatie
    if medicatie and "medicatie" not in info:
        info.append("medicatie")

    gezond_genoemd = bool(re.search(GEZOND, alles, re.I)) or any(re.match(r"^(nee|geen)\b", z) for z in zorg)
    if info:
        gezondheid = "aandacht"
    elif gezond_genoemd:
        gezondheid = "gezond"
    else:
        gezondheid = "onbekend"
    if medicatie is None and gezondheid == "gezond":
        medicatie = False
    dier["gezondheid"] = gezondheid
    dier["gezondheid_info"] = info
    dier["medicatie"] = medicatie
    dier["schema"] = SCHEMA if tekst else dier.get("schema", 1)
    return dier
