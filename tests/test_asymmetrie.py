"""Reihung, Gleichstände, Gegner zur Reihung und zur Schätzung: jeweils gegen einfache Aufzählung bzw. Rastersuche."""

import itertools

import numpy as np
import pytest

import trz_asymmetrie as AS
import trz_constants as C
import trz_netze as N
import trz_szenario as S
import trz_trefferzeit as T


def test_48_von_720_reihenfolgen(hand):
    H = T.treffer_matrix(hand)
    hpi = T.zeit_von_stationaer(hand, H)
    stimmig = [o for o in itertools.permutations(range(6)) if all(H[o[i], o[j]] <= H[o[j], o[i]] + 1e-9 for i in range(6) for j in range(i + 1, 6))]
    assert len(stimmig) == 48 == AS.zahl_stimmiger_reihenfolgen(hpi)
    assert sorted(map(sorted, AS.gleichstandsgruppen(hpi))) == [[0, 1, 4, 5], [2, 3]]
    assert all(hpi[o[i]] >= hpi[o[i + 1]] - 1e-9 for o in stimmig for i in range(5))


def test_verhaeltnisse_und_groesstes_paar(hand):
    H = T.treffer_matrix(hand)
    q = AS.verhaeltnisse(H)
    assert len(q) == 15 and q.max() == pytest.approx(11 / 3)
    u, v, groesstes = AS.groesstes_verhaeltnis(H)
    assert (u, v) == (2, 0) and groesstes == pytest.approx(11 / 3)            # bei Gleichstand das kleinste (u, v)
    assert AS.asymmetrisch(H).sum() == 8                                      # Ecke–Tür: 4 · 2
    assert AS.groesstes_paar(np.array([[0.0, 2.0, 2.0], [2.0, 0.0, 1.0], [1.0, 1.0, 0.0]])) == (0, 1)


def test_abstaende(hand):
    D = AS.abstaende(hand)
    assert D[0, 5] == 3 and D[0, 2] == 1 and (D == D.T).all()


def _ordnung_per_schleife(g, H):
    d = N.grade(g)
    D = AS.abstaende(g)
    summe = [sum(int(d[w]) * int(D[w, v]) for w in range(g.n)) for v in range(g.n)]
    asym = gleich = grad = beide = 0
    for u in range(g.n):
        for v in range(u + 1, g.n):
            if abs(H[u, v] - H[v, u]) <= 1e-9 * max(H[u, v], H[v, u]):
                continue
            asym += 1
            kurz = (u, v) if H[u, v] < H[v, u] else (v, u)        # (von, nach) der kürzeren Richtung
            von, nach = kurz
            gleich += d[u] == d[v]
            grad += d[nach] > d[von]
            beide += d[nach] > d[von] or (d[nach] == d[von] and summe[nach] < summe[von])
    return asym, gleich, grad, beide


@pytest.mark.parametrize("g", [N.zwei_hallen(3), N.zwei_hallen(5), N.saal_mit_stichgang(6, 3), N.handnetz(1)], ids=lambda g: g.name)
def test_ordnungsregeln_gegen_schleife(g):
    H = T.treffer_matrix(g)
    z = AS.ordnungsregeln(g, H, T.zeit_von_stationaer(g, H))
    assert (z["asymmetrisch"], z["gradgleich"], z["grad_richtig"], z["beide_richtig"]) == _ordnung_per_schleife(g, H)
    assert z["hpi_richtig"] == z["asymmetrisch"]


def _median_fehler(x, klasse, faktoren):
    """Der angezeigte Fehler: np.median von |c·x − 1| (bei gerader Anzahl das Mittel der beiden mittleren Werte)."""
    return float(np.median(np.abs(np.array([faktoren[int(k)] for k in klasse]) * x - 1)))


