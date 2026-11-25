"""Hin ist nicht zurück - Trefferzeit einer Irrfahrt auf Netzen - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Wie viele Schritte braucht eine Irrfahrt auf einem Netz im Mittel von u nach v? Hin und zurück, eine Reihenfolge für alle Paare, eine neue Kante und das Schätzen
durch Probeläufe mit Abbruch. Aufbau und Regeln stehen im DEMO-PLAYBOOK.md (§2).

Lauffähig mit: streamlit run app.py
"""

import math

import streamlit as st

import trz_constants as C
import trz_daten as D
import trz_evaluation as E
import trz_netze as N
import trz_szenario as S
from trz_layout import dunkles_design, kopf_css
from trz_presets import (
    bounds,
    groesse_gewechselt,
    init_session_state_defaults,
    load_permalink_settings,
    netz_gewechselt,
    passe_netzregler_an,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)
from trz_visualization import (
    abbruch_text,
    histogramm_laufzeiten,
    histogramm_verhaeltnisse,
    karte_aenderung,
    karte_anteil,
    karte_hpi,
    karte_paar,
    karte_weg,
)

st.set_page_config(page_title="Hin ist nicht zurück – Sebastian Hanisch", layout="wide")

KLICK_START, KLICK_ZIEL = "Start u", "Ziel v"
ANSICHT_ZIEL, ANSICHT_ANTEIL = "Weg zum Ziel v", "je Start: Anteil länger gewordener Ziele"


@st.cache_data(show_spinner=False)
def _netz(netz, a):
    return E.analysiere_netz(netz, a)


@st.cache_data(show_spinner=False)
def _asymmetrie(netz, a):
    return E.asymmetrie(_netz(netz, a))


@st.cache_data(show_spinner=False)
def _ordnung(netz, a):
    return E.ordnung(_netz(netz, a))


@st.cache_data(show_spinner=False)
def _ergaenzung(netz, a, kante):
    return E.ergaenze(_netz(netz, a), kante)


@st.cache_data(show_spinner=False)
def _zeilen_sweep(netz, a):
    return E.zeilen_sweep(_netz(netz, a))


@st.cache_data(show_spinner=False)
def _streuung(netz, a):
    return E.streuung(netz, a)


@st.cache_data(show_spinner=False)
def _probe(netz, a, u, v, abbruch):
    return E.probe_exakt(_netz(netz, a).g, _streuung(netz, a), u, v, abbruch)


@st.cache_data(show_spinner=False)
def _simulation(netz, a, u, v, laeufe, seed, K):
    return E.simuliere(_netz(netz, a).g, u, v, laeufe, seed, K)


@st.cache_data(show_spinner=False)
def _eckpaare():
    return E.eckpaare()


@st.cache_data(show_spinner=False)
def _saal_vergleich():
    return E.saal_vergleich()


@st.cache_data(show_spinner=False)
def _daten():
    return D.laden()


def _karte_geklickt():
    """Klick auf einen Platz der Hauptkarte setzt Start oder Ziel (je nach Auswahl darüber)."""
    auswahl = st.session_state.get("hauptkarte")
    punkte = auswahl["selection"]["points"] if auswahl else []
    if punkte and punkte[0].get("customdata") is not None:
        wert = punkte[0]["customdata"]
        wert = wert[0] if isinstance(wert, (list, tuple)) else wert
        st.session_state["u" if st.session_state.get("klickziel", KLICK_START) == KLICK_START else "v"] = int(wert)


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in trz_layout.py).
st.html(kopf_css(dunkles_design()))
st.html('<style>[data-testid="stMarkdownContainer"] table { display: block; overflow-x: auto; max-width: 100%; }</style>')   # breite Tabellen scrollen auf dem Telefon
with st.container(key="kopf"):
    st.title("🚶 Hin ist nicht zurück – Trefferzeit einer Irrfahrt auf Netzen")
st.markdown(
    """
Eine **Irrfahrt** (random walk) geht in jedem Schritt von ihrem Platz zu einem zufällig gewählten Nachbarn, jeder gleich wahrscheinlich. Die **Trefferzeit** (hitting time)
H(u,v) ist die erwartete Zahl der Schritte, bis sie von u aus zum ersten Mal v erreicht. Auf einem ungerichteten Netz ist der Hinweg im Allgemeinen **nicht so lang wie der
Rückweg**, und trotzdem lassen sich alle Plätze **widerspruchsfrei reihen**. Die Demo zeigt außerdem, was **eine neue Kante** ändert und warum **Probeläufe mit Abbruch**
den Mittelwert verfälschen. Die Trefferzeiten kommen aus Gleichungssystemen (ohne Zufall, bis auf Rundung); die Simulation steht daneben.

Direkt darunter erklärt **💬 In einfachen Worten** die Idee ohne Formeln. Weiter unten: **❓ Kernfragen**, vier **🔬 Experimente**, **🚧 Wo die Annahmen enden** und die Expander **⚠️ Annahmen, Grenzen und bekannte Probleme** und
**📐 Mathematische Formulierung**.
"""
)

# erklaerseite:einfach:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/hin-ist-nicht-zurueck-erklaert.json, nicht von Hand ändern)
with st.expander("💬 In einfachen Worten"):
    st.markdown(
        """
Eine **Irrfahrt** geht in jedem Schritt zu einem zufällig gewählten Nachbarplatz, jeder gleich wahrscheinlich. Die **Trefferzeit** ist die mittlere Zahl ihrer Schritte bis zum ersten Besuch eines Ziels. Hin und zurück dauern im Allgemeinen verschieden lang, obwohl jede Verbindung in beide Richtungen offen ist. Bei zwei kleinen Hallen mit einer Tür kann sie von einem Platz ohne Tür nicht in die andere Halle geraten, bevor sie den Türplatz derselben Halle erreicht; in der Gegenrichtung kann sie das. Trotzdem lassen sich alle Plätze so reihen, dass es von weiter vorn nach weiter hinten im Mittel nie länger dauert als zurück. Der Grund: Eine Runde über mehrere Plätze, jeweils bis zur ersten Ankunft, dauert im Mittel in beiden Umlaufrichtungen gleich lang. Das gilt für einfache, ungerichtete, zusammenhängende Netze.

[Ausführlich und verständlich erklärt, mit Fachteil](https://sebastianhanisch.net/hin-ist-nicht-zurueck-erklaert.html)
        """
    )
# erklaerseite:einfach:end

