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
        "meta/index.html",
        "tournois/2026-07-04-regional-bielefeld/index.html",
        "tournois/2026-04-01-regional-ancien/index.html",
        "leaders/purple-enel/index.html",
        "leaders/red-black-koby/index.html",
        "leaders/green-blue-luffy/index.html",
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
    assert f"studio decks import-pack {BASE}/leaders/purple-enel/deckpack.json" in \
        _html(out, "leaders/purple-enel/index.html")
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
    bloc = page[page.find("OP15-058"):]
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


def test_page_leader_cite_la_provenance(built):
    """Toute la valeur de preuve d'une page leader est dans la provenance des listes."""
    out, _ = built
    page = _html(out, "leaders/purple-enel/index.html")
    assert "Luka Forjan" in page and "Vieux Joueur" in page
    assert "Bielefeld" in page and "Ancien" in page


def test_index_liste_tournois_et_archetypes(built):
    out, _ = built
    page = _html(out, "index.html")
    assert "Bielefeld" in page and "Ancien" in page
    assert "purple-enel" in page
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
