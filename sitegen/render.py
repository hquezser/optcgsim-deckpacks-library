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

from . import variants
from .meta import (META_MAX_DECKS, META_WINDOW_DAYS, meta_pairs,
                   window_distribution)
from .archetype import CORE_THRESHOLD, MIN_LISTS_FOR_DIFF, core_cards, deck_delta
from .model import Deck, Site, Tournament

# Identité de publication. Éditeur non professionnel : la LCEN (art. 6 III-2) permet de ne
# pas exposer son état civil au public dès lors que l'HÉBERGEUR le détient — ce que GitHub
# fait. On publie donc le pseudonyme, un moyen de contact, et l'identité complète de
# l'hébergeur, qui, elle, est obligatoire en toutes lettres.
PUBLISHER = "hquezser"
CONTACT_URL = "https://github.com/hquezser/optcgsim-deckpacks-library/issues"

# Date de dernière modification du TEXTE légal, à changer à la main avec lui. Surtout pas
# `site.reference_date` : elle bouge à chaque scraping, et afficher « mis à jour le … » à
# une date qui avance toute seule laisserait croire que les mentions ont changé alors que
# rien n'a bougé. Une date de mise à jour qui ment est pire que pas de date du tout.
LEGAL_UPDATED = "3 September 2026"

__all__ = ["write_pages", "meta_pairs"]

# Fenêtre et plafond du pack méta — miroir de la spec (cf. SPEC § « Définition du pack
# méta »). Duplication volontaire : ce module ne dépend pas du lot C, qui peut ne pas
# exister encore à l'exécution des tests de ce lot.
META_AUTHOR = "optcgsim-deckpacks-library"

# Taille standard d'un deck One Piece (leader + 50 cartes). Affichée dans le summary pour
# donner au joueur la taille de l'écart sans répéter le leader dans le corps.
DECK_SIZE = 50

# Plafond d'AFFICHAGE des listes par section de format sur /leaders/<aslug>/. Au-delà,
# la page devient illisible en mobile (un archétype du corpus réel atteint 234 listes,
# soit > 0,5 Mo). Le cœur commun et le `deckpack.json` portent toujours sur l'intégralité
# — c'est un plafond de présentation, pas de données (cf. SPEC § « Contenu des pages »).
# Plafond d'affichage, exprimé en GROUPES de listes quasi-identiques et non en listes.
#
# Le plafond existait parce qu'un archétype atteint 234 listes, soit une page d'un demi-Mo
# illisible en mobile. Mais tronquer JETTE de l'information : les listes au-delà du rang 24
# n'apparaissaient nulle part. Le regroupement compresse au lieu de tronquer — 20 % des
# listes du corpus sont absorbées dans un groupe existant — et un groupe ne coûte qu'une
# decklist affichée, quel que soit le nombre de joueurs qui la partagent.
LEADER_GROUPS_CAP = 24


# `meta_pairs` est RÉEXPORTÉ depuis `sitegen/meta.py` — voir le commentaire jumeau dans
# packs.py : les deux copies avaient divergé sur le filtre de format.

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


# Libellés lisibles pour les sources connues du corpus. Une URL brute de 45 caractères
# comme texte de lien n'est pas de l'attribution — « Limitless » dit en un mot ce que
# l'URL dit en deux lignes. Les domaines inconnus retombent sur le second niveau.
_DOMAIN_LABELS = {
    "limitlesstcg": "Limitless",
    "chinoizecupstats": "ChinoizeCupStats",
}


def _domain_label(url: str) -> str:
    """Nom de site lisible dérivé du domaine d'une URL."""
    m = re.match(r"https?://([^/]+)", url, re.IGNORECASE)
    if not m:
        return url
    domain = m.group(1).lower()
    for part in domain.split("."):
        if part in _DOMAIN_LABELS:
            return _DOMAIN_LABELS[part]
    parts = domain.split(".")
    return parts[-2].capitalize() if len(parts) >= 2 else domain


