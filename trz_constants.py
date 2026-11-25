"""Konstanten: Regler-Grenzen, feste Annahmen, Namen und Presets."""

NETZ_HAND, NETZ_HALLEN, NETZ_SAAL = "hand", "hallen", "saal"
NETZE = (NETZ_HAND, NETZ_HALLEN, NETZ_SAAL)
NETZ_TEXT = {NETZ_HAND: "Handnetz zwei Hallen (6 Knoten)", NETZ_HALLEN: "Zwei Gitterhallen a×a, eine Tür", NETZ_SAAL: "Saal mit Stichgang 21 + 11 (Kontrast)"}

A_MIN, A_MAX, DEFAULT_A = 3, 10, 8            # n = 2a² ≤ 200 Knoten; je Netz eine n×n-Inversion (≤ 200³ = 8·10⁶ Operationen), CV: n Gleichungssysteme
SAAL, GANG = 21, 11

KANTE_TUER, KANTE_FREI = "tuer", "frei"
KANTEN_ARTEN = (KANTE_TUER, KANTE_FREI)
KANTE_TEXT = {KANTE_TUER: "zweite Tür", KANTE_FREI: "frei gewählte Kante"}

PAAR_CV, PAAR_TUER, PAAR_GEWAEHLT = "cv", "tuer", "gewaehlt"
PAARE = (PAAR_CV, PAAR_TUER, PAAR_GEWAEHLT)
PAAR_TEXT = {PAAR_CV: "größte Streuung (CV)", PAAR_TUER: "Türschritt", PAAR_GEWAEHLT: "gewählt (Start → Ziel)"}

LAEUFE_MIN, LAEUFE_MAX, LAEUFE_STEP, DEFAULT_LAEUFE = 50, 5000, 50, 1000
SCHRITT_DECKEL = 10_000_000                   # erwartete Gesamtschritte R·H einer Simulation; darüber wird R gekürzt (mit Hinweis)
ABBRUCH_OHNE = "ohne"
ABBRUCH_STUFEN = ("1", "2", "3", "5", "10", ABBRUCH_OHNE)

SEED_MAX, DEFAULT_SEED = 999999, 5821

WEG_MIN, WEG_MAX, DEFAULT_WEG = 4, 30, 8

# Vorrechnung (tools/vorrechnen.py -> daten/vorgerechnet.json); eigene Zufalls-Seeds, getrennt vom Regler und von den Presets
DECKUNG_WIEDERHOLUNGEN = 4000
DECKUNG_SEED = 730_100
STREUUNG_LAEUFE = (100, 500, 5000)
STREUUNG_SEED = 730_900
ABSTAENDE = (1, 4, 8, 10, 12, 14, 15)
ABSTAND_A, ABSTAND_C = 8, 3


def knoten_standard(netz: str, a: int) -> dict:
    """Standardwerte für Start, Ziel und die Endpunkte der frei gewählten Kante je Netz."""
    if netz == NETZ_HAND:
        return {"u": 0, "v": 2, "ka": 0, "kb": 4}
    if netz == NETZ_HALLEN:
        # Start: Ecke unter der Tür L(a−1, a−1); Ziel: Türknoten L(a//2, a−1); freie Kante: die beiden fernen Ecken oben
        return {"u": a * a - 1, "v": (a // 2) * a + a - 1, "ka": 0, "kb": a * a + a - 1}
    return {"u": SAAL + GANG - 2, "v": SAAL + GANG - 1, "ka": 0, "kb": SAAL + GANG - 1}


def anzahl_knoten(netz: str, a: int) -> int:
    return {NETZ_HAND: 6, NETZ_HALLEN: 2 * a * a, NETZ_SAAL: SAAL + GANG}[netz]


def _preset(netz, u, v, kante=KANTE_TUER, r=0, paar=PAAR_CV, abbruch="3", laeufe=DEFAULT_LAEUFE, a=DEFAULT_A):
    std = knoten_standard(netz, a)
    return {"netz": netz, "a": a, "u": u, "v": v, "kante": kante, "r": r, "ka": std["ka"], "kb": std["kb"], "paar": paar, "laeufe": laeufe, "abbruch": abbruch,
            "seed": DEFAULT_SEED}


PRESETS = {
    "Handnetz zwei Hallen": _preset(NETZ_HAND, 0, 2),
    "Zwei Hallen, eine Tür": _preset(NETZ_HALLEN, 63, 39, paar=PAAR_TUER),
    "Eine Tür mehr": _preset(NETZ_HALLEN, 7, 64),                    # Start und Ziel sind die Endpunkte der neuen Tür in Zeile 0
    "Probeläufe mit Abbruch": _preset(NETZ_HALLEN, 8, 9, laeufe=5000),
    "Saal mit Stichgang 21 + 11 (Kontrast)": _preset(NETZ_SAAL, 30, 31, kante=KANTE_FREI),
}
PRESET_HELP = {
    "Handnetz zwei Hallen": "Sechs Plätze, eine Tür: von 0 nach 2 sind es im Mittel 2 Schritte, zurück 22/3. Alles lässt sich von Hand nachrechnen.",
    "Zwei Hallen, eine Tür": "Zwei Gitter 8×8: Start in der Ecke unter der Tür, Ziel der Türknoten derselben Halle. Der Rückweg ist rund fünfmal so lang.",
    "Eine Tür mehr": "Eine zweite Tür in Zeile 0, die vorhandene bleibt. Start und Ziel sind ihre beiden Endpunkte.",
    "Probeläufe mit Abbruch": "Das Paar mit der größten Streuung auf zwei Hallen 8×8, 5 000 Probeläufe mit Abbruch nach dem Dreifachen der mittleren Schrittzahl.",
    "Saal mit Stichgang 21 + 11 (Kontrast)": "Vollständiger Saal mit 21 Plätzen, daran ein Gang mit 11 Plätzen: hier ist die Richtung viel wichtiger als auf den Hallen.",
}
