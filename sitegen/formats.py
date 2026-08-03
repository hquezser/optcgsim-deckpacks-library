"""Calendrier des formats et déduction depuis le pool de cartes — CONTRAT FIGÉ.

Le format (« la méta ») suit une ligne unique et connue d'avance, dictée par le calendrier
de sorties : … OP15, OP16, OP16.5, OP17 … Un booster ouvre son propre format ; les starter
decks et sets annexes entrent en légalité à une date qui, elle, doit être déclarée ici.

Il n'y a **pas** d'axe de formats parallèle par plateforme. Le simulateur est simplement
plus avancé sur la même ligne que le circuit papier : ChinoizeCup jouait ST31/32/33 alors
qu'aucun tournoi Limitless du corpus ne dépassait ST30. Ce décalage est une information de
produit, pas une anomalie à cloisonner.

Deux usages, dans les deux sens :
  - **déduire** le format d'un tournoi qui n'en déclare pas (`infer_format`) ;
  - **vérifier** celui d'un tournoi qui en déclare un (`sets_after_format`).
"""

from __future__ import annotations

import re

__all__ = [
    "FORMAT_OF_SET",
    "format_key",
    "format_of_set",
    "infer_format",
    "sets_after_format",
    "unknown_sets",
    "sets_in_text",
]

# Sets NON-boosters, avec le format où ils entrent en légalité. Seule la frontière récente
# est nécessaire : tout ce qui est plus ancien que le plus vieux format du corpus n'a aucun
# effet sur une déduction. À compléter à chaque sortie.
#
# ST30 : sorti avec OP16 — confirmé par le corpus (présent dans les 12 tournois OP16, absent
#        de tous les OP15 et OP14.5).
# ST31-ST36 : les starter decks de OP16.5, c'est-à-dire ce qui distingue OP16.5 de OP16.
FORMAT_OF_SET: dict[str, str] = {
    "ST30": "OP16",
    "ST31": "OP16.5",
    "ST32": "OP16.5",
    "ST33": "OP16.5",
    "ST34": "OP16.5",
    "ST35": "OP16.5",
    "ST36": "OP16.5",
}

_FORMAT_RE = re.compile(r"^OP(\d+)(?:\.(\d+))?$", re.IGNORECASE)
_BOOSTER_RE = re.compile(r"^OP(\d+)$", re.IGNORECASE)
_LINE_RE = re.compile(r"^\d+x([A-Z]+\d+)-\d+$")


def format_key(fmt: str) -> tuple[int, int]:
    """Ordre de tri d'un format : « OP16 » -> (16, 0), « OP16.5 » -> (16, 5).

    Un tri lexicographique placerait OP16.5 avant OP16 et OP9 après OP16 : il faut une clé
    numérique. `(-1, -1)` pour un format non reconnu, qui se range donc avant tout le reste.
    """
    m = _FORMAT_RE.match(fmt.strip()) if fmt else None
    if not m:
        return (-1, -1)
    return (int(m.group(1)), int(m.group(2) or 0))


def format_of_set(set_code: str) -> str | None:
    """Format où ce set entre en légalité. None si inconnu (ne rien deviner).

    Un booster `OPnn` ouvre le format `OPnn` — c'est structurel, pas une donnée à déclarer.
    Tout le reste vient de FORMAT_OF_SET.
    """
    code = set_code.strip().upper()
    m = _BOOSTER_RE.match(code)
    if m:
        return f"OP{int(m.group(1))}"
    return FORMAT_OF_SET.get(code)


def sets_in_text(text: str) -> tuple[str, ...]:
    """Codes de set présents dans une decklist native, dédupliqués et triés."""
    out = set()
    for line in text.split("\n"):
        m = _LINE_RE.match(line.strip())
        if m:
            out.add(re.sub(r"-\d+$", "", m.group(1)).upper())
    return tuple(sorted(out))


def infer_format(set_codes: tuple[str, ...] | list[str]) -> str:
    """Format le plus tardif parmi les sets fournis. "" si aucun n'est reconnu.

    C'est une **borne inférieure** : un tournoi ne peut pas être antérieur au set le plus
    récent qu'il joue. Il pourrait être postérieur (personne n'a joué le dernier set), donc
    on ne s'en sert que faute de déclaration explicite.
    """
    connus = [f for f in (format_of_set(c) for c in set_codes) if f]
    return max(connus, key=format_key) if connus else ""


def sets_after_format(fmt: str, set_codes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Sets dont la légalité est POSTÉRIEURE à `fmt` — donc incohérents avec cette étiquette.

    C'est le garde-fou : un tournoi annoncé OP16 qui joue du ST31 est soit mal étiqueté, soit
    en avance sur son circuit. Dans les deux cas il ne doit pas être agrégé avec les autres
    OP16, sous peine de fabriquer un cœur commun qu'aucun deck réel ne possède.
    """
    if not fmt:
        return ()
    borne = format_key(fmt)
    return tuple(sorted(
        c for c in set(set_codes)
        if (f := format_of_set(c)) and format_key(f) > borne
    ))


def unknown_sets(set_codes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Sets dont on ne sait pas dater la légalité — à déclarer dans FORMAT_OF_SET.

    Remonté en avertissement de build plutôt qu'ignoré en silence : un set inconnu qui
    apparaît est le signal qu'une sortie n'a pas été enregistrée ici.
    """
    return tuple(sorted(c for c in set(set_codes) if format_of_set(c) is None))
