"""Jede Zahl der README-Befundtabellen wird hier neu gerechnet: Der Test baut die Textstelle aus der Rechnung und sucht sie in der README.

Zahl und Text bleiben so verbunden: Ändert sich die Rechnung, passt die Textstelle nicht mehr. Die Zählung über den Graphen-Atlas und die Deckungsmessung werden
vollständig neu gerechnet; Messwerte aus Zufallsziehungen als Band."""

import importlib.util
import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

import trz_abbruch as AB
import trz_asymmetrie as AS
import trz_constants as C
import trz_daten as D
import trz_evaluation as E
import trz_netze as N
import trz_trefferzeit as T

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")


def steht(*teile):
    for teil in teile:
        assert teil in README, f"nicht in der README: {teil!r}"


def p(x, stellen=0):
    return E.prozent(x, stellen)


def d(x, stellen=2):
    return E.de(x, stellen)


def _vorrechnen():
    spec = importlib.util.spec_from_file_location("vorrechnen", ROOT / "tools" / "vorrechnen.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture(scope="module")
def netze():
    return {a: E.analysiere_netz(C.NETZ_HALLEN, a) for a in range(C.A_MIN, C.A_MAX + 1)}


@pytest.fixture(scope="module")
def saal():
    return E.analysiere_netz(C.NETZ_SAAL, 8)


@pytest.fixture(scope="module")
def streuungen():
    return {a: E.streuung(C.NETZ_HALLEN, a) for a in range(C.A_MIN, C.A_MAX + 1)}


def bruch(x, nenner):
    f = Fraction(x).limit_denominator(nenner)
    assert abs(float(f) - x) < 1e-9
    return f"{f.numerator}/{f.denominator}" if f.denominator > 1 else str(f.numerator)


def test_handnetz():
    g = N.handnetz(1)
    H = T.treffer_matrix(g)
    hpi = T.zeit_von_stationaer(g, H)
    steht(f"H(0,2) = {bruch(H[0, 2], 100)}, H(2,0) = {bruch(H[2, 0], 100)}; Türschritt H(2,3) = {bruch(H[2, 3], 100)}")
    steht(f"{AS.zahl_stimmiger_reihenfolgen(hpi)} von 720 Reihenfolgen")
    zz, mittel = T.zufallsziel(g, H)[0], T.mittlere_trefferzeit(H)
    steht(f"von jedem Start {bruch(zz, 100)} ≈ {d(zz)}; mittlere Trefferzeit über alle geordneten Paare {bruch(mittel, 100)} = {d(mittel)}")


def test_zweite_tuer_handnetz():
    an = E.analysiere_netz(C.NETZ_HAND, 8)
    e = E.ergaenze(an, (0, 5))
    steht(f"{e.anzahl_laenger} von {e.paare} Trefferzeiten länger (H(0,2): {bruch(an.H[0, 2], 100)} → {bruch(e.H2[0, 2], 100)}); H(0,5): {bruch(e.ab[0], 100)} → "
          f"{bruch(e.ab[1], 100)}; mittlere Trefferzeit {bruch(e.mittel[0], 100)} → {bruch(e.mittel[1], 100)}; Zeit zum stationär gezogenen Ziel "
          f"{bruch(e.zufallsziel[0], 100)} → {bruch(e.zufallsziel[1], 100)}")


def test_asymmetrie_hallen_und_saal(netze, saal):
    asy = {a: E.asymmetrie(an) for a, an in netze.items()}
    a8 = asy[8]
    steht(f"Median {d(a8['median'])}, 90-%-Quantil {d(a8['q90'])}, Maximum {d(a8['groesstes'])}")
    mediane = [x["median"] for x in asy.values()]
    maxima = [x["groesstes"] for x in asy.values()]
    steht(f"Median {d(min(mediane))} bis {d(max(mediane))}; 90-%-Quantil fällt von {d(asy[3]['q90'])} (a = 3) auf {d(asy[10]['q90'])} (a = 10); "
          f"Maximum {d(min(maxima), 1)} bis {d(max(maxima), 1)}")
    q = [asy[a]["q90"] for a in range(3, 11)]
    assert all(x >= y for x, y in zip(q, q[1:]))
    s = E.asymmetrie(saal)
    steht(f"Median-Verhältnis {d(s['median'])}, größtes {d(s['groesstes'], 0)}")
    f = a8["formel"]
    steht(f"Median-Fehler {p(f['roh'])}; mit bestem Vorfaktor {p(f['mit_faktor'])}; mit eigenem Wert je Zielgrad {p(f['mit_je_grad'])}")

    def spanne(key):
        werte = [round(100 * x["formel"][key]) for x in asy.values()]
        return f"{min(werte)} bis {max(werte)} %"

    steht(f"roh {spanne('roh')}; mit Vorfaktor {spanne('mit_faktor')}; mit Wert je Zielgrad {spanne('mit_je_grad')}")
    f = s["formel"]
    steht(f"{p(f['roh'])} / {p(f['mit_faktor'])} / {p(f['mit_je_grad'])}")


def test_reihungsregeln(netze, saal):
    z = {a: E.ordnung(an) for a, an in netze.items()}
    z8 = z[8]
    steht(f"von {E.ganz(z8['asymmetrisch'])} asymmetrischen Paaren haben {E.ganz(z8['gradgleich'])} ({p(z8['gradgleich'] / z8['asymmetrisch'])}) gleiche Grade")
    anteil = [round(100 * x["grad_richtig"] / x["grad_verschieden"]) for x in z.values()]
    steht(f"die Regel in {p(z8['grad_richtig'] / z8['grad_verschieden'])} richtig (a = 3 bis 10: {min(anteil)} bis {max(anteil)} %)")
    beide = [round(100 * x["beide_richtig"] / x["asymmetrisch"]) for x in z.values()]
    steht(f"{p(z8['beide_richtig'] / z8['asymmetrisch'], 1)} aller asymmetrischen Paare richtig, {z8['beide_offen']} bleiben offen (a = 3 bis 10: {min(beide)} bis {max(beide)} %)")
    steht(f"| nur der π-gewichtete Abstand, a = 8 | {p(z8['abstand_richtig'] / z8['asymmetrisch'], 1)} |")
    for x in list(z.values()) + [E.ordnung(saal), E.ordnung(E.analysiere_netz(C.NETZ_HAND, 8))]:
        assert x["hpi_richtig"] == x["asymmetrisch"]


def test_atlas_vollstaendig_neu():
    pytest.importorskip("networkx")
    at = _vorrechnen().atlas_zaehlung()
    gespeichert = D.laden()["atlas"]
    for key, wert in at.items():
        if isinstance(wert, float):
            assert wert == pytest.approx(gespeichert[key])
        elif key != "kleinstes_mit_laengerem_mittel":
            assert wert == gespeichert[key], key
    n = E.ganz(at["ergaenzungen"])
    steht(f"Alle {n} Ergänzungen der {at['graphen']} zusammenhängenden", f"mindestens eine Trefferzeit länger in {E.ganz(at['mindestens_eins_laenger'])} Fällen",
          f"zwischen den Endpunkten nie länger oder gleich ({at['endpunkte_nicht_kuerzer']} Fälle)")
    kl = at["kleinstes_mit_laengerem_mittel"]
    steht(f"mittlere Trefferzeit länger in {E.ganz(at['mittel_laenger'])} Fällen ({p(at['mittel_laenger'] / at['ergaenzungen'], 1)}), Zeit zum stationär gezogenen Ziel länger in "
          f"{at['zufallsziel_laenger']} ({p(at['zufallsziel_laenger'] / at['ergaenzungen'], 1)}); größter Faktor einer Trefferzeit {d(at['groesster_faktor'])}; "
          f"kleinstes Netz mit längerer mittlerer Trefferzeit: {kl['knoten']} Plätze, {d(kl['vorher'])} → {d(kl['nachher'], 3)}")
    steht(f"{p(at['mittlerer_anteil_je_ergaenzung'], 1)} als Mittel der Anteile je Ergänzung, {p(at['paare_laenger'] / at['paare'], 1)} über alle {E.ganz(at['paare'])} Paare zusammen")
    assert at["mindestens_eins_laenger"] == at["ergaenzungen"] and at["endpunkte_nicht_kuerzer"] == 0


def test_zweite_tuer_hallen(netze):
    anteile, faktoren = [], []
    mittel8, faktor8 = [], []
    for a, an in netze.items():
        for z in E.zeilen_sweep(an):
            anteile.append(round(100 * z["anteil_laenger"]))
            faktoren.append(z["faktor"])
            assert z["mittel"] < an.mittel and z["ab_nach"] < z["ab_vor"]
            if a == 8:
                mittel8.append(z["mittel"])
                faktor8.append(z["faktor"])
    steht(f"{min(anteile)} bis {max(anteile)} % der geordneten Paare länger",
          f"(a = 8: {d(netze[8].mittel, 0)} → {d(min(mittel8), 0)} bis {d(max(mittel8), 0)}); größter Faktor bis {d(max(faktoren), 1)} (a = 8: bis {d(max(faktor8), 1)})")
    r0 = E.zeilen_sweep(netze[8])[0]
    assert r0["r"] == 0
    steht(f"zwischen ihren Endpunkten {d(r0['ab_vor'], 0)} → {d(r0['ab_nach'], 0)}")


def test_freie_kanten_a3_bis_a5(netze):
    anteile, anzahlen = [], []
    for a in (3, 4, 5):
        an = netze[a]
        laenger = [T.mittlere_trefferzeit(T.treffer_matrix(N.mit_kante(an.g, u, v))) > an.mittel * (1 + 1e-9) for u, v in N.fehlende_kanten(an.g)]
        anteile.append(p(np.mean(laenger)).replace(" %", " %"))
        anzahlen.append(E.ganz(len(laenger)))
    steht(f"in {', '.join(anteile)} der Fälle länger ({', '.join(anzahlen)} Ergänzungen)")


def test_schlussstein():
    for n in (4, 6, 8, 20, 30):
        s = E.schlussstein(n)
        assert s["vorher"] == pytest.approx(1) and s["nachher"] == pytest.approx(n - 1)
    steht("wird von 1 zu n − 1")


def _kappe(g, u, v, h, c):
    e, pr = AB.gedeckelt(g, u, v, AB.abbruch_schritt(c, h))
    return e / h, pr, e / (1 - pr) / h


def test_streuung_hallen(netze, streuungen):
    mediane = [s.cv_median for s in streuungen.values()]
    vorgaben = [AB.laeufe_vorgabe(m) for m in mediane]
    steht(f"Median {d(min(mediane))} bis {d(max(mediane))} ({min(vorgaben)} bis {max(vorgaben)} Läufe)")
    st8 = streuungen[8]
    u, v = st8.cv_paar
    g = netze[8].g
    assert (g.knoten[u], g.knoten[v]) == ("L(1,0)", "L(1,1)")
    h = st8.H[u, v]
    anteil, pr, zens = _kappe(g, u, v, h, 3)
    steht(f"H = {d(h)}, CV {d(st8.CV[u, v])}, {E.ganz(AB.laeufe_vorgabe(st8.CV[u, v]))} Läufe; Abbruch nach 3·H: {p(pr, 1)} abgebrochen, Erwartungswert {p(anteil, 1)} des Mittels "
          f"(zensurbewusst {p(zens, 1)}); nach 10·H: {p(_kappe(g, u, v, h, 10)[0], 1)}")
    werte = {}
    for a in (3, 10):
        u, v = streuungen[a].cv_paar
        werte[a] = _kappe(netze[a].g, u, v, streuungen[a].H[u, v], 3)
    steht(f"{p(werte[3][0], 1)} des Mittels bei {p(werte[3][1], 1)} abgebrochen (a = 3); {p(werte[10][0], 1)} bei {p(werte[10][1], 1)} (a = 10)")
    orte = {a: tuple(netze[a].g.knoten[i] for i in streuungen[a].cv_paar) for a in netze}
    assert orte[3] == ("L(0,0)", "L(1,0)")
    assert all(orte[a] == ("L(0,0)", "L(0,1)") for a in (4, 5, 6)) and all(orte[a] == ("L(1,0)", "L(1,1)") for a in (7, 8, 9, 10))
    steht("a = 3: L(0,0) → L(1,0); a = 4 bis 6: L(0,0) → L(0,1); a = 7 bis 10: L(1,0) → L(1,1)")
    tu, tv = N.hallenknoten(8, 0, 4, 7), N.hallenknoten(8, 1, 4, 0)
    steht(f"H = {d(st8.H[tu, tv], 0)}, CV {d(st8.CV[tu, tv])}, {AB.laeufe_vorgabe(st8.CV[tu, tv])} Läufe")


def test_streuung_saal_und_handnetz(saal):
    s = E.streuung(C.NETZ_SAAL, 8)
    u, v = s.cv_paar
    assert (saal.g.knoten[u], saal.g.knoten[v]) == ("G10", "G11")
    h = s.H[u, v]
    anteil, pr, zens = _kappe(saal.g, u, v, h, 3)
    steht(f"H = {d(h, 0)}, CV {d(s.CV[u, v])}, {E.ganz(AB.laeufe_vorgabe(s.CV[u, v]))} Läufe; Abbruch nach 3·H: {p(anteil, 1)} des Mittels bei {p(pr, 1)} abgebrochen "
          f"(zensurbewusst {p(zens, 1)}); nach 10·H: {p(_kappe(saal.g, u, v, h, 10)[0], 1)}")
    steht(f"bleiben 42 % bzw. {p(anteil)} des Mittels")
    hand = N.handnetz(1)
    hv, cv = AB.momente_zu_ziel(hand, 1)
    e14, p14 = AB.gedeckelt(hand, 0, 1, 14)
    e47, _ = AB.gedeckelt(hand, 0, 1, 47)
    steht(f"H = {bruch(hv[0], 100)}, CV {d(cv[0])}, {E.ganz(AB.laeufe_vorgabe(cv[0]))} Läufe; Abbruch nach 14 Schritten (3·H): {p(e14 / hv[0], 1)} bei {p(p14, 1)} "
          f"abgebrochen; nach 47 Schritten: {p(e47 / hv[0], 1)}")


def test_ferne_ecken_und_alle_paare():
    ecken = E.eckpaare()
    steht(f"Handnetz 0 → 5: {p(ecken[0]['anteil'], 1)}; Gitter 8×8 Ecke zur Gegenecke: {p(ecken[1]['anteil'], 1)}; zwei Hallen 8×8 L(0,0) → R(7,7): {p(ecken[2]['anteil'], 1)}; "
          f"abgebrochen {d(100 * min(z['abbruch'] for z in ecken), 1)} bis {p(max(z['abbruch'] for z in ecken), 1)}")
    tab = _vorrechnen().abstand_tabelle()
    gespeichert = D.laden()["abstand"]
    assert tab["durchmesser"] == gespeichert["durchmesser"]
    for neu, alt in zip(tab["zeilen"], gespeichert["zeilen"]):
        for key in neu:
            assert neu[key] == pytest.approx(alt[key]), key
    z = {x["abstand_mindestens"]: x["kleinster_anteil"] for x in tab["zeilen"]}
    steht(f"kleinster Anteil ab Abstand 4: {p(z[4], 1)}; ab 8: {p(z[8], 1)}; ab 10: {p(z[10], 1)}; ab 12: {p(z[12], 1)}; ab 14: {p(z[14], 1)}; "
          f"ab 15 (Durchmesser {tab['durchmesser']}): {p(z[15], 1)}")
    assert z[14] < 0.96 < z[15]        # „erst ab Abstand 15 liegt jedes Paar über 96 %“


def test_deckungsgrad_neu_gerechnet():
    """Alle 20 Fälle mit denselben Zufalls-Seeds neu; Band statt Bitgleichheit, weil die Verteilungsfunktion aus Gleitkomma-Matrizen stammt."""
    v = _vorrechnen()
    gespeichert = D.laden()["deckung"]
    faelle = v.deckung_faelle()
    assert len(faelle) == len(gespeichert) == 20
    anteile = []
    for i, (fall, alt) in enumerate(zip(faelle, gespeichert)):
        neu = v.deckung_fall(i, *fall)
        assert (neu["netz"], neu["a"], neu["paar"], neu["u"], neu["v"], neu["laeufe"]) == (alt["netz"], alt["a"], alt["paar"], alt["u"], alt["v"], alt["laeufe"])
        assert neu["anteil"] == pytest.approx(alt["anteil"], abs=0.003)
        anteile.append(alt["anteil"])
    steht(f"20 Fälle, je {E.ganz(C.DECKUNG_WIEDERHOLUNGEN)} Wiederholungen", f"in {p(min(anteile), 1)} bis {p(max(anteile), 1)} der Wiederholungen")


def test_streuung_der_abbruchschaetzer():
    neu = _vorrechnen().streuung_tabelle()
    alt = D.laden()["streuung"]
    for n_, a_ in zip(neu["zeilen"], alt["zeilen"]):
        assert n_["gekappt"] == pytest.approx(a_["gekappt"], abs=0.005)
        assert n_["zensurbewusst"] == pytest.approx(a_["zensurbewusst"], abs=0.005)
    z = {x["laeufe"]: x["gekappt"] for x in alt["zeilen"]}
    steht(f"100 Läufe: der Schätzer mit Abbruch liegt in 90 % der Wiederholungen zwischen {p(z[100][0])} und {p(z[100][2])} von H; 5 000 Läufe: zwischen "
          f"{p(z[5000][0])} und {p(z[5000][2])}")


def test_vorgerechnete_datei_ist_vollstaendig():
    daten = json.loads((ROOT / "daten" / "vorgerechnet.json").read_text(encoding="utf-8"))
    assert {"atlas", "abstand", "deckung", "streuung"} <= set(daten)


def test_testzahl_in_der_readme(request):
    """Die README nennt die Gesamtzahl der gesammelten Tests (nur geprüft, wenn die ganze Suite gesammelt wurde)."""
    items = request.session.items
    if len({i.path.name for i in items}) < len(list((ROOT / "tests").glob("test_*.py"))):
        pytest.skip("nur beim Lauf der ganzen Suite")
    steht(f"**Testzahl:** {len(items)} Tests.")
