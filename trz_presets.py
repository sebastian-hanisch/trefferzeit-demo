"""Permalink (Begrenzen, Einrasten), Presets, Netzwechsel und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio).

Jeder Regler der Seitenleiste hat einen Eintrag in SETTING_SPECS. Werte aus der Adresszeile werden begrenzt (Zahlen) oder verworfen (unbekannte Auswahl).
Start, Ziel, Türzeile und freie Kante hängen am Netz: bei einem Netzwechsel setzt ein Callback sie auf die Standardwerte des Netzes, und `passe_netzregler_an`
hält sie vor dem Zeichnen im gültigen Bereich."""

import random
from dataclasses import dataclass

import streamlit as st

import trz_constants as C
import trz_szenario as S


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: type
    default: object
    lo: float | None = None
    hi: float | None = None
    options: tuple | None = None      # erlaubte Werte (Auswahllisten und Stufen)
    step: int = 1


_STANDARD = C.PRESETS[next(iter(C.PRESETS))]
_KNOTEN_MAX = 2 * C.A_MAX * C.A_MAX - 1

SETTING_SPECS = {
    "netz": SettingSpec("netz", str, _STANDARD["netz"], options=C.NETZE),
    "a": SettingSpec("a", int, _STANDARD["a"], C.A_MIN, C.A_MAX),
    "u": SettingSpec("u", int, _STANDARD["u"], 0, _KNOTEN_MAX),
    "v": SettingSpec("v", int, _STANDARD["v"], 0, _KNOTEN_MAX),
    "kante": SettingSpec("kante", str, _STANDARD["kante"], options=C.KANTEN_ARTEN),
    "r": SettingSpec("r", int, _STANDARD["r"], 0, C.A_MAX - 1),
    "ka": SettingSpec("ka", int, _STANDARD["ka"], 0, _KNOTEN_MAX),
    "kb": SettingSpec("kb", int, _STANDARD["kb"], 0, _KNOTEN_MAX),
    "paar": SettingSpec("paar", str, _STANDARD["paar"], options=C.PAARE),
    "laeufe": SettingSpec("laeufe", int, _STANDARD["laeufe"], C.LAEUFE_MIN, C.LAEUFE_MAX, step=C.LAEUFE_STEP),
    "abbruch": SettingSpec("c", str, _STANDARD["abbruch"], options=C.ABBRUCH_STUFEN),
    "seed": SettingSpec("seed", int, _STANDARD["seed"], 0, C.SEED_MAX),
}
PRESET_KEYS = {key: key for key in SETTING_SPECS}


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def _eingerastet(spec: SettingSpec, wert):
    """Wert auf Grenzen begrenzt und auf die Schrittweite eingerastet; unbekannte Auswahl gibt None."""
    if spec.options is not None:
        return wert if wert in spec.options else None
    if spec.step > 1:
        wert = spec.lo + round((wert - spec.lo) / spec.step) * spec.step
    if spec.lo is not None:
        wert = max(spec.lo, wert)
    if spec.hi is not None:
        wert = min(spec.hi, wert)
    return wert


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen. Nennt die Adresszeile nur das Netz (oder die Hallengröße), gelten dessen Standardplätze."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    gelesen = {}
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                wert = _eingerastet(spec, spec.caster(qp[spec.url_param]))
            except (ValueError, TypeError):
                continue
            if wert is not None:
                gelesen[state_key] = wert
    st.session_state.update(gelesen)
    if "netz" in gelesen or "a" in gelesen:
        netz = gelesen.get("netz", SETTING_SPECS["netz"].default)
        standard = C.knoten_standard(netz, gelesen.get("a", C.DEFAULT_A))
        for key, wert in standard.items():
            if key not in gelesen:
                st.session_state[key] = wert
        if "netz" in gelesen and "kante" not in gelesen and not S.hat_zweite_tuer(netz):
            st.session_state["kante"] = C.KANTE_FREI
    st.session_state["permalink_loaded"] = True


def passe_netzregler_an():
    """Vor dem Zeichnen: Werte, die im aktuellen Netz nicht existieren, auf dessen Standard setzen; die Zuweisung hält die Auswahl auch dann, wenn sich die
    Optionen eines Auswahlfelds ändern."""
    netz, a = st.session_state["netz"], int(st.session_state["a"])
    n = C.anzahl_knoten(netz, a)
    standard = C.knoten_standard(netz, a)
    for key in ("u", "v", "ka", "kb"):
        wert = int(st.session_state[key])
        st.session_state[key] = wert if 0 <= wert < n else standard[key]
    zeilen = S.tuerzeilen_neu(netz, a)
    st.session_state["r"] = st.session_state["r"] if st.session_state["r"] in zeilen else zeilen[0]


def netz_gewechselt():
    """Callback des Netzes: Start, Ziel und freie Kante auf die Standardplätze; die Art der neuen Kante auf „zweite Tür“, wo es eine gibt."""
    netz, a = st.session_state["netz"], int(st.session_state["a"])
    st.session_state.update(C.knoten_standard(netz, a))
    st.session_state["kante"] = C.KANTE_TUER if S.hat_zweite_tuer(netz) else C.KANTE_FREI


def groesse_gewechselt():
    """Callback der Hallengröße: nur auf den Gitterhallen ändern sich die Plätze."""
    if st.session_state["netz"] == C.NETZ_HALLEN:
        st.session_state.update(C.knoten_standard(C.NETZ_HALLEN, int(st.session_state["a"])))


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        if key in C.PRESETS[name]:
            st.session_state[state_key] = C.PRESETS[name][key]


def aktives_preset():
    """Name des Presets, dessen Werte GENAU den aktuellen Einstellungen entsprechen, sonst None.

    Zustandslos: verglichen wird jeder Regler aus SETTING_SPECS (ein Preset ohne Eintrag für einen Regler meint dessen
    Standardwert) mit dem Session State. Ein später ergänzter Regler braucht nur seinen Eintrag in SETTING_SPECS,
    dann hebt auch seine Änderung die Markierung auf (tests/test_layout.py prüft das für jeden Regler)."""
    preset_key_of = {state_key: key for key, state_key in PRESET_KEYS.items()}
    for name, preset in C.PRESETS.items():
        if all(
            st.session_state.get(state_key, spec.default) == preset.get(preset_key_of.get(state_key), spec.default)
            for state_key, spec in SETTING_SPECS.items()
        ):
            return name
    return None


def sidebar_presets():
    """Schnellstart oben in der Seitenleiste; das aktive Preset ist hervorgehoben (`type="primary"`)."""
    if not C.PRESETS:
        return
    st.header("🎯 Schnellstart")
    st.caption("Ein Beispielszenario laden:")
    aktiv = aktives_preset()
    for name in C.PRESETS:
        st.button(
            name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
            type="primary" if aktiv == name else "secondary",
        )


def randomize_seed():
    st.session_state["seed"] = random.randint(0, C.SEED_MAX)
