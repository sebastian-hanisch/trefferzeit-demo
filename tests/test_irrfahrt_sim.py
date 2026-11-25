"""Simulation: der Blockgenerator liefert die SplitMix64-Folge, die vektorisierten Läufe sind gleich einer einfachen Schleife, die Mittel liegen im Band."""

import math

import numpy as np
import pytest

import trz_abbruch as AB
import trz_netze as N
import trz_trefferzeit as T
from trz_irrfahrt_sim import BlockZufall, simuliere_trefferzeiten
from trz_rng import SplitMix64


@pytest.mark.parametrize("seed", [0, 1, 5821, 2**63, 2**64 - 1])
def test_blockgenerator_ist_splitmix64(seed):
    skalar = SplitMix64(seed)
    block = BlockZufall(seed)
    werte = np.concatenate([block.u64(3), block.u64(1), block.u64(0), block.u64(40)])
    assert [int(x) for x in werte] == [skalar.next_u64() for _ in range(44)]


def test_random_wie_skalar():
    skalar, block = SplitMix64(77), BlockZufall(77)
    assert block.random(20).tolist() == [skalar.random() for _ in range(20)]


def _schleife(g, u, v, laeufe, seed):
    """Einfache Referenz mit derselben Ziehungsreihenfolge: Schritt für Schritt, in jedem Schritt die offenen Läufer in aufsteigender Nummer."""
    nb = N.nachbarn(g)
    rng = SplitMix64(seed)
    ort, zeit = [u] * laeufe, [0] * laeufe
    offen = list(range(laeufe)) if u != v else []
    schritt = 0
    while offen:
        schritt += 1
        rest = []
        for i in offen:
            ort[i] = nb[ort[i]][rng.below(len(nb[ort[i]]))]
            if ort[i] == v:
                zeit[i] = schritt
            else:
                rest.append(i)
        offen = rest
    return zeit


@pytest.mark.parametrize("g,u,v", [(N.handnetz(1), 0, 1), (N.zwei_hallen(3), 0, 17), (N.saal_mit_stichgang(5, 3), 0, 7)], ids=["hand", "hallen", "saal"])
def test_vektorisierte_laeufe_gleich_der_schleife(g, u, v):
    for seed in (3, 4711):
        assert simuliere_trefferzeiten(g, u, v, 60, seed).tolist() == _schleife(g, u, v, 60, seed)


def test_gleicher_seed_gleiche_folge_und_schrittgrenze(hand):
    a = simuliere_trefferzeiten(hand, 0, 5, 200, 9)
    assert (a == simuliere_trefferzeiten(hand, 0, 5, 200, 9)).all()
    assert (a != simuliere_trefferzeiten(hand, 0, 5, 200, 10)).any()
    assert (simuliere_trefferzeiten(hand, 0, 5, 200, 9, max_schritte=2) == -1).all()       # nach 5 ist der Weg mindestens 3 Schritte lang
    assert (simuliere_trefferzeiten(hand, 2, 2, 5, 9) == 0).all()


@pytest.mark.parametrize("seed", [11, 12, 13])
def test_mittel_im_band_gegen_exakt(hand, seed):
    h, cv = AB.momente_zu_ziel(hand, 1)
    R = 20000
    zeiten = simuliere_trefferzeiten(hand, 0, 1, R, seed)
    se = cv[0] * h[0] / math.sqrt(R)
    assert abs(zeiten.mean() - T.treffer_matrix(hand)[0, 1]) < 4 * se


def test_unzusammenhaengend_wird_abgewiesen():
    with pytest.raises(ValueError):
        simuliere_trefferzeiten(N.netz("x", 4, [(0, 1), (2, 3)]), 0, 3, 10, 1)
