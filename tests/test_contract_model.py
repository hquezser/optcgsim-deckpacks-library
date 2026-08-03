"""Contrat du modèle figé — doit passer avant tout développement de lot."""

from __future__ import annotations

from datetime import date

from sitegen.model import Deck, Site, Tournament, slugify


def _deck(name="Purple Enel — Luka Forjan (1st)", archetype="Purple Enel",
          player="Luka Forjan", placement=1, leader="OP15-058"):
    return Deck(raw_name=name, archetype=archetype, player=player, placement=placement,
                leader_id=leader, cards=(("OP15-061", 4), ("OP15-067", 3)),
                text=f"1x{leader}\n4xOP15-061\n3xOP15-067")


def test_slugify_cas_reels():
    assert slugify("Purple Enel") == "purple-enel"
    assert slugify("Red/Black Koby") == "red-black-koby"
    assert slugify("Marc@@@1") == "marc-1"
    assert slugify("  Déjà--vu  ") == "d-j-vu"


def test_deck_slug_parse_et_non_parse():
    assert _deck().slug == "01-purple-enel-luka-forjan"
    orphan = _deck(name="Nom bizarre", archetype="", player="", placement=None)
    assert orphan.slug == "xx-nom-bizarre"
    assert not orphan.parsed
    assert _deck().parsed


def test_deck_total_exclut_le_leader():
    assert _deck().total_cards == 7


def test_tri_tournois_recent_dabord_puis_sans_date():
    a = Tournament("2026-04-01-a", "A", date(2026, 4, 1), "", "", ())
    b = Tournament("2026-07-04-b", "B", date(2026, 7, 4), "", "", ())
    c = Tournament("sans-date", "C", None, "", "", ())
    site = Site(tournaments=(a, c, b))
    assert [t.slug for t in site.sorted_tournaments] == ["2026-07-04-b", "2026-04-01-a",
                                                         "sans-date"]


def test_reference_date_est_le_tournoi_le_plus_recent():
    a = Tournament("2026-04-01-a", "A", date(2026, 4, 1), "", "", ())
    b = Tournament("2026-07-04-b", "B", date(2026, 7, 4), "", "", ())
    assert Site(tournaments=(a, b)).reference_date == date(2026, 7, 4)
    assert Site(tournaments=()).reference_date is None


def test_leaders_regroupe_et_exclut_les_non_parses():
    enel_recent = _deck(player="Récent", placement=1)
    enel_vieux = _deck(player="Vieux", placement=2)
    orphan = _deck(name="Bizarre", archetype="", player="", placement=None)
    recent = Tournament("2026-07-04-r", "R", date(2026, 7, 4), "", "",
                        (enel_recent, orphan))
    vieux = Tournament("2026-04-01-v", "V", date(2026, 4, 1), "", "", (enel_vieux,))
    groups = Site(tournaments=(vieux, recent)).leaders()

    assert list(groups) == ["purple-enel"]
    # Provenance conservée, et le plus récent en premier.
    assert [(t.slug, d.player) for t, d in groups["purple-enel"]] == [
        ("2026-07-04-r", "Récent"), ("2026-04-01-v", "Vieux")]


def _t(slug, d, fmt, decks=()):
    return Tournament(slug, slug, d, "", "", decks, format=fmt)


def test_format_slug_normalise_le_point():
    assert _t("x", None, "OP14.5").format_slug == "op14-5"
    assert _t("x", None, "OP16").format_slug == "op16"
    assert _t("x", None, "").format_slug == ""


def test_formats_regroupe_et_exclut_les_inconnus():
    a = _t("2026-07-04-a", date(2026, 7, 4), "OP16")
    b = _t("2026-04-01-b", date(2026, 4, 1), "OP15")
    c = _t("2026-05-01-c", date(2026, 5, 1), "")      # format indéterminé -> exclu
    site = Site(tournaments=(a, b, c))
    fmts = site.formats()
    assert list(fmts) == ["op15", "op16"]             # clés triées
    assert [t.slug for t in fmts["op16"]] == ["2026-07-04-a"]
    assert "2026-05-01-c" not in {t.slug for v in fmts.values() for t in v}


def test_current_format_suit_le_tournoi_le_plus_recent():
    a = _t("2026-07-04-a", date(2026, 7, 4), "OP16")
    b = _t("2026-04-01-b", date(2026, 4, 1), "OP15")
    assert Site(tournaments=(b, a)).current_format == "op16"
    # Un tournoi plus récent SANS format ne doit pas masquer le format courant.
    c = _t("2026-08-01-c", date(2026, 8, 1), "")
    assert Site(tournaments=(b, a, c)).current_format == "op16"
    assert Site(tournaments=()).current_format == ""


def test_format_label_restitue_la_casse_et_le_point():
    t = _t("x", date(2026, 3, 21), "OP14.5")
    assert Site(tournaments=(t,)).format_label("op14-5") == "OP14.5"


def test_leaders_filtre_par_format():
    """C'est le paramètre qui rend un cœur commun honnête : sans lui on moyenne deux métas."""
    d16 = _deck(player="Récent")
    d15 = _deck(player="Ancien", placement=2)
    a = _t("2026-07-04-a", date(2026, 7, 4), "OP16", (d16,))
    b = _t("2026-04-01-b", date(2026, 4, 1), "OP15", (d15,))
    site = Site(tournaments=(a, b))

    assert len(site.leaders()["purple-enel"]) == 2                 # tout le corpus
    assert [d.player for _, d in site.leaders("op16")["purple-enel"]] == ["Récent"]
    assert [d.player for _, d in site.leaders("op15")["purple-enel"]] == ["Ancien"]
    assert site.leaders("op99") == {}


def test_archetype_label_retrouve_le_libelle():
    t = Tournament("2026-07-04-r", "R", date(2026, 7, 4), "", "", (_deck(),))
    assert Site(tournaments=(t,)).archetype_label("purple-enel") == "Purple Enel"
