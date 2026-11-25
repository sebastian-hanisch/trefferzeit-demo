"""Layout (DEMO-PLAYBOOK §2): fester Kopf, Schnellstart oben in der Seitenleiste, aktives Preset hervorgehoben.

Die Hervorhebung ist zustandslos (`aktives_preset` vergleicht jeden Regler aus SETTING_SPECS mit dem Preset). Der Test unten stellt
sicher, dass wirklich JEDER Regler der Seitenleiste dort steht: sonst bliebe das Preset trotz Änderung markiert. Gesperrte Regler lassen sich auch in AppTest nicht
bedienen, deshalb startet jeder Regler von einem Preset aus, in dem er wirksam ist."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import trz_constants as C
import trz_presets as P

APP = str(Path(__file__).resolve().parent.parent / "app.py")
REGLER_ARTEN = ("slider", "number_input", "select_slider", "selectbox", "radio", "toggle", "checkbox", "text_input")

# Preset, in dem der Regler wirkt, und ein anderer Wert als der Preset-Wert
FALL = {
    "netz": ("Handnetz zwei Hallen", "hallen"), "a": ("Zwei Hallen, eine Tür", 5), "u": ("Zwei Hallen, eine Tür", 0), "v": ("Zwei Hallen, eine Tür", 0),
    "kante": ("Zwei Hallen, eine Tür", "frei"), "r": ("Zwei Hallen, eine Tür", 2), "ka": ("Saal mit Stichgang 21 + 11 (Kontrast)", 1),
    "kb": ("Saal mit Stichgang 21 + 11 (Kontrast)", 30), "paar": ("Handnetz zwei Hallen", "tuer"), "laeufe": ("Handnetz zwei Hallen", 100),
    "abbruch": ("Handnetz zwei Hallen", "ohne"), "seed": ("Handnetz zwei Hallen", 7),
}


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _typen(at) -> dict:
    """Button-Typ je Preset-Name (die Preset-Buttons der Seitenleiste)."""
    return {b.label: b.proto.type for b in at.sidebar.button if b.label in C.PRESETS}


def _regler(at, key):
    for art in REGLER_ARTEN:
        try:
            return getattr(at.sidebar, art)(key=key)
        except KeyError:
            continue
    raise AssertionError(f"Regler {key} steht nicht in der Seitenleiste")


def test_presets_stehen_in_der_seitenleiste_und_nicht_im_hauptbereich():
    at = _app()
    assert [b.label for b in at.sidebar.button][: len(C.PRESETS)] == list(C.PRESETS)  # die ersten Buttons der Seitenleiste
    assert not [b for b in at.main.button if b.label in C.PRESETS]


def test_titel_steht_im_festen_kopf():
    at = _app()
    assert "st-key-kopf" in " ".join(h.proto.body for h in at.get("html"))  # das Stylesheet setzt an der Klasse des Containers an
    assert at.title[0].value


def test_beim_start_ist_genau_das_standard_preset_hervorgehoben():
    typen = _typen(_app())
    assert [name for name, typ in typen.items() if typ == "primary"] == [next(iter(C.PRESETS))]


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_angeklicktes_preset_ist_hervorgehoben_und_bleibt_es_im_naechsten_lauf(name):
    at = _app()
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert [n for n, typ in _typen(at).items() if typ == "primary"] == [name]
    at.run()
    assert [n for n, typ in _typen(at).items() if typ == "primary"] == [name]


def test_jeder_regler_der_seitenleiste_steht_in_setting_specs():
    at = _app()
    schluessel = {w.key for art in REGLER_ARTEN for w in getattr(at.sidebar, art) if w.key}
    assert schluessel == set(P.SETTING_SPECS) == set(FALL)


@pytest.mark.parametrize("state_key", list(P.SETTING_SPECS))
def test_jede_aenderung_eines_reglers_hebt_die_hervorhebung_auf(state_key):
    preset, neu = FALL[state_key]
    at = _app()
    at.sidebar.button(key=f"preset_{preset}").click().run()
    regler = _regler(at, state_key)
    assert not regler.disabled and regler.value != neu
    regler.set_value(neu).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert "primary" not in _typen(at).values()
    # erneutes Anklicken markiert wieder
    at.sidebar.button(key=f"preset_{preset}").click().run()
    assert _typen(at)[preset] == "primary"