with st.expander("So funktioniert die Trefferzeit", expanded=True):
    st.markdown(
        """
1. **Ein Schritt.** Die Irrfahrt steht auf einem Platz und geht zu einem seiner Nachbarn, jeder mit derselben Wahrscheinlichkeit.
2. **Erster Schritt, dann weiter.** Für jedes Ziel v gilt: H(u,v) = 1 + Durchschnitt von H(w,v) über die Nachbarn w von u, und H(v,v) = 0. Das ist ein lineares
   Gleichungssystem, eines je Ziel.
3. **Alle auf einmal.** Die **Fundamentalmatrix** liefert alle Trefferzeiten mit einer einzigen Matrixinversion; die Demo prüft jedes Ergebnis an der Gleichung aus 2.
4. **Netze.** Das **Handnetz „zwei Hallen“** (zwei Dreiecke, eine Tür) zum Nachrechnen, **zwei Gitterhallen** a×a mit einer Tür in der Zeile a // 2 und zum Kontrast ein
   **Saal mit Stichgang** (21 Plätze, die alle miteinander verbunden sind, daran ein Gang mit 11 Plätzen; im Fachjargon Lutscher-Netz). Die Hallen sind eine Kulisse,
   keine belegte Lagerweg-Anwendung. In den Gitterhallen heißt L(1,0) „linke Halle, Zeile 1, Spalte 0“.
        """
    )

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()
passe_netzregler_an()

netz_jetzt, a_jetzt = st.session_state["netz"], int(st.session_state["a"])
g_jetzt = S.netz_fuer(netz_jetzt, a_jetzt)
art_wirksam = S.wirksame_art(netz_jetzt, st.session_state["kante"])

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("🧩 Netz")
    st.selectbox("Netz", C.NETZE, key="netz", format_func=C.NETZ_TEXT.get, on_change=netz_gewechselt,
                 help="Handnetz zum Nachrechnen, zwei Gitterhallen mit einer Tür oder als Kontrast ein vollständiger Saal mit Gang. Beim Wechsel stellen sich Start, Ziel und neue Kante auf Standardplätze.")
    st.slider("Hallenseite a (Gitterhallen)", *bounds("a"), key="a", disabled=netz_jetzt != C.NETZ_HALLEN, on_change=groesse_gewechselt,
              help="Jede Halle ist ein Gitter a×a, zusammen 2a² Plätze (18 bis 200). Nur bei den Gitterhallen.")
    st.header("📍 Start und Ziel")
    st.selectbox("Start u", range(g_jetzt.n), key="u", format_func=lambda i: g_jetzt.knoten[i], help="Auch per Klick auf die Hauptkarte wählbar.")
    st.selectbox("Ziel v", range(g_jetzt.n), key="v", format_func=lambda i: g_jetzt.knoten[i], help="Auch per Klick auf die Hauptkarte wählbar.")
    st.header("🚪 Neue Kante (Experiment 3)")
    st.radio("Art der neuen Kante", C.KANTEN_ARTEN, key="kante", format_func=C.KANTE_TEXT.get, disabled=not S.hat_zweite_tuer(netz_jetzt),
             help="Zweite Tür: die vorhandene Tür bleibt, eine weitere kommt dazu. Frei gewählt: eine Kante zwischen zwei beliebigen, noch nicht verbundenen Plätzen. Das Kontrastnetz hat keine zweite Tür.")
    st.selectbox("Zeile der zweiten Tür", S.tuerzeilen_neu(netz_jetzt, a_jetzt), key="r", disabled=not (netz_jetzt == C.NETZ_HALLEN and art_wirksam == C.KANTE_TUER),
                 help="Nur bei den Gitterhallen mit „zweite Tür“. Die vorhandene Tür liegt in Zeile a // 2. Beim Handnetz ist die zweite Tür die Kante 5–0.")
    st.selectbox("Freie Kante: erster Platz", range(g_jetzt.n), key="ka", format_func=lambda i: g_jetzt.knoten[i], disabled=art_wirksam != C.KANTE_FREI)
    st.selectbox("Freie Kante: zweiter Platz", range(g_jetzt.n), key="kb", format_func=lambda i: g_jetzt.knoten[i], disabled=art_wirksam != C.KANTE_FREI)
    st.header("🔬 Probeläufe (Experiment 4)")
    st.selectbox("Paar", C.PAARE, key="paar", format_func=C.PAAR_TEXT.get,
                 help="Größte Streuung: das geordnete Paar mit dem größten Variationskoeffizienten (bei Gleichstand das kleinste Paar). Türschritt: einmal durch die Tür (bzw. in den Gang). Gewählt: Start u nach Ziel v.")
    st.slider("Zahl der Probeläufe R", *bounds("laeufe"), key="laeufe", step=C.LAEUFE_STEP, help="So viele unabhängige Läufe simuliert die Demo.")
    st.select_slider("Abbruch nach c·H Schritten", options=C.ABBRUCH_STUFEN, key="abbruch", format_func=lambda c: "ohne" if c == C.ABBRUCH_OHNE else f"c = {c}",
                     help="Ein Lauf wird nach K = c·H Schritten (gerundet) abgebrochen und zählt mit K. H ist hier der wahre Wert aus dem Gleichungssystem; in der Praxis kennt man ihn vorab nicht.")
    st.number_input("Zufalls-Seed", *bounds("seed"), key="seed", step=1, help="Steuert die simulierten Läufe in Experiment 4.")
    st.button("🎲 Neuen Zufalls-Seed ziehen", width="stretch", on_click=randomize_seed)

sync_query_params({key: st.session_state[key] for key in ("netz", "a", "u", "v", "kante", "r", "ka", "kb", "paar", "laeufe", "abbruch", "seed")})

einst = E.Settings(netz_jetzt, a_jetzt, int(st.session_state["u"]), int(st.session_state["v"]), st.session_state["kante"], int(st.session_state["r"]),
                   int(st.session_state["ka"]), int(st.session_state["kb"]), st.session_state["paar"], int(st.session_state["laeufe"]),
                   st.session_state["abbruch"], int(st.session_state["seed"]))
u, v = einst.u, einst.v

# --- Ergebnis: ein Paar ------------------------------------------------------------------------------------------------------------------------

with st.spinner("Rechne die Trefferzeiten …"):
    an = _netz(einst.netz, einst.a)
g = an.g
st.markdown("## 🎯 Hin und zurück auf der Karte")
st.caption(f"{g.name}: {g.n} Plätze, {len(g.kanten)} Verbindungen. Erwartete Schritte der einfachen Irrfahrt (sie bleibt nie stehen).")
if an.residuum > 1e-8:
    st.error(f"Die Prüfung an der Gleichung H(u,v) = 1 + Mittel über die Nachbarn schlägt an (relative Abweichung {an.residuum:.1e}).")
r = E.richtungen(an, u, v)
m1, m2, m3, m4 = st.columns(4)
m1.metric(f"H(u,v): {g.knoten[u]} → {g.knoten[v]}", E.zeit(r["hin"]), help="Erwartete Schritte vom Start bis zum ersten Besuch des Ziels.")
m2.metric(f"H(v,u): {g.knoten[v]} → {g.knoten[u]}", E.zeit(r["her"]), help="Der Rückweg.")
m3.metric("Verhältnis der Richtungen", "–" if r["verhaeltnis"] is None else E.de(r["verhaeltnis"], 2), help="Längere durch kürzere Richtung.")
m4.metric("Zeit zu einem stationär gezogenen Ziel", E.zeit(r["zufallsziel"]),
          help="Ab Start u bis zu einem Ziel, das nach der stationären Verteilung gezogen wird (Anteil je Platz proportional zu seiner Nachbarzahl). Experiment 2: dieser Wert ist für jeden Start gleich.")
