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
from pathlib import Path

from .model import BuildWarning, Deck, Site, Tournament

__all__ = ["parse_deck_name", "parse_text", "load_site"]


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

    tournament = Tournament(
        slug=slug,
        name=name,
        date=tdate,
        description=description,
        author=author,
        decks=tuple(decks),
    )
    return tournament, warnings


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

    tournaments: list[Tournament] = []
    warnings: list[BuildWarning] = []
    for pack_dir in pack_dirs:
        tournament, w = _load_tournament(pack_dir)
        tournaments.append(tournament)
        warnings.extend(w)

    return Site(tournaments=tuple(tournaments), warnings=tuple(warnings))
