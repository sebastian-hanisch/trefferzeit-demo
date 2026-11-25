"""Vorgerechnete Messwerte lesen (erzeugt von tools/vorrechnen.py; `tests/test_claims.py` rechnet sie nach)."""

import json
from pathlib import Path

PFAD = Path(__file__).resolve().parent / "daten" / "vorgerechnet.json"


def laden() -> dict:
    return json.loads(PFAD.read_text(encoding="utf-8"))


def deckung_fuer(daten: dict, netz: str, a: int, paar: str):
    """Eintrag der Deckungsgrad-Messung für Netz, Hallenseite und Paarwahl oder None (frei gewähltes Paar: nicht vorgerechnet)."""
    for z in daten["deckung"]:
        if z["netz"] == netz and z["paar"] == paar and (netz != "hallen" or z["a"] == a):
            return z
    return None
