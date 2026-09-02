"""Contrat du LOT B — sitegen/render.py + templates. FIGÉ : le worker B implémente.

Interface attendue :
    render.write_pages(site, out: Path, base_url: str) -> list[Path]
"""

from __future__ import annotations

import re

import pytest

from sitegen import render

BASE = "https://exemple.org"


@pytest.fixture
def built(site, tmp_path):
    paths = render.write_pages(site, tmp_path, base_url=BASE)
    return tmp_path, paths


def _html(out, rel):
    return (out / rel).read_text(encoding="utf-8")


def test_emet_exactement_les_pages_du_contrat(built):
    out, paths = built
    rel = {p.relative_to(out).as_posix() for p in paths}
    assert rel == {
        "index.html",
        "style.css",
        "favicon.svg",
        "meta/index.html",
        "formats/op15/index.html",
        "formats/op16/index.html",
        "formats/op16-5/index.html",
        "tournois/2026-07-04-regional-bielefeld/index.html",
        "tournois/2026-04-01-regional-ancien/index.html",
        "tournois/2026-04-15-treasure-cup-noyau/index.html",
        "tournois/2026-06-15-chinoizecup-avance/index.html",
        # Identité = ID de la carte de leader, pas le nom parsé (cf. Deck.archetype_slug).
        # OP11-041 est le leader du deck non parsable : sans placement ni joueur il n'entre
        # dans aucune vue agrégée, donc pas de page.
        "leaders/op15-058/index.html",
        "leaders/op16-022/index.html",
        "leaders/op12-061/index.html",
        "leaders/op01-000/index.html",
    }
    assert all(p.exists() for p in paths)


def test_pas_de_page_html_par_deck(built):
    """Hors portée v1 : les decks sont des ancres sur la page de leur tournoi."""
    out, _ = built
    assert not list(out.glob("decks/**/*.html"))


def test_commande_import_presente_et_absolue(built):
    out, _ = built
    cmd = (f"studio decks import-pack {BASE}/tournois/"
           "2026-07-04-regional-bielefeld/deckpack.json")
    assert cmd in _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    assert f"studio decks import-pack {BASE}/leaders/op15-058/deckpack.json" in \
        _html(out, "leaders/op15-058/index.html")
    assert f"studio decks import-pack {BASE}/meta/deckpack.json" in _html(out, "meta/index.html")


def test_bloc_import_avant_toute_prose(built):
    """Le bloc import précède la description dans le document, sur toutes les pages.

    Ce n'est pas un détail de mise en page : la commande d'import est la seule chose que ce
    site offre et que Limitless n'offre pas. Une description de tournoi de plusieurs lignes
    la repousserait sous la ligne de flottaison en mobile, c'est-à-dire hors de vue.
    """
    out, paths = built
    for p in [q for q in paths if q.suffix == ".html"]:
        text = p.read_text(encoding="utf-8")
        i_import = text.find("studio decks import-pack")
        if i_import < 0:
            continue
        i_desc = text.find("t-desc")
        assert i_desc < 0 or i_import < i_desc, \
            f"la description précède le bloc import dans {p.name}"


def test_page_tournoi_montre_placements_joueurs_et_ids(built):
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    assert "Luka Forjan" in page and "Purple Enel" in page
    assert "OP15-058" in page and "OP15-061" in page
    # le deck non parsable reste affiché, sous son nom brut
    assert "Nom sans structure reconnaissable" in page


def test_commande_import_lisible_sans_scroll(built):
    """P1 — la commande doit s'afficher en entier et se sélectionner d'un clic.

    Mesuré en mobile 375 px avant correction : 297 px visibles sur 847 réels, soit 65 % de
    la commande cachée derrière une barre de défilement de quelques millimètres. Le seul
    élément qui justifie l'existence du site était donc inutilisable.
    """
    out, _ = built
    css = _html(out, "style.css").replace(" ", "").replace("\n", "")
    assert "user-select:all" in css, \
        "sans user-select:all, copier la commande demande une sélection manuelle précise"
    assert "pre-wrap" in css or "break-word" in css or "break-all" in css, \
        "la commande doit revenir à la ligne au lieu de défiler horizontalement"
    assert "white-space:nowrap" not in css


def test_lien_vers_optcgsim_studio(built):
    """P6 — un visiteur qui découvre le site ne sait pas ce qu'est cette commande."""
    out, _ = built
    for rel in ("index.html", "meta/index.html"):
        page = _html(out, rel)
        assert "optcgsim-studio" in page, f"aucune mention de l'outil dans {rel}"
    assert re.search(r"""<a\s[^>]*href=["'][^"']*optcgsim-studio[^"']*["']""",
                     _html(out, "index.html"), re.IGNORECASE), \
        "optcgsim-studio doit être un lien, pas du texte mort"


