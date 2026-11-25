"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen, jedes Preset zeigt seinen Fall."""

import trz_constants as C
import trz_evaluation as E
import trz_presets as P
import trz_szenario as S


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_valid_for_their_net():
    for name, p in C.PRESETS.items():
        for key, spec in P.SETTING_SPECS.items():
            if spec.options is not None:
                assert p[key] in spec.options, (name, key)
            elif spec.lo is not None:
                assert spec.lo <= p[key] <= spec.hi, (name, key)
        n = C.anzahl_knoten(p["netz"], p["a"])
        assert all(0 <= p[k] < n for k in ("u", "v", "ka", "kb")), name
        assert p["r"] in S.tuerzeilen_neu(p["netz"], p["a"]), name
        assert S.neue_kante(p["netz"], p["a"], p["kante"], p["r"], p["ka"], p["kb"])[0] is not None, name
        assert (p["laeufe"] - C.LAEUFE_MIN) % C.LAEUFE_STEP == 0


def test_presets_sind_verschieden():
    werte = [tuple(sorted(p.items())) for p in C.PRESETS.values()]
    assert len(set(werte)) == len(werte)


def test_default_preset_equals_the_default_settings():
    standard = C.PRESETS["Handnetz zwei Hallen"]
    assert next(iter(C.PRESETS)) == "Handnetz zwei Hallen"
    assert E.Settings(**standard) == E.Settings()
    assert {k: standard[k] for k in ("u", "v", "ka", "kb")} == C.knoten_standard(C.NETZ_HAND, 8) | {"u": 0, "v": 2}


def test_setting_specs_cover_every_preset_key():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)


def test_einrasten_der_adresszeile():
    assert P._eingerastet(P.SETTING_SPECS["laeufe"], 1234) == 1250
    assert P._eingerastet(P.SETTING_SPECS["laeufe"], 10**9) == C.LAEUFE_MAX
    assert P._eingerastet(P.SETTING_SPECS["a"], 99) == C.A_MAX
    assert P._eingerastet(P.SETTING_SPECS["netz"], "mond") is None
    assert P._eingerastet(P.SETTING_SPECS["abbruch"], "4") is None


def test_preset_hallen_eine_tuer_zeigt_ecke_und_tuerknoten():
    p = C.PRESETS["Zwei Hallen, eine Tür"]
    g = S.netz_fuer(p["netz"], p["a"])
    assert (g.knoten[p["u"]], g.knoten[p["v"]]) == ("L(7,7)", "L(4,7)")


def test_preset_eine_tuer_mehr_zeigt_die_endpunkte_der_neuen_tuer():
    p = C.PRESETS["Eine Tür mehr"]
    assert S.neue_kante(p["netz"], p["a"], p["kante"], p["r"], p["ka"], p["kb"])[0] == (p["u"], p["v"])
