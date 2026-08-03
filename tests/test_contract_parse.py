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
    # ChinoizeCupStats numérote sans suffixe ordinal : sans cette tolérance, tous ses
    # tournois étaient illisibles (0 deck parsé sur 4) et donc absents des vues agrégées.
    ("Roronoa Zoro & Sanji — Krullzor (1)", ("Roronoa Zoro & Sanji", "Krullzor", 1)),
    ("Monkey.D.Luffy — igordiasr (2)", ("Monkey.D.Luffy", "igordiasr", 2)),
    ("Dracule Mihawk — mirkosp95 (3)", ("Dracule Mihawk", "mirkosp95", 3)),
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
    assert len(site.tournaments) == 4
    slugs = {t.slug for t in site.tournaments}
    assert slugs == {"2026-07-04-regional-bielefeld", "2026-04-01-regional-ancien",
                     "2026-04-15-treasure-cup-noyau", "2026-06-15-chinoizecup-avance"}


def test_load_site_derive_la_date_du_slug(site):
    biel = next(t for t in site.tournaments if t.slug.endswith("bielefeld"))
    assert biel.date == date(2026, 7, 4)
    assert biel.name == "OP16 4th July 2026 - Regional Bielefeld"
    assert biel.author == "limitlesstcg-scraper"


def test_parse_format_depuis_le_nom_de_pack():
    """Source primaire : le préfixe du nom, qui porte la casse et le point."""
    assert parse.parse_format("OP14.5 21st March 2026 - Regional Melbourne", ()) == "OP14.5"
    assert parse.parse_format("OP16 4th July 2026 - Regional Bielefeld", ()) == "OP16"


def test_parse_format_repli_sur_les_tags():
    """Source secondaire, normalisée en majuscules."""
    assert parse.parse_format("CHINOIZECUP #200", ("meta", "op16", "2026")) == "OP16"
    assert parse.parse_format("Tournoi sans préfixe", ("op14.5",)) == "OP14.5"


def test_parse_format_inconnu_plutot_que_devine():
    """`op` nu (cas réel de ChinoizeCupStats) ne désigne aucun format : ne rien inventer."""
    assert parse.parse_format("CHINOIZECUP #200", ("meta", "online", "op", "2026")) == ""
    assert parse.parse_format("", ()) == ""
    assert parse.parse_format("Nom quelconque", ("meta", "Europe")) == ""


def test_load_site_renseigne_le_format(site):
    attendu = {
        "2026-07-04-regional-bielefeld": "OP16",
        "2026-04-01-regional-ancien": "OP15",
        "2026-04-15-treasure-cup-noyau": "OP15",
        # Ni préfixe de nom ni tag de format : déduit du pool (ST31 -> starter OP16.5).
        "2026-06-15-chinoizecup-avance": "OP16.5",
    }
    assert {t.slug: t.format for t in site.tournaments} == attendu


def test_format_deduit_du_pool_en_dernier_recours(site):
    """Le décalage réel du simulateur : un tournoi de juin en avance sur les OP16 de juillet.

    Troisième source, après le préfixe de nom et les tags. C'est ce qui permet de classer
    les tournois ChinoizeCupStats, dont le seul tag est « op » — lequel ne désigne aucun
    format et ne doit surtout pas être interprété comme tel.
    """
    ccs = next(t for t in site.tournaments if "chinoizecup" in t.slug)
    assert ccs.format == "OP16.5"
    assert ccs.format_slug == "op16-5"
    # La déduction ne doit PAS écraser une étiquette explicite, même en désaccord.
    melbourne_like = parse.parse_format("OP14.5 21st March 2026 - X", ("op16",))
    assert melbourne_like == "OP14.5"


def test_deduction_ne_prime_jamais_sur_une_etiquette(site):
    """Les tournois étiquetés gardent leur étiquette : la déduction est une borne inférieure."""
    biel = next(t for t in site.tournaments if t.slug.endswith("bielefeld"))
    assert biel.format == "OP16"


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
    # Ordre SOURCE, volontairement non trié dans la fixture : le tri par quantité est une
    # affaire d'affichage (lot B), pas de parsing — et les packs doivent rester verbatim.
    assert enel.cards == (("OP10-067", 2), ("OP15-061", 4), ("OP12-071", 3),
                          ("OP15-067", 4))
    assert enel.tags == ("meta", "2026", "Europe", "op16")
    # `text` est conservé verbatim : c'est lui qu'on réexporte dans les packs dérivés.
    assert enel.text.startswith("1xOP15-058\n2xOP10-067")


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
