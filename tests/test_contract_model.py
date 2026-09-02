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

    assert list(groups) == ["op15-058"]
    # Provenance conservée, et le plus récent en premier.
    assert [(t.slug, d.player) for t, d in groups["op15-058"]] == [
        ("2026-07-04-r", "Récent"), ("2026-04-01-v", "Vieux")]


def _t(slug, d, fmt, decks=(), circuit="paper"):
    return Tournament(slug, slug, d, "", "", decks, format=fmt, circuit=circuit)


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


def test_deux_metas_a_venir_sont_differenciees():
    """Le simulateur peut être en avance de PLUSIEURS formats sur le papier.

    Courant = dernier format du circuit PAPIER (ce que la majorité joue). À venir = tous les
    formats postérieurs présents dans le corpus, du plus proche au plus lointain — ce sont
    des rôles, les formats gardent leurs codes réels.
    """
    papier = _t("2026-07-26-papier", date(2026, 7, 26), "OP16")
    sim1 = _t("2026-07-15-sim", date(2026, 7, 15), "OP16.5", circuit="online")
    sim2 = _t("2026-07-20-sim2", date(2026, 7, 20), "OP17", circuit="online")
    vieux = _t("2026-05-01-vieux", date(2026, 5, 1), "OP15")
    site = Site(tournaments=(papier, sim1, sim2, vieux))

    assert site.current_format == "op16"
    assert site.upcoming_formats == ("op16-5", "op17")   # du plus proche au plus lointain
    assert site.past_formats == ("op15",)


def test_courant_ignore_les_tournois_en_ligne_plus_recents():
    """Le piège que la définition « tournoi le plus récent » faisait tomber.

    Un tournoi sim postérieur ET en avance ne doit pas devenir le format courant : il vide
    « à venir » et fait passer pour dépassé le format que presque tout le monde joue.
    """
    papier = _t("2026-07-01-papier", date(2026, 7, 1), "OP16")
    sim = _t("2026-07-28-sim", date(2026, 7, 28), "OP16.5", circuit="online")
    site = Site(tournaments=(papier, sim))
    assert site.current_format == "op16"
    assert site.upcoming_formats == ("op16-5",)


def test_repli_si_le_corpus_n_a_aucun_tournoi_papier():
    sim = _t("2026-07-28-sim", date(2026, 7, 28), "OP16.5", circuit="online")
    assert Site(tournaments=(sim,)).current_format == "op16-5"


def test_roles_vides_quand_il_n_y_a_qu_un_format():
    t = _t("2026-07-26-x", date(2026, 7, 26), "OP16")
    site = Site(tournaments=(t,))
    assert site.current_format == "op16"
    assert site.upcoming_formats == () and site.past_formats == ()


def test_ordre_des_roles_est_numerique():
    """OP9 ne doit pas passer pour postérieur à OP16 par comparaison textuelle."""
    courant = _t("2026-07-26-a", date(2026, 7, 26), "OP16")
    ancien = _t("2026-01-01-b", date(2026, 1, 1), "OP9")
    site = Site(tournaments=(courant, ancien))
    assert site.upcoming_formats == ()
    assert site.past_formats == ("op9",)


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

    assert len(site.leaders()["op15-058"]) == 2                 # tout le corpus
    assert [d.player for _, d in site.leaders("op16")["op15-058"]] == ["Récent"]
    assert [d.player for _, d in site.leaders("op15")["op15-058"]] == ["Ancien"]
    assert site.leaders("op99") == {}


def _liste(joueur, placement, cartes, leader="OP15-058"):
    txt = f"1x{leader}\n" + "\n".join(f"{q}x{c}" for c, q in cartes)
    return Deck(raw_name=f"Purple Enel — {joueur} ({placement})", archetype="Purple Enel",
                player=joueur, placement=placement, leader_id=leader, cards=tuple(cartes),
                text=txt)


_CARTES_A = (("OP15-061", 4), ("OP15-067", 3))
_CARTES_B = (("OP15-061", 4), ("OP12-071", 2))


def test_signature_ignore_l_ordre_et_le_nom():
    a = _liste("X", 1, (("OP15-061", 4), ("OP15-067", 3)))
    b = _liste("Y", 9, (("OP15-067", 3), ("OP15-061", 4)))   # même contenu, autre ordre
    assert a.signature == b.signature
    assert _liste("X", 1, _CARTES_A).signature != _liste("X", 1, _CARTES_B).signature


def test_dedup_meme_joueur_meme_liste_garde_la_plus_recente():
    """Les coupes en ligne sont quotidiennes : un joueur assidu rejoue sa liste, et sans
    déduplication il pèserait autant de fois dans le cœur commun."""
    recent = _t("2026-07-26-r", date(2026, 7, 26), "OP16", (_liste("Assidu", 1, _CARTES_A),))
    vieux = _t("2026-07-20-v", date(2026, 7, 20), "OP16", (_liste("Assidu", 5, _CARTES_A),))
    pairs = Site(tournaments=(vieux, recent)).leaders()["op15-058"]
    assert len(pairs) == 1, "une seule entrée pour un joueur rejouant sa liste"
    assert pairs[0][0].slug == "2026-07-26-r", "l'occurrence la plus récente est gardée"


def test_dedup_epargne_le_meme_joueur_avec_une_AUTRE_liste():
    t = _t("2026-07-26-r", date(2026, 7, 26), "OP16",
           (_liste("Assidu", 1, _CARTES_A), _liste("Assidu", 2, _CARTES_B)))
    assert len(Site(tournaments=(t,)).leaders()["op15-058"]) == 2


def test_dedup_epargne_deux_joueurs_avec_la_MEME_liste():
    """Convergence, pas redondance : deux joueurs arrivant indépendamment aux mêmes cartes
    est le signal le plus fort qu'une liste est résolue. Chacun garde sa voix."""
    t = _t("2026-07-26-r", date(2026, 7, 26), "OP16",
           (_liste("Alice", 1, _CARTES_A), _liste("Bob", 2, _CARTES_A)))
    assert len(Site(tournaments=(t,)).leaders()["op15-058"]) == 2


def test_dedup_insensible_a_la_casse_du_joueur():
    a = _t("2026-07-26-a", date(2026, 7, 26), "OP16", (_liste("DZayas", 1, _CARTES_A),))
    b = _t("2026-07-20-b", date(2026, 7, 20), "OP16", (_liste("dzayas", 3, _CARTES_A),))
    assert len(Site(tournaments=(b, a)).leaders()["op15-058"]) == 1


def test_converging_players_expose_la_convergence():
    t = _t("2026-07-26-r", date(2026, 7, 26), "OP16",
           (_liste("Alice", 1, _CARTES_A), _liste("Bob", 2, _CARTES_A),
            _liste("Carol", 3, _CARTES_B)))
    conv = Site(tournaments=(t,)).converging_players("op15-058")
    assert len(conv) == 1, "seule la liste partagée est renvoyée"
    assert list(conv.values())[0] == ("Alice", "Bob"), "joueurs triés, sortie déterministe"


def test_converging_players_ignore_une_liste_unique():
    t = _t("2026-07-26-r", date(2026, 7, 26), "OP16", (_liste("Seule", 1, _CARTES_A),))
    assert Site(tournaments=(t,)).converging_players("op15-058") == {}


def test_archetype_label_retrouve_le_libelle():
    t = Tournament("2026-07-04-r", "R", date(2026, 7, 4), "", "", (_deck(),))
    assert Site(tournaments=(t,)).archetype_label("op15-058") == "Purple Enel"
