"""Orakel: Trefferzeiten, Pendelzeit, Streuung und Abbruch gegen unabhängige Rechenwege.

* H: Gleichungssystem je Ziel in exakten Brüchen (eigene Gauß-Elimination, anderer Weg als die Fundamentalmatrix und die Gleitkomma-Löser der Demo) und die
  Spektralformel über die Eigenwerte der symmetrisierten Übergangsmatrix (Lovász, Satz 3.1).
* Pendelzeit H(u,v) + H(v,u) = 2m · R mit dem effektiven Widerstand aus einer Spannbaumzählung in Brüchen (Matrix-Baum-Satz). Nicht
  `networkx.resistance_distance`: In Version 3.7 weicht sie auf einem dichten Netz mit 12 Knoten um rund 0,8 % vom exakten Wert ab.
* CV und E[min(T, K)]: Momente aus der Verteilung P(T > t), die in Brüchen bzw. durch Aufsummieren entsteht.
Je Test eine kleine, feste Menge Zufallsnetze; der große Lauf mit mehreren hundert Netzen liegt außerhalb des Repos."""

from fractions import Fraction

import numpy as np
import pytest

import trz_abbruch as AB
import trz_netze as N
import trz_trefferzeit as T
from trz_rng import SplitMix64


def zufallsnetz(seed, nmin=3, nmax=9):
    """Zusammenhängendes Zufallsnetz: erst ein Zufallsbaum, dann weitere Kanten (kein Neuziehen bis zum Zusammenhang)."""
    rng = SplitMix64(seed)
    n = nmin + rng.below(nmax - nmin + 1)
    kanten = {(rng.below(v), v) for v in range(1, n)}
    fehlen = [(u, v) for u in range(n) for v in range(u + 1, n) if (u, v) not in kanten]
    rng.shuffle(fehlen)
    kanten |= set(fehlen[: rng.below(len(fehlen) + 1)])
    return N.netz("zufall", n, sorted(kanten))


