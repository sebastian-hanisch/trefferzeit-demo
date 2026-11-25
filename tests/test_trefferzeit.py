"""Trefferzeiten: Handrechnung auf „zwei Hallen“ (alle Brüche von Hand bzw. in Bruchrechnung vorab), drei Rechenwege gegeneinander."""

import numpy as np
import pytest

import trz_netze as N
import trz_trefferzeit as T
from conftest import bruch


def test_handwerte(hand):
    H = T.treffer_matrix(hand)
    # Wegen der Symmetrie 0 <-> 1 ist x = H(0,2) = H(1,2) und x = 1/2 + 1/2·(1 + x), also x = 2
    x = (0.5 + 0.5) / (1 - 0.5)
    assert H[0, 2] == pytest.approx(x) == pytest.approx(2)
    assert H[2, 0] == pytest.approx(bruch(22, 3))
    assert H[2, 3] == pytest.approx(2 * 3 + 1) == pytest.approx(H[3, 2])          # Türschritt: 2 · (Kanten der Halle) + 1
    assert H[0, 5] == pytest.approx(bruch(49, 3)) == pytest.approx(H[5, 0])
    assert H[0, 1] == pytest.approx(bruch(14, 3))


def test_stationaer_und_zeit_von_stationaer(hand):
    H = T.treffer_matrix(hand)
    assert T.stationaer(hand) == pytest.approx(np.array([2, 2, 3, 3, 2, 2]) / 14)
    hpi = T.zeit_von_stationaer(hand, H)
    assert hpi == pytest.approx([bruch(419, 42)] * 2 + [bruch(65, 14)] * 2 + [bruch(419, 42)] * 2)
    assert H[2, 0] - H[0, 2] == pytest.approx(hpi[0] - hpi[2]) == pytest.approx(bruch(16, 3))
    assert T.zufallsziel(hand, H) == pytest.approx([bruch(323, 42)] * 6)
    assert T.mittlere_trefferzeit(H) == pytest.approx(bruch(49, 5))


def test_zweite_tuer(hand):
    H = T.treffer_matrix(hand)
    g2 = N.handnetz(2)
    H2 = T.treffer_matrix(g2)
    laenger = {(u, v) for u in range(6) for v in range(6) if u != v and H2[u, v] > H[u, v] + 1e-9}
    assert laenger == {(0, 1), (0, 2), (1, 2), (4, 3), (5, 3), (5, 4)}
    assert H2[0, 2] == pytest.approx(bruch(64, 15))
    assert H2[0, 5] == pytest.approx(bruch(28, 5))
    assert T.mittlere_trefferzeit(H2) == pytest.approx(bruch(508, 75))
    assert T.zufallsziel(g2, H2) == pytest.approx([bruch(107, 20)] * 6)


def test_fluchtwahrscheinlichkeit_und_widerstand(hand):
    R = T.widerstand_matrix(hand)
    assert R[0, 5] == pytest.approx(bruch(7, 3))                     # 2/3 + 1 + 2/3 (Reihenschaltung: Dreieck, Tür, Dreieck)
    p = T.fluchtwahrscheinlichkeit(hand, 0, 5)
    assert 1 / (2 * p) == pytest.approx(R[0, 5])
    assert (bruch(49, 3) + bruch(7, 3)) / (1 + bruch(7, 3)) == pytest.approx(bruch(28, 5))


@pytest.mark.parametrize("g", [N.handnetz(1), N.handnetz(2), N.zwei_hallen(3), N.saal_mit_stichgang(5, 3), N.weg(7), N.weg_mit_schlussstein(9)], ids=lambda g: g.name)
def test_drei_rechenwege_stimmen_ueberein(g):
    H = T.treffer_matrix(g)
    for andere in (T.treffer_je_ziel(g), T.treffer_je_ziel(g, duenn=True), T.treffer_ueber_widerstand(g)):
        assert andere == pytest.approx(H, rel=1e-9, abs=1e-9)
    assert T.residuum(g, H) < 1e-10


def test_residuum_schlaegt_bei_falscher_matrix_an(hand):
    H = T.treffer_matrix(hand)
    H[0, 3] += 0.01
    assert T.residuum(hand, H) > 1e-4


def test_weg_mit_schlussstein_aus_eins_wird_n_minus_eins():
    for n in (4, 6, 8, 20, 50):
        assert T.treffer_zu_ziel(N.weg(n), 1)[0] == pytest.approx(1)
        assert T.treffer_zu_ziel(N.weg_mit_schlussstein(n), 1)[0] == pytest.approx(n - 1)


def test_traege_kette_verdoppelt(hand):
    assert T.treffer_matrix(hand, traege=True) == pytest.approx(2 * T.treffer_matrix(hand))