def test_description_brute_non_affichee(built):
    """P2 — la description est un champ de scraper, pas de l'éditorial.

    Elle répétait le titre et exposait les paramètres internes du scraper sur cinq lignes,
    repoussant le premier deck à ~685 px du haut en mobile.
    """
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    assert "region=Europe" not in page
    assert "time=3months" not in page
    assert "Scraped from" not in page
    # …mais l'attribution reste obligatoire (cf. test_attribution_de_la_source).


def test_decks_replies_dans_details(built):
    """P3 — 16 decklists dépliées faisaient 8 écrans de défilement en mobile."""
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    # 3 decks dans la fixture, chacun replié, plus le premier ouvert.
    assert page.count("<summary") >= 3, "chaque deck doit avoir un summary scannable"
    assert re.search(r"<details[^>]*\sopen", page), "le premier deck doit être ouvert"
    premier = re.search(r"<summary[^>]*>(.*?)</summary>", page, re.DOTALL)
    assert premier and "Purple Enel" in premier.group(1) and "Luka Forjan" in premier.group(1), \
        "le summary doit porter archétype et joueur pour être scannable replié"


def test_cartes_triees_par_quantite_decroissante(built):
    """P4 — l'ordre source empêchait de comparer deux listes du même archétype."""
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    # Sur le TEXTE rendu, pas sur le HTML brut : ce test porte sur l'ORDRE des cartes, et
    # ne doit rien imposer au balisage. Sa version précédente regexait la source, donc
    # exigeait que le chiffre et le « x » soient collés — ce qui interdisait le
    # `<span class="qty">` exigé par ailleurs. Deux de mes tests se contredisaient, et le
    # worker a résolu le conflit en déplaçant la classe sur le total du deck : les deux
    # tests passaient, la puce de carte avait perdu sa distinction.
    texte = re.sub(r"<[^>]+>", "", page)
    bloc = texte[texte.find("OP15-058"):]
    ordre = [(int(q), cid) for q, cid in re.findall(r"(\d+)x\s*(OP\d\d-\d\d\d)", bloc)][:4]
    # Fixture Enel : 4xOP15-061, 4xOP15-067, 3xOP12-071, 2xOP10-067
    assert ordre == sorted(ordre, key=lambda t: (-t[0], t[1])), \
        f"cartes non triées par quantité décroissante puis id : {ordre}"


def test_le_tri_daffichage_ne_touche_pas_les_packs(site, tmp_path):
    """Le tri est cosmétique : `text` reste verbatim, c'est un contrat de données."""
    from sitegen import packs
    biel = next(t for t in site.tournaments if t.slug.endswith("bielefeld"))
    enel = next(d for d in biel.decks if d.placement == 1)
    pack = packs.build_pack("T", ((biel, enel),))
    assert pack["decks"][0]["text"] == enel.text
    # L'ordre SOURCE (non trié) survit au passage par le pack.
    assert pack["decks"][0]["text"].startswith("1xOP15-058\n2xOP10-067\n4xOP15-061")


def test_placement_sans_exposant(built):
    """P6 — `1<sup>st</sup>` s'affichait « 1 st », lu comme une coquille."""
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    assert "<sup" not in page.lower()
    assert "1st" in page


def test_liens_internes_et_ressources_relatifs(built):
    """`dist/` doit être servable depuis n'importe où — domaine, sous-chemin, ou file://.

    Un `href`/`src` interne absolu contre `--base-url` fige le site sur une seule URL : la
    feuille de style meurt dès qu'on déploie ailleurs. Seule la commande d'import affichée
    est absolue, parce qu'elle doit être collable telle quelle dans un terminal.
    """
    out, paths = built
    for p in [q for q in paths if q.suffix in {".html", ".css"}]:
        text = p.read_text(encoding="utf-8")
        for attr in ("href", "src"):
            for url in re.findall(rf"""{attr}\s*=\s*["']([^"']+)""", text):
                assert not url.startswith(BASE), \
                    f"{p.name} : {attr} interne absolu ({url}) — doit être relatif"


def test_commande_import_reste_absolue(built):
    """Corollaire : la commande, elle, DOIT porter l'URL complète."""
    out, _ = built
    assert f"studio decks import-pack {BASE}/meta/deckpack.json" in _html(out, "meta/index.html")


def test_site_utilisable_en_file_url(built):
    """Test de portabilité : la feuille de style doit être atteignable depuis le document."""
    out, _ = built
    page = _html(out, "leaders/op15-058/index.html")
    href = re.search(r"""<link[^>]+href\s*=\s*["']([^"']+)""", page).group(1)
    cible = (out / "leaders" / "op15-058" / href).resolve()
    assert cible.is_file(), f"feuille de style introuvable depuis la page : {href}"


