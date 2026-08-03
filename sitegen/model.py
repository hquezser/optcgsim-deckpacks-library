"""Modèle de données du site — CONTRAT FIGÉ.

Ce module est la frontière entre les lots de développement : le parsing le produit, le
rendu et la génération de packs le consomment. Il ne contient aucune logique métier
au-delà des dérivations pures, précisément pour qu'aucun lot n'ait besoin de le modifier.

Voir SPEC-site-v1.md § « Modèle de données ». Ne pas modifier sans mettre à jour la spec.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

__all__ = ["slugify", "Deck", "Tournament", "Site", "BuildWarning"]


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Minuscules, toute suite de non-alphanumériques -> '-', tirets aux bords retirés.

    Unique implémentation autorisée : les slugs sont des URLs publiques, deux variantes
    divergentes casseraient des liens en silence.
    """
    return _NON_ALNUM.sub("-", value.lower()).strip("-")


@dataclass(frozen=True)
class BuildWarning:
    """Anomalie non bloquante, remontée dans le rapport de build.

    Le corpus amont est scrapé : il dérive. Un avertissement visible vaut mieux qu'une
    exception (qui perdrait tout le build) ou qu'un silence (qui masquerait la dérive).
    """

    scope: str   # ex. "2026-07-04-regional-bielefeld"
    message: str


@dataclass(frozen=True)
class Deck:
    """Une decklist, telle qu'affichable et réexportable.

    `raw_name` est toujours renseigné et verbatim ; `archetype`/`player`/`placement` sont
    le produit d'un parsing best-effort et peuvent être vides (cf. spec).
    """

    raw_name: str
    archetype: str                        # "" si non parsé
    player: str                           # "" si non parsé
    placement: int | None                 # None si non parsé
    leader_id: str                        # "OP15-058"
    cards: tuple[tuple[str, int], ...]    # (("OP15-061", 4), ...) leader exclu
    text: str                             # decklist native, verbatim (leader compris)
    tags: tuple[str, ...] = ()

    @property
    def parsed(self) -> bool:
        """Un deck non parsé reste affiché sur son tournoi, mais sort des vues agrégées."""
        return bool(self.archetype) and self.placement is not None

    @property
    def slug(self) -> str:
        if self.placement is None:
            return f"xx-{slugify(self.raw_name)}"
        return f"{self.placement:02d}-{slugify(self.archetype)}-{slugify(self.player)}"

    @property
    def archetype_slug(self) -> str:
        return slugify(self.archetype)

    @property
    def total_cards(self) -> int:
        """Total hors leader (le Don!! n'est pas listé — implicite à l'import studio)."""
        return sum(qty for _, qty in self.cards)


@dataclass(frozen=True)
class Tournament:
    """Un pack d'entrée = un tournoi."""

    slug: str                    # nom du dossier source
    name: str
    date: date | None            # dérivée du slug (préfixe AAAA-MM-JJ) si présent
    description: str
    author: str
    decks: tuple[Deck, ...]

    @property
    def parsed_decks(self) -> tuple[Deck, ...]:
        return tuple(d for d in self.decks if d.parsed)


@dataclass(frozen=True)
class Site:
    """Le corpus entier, plus ses vues dérivées.

    Les dérivations vivent ici (et non dans un lot) parce qu'elles définissent les URLs
    publiques : leur ordre de tri EST une garantie de sortie déterministe.
    """

    tournaments: tuple[Tournament, ...]
    warnings: tuple[BuildWarning, ...] = field(default=())

    @property
    def sorted_tournaments(self) -> tuple[Tournament, ...]:
        """Plus récent d'abord. Les tournois sans date passent en fin, par slug."""
        dated = sorted((t for t in self.tournaments if t.date),
                       key=lambda t: (t.date, t.slug), reverse=True)
        undated = sorted((t for t in self.tournaments if not t.date), key=lambda t: t.slug)
        return tuple(dated) + tuple(undated)

    @property
    def reference_date(self) -> date | None:
        """Date du tournoi le plus récent — l'horloge du site.

        Sciemment PAS `date.today()` : la sortie doit être reproductible et testable.
        """
        dates = [t.date for t in self.tournaments if t.date]
        return max(dates) if dates else None

    def leaders(self) -> dict[str, tuple[tuple[Tournament, Deck], ...]]:
        """archetype_slug -> ((tournoi, deck), ...) trié par date décroissante, placement.

        Renvoie les decks appariés à leur tournoi : une page /leaders/ doit citer la
        provenance de chaque liste, c'est toute sa valeur de preuve.
        """
        out: dict[str, list[tuple[Tournament, Deck]]] = {}
        for t in self.tournaments:
            for d in t.parsed_decks:
                out.setdefault(d.archetype_slug, []).append((t, d))
        return {
            aslug: tuple(sorted(
                pairs,
                key=lambda p: (-(p[0].date.toordinal() if p[0].date else 0),
                               p[1].placement or 999, p[1].slug),
            ))
            for aslug, pairs in sorted(out.items())
        }

    def archetype_label(self, archetype_slug: str) -> str:
        """Libellé lisible d'un archétype (premier trouvé — le slug est dérivé du libellé)."""
        for t in self.tournaments:
            for d in t.parsed_decks:
                if d.archetype_slug == archetype_slug:
                    return d.archetype
        return archetype_slug
