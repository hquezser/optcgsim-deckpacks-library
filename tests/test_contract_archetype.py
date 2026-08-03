"""Contrat du LOT E — sitegen/archetype.py. FIGÉ : le worker E implémente.

Interface attendue :
    archetype.CORE_THRESHOLD: float      # 0.8
    archetype.MIN_LISTS_FOR_DIFF: int    # 4
    archetype.core_cards(pairs) -> dict[str, int]
    archetype.deck_delta(deck, core) -> tuple[tuple[str, int, int], ...]

Les valeurs attendues ci-dessous sont calculées à la main sur la fixture
`2026-04-15-treasure-cup-noyau`, conçue pour ça : 5 listes « Blue Doflamingo » où

    OP01-001 : présent 5/5, quantités 4,4,4,4,4   -> cœur, modale 4
    OP01-002 : présent 4/5 (absent d'Echo)        -> cœur (4/5 = 0.8 pile), modale 4
    OP01-003 : présent 5/5, quantités 3,3,2,3,3   -> cœur, modale 3
    OP01-010 : 2/5   OP01-011 : 1/5   OP01-012 : 1/5   OP01-013 : 1/5  -> hors cœur

Le seuil se lit `présence / total >= CORE_THRESHOLD`, donc 4/5 entre et 3/4 (0.75) non.
"""

from __future__ import annotations

import pytest

from sitegen import archetype

ASLUG = "blue-doflamingo"


@pytest.fixture
def pairs(site):
    return site.leaders()[ASLUG]


@pytest.fixture
def core(pairs):
    return archetype.core_cards(pairs)


def _deck(pairs, joueur):
    return next(d for _, d in pairs if d.player == joueur)


def test_constantes_conformes_a_la_spec():
    assert archetype.CORE_THRESHOLD == 0.8
    assert archetype.MIN_LISTS_FOR_DIFF == 4


def test_la_fixture_a_bien_cinq_listes(pairs):
    assert len(pairs) == 5


def test_core_cards_retient_le_seuil_et_la_modale(core):
    assert core == {"OP01-001": 4, "OP01-002": 4, "OP01-003": 3}


def test_core_vide_en_dessous_du_seuil_de_listes(site):
    """purple-enel n'a que 2 listes : un « cœur commun » n'y a aucun sens."""
    assert len(site.leaders()["purple-enel"]) < archetype.MIN_LISTS_FOR_DIFF
    assert archetype.core_cards(site.leaders()["purple-enel"]) == {}
    assert archetype.core_cards(()) == {}


def test_delta_ajout_simple(pairs, core):
    """Alpha n'ajoute qu'une carte hors cœur ; sa quantité de cœur est la modale."""
    assert archetype.deck_delta(_deck(pairs, "Alpha"), core) == (("OP01-010", 2, 0),)


def test_delta_ajustement_de_quantite(pairs, core):
    """Charlie joue 2xOP01-003 là où la modale est 3 : c'est un écart, pas un ajout."""
    assert archetype.deck_delta(_deck(pairs, "Charlie"), core) == (
        ("OP01-010", 3, 0), ("OP01-003", 2, 3))


def test_delta_carte_du_coeur_absente(pairs, core):
    """Echo se passe entièrement d'OP01-002, qui est dans le cœur -> qty_deck = 0."""
    assert archetype.deck_delta(_deck(pairs, "Echo"), core) == (
        ("OP01-013", 4, 0), ("OP01-002", 0, 4))


def test_delta_trie_par_quantite_puis_id(pairs, core):
    for _, deck in pairs:
        d = archetype.deck_delta(deck, core)
        assert list(d) == sorted(d, key=lambda t: (-t[1], t[0])), \
            f"écart non trié pour {deck.player} : {d}"


def test_delta_vide_sans_coeur(pairs):
    """Sans cœur calculé (archétype trop petit), il n'y a pas d'écart à afficher."""
    assert archetype.deck_delta(_deck(pairs, "Alpha"), {}) == ()


def test_deterministe(pairs):
    a = archetype.core_cards(pairs)
    b = archetype.core_cards(pairs)
    assert a == b and list(a) == list(b)
