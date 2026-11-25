"""Kennzahlen der vier Experimente und die Verdikte (reine Funktionen, ohne Streamlit).

Alle Zeiten sind erwartete Schritte der einfachen, nicht trägen Irrfahrt auf einem zusammenhängenden, einfachen, ungerichteten Netz. „Länger“ heißt: um mehr als
1e-9 relativ größer. Anteile über Paare zählen geordnete Paare (u, v) mit u ≠ v, wo nicht „ungeordnet“ dasteht.
"""

from dataclasses import dataclass

import numpy as np

import trz_abbruch as AB
import trz_asymmetrie as AS
import trz_constants as C
import trz_netze as N
import trz_szenario as S
import trz_trefferzeit as T
from trz_irrfahrt_sim import simuliere_trefferzeiten

LAENGER = 1e-9


@dataclass(frozen=True)
class Settings:
    netz: str = C.NETZ_HAND
    a: int = C.DEFAULT_A
    u: int = 0
    v: int = 2
    kante: str = C.KANTE_TUER
    r: int = 0
    ka: int = 0
    kb: int = 4
    paar: str = C.PAAR_CV
    laeufe: int = C.DEFAULT_LAEUFE
    abbruch: str = "3"
    seed: int = C.DEFAULT_SEED


# ----------------------------------------------------------------------------------------------------------------------------------
# Zahlen als Text
# ----------------------------------------------------------------------------------------------------------------------------------

def de(x: float, stellen: int = 2) -> str:
    """Zahl mit Dezimalkomma, Tausender mit Leerzeichen."""
    return f"{x:,.{stellen}f}".replace(",", " ").replace(".", ",")


def ganz(x: int) -> str:
    return f"{int(x):,}".replace(",", " ")


def laeufe_text(r: int, dativ: bool = False) -> str:
    """„1 Lauf“, sonst „n Läufe“ (im Dativ „n Läufen“)."""
    return "1 Lauf" if int(r) == 1 else f"{ganz(r)} {'Läufen' if dativ else 'Läufe'}"


def zeit(h: float) -> str:
    """Eine Trefferzeit: unter 100 Schritten mit zwei, unter 1 000 mit einer Nachkommastelle, darüber ganz."""
    return de(h, 2 if abs(h) < 99.995 else (1 if abs(h) < 999.95 else 0))


def prozent(x: float, stellen: int = 0) -> str:
    return f"{de(100 * x, stellen)} %"


# ----------------------------------------------------------------------------------------------------------------------------------
# Netz und Ansicht oben
# ----------------------------------------------------------------------------------------------------------------------------------

@dataclass
class Netzanalyse:
    netz: str
    a: int
    g: N.Netz
    H: np.ndarray
    pi: np.ndarray
    hpi: np.ndarray          # H(π, v) je Ziel
    zufallsziel: np.ndarray  # Σ_v π(v) H(u, v) je Start
    mittel: float
    residuum: float


def analysiere_netz(netz: str, a: int) -> Netzanalyse:
    g = S.netz_fuer(netz, a)
    H = T.treffer_matrix(g)
    return Netzanalyse(netz, a, g, H, T.stationaer(g), T.zeit_von_stationaer(g, H), T.zufallsziel(g, H), T.mittlere_trefferzeit(H), T.residuum(g, H))


def richtungen(an: Netzanalyse, u: int, v: int) -> dict:
    hin, her = float(an.H[u, v]), float(an.H[v, u])
    verh = max(hin, her) / min(hin, her) if u != v else None
    return {"hin": hin, "her": her, "verhaeltnis": verh, "zufallsziel": float(an.zufallsziel[u]), "hpi_u": float(an.hpi[u]), "hpi_v": float(an.hpi[v])}


def kuerzere_richtung(an: Netzanalyse, u: int, v: int) -> int:
    """+1: u → v ist kürzer, −1: v → u ist kürzer, 0: beide gleich (relativ 1e-9)."""
    hin, her = an.H[u, v], an.H[v, u]
    if abs(hin - her) <= AS.GLEICH_REL * max(hin, her, 1.0):
        return 0
    return 1 if hin < her else -1


