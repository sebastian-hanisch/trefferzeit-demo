"""Netze: Handnetz, Gitterhallen mit beiden Türregeln, Kontrastnetze (Zählungen von Hand)."""

import math

import pytest

import trz_netze as N


def test_handnetz_eine_und_zwei_tueren():
    g = N.handnetz(1)
    assert g.n == 6 and len(g.kanten) == 7
    assert list(N.grade(g)) == [2, 2, 3, 3, 2, 2]
    g2 = N.handnetz(2)
    assert set(g2.kanten) - set(g.kanten) == {(0, 5)}
    assert N.nachbarn(g)[2] == [0, 1, 3]


@pytest.mark.parametrize("a", range(2, 11))
def test_zwei_hallen_zaehlung(a):
    g = N.zwei_hallen(a)
    # je Halle 2·a·(a−1) Gitterkanten, dazu eine Tür
    assert g.n == 2 * a * a and len(g.kanten) == 4 * a * (a - 1) + 1
    assert N.ist_zusammenhaengend(g)
    u, v = N.hallenknoten(a, 0, a // 2, a - 1), N.hallenknoten(a, 1, a // 2, 0)
    assert N.hat_kante(g, u, v)
    assert g.knoten[u] == f"L({a // 2},{a - 1})" and g.knoten[v] == f"R({a // 2},0)"


def test_ergaenzung_behaelt_die_alte_tuer():
    g = N.eine_tuer_mehr(8, 0)
    assert set(N.zwei_hallen(8).kanten) < set(g.kanten)
    assert set(g.kanten) - set(N.zwei_hallen(8).kanten) == {(7, 64)}
    with pytest.raises(ValueError):
        N.eine_tuer_mehr(8, 4)


def test_tuerfamilie_zeilen_nach_formel():
    for a in range(2, 13):
        for k in range(1, a + 1):
            assert N.tuerzeilen(a, k) == [math.floor((i + 0.5) * a / k) for i in range(k)]
            assert len(set(N.tuerzeilen(a, k))) == k
    assert N.tuerzeilen(8, 1) == [4] and N.tuerzeilen(8, 2) == [2, 6]      # k = 2 enthält die mittlere Tür nicht: keine Ergänzung
    assert N.k_tueren(8, 2).kanten != N.eine_tuer_mehr(8, 0).kanten


def test_saal_mit_stichgang():
    g = N.saal_mit_stichgang(21, 11)
    assert g.n == 32 and len(g.kanten) == 21 * 20 // 2 + 11
    d = N.grade(g)
    assert d[20] == 21 and d[31] == 1 and all(d[i] == 2 for i in range(21, 31))
    assert g.knoten[20] == "S20" and g.knoten[21] == "G1" and g.knoten[31] == "G11"


def test_weg_gitter_und_kantenwerkzeuge():
    assert len(N.weg(5).kanten) == 4 and len(N.weg_mit_schlussstein(5).kanten) == 5
    g = N.gitter(3)
    assert g.n == 9 and len(g.kanten) == 12
    assert len(N.fehlende_kanten(N.handnetz(1))) == 15 - 7
    neu = N.mit_kante(N.handnetz(1), 5, 0)
    assert neu.kanten == N.handnetz(2).kanten
    with pytest.raises(ValueError):
        N.mit_kante(neu, 0, 5)
    with pytest.raises(ValueError):
        N.mit_kante(neu, 1, 1)


def test_ungueltige_netze_werden_abgewiesen():
    with pytest.raises(ValueError):
        N.netz("x", 3, [(0, 3)])
    with pytest.raises(ValueError):
        N.netz("x", 3, [(0, 1), (1, 0)])
    assert not N.ist_zusammenhaengend(N.netz("x", 3, [(0, 1)]))