def test_page_en_anglais(built):
    """Le site est en anglais : tout son CONTENU l'est déjà (ids de cartes, joueurs,
    tournois), et son public est celui du Discord OPTCGSim et de Limitless.

    La documentation interne du projet, elle, reste en français — deux publics différents.
    """
    out, paths = built
    for p in [q for q in paths if q.suffix == ".html"]:
        page = p.read_text(encoding="utf-8")
        assert 'lang="en"' in page, f"{p.name} n'est pas déclaré en anglais"
        # Quelques mots français fréquents qui trahiraient une traduction oubliée.
        for mot in ("Tournois", "Importer", "Cœur", "cartes", "listes", "joueurs",
                    "Formats à venir", "Méta courant"):
            assert mot not in page, f"« {mot} » subsiste dans {p.name}"


def test_vocabulaire_tcg_anglais(built):
    """Employer les termes du TCG anglophone, pas des traductions littérales.

    « core » pour les cartes communes, « flex » pour celles qui distinguent une liste —
    ce sont les emplacements qu'un joueur choisit librement une fois le core posé.
    """
    out, _ = built
    page = _html(out, "leaders/op01-000/index.html")
    assert re.search(r"\bcore\b", page, re.IGNORECASE), "« core » attendu"
    assert re.search(r"\bflex\b", page, re.IGNORECASE), "« flex » attendu"
    for banni in ("delta", "difference", "gap", "common core"):
        assert banni.lower() not in page.lower(), f"« {banni} » : préférer core/flex"


def test_theme_sombre_par_defaut(built):
    """Registre « outil de joueur » : le fond est sombre SANS attendre une préférence.

    Un thème clair reste servi à qui le demande explicitement, donc on exige aussi le bloc
    `prefers-color-scheme: light`.
    """
    out, _ = built
    css = _html(out, "style.css").replace(" ", "").replace("\n", "")
    assert "prefers-color-scheme:light" in css, \
        "un thème clair doit rester disponible pour qui le demande"
    # Le fond par défaut doit être sombre : on le vérifie par la luminance de la couleur
    # déclarée sur body/:root hors media query.
    hors_media = re.split(r"@media", _html(out, "style.css"))[0]
    fonds = re.findall(r"background(?:-color)?\s*:\s*#([0-9a-fA-F]{3,6})", hors_media)
    assert fonds, "aucune couleur de fond déclarée hors media query"
    def lum(h):
        h = h if len(h) == 6 else "".join(c * 2 for c in h)
        r, v, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return (0.299 * r + 0.587 * v + 0.114 * b) / 255
    assert lum(fonds[0]) < 0.35, f"fond par défaut trop clair (#{fonds[0]})"


def test_chiffres_tabulaires(built):
    """Le site est rempli de « 4x », « 50/50 », « 234 listes » : sans chiffres de largeur
    fixe, rien ne s'aligne en colonne et l'ensemble paraît bâclé."""
    out, _ = built
    css = _html(out, "style.css").replace(" ", "")
    assert "tabular-nums" in css


def test_bloc_import_traite_comme_un_terminal(built):
    """C'est une commande shell : la faire ressembler à autre chose brouille le seul
    message du site. Surface distincte et marqueur de prompt."""
    out, _ = built
    page = _html(out, "meta/index.html")
    css = _html(out, "style.css")
    assert re.search(r"""class=["'][^"']*import[^"']*["']""", page)
    # Un marqueur de prompt, injecté en CSS pour rester hors du texte copié.
    assert "content:" in css.replace(" ", "") and "$" in css, \
        "le bloc doit porter un marqueur de prompt (en CSS, pour ne pas polluer la copie)"


def test_favicon_maison_et_meme_origine(built):
    """Seule exception à « aucun asset », et elle est délibérée : l'invariant vise les
    assets de CARTES sous copyright, pas une icône de projet."""
    out, paths = built
    svg = out / "favicon.svg"
    assert svg.is_file(), "favicon.svg manquant"
    contenu = svg.read_text(encoding="utf-8")
    assert contenu.lstrip().startswith("<svg"), "le favicon doit être un SVG écrit à la main"

    # `xmlns` est OBLIGATOIRE pour un SVG autonome servi en image/svg+xml : sans lui le
    # navigateur refuse de le rendre, silencieusement. Vérifié : naturalWidth valait 0.
    assert 'xmlns="http://www.w3.org/2000/svg"' in contenu, \
        "un SVG autonome sans xmlns ne se rend pas du tout"

    # Aucune RÉFÉRENCE externe — à distinguer de l'URI de namespace ci-dessus, qui est un
    # identifiant que le navigateur ne récupère jamais. La première version de ce test
    # interdisait la chaîne « http » tout court, ce qui interdisait mécaniquement le xmlns
    # requis : un test trop strict a produit un artefact cassé.
    for attr in ("href", "src", "xlink:href"):
        assert f"{attr}=" not in contenu, f"référence externe ({attr}) dans le favicon"
    assert "url(" not in contenu, "référence externe (url()) dans le favicon"
    for rel in ("index.html", "meta/index.html", "leaders/op15-058/index.html"):
        page = _html(out, rel)
        m = re.search(r"""<link[^>]*rel=["'][^"']*icon[^"']*["'][^>]*>""", page)
        assert m, f"favicon non référencé dans {rel}"
        assert "http" not in m.group(0), "le favicon doit être servi en relatif"


