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
        """Identité d'archétype = **l'ID de la carte de leader**, pas le nom parsé.

        Un nom ne suffit pas : ChinoizeCupStats nomme ses decks par nom de personnage, et
        « Monkey D. Luffy » recouvre au moins dix cartes de leader distinctes — regrouper
        dessus produisait 271 listes sans rapport sur une même page. À l'inverse, Limitless
        écrit « Green/Blue Luffy » là où ChinoizeCup écrit « Monkey D. Luffy » pour la MÊME
        carte : l'ID réconcilie les deux sources au lieu de les éclater.
        """
        return slugify(self.leader_id)

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
    format: str = ""             # « OP16 », « OP14.5 »… "" si indéterminable
    circuit: str = "paper"       # « paper » (tournoi physique) ou « online » (simulateur)

    @property
    def parsed_decks(self) -> tuple[Deck, ...]:
        return tuple(d for d in self.decks if d.parsed)

    @property
    def is_online(self) -> bool:
        return self.circuit == "online"

    @property
    def format_slug(self) -> str:
        """« OP14.5 » -> « op14-5 ». "" si le format est inconnu."""
        return slugify(self.format) if self.format else ""


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

    def formats(self) -> dict[str, tuple[Tournament, ...]]:
        """format_slug -> tournois de ce format, du plus récent au plus ancien.

        Le format (« la méta ») est l'axe de navigation que servent tous les sites de
        référence, et il est surtout la condition de justesse des vues agrégées : un cœur
        commun calculé sur deux formats mélangés décrit un deck qui n'a jamais existé.
        Les tournois de format indéterminé sont EXCLUS — mieux vaut ne pas les classer que
        les ranger au hasard.
        """
        out: dict[str, list[Tournament]] = {}
        for t in self.sorted_tournaments:
            if t.format_slug:
                out.setdefault(t.format_slug, []).append(t)
        return {k: tuple(v) for k, v in sorted(out.items())}

    @property
    def current_format(self) -> str:
        """format_slug du dernier format joué sur le **circuit papier**. "" si indéterminable.

        Volontairement PAS « le format du tournoi le plus récent » : le simulateur reçoit les
        sets en avance, donc le tournoi le plus récent est presque toujours en ligne et en
        avance. Cette définition-là faisait basculer « courant » sur un format que presque
        personne ne joue encore, et vidait « à venir » — elle effaçait le décalage qu'elle
        devait mettre en valeur.

        Le circuit papier est le repère stable : c'est le format que la majorité des joueurs
        pratique. Repli sur tous les circuits si le corpus n'a aucun tournoi papier.
        """
        for source in (
            (t for t in self.sorted_tournaments if not t.is_online),
            self.sorted_tournaments,
        ):
            for t in source:
                if t.format_slug:
                    return t.format_slug
        return ""

    def format_label(self, format_slug: str) -> str:
        """Libellé d'origine d'un format (« op14-5 » -> « OP14.5 »)."""
        for t in self.tournaments:
            if t.format_slug == format_slug:
                return t.format
        return format_slug

    @property
    def upcoming_formats(self) -> tuple[str, ...]:
        """format_slugs POSTÉRIEURS au format courant, du plus proche au plus lointain.

        Le simulateur reçoit les sets avant le circuit papier : un format peut donc être déjà
        joué en ligne alors que les tournois papier en sont encore au précédent. Il peut y en
        avoir **plusieurs** à la fois (OP16.5 puis OP17), d'où une liste ordonnée.

        « Courant » et « à venir » sont des RÔLES, pas des identités : les formats gardent
        leurs codes réels et leurs URLs. Rien ici n'invente d'étiquette.
        """
        from .formats import format_key

        courant = format_key(self.format_label(self.current_format))
        return tuple(sorted(
            (f for f in self.formats()
             if format_key(self.format_label(f)) > courant),
            key=lambda f: format_key(self.format_label(f)),
        ))

    @property
    def past_formats(self) -> tuple[str, ...]:
        """format_slugs antérieurs au format courant, du plus récent au plus ancien."""
        from .formats import format_key

        courant = format_key(self.format_label(self.current_format))
        return tuple(sorted(
            (f for f in self.formats()
             if format_key(self.format_label(f)) < courant),
            key=lambda f: format_key(self.format_label(f)), reverse=True,
        ))

    def leaders(self, format_slug: str | None = None
                ) -> dict[str, tuple[tuple[Tournament, Deck], ...]]:
        """archetype_slug -> ((tournoi, deck), ...) trié par date décroissante, placement.

        Renvoie les decks appariés à leur tournoi : une page /leaders/ doit citer la
        provenance de chaque liste, c'est toute sa valeur de preuve.

        `format_slug` restreint à un seul format. C'est le paramètre à utiliser dès qu'on
        agrège (cœur commun, écarts) : mélanger deux formats produit un cœur qui ne
        correspond à aucun deck réel. Sans lui, on obtient tout le corpus — utile pour un
        inventaire, pas pour une moyenne.
        """
        out: dict[str, list[tuple[Tournament, Deck]]] = {}
        for t in self.tournaments:
            if format_slug is not None and t.format_slug != format_slug:
                continue
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
        """Libellé lisible d'un archétype identifié par l'ID de son leader.

        Le slug étant désormais un ID de carte (`op16-022`), il faut choisir un libellé parmi
        les noms que les sources donnent au même deck. On **préfère le circuit papier** :
        Limitless écrit « Green/Blue Luffy », qui décrit le deck, là où ChinoizeCup écrit
        « Monkey D. Luffy », qui ne décrit que le personnage. À circuit égal, le nom le plus
        fréquent ; puis l'ordre alphabétique, pour que la sortie reste déterministe.
        """
        compte: dict[tuple[int, str], int] = {}
        for t in self.tournaments:
            for d in t.parsed_decks:
                if d.archetype_slug == archetype_slug and d.archetype:
                    cle = (0 if not t.is_online else 1, d.archetype)
                    compte[cle] = compte.get(cle, 0) + 1
        if not compte:
            return archetype_slug.upper()
        (_, label), _ = min(compte.items(), key=lambda kv: (kv[0][0], -kv[1], kv[0][1]))
        return label
