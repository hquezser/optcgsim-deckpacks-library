"""LOT E — vue par écart sur les pages /leaders/.

Sur un archétype assez fourni (>= MIN_LISTS_FOR_DIFF listes), on calcule le « cœur commun »
des decklists et on n'affiche plus que ce qui distingue chaque liste de ce cœur. L'information
utile au joueur est l'écart, pas la répétition d'une liste à 90 % identique à la précédente.

Stdlib uniquement — pas de dépendance nouvelle, pas d'accès réseau, sortie déterministe.
"""

from __future__ import annotations

from collections import Counter

from .model import Deck, Tournament

__all__ = [
    "CORE_THRESHOLD",
    "MIN_LISTS_FOR_DIFF",
    "core_cards",
    "deck_delta",
]

CORE_THRESHOLD = 0.8      # présence dans >= 80 % des listes
MIN_LISTS_FOR_DIFF = 4    # en dessous, un « cœur commun » n'a aucun sens


def core_cards(
    pairs: tuple[tuple[Tournament, Deck], ...]
) -> dict[str, int]:
    """card_id -> quantité modale, pour les IDs présents dans >= CORE_THRESHOLD des listes.

    `pairs` est la valeur de `Site.leaders()[aslug]`. Renvoie {} si len(pairs) <
    MIN_LISTS_FOR_DIFF. En cas d'égalité pour la quantité modale, on retient la plus grande
    — déterminisme obligatoire.
    """
    if len(pairs) < MIN_LISTS_FOR_DIFF:
        return {}
    total = len(pairs)
    quantities: dict[str, list[int]] = {}
    for _, deck in pairs:
        for card_id, qty in deck.cards:
            quantities.setdefault(card_id, []).append(qty)
    core: dict[str, int] = {}
    for card_id, qts in quantities.items():
        if len(qts) / total < CORE_THRESHOLD:
            continue
        counter = Counter(qts)
        max_count = max(counter.values())
        # Égalité -> la plus grande quantité (déterministe).
        core[card_id] = max(q for q, c in counter.items() if c == max_count)
    return dict(sorted(core.items()))


def deck_delta(
    deck: Deck,
    core: dict[str, int],
) -> tuple[tuple[str, int, int], ...]:
    """Ce qui distingue `deck` du cœur : ((card_id, qty_deck, qty_core), ...).

    Inclut les cartes absentes du cœur (qty_core = 0) ET celles dont la quantité diffère de
    la modale. Une carte du cœur absente du deck apparaît avec qty_deck = 0. Trié par
    quantité de deck décroissante puis par id, comme le reste de l'affichage. Renvoie () si
    `core` est vide (archétype trop petit pour un cœur).
    """
    if not core:
        return ()
    deck_map = dict(deck.cards)
    delta: list[tuple[str, int, int]] = []
    for card_id, qty in deck_map.items():
        core_qty = core.get(card_id, 0)
        if qty != core_qty:
            delta.append((card_id, qty, core_qty))
    for card_id, core_qty in core.items():
        if card_id not in deck_map:
            delta.append((card_id, 0, core_qty))
    delta.sort(key=lambda t: (-t[1], t[0]))
    return tuple(delta)
