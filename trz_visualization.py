"""Plotly-Figuren der Demo (alle Achsen gesperrt). Die Netzkarte selbst kommt aus `trz_karte`."""

import numpy as np
import plotly.graph_objects as go

import trz_constants as C
import trz_karte as K
import trz_netze as N

FARBE_BALKEN = "#4c78a8"
SKALA_AENDERUNG = [[0.0, "#2166ac"], [0.5, "#f2f2f2"], [1.0, "#b2182b"]]        # blau kürzer, rot länger


def _marken(g, u, v):
    marken = {u: ("u", K.FARBE_START)}
    if v != u:
        marken[v] = ("v", K.FARBE_ZIEL)
    return marken


def karte_paar(an, u: int, v: int):
    """Hauptkarte mit Start und Ziel."""
    grad = N.grade(an.g)
    hover = [f"{an.g.knoten[i]}<br>{int(grad[i])} Nachbarn" for i in range(an.g.n)]
    return K.karte(an.g, marken=_marken(an.g, u, v), hover=hover, hoehe=380)


def karte_hpi(an, u: int, v: int):
    """Färbung nach H(π, v): Zeit bis zum Platz ab einem stationär gezogenen Start."""
    hover = [f"{an.g.knoten[i]}<br>H(π, ·) = {an.hpi[i]:.2f}".replace(".", ",") for i in range(an.g.n)]
    return K.karte(an.g, werte=an.hpi, farbtitel="H(π, ·): Schritte bis zu diesem Platz", farbskala="Viridis", marken=_marken(an.g, u, v), hover=hover, hoehe=420)


def karte_aenderung(an, e, ziel: int):
    """Je Start x: Wie ändert die neue Kante H(x, Ziel)? Farbe = log2(nachher / vorher), blau kürzer, rot länger."""
    werte = np.zeros(an.g.n)
    maske = np.arange(an.g.n) != ziel
    werte[maske] = np.log2(e.H2[maske, ziel] / an.H[maske, ziel])
    grenze = max(float(np.abs(werte).max()), 1e-9)
    hover = [f"{an.g.knoten[i]} → {an.g.knoten[ziel]}<br>vorher {an.H[i, ziel]:.1f}, nachher {e.H2[i, ziel]:.1f}".replace(".", ",") for i in range(an.g.n)]
    return K.karte(e.neu, werte=werte, farbtitel="log₂(nachher / vorher): blau kürzer, rot länger", farbskala=SKALA_AENDERUNG, cmin=-grenze, cmax=grenze,
                   marken={ziel: ("Ziel", K.FARBE_ZIEL)}, neue_kante=e.kante, hover=hover, hoehe=420)


def karte_anteil(an, e):
    """Je Start x: Anteil der Ziele, zu denen der Weg länger wird."""
    anteil = 100 * e.laenger.sum(axis=1) / (an.g.n - 1)
    hover = [f"Start {an.g.knoten[i]}<br>{anteil[i]:.0f} % der Ziele länger" for i in range(an.g.n)]
    return K.karte(e.neu, werte=anteil, farbtitel="Anteil der Ziele mit längerem Weg (%)", farbskala="Reds", cmin=0, cmax=max(1.0, float(anteil.max())),
                   neue_kante=e.kante, hover=hover, hoehe=420)


def karte_weg(g, hoehe: int = 260):
    return K.karte(g, marken={0: ("Start", K.FARBE_START), 1: ("Ziel", K.FARBE_ZIEL)}, hoehe=hoehe, beschriftung=False)


def _balken(kanten, anzahl, farbe, name):
    mitten = (kanten[:-1] + kanten[1:]) / 2
    return go.Bar(x=mitten, y=anzahl, width=np.diff(kanten), marker=dict(color=farbe, line=dict(width=0.5, color="white")), name=name,
                  customdata=np.column_stack([kanten[:-1], kanten[1:]]), hovertemplate="%{customdata[0]:.2f} bis %{customdata[1]:.2f}: %{y}<extra></extra>",
                  showlegend=False)


