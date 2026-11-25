"""Probeläufe: Handrechnung zu H(0,1) = 14/3 auf „zwei Hallen“, Schätzer, Verteilung und Ziehen."""

import numpy as np
import pytest

import trz_abbruch as AB
import trz_netze as N
from conftest import bruch


def test_handwerte_probelaeufe(hand):
    h, cv = AB.momente_zu_ziel(hand, 1)
    assert h[0] == pytest.approx(bruch(14, 3))
    assert cv[0] == pytest.approx(1.8295, abs=5e-4)
    assert AB.laeufe_vorgabe(cv[0]) == 1286
    h3, cv3 = AB.momente_zu_ziel(hand, 3)
    assert h3[2] == pytest.approx(7) and cv3[2] == pytest.approx(1.0880, abs=5e-4)
    assert AB.laeufe_vorgabe(cv3[2]) == 455


def test_abbruch_nach_drei_und_zehn_h(hand):
    assert AB.abbruch_schritt(3, bruch(14, 3)) == 14
    e, p = AB.gedeckelt(hand, 0, 1, 14)
    assert e == pytest.approx(19630091 / 5668704, rel=1e-12)           # in Bruchrechnung auf zwei Wegen vorab bestimmt
    assert e / bruch(14, 3) == pytest.approx(0.742, abs=5e-4) and p == pytest.approx(0.0869, abs=5e-4)
    e47, _ = AB.gedeckelt(hand, 0, 1, 47)
    assert e47 / bruch(14, 3) == pytest.approx(0.978, abs=5e-4)


def test_ein_schritt_von_hand():
    """Weg mit 3 Plätzen, Start in der Mitte, Ziel ein Ende: T = 1 mit Chance ½, sonst 2 + T'. E[min(T, 1)] = 1, P(T > 1) = ½, E[min(T, 3)] = 1 + ½ + ½ = 2."""
    g = N.weg(3)
    assert AB.gedeckelt(g, 1, 0, 1) == (pytest.approx(1), pytest.approx(0.5))
    assert AB.gedeckelt(g, 1, 0, 3) == (pytest.approx(2), pytest.approx(0.25))
    assert AB.momente_zu_ziel(g, 0)[0][1] == pytest.approx(3)


def test_rekursion_gleich_potenz():
    g = N.zwei_hallen(3)
    K = np.arange(1, g.n + 1)
    E, P = AB.gedeckelt_alle_starts(g, 5, K)
    for u in range(g.n):
        if u != 5:
            e, p = AB.gedeckelt(g, u, 5, int(K[u]))
            assert E[u] == pytest.approx(e) and P[u] == pytest.approx(p)


def test_abbruch_schritt_rundung():
    assert AB.abbruch_schritt(3, 74.8627) == 225
    assert AB.abbruch_schritt(1, 0.2) == 1
    assert AB.abbruch_schritt(1, 2.5) == 3
    assert AB.abbruch_schritt(3, 12.5) == AB.abbruch_schritt(3, 12.499999999999998) == 38      # genau auf der Hälfte: das letzte Bit entscheidet nicht


def test_schaetzer_an_vier_laeufen():
    zeiten = np.array([1, 2, 3, 10])
    ohne = AB.schaetzer(zeiten)
    assert ohne["mittel"] == 4 and ohne["abgebrochen"] == 0 and ohne["zensurbewusst"] == 4
    mit = AB.schaetzer(zeiten, 3)
    # gekappt 1, 2, 3, 3; abgebrochen nur der Lauf mit 10 (T > 3); zensurbewusst 9 / 3
    assert mit["mittel"] == pytest.approx(2.25) and mit["abgebrochen"] == 1 and mit["abbruchanteil"] == 0.25 and mit["zensurbewusst"] == pytest.approx(3)
    assert AB.schaetzer(np.array([5, 6]), 2)["zensurbewusst"] is None
    assert mit["von"] < mit["mittel"] < mit["bis"]


def test_verteilung_und_ziehen(hand):
    F = AB.verteilungsfunktion(hand, 0, 1)
    assert F[0] == 0 and F[1] == pytest.approx(0.5) and np.all(np.diff(F) >= -1e-15)
    assert np.sum(1 - F) == pytest.approx(bruch(14, 3), abs=1e-8)        # E[T] = Σ_t P(T > t)
    assert AB.ziehe_zeiten(F, np.array([0.0, 0.4999, 0.5, 0.999999999999999])).tolist()[:3] == [1, 1, 2]
    anteil = AB.deckungsgrad(F, bruch(14, 3), 1286, 400, 99)
    assert 0.90 < anteil <= 1.0
    q = AB.kappungsstreuung(F, bruch(14, 3), 14, 2000, 200, 5)
    assert q["gekappt"][0] < 0.742 < q["gekappt"][2] and q["zensurbewusst"][1] > q["gekappt"][1]


def test_cv_null_braucht_einen_lauf():
    g = N.netz("zwei", 2, [(0, 1)])
    h, cv = AB.momente_zu_ziel(g, 1)
    assert h[0] == 1 and cv[0] == pytest.approx(0)
    assert AB.laeufe_vorgabe(cv[0]) == 1