def test_placement_de_tete_distingue(built):
    """Une page de 16 decks doit se parcourir des yeux : le podium se distingue, le
    reste reste calme."""
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    css = _html(out, "style.css")
    assert re.search(r"""class=["'][^"']*(rank|place|podium)[^"']*["']""", page), \
        "le placement doit porter une classe pour être distingué"
    assert re.search(r"\.(rank|place|podium)[\w-]*", css), \
        "et cette classe doit être stylée"


def test_puce_de_carte_distingue_quantite_et_id(built):
    """Un 4-of doit se lire comme la colonne vertébrale du deck, et une quantité
    inhabituelle (cartes sans limite, jouées à 8 ou 9) doit sauter aux yeux."""
    out, _ = built
    for rel in ("tournois/2026-07-04-regional-bielefeld/index.html",
                "leaders/op15-058/index.html"):
        page = _html(out, rel)
        # La quantité d'une CARTE, pas le total du deck : on exige le motif suivi d'un
        # identifiant de carte. Sans cette ancre, la classe posée sur « 50/50 cartes »
        # satisfaisait le test alors que les puces n'étaient pas traitées.
        assert re.search(
            r"""<[^>]*class=["'][^"']*(?:qty|quantite|qte)[^"']*["'][^>]*>\s*\d+\s*"""
            r"""</[^>]+>\s*x?\s*[A-Z]{2,4}\d\d-\d\d\d""", page), \
            f"la quantité d'une carte doit être un élément distinct de son id, dans {rel}"


def test_attribution_sans_libelle_duplique(built):
    """« Source : Limitless · Limitless » — deux URL de la même source donnaient deux fois
    le même libellé, ce qui ressemble à un bug d'affichage."""
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    # Fenêtre volontairement large : à 220 caractères elle coupait avant le second `</a>`,
    # le test ne voyait qu'un libellé et passait alors que la duplication était bien là.
    # Et pas de `if` — un test qui ne trouve pas son sujet doit échouer, pas se taire.
    bloc = re.search(r"Source\s*:(.*?)</p>", page, re.DOTALL)
    assert bloc, "aucun bloc « Source : » sur la page de tournoi"
    libelles = re.findall(r">([^<>]{2,40})</a>", bloc.group(1))
    assert len(libelles) >= 2, f"la fixture a deux URL source, trouvé {libelles}"
    assert len(libelles) == len(set(libelles)), \
        f"libellé de source dupliqué : {libelles}"


def test_attribution_porte_un_libelle_lisible(built):
    """Une URL brute de 45 caractères comme texte de lien n'est pas de l'attribution.

    Le nom de la source (« Limitless ») dit en un mot ce que l'URL dit en deux lignes.
    """
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    assert ">https://" not in page, "le texte du lien ne doit pas être l'URL brute"
    assert re.search(r"<a\s[^>]*limitlesstcg[^>]*>[^<]*[Ll]imitless", page), \
        "le lien de source doit être libellé par le nom du site"


def test_pas_de_leader_en_double(built):
    """Le `<summary>` porte déjà le leader : le répéter dans le corps est du bruit."""
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    assert "Leader :" not in page
    premier = re.search(r"<summary[^>]*>(.*?)</summary>", page, re.DOTALL).group(1)
    assert "OP15-058" in premier, "le summary doit porter le leader"
    assert "50" in premier, "le summary doit porter le total de cartes"


def test_page_leader_montre_lecart(built):
    """LOT E — sur un archétype assez fourni, la page affiche les écarts, pas 5 listes
    quasi identiques à lire l'une après l'autre."""
    out, _ = built
    page = _html(out, "leaders/op01-000/index.html")
    assert "core" in page.lower(), \
        "le cœur commun doit être nommé et affiché une seule fois"
    assert re.search(r"\d+\s*carte", page), "la taille de l'écart doit être indiquée"
    # Les cartes hors cœur restent visibles ; celles du cœur ne sont pas répétées 5 fois.
    assert page.count("OP01-001") <= 2, \
        "une carte du cœur ne doit pas être répétée pour chaque liste"
    for hors_coeur in ("OP01-010", "OP01-011", "OP01-012", "OP01-013"):
        assert hors_coeur in page, f"{hors_coeur} est un écart, il doit rester visible"


