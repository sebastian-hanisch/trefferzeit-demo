"""Netz und neue Kante aus den Einstellungen (ohne Streamlit)."""

import trz_constants as C
import trz_netze as N


def netz_fuer(netz: str, a: int) -> N.Netz:
    if netz == C.NETZ_HAND:
        return N.handnetz(1)
    if netz == C.NETZ_HALLEN:
        return N.zwei_hallen(a)
    if netz == C.NETZ_SAAL:
        return N.saal_mit_stichgang(C.SAAL, C.GANG)
    raise ValueError(f"unbekanntes Netz {netz}")


def tuerpaar(netz: str, a: int):
    """(u, v) des Türschritts: durch die Tür (Brücke) in Richtung rechte Halle bzw. in den Gang."""
    if netz == C.NETZ_HAND:
        return 2, 3
    if netz == C.NETZ_HALLEN:
        return N.hallenknoten(a, 0, a // 2, a - 1), N.hallenknoten(a, 1, a // 2, 0)
    return C.SAAL - 1, C.SAAL


def tuerzeilen_neu(netz: str, a: int) -> list:
    """Zeilen, in denen eine zweite Tür möglich ist (nur Gitterhallen)."""
    return [z for z in range(a) if z != a // 2] if netz == C.NETZ_HALLEN else [0]


def hat_zweite_tuer(netz: str) -> bool:
    return netz in (C.NETZ_HAND, C.NETZ_HALLEN)


def wirksame_art(netz: str, kante: str) -> str:
    """Auf dem Kontrastnetz gibt es keine zweite Tür; dort wirkt immer die frei gewählte Kante."""
    return kante if hat_zweite_tuer(netz) else C.KANTE_FREI


def neue_kante(netz: str, a: int, kante: str, r: int, ka: int, kb: int):
    """((x, y), None) für eine gültige neue Kante, sonst (None, Grund)."""
    g = netz_fuer(netz, a)
    if wirksame_art(netz, kante) == C.KANTE_TUER:
        if netz == C.NETZ_HAND:
            return (0, 5), None
        r = r if r in tuerzeilen_neu(netz, a) else tuerzeilen_neu(netz, a)[0]
        return (N.hallenknoten(a, 0, r, a - 1), N.hallenknoten(a, 1, r, 0)), None
    if ka == kb:
        return None, "Eine neue Kante braucht zwei verschiedene Endpunkte."
    if N.hat_kante(g, ka, kb):
        return None, "Diese beiden Plätze sind schon verbunden. Bitte zwei nicht verbundene Plätze wählen."
    return (ka, kb), None
