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
    "beyond_horizon",
    "CALENDAR_HORIZON",
    "LEGAL_SETS_AT_HORIZON",
    "sets_in_text",
]

# ─────────────────────────────────────────────────────────────────────────────────────
# Le calendrier, et pourquoi il est en MONDE CLOS
#
# Un booster `OPnn` ouvre le format `OPnn` : c'est structurel, jamais à déclarer, et c'est
# ce qui rend un nouveau format automatique. OP18 sortira, les tournois qui le jouent se
# classeront en OP18 tout seuls, les rôles suivront. Rien à faire.
#
# Ce qui n'est PAS automatique, c'est la frontière d'un format à décimale : ce sont des
# starter decks qui l'ouvrent (ST31-ST36 -> OP16.5), et rien dans une decklist ne dit si un
# nouveau ST est « légal dans le format courant » ou « ouvre le suivant ».
#
# Quatre signaux ont été essayés sur le corpus réel (134 tournois) et TOUS réfutés :
#
#   1. Dériver le calendrier des tournois qui déclarent leur format. 19 sur 134 déclarent,
#      et tous en OP14.5-OP16 : la dérivation date ST01 et EB01 de « OP14.5 », c'est-à-dire
#      du plus vieux tournoi déclarant du corpus, pas de leur sortie réelle.
#   2. La première apparition d'un set. ST14 apparaît pour la première fois le 2026-07-28 —
#      c'est un starter ancien que personne n'avait sorti en top 16 avant.
#   3. La cohorte (« plusieurs sets le même jour = une sortie »). ST35 arrive seul le
#      2026-07-21, ST36 seul le 2026-07-20 ; ce sont pourtant de vrais sets OP16.5.
#   4. Le taux d'adoption. ST35 (vrai OP16.5) : 0,3 % des decks à 30 jours, 1 tournoi.
#      ST14 (bruit) : 1,8 %, 3 tournois. EB03 (bruit) : 51,8 %. Le bruit domine le signal.
#
# La raison de fond : le corpus est un échantillon de decks JOUÉS. L'absence d'un set n'a
# jamais voulu dire « pas encore légal », seulement « personne n'a fini en top 16 avec ».
#
# D'où le monde clos. Plutôt qu'une liste ouverte de sets datés — où un set absent est
# muet —, on déclare l'inverse : à l'HORIZON ci-dessous, voici la liste COMPLÈTE des sets
# non-boosters légaux. Un set hors de cette liste est nécessairement postérieur à
# l'horizon, avec certitude et sans heuristique. C'est ce qui permet de le DÉTECTER.
# ─────────────────────────────────────────────────────────────────────────────────────

# Le format le plus récent dont le pool non-booster est entièrement déclaré ici.
# À BOUGER en même temps que LEGAL_SETS_AT_HORIZON, jamais séparément.
CALENDAR_HORIZON = "OP16.5"

# Sets non-boosters dont l'ENTRÉE en légalité compte, c'est-à-dire ceux sortis assez
# récemment pour distinguer deux formats du corpus. Tout ce qui est plus ancien est dans
# LEGAL_SETS_AT_HORIZON sans date : leur date n'a plus aucun effet sur une déduction.
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

# Liste COMPLÈTE des sets non-boosters légaux à CALENDAR_HORIZON. Relevée sur le corpus au
# 2026-09-03 (33 sets joués sur 134 tournois).
#
# Limite assumée : un set légal que personne n'a jamais joué en top 16 n'y figure pas. Le
# jour où quelqu'un le joue, il sera signalé comme nouveau à tort. Le coût est une ligne à
# ajouter et un tournoi non classé en attendant — pas une donnée fausse publiée. C'est le
# sens de l'arbitrage : mieux vaut ne pas classer que mal classer.
LEGAL_SETS_AT_HORIZON: frozenset[str] = frozenset({
    "EB01", "EB02", "EB03", "EB04", "PRB02",
    "ST01", "ST02", "ST03", "ST04", "ST05", "ST07", "ST10", "ST12", "ST13", "ST14",
    "ST15", "ST16", "ST17", "ST18", "ST21", "ST22", "ST23", "ST24", "ST26", "ST27",
    "ST29", "ST30", "ST31", "ST32", "ST33", "ST34", "ST35", "ST36",
})

# Accepte les DEUX orthographes du même format : le libellé « OP14.5 » et son slug d'URL
# « op14-5 ». Ne pas accepter le slug était un piège : `format_key("op14-5")` renvoyait
# (-1, -1) en silence, et tout appelant qui trie sur des slugs reléguait les formats à
# décimale en fin de liste. C'est arrivé dans le rendu — OP14.5 s'affichait après OP13.
_FORMAT_RE = re.compile(r"^OP(\d+)(?:[.-](\d+))?$", re.IGNORECASE)
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


def beyond_horizon(set_codes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Sets non-boosters absents du monde clos — donc postérieurs à CALENDAR_HORIZON.

    C'est la détection d'un changement de format en cours, et elle est CERTAINE : elle ne
    repose sur aucune heuristique de date, de cohorte ou d'adoption (toutes réfutées, voir
    l'en-tête). Un booster n'est jamais concerné : `OPnn` se date tout seul.

    Ce que ça ne dit PAS, et ne peut pas dire : si le set ouvre un format à décimale ou s'il
    est simplement légal dans le format courant. Cette question-là se tranche avec le
    calendrier de sorties, pas avec des decklists — d'où un signalement, pas une décision.
    """
    return tuple(sorted(
        c for c in {x.strip().upper() for x in set_codes}
        if not _BOOSTER_RE.match(c) and c not in LEGAL_SETS_AT_HORIZON
    ))


# Conservé sous son ancien nom : `unknown_sets` disait « set non daté », ce qui incluait les
# 26 sets anciens jamais listés dans FORMAT_OF_SET. Le nom trompait — l'immense majorité de
# ces « inconnus » étaient parfaitement bénins, et l'avertissement se lisait donc comme du
# bruit permanent. `beyond_horizon` répond à la vraie question : ce set est-il NOUVEAU ?
unknown_sets = beyond_horizon
