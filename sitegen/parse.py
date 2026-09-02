"""LOT A — lecture du corpus scrapé vers le modèle figé.

Convertit les `deckpack.json` d'un dossier en `Site`/`Tournament`/`Deck` (voir
`sitegen/model.py`). Best-effort avec dégradation propre : un nom de deck non
conforme ou une quantité de leader inattendue ne fait jamais échouer le build.

Bibliothèque standard uniquement. Aucun accès réseau.
"""

from __future__ import annotations

import json
import re
from datetime import date
from dataclasses import replace
from pathlib import Path

from . import formats
from .model import BuildWarning, Deck, Site, Tournament

__all__ = ["parse_deck_name", "parse_text", "load_site", "parse_format",
           "parse_circuit"]


# Nom de deck : séparateur = tiret cadratin U+2014, entouré d'espaces.
# Tiret court -> non conforme (cf. SPEC § « Règles de parsing »).
_NAME_RE = re.compile(
    r"^(?P<archetype>.+?)\s+\u2014\s+(?P<player>.+?)\s+"
    r"\((?P<place>\d+)(?:st|nd|rd|th)?\)$"
)

# Une ligne de decklist : `1xOP15-058` -> (qty=1, id="OP15-058").
_LINE_RE = re.compile(r"^(\d+)\s*x\s*([A-Za-z0-9][A-Za-z0-9-]*)$")

# Préfixe de slug de tournoi : `2026-07-04-regional-bielefeld` -> date.
_SLUG_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

# Format depuis le nom de pack : `"OP14.5 21st March 2026 - ..."` -> `OP14.5`.
# Source primaire : on conserve la casse et le point tels qu'écrits. Insensible à
# la casse pour rester robuste face à un scraper qui écrirait `op16` en tête, mais
# on retourne le texte original (le préfixe « porte la casse »).
# Deux formes de déclaration, toutes deux ANCRÉES en tête du nom :
#   « OP16 26th July 2026 - Treasure Cup Sofia »  (Limitless, circuit papier)
#   « [OP17] ChinoizeCup #104 Tuesday »           (ChinoizeCupStats, circuit en ligne)
# La seconde était ignorée : 12 tournois du corpus déclaraient leur format et on le jetait
# pour le redéduire du pool. Les 12 déductions tombaient juste, donc rien ne l'a signalé —
# mais c'est la source en ligne qui voit les nouveaux formats EN PREMIER, et une déclaration
# vaut toujours mieux qu'une déduction.
#
# L'ancrage n'est pas négociable : sans lui, « ChinoizeCup #97 » suivi d'un joueur nommé
# « OP17fan » ou un identifiant de carte dans le nom suffiraient à étiqueter le tournoi.
_FORMAT_NAME_RE = re.compile(r"^\[?(OP\d+(?:\.\d+)?)\]?", re.IGNORECASE)

# Format depuis un tag de deck : `op16`, `op14.5`. Le tag `op` nu (cas réel
# ChinoizeCupStats) ne matche pas — il faut au moins un chiffre. Normalisé en
# majuscules au retour (c'est la source secondaire, elle ne porte pas la casse).
_FORMAT_TAG_RE = re.compile(r"^op\d+(?:\.\d+)?$", re.IGNORECASE)


def parse_format(pack_name: str, tags: tuple[str, ...]) -> str:
    """Le format (« la méta ») du tournoi : « OP16 », « OP14.5 »… "" si indéterminable.

    Source primaire : le préfixe du nom de pack (porte la casse et le point).
    Source secondaire : un tag de deck `op\\d+(\\.\\d+)?`, normalisé en majuscules.
    Ne devine jamais : un tournoi non classé vaut mieux qu'un tournoi mal classé.
    """
    m = _FORMAT_NAME_RE.match(pack_name)
    if m:
        return m.group(1)
    for tag in tags:
        mt = _FORMAT_TAG_RE.fullmatch(tag)
        if mt:
            return mt.group(0).upper()
    return ""


def parse_circuit(author: str, tags: tuple[str, ...]) -> str:
    """« online » (simulateur) ou « paper » (tournoi physique). Défaut prudent : « paper ».

    Deux signaux concordants dans le corpus réel, chacun suffisant seul :
      1. l'auteur du pack : `chinoizecup-scraper` -> online, `limitlesstcg-scraper` -> paper ;
      2. un tag `online` sur les decks (les packs papier portent un nom de région à la place).
    """
    author_l = (author or "").lower()
    if "chinoizecup" in author_l:
        return "online"
    if "limitlesstcg" in author_l:
        return "paper"
    for tag in tags:
        if tag == "online":
            return "online"
    return "paper"


def parse_deck_name(name: str) -> tuple[str, str, int | None]:
    """-> (archétype, joueur, placement). ("", "", None) si non conforme.

    Jamais d'exception, jamais de valeur inventée.
    """
    m = _NAME_RE.match(name)
    if not m:
        return "", "", None
    return m.group("archetype"), m.group("player"), int(m.group("place"))


