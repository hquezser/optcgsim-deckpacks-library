"""Contrat du LOT B — sitegen/render.py + templates. FIGÉ : le worker B implémente.

Interface attendue :
    render.write_pages(site, out: Path, base_url: str,
                       card_link_base: str = "") -> list[Path]
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
        "legal/index.html",
        "tournaments/index.html",
        "meta/index.html",
        "formats/op15/index.html",
        "formats/op16/index.html",
        "formats/op16-5/index.html",
        "tournaments/2026-07-04-regional-bielefeld/index.html",
        "tournaments/2026-04-01-regional-ancien/index.html",
        "tournaments/2026-04-15-treasure-cup-noyau/index.html",
        "tournaments/2026-06-15-chinoizecup-avance/index.html",
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
    cmd = (f"studio decks import-pack {BASE}/tournaments/"
           "2026-07-04-regional-bielefeld/deckpack.json")
    assert cmd in _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
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
    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
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
    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
    assert "region=Europe" not in page
    assert "time=3months" not in page
    assert "Scraped from" not in page
    # …mais l'attribution reste obligatoire (cf. test_attribution_de_la_source).


def test_decks_replies_dans_details(built):
    """P3 — 16 decklists dépliées faisaient 8 écrans de défilement en mobile."""
    out, _ = built
    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
    # 3 decks dans la fixture, chacun replié, plus le premier ouvert.
    assert page.count("<summary") >= 3, "chaque deck doit avoir un summary scannable"
    assert re.search(r"<details[^>]*\sopen", page), "le premier deck doit être ouvert"
    premier = re.search(r"<summary[^>]*>(.*?)</summary>", page, re.DOTALL)
    assert premier and "Purple Enel" in premier.group(1) and "Luka Forjan" in premier.group(1), \
        "le summary doit porter archétype et joueur pour être scannable replié"


def test_cartes_triees_par_quantite_decroissante(built):
    """P4 — l'ordre source empêchait de comparer deux listes du même archétype."""
    out, _ = built
    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
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
    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
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


def test_anglais_sans_calques_du_francais(built):
    """Les tests peuvent passer avec un anglais mot-à-mot. Ces tournures-là sont des
    traductions littérales repérées sur le rendu, pas des hypothèses.

    « in one gesture » vient de « en un geste » — on dit « in one click ». « is offered »
    vient de « est offert » — on dit « is available ». Et « native decklist » est banni par
    le glossaire : c'est du vocabulaire de développeur, pas de joueur.
    """
    out, paths = built
    calques = {
        "in one gesture": "in one click",
        "is offered": "is available",
        "native decklist": "decklist",
        "Import to OPTCGSim": "Import into OPTCGSim",
    }
    for p in [q for q in paths if q.suffix == ".html"]:
        page = p.read_text(encoding="utf-8")
        for mauvais, bon in calques.items():
            assert mauvais.lower() not in page.lower(), \
                f"« {mauvais} » dans {p.name} : préférer « {bon} »"


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
    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
    css = _html(out, "style.css")
    assert re.search(r"""class=["'][^"']*(rank|place|podium)[^"']*["']""", page), \
        "le placement doit porter une classe pour être distingué"
    assert re.search(r"\.(rank|place|podium)[\w-]*", css), \
        "et cette classe doit être stylée"


