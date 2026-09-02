# optcgsim-deckpacks-library

**Générateur de site statique qui relie le méta compétitif One Piece Card Game au
simulateur OPTCGSim.**

Ce n'est pas une bibliothèque de decklists — [Limitless](https://onepiece.limitlesstcg.com)
fait déjà cela, mieux, et c'est l'une de nos sources. Ce site sert **une** chose que
personne d'autre ne sert : une commande copiable qui importe des decks dans le simulateur.

```bash
studio decks import-pack https://<site>/leaders/op15-058/deckpack.json
```

Une commande, et toutes les listes Purple Enel de dizaines de tournois arrivent dans
OPTCGSim. Tout le reste de chaque page en découle.

## Ce que le site apporte

**Les listes réduites à leur écart.** Sur une page d'archétype, les listes d'un même deck
sont identiques à ~90 %. On calcule le **cœur commun** (cartes présentes dans ≥ 80 % des
listes) et on n'affiche par liste que ce qui l'en distingue — l'information de méta est
dans ce qui varie, pas dans la répétition.

**Le méta courant et les métas à venir.** Le simulateur reçoit les extensions avant le
circuit papier : un format peut donc être déjà joué en ligne quand les tournois papier en
sont au précédent. Le site distingue le format courant (celui du circuit papier) des
formats en avance, avec leurs codes réels — OP16, OP16.5, OP17.

**Un cloisonnement par format, par justesse.** Un cœur commun calculé sur deux formats
mélangés décrit un deck qui n'a jamais existé. Les vues agrégées sont donc toujours
restreintes à un seul format.

## Invariants

Ces contraintes sont ce qui rend le projet publiable et gratuit. Elles ne sont pas
négociables pour du confort d'affichage — voir [AGENTS.md](AGENTS.md) pour le détail.

- **Aucun contenu sous copyright** : identifiants de cartes, quantités, méta publique de
  tournoi. Aucune image, aucun nom de carte, aucun texte de carte.
- **Aucune sous-ressource externe** : pas de CDN, pas de police distante, pas de tracker.
  Une page produite ne parle à personne. Les sources sont créditées par de simples liens.
- **Aucune monétisation, aucun compte, aucune base de données.** Le site est une
  contribution à l'écosystème, pas un produit. Il n'y a donc aucune donnée utilisateur.
- **Sortie déterministe** : deux builds sur la même entrée produisent des octets identiques.
- **Zéro JS**, et aucune dépendance au-delà de Jinja2.

## Utilisation

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Construire, puis servir
.venv/bin/python -m sitegen.build --out dist --base-url http://localhost:8731
python3 -m http.server -d dist 8731
```

`--packs-dir` pointe par défaut sur `../optcgsim-deckpacks-data/packs`.

## Vérifier

```bash
./orchestration/verify.sh
```

C'est le critère de « terminé » du projet, et il traverse plusieurs dépôts : tests, build,
validation des packs produits contre la spec du format, carte exacte des URLs, absence de
sous-ressource externe, cohérence format/pool de cartes, importabilité réelle par le
simulateur, et reproductibilité du build.

Un contrôle qui ne peut pas s'exécuter s'affiche `—` et non `✓` : le harnais distingue
partout « rien à signaler » de « je n'ai rien pu vérifier ».

## Écosystème

Quatre dépôts aux finalités disjointes, qui doivent rester voisins — les liens entre eux
sont des chemins relatifs.

| Dépôt | Rôle |
|---|---|
| [optcgsim-deckpacks](https://github.com/hquezser/optcgsim-deckpacks) | **Le format** : spec `deckpack.json`, schéma, validateur — l'arbitre |
| [optcgsim-deckpacks-data](https://github.com/hquezser/optcgsim-deckpacks-data) | **Les données** : scrapers et corpus, un pack par tournoi |
| **optcgsim-deckpacks-library** ← ici | **La vitrine** : ce générateur |
| [optcgsim-studio](https://github.com/hquezser/optcgsim-studio) | **Le consommateur** : `studio decks import-pack` |

## Licence

Le code est libre d'usage. Les decklists ne sont que des identifiants de cartes et des
résultats de tournois publics ; les illustrations, noms et textes de cartes One Piece Card
Game appartiennent à Bandai et ne figurent nulle part dans ce dépôt.
