"""Verdikte als reine Funktionen: Schwellen und jede Zahl im Text an handgesetzten Werten; Verdikt-Zeilen je Preset-Fall."""

import pytest

import trz_constants as C
import trz_daten as D
import trz_evaluation as E
import trz_netze as N


def test_zahlformate():
    assert E.de(1234.5, 1) == "1 234,5"
    assert E.ganz(79153) == "79 153"
    assert E.zeit(2) == "2,00" and E.zeit(99.996) == "100,0" and E.zeit(548.2) == "548,2" and E.zeit(1190.7) == "1 191"
    assert E.prozent(0.0694, 1) == "6,9 %"


def test_verdict_asymmetrie_schwelle():
    art, text = E.verdict_asymmetrie(1.25, 4.96, 0.73, 0.39, 0.31)
    assert art == "warning"
    for teil in ("1,25", "4,96", "73 %", "39 %", "31 %"):
        assert teil in text
    assert E.verdict_asymmetrie(1.59, 3.67, 0.51, 0.2, 0.07)[0] == "warning"
    assert E.verdict_asymmetrie(1.59, 3.67, 0.51, 0.199, 0.07)[0] == "info"


def test_verdict_ordnung():
    art, text = E.verdict_ordnung(100, 46, 50, 91, 100)
    assert art == "success" and "46 %" in text and "91 %" in text and "nie der längere (Satz)" in text
    art, text = E.verdict_ordnung(8, 0, 8, 8, 8)
    assert "kein asymmetrisches Paar offen" in text and "100 %" in text
    assert E.verdict_ordnung(100, 46, 50, 91, 99)[0] == "error"


def test_verdict_kante():
    art, text = E.verdict_kante(6, 30, (16.3, 5.6), (16.3, 5.6))
    assert art == "info" and "6 von 30" in text and "zwischen ihren Endpunkten keine" in text and "ab 3 Knoten" in text
    assert E.verdict_kante(0, 30, (2, 1), (2, 1))[0] == "error"
    assert E.verdict_kante(6, 30, (2, 2), (2, 1))[0] == "error"
    assert E.verdict_kante(6, 30, (2, 1), (1, 1.5))[0] == "error"


def _p(anteil, abbruch, zensur, h=100.0, vorgabe=500):
    return {"h": h, "anteil": anteil, "abbruch": abbruch, "zensur": zensur * h, "laeufe_vorgabe": vorgabe}


def test_verdict_abbruch_schwellen_und_zahlen():
    art, text = E.verdict_abbruch(_p(0.42, 0.069, 0.451), "3", {"wiederholungen": 4000, "laeufe": 5940, "anteil": 0.953}, {"abbruch": 0.0696, "anteil": 0.2553})
    assert art == "warning" and text.startswith("Nur 6,9 % der Läufe brechen ab")
    for teil in ("42 %", "58 % fehlen", "45 %", "7,0 %", "26 %", "5 940" if False else "500", "4 000", "5 940", "95,3 %"):
        assert teil in text
    art, text = E.verdict_abbruch(_p(0.6, 0.36, 0.9), "1")
    assert art == "warning" and not text.startswith("Nur") and "36,0 % der Läufe brechen ab" in text and "nicht vorgerechnet" in text
    assert E.verdict_abbruch(_p(0.899, 0.05, 0.95), "3")[0] == "warning"
    assert E.verdict_abbruch(_p(0.9, 0.05, 0.95), "3")[0] == "info"
    assert E.verdict_abbruch(_p(0.949, 0.05, 0.95), "3")[0] == "info"
    art, text = E.verdict_abbruch(_p(0.974, 0.031, 0.99), "3")
    assert art == "success" and "97,4 %" in text and "fast harmlos" in text
    art, text = E.verdict_abbruch(_p(1.0, 0.0, 1.0), C.ABBRUCH_OHNE)
    assert art == "info" and "wahre Mittel H = 100,0" in text and "500 Läufe" in text and text.count("Ohne Abbruch") == 1
    p = _p(0.5, 0.05, 0.9)
    p["zensur"] = None
    assert "zensurbewusste" not in E.verdict_abbruch(p, "3")[1]


def test_saalvergleich_nur_am_belegten_fall():
    assert E.zeigt_saalvergleich(C.NETZ_HALLEN, 8, C.PAAR_CV, "3")
    for fall in [(C.NETZ_SAAL, 8, C.PAAR_CV, "3"), (C.NETZ_HALLEN, 7, C.PAAR_CV, "3"), (C.NETZ_HALLEN, 8, C.PAAR_TUER, "3"), (C.NETZ_HALLEN, 8, C.PAAR_CV, "5")]:
        assert not E.zeigt_saalvergleich(*fall)