art, text = E.verdict_ansicht(an, u, v)
getattr(st, art)(text)
st.radio("Klick auf die Karte setzt", (KLICK_START, KLICK_ZIEL), key="klickziel", horizontal=True)
st.plotly_chart(karte_paar(an, u, v), width="stretch", key="hauptkarte", on_select=_karte_geklickt, selection_mode="points")
st.caption("u (rot): Start. v (grün): Ziel. Fährt man über einen Platz, erscheinen Name und Nachbarzahl.")

# --- Kernfragen --------------------------------------------------------------------------------------------------------------------------------

kante, grund = S.neue_kante(einst.netz, einst.a, einst.kante, einst.r, einst.ka, einst.kb)
erg = None if kante is None else _ergaenzung(einst.netz, einst.a, kante)
with st.spinner("Rechne die Streuung der Trefferzeiten (je Ziel zwei Gleichungssysteme) …"):
    streu = _streuung(einst.netz, einst.a)
pu, pv = E.probe_paar(einst, streu)
probe = None if pu == pv else _probe(einst.netz, einst.a, pu, pv, einst.abbruch)

st.markdown("---")
st.markdown("## ❓ Kernfragen")
st.markdown("**1. Warum ist hin nicht zurück?**")
st.markdown(E.kurz_warum(an, u, v))
st.markdown("**2. Wohin ist der Weg kürzer?**")
st.markdown(E.kurz_wohin(an, u, v))
st.markdown("**3. Kann eine neue Tür einen Weg verlängern?**")
st.markdown(f"Ja, eine neue Kante kann das. {grund}" if erg is None else E.kurz_tuer(erg, an))
st.markdown("**4. Wie viele Probeläufe reichen?**")
st.markdown("Dafür braucht es zwei verschiedene Plätze." if probe is None else E.kurz_laeufe(probe, g))
st.caption("Die Antworten rechnen mit den Einstellungen der Seitenleiste; die Voraussetzungen und Einschränkungen stehen in den Experimenten.")

st.markdown("---")

# --- Experiment 1 --------------------------------------------------------------------------------------------------------------------------------

asy = _asymmetrie(einst.netz, einst.a)
st.subheader("🔬 Experiment 1: Hin und zurück")
st.caption(f"Alle {E.ganz(asy['paare'])} ungeordneten Paare von {g.name}: größere durch kleinere Richtung.")
x1, x2, x3, x4 = st.columns(4)
x1.metric("Median-Verhältnis", E.de(asy["median"], 2))
x2.metric("90-%-Quantil", E.de(asy["q90"], 2), help="9 von 10 Paaren haben höchstens dieses Verhältnis.")
x3.metric("Größtes Verhältnis", E.de(asy["groesstes"], 2))
x4.metric(f"Asymmetrisch (von {E.ganz(asy['paare'])})", E.ganz(asy["asymmetrisch"]), help="Ungeordnete Paare, deren beide Richtungen sich unterscheiden (relativ mehr als 1e-9).")
la, lb = asy["paar"]
st.caption(f"Das Paar mit dem größten Verhältnis: {g.knoten[la]} → {g.knoten[lb]} braucht {E.zeit(an.H[la, lb])} Schritte, zurück {E.zeit(an.H[lb, la])}.")
st.plotly_chart(histogramm_verhaeltnisse(asy["verhaeltnisse"], asy["median"]), width="stretch", key="verhaeltnisse")
st.markdown("**Gegner: die Faustformel „nur der Zielgrad zählt“, H(u,v) ≈ 2m / d_v** (m Verbindungen, d_v Nachbarzahl des Ziels), für das gewählte Paar:")
if u != v:
    st.dataframe(
        [{"Richtung": z["richtung"], "exakt": E.zeit(z["exakt"]), "Nachbarzahl Ziel": z["grad_ziel"], "2m/d": E.zeit(z["roh"]),
          "mit Vorfaktor": E.zeit(z["mit_faktor"]), "Wert je Zielgrad": E.zeit(z["je_grad"])} for z in E.formel_zeilen(an, asy["formel"], u, v)],
        hide_index=True, width="stretch",
    )
f = asy["formel"]
art, text = E.verdict_asymmetrie(asy["median"], asy["groesstes"], f["roh"], f["mit_faktor"], f["mit_je_grad"])
getattr(st, art)(text)
st.caption(f"Vorfaktor {E.de(f['faktor'], 2)} und der Wert je Zielgrad sind auf genau den bewerteten Paaren dieses Netzes so angepasst, dass der Median-Fehler möglichst klein "
           "wird; das begünstigt den Gegner. Fehler: Median von |Schätzung − H| / H über alle geordneten Paare. Die kürzeste Entfernung in Schritten ist in beiden "
           "Richtungen gleich und kann keine Asymmetrie zeigen.")

st.markdown("---")

# --- Experiment 2 --------------------------------------------------------------------------------------------------------------------------------

ordn = _ordnung(einst.netz, einst.a)
st.subheader("🔬 Experiment 2: Eine Reihenfolge für alle Paare")
st.markdown("H(π,v) ist die mittlere Schrittzahl bis v ab einem zufällig nach π gezogenen Start. **Reiht man die Plätze nach fallendem H(π,·), gilt für jedes Paar „u vor v“: "
            "H(u,v) ≤ H(v,u)** (Satz; Lovász 1993). Die Richtung zum Platz mit dem kleineren H(π,·) ist also nie die längere.")
st.plotly_chart(karte_hpi(an, u, v), width="stretch", key="karte_hpi")
if g.n <= 10:
    st.markdown(f"Von den {E.ganz(math.factorial(g.n))} möglichen Reihenfolgen der {g.n} Plätze sind genau "
                f"**{E.ganz(ordn['stimmige_reihenfolgen'])}** mit allen Paaren stimmig; es sind die mit fallendem H(π,·), Plätze mit gleichem Wert beliebig untereinander.")
else:
    st.markdown(f"Die {g.n} Plätze fallen in {len(ordn['gruppen'])} Gruppen mit gleichem H(π,·) (relativ 1e-9, meist Spiegelbilder). Stimmig sind genau die "
                "Reihenfolgen mit fallendem H(π,·), innerhalb einer Gruppe beliebig.")
