"""Vorrechnung der Messreihen, die nicht live gerechnet werden: schreibt daten/vorgerechnet.json.

Aufruf (aus dem Demo-Ordner): python tools/vorrechnen.py [atlas] [abstand] [deckung] [streuung]  (ohne Angabe: alles)
Die Zählung über den Graphen-Atlas braucht networkx (requirements-dev.txt). `tests/test_claims.py` rechnet die Werte nach (die Deckungsmessung stichprobenweise).
"""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import trz_abbruch as AB  # noqa: E402
import trz_asymmetrie as AS  # noqa: E402
import trz_constants as C  # noqa: E402
import trz_netze as N  # noqa: E402
import trz_szenario as S  # noqa: E402
import trz_trefferzeit as T  # noqa: E402

ZIEL = ROOT / "daten" / "vorgerechnet.json"
LAENGER = 1 + 1e-9      # „länger“: um mehr als 1e-9 relativ


def atlas_netze(kleinste: int = 3, groesste: int = 7):
    """Alle zusammenhängenden, nicht isomorphen Graphen mit `kleinste` bis `groesste` Knoten (Graphen-Atlas aus networkx)."""
    import networkx as nx

    for g in nx.graph_atlas_g():
        n = g.number_of_nodes()
        if kleinste <= n <= groesste and nx.is_connected(g):
            yield N.netz("atlas", n, [tuple(sorted(e)) for e in g.edges()])


def atlas_zaehlung() -> dict:
    """Jede fehlende Kante jedes Graphen einzeln ergänzt."""
    graphen = ergaenzungen = irgendeins_laenger = endpunkt_laenger = mittel_laenger = zufallsziel_laenger = paare_laenger = paare = 0
    anteile, groesster_faktor, kleinstes = [], 1.0, None
    for g in atlas_netze():
        graphen += 1
        H = T.treffer_matrix(g)
        maske = ~np.eye(g.n, dtype=bool)
        mittel, zz = T.mittlere_trefferzeit(H), T.zufallsziel(g, H)[0]
        for a, b in N.fehlende_kanten(g):
            neu = N.mit_kante(g, a, b)
            H2 = T.treffer_matrix(neu)
            laenger = H2[maske] > H[maske] * LAENGER
            ergaenzungen += 1
            irgendeins_laenger += bool(laenger.any())
            endpunkt_laenger += bool(H2[a, b] > H[a, b] * (1 - 1e-9) or H2[b, a] > H[b, a] * (1 - 1e-9))
            paare_laenger += int(laenger.sum())
            paare += int(maske.sum())
            anteile.append(laenger.mean())
            groesster_faktor = max(groesster_faktor, float((H2[maske] / H[maske]).max()))
            mittel2 = T.mittlere_trefferzeit(H2)
            if mittel2 > mittel * LAENGER:
                mittel_laenger += 1
                if kleinstes is None or (g.n, len(g.kanten)) < (kleinstes["knoten"], kleinstes["kanten"]):
                    kleinstes = {"knoten": g.n, "kanten": len(g.kanten), "vorher": mittel, "nachher": mittel2}
            zufallsziel_laenger += bool(T.zufallsziel(neu, H2)[0] > zz * LAENGER)
    return {"graphen": graphen, "ergaenzungen": ergaenzungen, "mindestens_eins_laenger": irgendeins_laenger, "endpunkte_nicht_kuerzer": endpunkt_laenger,
            "mittel_laenger": mittel_laenger, "zufallsziel_laenger": zufallsziel_laenger, "paare_laenger": paare_laenger, "paare": paare,
            "mittlerer_anteil_je_ergaenzung": float(np.mean(anteile)), "groesster_faktor": groesster_faktor, "kleinstes_mit_laengerem_mittel": kleinstes}