def test_puce_de_carte_distingue_quantite_et_id(built):
    """Un 4-of doit se lire comme la colonne vertébrale du deck, et une quantité
    inhabituelle (cartes sans limite, jouées à 8 ou 9) doit sauter aux yeux."""
    out, _ = built
    for rel in ("tournaments/2026-07-04-regional-bielefeld/index.html",
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
    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
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
    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
    assert ">https://" not in page, "le texte du lien ne doit pas être l'URL brute"
    assert re.search(r"<a\s[^>]*limitlesstcg[^>]*>[^<]*[Ll]imitless", page), \
        "le lien de source doit être libellé par le nom du site"


def test_pas_de_leader_en_double(built):
    """Le `<summary>` porte déjà le leader : le répéter dans le corps est du bruit."""
    out, _ = built
    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
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


def test_plafond_par_section_compte_les_groupes_pas_les_listes(tmp_path):
    """Au plus 24 GROUPES affichés par format — et plus aucune liste jetée quand elle tient
    dans un groupe affiché.

    Ce test épinglait avant « au plus 24 noms de joueurs », un proxy du vrai invariant : une
    page d'un demi-Mo est illisible en mobile. Le proxy interdisait la bonne solution. Avec
    le regroupement, 30 listes identiques ne coûtent QU'UNE decklist affichée — le poids est
    porté par les decklists, pas par les noms — et les 30 joueurs restent nommés au lieu
    d'être tronqués.

    Mesuré sur le corpus réel en changeant de règle : +7 % de poids sur les pages /leaders/,
    +1 % sur le site entier, et 270 listes qui étaient purement et simplement jetées
    redeviennent visibles.
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

    # Les 30 listes sont identiques : un seul groupe, donc une seule decklist affichée.
    assert page.count('class="deck-details"') <= render.LEADER_GROUPS_CAP, \
        "plus de decklists affichées que le plafond de groupes"
    # Et surtout : aucun joueur n'est perdu, là où la troncature en jetait six.
    for i in range(1, 31):
        assert f"J{i:02d}" in page, f"J{i:02d} a disparu de la page"
    assert "30" in page, "le total réel doit rester annoncé"


def test_le_plafond_de_groupes_annonce_les_listes_perdues(tmp_path):
    """Quand il y a vraiment trop de groupes, ce qui reste hors page se compte en LISTES.

    Annoncer « 3 groupes omis » ne dirait pas au lecteur combien de listes il ne voit pas.
    """
    from datetime import date

    from sitegen.model import Deck, Site, Tournament

    # 30 listes deux à deux distinctes de plus d'un échange : 30 groupes, plafond 24.
    decks = tuple(
        Deck(raw_name=f"Purple Enel — K{i:02d} ({i})", archetype="Purple Enel",
             player=f"K{i:02d}", placement=i, leader_id="OP15-058",
             cards=(("OP15-061", 4), (f"OP16-{i:03d}", 4)),
             text=f"1xOP15-058\n4xOP15-061\n4xOP16-{i:03d}")
        for i in range(1, 31)
    )
    t = Tournament("2026-07-04-varie", "OP16 Tournoi Varié", date(2026, 7, 4), "", "",
                   decks, format="OP16")
    paths = render.write_pages(Site(tournaments=(t,)), tmp_path, base_url=BASE)
    page = next(p for p in paths
                if p.as_posix().endswith("leaders/op15-058/index.html")).read_text()

    assert page.count('class="deck-details"') <= render.LEADER_GROUPS_CAP
    assert re.search(r"6 more list", page), \
        "les 6 listes hors page doivent être annoncées en listes, pas en groupes"


def test_un_groupe_dit_QUEL_echange_le_distingue(tmp_path):
    """Sans ça, le regroupement PERD de l'information : une carte présente seulement chez un
    membre disparaîtrait de la page. Attrapé par test_page_leader_montre_lecart en réel.
    """
    from datetime import date

    from sitegen.model import Deck, Site, Tournament

    commun = tuple((f"OP01-{i:03d}", 4) for i in range(1, 13))
    a = Deck(raw_name="A — Ana (1)", archetype="A", player="Ana", placement=1,
             leader_id="OP15-058", cards=commun + (("OP02-111", 2),),
             text="1xOP15-058\n" + "\n".join(f"{q}x{c}" for c, q in commun + (("OP02-111", 2),)))
    b = Deck(raw_name="A — Bo (2)", archetype="A", player="Bo", placement=2,
             leader_id="OP15-058", cards=commun + (("OP02-111", 1), ("OP02-222", 1)),
             text="1xOP15-058\n" + "\n".join(
                 f"{q}x{c}" for c, q in commun + (("OP02-111", 1), ("OP02-222", 1))))
    t = Tournament("2026-07-04-x", "OP16 X", date(2026, 7, 4), "", "", (a, b), format="OP16")
    paths = render.write_pages(Site(tournaments=(t,)), tmp_path, base_url=BASE)
    page = next(p for p in paths
                if p.as_posix().endswith("leaders/op15-058/index.html")).read_text()

    assert "OP02-222" in page, \
        "la carte propre au membre du groupe doit rester visible sur la page"
    assert "swap" in page.lower(), "la règle de regroupement doit être annoncée au lecteur"


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
        rf"studio decks import-pack {re.escape(BASE)}/tournaments/[^/]+/decks/[^\s\"'<]+\.json",
        page), "aucune commande d'import par deck sur la page de leader"


def test_page_leader_relegue_l_import_en_bloc(built):
    """Le pack complet reste offert — c'est un inventaire — mais il ne doit plus être le
    premier élément de la page, et doit dire ce qu'il contient réellement."""
    out, _ = built
    page = _html(out, "leaders/op15-058/index.html")
    i_bloc = page.find(f"{BASE}/leaders/op15-058/deckpack.json")
    i_deck = page.find(f"{BASE}/tournaments/")
    assert i_deck > 0, "aucune action par deck trouvée"
    assert i_bloc < 0 or i_deck < i_bloc, \
        "l'import par deck doit précéder l'import en bloc sur une page de leader"


def test_deck_copiable_au_format_natif(built):
    """Le copier/coller natif ne demande AUCUNE installation — ni studio, ni terminal.

    C'est ce qui ouvre le site à quiconque joue, donc un chemin de premier plan.
    """
    out, _ = built
    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
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
    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
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


# --------------------------------------------------------------- LOT F : lien par carte
# Amendement du 2026-09-03 (cf. AGENTS.md § invariants, SPEC § « Lien par carte »). Le
# lien par carte est la SEULE ouverture consentie à l'invariant zéro-copyright, et elle
# tient entièrement à trois propriétés : opt-in, `<a href>` et jamais une sous-ressource,
# libellé = ID. Ces trois tests sont ce qui les rend non négociables.

CARD_LINK = "https://onepiece.limitlesstcg.com/cards/{id}"


def test_sans_drapeau_aucun_lien_par_carte(built):
    """Opt-in : sans `--card-link-base`, la sortie ne contient aucun lien de carte.

    C'est ce qui rend l'amendement réversible — et ce qui garantit que le site publié
    reste en IDs nus tant que personne n'a explicitement demandé autre chose.
    """
    out, paths = built
    for p in paths:
        if p.suffix != ".html":
            continue
        text = p.read_text(encoding="utf-8")
        assert "limitlesstcg.com/cards/" not in text, \
            f"lien de carte alors que le drapeau est absent : {p.name}"


def test_avec_drapeau_lid_est_lie_et_protege(site, tmp_path):
    """Chaque ID devient un `<a>` vers le gabarit, avec `rel` complet et `target`.

    `noreferrer` pour ne pas envoyer le référent du visiteur, `nofollow` pour ne pas
    promettre de poids SEO — même contrat que l'attribution de source. Sans `rel`, le
    lien tomberait sous le coup de `check_dist.check_no_outbound`.
    """
    paths = render.write_pages(site, tmp_path, base_url=BASE, card_link_base=CARD_LINK)
    page = next(p for p in paths
                if p.as_posix().endswith("2026-07-04-regional-bielefeld/index.html"))
    text = page.read_text(encoding="utf-8")

    balise = re.search(
        r"""<a\s[^>]*href=["']https://onepiece\.limitlesstcg\.com/cards/OP15-061["'][^>]*>""",
        text)
    assert balise, "OP15-061 n'est pas lié alors que le drapeau est passé"
    assert "noreferrer" in balise.group(0).lower()
    assert "nofollow" in balise.group(0).lower()
    assert "_blank" in balise.group(0).lower()

    # Le libellé reste l'ID : aucun nom de carte n'entre dans le HTML (invariant intact).
    assert re.search(r">\s*OP15-061\s*<", text), "le libellé du lien n'est plus l'ID"


def test_le_lien_par_carte_ne_lie_jamais_la_quantite(site, tmp_path):
    """La quantité n'appartient pas à la carte : `<span class="qty">4</span>` reste hors
    du lien. La puce doit continuer de distinguer quantité et identifiant (SPEC §
    « Registre visuel ») — un 4-of se lit comme la colonne vertébrale du deck.

    Et surtout : le lien reste un `<a href>`. Aucune `<img>`, aucun `src`/`data-src` ne
    doit apparaître, drapeau activé — c'est la frontière exacte de l'amendement.
    """
    paths = render.write_pages(site, tmp_path, base_url=BASE, card_link_base=CARD_LINK)
    for p in paths:
        if p.suffix not in {".html", ".css"}:
            continue
        text = p.read_text(encoding="utf-8")
        assert not re.search(r"""<a\s[^>]*>\s*<span class="qty">""", text), \
            f"la quantité est à l'intérieur du lien dans {p.name}"
        for attr in ("src=", "srcset=", "data-src="):
            assert attr not in text, \
                f"sous-ressource ({attr}) introduite avec le lien par carte : {p.name}"


def test_le_format_courant_dit_de_quel_circuit_il_vient(tmp_path):
    """Quand le papier a été doublé, « Current format » désigne un format joué EN LIGNE
    seulement. La page doit le dire, et dire où en est le papier.

    Sans cette mention, un joueur qui prépare un regional lirait « Current format : OP17 »
    et construirait pour un format qu'aucun tournoi sur table n'a encore joué. Le rôle est
    juste ; c'est la mention qui le rend utilisable.
    """
    from datetime import date

    from sitegen.model import Site, Tournament

    def _t(slug, d, fmt, circuit):
        return Tournament(slug, slug, d, "", "", (), format=fmt, circuit=circuit)

    site = Site(tournaments=(
        _t("2026-07-26-papier", date(2026, 7, 26), "OP16", "paper"),
        _t("2026-08-12-sim", date(2026, 8, 12), "OP16.5", "online"),
        _t("2026-09-01-sim", date(2026, 9, 1), "OP17", "online"),
    ))
    render.write_pages(site, tmp_path, base_url=BASE)
    index = _html(tmp_path, "index.html")

    bloc = re.search(r"<h3>Current format</h3>(.*?)</section>", index, re.S)
    assert bloc, "la section du format courant a disparu de l'index"
    note = re.sub(r"<[^>]+>", " ", bloc.group(1))
    assert "online" in note.lower(), "le circuit du format courant n'est pas annoncé"
    assert "OP16" in note, "l'index n'indique pas où en est le circuit papier"
    assert "26 July 2026" in note, "l'index ne date pas le dernier tournoi papier"

    # Et la page du format porte la même mention : on y arrive aussi en lien direct.
    page = _html(tmp_path, "formats/op17/index.html")
    assert "Current format" in page
    assert "OP16" in re.sub(r"<[^>]+>", " ",
                            re.search(r'class="format-role-label[^"]*"[^>]*>(.*?)</p>',
                                      page, re.S).group(1))


def test_pas_de_mention_de_circuit_quand_le_papier_donne_l_heure(built):
    """La contrepartie : en régime normal, aucune mention parasite.

    Le fixture a un papier OP16 et un seul format d'avance — le décalage voulu. Ajouter la
    mention là aussi la banaliserait jusqu'à ce que plus personne ne la lise.
    """
    out, _ = built
    bloc = re.search(r"<h3>Current format</h3>(.*?)</section>", _html(out, "index.html"), re.S)
    assert bloc
    assert "no paper tournament" not in re.sub(r"<[^>]+>", " ", bloc.group(1)).lower()


# ── Obligations légales du site publié ──────────────────────────────────────────────
# Ces tests ne jugent pas la qualité de la rédaction : ils vérifient qu'aucune des
# obligations ne peut DISPARAÎTRE sans que le portillon s'en aperçoive. Une page légale se
# perd exactement comme ça — un gabarit réécrit, personne ne s'en rend compte pendant un an.

def test_la_page_legale_porte_les_mentions_obligatoires(built):
    """Éditeur, hébergeur identifié en toutes lettres, contact, droit applicable.

    L'identité de l'hébergeur est la partie NON facultative : un éditeur non professionnel
    peut rester pseudonyme (LCEN art. 6 III-2), l'hébergeur jamais.
    """
    out, _ = built
    page = _html(out, "legal/index.html")
    for attendu in ("GitHub, Inc.", "88 Colin P. Kelly", "San Francisco",
                    "hquezser", "French law", "issues"):
        assert attendu in page, f"mention obligatoire absente : {attendu}"


def test_la_page_legale_traite_les_donnees_personnelles(built):
    """Noms de joueurs : finalité, base légale, et surtout procédure de retrait.

    755 noms de joueurs sont publiés. C'est la partie du site qui porte un vrai risque, pas
    les identifiants de cartes — et la seule réponse qui tienne est un droit de retrait
    effectif et facile à trouver.
    """
    out, _ = built
    page = _html(out, "legal/index.html")
    for attendu in ("Legitimate interest", "GDPR", "CNIL", "removed"):
        assert attendu in page, f"volet données personnelles incomplet : {attendu}"
    assert 'id="removal"' in page, "pas d'ancre stable vers la procédure de retrait"
    assert "do not have to justify" in page, \
        "le retrait doit être inconditionnel, sinon il n'est pas un droit"


def test_la_page_legale_decline_toute_affiliation(built):
    out, _ = built
    page = _html(out, "legal/index.html")
    assert "Bandai" in page
    assert "not affiliated" in page.lower()
    for source in ("limitlesstcg.com", "chinoizecupstats.com"):
        assert source in page, f"source non créditée sur la page légale : {source}"


def test_toute_page_mene_a_la_page_legale(built):
    """Une mention légale qu'on ne trouve qu'en devinant l'URL n'informe personne.

    Le lien est dans le pied de page commun, donc sur toutes les pages : le vérifier page par
    page est ce qui empêche une profondeur mal câblée (`rel`) de casser le lien ailleurs que
    sur l'accueil.
    """
    out, paths = built
    for p in paths:
        if p.suffix != ".html":
            continue
        rel = p.relative_to(out)
        text = p.read_text(encoding="utf-8")
        prefixe = "../" * (len(rel.parts) - 1)
        assert f'href="{prefixe}legal/"' in text, f"{rel} ne lie pas la page légale"
        cible = (out / rel.parent / f"{prefixe}legal/index.html").resolve()
        assert cible.is_file(), f"{rel} : le lien légal ne résout pas ({cible})"


def test_le_pied_de_page_annonce_l_absence_de_pistage(built):
    """L'affirmation la plus vérifiable du site, et celle qui rassure le plus vite."""
    out, _ = built
    pied = _html(out, "index.html")
    assert "No cookies" in pied and "no tracking" in pied


def test_la_page_legale_n_introduit_aucune_ressource_externe(built):
    """Le comble serait qu'une page sur la vie privée fasse fuiter l'IP du lecteur.

    Les liens sortants sont permis (le visiteur choisit de cliquer) mais doivent porter
    `noreferrer` ; une sous-ressource, elle, est chargée toute seule et resterait interdite.
    """
    out, _ = built
    page = _html(out, "legal/index.html")
    for attr in ("src=", "srcset=", "@import", "<script"):
        assert attr not in page, f"sous-ressource sur la page légale : {attr}"
    for lien in re.findall(r'<a\s[^>]*href="https?://[^"]+"[^>]*>', page):
        assert "noreferrer" in lien, f"lien externe sans noreferrer : {lien}"


def test_la_date_de_mise_a_jour_legale_ne_suit_pas_le_corpus(built):
    """Elle doit changer avec le TEXTE, jamais avec le dernier tournoi scrapé.

    Câblée sur `site.reference_date`, elle avançait à chaque collecte : le lecteur aurait lu
    « mis à jour le 1er septembre » sur des mentions inchangées depuis des semaines. Une date
    de mise à jour qui ment vaut moins que pas de date.
    """
    out, _ = built
    page = _html(out, "legal/index.html")
    assert render.LEGAL_UPDATED in page
    # Le fixture a un tournoi de juillet 2026 : la date légale ne doit pas s'y accrocher.
    assert "Last updated" in page


def test_un_groupe_identique_ne_se_repete_pas(built):
    """La convergence et le groupe identique disaient la même chose deux fois.

    « 2 identical lists » et « 2 players run this list » sur la même ligne : la seconde est
    la bonne formulation — ce qui compte n'est pas que les listes coïncident, c'est que des
    joueurs DIFFÉRENTS y soient arrivés. On ne le dit qu'une fois.
    """
    out, _ = built
    page = _html(out, "leaders/op15-058/index.html")
    for bloc in re.findall(r'<summary class="deck-summary">.*?</summary>', page, re.S):
        if "run this list" in bloc:
            assert "identical" not in bloc, "la même information est annoncée deux fois"
    # La mention de convergence, elle, doit rester : c'est le signal fort.
    assert "run this list" in page


# ── Atteindre un tournoi ────────────────────────────────────────────────────────────────
# Défaut signalé en usage réel : le segment /tournaments/ portait 134 pages filles et AUCUN
# index (404 en y montant), la nav « Tournaments » pointait sur l'accueil où les tournois
# sont la quatrième section, et une page de format ne listait que des archétypes. Depuis un
# format, on ne pouvait plus redescendre sur un tournoi — donc plus accéder à son pack.

def test_l_index_des_tournois_existe_et_est_complet(built):
    """Un segment d'URL qui porte des pages filles doit avoir un index. Sans lui, remonter
    l'URL donne un 404, et il n'existe aucune vue d'ensemble des tournois."""
    out, _ = built
    page = _html(out, "tournaments/index.html")
    for slug in ("2026-07-04-regional-bielefeld", "2026-04-01-regional-ancien",
                 "2026-04-15-treasure-cup-noyau", "2026-06-15-chinoizecup-avance"):
        assert f"tournaments/{slug}/" in page, f"{slug} absent de l'index des tournois"
    # Un tournoi de format indéterminé doit y figurer aussi, sous un libellé explicite
    # plutôt que dans un groupe muet.
    assert "Unclassified" in page or "chinoizecup-avance" in page


def test_la_nav_mene_a_l_index_des_tournois(built):
    """Depuis N'IMPORTE QUELLE page. Le lien pointait sur l'accueil : le titre disait
    « Recent tournaments » mais les deux premières sections étaient Formats et Meta."""
    out, paths = built
    for p in paths:
        if p.suffix != ".html":
            continue
        rel = p.relative_to(out)
        prefixe = "../" * (len(rel.parts) - 1)
        texte = p.read_text(encoding="utf-8")
        assert f'href="{prefixe}tournaments/"' in texte, \
            f"{rel} : la nav ne mène pas à l'index des tournois"
        assert (out / rel.parent / f"{prefixe}tournaments/index.html").resolve().is_file()


def test_une_page_de_format_redescend_sur_ses_tournois(built):
    """Le maillon manquant du chemin réellement emprunté : accueil -> format -> ??? ."""
    out, _ = built
    page = _html(out, "formats/op16/index.html")
    assert re.search(r'href="\.\./\.\./tournaments/[^"]+/"', page), \
        "aucun lien vers un tournoi sur la page d'un format"


def test_le_geste_de_selection_est_annonce(built):
    """`user-select: all` rendait déjà un clic suffisant pour tout sélectionner — mais rien
    ne le disait, donc personne ne l'essayait. La capacité existait, l'affordance manquait.

    Signalé en usage réel comme « il faut un bouton copier ». Un vrai bouton exigerait du
    JavaScript, que le site s'interdit et dont sa page légale garantit publiquement
    l'absence. Annoncer le geste coûte une phrase et tient la garantie.
    """
    out, _ = built
    css = _html(out, "style.css").replace(" ", "").replace("\n", "")
    assert "user-select:all" in css, "le clic ne sélectionne plus tout"
    assert "cursor:cell" in css, "rien n'indique visuellement que le bloc est sélectionnable"

    page = _html(out, "tournaments/2026-07-04-regional-bielefeld/index.html")
    assert "click it to select all" in page, \
        "la page ne dit pas comment copier la decklist"
    # L'accueil ne porte pas de bloc d'import : on interroge une page qui en a un.
    assert "Click the command to select all" in _html(out, "meta/index.html"), \
        "la page ne dit pas comment copier la commande d'import"


def test_aucun_script_nulle_part(built):
    """L'invariant que le bouton copier aurait rompu, et que la page légale publie.

    `check_dist` le vérifie déjà sur le build complet ; ici on le verrouille au niveau du
    rendu, pour qu'une régression échoue au plus près de sa cause.
    """
    out, paths = built
    for p in paths:
        if p.suffix not in {".html", ".css"}:
            continue
        texte = p.read_text(encoding="utf-8").lower()
        for motif in ("<script", "javascript:", "onclick=", "onload=", "navigator.clipboard"):
            assert motif not in texte, f"{p.relative_to(out)} : {motif}"


def test_l_extrait_de_l_accueil_mene_a_l_index_complet(built):
    """L'accueil ne montre que les 20 tournois les plus récents. Sans lien vers l'index, le
    lecteur croit que c'est tout ce qu'il y a — c'est exactement la confusion signalée.
    """
    out, _ = built
    page = _html(out, "index.html")
    assert re.search(r'class="see-all" href="tournaments/"', page), \
        "l'extrait de l'accueil ne mène pas à l'index complet des tournois"


def test_le_titre_de_l_accueil_ne_promet_pas_une_section_absente(built):
    """Le `h1` annonçait « Recent tournaments » alors que la première section est Formats et
    que les tournois arrivent en quatrième position. Un titre doit décrire sa page.
    """
    out, _ = built
    page = _html(out, "index.html")
    h1 = re.search(r"<h1>(.*?)</h1>", page, re.S).group(1).strip()
    assert "recent tournaments" not in h1.lower(), \
        f"le titre « {h1} » promet une liste de tournois qui n'ouvre pas la page"


def test_plur_refuse_ce_qui_n_est_pas_un_nombre():
    """« 1 more lists » venait d'un gabarit passant la LISTE au lieu de sa longueur, et le
    filtre pluralisait en silence. Un gabarit fautif doit casser le build.
    """
    assert render.plur(1, "list") == "list"
    assert render.plur(2, "list") == "lists"
    for mauvais in ([1], (1, 2), "1", None, True):
        with pytest.raises(TypeError):
            render.plur(mauvais, "list")


def test_une_variable_css_inline_est_portee_par_l_element_qui_l_utilise(built):
    """`var()` ne remonte pas des enfants vers le parent.

    Défaut réel : la barre de part a été déplacée sur `.field-row::before` sans déplacer le
    `style="--share: N"`, resté sur un `<span>` enfant. La largeur devenait invalide et
    TOUTES les barres tombaient sur leur `min-width` de 2 px — soit exactement l'apparence
    du défaut qu'on corrigeait, ce qui rendait la panne invisible à la relecture.

    Le contrôle : pour chaque variable posée en style inline, la feuille doit contenir une
    règle qui l'utilise ET qui vise la classe de l'élément porteur.
    """
    out, paths = built
    css = _html(out, "style.css")
    verifiees = 0
    for p in paths:
        if p.suffix != ".html":
            continue
        texte = p.read_text(encoding="utf-8")
        for classes, var in re.findall(
                r'<\w+[^>]*class="([^"]*)"[^>]*style="\s*(--[\w-]+)\s*:', texte):
            verifiees += 1
            regles = [b for sel, b in re.findall(r"([^{}]+)\{([^}]*)\}", css)
                      if f"var({var}" in b]
            assert regles, f"{p.relative_to(out)} : {var} posé mais utilisé nulle part"
            selecteurs = " ".join(sel for sel, b in re.findall(r"([^{}]+)\{([^}]*)\}", css)
                                  if f"var({var}" in b)
            assert any(f".{c}" in selecteurs for c in classes.split()), (
                f"{p.relative_to(out)} : {var} est posé sur « {classes} » mais la règle qui "
                f"l'utilise vise « {selecteurs.strip()} » — var() ne remonte pas")
    assert verifiees, "aucune variable inline trouvée, le motif de détection a dû changer"
