"""Asymmetrie der Trefferzeiten, eine Reihenfolge für alle Paare und die billigen Gegner (ohne Streamlit). Braucht `trz_netze`.

Gegner zur Schätzung („nur der Zielgrad zählt“): H(u, v) ≈ 2m / d_v, (a) roh, (b) mit dem besten Vorfaktor c, (c) mit einem eigenen Wert je Zielgrad.
Fehlermaß: Median von |Schätzung − H| / H über alle geordneten Paare. (b) und (c) werden **auf den bewerteten Paaren selbst** angepasst, also zugunsten des Gegners.

Gegner zur Reihung („wohin ist der Weg kürzer?“): zum Knoten mit höherem Grad; bei gleichem Grad zum Knoten mit kleinerem π-gewichtetem mittlerem Abstand
Σ_w π(w)·Abstand(w, v). Beide brauchen die Abstände bzw. Grade im ganzen Netz.
"""

import math
from collections import deque

import numpy as np

import trz_netze as N

GLEICH_REL = 1e-9


def ungeordnete_paare(n: int):
    return np.triu_indices(n, 1)


def verhaeltnisse(H: np.ndarray) -> np.ndarray:
    """Je ungeordnetem Paar: größere durch kleinere Richtung (≥ 1)."""
    iu, iv = ungeordnete_paare(len(H))
    hin, her = H[iu, iv], H[iv, iu]
    return np.maximum(hin, her) / np.minimum(hin, her)


def groesstes_paar(M: np.ndarray, maske: np.ndarray = None):
    """Geordnetes Paar (u, v), u ≠ v, mit dem größten M(u, v); bei Gleichstand (relativ 1e-9) das kleinste (u, v)."""
    maske = ~np.eye(len(M), dtype=bool) if maske is None else maske
    groesst = M[maske].max()
    u, v = np.argwhere(maske & (M >= groesst - GLEICH_REL * abs(groesst)))[0]
    return int(u), int(v)


def groesstes_verhaeltnis(H: np.ndarray):
    """(u, v, Verhältnis) mit H(u, v) / H(v, u) maximal: u → v ist die lange Richtung."""
    Q = np.ones_like(H)
    maske = ~np.eye(len(H), dtype=bool)
    Q[maske] = H[maske] / H.T[maske]
    u, v = groesstes_paar(Q, maske)
    return u, v, float(Q[u, v])


def asymmetrisch(H: np.ndarray) -> np.ndarray:
    """Je ungeordnetem Paar: Sind die beiden Richtungen verschieden (relativ 1e-9)?"""
    iu, iv = ungeordnete_paare(len(H))
    hin, her = H[iu, iv], H[iv, iu]
    return np.abs(hin - her) > GLEICH_REL * np.maximum(hin, her)


def gleichstandsgruppen(werte: np.ndarray, rel: float = GLEICH_REL) -> list:
    """Knoten nach fallendem Wert in Gruppen gleicher Werte (relativ `rel`), in jeder Gruppe aufsteigend."""
    reihenfolge = sorted(range(len(werte)), key=lambda i: (-werte[i], i))
    gruppen = []
    for i in reihenfolge:
        if gruppen and abs(werte[gruppen[-1][-1]] - werte[i]) <= rel * max(1.0, abs(werte[i])):
            gruppen[-1].append(i)
        else:
            gruppen.append([i])
    return [sorted(g) for g in gruppen]


def zahl_stimmiger_reihenfolgen(hpi: np.ndarray) -> int:
    """Stimmig („u vor v“ ⇒ H(u, v) ≤ H(v, u)) sind genau die Reihenfolgen mit nicht steigendem H(π, ·): Produkt der Fakultäten der Gleichstandsgruppen."""
    return math.prod(math.factorial(len(g)) for g in gleichstandsgruppen(hpi))


def abstaende(g: N.Netz) -> np.ndarray:
    """Kürzeste Distanzen in Schritten (Breitensuche von jedem Knoten)."""
    nb = N.nachbarn(g)
    D = np.full((g.n, g.n), -1, dtype=np.int64)
    for s in range(g.n):
        D[s, s] = 0
        schlange = deque([s])
        while schlange:
            u = schlange.popleft()
            for w in nb[u]:
                if D[s, w] < 0:
                    D[s, w] = D[s, u] + 1
                    schlange.append(w)
    return D


# ----------------------------------------------------------------------------------------------------------------------------------
# Gegner zur Reihung
# ----------------------------------------------------------------------------------------------------------------------------------

def _vorzeichen(x: np.ndarray, skala: np.ndarray) -> np.ndarray:
    return np.where(np.abs(x) > GLEICH_REL * np.maximum(skala, 1.0), np.sign(x), 0.0)