st.markdown("**Billige Regeln als Gegner** (alle asymmetrischen ungeordneten Paare; ein Paar, das eine Regel offen lässt, zählt als nicht richtig):")
nenner = max(ordn["asymmetrisch"], 1)
st.dataframe(
    [
        {"Regel: kürzer ist der Weg zum Platz …": "mit mehr Nachbarn (Grad)", "richtig": f"{E.ganz(ordn['grad_richtig'])} von {E.ganz(ordn['asymmetrisch'])}",
         "Anteil": E.prozent(ordn["grad_richtig"] / nenner, 1), "braucht": "zwei Nachbarzahlen"},
        {"Regel: kürzer ist der Weg zum Platz …": "mit kleinerem π-gewichtetem Abstand", "richtig": f"{E.ganz(ordn['abstand_richtig'])} von {E.ganz(ordn['asymmetrisch'])}",
         "Anteil": E.prozent(ordn["abstand_richtig"] / nenner, 1), "braucht": "alle Abstände im Netz"},
        {"Regel: kürzer ist der Weg zum Platz …": "mit mehr Nachbarn, bei Gleichstand mit kleinerem Abstand", "richtig": f"{E.ganz(ordn['beide_richtig'])} von {E.ganz(ordn['asymmetrisch'])}",
         "Anteil": E.prozent(ordn["beide_richtig"] / nenner, 1), "braucht": "alle Abstände im Netz"},
        {"Regel: kürzer ist der Weg zum Platz …": "mit kleinerem H(π,·) (Satz)", "richtig": f"{E.ganz(ordn['hpi_richtig'])} von {E.ganz(ordn['asymmetrisch'])}",
         "Anteil": E.prozent(ordn["hpi_richtig"] / nenner, 1), "braucht": "die Trefferzeiten selbst"},
    ],
    hide_index=True, width="stretch",
)
art, text = E.verdict_ordnung(ordn["asymmetrisch"], ordn["gradgleich"], ordn["grad_richtig"], ordn["beide_richtig"], ordn["hpi_richtig"])
getattr(st, art)(text)
st.caption("„π-gewichteter Abstand“ eines Platzes v: Mittel der kürzesten Entfernungen aller Plätze w zu v, jeder mit π(w) gewichtet. Wie oft zwei Plätze genau gleich "
           f"stehen, entscheidet die Demo in ganzen Zahlen; die kombinierte Regel lässt hier {E.ganz(ordn['beide_offen'])} asymmetrische Paare offen.")
st.markdown("**Zufallsziel:** Die Zeit bis zu einem nach π gezogenen Ziel ist **von jedem Start aus dieselbe** (Σ_v π(v)·H(u,v) hängt nicht von u ab; random target lemma).")
z1, z2 = st.columns(2)
z1.metric("kleinster Wert über alle Starts", E.zeit(ordn["zz_min"]))
z2.metric("größter Wert über alle Starts", E.zeit(ordn["zz_max"]))
beispiele = sorted({u, v, 0, g.n - 1, int(an.hpi.argmax()), int(an.hpi.argmin())})
st.dataframe([{"Start": g.knoten[i], "Zeit zu stationär gezogenem Ziel": E.zeit(an.zufallsziel[i]), "H(π, Start)": E.zeit(an.hpi[i])} for i in beispiele],
             hide_index=True, width="content")
st.caption(f"Nicht dasselbe wie die mittlere Trefferzeit über alle geordneten Paare, hier {E.zeit(an.mittel)}. π(v) = Nachbarzahl von v / (2m): So oft besucht die Irrfahrt "
           "auf einem zusammenhängenden Netz auf lange Sicht jeden Platz (Anteil der Besuche). Mehr dazu in der Demo „Meinungsbildung“ des Portfolios.")

st.markdown("---")

# --- Experiment 3 --------------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 3: Eine Tür mehr (eine neue Kante)")
if erg is None:
    st.info(grund)
else:
    x, y = kante
    if art_wirksam == C.KANTE_TUER:
        beschreibung = ("Zweite Tür 5–0 auf dem Handnetz" if einst.netz == C.NETZ_HAND
                        else f"Zweite Tür in Zeile {x // einst.a} ({g.knoten[x]} – {g.knoten[y]}); die vorhandene Tür in Zeile {einst.a // 2} bleibt")
    else:
        beschreibung = f"Frei gewählte neue Kante {g.knoten[x]} – {g.knoten[y]}"
        if not S.hat_zweite_tuer(einst.netz):
            beschreibung += " (das Kontrastnetz hat keine Tür, hier zählt immer die frei gewählte Kante)"
    st.caption(f"{beschreibung}. Orange gestrichelt: die neue Kante. „Länger“ heißt: um mehr als 1e-9 relativ größer.")
    ansicht = st.radio("Karte zeigt", (ANSICHT_ZIEL, ANSICHT_ANTEIL), horizontal=True, key="kartenansicht")
    if ansicht == ANSICHT_ZIEL:
        st.plotly_chart(karte_aenderung(an, erg, v), width="stretch", key="karte_tuer_ziel")
        st.caption(f"Farbe je Startplatz: Wie ändert sich der Weg von dort zum Ziel {g.knoten[v]}?")
    else:
        st.plotly_chart(karte_anteil(an, erg), width="stretch", key="karte_tuer_anteil")
        st.caption("Farbe je Startplatz: Anteil der Ziele, zu denen der Weg von dort länger wird.")
    if erg.residuum > 1e-8:
        st.error("Die Prüfung der Trefferzeiten im neuen Netz schlägt an.")
    t1, t2, t3 = st.columns(3)
    t1.metric("Länger gewordene Trefferzeiten", E.prozent(erg.anzahl_laenger / erg.paare, 1),
              help=f"{E.ganz(erg.anzahl_laenger)} von {E.ganz(erg.paare)} geordneten Paaren (u, v).")
    t2.metric("Mittlere Trefferzeit", E.zeit(erg.mittel[1]), delta=f"{E.zeit(erg.mittel[1] - erg.mittel[0])} (vorher {E.zeit(erg.mittel[0])})", delta_color="inverse",
              help="Mittel über alle geordneten Paare, jedes gleich gewichtet.")
    t3.metric("Zeit zu stationär gezogenem Ziel", E.zeit(erg.zufallsziel[1]), delta=f"{E.zeit(erg.zufallsziel[1] - erg.zufallsziel[0])} (vorher {E.zeit(erg.zufallsziel[0])})", delta_color="inverse")
    t4, t5, t6 = st.columns(3)
    t4.metric(f"H({g.knoten[x]}, {g.knoten[y]})", E.zeit(erg.ab[1]), delta=f"{E.zeit(erg.ab[1] - erg.ab[0])} (vorher {E.zeit(erg.ab[0])})", delta_color="inverse")
    t5.metric(f"H({g.knoten[y]}, {g.knoten[x]})", E.zeit(erg.ba[1]), delta=f"{E.zeit(erg.ba[1] - erg.ba[0])} (vorher {E.zeit(erg.ba[0])})", delta_color="inverse")
    t6.metric("Größter Faktor einer Trefferzeit", E.de(erg.groesster_faktor, 2), help="Größtes H nachher durch H vorher über alle geordneten Paare.")
    art, text = E.verdict_kante(erg.anzahl_laenger, erg.paare, erg.ab, erg.ba)
    getattr(st, art)(text)
    st.caption("Zwischen den Endpunkten der neuen Kante wird die Trefferzeit kürzer; die Formel dafür und die Begründung stehen unten im Expander 📐.")
    if einst.netz == C.NETZ_HALLEN:
        st.markdown("**Alle möglichen Zeilen der zweiten Tür** (die vorhandene bleibt):")
        with st.spinner("Rechne alle Zeilen …"):
            sweep = _zeilen_sweep(einst.netz, einst.a)
        st.dataframe([{"Zeile r": z["r"], "länger (geordnete Paare)": E.prozent(z["anteil_laenger"], 1), "mittlere Trefferzeit": E.zeit(z["mittel"]),
                       "zwischen den neuen Türknoten, vorher → nachher": f"{E.zeit(z['ab_vor'])} → {E.zeit(z['ab_nach'])}",
                       "größter Faktor": E.de(z["faktor"], 2)} for z in sweep], hide_index=True, width="stretch")
        st.caption(f"Ohne zweite Tür ist die mittlere Trefferzeit {E.zeit(an.mittel)}.")
