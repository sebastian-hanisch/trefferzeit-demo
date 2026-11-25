"""Netze: einfach, ungerichtet, mit Knotennamen und Koordinaten für die Karte (ohne Streamlit, nur numpy).

Gemeinsamer Baustein der Reihe „Irrfahrten auf Netzen“: zum Kopieren in spätere Demos (kopieren, nicht importieren).

Netze:
* Handnetz „zwei Hallen“: Dreiecke {0, 1, 2} und {3, 4, 5}, eine Tür 2–3, auf Wunsch eine zweite Tür 5–0.
* Gitterhallen: zwei Gitter a×a (Vierernachbarschaft) nebeneinander; eine Tür verbindet die rechte Spalte der linken Halle mit der linken Spalte der rechten in
  derselben Zeile. Zwei Türregeln, nie vermischen:
  - **Ergänzung** (`eine_tuer_mehr`): die vorhandene Tür in Zeile a // 2 bleibt, eine neue kommt in eine wählbare Zeile r.
  - **Netzfamilie** (`k_tueren`): k gleichmäßig verteilte Türen in den Zeilen floor((i + 0,5)·a / k), i = 0 … k−1. Für k = 1 ist das Zeile a // 2; für k ≥ 2
    enthält die Familie die mittlere Tür nicht zwingend, sie ist also keine Ergänzung.
* Kontrastnetze: Saal mit Stichgang (vollständiger Saal, daran ein Gang), einzelnes Gitter, Weg, Weg mit Schlussstein.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Netz:
    name: str
    n: int
    kanten: tuple          # sortierte Paare (u, v) mit u < v
    knoten: tuple          # Name je Knoten
    pos: tuple             # (x, y) je Knoten, nur für die Karte


def netz(name: str, n: int, kanten, knoten=None, pos=None) -> Netz:
    """Netz aus einer Kantenliste; Schleifen, Doppelkanten und Knoten außerhalb 0 … n−1 werden abgewiesen."""
    paare = []
    for u, v in kanten:
        if u == v or not (0 <= u < n and 0 <= v < n):
            raise ValueError(f"ungültige Kante ({u}, {v}) bei {n} Knoten")
        paare.append((min(u, v), max(u, v)))
    if len(set(paare)) != len(paare):
        raise ValueError("doppelte Kante")
    knoten = tuple(str(i) for i in range(n)) if knoten is None else tuple(knoten)
    if pos is None:
        winkel = 2 * np.pi * np.arange(n) / max(n, 1)
        pos = tuple((float(np.cos(w)), float(np.sin(w))) for w in winkel)
    return Netz(name, n, tuple(sorted(paare)), knoten, tuple(pos))


def adjazenz(g: Netz) -> np.ndarray:
    A = np.zeros((g.n, g.n))
    if g.kanten:
        k = np.array(g.kanten)
        A[k[:, 0], k[:, 1]] = 1.0
        A[k[:, 1], k[:, 0]] = 1.0
    return A


def grade(g: Netz) -> np.ndarray:
    d = np.zeros(g.n, dtype=np.int64)
    for u, v in g.kanten:
        d[u] += 1
        d[v] += 1
    return d


def nachbarn(g: Netz) -> list:
    """Sortierte Nachbarlisten (die Reihenfolge legt fest, welche Ziehung welchen Schritt bedeutet)."""
    nb = [[] for _ in range(g.n)]
    for u, v in g.kanten:
        nb[u].append(v)
        nb[v].append(u)
    return [sorted(x) for x in nb]


def ist_zusammenhaengend(g: Netz) -> bool:
    if g.n == 0:
        return False
    nb = nachbarn(g)
    gesehen, stapel = {0}, [0]
    while stapel:
        u = stapel.pop()
        for w in nb[u]:
            if w not in gesehen:
                gesehen.add(w)
                stapel.append(w)
    return len(gesehen) == g.n


def hat_kante(g: Netz, u: int, v: int) -> bool:
    return (min(u, v), max(u, v)) in g.kanten


def mit_kante(g: Netz, u: int, v: int) -> Netz:
    """Dasselbe Netz mit der neuen Kante u–v (nur zwischen zwei verschiedenen, noch nicht verbundenen Knoten)."""
    if u == v or hat_kante(g, u, v):
        raise ValueError("neue Kante nur zwischen zwei verschiedenen, bisher nicht verbundenen Knoten")
    return netz(g.name, g.n, list(g.kanten) + [(u, v)], g.knoten, g.pos)


def fehlende_kanten(g: Netz) -> list:
    vorhanden = set(g.kanten)
    return [(u, v) for u in range(g.n) for v in range(u + 1, g.n) if (u, v) not in vorhanden]


# ----------------------------------------------------------------------------------------------------------------------------------
# Handnetz „zwei Hallen“
# ----------------------------------------------------------------------------------------------------------------------------------

HANDNETZ_POS = ((0.0, 1.4), (0.0, 0.0), (1.2, 0.7), (2.8, 0.7), (4.0, 0.0), (4.0, 1.4))


def handnetz(tueren: int = 1) -> Netz:
    """Dreiecke {0,1,2} und {3,4,5}; Tür 2–3, bei zwei Türen zusätzlich 5–0."""
    if tueren not in (1, 2):
        raise ValueError("Handnetz mit einer oder zwei Türen")
    kanten = [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5), (2, 3)]
    if tueren == 2:
        kanten.append((0, 5))
    return netz("Handnetz zwei Hallen", 6, kanten, pos=HANDNETZ_POS)


# ----------------------------------------------------------------------------------------------------------------------------------
# Gitterhallen
# ----------------------------------------------------------------------------------------------------------------------------------

def hallenknoten(a: int, halle: int, zeile: int, spalte: int) -> int:
    """Knotennummer in den Gitterhallen: erst die linke Halle zeilenweise, dann die rechte."""
    if not (halle in (0, 1) and 0 <= zeile < a and 0 <= spalte < a):
        raise ValueError("Platz außerhalb der Halle")
    return halle * a * a + zeile * a + spalte


def tuerzeilen(a: int, k: int) -> list:
    """Zeilen der k gleichmäßig verteilten Türen: floor((i + 0,5)·a / k), in ganzen Zahlen gerechnet."""
    if not 1 <= k <= a:
        raise ValueError("1 bis a Türen")
    return [((2 * i + 1) * a) // (2 * k) for i in range(k)]


def gitterhallen(a: int, zeilen) -> Netz:
    """Zwei Gitter a×a, je eine Tür in jeder Zeile aus `zeilen`."""
    if a < 2:
        raise ValueError("a mindestens 2")
    zeilen = list(zeilen)
    if len(set(zeilen)) != len(zeilen) or not zeilen:
        raise ValueError("mindestens eine Tür, jede Zeile höchstens einmal")
    kanten, namen, pos = [], [], []
    for h, buchstabe in enumerate("LR"):
        for z in range(a):
            for s in range(a):
                u = hallenknoten(a, h, z, s)
                if z + 1 < a:
                    kanten.append((u, hallenknoten(a, h, z + 1, s)))
                if s + 1 < a:
                    kanten.append((u, hallenknoten(a, h, z, s + 1)))
                namen.append(f"{buchstabe}({z},{s})")
                pos.append((float(s + h * (a + 1)), float(a - 1 - z)))
    kanten += [(hallenknoten(a, 0, z, a - 1), hallenknoten(a, 1, z, 0)) for z in zeilen]
    return netz(f"Zwei Hallen {a}×{a}", 2 * a * a, kanten, namen, pos)


def zwei_hallen(a: int) -> Netz:
    """Zwei Hallen mit einer Tür in Zeile a // 2."""
    return gitterhallen(a, [a // 2])


def eine_tuer_mehr(a: int, r: int) -> Netz:
    """Ergänzung: die vorhandene Tür (Zeile a // 2) bleibt, die neue kommt in Zeile r ≠ a // 2."""
    if r == a // 2:
        raise ValueError("die neue Tür braucht eine andere Zeile als die vorhandene")
    return gitterhallen(a, [a // 2, r])


def k_tueren(a: int, k: int) -> Netz:
    """Netzfamilie mit k gleichmäßig verteilten Türen (keine Ergänzung der einen Tür)."""
    return gitterhallen(a, tuerzeilen(a, k))


# ----------------------------------------------------------------------------------------------------------------------------------
# Kontrastnetze
# ----------------------------------------------------------------------------------------------------------------------------------

def gitter(a: int) -> Netz:
    """Ein einzelnes Gitter a×a."""
    kanten, namen, pos = [], [], []
    for z in range(a):
        for s in range(a):
            u = z * a + s
            if z + 1 < a:
                kanten.append((u, u + a))
            if s + 1 < a:
                kanten.append((u, u + 1))
            namen.append(f"({z},{s})")
            pos.append((float(s), float(a - 1 - z)))
    return netz(f"Gitter {a}×{a}", a * a, kanten, namen, pos)


def saal_mit_stichgang(saal: int = 21, gang: int = 11) -> Netz:
    """Vollständiger Saal mit `saal` Plätzen (jeder mit jedem verbunden), am letzten Saalplatz ein Gang mit `gang` Plätzen (Lutscher-Netz, lollipop)."""
    if saal < 2 or gang < 1:
        raise ValueError("Saal mit mindestens 2, Gang mit mindestens 1 Platz")
    kanten = [(i, j) for i in range(saal) for j in range(i + 1, saal)]
    kanten += [(i, i + 1) for i in range(saal - 1, saal + gang - 1)]
    namen = [f"S{i}" for i in range(saal)] + [f"G{i + 1}" for i in range(gang)]
    radius = 3.0
    winkel = [2 * np.pi * (i + 1) / saal for i in range(saal)]       # der letzte Saalplatz liegt rechts, am Gang
    pos = [(float(radius * np.cos(w)), float(radius * np.sin(w))) for w in winkel]
    pos += [(radius + 0.8 * (i + 1), 0.0) for i in range(gang)]
    return netz(f"Saal mit Stichgang {saal} + {gang}", saal + gang, kanten, namen, pos)


def weg(n: int) -> Netz:
    """Weg (Pfad) mit n Knoten."""
    return netz(f"Weg {n}", n, [(i, i + 1) for i in range(n - 1)], pos=[(float(i), 0.0) for i in range(n)])


def weg_mit_schlussstein(n: int) -> Netz:
    """Weg mit n Knoten, dessen Enden zusätzlich verbunden sind (ein Kreis)."""
    if n < 3:
        raise ValueError("ein Kreis braucht mindestens 3 Knoten")
    winkel = [np.pi / 2 - 2 * np.pi * i / n for i in range(n)]
    return netz(f"Weg {n} mit Schlussstein", n, [(i, i + 1) for i in range(n - 1)] + [(0, n - 1)],
                pos=[(float(np.cos(w)), float(np.sin(w))) for w in winkel])