def loese_brueche(M, b):
    n = len(b)
    M = [list(z) + [x] for z, x in zip(M, b)]
    for c in range(n):
        p = next(r for r in range(c, n) if M[r][c] != 0)
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c and M[r][c] != 0:
                f = M[r][c] / M[c][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def treffer_brueche(g):
    nb = N.nachbarn(g)
    H = [[Fraction(0)] * g.n for _ in range(g.n)]
    for v in range(g.n):
        rest = [u for u in range(g.n) if u != v]
        M = [[Fraction(int(u == w)) - (Fraction(1, len(nb[u])) if w in nb[u] else 0) for w in rest] for u in rest]
        for u, x in zip(rest, loese_brueche(M, [Fraction(1)] * len(rest))):
            H[u][v] = x
    return H


def treffer_spektral(g):
    """H(u,v) = 2m Σ_{k≥2} 1/(1−λ_k) · (ψ_k(v)²/d_v − ψ_k(u)ψ_k(v)/√(d_u d_v)) mit den Eigenpaaren von D^-1/2 A D^-1/2."""
    A = N.adjazenz(g)
    d = A.sum(axis=1)
    lam, V = np.linalg.eigh(A / np.sqrt(np.outer(d, d)))
    rest = np.argsort(lam)[:-1]
    W = V[:, rest] / np.sqrt(d)[:, None]
    g_ = 1 / (1 - lam[rest])
    G = (W * g_) @ W.T
    H = d.sum() * (np.diag(G)[None, :] - G)
    return H


@pytest.mark.parametrize("seed", range(40))
def test_fundamentalmatrix_gegen_brueche_und_spektrum(seed):
    g = zufallsnetz(seed)
    H = T.treffer_matrix(g)
    exakt = np.array([[float(x) for x in z] for z in treffer_brueche(g)])
    assert H == pytest.approx(exakt, rel=1e-9, abs=1e-9)
    assert treffer_spektral(g) == pytest.approx(exakt, rel=1e-8, abs=1e-8)
    assert T.treffer_je_ziel(g, duenn=True) == pytest.approx(exakt, rel=1e-9, abs=1e-9)
    assert T.treffer_ueber_widerstand(g) == pytest.approx(exakt, rel=1e-8, abs=1e-8)


def determinante(M):
    """Exakte Determinante in Brüchen (Gauß mit Zeilentausch)."""
    M = [list(z) for z in M]
    n, det = len(M), Fraction(1)
    for c in range(n):
        p = next((r for r in range(c, n) if M[r][c] != 0), None)
        if p is None:
            return Fraction(0)
        if p != c:
            M[c], M[p] = M[p], M[c]
            det = -det
        det *= M[c][c]
        for r in range(c + 1, n):
            f = M[r][c] / M[c][c]
            M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return det


def widerstand_ueber_spannbaeume(g, u, v):
    """Matrix-Baum-Satz: R(u,v) = det(L ohne u und v) / det(L ohne u) (Spannwälder, die u und v trennen, durch Spannbäume)."""
    nb = N.nachbarn(g)

    def ohne(weg):
        rest = [x for x in range(g.n) if x not in weg]
        return [[Fraction(len(nb[x])) if x == y else Fraction(-int(y in nb[x])) for y in rest] for x in rest]

    return determinante(ohne({u, v})) / determinante(ohne({u}))


@pytest.mark.parametrize("seed", range(100, 130))
def test_pendelzeit_gleich_2m_mal_widerstand_aus_spannbaumzaehlung(seed):
    g = zufallsnetz(seed)
    H = T.treffer_matrix(g)
    R = T.widerstand_matrix(g)
    for u, v in [(0, 1), (0, g.n - 1), (1, g.n - 1)]:
        if u == v:
            continue
        r = float(widerstand_ueber_spannbaeume(g, u, v))
        assert R[u, v] == pytest.approx(r, rel=1e-9)
        assert H[u, v] + H[v, u] == pytest.approx(2 * len(g.kanten) * r, rel=1e-9)


def momente_aus_verteilung(g, u, v, grenze=1e-14):
    """E[T], CV und E[min(T,K)] aus P(T > t), vorwärts gerechnet (Zeilenvektor, eigene Schleife)."""
    nb = N.nachbarn(g)
    verteilt = {u: 1.0}
    ueberlebt = []
    while True:
        offen = sum(verteilt.values())
        ueberlebt.append(offen)
        if offen < grenze:
            break
        neu = {}
        for x, p in verteilt.items():
            for w in nb[x]:
                if w != v:
                    neu[w] = neu.get(w, 0.0) + p / len(nb[x])
        verteilt = neu
    s = np.array(ueberlebt)
    e1 = s.sum()
    e2 = ((2 * np.arange(len(s)) + 1) * s).sum()
    return float(e1), float(np.sqrt(e2 - e1 * e1) / e1), s


@pytest.mark.parametrize("seed", range(200, 230))
def test_cv_und_abbruch_gegen_verteilung(seed):
    g = zufallsnetz(seed, 3, 7)
    u, v = 0, g.n - 1
    h, cv = AB.momente_zu_ziel(g, v)
    e1, cv_v, s = momente_aus_verteilung(g, u, v)
    assert h[u] == pytest.approx(e1, rel=1e-8) and cv[u] == pytest.approx(cv_v, rel=1e-6, abs=1e-6)
    for K in (1, 2, 5, AB.abbruch_schritt(3, h[u])):
        e, p = AB.gedeckelt(g, u, v, K)
        summe = s[:K].sum() if K <= len(s) else s.sum()
        assert e == pytest.approx(summe, rel=1e-9) and p == pytest.approx(s[K] if K < len(s) else 0.0, abs=1e-10)


def test_orakel_am_handbeispiel(hand):
    exakt = treffer_brueche(hand)
    assert exakt[0][2] == 2 and exakt[2][0] == Fraction(22, 3) and exakt[0][1] == Fraction(14, 3)
    assert treffer_spektral(hand)[2, 0] == pytest.approx(22 / 3)
    e1, cv, _ = momente_aus_verteilung(hand, 0, 1)
    assert e1 == pytest.approx(14 / 3) and cv == pytest.approx(1.8295, abs=5e-4)
