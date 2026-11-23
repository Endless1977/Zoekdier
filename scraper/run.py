"""Zoekdier scraper: haalt alle bronnen op en schrijft data/dieren.json.

Gebruik:  python scraper/run.py
Omgeving: ZOEKDIER_MAX_DETAIL (standaard 350 nieuwe Verhuisdieren-detailpagina's per run)
          ZOEKDIER_MAX_PAGINAS (standaard 120 overzichtspagina's Verhuisdieren)
          ZOEKDIER_DELAY (seconden tussen verzoeken, standaard 1.2)
"""
import datetime as dt
import json
import os
import sys
import traceback

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HIER, os.path.join(HIER, "adapters")]

import generiek  # noqa: E402
import verhuisdieren  # noqa: E402
from common import bewaar_geocache, geocodeer  # noqa: E402
from scoring import beoordeel_alles  # noqa: E402

DATA = os.path.join(HIER, "..", "data")
UIT = os.path.join(DATA, "dieren.json")
STATUS = os.path.join(DATA, "bronstatus.json")
MAX_DETAIL = int(os.environ.get("ZOEKDIER_MAX_DETAIL", "350"))
MAX_PAGINAS = int(os.environ.get("ZOEKDIER_MAX_PAGINAS", "120"))


def laad_vorige():
    try:
        with open(UIT, encoding="utf-8") as f:
            return {d["id"]: d for d in json.load(f).get("dieren", [])}
    except (OSError, ValueError):
        return {}


def run_verhuisdieren(vorige, status):
    uit, nieuw_opgehaald = [], 0
    for basis in verhuisdieren.lijst(MAX_PAGINAS):
        oud = vorige.get(basis["id"])
        if oud and not oud.get("detail_nodig"):
            oud.update({"status": basis["status"], "naam": basis["naam"]})
            uit.append(oud)
            continue
        if nieuw_opgehaald >= MAX_DETAIL:
            # nog niet in detail opgehaald: toon wat we van de kaart weten, volgende run aanvullen
            foto = basis.pop("foto", None)
            uit.append({**basis, "fotos": [foto] if foto else [], "detail_nodig": True,
                        "aanbieder": {"naam": "Particulier via Verhuisdieren", "type": "herplaatsing"},
                        "bron": verhuisdieren.NAAM})
            continue
        d = verhuisdieren.detail(basis)
        nieuw_opgehaald += 1
        if d:
            d.pop("foto", None)
            uit.append(d)
    status.append({"bron": verhuisdieren.NAAM, "aantal": len(uit), "nieuw_detail": nieuw_opgehaald, "ok": len(uit) > 0})
    return uit


def run_generiek(status):
    with open(os.path.join(HIER, "bronnen.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    uit = []
    for bron in cfg["bronnen"]:
        if not bron.get("actief"):
            continue
        try:
            urls = generiek.links(bron)
            gevonden = [d for d in (generiek.detail(bron, u) for u in urls) if d]
            uit += gevonden
            status.append({"bron": bron["naam"], "aantal": len(gevonden), "links": len(urls), "ok": len(gevonden) > 0})
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            status.append({"bron": bron["naam"], "aantal": 0, "ok": False, "fout": str(e)[:200]})
    return uit


def main():
    vorige = laad_vorige()
    status = []
    dieren = []
    try:
        dieren += run_verhuisdieren(vorige, status)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        status.append({"bron": verhuisdieren.NAAM, "aantal": 0, "ok": False, "fout": str(e)[:200]})
        # bij een fout de vorige gegevens van deze bron behouden
        dieren += [d for d in vorige.values() if d.get("bron") == verhuisdieren.NAAM]
    dieren += run_generiek(status)

    for d in dieren:
        if d.get("plaats") and not d.get("coord"):
            d["coord"] = geocodeer(d["plaats"])
    bewaar_geocache()
    beoordeel_alles(dieren)

    nu = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    aantallen = {}
    for d in dieren:
        aantallen[d["soort"]] = aantallen.get(d["soort"], 0) + 1
    os.makedirs(DATA, exist_ok=True)
    with open(UIT, "w", encoding="utf-8") as f:
        json.dump({"gegenereerd": nu, "aantallen": aantallen, "dieren": dieren}, f, ensure_ascii=False, separators=(",", ":"))
    with open(STATUS, "w", encoding="utf-8") as f:
        json.dump({"gegenereerd": nu, "bronnen": status}, f, ensure_ascii=False, indent=1)
    print(f"Klaar: {len(dieren)} dieren {aantallen}")
    for s in status:
        print("  ", s)


if __name__ == "__main__":
    main()