def verdict_ansicht(an: Netzanalyse, u: int, v: int):
    a, b = an.g.knoten[u], an.g.knoten[v]
    if u == v:
        return "info", "Start und Ziel sind derselbe Platz: die Trefferzeit ist 0. Bitte zwei verschiedene Plätze wählen."
    r = richtungen(an, u, v)
    richtung = kuerzere_richtung(an, u, v)
    if richtung == 0:
        return "info", f"Zwischen {a} und {b} sind beide Richtungen gleich lang: je {zeit(r['hin'])} erwartete Schritte."
    kurz, lang = (a, b) if richtung == 1 else (b, a)
    return "warning", (f"Hin ist nicht zurück: von {kurz} nach {lang} im Mittel {zeit(min(r['hin'], r['her']))} Schritte, von {lang} nach {kurz} im Mittel "
                       f"{zeit(max(r['hin'], r['her']))} (Verhältnis {de(r['verhaeltnis'], 2)}).")


# ----------------------------------------------------------------------------------------------------------------------------------
# Experiment 1: Asymmetrie und die Faustformel
# ----------------------------------------------------------------------------------------------------------------------------------

def asymmetrie(an: Netzanalyse) -> dict:
    q = AS.verhaeltnisse(an.H)
    lang_u, lang_v, groesstes = AS.groesstes_verhaeltnis(an.H)
    return {"verhaeltnisse": q, "median": float(np.median(q)), "q90": float(np.quantile(q, 0.9)), "groesstes": groesstes, "paar": (lang_u, lang_v),
            "paare": len(q), "asymmetrisch": int(AS.asymmetrisch(an.H).sum()), "formel": AS.formel_gegner(an.g, an.H)}


def formel_zeilen(an: Netzanalyse, formel: dict, u: int, v: int) -> list:
    """Die drei Faustformel-Varianten neben dem exakten Wert für beide Richtungen des gewählten Paars."""
    d = N.grade(an.g)
    zeilen = []
    for von, nach in ((u, v), (v, u)):
        roh = formel["zwei_m"] / d[nach]
        zeilen.append({"richtung": f"{an.g.knoten[von]} → {an.g.knoten[nach]}", "exakt": float(an.H[von, nach]), "grad_ziel": int(d[nach]), "roh": float(roh),
                       "mit_faktor": float(formel["faktor"] * roh), "je_grad": float(formel["je_grad"][int(d[nach])] * roh)})
    return zeilen


def verdict_asymmetrie(median: float, groesstes: float, roh: float, mit_faktor: float, mit_je_grad: float):
    if groesstes <= 1 + 1e-9:
        return "info", "Auf diesem Netz sind alle Paare symmetrisch: hin und zurück sind gleich lang."
    art = "warning" if mit_faktor >= 0.2 else "info"
    return art, (f"Median-Verhältnis {de(median, 2)}, größtes {de(groesstes, 2)}. Die Faustformel 2m/d_Ziel liegt im Median {prozent(roh)} daneben; "
                 f"auch mit dem besten Vorfaktor bleiben {prozent(mit_faktor)}, mit einem eigenen Wert je Zielgrad {prozent(mit_je_grad)}.")


# ----------------------------------------------------------------------------------------------------------------------------------
# Experiment 2: eine Reihenfolge für alle Paare
# ----------------------------------------------------------------------------------------------------------------------------------

def ordnung(an: Netzanalyse) -> dict:
    z = AS.ordnungsregeln(an.g, an.H, an.hpi)
    gruppen = AS.gleichstandsgruppen(an.hpi)
    z["gruppen"] = gruppen
    z["stimmige_reihenfolgen"] = AS.zahl_stimmiger_reihenfolgen(an.hpi)
    z["zz_min"], z["zz_max"] = float(an.zufallsziel.min()), float(an.zufallsziel.max())
    return z


def verdict_ordnung(asymmetrisch: int, gradgleich: int, grad_richtig: int, beide_richtig: int, hpi_richtig: int):
    if asymmetrisch == 0:
        return "info", "Auf diesem Netz sind alle Paare symmetrisch; es gibt nichts zu reihen."
    if hpi_richtig != asymmetrisch:
        return "error", f"Prüfung verletzt: H(π,·) ordnet nur {ganz(hpi_richtig)} von {ganz(asymmetrisch)} asymmetrischen Paaren richtig."
    if gradgleich == 0:
        grad = f"Der Grad allein lässt hier kein asymmetrisches Paar offen und ordnet {prozent(grad_richtig / asymmetrisch)} richtig"
    else:
        grad = f"Der Grad allein lässt {prozent(gradgleich / asymmetrisch)} der asymmetrischen Paare offen"
    return "success", ("In diesem ungerichteten Netz ist der Weg zum Knoten mit kleinerem H(π,·) nie der längere (Satz). "
                       f"{grad}; Grad und Abstand zusammen ordnen {prozent(beide_richtig / asymmetrisch)} aller asymmetrischen Paare richtig.")


