"""Fixtures partagées — FIGÉ.

Le corpus de test est volontairement minuscule et hermétique (aucune lecture du dépôt
sibling de données, qui bouge à chaque scraping) mais contient les cas limites réels :
nom de joueur à caractères parasites, nom de deck non parsable, tournoi hors fenêtre méta.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

FIXTURE_PACKS = Path(__file__).parent / "fixtures" / "packs"

# Le tournoi le plus récent de la fixture : l'horloge attendue du site.
REF_DATE = date(2026, 7, 4)


@pytest.fixture
def packs_dir() -> Path:
    return FIXTURE_PACKS


@pytest.fixture
def site(packs_dir: Path):
    from sitegen import parse

    return parse.load_site(packs_dir)