if st.toggle("Weg mit Schlussstein zeigen", key="schlussstein", help="Das kleinste Beispiel: Ein Weg wird zum Kreis, und ein Schritt wird zu vielen."):
    n_weg = st.slider("Länge des Wegs (Plätze)", C.WEG_MIN, C.WEG_MAX, C.DEFAULT_WEG, key="weg_n")
    s = E.schlussstein(n_weg)
    w1, w2 = st.columns(2)
    w1.plotly_chart(karte_weg(N.weg(n_weg), 160), width="stretch", key="weg_vorher")
    w2.plotly_chart(karte_weg(N.weg_mit_schlussstein(n_weg), 260), width="stretch", key="weg_nachher")
    k1, k2 = st.columns(2)
    k1.metric("Weg: H(Ende, Nachbar)", E.zeit(s["vorher"]))
    k2.metric("mit Schlussstein: derselbe Weg", E.zeit(s["nachher"]))
    st.markdown(f"Aus **1** Schritt werden **{n_weg - 1}** erwartete Schritte. Der Start ist ein Blatt: Vorher ist der Schritt zum Nachbarn deshalb erzwungen. Lovász (1993, "
                "Abschnitt zur Monotonie) nennt dieses Beispiel. Die neue Kante liegt nicht am Ziel; eine neue Kante am Ziel verlängert H(Start, Ziel) nie.")
with st.expander("Zählung über alle kleinen Netze (vorgerechnet)"):
    at = _daten()["atlas"]
    kl = at["kleinstes_mit_laengerem_mittel"]
    st.markdown(
        f"Alle {E.ganz(at['graphen'])} zusammenhängenden, nicht isomorphen Netze mit 3 bis 7 Plätzen (Graphen-Atlas aus networkx), jede fehlende Kante je Netz einzeln "
        f"ergänzt: **{E.ganz(at['ergaenzungen'])} Ergänzungen**.\n\n"
        f"* Mindestens eine Trefferzeit wird länger: {E.ganz(at['mindestens_eins_laenger'])} von {E.ganz(at['ergaenzungen'])}.\n"
        f"* Zwischen den Endpunkten wird sie nicht kürzer: {E.ganz(at['endpunkte_nicht_kuerzer'])}.\n"
        f"* Die mittlere Trefferzeit wird länger: {E.ganz(at['mittel_laenger'])} ({E.prozent(at['mittel_laenger'] / at['ergaenzungen'], 1)}); die Zeit zu einem stationär "
        f"gezogenen Ziel: {E.ganz(at['zufallsziel_laenger'])} ({E.prozent(at['zufallsziel_laenger'] / at['ergaenzungen'], 1)}).\n"
        f"* Anteil länger gewordener geordneter Paare: {E.prozent(at['mittlerer_anteil_je_ergaenzung'], 1)} als Mittel der Anteile je Ergänzung, "
        f"{E.prozent(at['paare_laenger'] / at['paare'], 1)} über alle {E.ganz(at['paare'])} Paare zusammen.\n"
        f"* Größter Faktor einer einzelnen Trefferzeit: {E.de(at['groesster_faktor'], 2)}. Das kleinste Netz, auf dem eine Ergänzung die mittlere Trefferzeit verlängert, hat "
        f"{kl['knoten']} Plätze ({E.de(kl['vorher'], 2)} → {E.de(kl['nachher'], 3)})."
    )

st.markdown("---")

# --- Experiment 4 --------------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 4: Probeläufe mit Abbruch")
cu, cv_ = streu.cv_paar
st.caption(f"Wer H(u,v) nicht ausrechnen kann, schickt Probeläufe los: unabhängige Läufe von u bis zum ersten Treffer von v. Variationskoeffizient (CV = Standardabweichung / Mittel) "
           f"aller geordneten Paare auf diesem Netz: Median {E.de(streu.cv_median, 2)}, größter {E.de(float(streu.CV[cu, cv_]), 2)} bei {g.knoten[cu]} → {g.knoten[cv_]}.")
if probe is None:
    st.info("Start und Ziel sind derselbe Platz: Bitte zwei verschiedene Plätze oder ein anderes Paar wählen.")