# ----------------------------------------------------------------------------------------------------------------------------------
# Experiment 3: eine neue Kante
# ----------------------------------------------------------------------------------------------------------------------------------

@dataclass
class Ergaenzung:
    kante: tuple
    neu: N.Netz
    H2: np.ndarray
    laenger: np.ndarray        # Wahrheitsmatrix: H'(u, v) länger als H(u, v)
    anzahl_laenger: int
    paare: int
    ab: tuple                  # (H(a, b), H'(a, b))
    ba: tuple                  # (H(b, a), H'(b, a))
    mittel: tuple              # mittlere Trefferzeit vorher, nachher
    zufallsziel: tuple         # Zeit zum stationär gezogenen Ziel vorher, nachher
    groesster_faktor: float
    r_ab: float                # 1 / (d_a · Fluchtwahrscheinlichkeit a → b) im alten Netz
    r_ba: float
    residuum: float


def ergaenze(an: Netzanalyse, kante: tuple) -> Ergaenzung:
    a, b = kante
    neu = N.mit_kante(an.g, a, b)
    H2 = T.treffer_matrix(neu)
    maske = ~np.eye(an.g.n, dtype=bool)
    laenger = np.zeros_like(maske)
    laenger[maske] = H2[maske] > an.H[maske] * (1 + LAENGER)
    d = N.grade(an.g)
    return Ergaenzung(kante, neu, H2, laenger, int(laenger.sum()), int(maske.sum()), (float(an.H[a, b]), float(H2[a, b])), (float(an.H[b, a]), float(H2[b, a])),
                      (an.mittel, T.mittlere_trefferzeit(H2)), (float(an.zufallsziel[0]), float(T.zufallsziel(neu, H2)[0])),
                      float((H2[maske] / an.H[maske]).max()), 1.0 / (d[a] * T.fluchtwahrscheinlichkeit(an.g, a, b)),
                      1.0 / (d[b] * T.fluchtwahrscheinlichkeit(an.g, b, a)), T.residuum(neu, H2))


SATZ_NEUE_KANTE = ("Auf jedem zusammenhängenden, einfachen, ungerichteten Netz ab 3 Knoten wird durch eine neue Kante zwischen bisher nicht verbundenen Knoten "
                   "mindestens eine Trefferzeit länger, und die zwischen ihren Endpunkten wird kürzer.")


def verdict_kante(anzahl_laenger: int, paare: int, ab: tuple, ba: tuple):
    endpunkte_kuerzer = ab[1] < ab[0] and ba[1] < ba[0]
    if anzahl_laenger < 1 or not endpunkte_kuerzer:
        return "error", "Prüfung verletzt: auf diesem Netz müsste mindestens eine Trefferzeit länger und die zwischen den Endpunkten kürzer werden."
    return "info", (f"Die neue Kante macht {ganz(anzahl_laenger)} von {ganz(paare)} Trefferzeiten länger; zwischen ihren Endpunkten keine. {SATZ_NEUE_KANTE}")


def zeilen_sweep(an: Netzanalyse) -> list:
    """Nur Gitterhallen: je Zeile r ≠ a//2 die zweite Tür; höchstens a − 1 ≤ 9 zusätzliche Inversionen."""
    zeilen = []
    for r in S.tuerzeilen_neu(an.netz, an.a):
        kante, _ = S.neue_kante(an.netz, an.a, C.KANTE_TUER, r, 0, 1)
        e = ergaenze(an, kante)
        zeilen.append({"r": r, "anteil_laenger": e.anzahl_laenger / e.paare, "mittel": e.mittel[1], "zufallsziel": e.zufallsziel[1], "ab_vor": e.ab[0],
                       "ab_nach": e.ab[1], "faktor": e.groesster_faktor})
    return zeilen


