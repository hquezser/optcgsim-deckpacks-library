"""LOT B — rendu HTML statique du site depuis le modèle figé.

Produit exactement l'ensemble des pages décrit par SPEC-site-v1.md § « Carte des URLs »
(côté HTML + `style.css`) : `index.html`, une page par tournoi, une page par archétype
parsé, `meta/index.html`, et la feuille unique.

La commande d'import OPTCGSim est l'élément visuellement dominant de chaque page — c'est
la seule raison du site (cf. SPEC § « Positionnement »). Tout le reste est secondaire.

Invariants respectés :
- Jinja2 `autoescape=True` (un nom de joueur peut contenir `<` ou `&`).
- Zéro `<script>`, zéro `@import`, zéro police/image distante, zéro CDN.
- Aucune URL ne sort du `base_url` fourni.
- Aucun nom de carte — uniquement des IDs (`OP15-058`).
- Sortie déterministe : aucun horodatage, aucun parcours de `set` non trié.
"""

from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

from .model import Deck, Site, Tournament

__all__ = ["write_pages", "meta_pairs"]

# Fenêtre et plafond du pack méta — miroir de la spec (cf. SPEC § « Définition du pack
# méta »). Duplication volontaire : ce module ne dépend pas du lot C, qui peut ne pas
# exister encore à l'exécution des tests de ce lot.
META_WINDOW_DAYS = 60
META_MAX_DECKS = 40
META_AUTHOR = "optcgsim-deckpacks-library"


def meta_pairs(site: Site) -> tuple[tuple[Tournament, Deck], ...]:
    """Sélection déterministe des decks du pack méta (cf. SPEC).

    Date de référence = date du tournoi le plus récent. Fenêtre de 60 jours avant,
    `placement <= 8`, `archetype != ""`. Tri par date décroissante puis placement
    croissant. Plafond à 40 decks.
    """
    ref = site.reference_date
    if ref is None:
        return ()
    cutoff = ref - timedelta(days=META_WINDOW_DAYS)
    pairs: list[tuple[Tournament, Deck]] = []
    for t in site.tournaments:
        if t.date is None or t.date < cutoff or t.date > ref:
            continue
        for d in t.parsed_decks:
            if d.placement is not None and d.placement <= 8:
                pairs.append((t, d))
    pairs.sort(key=lambda p: (
        # date décroissante
        -(p[0].date.toordinal() if p[0].date else 0),
        p[1].placement if p[1].placement is not None else 999,
        p[0].slug,
        p[1].slug,
    ))
    return tuple(pairs[:META_MAX_DECKS])


def _import_command(base_url: str, pack_url: str) -> str:
    """La commande copiable. `pack_url` est un chemin absolu depuis la racine du site."""
    return f"studio decks import-pack {base_url}{pack_url}"


# URL dans un texte libre — on capture le schéma + tout ce qui n'est pas espace.
# On retire ensuite la ponctuation terminale susceptible d'appartenir au texte
# environnant plutôt qu'à l'URL (point, virgule, parenthèse fermante...).
_URL_RE = re.compile(r"(https?://[^\s<>'\"]+)", re.IGNORECASE)
_URL_TRAIL = ".,;:!?)]}\"'"


def linkify(text: str) -> Markup:
    """Échappe `text` et rend les URL cliquables, sans envoyer de référent ni de poids SEO.

    Seul le sous-ensemble URL devient une balise `<a>` ; le reste reste échappé. La balise
    porte `rel="noreferrer nofollow"` et `target="_blank"` (cf. SPEC § « Contenu des pages »
    et AGENTS.md : créditer la source est délibéré, mais sans exposer le visiteur).
    """
    if not text:
        return Markup("")
    out: list[str] = []
    pos = 0
    for m in _URL_RE.finditer(text):
        if m.start() > pos:
            out.append(escape(text[pos:m.start()]))
        url = m.group(0)
        while url and url[-1] in _URL_TRAIL:
            url = url[:-1]
        out.append(
            f'<a href="{escape(url)}" rel="noreferrer nofollow" '
            f'target="_blank">{escape(url)}</a>'
        )
        # On avance jusqu'à la fin de l'URL rognée : la ponctuation excédentaire
        # appartient au texte environnant et réapparaîtra (échappée) au segment suivant.
        pos = m.start() + len(url)
    if pos < len(text):
        out.append(escape(text[pos:]))
    return Markup("".join(out))


def urls_only(text: str) -> Markup:
    """N'extrait que les URL de `text`, rendues en une ligne d'attribution compacte.

    La `description` d'un pack est un champ de métadonnées de scraper : il répète le titre
    et expose des paramètres internes (`region=Europe`, `time=3months`). Seules les URL
    qu'il contient sont citées (cf. SPEC § « Contenu des pages » — l'attribution reste
    obligatoire, l'étaler ne l'est pas). URL dédupliquées en conservant l'ordre d'apparition.
    """
    if not text:
        return Markup("")
    seen: set[str] = set()
    unique: list[str] = []
    for m in _URL_RE.finditer(text):
        url = m.group(0)
        while url and url[-1] in _URL_TRAIL:
            url = url[:-1]
        if url and url not in seen:
            seen.add(url)
            unique.append(url)
    links = [
        f'<a href="{escape(u)}" rel="noreferrer nofollow" '
        f'target="_blank">{escape(u)}</a>'
        for u in unique
    ]
    return Markup(" · ".join(links))