def test_index_annonce_les_formats(built):
    """Le format est le premier repère qu'un joueur cherche : « on est en quelle méta ? »."""
    out, _ = built
    page = _html(out, "index.html")
    assert "OP16" in page and "OP15" in page
    assert re.search(r"""href=["'][^"']*formats/op16/""", page), \
        "les formats doivent être navigables depuis l'accueil"


def test_index_distingue_courant_a_venir_et_passes(built):
    """Trois rôles, mais les formats gardent leurs codes réels — on annote, on ne renomme pas.

    Fixture : courant OP16 (tournoi le plus récent), à venir OP16.5 (tournoi en ligne joué
    en avance), passé OP15.
    """
    out, _ = built
    page = _html(out, "index.html")
    for role in ("courant", "venir"):
        assert role in page.lower(), f"le rôle « {role} » doit être nommé sur l'accueil"
    # Les codes réels restent les identifiants affichés et liés.
    assert "OP16.5" in page and "OP16" in page and "OP15" in page
    assert re.search(r"""href=["'][^"']*formats/op16-5/""", page)

    # Le format à venir doit être présenté APRÈS le courant, pas fondu dans la liste.
    i_courant, i_venir = page.lower().find("courant"), page.lower().find("venir")
    assert 0 < i_courant < i_venir


def test_ordre_des_formats_suit_le_modele(tmp_path):
    """Le rendu doit CONSOMMER l'ordre du modèle, pas en refaire un.

    Bug observé sur le corpus réel : « Formats passés » affichait OP15, OP14, OP13, OP14.5 —
    OP14.5 relégué après OP13, alors que `Site.past_formats` renvoyait le bon ordre. Le
    rendu re-triait, et sur des libellés à décimale un tri maison se trompe.
    """
    from datetime import date

    from sitegen.model import Deck, Site, Tournament

    def t(slug, fmt, mois, jour, circuit="paper"):
        d = Deck(raw_name="X — Y (1)", archetype="X", player="Y", placement=1,
                 leader_id="OP01-001", cards=(("OP01-002", 4),),
                 text="1xOP01-001\n4xOP01-002")
        return Tournament(slug, slug, date(2026, mois, jour), "", "", (d,),
                          format=fmt, circuit=circuit)

    # Les dates DIVERGENT volontairement de l'ordre des formats, comme dans le corpus réel :
    # OP14.5 n'a qu'un tournoi ancien (mars), tandis qu'OP14 en a un plus récent (juin). Un
    # tri sur « date du tournoi le plus récent du format » reléguerait donc OP14.5 en fin de
    # liste — c'est exactement le bug observé, où OP14.5 s'affichait après OP13.
    site = Site(tournaments=(
        t("2026-07-20-a", "OP16", 7, 20), t("2026-07-10-b", "OP15", 7, 10),
        t("2026-03-05-c", "OP14.5", 3, 5), t("2026-06-01-d", "OP14", 6, 1),
        t("2026-02-01-e", "OP13", 2, 1),
        t("2026-07-25-f", "OP16.5", 7, 25, circuit="online"),
    ))
    assert site.past_formats == ("op15", "op14-5", "op14", "op13")

    paths = render.write_pages(site, tmp_path, base_url=BASE)
    page = next(p for p in paths if p.name == "index.html").read_text()
    positions = [page.find(f"formats/{f}/") for f in site.past_formats]
    assert all(p >= 0 for p in positions), "tous les formats passés doivent être liés"
    assert positions == sorted(positions), \
        f"ordre d'affichage {positions} ≠ ordre du modèle {site.past_formats}"


def test_page_format_annonce_son_role(built):
    """Un visiteur arrivant directement sur /formats/op16-5/ doit savoir où il est."""
    out, _ = built
    assert "venir" in _html(out, "formats/op16-5/index.html").lower()
    assert "courant" in _html(out, "formats/op16/index.html").lower()


def test_meta_reste_ancre_au_format_courant(built):
    """`/meta/` sert l'instantané courant. Les formats à venir ont déjà leurs pages."""
    out, _ = built
    page = _html(out, "meta/index.html")
    assert "OP16" in page
    assert f"studio decks import-pack {BASE}/meta/deckpack.json" in page


def test_page_format_liste_ses_archetypes(built):
    out, _ = built
    page = _html(out, "formats/op15/index.html")
    assert "OP15" in page
    assert "Blue Doflamingo" in page, "l'archétype OP15 de la fixture doit y figurer"
    assert "studio decks import-pack" in page
    # Un archétype qui n'existe qu'en OP16 n'a rien à faire sur la page OP15.
    assert "Red/Black Koby" not in page


