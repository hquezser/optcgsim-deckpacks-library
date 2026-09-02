"""Contrat du calendrier des formats — FIGÉ, écrit avec le module.

Le point sensible est l'ORDRE : un tri lexicographique classerait OP16.5 avant OP16 et OP9
après OP16, ce qui ferait déduire des formats faux en silence.
"""

from __future__ import annotations

from sitegen import formats as F


def test_ordre_numerique_pas_lexicographique():
    assert F.format_key("OP16") == (16, 0)
    assert F.format_key("OP16.5") == (16, 5)
    assert F.format_key("OP16.5") > F.format_key("OP16")
    assert F.format_key("OP17") > F.format_key("OP16.5")
    # Le piège lexicographique : "OP9" > "OP16" en texte, mais 9 < 16.
    assert F.format_key("OP9") < F.format_key("OP16")
    assert F.format_key("") == (-1, -1) and F.format_key("bidon") == (-1, -1)


def test_format_key_accepte_le_slug_autant_que_le_libelle():
    """Deux orthographes du même format : le libellé « OP14.5 » et le slug d'URL « op14-5 ».

    Ne reconnaître que le libellé était un piège silencieux : tout appelant triant sur des
    slugs obtenait (-1, -1) et reléguait les formats à décimale en fin de liste. Constaté
    dans le rendu, où OP14.5 s'affichait après OP13.
    """
    assert F.format_key("op14-5") == F.format_key("OP14.5") == (14, 5)
    assert F.format_key("op16-5") == (16, 5)
    assert F.format_key("op16") == (16, 0)
    # Et l'ordre attendu tient sur des slugs seuls.
    slugs = ["op13", "op14", "op14-5", "op15", "op16", "op16-5"]
    assert sorted(slugs, key=F.format_key, reverse=True) == [
        "op16-5", "op16", "op15", "op14-5", "op14", "op13"]


def test_un_booster_ouvre_son_propre_format():
    """Structurel : aucune donnée à déclarer pour les boosters."""
    assert F.format_of_set("OP16") == "OP16"
    assert F.format_of_set("op07") == "OP7"


def test_calendrier_des_starters():
    """ST30 est sorti avec OP16 ; ST31+ sont les starters qui font OP16.5."""
    assert F.format_of_set("ST30") == "OP16"
    assert F.format_of_set("ST31") == "OP16.5"
    assert F.format_of_set("ST36") == "OP16.5"


def test_set_inconnu_ne_devine_rien():
    assert F.format_of_set("ST99") is None
    assert F.format_of_set("EB03") is None      # non daté ici : trop ancien pour compter


def test_non_date_et_nouveau_sont_deux_choses_differentes():
    """La distinction sur laquelle reposait un avertissement inutilisable.

    `format_of_set` répond « à quel format ce set entre-t-il ? » — None pour les 26 sets
    anciens dont la date n'a plus d'effet sur aucune déduction. `beyond_horizon` répond
    « ce set est-il NOUVEAU ? » — et seul celui-là est actionnable. Les confondre listait
    26 sets anciens à chaque build pendant que tous les tournois étaient bien classés, donc
    un avertissement permanent, donc plus aucun avertissement.
    """
    assert F.format_of_set("EB03") is None          # non daté…
    assert F.beyond_horizon(("EB03",)) == ()        # …mais parfaitement connu
    assert F.beyond_horizon(("ST99",)) == ("ST99",)  # celui-là est vraiment neuf
    assert F.unknown_sets is F.beyond_horizon        # l'ancien nom pointe sur la vraie question


def test_un_nouveau_booster_ne_declenche_jamais_la_detection():
    """C'est ce qui rend un nouveau format automatique et sans entretien.

    `OPnn` ouvre `OPnn` structurellement. OP18 sortira sans qu'aucune ligne ne soit ajoutée
    ici : les tournois qui le jouent se classeront en OP18, et les rôles suivront.
    """
    assert F.beyond_horizon(("OP18", "OP19", "OP42")) == ()
    assert F.infer_format(("OP16", "OP18")) == "OP18"


def test_horizon_et_liste_de_sets_bougent_ensemble():
    """Garde-fou : avancer l'horizon sans déclarer les sets du nouveau format rendrait la
    détection aveugle exactement au moment où elle sert.
    """
    assert F.format_key(F.CALENDAR_HORIZON) > (0, 0), "horizon illisible"
    # Tout set daté dans FORMAT_OF_SET doit être couvert par le monde clos, sinon il serait
    # signalé comme nouveau alors qu'on connaît sa date.
    non_couverts = sorted(set(F.FORMAT_OF_SET) - F.LEGAL_SETS_AT_HORIZON)
    assert not non_couverts, f"datés mais hors du monde clos : {non_couverts}"
    # Et aucun set daté ne doit être postérieur à l'horizon annoncé.
    trop_recents = sorted(s for s, f in F.FORMAT_OF_SET.items()
                          if F.format_key(f) > F.format_key(F.CALENDAR_HORIZON))
    assert not trop_recents, f"postérieurs à l'horizon {F.CALENDAR_HORIZON} : {trop_recents}"


def test_sets_in_text():
    txt = "1xOP15-058\n4xOP15-061\n2xST31-004\n\n  3xEB03-012  "
    assert F.sets_in_text(txt) == ("EB03", "OP15", "ST31")


def test_infer_format_prend_le_plus_tardif():
    assert F.infer_format(("OP15", "OP16", "ST30")) == "OP16"
    # Le cas ChinoizeCup réel : ST31/32/33 dans un pool par ailleurs OP16.
    assert F.infer_format(("OP16", "ST30", "ST31", "ST32", "ST33")) == "OP16.5"
    assert F.infer_format(("EB03", "ST99")) == ""
    assert F.infer_format(()) == ""


def test_sets_after_format_est_le_garde_fou():
    """Un tournoi annoncé OP16 qui joue du ST31 est en avance ou mal étiqueté."""
    assert F.sets_after_format("OP16", ("OP16", "ST30")) == ()
    assert F.sets_after_format("OP16", ("OP16", "ST31", "ST32")) == ("ST31", "ST32")
    # Depuis OP16.5, ces mêmes sets sont cohérents.
    assert F.sets_after_format("OP16.5", ("OP16", "ST31", "ST32")) == ()
    # Sans étiquette, il n'y a rien à contredire.
    assert F.sets_after_format("", ("ST31",)) == ()