def ordinal(n: int | None) -> str:
    """Rendu contigu du placement : `1st`, `2nd`, `11th` — sans `<sup>`.

    La mise en exposant produisait un espace visible (« 1 st ») lu comme une coquille
    (cf. SPEC § « Placement »).
    """
    if n is None:
        return "—"
    suffix = "th"
    if n % 100 not in (11, 12, 13):
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def sort_cards(cards) -> list:
    """Tri d'affichage par quantité décroissante puis identifiant croissant.

    Cosmétique uniquement — `Deck.text` et les `deckpack.json` conservent l'ordre source
    (cf. SPEC § « Affichage des cartes » et test_le_tri_daffichage_ne_touche_pas_les_packs).
    """
    return sorted(cards, key=lambda c: (-c[1], c[0]))


def _env(templates_dir: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        # Pas de trim_blocks/lstrip_blocks : on veut contrôler soi-même les espaces
        # pour une sortie déterministe et lisible.
        keep_trailing_newline=True,
    )
    env.globals["import_command"] = _import_command
    env.filters["linkify"] = linkify
    env.filters["urls_only"] = urls_only
    env.filters["ordinal"] = ordinal
    env.filters["sort_cards"] = sort_cards
    return env


def _write(out: Path, rel: str, content: str) -> Path:
    target = out / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def write_pages(site: Site, out: Path, base_url: str) -> list[Path]:
    """Écrit les pages HTML + `style.css` sous `out`. Renvoie la liste exacte des
    chemins écrits, dans un ordre déterministe.
    """
    out = Path(out)
    base_url = base_url.rstrip("/")
    templates_dir = Path(__file__).parent / "templates"
    env = _env(templates_dir)

    written: list[Path] = []
    ctx_common = {"base_url": base_url}

    # --- style.css ----------------------------------------------------------
    style_tpl = env.get_template("style.css")
    written.append(_write(out, "style.css", style_tpl.render(**ctx_common)))

    # --- index.html ---------------------------------------------------------
    leaders = site.leaders()  # dict trié par aslug
    archetype_rows = [
        (aslug, site.archetype_label(aslug), len(pairs))
        for aslug, pairs in leaders.items()
    ]
    # Tri par nombre de listes décroissant, puis libellé croissant (déterministe).
    archetype_rows.sort(key=lambda r: (-r[2], r[1]))
    recent = site.sorted_tournaments[:20]
    index_tpl = env.get_template("index.html")
    written.append(_write(out, "index.html", index_tpl.render(
        site=site,
        recent_tournaments=recent,
        archetype_rows=archetype_rows,
        meta_count=len(meta_pairs(site)),
        **ctx_common,
    )))

    # --- une page par tournoi ----------------------------------------------
    tournoi_tpl = env.get_template("tournoi.html")
    for t in site.sorted_tournaments:
        pack_url = f"/tournois/{t.slug}/deckpack.json"
        # Decks triés par placement croissant ; les non parsés (placement None)
        # en fin de liste, par ordre de raw_name pour déterminisme.
        decks_sorted = sorted(
            t.decks,
            key=lambda d: (
                d.placement if d.placement is not None else 10**9,
                d.raw_name,
            ),
        )
        page = tournoi_tpl.render(
            site=site,
            tournament=t,
            decks=decks_sorted,
            pack_url=pack_url,
            **ctx_common,
        )
        written.append(_write(
            out, f"tournois/{t.slug}/index.html", page
        ))

    # --- une page par archétype (parsé) ------------------------------------
    leader_tpl = env.get_template("leader.html")
    for aslug, pairs in leaders.items():
        pack_url = f"/leaders/{aslug}/deckpack.json"
        label = site.archetype_label(aslug)
        page = leader_tpl.render(
            site=site,
            archetype_slug=aslug,
            archetype_label=label,
            pairs=pairs,
            pack_url=pack_url,
            **ctx_common,
        )
        written.append(_write(out, f"leaders/{aslug}/index.html", page))

    # --- meta ---------------------------------------------------------------
    meta_tpl = env.get_template("meta.html")
    meta = meta_pairs(site)
    # Groupage par archétype, tri par nombre de listes décroissant puis libellé.
    by_arch: dict[str, list[tuple[Tournament, Deck]]] = {}
    for t, d in meta:
        by_arch.setdefault(d.archetype_slug, []).append((t, d))
    arch_groups = sorted(
        by_arch.items(),
        key=lambda kv: (-len(kv[1]), site.archetype_label(kv[0])),
    )
    meta_groups = [
        (aslug, site.archetype_label(aslug), pairs)
        for aslug, pairs in arch_groups
    ]
    ref = site.reference_date
    meta_name = f"Méta {ref:%Y-%m}" if ref else "Méta"
    page = meta_tpl.render(
        site=site,
        meta_name=meta_name,
        meta_pairs=meta,
        meta_groups=meta_groups,
        pack_url="/meta/deckpack.json",
        **ctx_common,
    )
    written.append(_write(out, "meta/index.html", page))

    # Ordre de retour déterministe : stable sur l'ordre d'insertion ci-dessus,
    # qui ne dépend que du modèle (lui-même trié).
    return written
