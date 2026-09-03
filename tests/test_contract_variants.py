"""Contrat du regroupement des listes quasi-identiques — FIGÉ.

La promesse faite au lecteur est précise : « toutes les listes de ce groupe sont à un échange
près les unes des autres ». Ces tests existent pour qu'elle reste vraie.
"""

from __future__ import annotations

import itertools
import random
from datetime import date

import pytest

from sitegen import variants
from sitegen.model import Deck, Tournament


def _deck(nom, cartes, placement=1):
    return Deck(raw_name=f"A — {nom} ({placement})", archetype="A", player=nom,
                placement=placement, leader_id="OP15-058", cards=cartes,
                text="1xOP15-058\n" + "\n".join(f"{q}x{c}" for c, q in cartes))


def _t(decks, slug="2026-07-04-x", d=date(2026, 7, 4)):
    return Tournament(slug, slug, d, "", "", tuple(decks), format="OP16")


def _rows(decks, t=None):
    t = t or _t(decks)
    return [(t, d, ()) for d in decks]


# ── la métrique ────────────────────────────────────────────────────────────────────────
def test_un_echange_vaut_un():
    """Retirer un exemplaire et en ajouter un autre : DEUX cartes changent, un échange."""
    a = _deck("A", (("X", 4), ("Y", 3)))
    b = _deck("B", (("X", 3), ("Y", 4)))
    assert variants.swaps(a, b) == 1


def test_liste_identique_vaut_zero():
    cartes = (("X", 4), ("Y", 3))
    assert variants.swaps(_deck("A", cartes), _deck("B", cartes)) == 0


def test_une_carte_remplacee_par_une_autre_vaut_un():
    a = _deck("A", (("X", 4), ("Y", 1)))
    b = _deck("B", (("X", 4), ("Z", 1)))
    assert variants.swaps(a, b) == 1


def test_la_metrique_est_symetrique():
    a, b = _deck("A", (("X", 4), ("Y", 2))), _deck("B", (("X", 1), ("Z", 3)))
    assert variants.swaps(a, b) == variants.swaps(b, a)


# ── le diamètre garanti : la raison d'être de la liaison complète ──────────────────────
def test_le_diametre_du_groupe_est_borne_pas_seulement_la_liaison():
    """LE test du lot. Trois listes en chaîne — A~B, B~C — mais A et C à deux échanges.

    Un regroupement par liaison SIMPLE les mettrait ensemble : c'est ce qui, sur le corpus
    réel, réunissait 58 des 106 listes Purple Enel OP16 dans une grappe de 5 échanges de
    diamètre. La promesse « quasi-identiques » aurait alors été fausse pour la plupart des
    paires que le lecteur compare.
    """
    a = _deck("A", (("X", 4), ("Y", 0 + 2), ("Z", 0)), placement=1)
    b = _deck("B", (("X", 3), ("Y", 3), ("Z", 0)), placement=2)
    c = _deck("C", (("X", 2), ("Y", 4), ("Z", 0)), placement=3)
    assert variants.swaps(a, b) == 1 and variants.swaps(b, c) == 1
    assert variants.swaps(a, c) == 2, "prémisse du test"

    groupes = variants.group_lists(_rows([a, b, c]))
    for gr in groupes:
        membres = [gr.rep] + [o[:3] for o in gr.others]
        for x, y in itertools.combinations(membres, 2):
            assert variants.swaps(x[1], y[1]) <= variants.MAX_SWAPS, \
                "deux listes du même groupe dépassent la tolérance annoncée"
    assert len(groupes) == 2, "A et C ne peuvent pas cohabiter"


@pytest.mark.parametrize("graine", [0, 1, 7, 42])
def test_la_partition_ne_depend_pas_de_l_ordre_d_entree(graine):
    """La sortie du site est comparée octet pour octet d'un build à l'autre : une partition
    qui dépend de l'ordre d'itération rendrait le build non reproductible.
    """
    decks = [_deck(f"J{i:02d}", (("X", 4 - (i % 3)), ("Y", i % 3), ("Z", 1)), placement=i + 1)
             for i in range(12)]
    ref = variants.group_lists(_rows(decks))
    melange = _rows(decks)
    random.Random(graine).shuffle(melange)
    autre = variants.group_lists(melange)

    def forme(gs):
        return [tuple(sorted([g.rep[1].slug] + [o[1].slug for o in g.others]))
                for g in gs]
    assert forme(ref) == forme(autre)


