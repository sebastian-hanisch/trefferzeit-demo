"""Probeläufe: Streuung der Trefferzeit, Läufe-Vorgabe, Abbruch nach K Schritten und Schätzer (ohne Streamlit). Braucht `trz_netze`, `trz_trefferzeit`.

T = Schrittzahl eines Laufs von u bis zum ersten Besuch von v; E[T] = H(u, v). Q ist die Übergangsmatrix ohne Zeile und Spalte v.
* Variationskoeffizient (CV = Standardabweichung / Mittel) aus zwei linearen Systemen: t = (I − Q)⁻¹ 1 und E[T²] = (I − Q)⁻¹ (2t − 1).
* Läufe-Vorgabe für ±10 % bei 95 % nach Normalnäherung: R = ⌈(1,96·CV / 0,1)²⌉.
* Abbruch nach K Schritten, abgebrochene Läufe zählen mit K: E[min(T, K)] = t_u − (Q^K t)_u und P(T > K) = (Q^K 1)_u.
* Zensurbewusster Schätzer: Summe aller min(T, K) geteilt durch die Zahl der beendeten Läufe (richtig, wenn die Abbruchrate je Schritt konstant wäre).
"""

import math

import numpy as np

import trz_netze as N
import trz_trefferzeit as T
from trz_irrfahrt_sim import BlockZufall

Z95 = 1.96
GENAUIGKEIT = 0.1


def _q(g: N.Netz, v: int):
    rest = [x for x in range(g.n) if x != v]
    return rest, T.uebergang(g)[np.ix_(rest, rest)]


def momente_zu_ziel(g: N.Netz, v: int):
    """(H(·, v), CV(·, v)) als Felder über alle Starts; beim Start v steht 0."""
    rest, Q = _q(g, v)
    M = np.eye(len(rest)) - Q
    t = np.linalg.solve(M, np.ones(len(rest)))
    s = np.linalg.solve(M, 2 * t - 1)
    h, cv = np.zeros(g.n), np.zeros(g.n)
    h[rest] = t
    cv[rest] = np.sqrt(np.maximum(s - t * t, 0.0)) / t
    return h, cv


def momente_alle(g: N.Netz):
    """Matrizen H und CV über alle geordneten Paare."""
    H, CV = np.zeros((g.n, g.n)), np.zeros((g.n, g.n))
    for v in range(g.n):
        H[:, v], CV[:, v] = momente_zu_ziel(g, v)
    return H, CV


def laeufe_vorgabe(cv: float, genauigkeit: float = GENAUIGKEIT, z: float = Z95) -> int:
    """Zahl unabhängiger Läufe für ±`genauigkeit` (relativ zum Mittel) bei 95 % nach Normalnäherung, mindestens 1."""
    return max(1, math.ceil((z * cv / genauigkeit) ** 2 - 1e-9))


def abbruch_schritt(c: float, h: float) -> int:
    """K = c·H, kaufmännisch gerundet, mindestens 1.

    Die Toleranz 1e-9 hält Fälle fest, in denen c·H genau auf einer Hälfte liegt (zwei Hallen 3×3: H = 12,5, 3·H = 37,5): Sonst entschiede das letzte Bit des
    Rechenwegs (und der Plattform), ob K = 37 oder 38 ist."""
    return max(1, int(math.floor(c * h + 0.5 + 1e-9)))


def gedeckelt(g: N.Netz, u: int, v: int, K: int):
    """(E[min(T, K)], P(T > K)) exakt über die K-te Potenz von Q."""
    rest, Q = _q(g, v)
    i = rest.index(u)
    t = np.linalg.solve(np.eye(len(rest)) - Q, np.ones(len(rest)))
    QK = np.linalg.matrix_power(Q, K)
    return float(t[i] - QK[i] @ t), float(QK[i].sum())


def gedeckelt_alle_starts(g: N.Netz, v: int, K: np.ndarray):
    """Je Start u ≠ v: (E[min(T, K_u)], P(T > K_u)); `K` ist ein ganzzahliges Feld über alle Starts (Rekursion der Überlebenswahrscheinlichkeiten)."""
    rest, Q = _q(g, v)
    k = np.asarray(K)[rest]
    ueberlebt = np.ones(len(rest))
    summe = np.zeros(len(rest))
    em, pr = np.zeros(len(rest)), np.zeros(len(rest))
    for t in range(int(k.max()) + 1):
        treffer = k == t
        em[treffer] = summe[treffer]
        pr[treffer] = ueberlebt[treffer]
        summe += ueberlebt
        ueberlebt = Q @ ueberlebt
    E, P = np.zeros(g.n), np.zeros(g.n)
    E[rest], P[rest] = em, pr
    return E, P