def parse_text(text: str) -> tuple[str, tuple[tuple[str, int], ...]]:
    """-> (leader_id, ((card_id, qty), ...)). Le leader est la 1re ligne non vide,
    exclu des cartes. Les lignes vides et les espaces de bord sont tolérés.
    """
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]

    leader_id = ""
    cards: list[tuple[str, int]] = []
    for i, ln in enumerate(lines):
        m = _LINE_RE.match(ln)
        if not m:
            # Ligne non conforme : on l'ignore silencieusement ici. Le texte
            # verbatim reste disponible dans Deck.text pour réexport ; un
            # avertissement amont serait le travail du scraper, pas du parser.
            continue
        qty, card_id = int(m.group(1)), m.group(2)
        if i == 0:
            leader_id = card_id
        else:
            cards.append((card_id, qty))
    return leader_id, tuple(cards)


def _date_from_slug(slug: str) -> date | None:
    m = _SLUG_DATE_RE.match(slug)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        # Préfixe bien formé mais date impossible (ex. 2026-13-40) : on ne
        # devine rien, on retourne None plutôt que de faire échouer le build.
        return None


def _load_tournament(pack_dir: Path) -> tuple[Tournament, list[BuildWarning]]:
    manifest_path = pack_dir / "deckpack.json"
    # Laisse OSError (fichier absent/illisible) et ValueError (JSON invalide)
    # remonter à l'appelant : la spec exige un échec sur corpus illisible.
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    slug = pack_dir.name
    tdate = _date_from_slug(slug)
    name = manifest.get("name", "")
    author = manifest.get("author", "")
    description = manifest.get("description", "")
    raw_decks = manifest.get("decks", []) or []

    decks: list[Deck] = []
    warnings: list[BuildWarning] = []
    for raw in raw_decks:
        raw_name = raw.get("name", "")
        archetype, player, placement = parse_deck_name(raw_name)
        text = raw.get("text", "")
        leader_id, cards = parse_text(text)
        tags = tuple(raw.get("tags", []) or [])

        # Le leader est censé être en tête avec qty=1 (scraper amont). Si la
        # première ligne exploitable a une quantité différente, on avertit sans
        # échouer — le deck reste affiché.
        first_line = next(
            (ln.strip() for ln in text.split("\n") if ln.strip()), None
        )
        if first_line is not None:
            fm = _LINE_RE.match(first_line)
            if fm and int(fm.group(1)) != 1:
                warnings.append(BuildWarning(
                    scope=slug,
                    message=f"quantité de leader != 1 pour « {raw_name} » : {fm.group(1)}x{fm.group(2)}",
                ))

        decks.append(Deck(
            raw_name=raw_name,
            archetype=archetype,
            player=player,
            placement=placement,
            leader_id=leader_id,
            cards=cards,
            text=text,
            tags=tags,
        ))

    # Format du tournoi, trois sources dans l'ordre (cf. SPEC § « Format ») :
    #   1. préfixe du nom de pack (porte la casse et le point) ;
    #   2. tag de deck `op\d+(\.\d+)?` normalisé en majuscules ;
    #   3. à défaut, déduction depuis le pool de cartes (borne inférieure : un
    #      tournoi ne peut pas être antérieur au set le plus récent qu'il joue).
    # L'étiquette explicite gagne toujours sur la déduction — on ne l'écrase pas.
    fmt = parse_format(name, ())
    if not fmt:
        for raw in raw_decks:
            deck_tags = tuple(raw.get("tags", []) or [])
            fmt = parse_format("", deck_tags)
            if fmt:
                break
    if not fmt:
        # Troisième source : le pool de cartes du tournoi entier. Les tournois
        # ChinoizeCupStats ne portent ni préfixe ni tag de format (leur seul tag
        # est « op » nu) : c'est ce qui les classe, via ST31/32/33 -> OP16.5.
        pool: set[str] = set()
        for raw in raw_decks:
            pool.update(formats.sets_in_text(raw.get("text", "") or ""))
        nouveaux = formats.beyond_horizon(tuple(sorted(pool)))
        if nouveaux:
            # Le tournoi joue un set POSTÉRIEUR à l'horizon du calendrier et ne déclare
            # rien. On ne peut pas savoir si ce set est simplement légal dans le format
            # courant ou s'il en ouvre un nouveau — c'est une question de calendrier de
            # sorties, pas de decklist. Déduire quand même donnerait le format du booster
            # le plus récent, et fondrait en silence un format neuf dans le précédent :
            # exactement ce qui fabrique un « cœur commun » qu'aucun deck réel ne possède.
            #
            # On laisse donc le tournoi NON CLASSÉ. Il reste visible sur l'accueil et sur sa
            # propre page ; il sort seulement des vues par format, le temps qu'une ligne
            # soit ajoutée à `formats.LEGAL_SETS_AT_HORIZON`.
            warnings.append(BuildWarning(
                scope=slug,
                message=(f"non classé : joue {', '.join(nouveaux)}, postérieur à l'horizon "
                         f"{formats.CALENDAR_HORIZON} du calendrier, et ne déclare aucun "
                         f"format"),
            ))
        elif pool:
            fmt = formats.infer_format(tuple(sorted(pool)))

    # Circuit du tournoi : « online » (simulateur) ou « paper » (tournoi physique).
    # Deux signaux concordants dans le corpus réel : l'auteur du pack et un tag
    # `online` porté par les decks. Défaut prudent : « paper ». L'union des tags
    # des decks suffit à capter le tag `online` quel que soit le deck qui le porte.
    all_tags = tuple(sorted({t for raw in raw_decks for t in (raw.get("tags", []) or [])}))
    circuit = parse_circuit(author, all_tags)

    tournament = Tournament(
        slug=slug,
        name=name,
        date=tdate,
        description=description,
        author=author,
        decks=tuple(decks),
        format=fmt,
        circuit=circuit,
    )
    return tournament, warnings


