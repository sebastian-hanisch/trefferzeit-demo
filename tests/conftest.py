"""Gemeinsame Fixtures: das Handnetz „zwei Hallen“, an dem jede Einheit von Hand geprüft wird."""

import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import trz_netze as N  # noqa: E402


@pytest.fixture
def hand():
    """Dreiecke {0,1,2} und {3,4,5}, eine Tür 2–3: Grade 2, 2, 3, 3, 2, 2 und 7 Kanten."""
    return N.handnetz(1)


def bruch(z, n=1):
    """Von Hand gerechneter Sollwert als Gleitkommazahl."""
    return float(Fraction(z, n))