def test_verdict_negativ_aus_den_zahlen():
    ecken = [{"anteil": 0.974, "abbruch": 0.031}, {"anteil": 0.966, "abbruch": 0.038}]
    abstand = {"zeilen": [{"abstand_mindestens": 8, "kleinster_anteil": 0.746}, {"abstand_mindestens": 15, "kleinster_anteil": 0.965}]}
    art, text = E.verdict_negativ(ecken, abstand)
    assert art == "info"
    for teil in ("96,6 bis 97,4 %", "3,1 bis 3,8 %", "nur 75 %", "ab Abstand 15", "über 96 %"):
        assert teil in text


def test_deckung_nur_fuer_vorgerechnete_paare():
    daten = D.laden()
    assert D.deckung_fuer(daten, C.NETZ_HALLEN, 8, C.PAAR_CV)["laeufe"] == 5940
    assert D.deckung_fuer(daten, C.NETZ_HAND, 5, C.PAAR_TUER)["netz"] == "hand"
    assert D.deckung_fuer(daten, C.NETZ_HALLEN, 8, C.PAAR_GEWAEHLT) is None


def test_verdict_ansicht_richtungen():
    an = E.analysiere_netz(C.NETZ_HAND, 8)
    art, text = E.verdict_ansicht(an, 0, 2)
    assert art == "warning" and "von 0 nach 2 im Mittel 2,00" in text and "7,33" in text and "3,67" in text
    assert "von 0 nach 2" in E.verdict_ansicht(an, 2, 0)[1]                     # die kürzere Richtung steht zuerst
    assert E.verdict_ansicht(an, 0, 5)[0] == "info" and "gleich lang" in E.verdict_ansicht(an, 0, 5)[1]
    assert E.verdict_ansicht(an, 3, 3)[0] == "info"


def test_einzahl_bei_einem_lauf():
    p = _p(1.0, 0.0, 1.0, h=1.0, vorgabe=1)
    deckung = {"wiederholungen": 4000, "laeufe": 1, "anteil": 1.0}
    for abbruch in (C.ABBRUCH_OHNE, "3"):
        text = E.verdict_abbruch(p, abbruch, deckung)[1]
        assert "1 Läufe" not in text and "1 Lauf vor" in text and "mit je 1 Lauf ohne Abbruch" in text


def _kurz(netz, u, v, abbruch, a=8):
    an = E.analysiere_netz(netz, a)
    p = E.probe_exakt(an.g, E.streuung(netz, a), u, v, abbruch)
    return p, E.kurz_laeufe(p, an.g)


@pytest.mark.parametrize("abbruch", list(C.ABBRUCH_STUFEN))
def test_kurz_laeufe_ohne_fehlbetrag_wenn_der_erste_schritt_immer_trifft(abbruch):
    """Saal, Gangende G11 → G10: T = 1 sicher, also P(T > K) = 0 für jedes K ≥ 1 und kein Fehlbetrag."""
    p, text = _kurz(C.NETZ_SAAL, 31, 30, abbruch)
    assert p["abbruch"] == 0.0 and p["gekappt"] == p["h"] == pytest.approx(1.0)
    assert "1 Lauf für ±10 %" in text and "1 Läufe" not in text
    assert "systematischen Fehlbetrag" not in text and "T = 1" in text


@pytest.mark.parametrize("abbruch", list(C.ABBRUCH_STUFEN))
def test_kurz_laeufe_nennt_den_fehlbetrag_wenn_laeufe_abbrechen_koennen(abbruch):
    p, text = _kurz(C.NETZ_HAND, 0, 1, abbruch)
    assert (p["abbruch"] > 0) == (abbruch != C.ABBRUCH_OHNE)
    assert "systematischen Fehlbetrag" in text and "T = 1" not in text and "zählt sie mit K" in text


def test_fehlbetrag_fehlt_genau_beim_erzwungenen_schritt():
    """Auf allen Netzen der App, jedes geordnete Paar: Ein Abbruch nach K ≥ 1 Schritten kann nur dann nie greifen, wenn der Start allein am Ziel hängt (H = 1)."""
    for netz, a in [(C.NETZ_HAND, 8), (C.NETZ_SAAL, 8)] + [(C.NETZ_HALLEN, a) for a in range(C.A_MIN, C.A_MAX + 1)]:
        an = E.analysiere_netz(netz, a)
        nb = N.nachbarn(an.g)
        for u in range(an.g.n):
            for v in range(an.g.n):
                if u != v:
                    assert (an.H[u, v] <= 1 + 1e-9) == (list(nb[u]) == [v])


@pytest.mark.parametrize("u,v", [(0, 2), (2, 0), (0, 5), (3, 3)])
def test_kernfragen_texte(u, v):
    an = E.analysiere_netz(C.NETZ_HAND, 8)
    warum, wohin = E.kurz_warum(an, u, v), E.kurz_wohin(an, u, v)
    if u == v:
        assert "verschiedene" in warum
    elif E.kuerzere_richtung(an, u, v) == 0:
        assert "gleich lang" in warum and "gleich lang" in wohin and "-0,00" not in warum
    else:
        assert "H(π" in warum and "kürzer ist der Weg nach 2" in wohin
