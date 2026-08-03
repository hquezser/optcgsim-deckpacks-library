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


def test_page_tournoi_montre_placements_joueurs_et_ids(built):
    out, _ = built
    page = _html(out, "tournois/2026-07-04-regional-bielefeld/index.html")
    assert "Luka Forjan" in page and "Purple Enel" in page
    assert "OP15-058" in page and "OP15-061" in page
    # le deck non parsable reste affiché, sous son nom brut
    assert "Nom sans structure reconnaissable" in page


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


def test_aucune_requete_reseau_sortante(built):
    """Invariant AGENTS.md : les pages produites ne parlent à personne."""
    out, paths = built
    for p in paths:
        if p.suffix not in {".html", ".css"}:
            continue
        text = p.read_text(encoding="utf-8")
        for url in re.findall(r"https?://[^\s\"'<>)]+", text):
            assert url.startswith(BASE), f"URL externe dans {p.name} : {url}"
        for motif in ("<script", "@import", "cdn.", "fonts.google", "googletagmanager"):
            assert motif not in text.lower(), f"{motif} interdit dans {p.name}"


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