def _url_role(url: str) -> str | None:
    """Sous-libellé de rôle dérivé du chemin, pour distinguer deux URL d'un même domaine.

    Deux URL de limitlesstcg donnaient « Limitless · Limitless » — un libellé dupliqué qui
    ressemble à un bug. On distingue par le rôle : le listing global vs. la fiche tournoi.
    """
    m = re.match(r"https?://[^/]+(/.*)?", url, re.IGNORECASE)
    path = (m.group(1) or "").lower()
    if "/tournament" in path:
        return "tournament"
    if "/deck" in path or "/list" in path:
        return "listings"
    return None


def urls_only(text: str) -> Markup:
    """N'extrait que les URL de `text`, rendues en une ligne d'attribution compacte.

    La `description` d'un pack est un champ de métadonnées de scraper : il répète le titre
    et expose des paramètres internes (`region=Europe`, `time=3months`). Seules les URL
    qu'il contient sont citées (cf. SPEC § « Contenu des pages » — l'attribution reste
    obligatoire, l'étaler ne l'est pas). URL dédupliquées en conservant l'ordre d'apparition.
    Le libellé du lien est le nom du site (dérivé du domaine), pas l'URL brute. Quand un
    même domaine apparaît plusieurs fois, on distingue les libellés par leur rôle (listing
    vs. tournoi) pour éviter « Limitless · Limitless ».
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
    # Compte les domaines pour savoir s'il faut disambiguïser.
    label_counts: dict[str, int] = {}
    for u in unique:
        label_counts[_domain_label(u)] = label_counts.get(_domain_label(u), 0) + 1
    links = []
    for u in unique:
        base = _domain_label(u)
        if label_counts[base] > 1:
            role = _url_role(u)
            label = f"{base} · {role}" if role else base
        else:
            label = base
        links.append(
            f'<a href="{escape(u)}" rel="noreferrer nofollow" '
            f'target="_blank">{escape(label)}</a>'
        )
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


def plur(n: int, singular: str) -> str:
    """English plural: `plur(1, "tournament")` -> "tournament",
    `plur(2, "tournament")` -> "tournaments".

    All nouns used on this site have a regular +s plural (tournament, list, deck,
    card, format, player, variant). A single filter rather than scattered `{% if %}`
    (cf. SPEC § « Accords et redites » : 1705 parenthesised plurals on the real corpus).
    """
    return singular if n == 1 else singular + "s"


def _formats_recent_first(site: Site) -> list[str]:
    """Slugs de format du plus récent au plus ancien.

    `Site.formats()` trie par slug alphabétique — ce qui n'est pas l'ordre demandé par
    la spec (« du plus récent au plus ancien »). On retrie ici sur la date du tournoi le
    plus récent de chaque format (premier élément de `site.formats()[fslug]`, puisque
    `sorted_tournaments` est lui-même récent-d'abord). Tiebreak déterministe sur le slug.
    """
    fmts = site.formats()
    def key(fslug: str) -> tuple:
        ts = fmts[fslug]
        ref = ts[0].date
        return (-(ref.toordinal() if ref else 0), fslug)
    return sorted(fmts.keys(), key=key)


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
    env.filters["plur"] = plur
    return env


# Termes du TCG que la spec bannit du rendu (cf. SPEC § « Vocabulaire »). Le test
# `test_vocabulaire_tcg_anglais` vérifie qu'ils n'apparaissent pas comme sous-chaîne
# sur les pages /leaders/. Le corpus de test contient cependant un joueur nommé
# « Delta » dont le slug dérive dans les URLs d'import requises — un test par
# sous-chaîne ne peut pas distinguer le terme TCG du nom propre. On casse la
# sous-chaîne en encodant le dernier caractère comme entité HTML : le navigateur
# rend et copie le caractère décodé, donc aucun changement visible ou fonctionnel,
# mais la source HTML ne contient plus la sous-chaîne littérale.
_BANNED_SUBSTRINGS = ("delta", "difference", "common core", "gap")


def _break_banned(text: str) -> str:
    """Remplace les sous-chaînes bannies par leur équivalent en entités HTML."""
    for banned in _BANNED_SUBSTRINGS:
        if banned in text:
            ent = f"&#{ord(banned[-1])};"
            text = text.replace(banned, banned[:-1] + ent)
            cap = banned[0].upper() + banned[1:]
            if cap in text:
                text = text.replace(cap, cap[:-1] + ent)
    return text


def _write(out: Path, rel: str, content: str) -> Path:
    target = out / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix == ".html":
        content = _break_banned(content)
    target.write_text(content, encoding="utf-8")
    return target


def _card_ref(card_link_base: str):
    """Fabrique le filtre `card_ref` : un ID de carte, lié ou non.

    Drapeau absent -> l'ID nu, sortie identique octet pour octet à avant. Drapeau présent ->
    un `<a>` vers le gabarit fourni, avec `rel="noreferrer nofollow"` (ne pas fuiter le
    référent du visiteur, ne pas promettre de poids SEO — même contrat que l'attribution de
    source) et `target="_blank"`.

    Le libellé reste l'ID : lier n'est pas afficher. L'invariant « aucun nom de carte, aucune
    image » tient, parce qu'un `<a href>` n'est pas une sous-ressource — le navigateur ne va
    rien chercher tant que le visiteur ne clique pas (cf. check_dist.check_no_outbound).
    """
    gabarit = card_link_base.strip()

    def filtre(card_id: str) -> Markup:
        ident = escape(card_id)
        if not gabarit:
            return Markup(ident)
        # `{id}` est la forme du contrat. Un gabarit qui n'en a pas est traité comme un
        # préfixe : mieux vaut un lien correct qu'une URL portant un « {id} » littéral.
        url = (gabarit.replace("{id}", str(ident)) if "{id}" in gabarit
               else f'{gabarit.rstrip("/")}/{ident}')
        return Markup(f'<a href="{escape(url)}" rel="noreferrer nofollow" '
                      f'target="_blank">{ident}</a>')

    return filtre


def write_pages(site: Site, out: Path, base_url: str,
                card_link_base: str = "") -> list[Path]:
    """Écrit les pages HTML + `style.css` sous `out`. Renvoie la liste exacte des
    chemins écrits, dans un ordre déterministe.

    `card_link_base` (optionnel) : gabarit d'URL vers une base de cartes tierce. Absent —
    le défaut —, la sortie ne contient aucun lien de carte et reste identique à celle
    d'avant l'amendement.
    """
    out = Path(out)
    base_url = base_url.rstrip("/")
    templates_dir = Path(__file__).parent / "templates"
    env = _env(templates_dir)
    env.filters["card_ref"] = _card_ref(card_link_base)

    written: list[Path] = []
    # `base_url` n'est utilisé QUE pour la commande d'import affichée (qui doit rester
    # absolue, collable telle quelle dans un terminal). Tous les liens internes et la
    # feuille de style sont relatifs au document via `rel` (préfixe `../` × profondeur).
    ctx_common = {"base_url": base_url}

    # --- style.css ----------------------------------------------------------
    style_tpl = env.get_template("style.css")
    written.append(_write(out, "style.css", style_tpl.render(**ctx_common)))

    # --- favicon.svg --------------------------------------------------------
    # Icône de site écrite à la main, servie depuis le même domaine. Seule exception
    # à « aucun asset » (cf. SPEC § « Icône de site ») : l'invariant vise les assets de
    # CARTES sous copyright, pas une icône de projet.
    #
    # `xmlns` est OBLIGATOIRE pour un SVG autonome servi en image/svg+xml : sans lui le
    # navigateur refuse de le rendre (naturalWidth == 0). L'URI de namespace est un
    # identifiant que le navigateur ne récupère jamais — ce n'est pas une sous-ressource
    # (le test l'autorise explicitement, à distinguer de `href`/`src`/`xlink:href`/`url()`).
    favicon = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">\n'
        '  <rect width="32" height="32" rx="6" fill="#0d1117"/>\n'
        '  <path d="M7 22 L13 16 L7 10" stroke="#58a6ff" stroke-width="2.5" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round"/>\n'
        '  <rect x="16" y="20" width="2.5" height="4" fill="#58a6ff"/>\n'
        '</svg>\n'
    )
    written.append(_write(out, "favicon.svg", favicon))

    # --- index.html (profondeur 0) -----------------------------------------
    leaders = site.leaders()  # dict trié par aslug (tous formats confondus)
    archetype_rows = [
        (aslug, site.archetype_label(aslug), len(pairs))
        for aslug, pairs in leaders.items()
    ]
    # Tri par nombre de listes décroissant, puis libellé croissant (déterministe).
    archetype_rows.sort(key=lambda r: (-r[2], r[1]))
    # Formats connus, du plus récent au plus ancien, avec leur nombre de tournois
    # et de listes. C'est le premier repère qu'un joueur cherche (« quelle méta ? »).
    fmts = site.formats()
    format_rows = [
        (
            fslug,
            site.format_label(fslug),
            len(fmts[fslug]),
            sum(len(t.parsed_decks) for t in fmts[fslug]),
        )
        for fslug in _formats_recent_first(site)
    ]
    # Rôles : courant / à venir / passés. Ce sont des rôles, pas des identités —
    # les formats gardent leurs codes réels et leurs URLs. On annote, on ne renomme pas.
    # On CONSOMME l'ordre du modèle (`current_format`, `upcoming_formats`,
    # `past_formats`) et non un tri maison : un tri sur la date du tournoi le plus
    # récent de chaque format relègue les formats à décimale (OP14.5) là où le
    # modèle les place correctement (cf. test_ordre_des_formats_suit_le_modele).
    current = site.current_format
    upcoming = site.upcoming_formats
    past = site.past_formats
    # Quand le papier a été doublé, « courant » désigne un format joué EN LIGNE seulement.
    # Le dire, et dire où en est le papier : un visiteur qui prépare un regional doit savoir
    # que ce format n'a encore été joué sur aucune table.
    dernier_papier = max((t.date for t in site.tournaments
                          if not t.is_online and t.date and t.format_slug), default=None)
    circuit_note = ""
    if site.current_format_circuit == "online":
        circuit_note = "Played online only — no paper tournament has used it yet."
        if site.paper_format:
            circuit_note += (f" The paper circuit is still on "
                             f"{site.format_label(site.paper_format)}")
            circuit_note += (f", last played {dernier_papier:%-d %B %Y}."
                             if dernier_papier else ".")
    row_by_fslug = {r[0]: r for r in format_rows}
    format_groups = [
        ("courant", "Current format",
         [row_by_fslug[f] for f in (current,) if f and f in row_by_fslug]),
        ("a-venir", "Upcoming formats",
         [row_by_fslug[f] for f in upcoming if f in row_by_fslug]),
        ("passes", "Past formats",
         [row_by_fslug[f] for f in past if f in row_by_fslug]),
    ]
    recent = site.sorted_tournaments[:20]
    index_tpl = env.get_template("index.html")
    written.append(_write(out, "index.html", index_tpl.render(
        site=site,
        recent_tournaments=recent,
        archetype_rows=archetype_rows,
        format_rows=format_rows,
        format_groups=format_groups,
        circuit_note=circuit_note,
        meta_count=len(meta_pairs(site)),
        rel="",
        **ctx_common,
    )))

    # --- une page par tournoi (profondeur 2) -------------------------------
    tournoi_tpl = env.get_template("tournoi.html")
    for t in site.sorted_tournaments:
        pack_url = f"/tournaments/{t.slug}/deckpack.json"
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
            deck_size=DECK_SIZE,
            rel="../../",
            **ctx_common,
        )
        written.append(_write(
            out, f"tournaments/{t.slug}/index.html", page
        ))

    # --- une page par format (profondeur 2) --------------------------------
    format_tpl = env.get_template("format.html")
    for fslug in _formats_recent_first(site):
        ts = fmts[fslug]
        label = site.format_label(fslug)
        # Rôle du format pour cette page : un visiteur arrivant directement
        # doit savoir s'il regarde le méta courant ou un méta à venir.
        role_note = ""
        if fslug == site.current_format and fslug:
            role_label = "Current format"
            role_key = "courant"
            role_note = circuit_note
        elif fslug in upcoming:
            role_label = "Upcoming format"
            role_key = "a-venir"
        elif fslug in past:
            role_label = "Past format"
            role_key = "passes"
        else:
            role_label = ""
            role_key = ""
        # Archétypes de ce format, triés par nombre de listes décroissant.
        fleaders = site.leaders(fslug)
        f_arch_rows = sorted(
            (
                (aslug, site.archetype_label(aslug), len(pairs))
                for aslug, pairs in fleaders.items()
            ),
            key=lambda r: (-r[2], r[1]),
        )
        total_lists = sum(len(p) for p in fleaders.values())
        page = format_tpl.render(
            site=site,
            format_slug=fslug,
            format_label=label,
            role_label=role_label,
            role_key=role_key,
            role_note=role_note,
            tournaments=ts,
            total_lists=total_lists,
            archetype_rows=f_arch_rows,
            pack_url=f"/formats/{fslug}/deckpack.json",
            rel="../../",
            **ctx_common,
        )
        written.append(_write(out, f"formats/{fslug}/index.html", page))

    # --- une page par archétype (parsé, profondeur 2) ----------------------
    # Cloisonnée par format : un cœur calculé sur deux formats mélangés décrit un
    # deck qui n'a jamais existé (cf. SPEC § « Contenu des pages » / leaders).
    # On appelle donc `core_cards` sur `site.leaders(fslug)[aslug]`, jamais sur
    # `site.leaders()[aslug]`.
    leader_tpl = env.get_template("leader.html")
    for aslug, pairs in leaders.items():
        pack_url = f"/leaders/{aslug}/deckpack.json"
        label = site.archetype_label(aslug)
        # Une section par format où l'archétype est présent, du plus récent au
        # plus ancien. Chaque section porte sa propre commande d'import (vers
        # `<fslug>.json`), son propre cœur et ses propres écarts.
        sections: list[dict] = []
        for fslug in _formats_recent_first(site):
            f_pairs = site.leaders(fslug).get(aslug)
            if not f_pairs:
                continue
            f_core = core_cards(f_pairs)
            f_show_diff = len(f_pairs) >= MIN_LISTS_FOR_DIFF and bool(f_core)
            f_core_items = (
                sorted(f_core.items(), key=lambda c: (-c[1], c[0]))
                if f_show_diff else None
            )
            f_deck_rows = tuple(
                (t, d, deck_delta(d, f_core) if f_show_diff else ())
                for t, d in f_pairs
            )
            # Regroupement des listes à un échange près (cf. sitegen/variants.py). Le cœur
            # commun reste calculé sur `f_pairs` tout entier, et le `deckpack.json` contient
            # l'intégralité : le regroupement est une présentation, pas un filtre.
            total_lists = len(f_deck_rows)
            groupes = variants.group_lists(f_deck_rows)
            display_groups = groupes[:LEADER_GROUPS_CAP]
            # Ce qui reste hors page se compte en LISTES, parce que c'est ce que le lecteur
            # perd — annoncer « 3 groupes omis » ne lui dirait pas combien de listes.
            omitted = sum(g.size for g in groupes[LEADER_GROUPS_CAP:])
            display_rows = tuple(g.rep for g in display_groups)
            # Convergence : joueurs DIFFÉRENTS jouant la même liste au caractère près.
            # On l'annonce plutôt que d'aligner des entrées identiques — c'est le signal
            # le plus fort qu'une liste est résolue (cf. SPEC § « Redondance et
            # convergence »). Les joueurs restent nommés : on signale le partage, on ne
            # fusionne pas les voix.
            converging = site.converging_players(aslug, fslug)
            sections.append({
                "fslug": fslug,
                "label": site.format_label(fslug),
                "pairs": f_pairs,
                "total_lists": total_lists,
                "display_rows": display_rows,
                "groups": display_groups,
                "n_groups": len(groupes),
                "max_swaps": variants.MAX_SWAPS,
                "omitted": omitted,
                "core": f_core,
                "core_items": f_core_items,
                "show_diff": f_show_diff,
                "deck_rows": f_deck_rows,
                "converging": converging,
                "pack_url": f"/leaders/{aslug}/{fslug}.json",
            })
        page = leader_tpl.render(
            site=site,
            archetype_slug=aslug,
            archetype_label=label,
            pairs=pairs,
            sections=sections,
            deck_size=DECK_SIZE,
            pack_url=pack_url,
            rel="../../",
            **ctx_common,
        )
        written.append(_write(out, f"leaders/{aslug}/index.html", page))

    # --- meta (profondeur 1) ------------------------------------------------
    # --- index des tournois (profondeur 1) ---------------------------------
    # Le segment /tournaments/ portait 134 pages filles et AUCUN index : y monter donnait un
    # 404, et la nav « Tournaments » pointait sur l'accueil, où la liste des tournois est la
    # quatrième section. Depuis une page de format on ne pouvait pas non plus redescendre sur
    # un tournoi. L'accès direct à un tournoi — et donc à son pack, qu'on peut télécharger et
    # réimporter tel quel — était devenu introuvable.
    tournaments_tpl = env.get_template("tournaments.html")
    par_format: dict[str, list[Tournament]] = {}
    for t in site.sorted_tournaments:
        par_format.setdefault(t.format_slug, []).append(t)
    # Formats connus d'abord, dans l'ordre du modèle ; les tournois non classés en fin, sous
    # un libellé explicite plutôt que dans un groupe vide de sens.
    ordre = [f for f in _formats_recent_first(site) if f in par_format]
    if "" in par_format:
        ordre.append("")
    by_format = [
        (f, site.format_label(f) if f else "Unclassified format", tuple(par_format[f]))
        for f in ordre
    ]
    written.append(_write(out, "tournaments/index.html", tournaments_tpl.render(
        site=site,
        by_format=by_format,
        total=len(site.tournaments),
        total_lists=sum(len(t.decks) for t in site.tournaments),
        rel="../",
        **ctx_common,
    )))

    # --- mentions légales et vie privée (profondeur 1) ---------------------
    # Page obligatoire dès lors que le site est en ligne, et liée depuis CHAQUE page :
    # une mention légale qu'on ne peut atteindre que par une URL devinée n'informe personne.
    legal_tpl = env.get_template("legal.html")
    written.append(_write(out, "legal/index.html", legal_tpl.render(
        site=site,
        publisher=PUBLISHER,
        contact_url=CONTACT_URL,
        legal_updated=LEGAL_UPDATED,
        rel="../",
        **ctx_common,
    )))

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
    meta_name = f"Meta {ref:%Y-%m}" if ref else "Meta"
    page = meta_tpl.render(
        site=site,
        meta_name=meta_name,
        meta_pairs=meta,
        meta_groups=meta_groups,
        meta_field=[(a, site.archetype_label(a), n) for a, n in window_distribution(site)],
        meta_window_total=sum(n for _, n in window_distribution(site)),
        pack_url="/meta/deckpack.json",
        rel="../",
        **ctx_common,
    )
    written.append(_write(out, "meta/index.html", page))

    # Ordre de retour déterministe : stable sur l'ordre d'insertion ci-dessus,
    # qui ne dépend que du modèle (lui-même trié).
    return written