def _raster_median(x, klasse, stellen_c=40_001, stellen_s=41):
    """Zweiter Rechenweg: je Klasse ein Faktor aus einem dichten Raster. Gezählt wird nur, wie viele Fehler höchstens s sind (Binärsuche in den sortierten x).

    Der Median ist (s + t) / 2 mit s = h-kleinster und t = (h+1)-kleinster Fehler (N = 2h, bei ungeradem N ist s = t). (s, t) ist erreichbar, wenn Faktoren je
    Klasse zusammen mindestens h Fehler ≤ s liefern und dabei insgesamt mindestens h+1 Fehler ≤ t. Über s wird ein Raster gelegt, t je s durch Halbierung gesucht.
    Das Ergebnis ist eine obere Schranke an das wahre Minimum."""
    n = len(x)
    h, voll = (n + 1) // 2, n // 2 + 1
    teile = []
    for k in sorted(set(klasse.tolist())):
        xs = np.sort(x[klasse == k])
        kandidaten = np.linspace((1 / xs).min() * 0.3, (1 / np.quantile(xs, 0.02)) * 1.3, stellen_c)
        teile.append((xs, kandidaten))

    def zaehle(xs, c, s):
        return np.searchsorted(xs, (1 + s) / c, side="right") - np.searchsorted(xs, (1 - s) / c, side="left")

    def erreichbar(je_s, s, t):
        beste = [int(z.max()) for z in je_s]
        if sum(beste) < h:
            return False
        if s == t and sum(beste) >= voll:
            return True
        for i, (xs, c) in enumerate(teile):
            zt = zaehle(xs, c, t)
            rest = sum(beste) - beste[i]
            maske = zt >= je_s[i] + 1                       # in dieser Klasse liegt bei t ein Punkt mehr
            if maske.any() and rest + int(je_s[i][maske].max()) >= h:
                return True
        return sum(int(zaehle(xs, c, t).max()) for xs, c in teile) >= voll and sum(beste) >= voll

    def kleinstes_s(ziel):
        lo, hi = 0.0, 4.0
        for _ in range(40):
            m = (lo + hi) / 2
            if sum(int(zaehle(xs, c, m).max()) for xs, c in teile) >= ziel:
                hi = m
            else:
                lo = m
        return hi

    s0, s1 = kleinstes_s(h), kleinstes_s(voll)
    if h == voll:                                            # ungerade Anzahl: ein Wert
        return s1
    beste_summe = 2 * s1
    for s in np.linspace(s0, s1, stellen_s):
        je_s = [zaehle(xs, c, s) for xs, c in teile]
        lo, hi = s, 2 * s1 - s
        if hi < lo or not erreichbar(je_s, s, hi):
            continue
        for _ in range(30):
            m = (lo + hi) / 2
            lo, hi = (lo, m) if erreichbar(je_s, s, m) else (m, hi)
        beste_summe = min(beste_summe, s + hi)
    return beste_summe / 2


APP_NETZE = [("hand", 8)] + [("hallen", a) for a in range(C.A_MIN, C.A_MAX + 1)] + [("saal", 8)]


def _punkte(netz, a):
    g = S.netz_fuer(netz, a)
    H = T.treffer_matrix(g)
    maske = ~np.eye(g.n, dtype=bool)
    d = N.grade(g)
    ziel = np.broadcast_to(d, (g.n, g.n))[maske]
    return g, H, d.sum() / ziel / H[maske], ziel


@pytest.mark.parametrize("netz,a", APP_NETZE, ids=[f"{n}-{a}" for n, a in APP_NETZE])
def test_bester_vorfaktor_minimiert_den_angezeigten_median(netz, a):
    """Alle Netze und Größen der App, ein Vorfaktor: dichtes Raster über c, ausgewertet mit np.median selbst (grob, dann zweimal verfeinert um die zehn besten)."""
    g, H, x, _ = _punkte(netz, a)
    f = AS.formel_gegner(g, H)
    klasse = np.zeros(len(x), dtype=int)
    assert f["mit_faktor"] == pytest.approx(_median_fehler(x, klasse, {0: f["faktor"]}), abs=1e-9)
    c = np.linspace(0.2 / np.quantile(x, 0.9), 3 / np.quantile(x, 0.1), 4001)
    schritt = c[1] - c[0]
    werte = np.array([np.median(np.abs(k * x - 1)) for k in c])
    bester = werte.min()
    for k in c[np.argsort(werte)[:10]]:
        fein = np.linspace(k - schritt, k + schritt, 201)
        w = np.array([np.median(np.abs(z * x - 1)) for z in fein])
        sehr_fein = np.linspace(fein[w.argmin()] - schritt / 100, fein[w.argmin()] + schritt / 100, 201)
        bester = min(bester, w.min(), min(np.median(np.abs(z * x - 1)) for z in sehr_fein))
    assert f["mit_faktor"] <= bester + 1e-12, (f["mit_faktor"], bester)       # nie schlechter als das Raster
    assert f["mit_faktor"] >= bester - 1e-4                                   # und das Raster kommt heran