else:
    st.markdown(f"**Gezeigtes Paar ({C.PAAR_TEXT[einst.paar]}): {g.knoten[pu]} → {g.knoten[pv]}**, Abbruch {abbruch_text(einst.abbruch)}"
                + (f" (K = {E.ganz(probe['K'])} Schritte)" if probe["K"] else "") + ".")
    p1, p2, p3 = st.columns(3)
    p1.metric("wahres Mittel H", E.zeit(probe["h"]), help="Aus dem Gleichungssystem, also mit Kenntnis des ganzen Netzes.")
    p2.metric("Variationskoeffizient", E.de(probe["cv"], 2))
    p3.metric("Läufe-Vorgabe (±10 %, 95 %)", E.ganz(probe["laeufe_vorgabe"]), help="R = ⌈(1,96 · CV / 0,1)²⌉, Normalnäherung, ohne Abbruch.")
    p4, p5, p6 = st.columns(3)
    p4.metric("Mit Abbruch: Anteil von H", E.prozent(probe["anteil"], 1),
              help="Erwartungswert E[min(T, K)] geteilt durch H: abgebrochene Läufe zählen mit K. Wer sie verwirft, liegt noch tiefer.")
    p5.metric("Abgebrochene Läufe", E.prozent(probe["abbruch"], 1), help="Wahrscheinlichkeit P(T > K).")
    p6.metric("Zensurbewusst: Anteil von H", "–" if probe["zensur"] is None else E.prozent(probe["zensur"] / probe["h"], 1),
              help="Gegner (zensurbewusster Schätzer): Summe aller min(T, K) geteilt durch die Zahl der beendeten Läufe. Richtig, wenn die Abbruchrate je Schritt konstant wäre. Hier als Verhältnis der Erwartungswerte.")
    deckung = D.deckung_fuer(_daten(), einst.netz, einst.a, einst.paar)
    vergleich = _saal_vergleich() if E.zeigt_saalvergleich(einst.netz, einst.a, einst.paar, einst.abbruch) else None
    art, text = E.verdict_abbruch(probe, einst.abbruch, deckung, vergleich)
    getattr(st, art)(text)
    st.caption("Prozentzahlen mit Abbruch sind Erwartungswerte (exakt gerechnet); eine einzelne Messreihe streut darum. Das exakte Gleichungssystem ist hier der Prüfstein und "
               "kein Gegner: Es braucht das ganze Netz, ein Probelauf nur die Nachbarn des jeweiligen Platzes.")
    laeufe = E.simulation_laeufe(einst.laeufe, probe["h"])
    st.markdown(f"**Simulation: {E.ganz(laeufe)} Läufe, Zufalls-Seed {einst.seed}**")
    if laeufe < einst.laeufe:
        st.info(f"Gekürzt auf {E.ganz(laeufe)} Läufe: Bei H = {E.zeit(probe['h'])} wären {E.ganz(einst.laeufe)} Läufe im Mittel mehr als {E.ganz(C.SCHRITT_DECKEL)} Schritte.")
    with st.spinner("Simuliere die Läufe …"):
        sim = _simulation(einst.netz, einst.a, pu, pv, laeufe, einst.seed, probe["K"])
    ohne, mit = sim["ohne"], sim["mit"]
    zeilen = [{"Schätzer": "Mittel ohne Abbruch", "Wert": E.zeit(ohne["mittel"]), "Anteil von H": E.prozent(ohne["mittel"] / probe["h"], 1),
               "95-%-Intervall (Normalnäherung)": f"{E.zeit(ohne['von'])} bis {E.zeit(ohne['bis'])}"}]
    if probe["K"] is not None:
        zeilen.append({"Schätzer": "Mittel mit Abbruch (zählt mit K)", "Wert": E.zeit(mit["mittel"]), "Anteil von H": E.prozent(mit["mittel"] / probe["h"], 1),
                       "95-%-Intervall (Normalnäherung)": f"{E.zeit(mit['von'])} bis {E.zeit(mit['bis'])}"})
        zeilen.append({"Schätzer": "zensurbewusst", "Wert": "–" if mit["zensurbewusst"] is None else E.zeit(mit["zensurbewusst"]),
                       "Anteil von H": "–" if mit["zensurbewusst"] is None else E.prozent(mit["zensurbewusst"] / probe["h"], 1), "95-%-Intervall (Normalnäherung)": "–"})
    st.dataframe(zeilen, hide_index=True, width="stretch")
    st.caption(f"Abgebrochen wären in dieser Simulation {E.ganz(mit['abgebrochen'])} von {E.ganz(mit['laeufe'])} Läufen ({E.prozent(mit['abbruchanteil'], 1)}). "
               "Das Intervall um das Mittel mit Abbruch beschreibt nur die Streuung, nicht den Fehlbetrag gegenüber H.")
    st.plotly_chart(histogramm_laufzeiten(sim["zeiten"], probe["h"], probe["K"]), width="stretch", key="histogramm_laeufe")

st.markdown("**Wo der Abbruch wenig schadet, und wo man sich darauf nicht verlassen kann** (Abbruch nach 3·H):")
ecken = _eckpaare()
st.dataframe([{"Paar ferner Ecken": z["paar"], "H": E.zeit(z["h"]), "Erwartungswert / H": E.prozent(z["anteil"], 1), "abgebrochen": E.prozent(z["abbruch"], 1)} for z in ecken],
             hide_index=True, width="stretch")
abstand = _daten()["abstand"]
st.dataframe([{"zwei Hallen 8×8: Abstand mindestens": z["abstand_mindestens"], "geordnete Paare": E.ganz(z["paare"]),
               "kleinster Anteil von H": E.prozent(z["kleinster_anteil"], 1), "Median": E.prozent(z["median_anteil"], 1),
               "Paare unter 90 %": E.prozent(z["anteil_unter_90"], 1)} for z in abstand["zeilen"]], hide_index=True, width="stretch")
art, text = E.verdict_negativ(ecken, abstand)
getattr(st, art)(text)
with st.expander("Helfen mehr Läufe gegen den Fehlbetrag? (vorgerechnet, zwei Hallen 8×8, größte Streuung, c = 3)"):
    stre = _daten()["streuung"]
    st.dataframe([{"Läufe R": E.ganz(z["laeufe"]),
                   "mit Abbruch, Anteil von H (5 % / Median / 95 %)": " / ".join(E.prozent(q) for q in z["gekappt"]),
                   "zensurbewusst, Anteil von H (5 % / Median / 95 %)": " / ".join(E.prozent(q) for q in z["zensurbewusst"])} for z in stre["zeilen"]],
                 hide_index=True, width="stretch")
    st.markdown(f"Je Zeile {E.ganz(stre['wiederholungen'])} Wiederholungen, jede mit R Läufen aus der exakten Verteilung von T. Mehr Läufe machen die Streuung kleiner; "
                "der Wert, um den sie streuen, bleibt weit unter H. Der Fehlbetrag ist systematisch.")

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown("Diese Demo ist die erste der Reihe „Irrfahrten auf Netzen“. Die rechte Spalte nennt die Demo der Reihe, in der es weitergeht; jede ist eine eigene Demo.")
st.markdown(
    """
| Grenze dieser Demo | Wie es weitergeht | Thema |
|---|---|---|
| **Es gibt genau ein Ziel.** | Diese Demo fragt, wie viele Schritte die Irrfahrt im Mittel bis zu einem Ziel braucht. Die Demo „Etiketten“ setzt auf dem Netz zwei Ziele mit verschiedenen Etiketten und fragt, welches die Irrfahrt zuerst trifft. | Etiketten |
| **Die Trefferzeit hängt von der Richtung ab.** | Die Trefferzeit hängt von der Richtung ab (zwei Hallen mit einer Tür: H(0,2) = 2, H(2,0) = 22/3), sie ist also keine Größe des Paars {u, v}. Die Pendelzeit H(u,v) + H(v,u) zählt beide Richtungen, ist symmetrisch und lässt sich auf ungerichteten, zusammenhängenden Netzen als 2m·R aus Kantenzahl und effektivem Widerstand berechnen. | Pendelzeit |
| **Gefragt ist nur ein Ziel, nicht alle Plätze.** | Diese Demo misst, wie lange die Irrfahrt bis zu einem bestimmten Ziel braucht. Die Demo „Überdeckungszeit“ fragt auf demselben Handnetz und auf benannten Kontrastnetzen, wie lange es dauert, bis sie jeden Knoten mindestens einmal besucht hat, und was mehrere Läufer vom selben Start daran ändern. | Überdeckungszeit |
| **Die Übergänge sind vorgegeben.** | In dieser Demo sind die Übergänge vorgegeben: Von jedem Knoten geht es mit gleicher Wahrscheinlichkeit zu jedem Nachbarn. Die Demo „Streife“ wählt den Weg der Streife selbst (andere Kette, Kette mit einem Schritt Gedächtnis oder Rundtour) und misst in einem Forschungsmodell, wie gut sie einen Angriff entdeckt. | Streife |
| **Nach langer Zeit ist der Start vergessen.** | Läuft die Irrfahrt lange, hängt ihr Aufenthaltsort kaum noch vom Start ab und sagt wenig darüber, was nah am Start liegt (auf nicht bipartiten Netzen oder in der trägen Fassung; auf den bipartiten Gitterhallen bleibt bei der nicht trägen Irrfahrt nur die Parität des Starts erhalten). Die Demo „Lokaler Schnitt“ lässt sie in jedem Schritt mit einer Sprungwahrscheinlichkeit zum Start zurückspringen und schneidet aus der so entstehenden Gewichtung eine Menge um den Start. | Lokaler Schnitt |
"""
)
st.markdown(
    """
* **Keine Mischzeit hier:** Wie schnell der Start vergessen wird, zeigt diese Demo nicht; dazu die Demos „Mischzeit exakt“ (auch zur Periodizität auf Netzen wie den Gitterhallen) und „Meinungsbildung“ des Portfolios.
* **Träge Irrfahrt:** Bleibt die Irrfahrt in jedem Schritt mit Wahrscheinlichkeit ½ stehen, werden alle Trefferzeiten genau doppelt so lang.
* **Gerichtete oder gewichtete Netze** rechnet die Demo nicht; die Aussagen oben gelten für einfache, ungerichtete, zusammenhängende Netze und gleich wahrscheinliche Nachbarn.
* **Netze abtasten:** Wer Knoten zieht, indem er eine Irrfahrt laufen lässt, zieht sie auf lange Sicht proportional zum Grad; Umgewichten mit 1/Grad oder Metropolis-Hastings korrigiert das (Gjoka u. a., „A Walk in Facebook“). Dazu die Demos „Raten und Gewichte“ (Verzerrung nach Größe), „Metropolis im kleinen Raum“ und „Eindämmung“ (Impfen über Bekannte) des Portfolios.
"""
)

