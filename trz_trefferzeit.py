"""Trefferzeiten H(u, v) der einfachen, nicht trägen Irrfahrt auf einem zusammenhängenden, einfachen, ungerichteten Netz (ohne Streamlit).

Gemeinsamer Baustein der Reihe „Irrfahrten auf Netzen“: zum Kopieren in spätere Demos. Braucht `trz_netze`.

H(u, v) = erwartete Zahl der Schritte von u bis zum ersten Besuch von v; H(v, v) = 0. Drei Rechenwege:
1. `treffer_matrix` (dicht, ein System): Fundamentalmatrix Z = (I − P + 1πᵀ)⁻¹, H(u, v) = (Z_vv − Z_uv) / π_v.
2. `treffer_zu_ziel` / `treffer_je_ziel` (je Ziel ein Gleichungssystem h = 1 + P h mit h(v) = 0), dicht oder dünn besetzt.
3. `treffer_ueber_widerstand` (Tetali-Formel über die effektiven Widerstände aus dem geerdeten Laplace; kein `pinv`).
`residuum` prüft ein Ergebnis an der definierenden Gleichung (unabhängig vom Rechenweg, auch in der App benutzt).
"""

import numpy as np

import trz_netze as N


def _pruefe(g: N.Netz) -> None:
    if g.n < 2 or not N.ist_zusammenhaengend(g):
        raise ValueError("Trefferzeiten nur für zusammenhängende Netze mit mindestens 2 Knoten")


def stationaer(g: N.Netz) -> np.ndarray:
    """Stationäre Verteilung der Irrfahrt: π(v) = Grad(v) / (2·Kantenzahl)."""
    d = N.grade(g).astype(float)
    return d / d.sum()


def uebergang(g: N.Netz, traege: bool = False) -> np.ndarray:
    """Übergangsmatrix: gleich wahrscheinlich zu jedem Nachbarn; träge: mit ½ stehen bleiben."""
    _pruefe(g)
    A = N.adjazenz(g)
    P = A / A.sum(axis=1, keepdims=True)
    return (P + np.eye(g.n)) / 2 if traege else P


def treffer_matrix(g: N.Netz, traege: bool = False) -> np.ndarray:
    """Alle Trefferzeiten auf einmal aus der Fundamentalmatrix (eine n×n-Inversion)."""
    P = uebergang(g, traege)
    pi = stationaer(g)
    Z = np.linalg.inv(np.eye(g.n) - P + np.outer(np.ones(g.n), pi))
    H = (np.diag(Z)[None, :] - Z) / pi[None, :]
    np.fill_diagonal(H, 0.0)
    return H


def treffer_zu_ziel(g: N.Netz, v: int, duenn: bool = False) -> np.ndarray:
    """Spalte H(·, v) aus einem Gleichungssystem je Ziel.

    dicht: (I − Q) h = 1 mit Q = P ohne Zeile und Spalte v. dünn: dasselbe mit den Graden multipliziert, (D − A) h = d, also der an v geerdete Laplace als
    dünn besetzte Matrix (scipy)."""
    _pruefe(g)
    rest = [u for u in range(g.n) if u != v]
    h = np.zeros(g.n)
    if duenn:
        from scipy.sparse import csc_matrix, diags
        from scipy.sparse.linalg import spsolve

        k = np.array(g.kanten)
        zeilen = np.concatenate([k[:, 0], k[:, 1]])
        spalten = np.concatenate([k[:, 1], k[:, 0]])
        A = csc_matrix((np.ones(len(zeilen)), (zeilen, spalten)), shape=(g.n, g.n))
        d = N.grade(g).astype(float)
        L = (diags(d) - A).tocsc()[rest, :][:, rest]
        h[rest] = np.atleast_1d(spsolve(L.tocsc(), d[rest]))
    else:
        Q = uebergang(g)[np.ix_(rest, rest)]
        h[rest] = np.linalg.solve(np.eye(g.n - 1) - Q, np.ones(g.n - 1))
    return h


def treffer_je_ziel(g: N.Netz, duenn: bool = False) -> np.ndarray:
    """Alle Trefferzeiten, je Ziel ein Gleichungssystem (zweiter Rechenweg zu `treffer_matrix`)."""
    return np.column_stack([treffer_zu_ziel(g, v, duenn) for v in range(g.n)])


def widerstand_matrix(g: N.Netz) -> np.ndarray:
    """Effektive Widerstände (jede Kante 1 Ohm) aus dem am letzten Knoten geerdeten Laplace: R_uv = M_uu + M_vv − 2·M_uv."""
    _pruefe(g)
    A = N.adjazenz(g)
    L = np.diag(A.sum(axis=1)) - A
    M = np.zeros((g.n, g.n))
    M[:-1, :-1] = np.linalg.inv(L[:-1, :-1])
    diag = np.diag(M)
    R = diag[:, None] + diag[None, :] - 2 * M
    np.fill_diagonal(R, 0.0)
    return R


def treffer_ueber_widerstand(g: N.Netz) -> np.ndarray:
    """Tetali-Formel: H(u, v) = ½ Σ_w d_w (R_uv + R_vw − R_uw)."""
    R = widerstand_matrix(g)
    d = N.grade(g).astype(float)
    s = R @ d                                                        # s[x] = Σ_w d_w R_xw
    H = 0.5 * (d.sum() * R + s[None, :] - s[:, None])
    np.fill_diagonal(H, 0.0)
    return H


def zeit_von_stationaer(g: N.Netz, H: np.ndarray) -> np.ndarray:
    """H(π, v) je Ziel v: Trefferzeit von v ab einem nach π gezogenen Start."""
    return stationaer(g) @ H


def zufallsziel(g: N.Netz, H: np.ndarray) -> np.ndarray:
    """Σ_v π(v)·H(u, v) je Start u: Zeit bis zu einem nach π gezogenen Ziel."""
    return H @ stationaer(g)


def mittlere_trefferzeit(H: np.ndarray) -> float:
    """Mittel über alle geordneten Paare u ≠ v, jedes gleich gewichtet."""
    n = len(H)
    return float(H.sum() / (n * (n - 1)))


def fluchtwahrscheinlichkeit(g: N.Netz, a: int, b: int) -> float:
    """Wahrscheinlichkeit, ab a den Knoten b vor der Rückkehr nach a zu erreichen (harmonische Werte f mit f(a) = 0, f(b) = 1)."""
    P = uebergang(g)
    frei = [x for x in range(g.n) if x not in (a, b)]
    f = np.zeros(g.n)
    f[b] = 1.0
    if frei:
        f[frei] = np.linalg.solve(np.eye(len(frei)) - P[np.ix_(frei, frei)], P[frei, b])
    return float(P[a] @ f)


def residuum(g: N.Netz, H: np.ndarray) -> float:
    """Größte relative Verletzung der definierenden Gleichung H(u, v) = 1 + Mittel der H(w, v) über die Nachbarn w von u (u ≠ v) und H(v, v) = 0."""
    rest = H - 1.0 - uebergang(g) @ H
    np.fill_diagonal(rest, 0.0)
    return float(max(np.abs(rest).max(), np.abs(np.diag(H)).max()) / max(1.0, float(np.abs(H).max())))