# Fichier de demandes de retrait, à la racine du dépôt. Volontairement pas dans le dépôt de
# données : c'est ce module qui décide de ce qui est publié, et le scraping quotidien
# réécrirait les packs. Un retrait annulé par la collecte suivante n'est pas un retrait.
REMOVALS_FILE = Path(__file__).resolve().parent.parent / "removals.txt"


def load_removals(path: Path | None = None) -> frozenset[str]:
    """Noms de joueurs à écarter, normalisés (casefold + strip). Fichier absent -> vide."""
    f = Path(path) if path is not None else REMOVALS_FILE
    if not f.is_file():
        return frozenset()
    noms = set()
    for ligne in f.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#"):
            noms.add(ligne.casefold())
    return frozenset(noms)


def load_site(packs_dir: Path) -> Site:
    """Lit `packs_dir/*/deckpack.json` -> Site.

    Lève `OSError` (pack absent/illisible) ou `ValueError` (JSON invalide) si un
    pack est illisible : la spec veut un code de sortie 1 dans ce cas.
    """
    packs_dir = Path(packs_dir)
    # Tri explicite sur le nom du dossier : la sortie doit être déterministe,
    # indépendante de l'ordre de `iterdir` (qui suit l'inode sur macOS/ext4).
    pack_dirs = sorted(
        (p for p in packs_dir.iterdir() if p.is_dir()),
        key=lambda p: p.name,
    )

    retires = load_removals()

    tournaments: list[Tournament] = []
    warnings: list[BuildWarning] = []
    n_retires = 0
    for pack_dir in pack_dirs:
        tournament, w = _load_tournament(pack_dir)
        if retires:
            gardes = tuple(d for d in tournament.decks
                           if d.player.strip().casefold() not in retires)
            n_retires += len(tournament.decks) - len(gardes)
            if len(gardes) != len(tournament.decks):
                tournament = replace(tournament, decks=gardes)
        tournaments.append(tournament)
        warnings.extend(w)

    # Tracé dans le rapport de build : un retrait silencieux ne se distingue pas d'un
    # fichier mal lu, et il faut pouvoir constater qu'une demande a bien été honorée.
    if retires:
        warnings.append(BuildWarning(
            scope="corpus",
            message=(f"retraits RGPD honorés : {len(retires)} joueur(s) listé(s) dans "
                     f"removals.txt, {n_retires} deck(s) écarté(s) de la publication"),
        ))

    # Détection d'un changement de format en cours, pour tout le corpus.
    #
    # Portée : les tournois QUE ÇA EMPÊCHE DE CLASSER. Un set neuf joué dans un tournoi qui
    # déclare son format ne gêne personne — la déclaration a tranché. Un avertissement qui se
    # déclenche à chaque build n'avertit plus de rien : la version précédente listait 26 sets
    # anciens en permanence pendant que les 114 tournois étaient correctement classés.
    nouveaux_sets: set[str] = set()
    bloques: list[str] = []
    for t in tournaments:
        if t.format:
            continue
        pool: set[str] = set()
        for d in t.decks:
            pool.update(formats.sets_in_text(d.text))
        n = formats.beyond_horizon(tuple(sorted(pool)))
        if n:
            nouveaux_sets.update(n)
            bloques.append(t.slug)
    if nouveaux_sets:
        listés = ", ".join(sorted(nouveaux_sets))
        warnings.append(BuildWarning(
            scope="corpus",
            message=(
                f"NOUVEAU(X) SET(S) : {listés} — postérieur(s) à l'horizon "
                f"{formats.CALENDAR_HORIZON}. {len(bloques)} tournoi(s) restent non classés. "
                f"Décider si ces sets ouvrent un format à décimale (les ajouter à "
                f"FORMAT_OF_SET) ou sont légaux dans le format courant (les ajouter "
                f"seulement à LEGAL_SETS_AT_HORIZON), puis avancer CALENDAR_HORIZON."
            ),
        ))

    return Site(tournaments=tuple(tournaments), warnings=tuple(warnings))