st.markdown("---")

with st.expander("⚠️ Annahmen, Grenzen und bekannte Probleme"):
    st.markdown(
        """
**Annahmen.**
- Einfaches, ungerichtetes, zusammenhängendes Netz; in jedem Schritt jeder Nachbar gleich wahrscheinlich; die Irrfahrt bleibt nie stehen. Alle Zeiten sind **erwartete** Schritte.
- Probeläufe sind unabhängig, jeder startet in u; abgebrochene Läufe zählen mit der Abbruchzeit K. Die Abbruchzeit wird als Vielfaches des wahren H gesetzt, das man in der Praxis vorab nicht kennt.
- Die Läufe-Vorgabe beruht auf der Normalnäherung (±10 % bei 95 %).

**Grenzen.**
- Die Zahlen zu den Netzen (Asymmetrie, Faustformeln, Reihungsregeln, zweite Tür, Abbruch) gelten für diese Netze, nicht für Netze allgemein. Die Sätze (Reihenfolge, Zufallsziel, neue Kante) gelten auf jedem Netz mit den Annahmen oben.
- Die Faustformel-Gegner sind auf den bewerteten Paaren angepasst, also zu ihren Gunsten. Andere Faustformeln oder Reihungsregeln sind nicht geprüft.
- Wie oft die Läufe-Vorgabe wirklich ±10 % trifft, ist für die Paare „größte Streuung“ und „Türschritt“ jedes angebotenen Netzes vorgerechnet, für frei gewählte Paare nicht.
- Auf dem Handnetz und den Gitterhallen ist die Asymmetrie im Median mäßig; der Saal mit Stichgang zeigt den Effekt deutlich.

**Bekannte Probleme und Unsicherheiten.**
- Die Wahl von Start und Ziel per Klick auf die Karte ist nicht mit einem echten Mausklick bestätigt (geprüft wurde die Verarbeitung eines im Browser ausgelösten Auswahl-Ereignisses; der automatisierte Klick löste keine Auswahl aus). Die Auswahlfelder in der Seitenleiste tun dasselbe.
- Bei den größten Gitterhallen dauern die Streuungsrechnung und die Simulation einen Moment.
        """
    )

# --- Formeln -------------------------------------------------------------------------------------------------------------------------------------