def schlussstein(n: int) -> dict:
    """Weg mit n Knoten, Start am Ende, Ziel sein Nachbar: H vor und nach der Kante zwischen den beiden Enden."""
    vorher = T.treffer_zu_ziel(N.weg(n), 1)[0]
    nachher = T.treffer_zu_ziel(N.weg_mit_schlussstein(n), 1)[0]
    return {"n": n, "vorher": float(vorher), "nachher": float(nachher)}


# ----------------------------------------------------------------------------------------------------------------------------------
# Experiment 4: Probeläufe und Abbruch
# ----------------------------------------------------------------------------------------------------------------------------------

@dataclass
class Streuung:
    H: np.ndarray
    CV: np.ndarray
    cv_median: float
    cv_paar: tuple


def streuung(netz: str, a: int) -> Streuung:
    H, CV = AB.momente_alle(S.netz_fuer(netz, a))
    maske = ~np.eye(len(H), dtype=bool)
    return Streuung(H, CV, float(np.median(CV[maske])), AS.groesstes_paar(CV))


def probe_paar(settings: Settings, st_: Streuung):
    if settings.paar == C.PAAR_CV:
        return st_.cv_paar
    if settings.paar == C.PAAR_TUER:
        return S.tuerpaar(settings.netz, settings.a)
    return settings.u, settings.v


def probe_exakt(g: N.Netz, st_: Streuung, u: int, v: int, abbruch: str) -> dict:
    h, cv = float(st_.H[u, v]), float(st_.CV[u, v])
    ergebnis = {"u": u, "v": v, "h": h, "cv": cv, "laeufe_vorgabe": AB.laeufe_vorgabe(cv), "K": None, "gekappt": h, "anteil": 1.0, "abbruch": 0.0, "zensur": h}
    if abbruch != C.ABBRUCH_OHNE:
        K = AB.abbruch_schritt(float(abbruch), h)
        e, p = AB.gedeckelt(g, u, v, K)
        ergebnis.update(K=K, gekappt=e, anteil=e / h, abbruch=p, zensur=(e / (1 - p)) if p < 1 - 1e-12 else None)
    return ergebnis


