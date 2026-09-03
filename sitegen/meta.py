"""Le pack « méta » : quel échantillon du méta courant on publie, et pourquoi celui-là.

## Le défaut corrigé ici

La sélection était « les 40 listes les plus récentes du format courant ». Mesuré sur le
corpus au 2026-09-03, sur une fenêtre de 313 listes éligibles, ça donnait :

  - **5 tournois**, les cinq derniers, tous en ligne ;
  - **12 archétypes sur 33**.

Manquaient Green/Blue Luffy (38 listes dans la fenêtre), Purple/Yellow Rosinante (28),
Blue/Yellow Nami (26), Black/Yellow Blackbeard (12). Un joueur qui importait ce pack pour
s'entraîner contre le méta ne rencontrait pas les trois archétypes les plus joués. Ce n'était
pas un instantané du méta, c'était « les cinq derniers événements » : la date dominait tout.

## La règle retenue

Le pack doit répondre à une question précise : **contre quoi vais-je jouer ?** Donc les
slots sont répartis **au prorata de la part de chaque archétype** dans la fenêtre, et non
distribués par ordre d'arrivée.

Répartition par la méthode des plus forts restes : chaque archétype reçoit la partie entière
de son quota, puis les slots restants vont aux plus gros restes. C'est exact (la somme fait
toujours le plafond) et déterministe (les égalités se tranchent sur l'effectif puis le slug).

Un archétype à 1 liste sur 313 n'obtient aucun slot, et c'est **voulu** : il représente 0,3 %
du champ, et lui donner une place la retirerait à un archétype qu'on rencontre vraiment. La
PAGE, elle, affiche la distribution complète — un archétype absent du pack reste visible et
chiffré (`window_distribution`).

## Quelle liste, dans un archétype

Sa liste de **consensus** : on regroupe ses listes à un échange près (cf. `variants`) et on
prend les représentants des plus gros groupes d'abord. Un pack d'entraînement doit contenir
les builds que l'on rencontre, pas les tentatives isolées.

## Ancrage au format

Une fenêtre de dates seule peut chevaucher un changement de format et mélanger deux
environnements de jeu sans le signaler. Le filtre par format courant était présent dans une
des deux copies de cette fonction et absent de l'autre : la page et son propre pack
divergeaient dès que la fenêtre couvrait deux formats. C'est la raison d'être de ce module —
**une règle, un seul endroit.**
"""

from __future__ import annotations

from datetime import timedelta

from . import variants
from .model import Deck, Site, Tournament

__all__ = ["META_WINDOW_DAYS", "META_MAX_DECKS", "meta_pairs", "window_pairs",
           "window_distribution"]

META_WINDOW_DAYS = 60
META_MAX_DECKS = 40


def window_pairs(site: Site) -> tuple[tuple[Tournament, Deck], ...]:
    """Toutes les listes ÉLIGIBLES : format courant, dans la fenêtre, top 8, parsées.

    Sans plafond — c'est le vivier dont le pack est un échantillon, et c'est aussi ce que la
    page doit pouvoir chiffrer pour annoncer une distribution honnête.
    """
    ref = site.reference_date
    if ref is None:
        return ()
    current = site.current_format
    start = ref - timedelta(days=META_WINDOW_DAYS)
    out: list[tuple[Tournament, Deck]] = []
    for t in site.tournaments:
        if t.date is None or t.date < start or t.date > ref:
            continue
        if current and t.format_slug != current:
            continue
        for d in t.decks:
            if d.parsed and d.placement is not None and d.placement <= 8:
                out.append((t, d))
    out.sort(key=lambda p: (-(p[0].date.toordinal()), p[1].placement, p[0].slug, p[1].slug))
    return tuple(out)


def window_distribution(site: Site) -> tuple[tuple[str, int], ...]:
    """(archetype_slug, nombre de listes) sur toute la fenêtre, du plus joué au moins joué.

    C'est LE contenu informatif de la page méta, et il ne coûte presque rien : un archétype
    absent du pack reste ainsi visible et chiffré, au lieu de disparaître.
    """
    compte: dict[str, int] = {}
    for _, d in window_pairs(site):
        compte[d.archetype_slug] = compte.get(d.archetype_slug, 0) + 1
    return tuple(sorted(compte.items(), key=lambda kv: (-kv[1], kv[0])))


def _quotas(distribution, plafond: int) -> dict[str, int]:
    """Répartition des slots au prorata, par plus forts restes. Somme exacte = plafond."""
    total = sum(n for _, n in distribution)
    if total == 0:
        return {}
    if total <= plafond:
        return {a: n for a, n in distribution}

    entiers: dict[str, int] = {}
    restes: list[tuple[float, int, str]] = []
    for aslug, n in distribution:
        exact = n * plafond / total
        entiers[aslug] = int(exact)
        # Égalités tranchées sur l'effectif décroissant puis le slug : ordre total, donc
        # sortie reproductible d'un build à l'autre.
        restes.append((exact - int(exact), n, aslug))
    reste_a_placer = plafond - sum(entiers.values())
    restes.sort(key=lambda r: (-r[0], -r[1], r[2]))
    for _, _, aslug in restes[:reste_a_placer]:
        entiers[aslug] += 1
    return entiers


def meta_pairs(site: Site) -> tuple[tuple[Tournament, Deck], ...]:
    """L'échantillon publié du méta courant : représentatif, plafonné, déterministe.

    Ne dépend jamais de la date du jour (la référence est le tournoi le plus récent du
    corpus), pour que la sortie du site reste reproductible.
    """
    vivier = window_pairs(site)
    if not vivier:
        return ()

    distribution = window_distribution(site)
    quotas = _quotas(distribution, META_MAX_DECKS)

    par_archetype: dict[str, list[tuple[Tournament, Deck]]] = {}
    for t, d in vivier:
        par_archetype.setdefault(d.archetype_slug, []).append((t, d))

    choisis: list[tuple[Tournament, Deck]] = []
    for aslug, quota in sorted(quotas.items(), key=lambda kv: (-kv[1], kv[0])):
        if quota <= 0:
            continue
        rows = [(t, d, ()) for t, d in par_archetype.get(aslug, ())]
        # Représentants des plus gros groupes d'abord : le build de consensus avant les
        # tentatives isolées.
        for groupe in variants.group_lists(rows)[:quota]:
            t, d, _ = groupe.rep
            choisis.append((t, d))

    # Ordre de sortie : date décroissante puis placement, comme avant — c'est l'ordre que
    # le lecteur attend d'un instantané, et le pack le conserve tel quel.
    choisis.sort(key=lambda p: (-(p[0].date.toordinal()), p[1].placement,
                                p[0].slug, p[1].slug))
    return tuple(choisis)
