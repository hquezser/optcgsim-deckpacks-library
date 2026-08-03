"""Contrat du LOT A — sitegen/parse.py. FIGÉ : le worker A implémente, ne modifie pas.

Interface attendue :
    parse.load_site(packs_dir: Path) -> Site
    parse.parse_deck_name(name: str) -> tuple[str, str, int | None]   # archétype, joueur, place
    parse.parse_text(text: str) -> tuple[str, tuple[tuple[str, int], ...]]  # leader, cartes
"""

from __future__ import annotations

from datetime import date

import pytest

from sitegen import parse


# --- parse_deck_name -----------------------------------------------------------------

@pytest.mark.parametrize("name,attendu", [
    ("Purple Enel — Luka Forjan (1st)", ("Purple Enel", "Luka Forjan", 1)),
    ("Red/Black Koby — Marc@@@1 (2nd)", ("Red/Black Koby", "Marc@@@1", 2)),
    ("Green/Blue Luffy — Sammy Wang (3rd)", ("Green/Blue Luffy", "Sammy Wang", 3)),
    ("Red/Green Luffy & Ace — Davide Ferrari (4th)",
     ("Red/Green Luffy & Ace", "Davide Ferrari", 4)),
    ("Purple Enel — Georgios Karapiperis (11th)",
     ("Purple Enel", "Georgios Karapiperis", 11)),
])
def test_parse_noms_conformes(name, attendu):
    assert parse.parse_deck_name(name) == attendu


@pytest.mark.parametrize("name", [
    "Nom sans structure reconnaissable",
    "Purple Enel - Luka Forjan (1st)",      # tiret court, pas cadratin -> non conforme
    "Purple Enel — Luka Forjan",            # placement absent
    "Purple Enel — Luka Forjan (1er)",      # suffixe non anglais
    "",
])
def test_parse_noms_non_conformes_degradent_proprement(name):
    """Jamais d'exception, jamais de valeur inventée."""
    assert parse.parse_deck_name(name) == ("", "", None)


# --- parse_text ----------------------------------------------------------------------

def test_parse_text_leader_puis_cartes_dans_lordre():
    leader, cards = parse.parse_text("1xOP15-058\n4xOP15-061\n3xOP12-071")
    assert leader == "OP15-058"
    assert cards == (("OP15-061", 4), ("OP12-071", 3))


def test_parse_text_tolere_lignes_vides_et_espaces():
    leader, cards = parse.parse_text("1xOP15-058\n\n  4xOP15-061  \n")
    assert leader == "OP15-058"
    assert cards == (("OP15-061", 4),)


# --- load_site -----------------------------------------------------------------------

def test_load_site_lit_le_corpus_fixture(site):
    assert len(site.tournaments) == 2
    slugs = {t.slug for t in site.tournaments}
    assert slugs == {"2026-07-04-regional-bielefeld", "2026-04-01-regional-ancien"}


def test_load_site_derive_la_date_du_slug(site):
    biel = next(t for t in site.tournaments if t.slug.endswith("bielefeld"))
    assert biel.date == date(2026, 7, 4)
    assert biel.name == "OP16 4th July 2026 - Regional Bielefeld"
    assert biel.author == "limitlesstcg-scraper"


def test_load_site_conserve_le_deck_non_parsable(site):
    biel = next(t for t in site.tournaments if t.slug.endswith("bielefeld"))
    assert len(biel.decks) == 3
    assert len(biel.parsed_decks) == 2

    orphan = next(d for d in biel.decks if not d.parsed)
    assert orphan.raw_name == "Nom sans structure reconnaissable"   # verbatim
    assert orphan.leader_id == "OP11-041"                            # leader quand même lu
    assert orphan.archetype == "" and orphan.player == ""


def test_load_site_remplit_deck_et_tags(site):
    biel = next(t for t in site.tournaments if t.slug.endswith("bielefeld"))
    enel = next(d for d in biel.decks if d.placement == 1)
    assert enel.archetype == "Purple Enel"
    assert enel.player == "Luka Forjan"
    assert enel.leader_id == "OP15-058"
    assert enel.cards == (("OP15-061", 4), ("OP15-067", 4), ("OP12-071", 3),
                          ("OP10-067", 2))
    assert enel.tags == ("meta", "2026", "Europe", "op16")
    # `text` est conservé verbatim : c'est lui qu'on réexporte dans les packs dérivés.
    assert enel.text.startswith("1xOP15-058\n4xOP15-061")


def test_load_site_est_deterministe(packs_dir):
    a, b = parse.load_site(packs_dir), parse.load_site(packs_dir)
    assert [t.slug for t in a.sorted_tournaments] == [t.slug for t in b.sorted_tournaments]
    assert a.leaders().keys() == b.leaders().keys()


def test_load_site_echoue_sur_corpus_illisible(tmp_path):
    bad = tmp_path / "casse"
    bad.mkdir()
    (bad / "deckpack.json").write_text("{ ceci n'est pas du json")
    with pytest.raises((OSError, ValueError)):
        parse.load_site(tmp_path)
