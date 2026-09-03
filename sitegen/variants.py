"""Regroupement des listes quasi-identiques d'un archétype.

Le problème, mesuré sur le corpus : un archétype fourni aligne des dizaines de listes qui se
ressemblent. `Purple Enel` en OP16 a 106 listes, dont **75 % sont à un seul échange près
d'une autre**. La page les affichait à la suite, puis en tronquait le surplus — donc à la
fois répétitive ET incomplète.

## Pourquoi l'échange, et pas un seuil réglé

Deux decks légaux ont 50 cartes. La distance « nombre de cartes qui diffèrent » est donc
toujours PAIRE, et sa moitié se lit directement : c'est le nombre d'**échanges** (retirer un
exemplaire, en ajouter un autre). `MAX_SWAPS = 1` n'est pas un seuil ajusté sur les données,
c'est la plus petite modification qu'un joueur puisse faire à un deck. C'est ce qui le rend
explicable — et vérifiable par le lecteur, à qui on annonce la règle.

Il fallait cette propriété, parce que **les données n'offrent aucun seuil naturel**. La
distribution des distances par paires est unimodale et lisse, avec un pic autour de 8 à 10
cartes d'écart : il n'existe aucun creux où poser une frontière.

## Pourquoi la liaison complète, et pas le chaînage

Première tentative, réfutée par la mesure : regrouper par liaison SIMPLE (A~B et B~C mettent
A, B, C ensemble). Sur un continuum, ça chaîne. À un échange de tolérance, 58 des 106 listes
`Purple Enel` OP16 tombaient dans une seule grappe de **10 cartes de diamètre** — cinq
échanges entre ses deux extrêmes. Appeler ça « quasi-identique » aurait été faux.

D'où la liaison COMPLÈTE : une liste ne rejoint un groupe que si elle est à ≤ MAX_SWAPS de
**toutes** ses membres. Le diamètre du groupe est alors borné par construction, et la
promesse faite au lecteur est vraie de n'importe quelle paire qu'il compare.

Le prix est que le partitionnement glouton n'est pas canonique : un autre ordre de départ
donnerait d'autres groupes (tous valides). L'ordre est donc fixé — meilleur placement
d'abord — ce qui rend la sortie déterministe ET donne à chaque groupe le meilleur résultat
pour représentant, qui est celui que le lecteur veut voir.

Stdlib uniquement, sortie déterministe.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Deck, Tournament

__all__ = ["MAX_SWAPS", "swaps", "swap_detail", "VariantGroup", "group_lists"]

# Un échange = retirer un exemplaire d'une carte, en ajouter un d'une autre. Voir l'en-tête :
# c'est une unité de jeu, pas un paramètre à régler.
MAX_SWAPS = 1


def swaps(a: Deck, b: Deck) -> int:
    """Nombre d'échanges séparant deux listes.

    Somme des écarts de quantité, divisée par deux : deux decks de 50 cartes ne peuvent
    différer que par un nombre pair de cartes, et chaque échange en déplace deux. Une
    division entière suffit donc, et reste juste même sur une liste malformée (arrondir vers
    le bas sous-estime l'écart, ce qui ne peut que refuser un regroupement, jamais en
    inventer un).
    """
    ca, cb = dict(a.cards), dict(b.cards)
    total = sum(abs(ca.get(k, 0) - cb.get(k, 0)) for k in ca.keys() | cb.keys())
    return total // 2


def swap_detail(rep: Deck, other: Deck) -> tuple[tuple[str, int], ...]:
    """Ce qui change entre `rep` et `other`, carte par carte : (id, écart de quantité).

    Écart POSITIF = `other` en joue plus que le représentant. Trié par écart décroissant
    puis identifiant, pour un ordre total et une lecture naturelle (les ajouts d'abord).

    Indispensable, et pas seulement agréable : annoncer « un échange » sans dire lequel
    ferait DISPARAÎTRE de la page les cartes propres aux membres du groupe. Un test de
    contrat l'a attrapé — c'est de l'information perdue, pas de la compression.
    """
    ca, cb = dict(rep.cards), dict(other.cards)
    ecarts = [(c, cb.get(c, 0) - ca.get(c, 0)) for c in ca.keys() | cb.keys()]
    return tuple(sorted(((c, n) for c, n in ecarts if n != 0),
                        key=lambda cn: (-cn[1], cn[0])))


@dataclass(frozen=True)
class VariantGroup:
    """Un groupe de listes toutes à ≤ MAX_SWAPS échanges les unes des autres.

    `rep` est la ligne représentative — le meilleur placement du groupe. `others` sont les
    autres, appariées à leur écart en échanges par rapport à `rep`.
    """

    rep: tuple[Tournament, Deck, tuple]
    # (tournoi, deck, delta au cœur, nombre d'échanges, détail des échanges vs `rep`)
    others: tuple[tuple[Tournament, Deck, tuple, int, tuple], ...]

    @property
    def size(self) -> int:
        return 1 + len(self.others)

    @property
    def players(self) -> tuple[str, ...]:
        """Joueurs distincts du groupe, ordre d'apparition. Les noms restent nommés : on
        signale le partage d'une liste, on ne fusionne pas les voix (cf. SPEC § convergence).
        """
        vus: list[str] = []
        for row in (self.rep,) + self.others:
            d = row[1]
            if d.player and d.player not in vus:
                vus.append(d.player)
        return tuple(vus)

    @property
    def identical(self) -> bool:
        """Toutes les listes du groupe sont-elles la MÊME liste au caractère près ?

        Distinction qui compte pour le lecteur : « 8 joueurs ont joué exactement ces 51
        cartes » est un signal bien plus fort que « 8 listes à un échange près ».
        """
        return all(n == 0 for *_, n, _ in self.others)


def _cle_de_depart(row: tuple[Tournament, Deck, tuple]) -> tuple:
    """Ordre d'amorçage des groupes : meilleur placement, puis plus récent, puis slug.

    Fixé, pour deux raisons qui vont dans le même sens : la sortie doit être déterministe
    (le site est comparé octet pour octet d'un build à l'autre), et le représentant d'un
    groupe doit être son meilleur résultat.
    """
    t, d, *_ = row
    return (d.placement if d.placement is not None else 10**6,
            -(t.date.toordinal() if t.date else 0),
            t.slug, d.slug)


def group_lists(rows, max_swaps: int = MAX_SWAPS) -> list[VariantGroup]:
    """Partitionne des lignes `(tournoi, deck, delta)` en groupes de diamètre borné.

    Glouton à liaison complète : chaque liste rejoint le premier groupe dont TOUTES les
    membres sont à ≤ `max_swaps`, sinon elle en ouvre un nouveau.

    Groupes rendus du plus gros au plus petit — le plus gros est le build de consensus, et
    c'est l'information que le lecteur cherche d'abord. À taille égale, le meilleur placement
    puis le slug tranchent, pour un ordre total.
    """
    rows = list(rows)
    if not rows:
        return []
    ordre = sorted(rows, key=_cle_de_depart)

    grappes: list[list[tuple]] = []
    for row in ordre:
        for g in grappes:
            if all(swaps(row[1], m[1]) <= max_swaps for m in g):
                g.append(row)
                break
        else:
            grappes.append([row])

    groupes = [
        VariantGroup(
            rep=g[0],
            others=tuple((t, d, delta, swaps(d, g[0][1]), swap_detail(g[0][1], d))
                         for t, d, delta in g[1:]),
        )
        for g in grappes
    ]
    groupes.sort(key=lambda gr: (-gr.size, _cle_de_depart(gr.rep)))
    return groupes
