"""End-to-end mit AppTest: Standard, jeder Button, jeder wirksame Schieberegler an Minimum und Maximum, jedes Preset mit seiner Verdikt-Zeile, Permalink,
Auswahlregler, Netzwechsel und Randfälle."""

import os

import pytest
from streamlit.testing.v1 import AppTest

import trz_constants as C

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "180"))


def _fresh(**query) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    for k, v in query.items():
        at.query_params[k] = str(v)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _texte(at, *arten) -> str:
    arten = arten or ("success", "info", "warning", "error", "markdown", "caption")
    return " ".join(str(e.value) for kind in arten for e in getattr(at, kind))


def _ok(at):
    assert not at.exception, [str(e) for e in at.exception]
    assert not at.error, [e.value for e in at.error]


def _experimente(at):
    return [s.value for s in at.subheader if s.value.startswith("🔬")]


def test_standard_zeigt_alle_vier_experimente():
    at = _fresh()
    _ok(at)
    assert len(_experimente(at)) == 4
    assert "von 0 nach 2 im Mittel 2,00" in _texte(at, "warning")
    assert "48" in _texte(at, "markdown") and "6 von 30" in _texte(at, "info")


def test_jeder_button_ohne_fehler():
    labels = [b.label for b in _fresh().button]
    for index in range(len(labels)):
        at = _fresh()
        at.button[index].click().run(timeout=TIMEOUT)
        _ok(at)


@pytest.mark.parametrize("preset", ["Zwei Hallen, eine Tür", "Saal mit Stichgang 21 + 11 (Kontrast)"])
def test_schieberegler_an_den_grenzen(preset):
    at = _fresh()
    at.sidebar.button(key=f"preset_{preset}").click().run()
    for key in [s.key for s in at.slider if not s.disabled]:
        for rand in ("min", "max"):
            at = _fresh()
            at.sidebar.button(key=f"preset_{preset}").click().run()
            schieber = at.slider(key=key)
            schieber.set_value(int(getattr(schieber, rand))).run(timeout=TIMEOUT)
            _ok(at)


def test_alle_minima_und_alle_maxima_zusammen():
    for werte in ({"a": C.A_MIN, "laeufe": C.LAEUFE_MIN, "seed": 0}, {"a": C.A_MAX, "laeufe": C.LAEUFE_MAX, "seed": C.SEED_MAX}):
        _ok(_fresh(netz="hallen", **werte))


ERWARTET = {
    "Handnetz zwei Hallen": ["von 0 nach 2 im Mittel 2,00", "Median-Verhältnis 1,59", "kein asymmetrisches Paar offen", "6 von 30", "Nur 8,7 %", "74 %"],
    "Zwei Hallen, eine Tür": ["von L(7,7) nach L(4,7) im Mittel 110,4", "Median-Verhältnis 1,25", "46 %", "91 %", "4 146 von 16 256", "9,9 %", "83 %"],
    "Eine Tür mehr": ["gleich lang: je 996,4", "4 146 von 16 256", "6,9 %", "42 %"],
    "Probeläufe mit Abbruch": ["Nur 6,9 %", "nur 42 %", "58 % fehlen", "45 %", "7,0 % ab, und es bleiben 26 %", "5 940", "95,3 %"],
    "Saal mit Stichgang 21 + 11 (Kontrast)": ["Median-Verhältnis 13,91", "436 von 992", "Nur 7,0 %", "26 %", "27 %", "7 721", "besten Vorfaktor bleiben 55 %"],
}


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_jedes_preset_mit_seinen_verdikten(name):
    at = _fresh()
    at.sidebar.button(key=f"preset_{name}").click().run(timeout=TIMEOUT)
    _ok(at)
    assert len(_experimente(at)) == 4
    verdikte = _texte(at, "success", "info", "warning")
    for teil in ERWARTET[name]:
        assert teil in verdikte, (name, teil)


def test_saalvergleich_nur_beim_belegten_fall():
    at = _fresh()
    at.sidebar.button(key="preset_Probeläufe mit Abbruch").click().run()
    at.sidebar.select_slider(key="abbruch").set_value("5").run()
    assert "Der Abbruchanteil sagt nicht" not in _texte(at, "success", "info", "warning")


