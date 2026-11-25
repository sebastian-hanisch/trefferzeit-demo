"""Eigenschaften, die auf jedem zusammenhängenden, einfachen, ungerichteten Netz gelten müssen (je 30 Zufallsnetze): Reihung, Zufallsziel, neue Kante, Umnummerieren."""

import numpy as np
import pytest

import trz_netze as N
import trz_trefferzeit as T
from test_oracle_trefferzeit import zufallsnetz

SEEDS = range(500, 530)


@pytest.mark.parametrize("seed", SEEDS)
def test_zyklus_reihung_zufallsziel(seed):
    g = zufallsnetz(seed, 3, 12)
    H = T.treffer_matrix(g)
    hpi = T.zeit_von_stationaer(g, H)
    n = g.n
    for u in range(n):
        for v in range(n):
            assert H[u, v] - H[v, u] == pytest.approx(hpi[v] - hpi[u], abs=1e-8)
            for w in range(n):
                assert H[u, v] + H[v, w] + H[w, u] == pytest.approx(H[u, w] + H[w, v] + H[v, u], abs=1e-8)
    ordnung = sorted(range(n), key=lambda i: -hpi[i])
    assert all(H[ordnung[i], ordnung[j]] <= H[ordnung[j], ordnung[i]] + 1e-8 for i in range(n) for j in range(i + 1, n))
    zz = T.zufallsziel(g, H)
    assert np.ptp(zz) < 1e-8
    # Nachbarmittel: Σ_{w ~ v} H(w, v) / d_v = 2m/d_v − 1
    nb = N.nachbarn(g)
    for v in range(n):
        assert np.mean([H[w, v] for w in nb[v]]) == pytest.approx(2 * len(g.kanten) / len(nb[v]) - 1)


@pytest.mark.parametrize("seed", SEEDS)
def test_traege_doppelt_und_umnummerieren(seed):
    g = zufallsnetz(seed, 3, 10)
    H = T.treffer_matrix(g)
    assert T.treffer_matrix(g, traege=True) == pytest.approx(2 * H)
    perm = list(range(g.n))[::-1]
    um = N.netz("um", g.n, [(perm[u], perm[v]) for u, v in g.kanten])
    H2 = T.treffer_matrix(um)
    assert H2[np.ix_(perm, perm)] == pytest.approx(H)


@pytest.mark.parametrize("seed", SEEDS)
def test_neue_kante(seed):
    g = zufallsnetz(seed, 3, 9)
    if not N.fehlende_kanten(g):                       # vollständiges Netz: es gibt keine neue Kante; stattdessen ein Kreis
        g = N.weg_mit_schlussstein(g.n + 2)
    fehlen = N.fehlende_kanten(g)
    H = T.treffer_matrix(g)
    d = N.grade(g)
    for a, b in fehlen[:6]:
        neu = N.mit_kante(g, a, b)
        H2 = T.treffer_matrix(neu)
        assert (H2 > H + 1e-9).any()                                           # mindestens eine länger
        nb = N.nachbarn(neu)
        for x, y in ((a, b), (b, a)):
            assert H2[x, y] < H[x, y]                                          # zwischen den Endpunkten kürzer
            r = 1 / (d[x] * T.fluchtwahrscheinlichkeit(g, x, y))
            assert r == pytest.approx(T.widerstand_matrix(g)[x, y])            # R aus der Fluchtwahrscheinlichkeit = effektiver Widerstand
            assert H2[x, y] == pytest.approx((H[x, y] + r) / (1 + r))
        for c in range(g.n):
            if c not in (a, b):                                                # Rückkehrzeit: Nachbarmittel wächst um genau 2/d_c
                assert np.mean([H2[w, c] - H[w, c] for w in nb[c]]) == pytest.approx(2 / d[c])
        # eine Kante am Ziel t verlängert H(s, t) nie
        for t in (a, b):
            assert (H2[:, t] <= H[:, t] + 1e-9).all()