def abstand_tabelle(a: int = C.ABSTAND_A, c: int = C.ABSTAND_C) -> dict:
    """Zwei Hallen a×a, alle geordneten Paare, Abbruch nach c·H: Anteil des Erwartungswerts am wahren Mittel, gruppiert nach „Abstand mindestens“."""
    g = N.zwei_hallen(a)
    H = T.treffer_matrix(g)
    anteil, rest = AB.alle_paare_gedeckelt(g, c, H)
    D = AS.abstaende(g)
    maske = ~np.eye(g.n, dtype=bool)
    zeilen = []
    for d in C.ABSTAENDE:
        m = maske & (D >= d)
        zeilen.append({"abstand_mindestens": d, "paare": int(m.sum()), "kleinster_anteil": float(anteil[m].min()), "median_anteil": float(np.median(anteil[m])),
                       "anteil_unter_90": float(np.mean(anteil[m] < 0.9)), "abbruch_groesster": float(rest[m].max())})
    return {"a": a, "c": c, "durchmesser": int(D.max()), "zeilen": zeilen}


def deckung_faelle():
    faelle = [(C.NETZ_HAND, C.DEFAULT_A)] + [(C.NETZ_HALLEN, a) for a in range(C.A_MIN, C.A_MAX + 1)] + [(C.NETZ_SAAL, C.DEFAULT_A)]
    return [(netz, a, paar) for netz, a in faelle for paar in (C.PAAR_CV, C.PAAR_TUER)]


def deckung_fall(nummer: int, netz: str, a: int, paar: str, wiederholungen: int = C.DECKUNG_WIEDERHOLUNGEN) -> dict:
    """Deckungsgrad der Läufe-Vorgabe: Anteil der Wiederholungen, in denen das Mittel aus R Läufen höchstens 10 % neben H liegt."""
    g = S.netz_fuer(netz, a)
    if paar == C.PAAR_CV:
        H, CV = AB.momente_alle(g)
        u, v = AS.groesstes_paar(CV)
    else:
        u, v = S.tuerpaar(netz, a)
    h, cv = AB.momente_zu_ziel(g, v)
    R = AB.laeufe_vorgabe(cv[u])
    F = AB.verteilungsfunktion(g, u, v)
    anteil = AB.deckungsgrad(F, h[u], R, wiederholungen, C.DECKUNG_SEED + nummer)
    return {"netz": netz, "a": a, "paar": paar, "u": u, "v": v, "h": float(h[u]), "cv": float(cv[u]), "laeufe": R, "wiederholungen": wiederholungen,
            "anteil": anteil}


def streuung_tabelle() -> dict:
    """Zwei Hallen 8×8, Paar mit größter Streuung, Abbruch nach 3·H: Quantile beider Schätzer aus endlich vielen Läufen."""
    g = N.zwei_hallen(8)
    H, CV = AB.momente_alle(g)
    u, v = AS.groesstes_paar(CV)
    K = AB.abbruch_schritt(3, H[u, v])
    F = AB.verteilungsfunktion(g, u, v)
    zeilen = [{"laeufe": R, **AB.kappungsstreuung(F, H[u, v], K, R, C.DECKUNG_WIEDERHOLUNGEN, C.STREUUNG_SEED + i)} for i, R in enumerate(C.STREUUNG_LAEUFE)]
    return {"a": 8, "c": 3, "u": u, "v": v, "K": K, "wiederholungen": C.DECKUNG_WIEDERHOLUNGEN, "zeilen": zeilen}


def main(teile):
    daten = json.loads(ZIEL.read_text(encoding="utf-8")) if ZIEL.exists() else {}
    if "atlas" in teile:
        daten["atlas"] = atlas_zaehlung()
        print("atlas", daten["atlas"], flush=True)
    if "abstand" in teile:
        daten["abstand"] = abstand_tabelle()
        print("abstand", daten["abstand"], flush=True)
    if "deckung" in teile:
        daten["deckung"] = []
        for i, fall in enumerate(deckung_faelle()):
            daten["deckung"].append(deckung_fall(i, *fall))
            print("deckung", daten["deckung"][-1], flush=True)
    if "streuung" in teile:
        daten["streuung"] = streuung_tabelle()
        print("streuung", daten["streuung"], flush=True)
    ZIEL.parent.mkdir(exist_ok=True)
    ZIEL.write_text(json.dumps(daten, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main(sys.argv[1:] or ["atlas", "abstand", "deckung", "streuung"])
