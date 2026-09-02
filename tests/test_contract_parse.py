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


def test_parse_format_lit_la_declaration_entre_crochets():
    """La forme de ChinoizeCupStats — jetée jusqu'au 2026-09-03.

    12 tournois du corpus déclarent `[OP17] …` et on redéduisait leur format du pool. Les 12
    déductions tombaient juste, donc rien ne le signalait ; mais c'est la source EN LIGNE qui
    voit les nouveaux formats en premier, et une déclaration bat toujours une déduction.
    """
    assert parse.parse_format("[OP17] ChinoizeCup #104 Tuesday", ()) == "OP17"
    assert parse.parse_format("[OP14] Christmas ChinoizeCup", ()) == "OP14"
    assert parse.parse_format("[op16.5] ChinoizeCup #96", ()) == "op16.5"


def test_la_declaration_reste_ancree_en_tete():
    """Sans ancrage, un `OP17` n'importe où dans le nom étiquetterait le tournoi — un pseudo
    de joueur, un identifiant de carte. On ne lit une déclaration qu'à la place où les deux
    sources en mettent une.
    """
    assert parse.parse_format("ChinoizeCup #97 - won by OP17fan", ()) == ""
    assert parse.parse_format("Treasure Cup (format OP16)", ()) == ""


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


def test_pas_d_avertissement_si_tout_est_classe(site):
    """Un avertissement qui se déclenche toujours n'avertit plus de rien.

    Sur le corpus élargi il listait 26 sets non datés à chaque build alors que les 114
    tournois étaient correctement classés. Un set non daté n'est actionnable que s'il
    empêche effectivement un classement.
    """
    assert all(t.format for t in site.tournaments), "la fixture doit être entièrement classée"
    non_dates = [w for w in site.warnings if "non daté" in w.message.lower()]
    assert non_dates == [], f"avertissement inutile : {[w.message for w in non_dates]}"


def test_parse_circuit_deux_signaux_independants():
    """« online » ou « paper ». Deux signaux concordants dans le corpus réel :
    l'auteur du pack et le tag de circuit. Défaut prudent : « paper »."""
    assert parse.parse_circuit("chinoizecup-scraper", ("meta", "online", "op")) == "online"
    assert parse.parse_circuit("limitlesstcg-scraper", ("meta", "Europe", "op16")) == "paper"
    # Chaque signal suffit seul.
    assert parse.parse_circuit("chinoizecup-scraper", ()) == "online"
    assert parse.parse_circuit("", ("meta", "online")) == "online"
    assert parse.parse_circuit("", ()) == "paper"


def test_load_site_renseigne_le_circuit(site):
    ccs = next(t for t in site.tournaments if "chinoizecup" in t.slug)
    biel = next(t for t in site.tournaments if t.slug.endswith("bielefeld"))
    assert ccs.circuit == "online" and ccs.is_online
    assert biel.circuit == "paper" and not biel.is_online


def test_courant_reste_le_papier_sur_la_fixture(site):
    """La fixture ChinoizeCup est en OP16.5 : elle doit être « à venir », pas « courant »."""
    assert site.current_format == "op16"
    assert site.upcoming_formats == ("op16-5",)


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


def _ecrire_pack(racine, slug, nom, textes, tags=("meta", "online")):
    import json
    d = racine / slug
    d.mkdir(parents=True)
    (d / "deckpack.json").write_text(json.dumps({
        "schema_version": 1,
        "name": nom,
        "author": "chinoizecup-scraper",
        "decks": [{"name": f"A — J{i} ({i+1})", "tags": list(tags), "text": t}
                  for i, t in enumerate(textes)],
    }), encoding="utf-8")


def test_un_set_posterieur_a_l_horizon_laisse_le_tournoi_non_classe(tmp_path):
    """Le comportement qui protège un format réel d'être pollué par le suivant.

    Avant : un tournoi muet jouant un set inconnu se voyait déduire le format de son booster
    le plus récent — un OP17.5 naissant se fondait donc en silence dans OP17, et le « core »
    d'OP17 décrivait des decks qui n'ont jamais existé. La déduction était fausse ET
    invisible.

    Maintenant : non classé, et signalé. Le tournoi reste consultable, il sort seulement des
    vues par format le temps qu'une ligne soit ajoutée au calendrier.
    """
    _ecrire_pack(tmp_path, "2026-11-02-chinoizecup-200",
                 "ChinoizeCup #200 Monday", ["1xOP17-001\n4xST37-004\n4xOP17-020"])
    site = parse.load_site(tmp_path)
    t = site.tournaments[0]

    assert t.format == "", "le tournoi a été classé alors que son pool est indatable"
    assert len(t.decks) == 1, "le tournoi doit rester lisible, seulement pas classé"

    corpus = [w for w in site.warnings if w.scope == "corpus"]
    assert corpus, "aucun avertissement : un nouveau set serait passé inaperçu"
    msg = corpus[0].message
    assert "ST37" in msg, "l'avertissement ne nomme pas le set en cause"
    assert "OP17" not in msg.split("horizon")[0], "il ne doit surtout pas proposer un format"