def test_page_leader_cloisonne_par_format(built):
    """Exigence de justesse : un cœur calculé sur deux formats décrit un deck fictif.

    purple-enel a une liste en OP16 et une en OP15 dans la fixture : la page doit les
    présenter séparément, pas les fondre.
    """
    out, _ = built
    page = _html(out, "leaders/op15-058/index.html")
    assert "OP16" in page and "OP15" in page
    i16, i15 = page.find("OP16"), page.find("OP15")
    assert 0 < i16 < i15, "les formats doivent aller du plus récent au plus ancien"


def test_page_leader_import_par_format(built):
    """Chaque section de format porte sa propre commande, restreinte à ce format."""
    out, _ = built
    page = _html(out, "leaders/op01-000/index.html")
    assert f"studio decks import-pack {BASE}/leaders/op01-000/op15.json" in page


def test_plafond_de_listes_par_section(tmp_path):
    """Au plus 24 listes affichées par format ; le cœur et le pack portent sur toutes.

    Sur le corpus réel un archétype atteint 234 listes — une page de plus d'un demi-Mo,
    illisible en mobile. Construit ici en mémoire plutôt qu'en fixture : 30 decks de fichiers
    alourdiraient tous les autres tests pour un seul comportement.
    """
    from datetime import date

    from sitegen.model import Deck, Site, Tournament

    decks = tuple(
        Deck(raw_name=f"Purple Enel — J{i:02d} ({i})", archetype="Purple Enel",
             player=f"J{i:02d}", placement=i, leader_id="OP15-058",
             cards=(("OP15-061", 4), ("OP15-067", 3)),
             text="1xOP15-058\n4xOP15-061\n3xOP15-067")
        for i in range(1, 31)
    )
    t = Tournament("2026-07-04-gros", "OP16 Gros Tournoi", date(2026, 7, 4), "", "",
                   decks, format="OP16")
    paths = render.write_pages(Site(tournaments=(t,)), tmp_path, base_url=BASE)
    page = next(p for p in paths
                if p.as_posix().endswith("leaders/op15-058/index.html")).read_text()

    affichees = len(re.findall(r"J\d\d", page))
    assert affichees <= 24, f"{affichees} listes affichées, plafond 24"
    assert "30" in page, "le total réel doit rester annoncé"
    assert re.search(r"(6|autre|omis|de plus)", page, re.IGNORECASE), \
        "le nombre de listes non affichées doit être indiqué"


def _site_avec_ecarts():
    """5 listes partageant 12 cartes, chacune avec une carte propre : cœur de 12, écart de 1."""
    from datetime import date

    from sitegen.model import Deck, Site, Tournament

    commun = tuple((f"OP01-{i:03d}", 4) for i in range(1, 13))          # 48 cartes
    decks = []
    for i in range(5):
        propre = (f"OP02-{i:03d}", 2)                                    # +2 = 50
        cartes = commun + (propre,)
        texte = "1xOP01-000\n" + "\n".join(f"{q}x{c}" for c, q in cartes)
        decks.append(Deck(raw_name=f"X — J{i} ({i + 1})", archetype="X", player=f"J{i}",
                          placement=i + 1, leader_id="OP01-000", cards=cartes, text=texte))
    t = Tournament("2026-07-04-t", "OP16 Tournoi", date(2026, 7, 4), "", "",
                   tuple(decks), format="OP16")
    return Site(tournaments=(t,))


def test_aucun_pluriel_parenthese(built):
    """« carte(s) » est une facilité d'écriture, pas du français.

    1705 occurrences sur le corpus réel, dont 1025 « carte(s) ». Le nombre est toujours connu
    au moment du rendu : il n'y a aucune raison de laisser le lecteur choisir.
    """
    out, paths = built
    for p in [q for q in paths if q.suffix in {".html", ".css"}]:
        texte = p.read_text(encoding="utf-8")
        trouve = re.findall(r"\w+\((?:s|x)\)", texte)
        assert not trouve, f"pluriel parenthésé dans {p.name} : {sorted(set(trouve))[:5]}"


def test_accord_singulier_et_pluriel(tmp_path):
    """Un seul élément se dit au singulier, plusieurs au pluriel."""
    from datetime import date

    from sitegen.model import Deck, Site, Tournament

    d = Deck(raw_name="X — J (1)", archetype="X", player="J", placement=1,
             leader_id="OP01-000", cards=(("OP01-001", 4),), text="1xOP01-000\n4xOP01-001")
    un = Tournament("2026-07-04-un", "OP16 Un", date(2026, 7, 4), "", "", (d,), format="OP16")
    page = next(p for p in render.write_pages(Site(tournaments=(un,)), tmp_path, base_url=BASE)
                if p.name == "index.html").read_text()
    assert "1 tournament " in page or "1 tournament<" in page or "1 tournament\n" in page
    assert "1 tournaments" not in page
    assert "1 lists" not in page