with st.expander("📐 Mathematische Formulierung"):
    # erklaerseite:lesehilfe:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/hin-ist-nicht-zurueck-erklaert.json, nicht von Hand ändern)
    st.markdown(
        r"""
**Lesehilfe.** Gegeben ist ein einfaches, ungerichtetes, zusammenhängendes Netz, auf dem die Irrfahrt in jedem Schritt gleich wahrscheinlich zu einem Nachbarn geht. Gesucht sind die erwarteten Schrittzahlen $H(u,v)$ von jedem Platz $u$ zu jedem Platz $v$.

| Symbol | Bedeutung |
|---|---|
| $n$, $m$ | Zahl der Plätze (Knoten), Zahl der Verbindungen (Kanten) |
| $u$, $v$, $w \sim u$ | Plätze, meist Start $u$ und Ziel $v$; $w \sim u$ heißt: $w$ ist Nachbar von $u$ |
| $d_u$ | Zahl der Nachbarn (Grad) des Platzes $u$; ebenso $d_v$, $d_a$, $d_c$, $d_x$ |
| $P$, $P_{uw}$ | Übergangsmatrix: $P_{uw} = 1/d_u$ für $w \sim u$, sonst 0 |
| $\pi(v) = d_v / 2m$ | stationäre Verteilung: so oft besucht die Irrfahrt auf lange Sicht den Platz $v$ (Anteil der Besuche) |
| $H(u,v)$ | Trefferzeit: erwartete Schritte von $u$ bis zum ersten Besuch von $v$, $H(v,v) = 0$ |
| $H(\pi,v)$, $H(\pi,\cdot)$ | erwartete Schritte bis $v$ ab einem nach $\pi$ gezogenen Start; der Punkt steht für einen beliebigen Platz |
| $Z$, $I$, $\mathbf{1}$, $\top$ | Fundamentalmatrix; Einheitsmatrix; Spaltenvektor aus Einsen; transponiert |
| $a$, $b$, $c$ | neue Kante: ihre bisher nicht verbundenen Endpunkte $a$, $b$; $c$ ein anderer Platz |
| $p_{ab}$, $\ell$, $R_{ab}$ | Fluchtwahrscheinlichkeit (von $a$ aus $b$ vor der Rückkehr nach $a$ erreichen); mittlere Länge eines Ausflugs; effektiver Widerstand $1/(d_a\, p_{ab})$ |
| $H'(a,b)$ | Trefferzeit im Netz mit der neuen Kante |
| $s$, $t$, $x$ | nur beim Satz über eine neue Kante am Ziel: Start $s$, Ziel $t$, anderer Endpunkt $x$ |
| $T$, $Q$ | Probeläufe: Schrittzahl eines Laufs von $u$ nach $v$; $P$ ohne Zeile und Spalte $v$ |
| $t$, $t_u$ | nur bei den Probeläufen: Vektor der Trefferzeiten nach $v$ und sein Eintrag für den Start $u$ (nicht das Ziel $t$ von oben) |
| $E[\,\cdot\,]$, $P(\ldots)$ | Erwartungswert; Wahrscheinlichkeit ($P$ mit Klammer ist nicht die Übergangsmatrix) |
| $\mathrm{CV}$, $R$, $\lceil\,\cdot\,\rceil$ | Variationskoeffizient von $T$; Zahl der Probeläufe (nicht der Widerstand $R_{ab}$); Aufrunden auf eine ganze Zahl |
| $K$ | Abbruch eines Laufs nach $K$ Schritten |

[Schritt für Schritt erklärt, mit Herleitung und Literatur](https://sebastianhanisch.net/hin-ist-nicht-zurueck-erklaert.html#fachleute)
        """
    )
    # erklaerseite:lesehilfe:end
    st.markdown(
        r"""
**Definierende Gleichung** (erster Schritt, für $u \ne v$):

$$
H(u,v) = 1 + \frac{1}{d_u} \sum_{w \sim u} H(w,v)
$$

**Alle auf einmal** über die Fundamentalmatrix ($\mathbf{1}$ Spaltenvektor aus Einsen):

$$
Z = (I - P + \mathbf{1}\pi^{\top})^{-1}
$$

$$
H(u,v) = \frac{Z_{vv} - Z_{uv}}{\pi(v)}
$$

**Eine Reihenfolge für alle Paare** (Zyklusidentität und Reihung, Lovász 1993):

$$
\begin{aligned} & H(u,v) - H(v,u) \\ ={} & H(\pi,v) - H(\pi,u) \end{aligned}
$$

Also ist die Richtung zum Platz mit kleinerem $H(\pi,\cdot)$ nie die längere. **Zufallsziel:** $\sum_v \pi(v)\, H(u,v)$ ist für jeden Start $u$ gleich.

**Eine neue Kante** zwischen zwei bisher nicht verbundenen Knoten $a$, $b$ (ab 3 Knoten). Erstens: Für jeden Knoten $c$ außer $a$, $b$ ist die mittlere Rückkehrzeit

$$
\frac{2m}{d_c} = 1 + \frac{1}{d_c} \sum_{w \sim c} H(w,c)
$$

Die neue Kante erhöht $m$ um 1 und ändert weder $d_c$ noch die Nachbarn von $c$. Also wächst dieses Mittel um genau $2/d_c$: **mindestens eine Trefferzeit wird länger.**

Zweitens: Von $a$ aus endet jeder Ausflug entweder in $b$ (Wahrscheinlichkeit $p_{ab}$, Fluchtwahrscheinlichkeit) oder wieder in $a$; mit mittlerer Länge $\ell$ ist $H(a,b) = \ell / p_{ab}$. Mit der
neuen Kante führt der erste Schritt mit Wahrscheinlichkeit $1/(d_a+1)$ sofort nach $b$, sonst folgt ein alter Ausflug. Daraus ergibt sich mit $R_{ab} = 1/(d_a\, p_{ab})$:

$$
H'(a,b) = \frac{H(a,b) + R_{ab}}{1 + R_{ab}} < H(a,b)
$$

denn $H(a,b) > 1$, weil $a$ und $b$ nicht verbunden sind; ebenso von $b$ aus. $R_{ab}$ ist der effektive Widerstand, den die Demo „Pendelzeit“ der Reihe erklärt. Eine neue Kante $t$–$x$ am Ziel $t$ verlängert $H(s,t)$ nicht: Die neue
Irrfahrt ist die alte, die bei jedem Besuch von $x$ mit Wahrscheinlichkeit $1/(d_x+1)$ vorzeitig in $t$ endet. Beide Herleitungen stehen hier als kurze Folgerungen; ob sie so in der
Literatur stehen, ist nicht geprüft. Lovász (1993) zeigt an Beispielen, dass neue Kanten Trefferzeiten verlängern können.
        """
    )
    if erg is not None:
        x, y = erg.kante
        st.markdown(f"**An der gewählten Kante {g.knoten[x]}–{g.knoten[y]}:** $R_{{ab}}$ = {E.de(erg.r_ab, 3)}, also $H'(a,b)$ = ({E.de(erg.ab[0], 3)} + {E.de(erg.r_ab, 3)}) / "
                    f"(1 + {E.de(erg.r_ab, 3)}) = {E.de((erg.ab[0] + erg.r_ab) / (1 + erg.r_ab), 3)}; direkt aus dem neuen Netz gerechnet: {E.de(erg.ab[1], 3)}.")
    st.markdown(
        r"""
**Probeläufe.** Mit $t = (I-Q)^{-1}\mathbf{1}$ (die Trefferzeiten) ist

$$
E[T^2] = (I-Q)^{-1}(2t - \mathbf{1})
$$

$$
\mathrm{CV} = \frac{\sqrt{E[T^2] - t^2}}{t}
$$

(jeweils die Komponente von $u$). Für ±10 % bei 95 % nach Normalnäherung braucht es

$$
R = \left\lceil \left( \frac{1{,}96 \cdot \mathrm{CV}}{0{,}1} \right)^{2} \right\rceil
$$

Läufe. Bricht man nach $K$ Schritten ab und zählt mit $K$, ist

$$
E[\min(T,K)] = t_u - (Q^K t)_u
$$

$$
P(T > K) = (Q^K \mathbf{1})_u
$$

Der zensurbewusste Schätzer teilt $\sum \min(T,K)$ durch die Zahl der beendeten Läufe.

**Literatur.** L. Lovász, *Random Walks on Graphs: A Survey* (1993; die Fassungen haben verschiedene Seitenzahlen): Zyklusidentität (Satz 2.4), Reihung (Korollar 2.5), Beispiele zur
Monotonie, startunabhängige Zeit zum stationär gezogenen Ziel (Gl. 3.3). D. Levin, Y. Peres, E. Wilmer, *Markov Chains and Mixing Times*, 2. Auflage: Zufallsziel-Lemma (Lemma 10.1).
M. Gjoka, M. Kurant, C. Butts, A. Markopoulou, *A Walk in Facebook*: Verzerrung der Irrfahrt beim Abtasten und Umgewichten (Zusammenfassung, Abschnitte I und III).
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Irrfahrten auf Netzen: Trefferzeit bis Schnitt](https://sebastianhanisch.net/konzepte-irrfahrten.html)."
)
