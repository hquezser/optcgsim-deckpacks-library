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
    assert F.unknown_sets(("OP16", "ST31", "EB03", "ST99")) == ("EB03", "ST99")


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
