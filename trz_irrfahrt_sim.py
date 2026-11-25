"""Simulation der einfachen Irrfahrt, vektorisiert, mit SplitMix64 (ohne Streamlit, nur numpy).

Gemeinsamer Baustein der Reihe „Irrfahrten auf Netzen“: zum Kopieren in spätere Demos. Braucht `trz_netze`.

Der Generator liefert exakt dieselbe Folge wie die Klasse `SplitMix64` in `trz_rng.py` (Test: `tests/test_irrfahrt_sim.py`): der k-te Wert ist die Mischung von
Zufalls-Seed + k·γ, also lassen sich ganze Blöcke auf einmal rechnen. Gezogen wird nur ganzzahlig (u64 mod Grad), die Läufe sind damit plattformgleich.

Reihenfolge der Ziehungen: in jedem Schritt bekommt jeder noch laufende Läufer genau einen Wert, in aufsteigender Läufernummer. Der Nachbar ist der Eintrag
Nummer (u64 mod Grad) der aufsteigend sortierten Nachbarliste.
"""

import numpy as np

import trz_netze as N

GAMMA = np.uint64(0x9E3779B97F4A7C15)
_M1 = np.uint64(0xBF58476D1CE4E5B9)
_M2 = np.uint64(0x94D049BB133111EB)
MASK = (1 << 64) - 1


class BlockZufall:
    """SplitMix64 blockweise: `u64(m)` sind die nächsten m Werte der Folge."""

    def __init__(self, seed: int):
        self.seed = int(seed) & MASK
        self.gezogen = 0

    def u64(self, m: int) -> np.ndarray:
        nummer = np.arange(self.gezogen + 1, self.gezogen + m + 1, dtype=np.uint64)
        self.gezogen += m
        z = nummer * GAMMA + np.full(m, self.seed, dtype=np.uint64)      # uint64-Felder rechnen modulo 2^64
        z = (z ^ (z >> np.uint64(30))) * _M1
        z = (z ^ (z >> np.uint64(27))) * _M2
        return z ^ (z >> np.uint64(31))

    def random(self, m: int) -> np.ndarray:
        """Gleichverteilt in [0, 1) mit 53 Bit."""
        return (self.u64(m) >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def nachbar_tabelle(g: N.Netz):
    """(Tabelle n × Höchstgrad der sortierten Nachbarn, Grade als uint64)."""
    nb = N.nachbarn(g)
    grad = np.array([len(x) for x in nb], dtype=np.uint64)
    tabelle = np.zeros((g.n, max(1, int(grad.max(initial=0)))), dtype=np.int64)
    for u, liste in enumerate(nb):
        tabelle[u, : len(liste)] = liste
    return tabelle, grad


def simuliere_trefferzeiten(g: N.Netz, u: int, v: int, laeufe: int, seed: int, max_schritte: int = 10_000_000) -> np.ndarray:
    """Schrittzahl je Lauf von u bis zum ersten Besuch von v (u = v gibt 0). Läufe, die nach `max_schritte` Schritten je Lauf nicht fertig sind, bekommen −1."""
    if not N.ist_zusammenhaengend(g):
        raise ValueError("Simulation nur auf zusammenhängenden Netzen")
    tabelle, grad = nachbar_tabelle(g)
    zeiten = np.zeros(laeufe, dtype=np.int64)
    if u == v or laeufe == 0:
        return zeiten
    rng = BlockZufall(seed)
    ort = np.full(laeufe, u, dtype=np.int64)
    aktiv = np.arange(laeufe)
    schritt = 0
    while aktiv.size and schritt < max_schritte:
        schritt += 1
        hier = ort[aktiv]
        wahl = (rng.u64(aktiv.size) % grad[hier]).astype(np.int64)
        dort = tabelle[hier, wahl]
        ort[aktiv] = dort
        angekommen = dort == v
        if angekommen.any():
            zeiten[aktiv[angekommen]] = schritt
            aktiv = aktiv[~angekommen]
    zeiten[aktiv] = -1
    return zeiten