def _layout(fig, hoehe, x_titel, y_titel):
    fig.update_xaxes(title=x_titel, fixedrange=True)
    fig.update_yaxes(title=y_titel, fixedrange=True)
    fig.update_layout(height=hoehe, margin=dict(l=10, r=10, t=30, b=10), bargap=0)
    return fig


def histogramm_verhaeltnisse(q: np.ndarray, median: float):
    """Verteilung „größere durch kleinere Richtung“ über alle ungeordneten Paare; bei großer Spanne mit Klassen gleicher Breite im Logarithmus."""
    groesst = max(float(q.max()), 1.0 + 1e-6)
    logarithmisch = groesst > 12
    kanten = np.geomspace(1.0, groesst * 1.0001, 31) if logarithmisch else np.linspace(1.0, groesst * 1.0001, 31)
    anzahl, _ = np.histogram(np.maximum(q, 1.0), bins=kanten)
    fig = go.Figure()
    if logarithmisch:
        unten, oben = np.log10(kanten[:-1]), np.log10(kanten[1:])
        fig.add_trace(go.Bar(x=(unten + oben) / 2, y=anzahl, width=oben - unten, marker=dict(color=FARBE_BALKEN, line=dict(width=0.5, color="white")),
                             customdata=np.column_stack([kanten[:-1], kanten[1:]]),
                             hovertemplate="%{customdata[0]:.2f} bis %{customdata[1]:.2f}: %{y}<extra></extra>", showlegend=False))
        marken = [t for t in (1, 2, 5, 10, 20, 50, 100, 200, 500) if t <= groesst]
        fig.update_xaxes(tickvals=list(np.log10(marken)), ticktext=[str(t) for t in marken])
        stelle = float(np.log10(median))
    else:
        fig.add_trace(_balken(kanten, anzahl, FARBE_BALKEN, "Paare"))
        stelle = median
    fig.add_vline(x=stelle, line=dict(color=K.FARBE_START, width=2, dash="dash"))
    fig.add_annotation(x=stelle, y=1, yref="paper", text="Median", showarrow=False, xanchor="left", font=dict(color=K.FARBE_START))
    return _layout(fig, 300, "größere durch kleinere Richtung" + (" (logarithmische Achse)" if logarithmisch else ""), "ungeordnete Paare")


def histogramm_laufzeiten(zeiten: np.ndarray, h: float, K_schritt=None):
    """Histogramm der simulierten Schrittzahlen; die längsten 0,5 % stehen gesammelt in der letzten Klasse."""
    ende = max(float(np.quantile(zeiten, 0.995)), 2.0, 0.0 if K_schritt is None else 1.3 * K_schritt, 1.3 * h)
    kanten = np.linspace(0, ende, 41)
    anzahl, _ = np.histogram(np.minimum(zeiten, ende - 1e-9), bins=kanten)
    fig = go.Figure(_balken(kanten, anzahl, FARBE_BALKEN, "Läufe"))
    fig.add_vline(x=h, line=dict(color=K.FARBE_ZIEL, width=2))
    fig.add_annotation(x=h, y=1, yref="paper", text="wahres Mittel H", showarrow=False, xanchor="left", font=dict(color=K.FARBE_ZIEL), bgcolor="rgba(255,255,255,0.8)")
    if K_schritt is not None:
        fig.add_vline(x=K_schritt, line=dict(color=K.FARBE_START, width=2, dash="dash"))
        fig.add_annotation(x=K_schritt, y=0.85, yref="paper", text="Abbruch K", showarrow=False, xanchor="left", font=dict(color=K.FARBE_START),
                           bgcolor="rgba(255,255,255,0.8)")
    return _layout(fig, 320, "Schritte je Lauf (letzte Klasse: alle längeren)", "Läufe")


def abbruch_text(c: str) -> str:
    return "ohne Abbruch" if c == C.ABBRUCH_OHNE else f"nach {c}·H"