# ── ce que le groupe raconte ───────────────────────────────────────────────────────────
def test_le_representant_est_le_meilleur_placement():
    """C'est le résultat que le lecteur veut voir en tête, et ça fixe l'ordre — donc le
    déterminisme — d'une seule décision."""
    cartes = (("X", 4), ("Y", 3))
    decks = [_deck("Tard", cartes, placement=9), _deck("Tot", cartes, placement=2)]
    (gr,) = variants.group_lists(_rows(decks))
    assert gr.rep[1].player == "Tot"


def test_les_groupes_sortent_du_plus_gros_au_plus_petit():
    """Le plus gros groupe EST le build de consensus : c'est ce qu'on cherche d'abord."""
    commun = (("X", 4), ("Y", 3))
    seuls = (("A", 4), ("B", 3))
    decks = ([_deck(f"C{i}", commun, placement=i + 2) for i in range(4)]
             + [_deck("Seul", seuls, placement=1)])
    groupes = variants.group_lists(_rows(decks))
    assert [g.size for g in groupes] == [4, 1]


def test_identical_distingue_la_convergence_de_la_variante():
    """« 8 joueurs ont joué exactement ces 51 cartes » est un signal bien plus fort que
    « 8 listes à un échange près » — le rendu doit pouvoir les dire différemment."""
    cartes = (("X", 4), ("Y", 3))
    (gr,) = variants.group_lists(_rows([_deck("A", cartes, 1), _deck("B", cartes, 2)]))
    assert gr.identical

    voisin = _deck("C", (("X", 3), ("Y", 4)), 3)
    (gr2,) = variants.group_lists(_rows([_deck("A", cartes, 1), voisin]))
    assert not gr2.identical


def test_les_joueurs_restent_nommes_et_dedupliques():
    cartes = (("X", 4), ("Y", 3))
    (gr,) = variants.group_lists(_rows([_deck("Ana", cartes, 1), _deck("Ana", cartes, 2),
                                        _deck("Bo", cartes, 3)]))
    assert gr.players == ("Ana", "Bo")


def test_corpus_vide_et_liste_unique():
    assert variants.group_lists([]) == []
    (gr,) = variants.group_lists(_rows([_deck("Seul", (("X", 4),))]))
    assert gr.size == 1 and gr.others == () and gr.identical


def test_une_liste_non_parsee_ne_fait_pas_tomber_le_regroupement():
    """Les listes sans placement existent (nom non conforme) et doivent rester groupables :
    `_cle_de_depart` les range en fin plutôt que de lever."""
    cartes = (("X", 4), ("Y", 3))
    orphelin = Deck(raw_name="Nom bizarre", archetype="", player="", placement=None,
                    leader_id="OP15-058", cards=cartes, text="1xOP15-058\n4xX\n3xY")
    groupes = variants.group_lists(_rows([_deck("A", cartes, 1), orphelin]))
    assert len(groupes) == 1 and groupes[0].size == 2
    assert groupes[0].rep[1].player == "A", "le représentant doit rester le deck placé"


# ── le détail de l'échange : sans lui, le regroupement PERD de l'information ────────────
def test_le_detail_de_l_echange_nomme_les_cartes():
    """Annoncer « un échange » sans dire lequel ferait disparaître de la page les cartes
    propres aux membres du groupe. Un test de rendu l'a attrapé en conditions réelles : une
    carte présente seulement chez un membre n'apparaissait plus nulle part.
    """
    rep = _deck("Rep", (("X", 4), ("Y", 2)), 1)
    autre = _deck("Autre", (("X", 3), ("Y", 3)), 2)
    assert variants.swap_detail(rep, autre) == (("Y", 1), ("X", -1))

    (gr,) = variants.group_lists(_rows([rep, autre]))
    assert gr.others[0][4] == (("Y", 1), ("X", -1))


def test_le_detail_est_vide_pour_une_liste_identique():
    cartes = (("X", 4), ("Y", 3))
    (gr,) = variants.group_lists(_rows([_deck("A", cartes, 1), _deck("B", cartes, 2)]))
    assert gr.others[0][4] == ()


def test_le_detail_nomme_une_carte_entierement_nouvelle():
    """Le cas qui compte : une carte absente du représentant. C'est précisément celle qui
    disparaîtrait de la page si on ne la nommait pas."""
    rep = _deck("Rep", (("X", 4), ("Y", 1)), 1)
    autre = _deck("Autre", (("X", 4), ("Z", 1)), 2)
    detail = variants.swap_detail(rep, autre)
    assert detail == (("Z", 1), ("Y", -1))
    assert any(c == "Z" and n > 0 for c, n in detail), "la carte propre au membre est nommée"