def simulation_laeufe(laeufe: int, h: float) -> int:
    """Zahl der simulierten Läufe: wie gewählt, höchstens so viele, dass die erwarteten Gesamtschritte den Deckel nicht überschreiten."""
    return int(max(1, min(laeufe, C.SCHRITT_DECKEL // max(h, 1.0))))


def simuliere(g: N.Netz, u: int, v: int, laeufe: int, seed: int, K) -> dict:
    zeiten = simuliere_trefferzeiten(g, u, v, laeufe, seed)
    if (zeiten < 0).any():
        raise ValueError("ein Lauf hat die Schrittgrenze erreicht")
    return {"zeiten": zeiten, "ohne": AB.schaetzer(zeiten), "mit": AB.schaetzer(zeiten, K)}


def eckpaare() -> list:
    """Drei Paare ferner Ecken (Negativbefund), Abbruch nach 3·H."""
    faelle = [("Handnetz, 0 → 5", N.handnetz(1), 0, 5), ("Gitter 8×8, Ecke → Gegenecke", N.gitter(8), 0, 63),
              ("Zwei Hallen 8×8, L(0,0) → R(7,7)", N.zwei_hallen(8), 0, 127)]
    zeilen = []
    for name, g, u, v in faelle:
        h = float(T.treffer_zu_ziel(g, v)[u])
        e, p = AB.gedeckelt(g, u, v, AB.abbruch_schritt(3, h))
        zeilen.append({"paar": name, "h": h, "anteil": e / h, "abbruch": p})
    return zeilen


def saal_vergleich() -> dict:
    """Saal mit Stichgang 21 + 11, Paar mit der größten Streuung, Abbruch nach 3·H (Vergleichssatz im Verdikt)."""
    g = N.saal_mit_stichgang(C.SAAL, C.GANG)
    st_ = streuung(C.NETZ_SAAL, C.DEFAULT_A)
    u, v = st_.cv_paar
    return probe_exakt(g, st_, u, v, "3")


def verdict_abbruch(p: dict, abbruch: str, deckung: dict = None, vergleich: dict = None):
    if deckung is None:
        zusatz = " Wie oft die Läufe-Vorgabe bei diesem Paar das Mittel auf ±10 % trifft, ist nicht vorgerechnet."
    else:
        zusatz = (f" In {ganz(deckung['wiederholungen'])} Wiederholungen mit je {laeufe_text(deckung['laeufe'], dativ=True)} ohne Abbruch lag das Mittel in "
                  f"{prozent(deckung['anteil'], 1)} der Fälle höchstens 10 % neben H.")
    vorgabe = f" Für ±10 % bei 95 % sieht die Normalnäherung ohne Abbruch {laeufe_text(p['laeufe_vorgabe'])} vor."
    if abbruch == C.ABBRUCH_OHNE:
        return "info", (f"Ohne Abbruch ist der Erwartungswert das wahre Mittel H = {zeit(p['h'])}. Für ±10 % bei 95 % sieht die Normalnäherung "
                        f"{laeufe_text(p['laeufe_vorgabe'])} vor.{zusatz}")
    erreicht = round(100 * p["anteil"])
    fehlt = 100 - erreicht
    teil = prozent(p["abbruch"], 1)
    zensur = "" if p["zensur"] is None else f"; der zensurbewusste Schätzer kommt auf {prozent(p['zensur'] / p['h'])}"
    if p["anteil"] < 0.9:
        art = "warning"
        if p["abbruch"] < 0.1:
            kopf = f"Nur {teil} der Läufe brechen ab, und doch erreicht der Erwartungswert nur {erreicht} % des wahren Mittels ({fehlt} % fehlen)"
        else:
            kopf = f"{teil} der Läufe brechen ab, und der Erwartungswert erreicht nur {erreicht} % des wahren Mittels ({fehlt} % fehlen)"
    elif p["anteil"] < 0.95:
        art = "info"
        kopf = f"{teil} der Läufe brechen ab; der Erwartungswert erreicht {erreicht} % des wahren Mittels ({fehlt} % fehlen)"
    else:
        art = "success"
        kopf = f"Hier ist der Abbruch fast harmlos: {teil} der Läufe brechen ab, und der Erwartungswert erreicht {de(100 * p['anteil'], 1)} % des wahren Mittels"
    satz = f"{kopf}{zensur}."
    if vergleich is not None:
        satz += (f" Der Abbruchanteil sagt nicht, wie viel fehlt: Im Saal mit Stichgang 21 + 11 (Paar mit größter Streuung, Abbruch nach 3·H) brechen "
                 f"{prozent(vergleich['abbruch'], 1)} ab, und es bleiben {prozent(vergleich['anteil'])}.")
    return art, satz + vorgabe + zusatz


def verdict_negativ(ecken: list, abstand: dict):
    """Negativbefund und seine Grenze: ferne Ecken harmlos, Abstand allein schützt nicht (Zahlen aus der Rechnung bzw. der vorgerechneten Tabelle)."""
    zeile = {z["abstand_mindestens"]: z for z in abstand["zeilen"]}
    anteile = [z["anteil"] for z in ecken]
    abbruch = [z["abbruch"] for z in ecken]
    return "info", (f"In den drei Paaren ferner Ecken ist der Abbruch nach 3·H fast harmlos: Der Erwartungswert erreicht {de(100 * min(anteile), 1)} bis "
                    f"{de(100 * max(anteile), 1)} % des Mittels, abgebrochen werden {de(100 * min(abbruch), 1)} bis {de(100 * max(abbruch), 1)} % der Läufe. "
                    f"Abstand allein schützt aber nicht zuverlässig: Auf zwei Hallen 8×8 behalten unter allen geordneten Paaren mit Abstand von mindestens 8 "
                    f"einzelne nur {prozent(zeile[8]['kleinster_anteil'])} des Mittels; erst ab Abstand 15 liegt jedes Paar über "
                    f"{prozent(int(100 * zeile[15]['kleinster_anteil']) / 100)}.")


def zeigt_saalvergleich(netz: str, a: int, paar: str, abbruch: str) -> bool:
    """Der Vergleichssatz gilt für den Fall, an dem er steht: zwei Hallen 8×8, Paar mit größter Streuung, Abbruch nach 3·H."""
    return netz == C.NETZ_HALLEN and a == 8 and paar == C.PAAR_CV and abbruch == "3"


# ----------------------------------------------------------------------------------------------------------------------------------
# Kernfragen (kurze Antworten mit den Zahlen der gewählten Einstellungen)
# ----------------------------------------------------------------------------------------------------------------------------------

def kurz_warum(an: Netzanalyse, u: int, v: int) -> str:
    if u == v:
        return "Dafür braucht es zwei verschiedene Plätze."
    r = richtungen(an, u, v)
    a, b = an.g.knoten[u], an.g.knoten[v]
    gleich = kuerzere_richtung(an, u, v) == 0
    kopf = ("Bei diesem Paar sind beide Richtungen gleich lang." if gleich else
            "Weil die Irrfahrt auf dem Hinweg andere Umwege machen kann als auf dem Rückweg.")
    diff_h = 0.0 if gleich else r["hin"] - r["her"]
    diff_pi = 0.0 if gleich else r["hpi_v"] - r["hpi_u"]
    return (f"{kopf} Für jedes Paar gilt H(u,v) − H(v,u) = H(π,v) − H(π,u): Hier ist H({a},{b}) − H({b},{a}) = {zeit(diff_h)} und "
            f"H(π,{b}) − H(π,{a}) = {zeit(diff_pi)}. H(π,v) ist die mittlere Schrittzahl bis v, wenn der Start zufällig nach der stationären Verteilung "
            "(Anteil je Platz proportional zu seiner Nachbarzahl) gezogen wird.")


def kurz_wohin(an: Netzanalyse, u: int, v: int) -> str:
    richtung = kuerzere_richtung(an, u, v) if u != v else 0
    a, b = an.g.knoten[u], an.g.knoten[v]
    kopf = "Zum Platz mit dem kleineren H(π,·), also zum Platz, den ein zufälliger Start im Mittel schneller findet."
    if u == v:
        return kopf
    if richtung == 0:
        return f"{kopf} Bei {a} und {b} sind beide Werte gleich, beide Richtungen sind gleich lang."
    ziel, von = (b, a) if richtung == 1 else (a, b)
    i, j = (v, u) if richtung == 1 else (u, v)
    return f"{kopf} Hier ist H(π,{ziel}) = {zeit(an.hpi[i])} kleiner als H(π,{von}) = {zeit(an.hpi[j])}: kürzer ist der Weg nach {ziel}."


def kurz_tuer(e: Ergaenzung, an: Netzanalyse) -> str:
    a, b = an.g.knoten[e.kante[0]], an.g.knoten[e.kante[1]]
    richtung = "sinkt" if e.mittel[1] < e.mittel[0] else "steigt"
    return (f"Ja. Die gewählte neue Kante {a}–{b} macht {ganz(e.anzahl_laenger)} von {ganz(e.paare)} Trefferzeiten länger "
            f"({prozent(e.anzahl_laenger / e.paare, 1)}), obwohl der Weg zwischen ihren Endpunkten kürzer wird; die mittlere Trefferzeit {richtung} dabei von "
            f"{zeit(e.mittel[0])} auf {zeit(e.mittel[1])}.")


def kurz_laeufe(p: dict, g: N.Netz) -> str:
    von, nach = g.knoten[p["u"]], g.knoten[p["v"]]
    # Ein Abbruch nach K ≥ 1 Schritten greift genau dann nie, wenn der erste Schritt immer schon trifft (der Start hängt nur am Ziel: T = 1, H = 1). Sonst kann die
    # Irrfahrt beliebig oft zwischen dem Start und einem anderen Nachbarn pendeln, also ist P(T > K) > 0 für jedes K.
    if p["h"] <= 1 + 1e-9:
        ende = f"Von {von} führt jeder erste Schritt nach {nach} (T = 1): Ein Abbruch nach mindestens einem Schritt trifft keinen Lauf, es fehlt nichts."
    else:
        ende = ("Bricht man Läufe nach K Schritten ab und zählt sie mit K, hilft auch eine größere Zahl von Läufen nicht gegen den systematischen Fehlbetrag.")
    return (f"Für {von} → {nach} (H = {zeit(p['h'])}, Variationskoeffizient {de(p['cv'], 2)}) sieht die Normalnäherung "
            f"{laeufe_text(p['laeufe_vorgabe'])} für ±10 % bei 95 % vor. {ende}")
