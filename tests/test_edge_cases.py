"""Randfälle: zwei und drei Plätze, Blatt als Start, unzusammenhängende Netze, Gleichstände, vollständiger Saal ohne fehlende Kante, Reglerränder."""

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import trz_abbruch as AB
import trz_asymmetrie as AS
import trz_constants as C
import trz_evaluation as E
import trz_netze as N
import trz_szenario as S
import trz_trefferzeit as T

ROOT = Path(__file__).resolve().parent.parent


def test_zwei_plaetze():
    g = N.netz("zwei", 2, [(0, 1)])
    H = T.treffer_matrix(g)
    assert H == pytest.approx(np.array([[0, 1], [1, 0]]))
    assert N.fehlende_kanten(g) == []
    assert AS.verhaeltnisse(H).tolist() == [1.0]


def test_drei_plaetze_und_blattstart():
    g = N.weg(3)
    H = T.treffer_matrix(g)
    assert H[0, 1] == pytest.approx(1) and H[1, 0] == pytest.approx(3) and H[0, 2] == pytest.approx(4)
    neu = N.mit_kante(g, 0, 2)
    H2 = T.treffer_matrix(neu)
    assert H2[0, 2] < H[0, 2] and (H2 > H + 1e-9).any()
    assert H2 == pytest.approx(2 * (1 - np.eye(3)))             # Dreieck: jede Trefferzeit 2


def test_unzusammenhaengend_abgewiesen():
    g = N.netz("x", 4, [(0, 1), (2, 3)])
    for fn in (T.treffer_matrix, T.treffer_je_ziel, T.widerstand_matrix):
        with pytest.raises(ValueError):
            fn(g)


def test_vollstaendiger_saal_ist_symmetrisch():
    g = N.netz("k5", 5, [(i, j) for i in range(5) for j in range(i + 1, 5)])
    H = T.treffer_matrix(g)
    assert H[~np.eye(5, dtype=bool)] == pytest.approx(4)
    assert not AS.asymmetrisch(H).any()
    z = AS.ordnungsregeln(g, H, T.zeit_von_stationaer(g, H))
    assert z["asymmetrisch"] == 0
    assert E.verdict_ordnung(0, 0, 0, 0, 0)[0] == "info"
    assert E.verdict_asymmetrie(1.0, 1.0, 0.0, 0.0, 0.0)[0] == "info"
    assert AS.zahl_stimmiger_reihenfolgen(T.zeit_von_stationaer(g, H)) == 120
    assert N.fehlende_kanten(g) == []


def test_gleichstandsgruppen_toleranz():
    assert AS.gleichstandsgruppen(np.array([2.0, 5.0, 2.0 + 1e-12, 5.0 - 1e-11])) == [[1, 3], [0, 2]]
    assert len(AS.gleichstandsgruppen(np.array([1.0, 1.0 + 1e-6]))) == 2


def test_neue_kante_ungueltig_und_standardwerte():
    kante, grund = S.neue_kante(C.NETZ_HAND, 8, C.KANTE_FREI, 0, 1, 1)
    assert kante is None and "verschiedene" in grund
    kante, grund = S.neue_kante(C.NETZ_HAND, 8, C.KANTE_FREI, 0, 0, 1)
    assert kante is None and "schon verbunden" in grund
    assert S.neue_kante(C.NETZ_HAND, 8, C.KANTE_TUER, 0, 0, 1) == ((0, 5), None)
    assert S.neue_kante(C.NETZ_HALLEN, 8, C.KANTE_TUER, 4, 0, 1) == ((7, 64), None)       # Zeile der vorhandenen Tür: die erste andere Zeile
    assert S.wirksame_art(C.NETZ_SAAL, C.KANTE_TUER) == C.KANTE_FREI
    for netz in C.NETZE:
        for a in range(C.A_MIN, C.A_MAX + 1):
            g = S.netz_fuer(netz, a)
            std = C.knoten_standard(netz, a)
            assert g.n == C.anzahl_knoten(netz, a)
            assert all(0 <= w < g.n for w in std.values()) and std["u"] != std["v"]
            assert not N.hat_kante(g, std["ka"], std["kb"])
            u, v = S.tuerpaar(netz, a)
            assert N.hat_kante(g, u, v)
            if netz != C.NETZ_SAAL:
                assert len(S.tuerzeilen_neu(netz, a)) >= 1


def test_simulation_wird_bei_grossem_h_gekuerzt():
    assert E.simulation_laeufe(5000, 100.0) == 5000
    assert E.simulation_laeufe(5000, 2065.0) == C.SCHRITT_DECKEL // 2065
    assert E.simulation_laeufe(50, 1e9) == 1


def test_gleiche_ergebnisse_in_prozessen_mit_anderer_hash_reihenfolge():
    """Dieselbe Rechnung in zwei Prozessen mit verschiedenem PYTHONHASHSEED: keine Abhängigkeit von der Reihenfolge in Mengen oder Wörterbüchern."""
    code = ("import trz_evaluation as E;an=E.analysiere_netz('hallen',4);s=E.streuung('hallen',4);f=E.asymmetrie(an)['formel'];"
            "z=E.simuliere(an.g,*s.cv_paar,50,3,None);print(s.cv_paar, sorted(f['je_grad']), round(f['mit_je_grad'],12), int(z['zeiten'].sum()))")
    ausgaben = set()
    for hashseed in ("1", "2"):
        umgebung = dict(os.environ, PYTHONHASHSEED=hashseed)
        lauf = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, env=umgebung, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        assert lauf.returncode == 0, lauf.stderr
        ausgaben.add(lauf.stdout)
    assert len(ausgaben) == 1


def test_regler_maximum_groesstes_netz():
    """Hallenseite 10 (200 Plätze) mit allen Rechnungen der Seite einmal (kein Zeitlimit, nur kein Absturz und Prüfung am Ergebnis)."""
    an = E.analysiere_netz(C.NETZ_HALLEN, C.A_MAX)
    assert an.g.n == 200 and an.residuum < 1e-10
    st_ = E.streuung(C.NETZ_HALLEN, C.A_MAX)
    p = E.probe_exakt(an.g, st_, *st_.cv_paar, "10")
    assert 0 < p["anteil"] < 1 and p["K"] == AB.abbruch_schritt(10, p["h"])
    e = E.ergaenze(an, S.neue_kante(C.NETZ_HALLEN, 10, C.KANTE_TUER, 0, 0, 1)[0])
    assert e.residuum < 1e-10 and e.ab[1] < e.ab[0]
    assert len(E.zeilen_sweep(an)) == 9