def alle_paare_gedeckelt(g: N.Netz, c: float, H: np.ndarray):
    """Für jedes geordnete Paar mit K = abbruch_schritt(c, H(u, v)): Matrizen (E[min(T, K)] / H, P(T > K)); auf der Diagonale 1 bzw. 0."""
    anteil, rest = np.ones((g.n, g.n)), np.zeros((g.n, g.n))
    for v in range(g.n):
        K = np.array([0 if u == v else abbruch_schritt(c, H[u, v]) for u in range(g.n)])
        E, P = gedeckelt_alle_starts(g, v, K)
        maske = np.arange(g.n) != v
        anteil[maske, v] = E[maske] / H[maske, v]
        rest[:, v] = P
    return anteil, rest


def schaetzer(zeiten: np.ndarray, K=None) -> dict:
    """Schätzungen aus simulierten Läufen. K=None: ohne Abbruch. Läufe mit T > K zählen als abgebrochen und mit K."""
    zeiten = np.asarray(zeiten, dtype=float)
    R = len(zeiten)
    gekappt = zeiten if K is None else np.minimum(zeiten, K)
    abgebrochen = 0 if K is None else int((zeiten > K).sum())
    mittel = float(gekappt.mean())
    streuung = float(gekappt.std(ddof=1)) if R > 1 else 0.0
    halb = Z95 * streuung / math.sqrt(R)
    beendet = R - abgebrochen
    return {"laeufe": R, "mittel": mittel, "von": mittel - halb, "bis": mittel + halb, "abgebrochen": abgebrochen, "abbruchanteil": abgebrochen / R,
            "zensurbewusst": float(gekappt.sum() / beendet) if beendet else None}


# ----------------------------------------------------------------------------------------------------------------------------------
# Verteilung von T: für den Deckungsgrad der Läufe-Vorgabe und die Streuung der Abbruch-Schätzung
# ----------------------------------------------------------------------------------------------------------------------------------

def verteilungsfunktion(g: N.Netz, u: int, v: int, rest_grenze: float = 1e-12, max_schritte: int = 5_000_000) -> np.ndarray:
    """F(t) = P(T ≤ t) für t = 0, 1, … bis P(T > t) < rest_grenze (Rekursion x ← x·Q)."""
    rest, Q = _q(g, v)
    x = np.zeros(len(rest))
    x[rest.index(u)] = 1.0
    Qt = Q.T
    F = [0.0]
    for _ in range(max_schritte):
        x = Qt @ x
        offen = float(x.sum())
        F.append(1.0 - offen)
        if offen < rest_grenze:
            return np.array(F)
    raise ValueError("Verteilung nicht vollständig erreicht")


def ziehe_zeiten(F: np.ndarray, zufall: np.ndarray) -> np.ndarray:
    """Inversionsverfahren: kleinstes t mit F(t) > Zufallswert aus [0, 1)."""
    return np.minimum(np.searchsorted(F, zufall, side="right"), len(F) - 1)


def wiederholungen_ziehen(F: np.ndarray, R: int, wiederholungen: int, seed: int, K=None, block: int = 2_000_000):
    """Je Wiederholung R unabhängige Werte von T aus der exakten Verteilung. Liefert (Mittel der min(T, K), Zahl der Abbrüche) je Wiederholung."""
    rng = BlockZufall(seed)
    summen, abbrueche = np.zeros(wiederholungen), np.zeros(wiederholungen, dtype=np.int64)
    je_block = max(1, block // R)
    for start in range(0, wiederholungen, je_block):
        w = min(je_block, wiederholungen - start)
        t = ziehe_zeiten(F, rng.random(w * R)).reshape(w, R)
        if K is not None:
            abbrueche[start:start + w] = (t > K).sum(axis=1)
            t = np.minimum(t, K)
        summen[start:start + w] = t.sum(axis=1)
    return summen / R, abbrueche


def deckungsgrad(F: np.ndarray, h: float, R: int, wiederholungen: int, seed: int, genauigkeit: float = GENAUIGKEIT) -> float:
    """Anteil der Wiederholungen, in denen das Mittel aus R Läufen ohne Abbruch höchstens um `genauigkeit`·H neben H liegt."""
    mittel, _ = wiederholungen_ziehen(F, R, wiederholungen, seed)
    return float(np.mean(np.abs(mittel - h) <= genauigkeit * h))


def kappungsstreuung(F: np.ndarray, h: float, K: int, R: int, wiederholungen: int, seed: int, quantile=(0.05, 0.5, 0.95)) -> dict:
    """Quantile (über Wiederholungen mit je R Läufen) der beiden Schätzer nach Abbruch, als Anteil von H."""
    mittel, abbrueche = wiederholungen_ziehen(F, R, wiederholungen, seed, K=K)
    beendet = R - abbrueche
    if (beendet == 0).any():
        raise ValueError("Wiederholung ohne beendeten Lauf")
    zensur = mittel * R / beendet
    return {"gekappt": [float(np.quantile(mittel / h, q)) for q in quantile], "zensurbewusst": [float(np.quantile(zensur / h, q)) for q in quantile]}