def test_nombre_d_ecart_annonce_une_seule_fois(tmp_path):
    """Le compte d'écart figurait dans le résumé ET en titre juste dessous.

    Le résumé est le bon endroit : il reste visible quand la liste est repliée.
    """
    paths = render.write_pages(_site_avec_ecarts(), tmp_path, base_url=BASE)
    page = next(p for p in paths
                if p.as_posix().endswith("leaders/op01-000/index.html")).read_text()
    # Le compte de flex figurait dans le résumé ET en titre juste dessous.
    assert "card(s) flex" not in page
    # 5 listes, donc 5 mentions de flex — pas 10.
    mentions = len(re.findall(r"\bflex\b", page, re.IGNORECASE))
    assert mentions == 5, f"{mentions} mentions de « flex » pour 5 listes"


def test_page_leader_offre_l_import_par_deck(built):
    """Sur une page de leader, l'action utile est « prendre CELLE-CI », pas tout importer.

    72 listes Enel en OP16 ne font que 36 variantes réelles à ≤ 2 cartes : les importer en
    bloc remplit le simulateur de decks à deux cartes d'écart.
    """
    out, _ = built
    page = _html(out, "leaders/op15-058/index.html")
    # Chaque liste porte une commande d'import qui lui est propre, vers le pack d'un deck.
    assert re.search(
        rf"studio decks import-pack {re.escape(BASE)}/tournois/[^/]+/decks/[^\s\"'<]+\.json",
        page), "aucune commande d'import par deck sur la page de leader"


def test_page_leader_relegue_l_import_en_bloc(built):
    """Le pack complet reste offert — c'est un inventaire — mais il ne doit plus être le
    premier élément de la page, et doit dire ce qu'il contient réellement."""
    out, _ = built
    page = _html(out, "leaders/op15-058/index.html")
    i_bloc = page.find(f"{BASE}/leaders/op15-058/deckpack.json")
    i_deck = page.find(f"{BASE}/tournois/")
    assert i_deck > 0, "aucune action par deck trouvée"
    assert i_bloc < 0 or i_deck < i_bloc, \
        "l'import par deck doit précéder l'import en bloc sur une page de leader"


def test_deck_copiable_au_format_natif(built):
    """Le copier/coller natif ne demande AUCUNE installation — ni studio, ni terminal.

    C'est ce qui ouvre le site à quiconque joue, donc un chemin de premier plan.
    """
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    css = _html(out, "style.css").replace(" ", "").replace("\n", "")
    # La decklist native, verbatim, dans un bloc dédié et sélectionnable d'un geste.
    assert re.search(r"""class=["'][^"']*(decklist)[^"']*["']""", page), \
        "aucun bloc de decklist au format natif"
    bloc = re.search(
        r"""<[^>]*class=["'][^"']*(?:decklist)[^"']*["'][^>]*>(.{0,400})""",
        page, re.DOTALL)
    assert bloc and re.search(r"1x\s*OP\d\d-\d\d\d", bloc.group(1)), \
        "le bloc natif doit contenir la decklist, leader compris"
    assert "user-select:all" in css


def test_page_leader_annonce_la_convergence(built):
    """Plusieurs joueurs sur la même liste au caractère près : c'est le signal le plus fort
    qu'une liste est résolue, et l'annoncer vaut mieux que d'aligner des entrées identiques.

    Fixture : Krullzor et mirkosp95 jouent la même liste en OP16.5 (ordre des lignes
    différent, signature identique).
    """
    out, _ = built
    page = _html(out, "leaders/op15-058/index.html")
    assert re.search(r"""class=["'][^"']*converg[^"']*["']""", page), \
        "la convergence doit porter une classe pour être stylée et testable"
    # Les deux joueurs restent nommés — on annonce le partage, on ne fusionne pas les voix.
    assert "Krullzor" in page and "mirkosp95" in page
    bloc = re.search(r"""<[^>]*class=["'][^"']*converg[^"']*["'][^>]*>(.{0,200})""",
                     page, re.DOTALL)
    assert bloc and re.search(r"\d+\s*joueur", bloc.group(1)), \
        "le nombre de joueurs partageant la liste doit être annoncé"


def test_page_leader_sous_le_seuil_reste_complete(built):
    """purple-enel n'a que 2 listes : pas de cœur, affichage complet conservé."""
    out, _ = built
    page = _html(out, "leaders/op15-058/index.html")
    assert "OP15-061" in page and "OP15-067" in page


