"""Karte: ein Punkt je Platz mit seiner Nummer in customdata, Beschriftung als Annotation, gesperrte Achsen, volle Deckkraft bei Auswahl."""

import trz_karte as K
import trz_netze as N


def _knotenspur(fig):
    return next(t for t in fig.data if t.customdata is not None)


def test_knoten_und_kanten():
    g = N.handnetz(1)
    fig = K.karte(g, marken={0: ("u", K.FARBE_START), 2: ("v", K.FARBE_ZIEL)}, neue_kante=(0, 5))
    spur = _knotenspur(fig)
    assert list(spur.customdata) == list(range(6)) and len(spur.x) == 6
    assert spur.selected.marker.opacity == 1 and spur.unselected.marker.opacity == 1
    kanten = fig.data[0]
    assert sum(x is None for x in kanten.x) == 7
    assert any(t.line.dash == "dash" for t in fig.data if t.mode == "lines")
    texte = [a.text for a in fig.layout.annotations]
    assert [str(i) for i in range(6)] == texte[:6] and "<b>u</b>" in texte and "<b>v</b>" in texte
    assert fig.layout.xaxis.fixedrange and fig.layout.yaxis.fixedrange and fig.layout.yaxis.scaleanchor == "x"
    assert not any(t.mode == "text" for t in fig.data)


def test_farbwerte_und_grosse_netze():
    g = N.zwei_hallen(8)
    fig = K.karte(g, werte=range(g.n), farbtitel="x")
    spur = _knotenspur(fig)
    assert spur.marker.showscale and len(spur.marker.color) == 128
    assert len(fig.layout.annotations) == 0                      # keine Nummern bei großen Netzen
    assert K.knotengroesse(6) > K.knotengroesse(128)