def ordnungsregeln(g: N.Netz, H: np.ndarray, hpi: np.ndarray) -> dict:
    """Zählungen über alle asymmetrischen ungeordneten Paare. Eine Regel, die ein Paar offen lässt, zählt dort als nicht richtig."""
    iu, iv = ungeordnete_paare(g.n)
    asym = asymmetrisch(H)
    # richtig = +1: der Weg u → v ist der kürzere, also v der „leichtere“ Knoten
    wahr = np.sign(H[iv, iu] - H[iu, iv])[asym]
    d = N.grade(g)
    # Σ_w d_w·Abstand(w, v) in ganzen Zahlen (= 2m mal der π-gewichtete mittlere Abstand): exakte Gleichstände bleiben Gleichstände. Mit Gleitkomma-Mittelwerten
    # entschiede das Rundungsrauschen solche Paare zufällig und damit plattformabhängig.
    abstand_summe = d @ abstaende(g)
    nach_grad = np.sign(d[iv] - d[iu])[asym]
    nach_abstand = np.sign(abstand_summe[iu] - abstand_summe[iv])[asym]
    nach_hpi = _vorzeichen(hpi[iu] - hpi[iv], np.maximum(hpi[iu], hpi[iv]))[asym]
    beide = np.where(nach_grad != 0, nach_grad, nach_abstand)
    anzahl = int(asym.sum())
    verschieden = nach_grad != 0
    return {
        "paare": len(iu),
        "asymmetrisch": anzahl,
        "gradgleich": int((~verschieden).sum()),
        "grad_richtig": int((nach_grad == wahr).sum()),
        "grad_verschieden": int(verschieden.sum()),
        "abstand_richtig": int((nach_abstand == wahr).sum()),
        "beide_richtig": int((beide == wahr).sum()),
        "beide_offen": int((beide == 0).sum()),
        "hpi_richtig": int((nach_hpi == wahr).sum()),
        "abstand_pi": abstand_summe / d.sum(),
    }


# ----------------------------------------------------------------------------------------------------------------------------------
# Gegner zur Schätzung: H ≈ 2m / d_Ziel
# ----------------------------------------------------------------------------------------------------------------------------------

def _bestes_c(x: np.ndarray, schranke: float):
    """Für Fehler ≤ schranke: Intervall von c je Punkt, |c·x − 1| ≤ schranke. Liefert (größte Zahl überdeckter Punkte, ein c, das sie erreicht)."""
    unten, oben = np.sort((1 - schranke) / x), np.sort((1 + schranke) / x)
    ueberdeckt = np.arange(1, len(x) + 1) - np.searchsorted(oben, unten, side="left")
    i = int(np.argmax(ueberdeckt))
    ende = oben[np.searchsorted(oben, unten[i], side="left")]
    naechster = unten[i + 1] if i + 1 < len(x) else ende
    return int(ueberdeckt[i]), float((unten[i] + min(ende, max(naechster, unten[i]))) / 2)


def _zahl(teile: dict, klassen: list, schranke: float) -> int:
    """So viele Punkte der genannten Klassen haben höchstens den Fehler `schranke`, wenn jede ihren besten Faktor nimmt."""
    return sum(_bestes_c(teile[k], schranke)[0] for k in klassen)


def _kleinste_schranke(teile: dict, klassen: list, ziel: int, oben: float) -> float:
    """Kleinste Fehlerschranke in [0, oben], bei der mindestens `ziel` Punkte überdeckt sind (Halbierung; bei `oben` müssen es genug sein)."""
    if ziel <= 0 or _zahl(teile, klassen, 0.0) >= ziel:
        return 0.0
    lo, hi = 0.0, oben
    for _ in range(60):
        mitte = (lo + hi) / 2
        if _zahl(teile, klassen, mitte) >= ziel:
            hi = mitte
        else:
            lo = mitte
        if hi - lo <= 1e-15 * hi:
            break
    return hi