@pytest.mark.parametrize("netz,a", APP_NETZE, ids=[f"{n}-{a}" for n, a in APP_NETZE])
def test_beste_faktoren_je_zielgrad_gegen_rastersuche(netz, a):
    """Alle Netze und Größen der App, ein Faktor je Zielgrad (und als Gegenprobe einer für alle) gegen den zweiten Rechenweg."""
    g, H, x, ziel = _punkte(netz, a)
    f = AS.formel_gegner(g, H)
    assert f["mit_je_grad"] == pytest.approx(_median_fehler(x, ziel, f["je_grad"]), abs=1e-9)
    for klasse, fehler in ((ziel, f["mit_je_grad"]), (np.zeros(len(x), dtype=int), f["mit_faktor"])):
        raster = _raster_median(x, klasse)
        assert fehler <= raster + 1e-9, (fehler, raster)
        assert fehler >= raster - 2e-3


def test_saal_bester_vorfaktor_bestaetigter_sollwert():
    g, H, _, _ = _punkte("saal", 8)
    f = AS.formel_gegner(g, H)
    assert f["faktor"] == pytest.approx(1.4409, abs=1e-4)
    assert f["mit_faktor"] == pytest.approx(0.5476, abs=1e-4)


def _zwei_klassen_raster(x, klasse, stellen=1201):
    """Vollständiges zweidimensionales Raster über (c0, c1) für kleine Zufallsbeispiele."""
    c = np.linspace(0.2, 6.0, stellen)
    e0 = np.abs(np.outer(c, x[klasse == 0]) - 1)
    e1 = np.abs(np.outer(c, x[klasse == 1]) - 1)
    beste = np.inf
    for zeile in e0:
        alle = np.concatenate([np.broadcast_to(zeile, (stellen, len(zeile))), e1], axis=1)
        beste = min(beste, np.median(alle, axis=1).min())
    return float(beste), float(c[1] - c[0])


@pytest.mark.parametrize("seed", range(24))
def test_beste_faktoren_kleine_zufallsbeispiele(seed):
    """Gerade und ungerade Anzahl, eine und zwei Klassen: gegen das vollständige Raster."""
    rng = np.random.default_rng(seed)
    n = int(rng.integers(4, 13))
    x = rng.uniform(0.3, 2.5, n)
    klasse = rng.integers(0, 2, n)
    klasse[0], klasse[1] = 0, 1
    fehler = _median_fehler(x, klasse, AS.passe_faktoren_an(x, klasse))
    raster, schritt = _zwei_klassen_raster(x, klasse)
    assert fehler <= raster + 1e-9, (fehler, raster)
    assert fehler >= raster - schritt * x.max()                             # Fehler ändert sich je c-Schritt höchstens um Schritt·max x
    eine = np.zeros(n, dtype=int)
    c = np.linspace(0.2, 6.0, 100_001)
    raster1 = float(np.median(np.abs(np.outer(c, x) - 1), axis=1).min())
    fehler1 = _median_fehler(x, eine, AS.passe_faktoren_an(x, eine))
    assert fehler1 <= raster1 + 1e-9 and fehler1 >= raster1 - (c[1] - c[0]) * x.max()


def test_formel_gegner_reihenfolge_der_fehler():
    g = N.zwei_hallen(4)
    f = AS.formel_gegner(g, T.treffer_matrix(g))
    assert f["mit_je_grad"] <= f["mit_faktor"] + 1e-9 <= f["roh"] + 1e-9
    assert set(f["je_grad"]) == {2, 3, 4}