def test_permalink_laedt_netz_mit_standardplaetzen():
    at = _fresh(netz="hallen", a=6)
    assert at.session_state["netz"] == "hallen" and at.session_state["a"] == 6
    std = C.knoten_standard("hallen", 6)
    assert (at.session_state["u"], at.session_state["v"]) == (std["u"], std["v"])
    at = _fresh(netz="saal")
    assert at.session_state["kante"] == "frei" and at.session_state["u"] == 30
    at = _fresh(netz="hallen", a=3, u=500, v=1, r=1, c="4", laeufe=123)
    assert at.session_state["u"] == C.knoten_standard("hallen", 3)["u"]       # außerhalb des Netzes: Standardplatz
    assert at.session_state["v"] == 1 and at.session_state["r"] == 0           # Zeile 1 ist die vorhandene Tür
    assert at.session_state["abbruch"] == "3" and at.session_state["laeufe"] == 100
    _ok(at)


def test_adresszeile_spiegelt_die_regler():
    at = _fresh()
    at.sidebar.number_input(key="seed").set_value(42).run()
    assert str(at.query_params["seed"]).strip("[]'") == "42"


@pytest.mark.parametrize("key,optionen", [("netz", C.NETZE), ("paar", C.PAARE), ("abbruch", C.ABBRUCH_STUFEN)])
def test_jede_option_der_auswahlregler(key, optionen):
    for option in optionen:
        at = _fresh()
        regler = at.sidebar.select_slider(key=key) if key == "abbruch" else at.sidebar.selectbox(key=key)
        regler.set_value(option).run()
        _ok(at)


def test_netzwechsel_setzt_standardplaetze():
    at = _fresh()
    at.sidebar.selectbox(key="netz").set_value("saal").run()
    _ok(at)
    assert (at.session_state["u"], at.session_state["v"], at.session_state["kante"]) == (30, 31, "frei")
    at.sidebar.selectbox(key="netz").set_value("hallen").run()
    assert (at.session_state["u"], at.session_state["v"], at.session_state["kante"]) == (63, 39, "tuer")
    at.sidebar.slider(key="a").set_value(3).run()
    _ok(at)
    assert (at.session_state["u"], at.session_state["v"], at.session_state["r"]) == (8, 5, 0)


def test_start_gleich_ziel_und_ungueltige_kante():
    at = _fresh()
    at.sidebar.selectbox(key="u").set_value(2).run()
    _ok(at)
    assert "derselbe Platz" in _texte(at, "info")
    at.sidebar.selectbox(key="paar").set_value("gewaehlt").run()
    _ok(at)
    assert "ein anderes Paar" in _texte(at, "info")
    at.sidebar.radio(key="kante").set_value("frei").run()
    at.sidebar.selectbox(key="kb").set_value(1).run()
    _ok(at)
    assert "schon verbunden" in _texte(at, "info")


def test_ansicht_anteil_und_weg_mit_schlussstein():
    at = _fresh()
    at.radio(key="kartenansicht").set_value("je Start: Anteil länger gewordener Ziele").run()
    _ok(at)
    at.toggle(key="schlussstein").set_value(True).run()
    _ok(at)
    at.slider(key="weg_n").set_value(20).run()
    _ok(at)
    werte = {m.label: m.value for m in at.metric}
    assert werte["Weg: H(Ende, Nachbar)"] == "1,00" and werte["mit Schlussstein: derselbe Weg"] == "19,00"


def test_erzwungener_schritt_ohne_fehlbetrag_und_in_der_einzahl():
    """Saal, G11 → G10: T = 1 sicher. Kernfrage 4 nennt keinen Fehlbetrag und schreibt „1 Lauf“."""
    for abbruch in ("1", "3", "ohne"):
        at = _fresh(netz="saal", u=31, v=30, paar="gewaehlt", abbruch=abbruch)
        _ok(at)
        text = _texte(at)
        assert "sieht die Normalnäherung 1 Lauf für ±10 %" in text and "1 Läufe" not in text
        assert "systematischen Fehlbetrag" not in text and "trifft keinen Lauf" in text


def test_grosse_paare_werden_gekuerzt():
    at = _fresh(netz="hallen", a=10, u=0, v=199, paar="gewaehlt", laeufe=5000)
    _ok(at)
    assert "Gekürzt auf" in _texte(at, "info")