def _bestes_paar(x: np.ndarray, a: int, r: float):
    """x aufsteigend. Minimiert max(f_a(c), r) + max(f_{a+1}(c), r) über c: f_a ist der größte Fehler in einem Fenster aus a benachbarten Punkten, f_{a+1} in einem
    Fenster aus a + 1 Punkten, das es enthält; r ist die Schranke, die die übrigen Klassen brauchen. Liefert (Summe, c).

    Die a kleinsten Fehler |c·x − 1| einer Klasse liegen bei benachbarten x, der größte davon an einem Rand: f = max(1 − c·x_links, c·x_rechts − 1). Je Fensterpaar ist
    die Summe konvex und stückweise linear in c; ihr Minimum liegt an einem Knick, also an einem der sechs Kandidaten."""
    n = len(x)
    if a == 0:                                   # kein Punkt unter den ersten, einer dahinter: sein Fehler lässt sich auf 0 setzen
        return 2 * r, float(1 / x[n // 2])
    beste, bestes_c = np.inf, 1.0
    start = np.arange(n - a + 1)                 # Fenster aus a Punkten
    for versatz in (-1, 0):                      # das größere Fenster beginnt einen Punkt davor oder an derselben Stelle
        j = start[(start + versatz >= 0) & (start + versatz + a < n)]
        if len(j) == 0:
            continue
        k = j + versatz
        a1, b1, a2, b2 = x[j], x[j + a - 1], x[k], x[k + a]
        c = np.stack([2 / (a1 + b1), 2 / (a2 + b2), (1 - r) / a1, (1 + r) / b1, (1 - r) / a2, (1 + r) / b2])
        wert = (np.maximum(np.maximum(1 - c * a1, c * b1 - 1), r) + np.maximum(np.maximum(1 - c * a2, c * b2 - 1), r))
        wert = np.where(c > 0, wert, np.inf)
        i = np.unravel_index(int(np.argmin(wert)), wert.shape)
        if wert[i] < beste:
            beste, bestes_c = float(wert[i]), float(c[i])
    return beste, bestes_c


def passe_faktoren_an(x: np.ndarray, klasse: np.ndarray) -> dict:
    """Je Klasse ein Faktor c > 0, so dass np.median von |c·x − 1| über alle Punkte kleinstmöglich ist (x > 0). Das ist genau der angezeigte Median-Fehler.

    Ungerade Anzahl: Der Median ist ein einzelner Wert. Für eine feste Fehlerschranke zählt jede Klasse ihre größtmögliche Zahl überdeckter Punkte unabhängig; die
    kleinste Schranke, bei der die Summe N//2 + 1 erreicht, wird per Halbierung gesucht.

    Gerade Anzahl N = 2h: Der Median ist (s + t) / 2 aus dem h-kleinsten Fehler s und dem (h+1)-kleinsten t. Der Punkt mit t liegt in einer Klasse m, die a der ersten
    h Punkte stellt; die übrigen Klassen stellen h − a und brauchen dafür mindestens die Schranke r. Über alle m, a und Fenster der Klasse m wird die Summe s + t exakt
    minimiert (`_bestes_paar`). Weil s ≤ s_oben gilt (s_oben: die kleinste Schranke mit h + 1 überdeckten Punkten; dort ist s + t ≤ 2·s_oben erreichbar), kommen nur
    wenige a infrage."""
    voll = len(x) // 2 + 1
    klassen = sorted(set(klasse.tolist()))
    teile = {k: np.sort(x[klasse == k]) for k in klassen}
    oben = 1.0
    while _zahl(teile, klassen, oben) < voll:
        oben *= 2
    s_oben = _kleinste_schranke(teile, klassen, voll, oben)
    faktoren_oben = {k: _bestes_c(teile[k], s_oben)[1] for k in klassen}
    if len(x) % 2:
        return faktoren_oben

    def median(faktoren):
        return float(np.median(np.abs(np.concatenate([faktoren[k] * teile[k] - 1 for k in klassen]))))

    h = len(x) // 2
    grenze = s_oben * (1 + 1e-12)
    beste_summe, beste_wahl = np.inf, None
    for m in klassen:
        andere = [k for k in klassen if k != m]
        je_andere = _zahl(teile, andere, grenze)
        for a in range(max(0, h - je_andere), min(_bestes_c(teile[m], grenze)[0], len(teile[m]) - 1) + 1):
            r = _kleinste_schranke(teile, andere, h - a, grenze)
            summe, c = _bestes_paar(teile[m], a, r)
            if summe < beste_summe - 1e-13:
                beste_summe, beste_wahl = summe, (m, c, r)
    if beste_wahl is None:
        return faktoren_oben
    m, c, r = beste_wahl
    r_sicher = r * (1 + 1e-12) + 1e-15          # ein Hauch Luft, damit ein Punkt genau auf der Schranke mitzählt
    faktoren = {k: (c if k == m else _bestes_c(teile[k], r_sicher)[1]) for k in klassen}
    return min((faktoren, faktoren_oben), key=median)


def formel_gegner(g: N.Netz, H: np.ndarray) -> dict:
    """Die drei Varianten von H(u, v) ≈ 2m/d_v mit ihrem Median-Fehler über alle geordneten Paare."""
    maske = ~np.eye(g.n, dtype=bool)
    d = N.grade(g)
    zwei_m = float(d.sum())
    ziel = np.broadcast_to(d, (g.n, g.n))[maske]
    h = H[maske]
    roh = zwei_m / ziel
    x = roh / h

    def fehler(schaetzung):
        return float(np.median(np.abs(schaetzung - h) / h))

    c = passe_faktoren_an(x, np.zeros(len(x), dtype=int))[0]
    je_grad = passe_faktoren_an(x, ziel)
    vorhersage_grad = roh * np.array([je_grad[int(k)] for k in ziel])
    return {"zwei_m": zwei_m, "roh": fehler(roh), "faktor": c, "mit_faktor": fehler(c * roh),
            "je_grad": {int(k): v for k, v in je_grad.items()}, "mit_je_grad": fehler(vorhersage_grad)}