def test_une_declaration_explicite_prime_sur_un_set_inconnu(tmp_path):
    """La contrepartie : un set neuf ne doit pas déclasser un tournoi qui, lui, a déclaré.

    La déclaration a déjà tranché la question que le calendrier ne sait pas trancher. Faire
    l'inverse ferait disparaître des vues par format les tournois les mieux renseignés du
    corpus, exactement quand un nouveau format démarre.
    """
    _ecrire_pack(tmp_path, "2026-11-03-chinoizecup-201",
                 "[OP17.5] ChinoizeCup #201 Tuesday", ["1xOP17-001\n4xST37-004"])
    site = parse.load_site(tmp_path)

    assert site.tournaments[0].format == "OP17.5"
    assert not [w for w in site.warnings if w.scope == "corpus"], \
        "un tournoi déclaré ne doit pas déclencher l'alerte de nouveau set"


def test_pas_d_alerte_permanente_sur_les_sets_anciens(tmp_path):
    """L'avertissement doit rester silencieux en régime normal, sinon il ne veut plus rien
    dire. La version précédente listait 26 sets anciens à CHAQUE build alors que les 114
    tournois du corpus étaient tous correctement classés.
    """
    _ecrire_pack(tmp_path, "2026-07-16-chinoizecup-90",
                 "ChinoizeCup #90 Wednesday", ["1xOP15-058\n4xEB03-012\n4xST31-004"])
    site = parse.load_site(tmp_path)

    assert site.tournaments[0].format == "OP16.5", "ST31 doit toujours classer en OP16.5"
    assert not [w for w in site.warnings if w.scope == "corpus"]


def test_un_retrait_ecarte_le_deck_de_toute_la_publication(tmp_path, monkeypatch):
    """La demande de retrait doit être honorée au point qui décide de ce qui est PUBLIÉ.

    Le scraping tourne tous les jours et réécrit les packs : honorer le retrait dans les
    données seules le ferait annuler à la collecte suivante. Un retrait que la prochaine
    exécution défait n'est pas un retrait — c'est ce qui transformerait la page légale en
    promesse fausse.
    """
    _ecrire_pack(tmp_path, "2026-07-04-regional-x", "OP16 4th July 2026 - Regional X",
                 ["1xOP15-058\n4xOP15-061", "1xOP15-058\n4xOP16-042"])
    liste = tmp_path / "removals.txt"
    liste.write_text("# commentaire ignoré\n\n  J0  \n", encoding="utf-8")
    monkeypatch.setattr(parse, "REMOVALS_FILE", liste)

    site = parse.load_site(tmp_path)
    joueurs = [d.player for t in site.tournaments for d in t.decks]

    assert "J0" not in joueurs, "le deck retiré est toujours publié"
    assert "J1" in joueurs, "le retrait a emporté un deck qui n'était pas demandé"
    assert any("retraits RGPD" in w.message for w in site.warnings), \
        "un retrait doit être tracé dans le rapport de build"


def test_le_retrait_est_insensible_a_la_casse_et_aux_espaces(tmp_path, monkeypatch):
    """Une demande arrive écrite à la main : « j0 », « J0 » ou « J0 » entouré d'espaces
    doivent tous fonctionner. Un droit qui échoue sur une majuscule n'est pas exerçable.
    """
    _ecrire_pack(tmp_path, "2026-07-04-regional-x", "OP16 4th July 2026 - Regional X",
                 ["1xOP15-058\n4xOP15-061"])
    liste = tmp_path / "removals.txt"
    liste.write_text("  j0\n", encoding="utf-8")
    monkeypatch.setattr(parse, "REMOVALS_FILE", liste)

    site = parse.load_site(tmp_path)
    assert not [d for t in site.tournaments for d in t.decks]


def test_sans_fichier_de_retrait_rien_ne_change(tmp_path, monkeypatch):
    """Le chemin par défaut ne doit rien coûter : fichier absent -> corpus intact, et
    surtout aucun avertissement (un avertissement permanent n'avertit de rien).
    """
    _ecrire_pack(tmp_path, "2026-07-04-regional-x", "OP16 4th July 2026 - Regional X",
                 ["1xOP15-058\n4xOP15-061"])
    monkeypatch.setattr(parse, "REMOVALS_FILE", tmp_path / "absent.txt")

    site = parse.load_site(tmp_path)
    assert len(site.tournaments[0].decks) == 1
    assert not [w for w in site.warnings if "retrait" in w.message]