def test_page_leader_cite_la_provenance(built):
    """Toute la valeur de preuve d'une page leader est dans la provenance des listes."""
    out, _ = built
    page = _html(out, "leaders/op15-058/index.html")
    assert "Luka Forjan" in page and "Vieux Joueur" in page
    assert "Bielefeld" in page and "Ancien" in page


def test_index_liste_tournois_et_archetypes(built):
    out, _ = built
    page = _html(out, "index.html")
    assert "Bielefeld" in page and "Ancien" in page
    assert "op15-058" in page
    assert "meta/" in page


def test_aucune_sous_ressource_externe(built):
    """Invariant AGENTS.md : rien n'est chargé automatiquement depuis un tiers.

    Une sous-ressource expose l'IP du visiteur à l'affichage ; un `<a href>` externe non
    (cf. test_attribution_de_la_source ci-dessous, qui les exige au contraire).
    """
    out, paths = built
    sous_ressource = re.compile(
        r"""(?:src|srcset|data-src)\s*=\s*["']([^"']+)"""
        r"""|<link[^>]+href\s*=\s*["']([^"']+)"""
        r"""|@import\s+(?:url\()?["']?([^"')\s;]+)"""
        r"""|url\(\s*["']?([^"')]+)""", re.IGNORECASE)

    for p in paths:
        if p.suffix not in {".html", ".css"}:
            continue
        text = p.read_text(encoding="utf-8")
        for groups in sous_ressource.findall(text):
            url = next((g for g in groups if g), "")
            if url.lower().startswith(("http://", "https://")):
                assert url.startswith(BASE), f"sous-ressource externe dans {p.name} : {url}"
        for motif in ("<script", "@import", "cdn.", "fonts.google", "googletagmanager"):
            assert motif not in text.lower(), f"{motif} interdit dans {p.name}"


def test_attribution_de_la_source(built):
    """Les URL de la `description` deviennent des liens cliquables et crédités.

    Citer Limitless est un choix délibéré : c'est ce qui distingue ce site d'une reprise de
    données non créditée. `noreferrer` pour ne pas leur envoyer le référent du visiteur,
    `nofollow` pour ne pas leur promettre de poids SEO.
    """
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    lien = re.search(
        r"""<a\s[^>]*href=["']https://onepiece\.limitlesstcg\.com/tournaments/431["'][^>]*>""",
        page, re.IGNORECASE)
    assert lien, "l'URL source de la description n'est pas rendue cliquable"
    assert "noreferrer" in lien.group(0).lower()
    assert "nofollow" in lien.group(0).lower()


def test_tout_lien_externe_est_protege(built):
    out, paths = built
    for p in [q for q in paths if q.suffix == ".html"]:
        text = p.read_text(encoding="utf-8")
        for balise in re.findall(r"<a\s[^>]*href\s*=\s*[\"']https?://[^\"']+[\"'][^>]*>",
                                 text, re.IGNORECASE):
            if BASE in balise:
                continue
            assert "noreferrer" in balise.lower(), f"lien externe nu dans {p.name} : {balise}"


def test_html_minimal_valide_et_responsive(built):
    out, paths = built
    for p in [q for q in paths if q.suffix == ".html"]:
        text = p.read_text(encoding="utf-8")
        assert text.lstrip().lower().startswith("<!doctype html>")
        assert 'lang=' in text and "<title>" in text
        assert 'name="viewport"' in text, f"pas de viewport dans {p}"
        assert 'href="' in text or p.name == "style.css"


def test_echappement_html(site, tmp_path):
    """`&` dans « Luffy & Ace » doit sortir échappé, pas brut."""
    from sitegen.model import Deck, Site, Tournament
    from datetime import date
    d = Deck(raw_name="R/G Luffy & Ace — A <b>B</b> (1st)", archetype="R/G Luffy & Ace",
             player="A <b>B</b>", placement=1, leader_id="OP01-001",
             cards=(("OP01-002", 4),), text="1xOP01-001\n4xOP01-002")
    t = Tournament("2026-07-04-x", "X & Y", date(2026, 7, 4), "", "", (d,))
    paths = render.write_pages(Site(tournaments=(t,)), tmp_path, base_url=BASE)
    page = next(p for p in paths if p.as_posix().endswith("2026-07-04-x/index.html"))
    text = page.read_text(encoding="utf-8")
    assert "<b>B</b>" not in text
    assert "&lt;b&gt;" in text or "&amp;lt;b&amp;gt;" in text


def test_write_pages_est_deterministe(site, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    render.write_pages(site, a, base_url=BASE)
    render.write_pages(site, b, base_url=BASE)
    for pa in sorted(a.rglob("*")):
        if pa.is_file():
            assert pa.read_bytes() == (b / pa.relative_to(a)).read_bytes(), \
                f"sortie non déterministe : {pa}"
