"""LOT C — production des manifestes `deckpack.json` dérivés du modèle.

Ces manifestes sont **le produit réel du site** : c'est eux que `studio decks import-pack
<url>` consomme. Les pages HTML (lot B) n'en sont que la vitrine.

Bibliothèque standard uniquement. Aucun accès réseau. Sortie déterministe (deux builds sur
la même entrée produisent des octets identiques).
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from .meta import META_MAX_DECKS, META_WINDOW_DAYS, meta_pairs
from .model import Deck, Site, Tournament

__all__ = [
    "META_WINDOW_DAYS",
    "META_MAX_DECKS",
    "meta_pairs",
    "build_pack",
    "write_packs",
]


DEFAULT_AUTHOR = "optcgsim-deckpacks-library"


# --- pack méta ------------------------------------------------------------------------

# `meta_pairs` vit dans `sitegen/meta.py` et est RÉEXPORTÉ ici.
#
# Il en existait deux copies, une par lot, avec un commentaire « duplication volontaire ».
# Elles avaient divergé : celle-ci filtrait sur le format courant, celle du rendu non. Sur
# une fenêtre couvrant deux formats, la page affichait donc des decks que son propre pack ne
# contenait pas. Une règle, un seul endroit.

# --- construction du manifeste --------------------------------------------------------

def build_pack(name: str, pairs: tuple[tuple[Tournament, Deck], ...],
               author: str = DEFAULT_AUTHOR) -> dict:
    """Manifeste deckpack v1. Chaque entrée utilise `text` inline, jamais `file`/`source_url`.

    Le `text` est réexporté verbatim : c'est le format natif attendu par le simulateur,
    toute renormalisation casserait l'import.
    """
    decks = []
    for _t, d in pairs:
        entry = {"name": d.raw_name, "text": d.text}
        if d.tags:
            entry["tags"] = list(d.tags)
        decks.append(entry)
    return {
        "schema_version": 1,
        "name": name,
        "author": author,
        "decks": decks,
    }


# --- écriture -------------------------------------------------------------------------

def _dump(manifest: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys=True : ordre de clés stable indépendant de l'ordre d'insertion.
    # ensure_ascii=False : les noms comportent des tirets cadratin (U+2014) et des
    # accents — les réencoder en \uXXXX rendrait la sortie illisible sans raison.
    blob = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    path.write_bytes(blob.encode("utf-8"))


def write_packs(site: Site, out: Path) -> list[Path]:
    """Écrit tous les packs sous `out`. Renvoie la liste exacte des chemins écrits.

    L'ensemble des chemins est dicté par la SPEC § « Carte des URLs » :
      - tournaments/<tslug>/deckpack.json         tous les decks du tournoi
      - tournaments/<tslug>/decks/<dslug>.json    un pack d'un seul deck (import unitaire)
      - leaders/<aslug>/deckpack.json          toutes les listes de cet archétype
      - meta/deckpack.json                     l'instantané du méta courant
    """
    out = Path(out)
    written: list[Path] = []

    # 1. Par tournoi : pack complet + un pack par deck (y compris non parsables —
    #    ils restent affichables sur leur tournoi, juste exclus des vues agrégées).
    for t in site.sorted_tournaments:
        tdir = out / "tournaments" / t.slug
        pairs = tuple((t, d) for d in t.decks)
        manifest = build_pack(
            name=t.name or t.slug,
            pairs=pairs,
            author=t.author or DEFAULT_AUTHOR,
        )
        if t.description:
            manifest["description"] = t.description
        path = tdir / "deckpack.json"
        _dump(manifest, path)
        written.append(path)

        for d in t.decks:
            dpath = tdir / "decks" / f"{d.slug}.json"
            _dump(build_pack(name=d.raw_name, pairs=((t, d),)), dpath)
            written.append(dpath)

    # 2. Par archétype : toutes les listes, tous tournois. `Site.leaders()` fait le
    #    regroupement et le tri — ne pas le réimplémenter.
    for aslug, pairs in site.leaders().items():
        path = out / "leaders" / aslug / "deckpack.json"
        _dump(
            build_pack(name=site.archetype_label(aslug), pairs=pairs),
            path,
        )
        written.append(path)

    # 2.bis Par archétype restreint à un format : un fichier <fslug>.json par format
    #     où l'archétype a au moins une liste. `Site.leaders(format_slug)` fait le
    #     filtrage — ne pas le réimplémenter. Les formats indéterminés (slug vide)
    #     ne produisent aucun fichier.
    for fslug in site.formats():
        for aslug, pairs in site.leaders(fslug).items():
            path = out / "leaders" / aslug / f"{fslug}.json"
            _dump(
                build_pack(
                    name=f"{site.archetype_label(aslug)} — {site.format_label(fslug)}",
                    pairs=pairs,
                ),
                path,
            )
            written.append(path)

    # 3. Par format : tous les decks du format. Les formats indéterminés (slug vide)
    #    sont exclus par `Site.formats()` elle-même.
    for fslug, tournaments in site.formats().items():
        pairs: list[tuple[Tournament, Deck]] = []
        for t in tournaments:
            for d in t.decks:
                pairs.append((t, d))
        path = out / "formats" / fslug / "deckpack.json"
        _dump(
            build_pack(name=site.format_label(fslug), pairs=tuple(pairs)),
            path,
        )
        written.append(path)

    # 3. Méta courant.
    ref = site.reference_date
    if ref is not None:
        path = out / "meta" / "deckpack.json"
        _dump(
            build_pack(name=f"Méta {ref:%Y-%m}", pairs=meta_pairs(site)),
            path,
        )
        written.append(path)

    return written
