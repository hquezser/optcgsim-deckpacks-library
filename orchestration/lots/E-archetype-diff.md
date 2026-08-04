# LOT E — vue par écart sur les pages `/leaders/`

## Objectif

Sur une page d'archétype, calculer le **cœur commun** des listes et n'afficher pour chacune
que ce qui l'en distingue.

## Contexte

Tu travailles dans le dépôt courant (`optcgsim-deckpacks-library`, dans l'écosystème optcgsim). **Ce lot arrive
après les lots A à D, qui sont verts** : `sitegen/parse.py`, `packs.py`, `render.py` et les
gabarits existent et fonctionnent.

Lis d'abord :

1. `SPEC-site-v1.md` — le contrat, en particulier « Contenu des pages » et « Affichage des cartes ».
2. `AGENTS.md` — les invariants (dont : uniquement des IDs de cartes, sortie déterministe).
3. `sitegen/model.py` — le modèle **figé**. `Site.leaders()` renvoie déjà
   `archetype_slug -> ((Tournament, Deck), ...)` trié : c'est ton entrée.
4. `tests/test_contract_archetype.py` — **ta spécification exécutable**.
5. `sitegen/render.py` et `sitegen/templates/leader.html` — ce que tu vas étendre.

### Le problème que ça résout

Sur `/leaders/op15-058/`, 19 listes sont identiques à ~90 %. Les lire l'une après l'autre
n'apprend rien. Ce qu'un joueur veut savoir, c'est **ce qui varie** entre elles : c'est là
qu'est l'information de méta, et aucun site ne la sert aujourd'hui.

## Tâche

### 1. `sitegen/archetype.py` (nouveau module, stdlib uniquement)

```python
CORE_THRESHOLD = 0.8      # présence dans ≥ 80 % des listes
MIN_LISTS_FOR_DIFF = 4    # en dessous, un « cœur commun » n'a aucun sens

def core_cards(pairs) -> dict[str, int]
    """card_id -> quantité modale, pour les IDs présents dans ≥ CORE_THRESHOLD des listes.

    `pairs` est une séquence de (Tournament, Deck) — la valeur de Site.leaders()[aslug].
    Renvoie {} si len(pairs) < MIN_LISTS_FOR_DIFF.
    """

def deck_delta(deck, core) -> tuple[tuple[str, int, int], ...]
    """Ce qui distingue `deck` du cœur : ((card_id, qty_deck, qty_core), ...).

    Inclut les cartes absentes du cœur (qty_core = 0) ET celles dont la quantité diffère de
    la modale. Une carte du cœur absente du deck apparaît avec qty_deck = 0.
    Trié par quantité de deck décroissante puis par id, comme le reste de l'affichage.
    """
```

En cas d'égalité pour la quantité modale, retenir **la plus grande** — déterminisme obligatoire.

### 2. Intégration dans le rendu

Sur `/leaders/<aslug>/`, quand l'archétype a au moins `MIN_LISTS_FOR_DIFF` listes :

- afficher le **cœur commun une seule fois**, replié dans un `<details>` (il est long et
  identique partout), avec son nombre de cartes ;
- pour chaque liste, afficher **seulement son écart**, en distinguant visuellement un ajout
  (absent du cœur) d'un ajustement de quantité ;
- indiquer la taille de l'écart (« 6 cartes d'écart »), qui est l'information la plus utile
  au premier coup d'œil.

En dessous du seuil, garder l'affichage complet actuel — 9 archétypes sur 15 du corpus
n'ont qu'une ou deux listes, un « écart » y serait du bruit.

### 3. Deux redondances à supprimer au passage

Repérées sur le rendu réel, elles ont chacune un test rouge :

- **Le lien de source affiche l'URL brute comme texte** (« https://onepiece.limitlesstcg.com/decks/lists »,
  45 caractères sur deux lignes en mobile). Libelle-le par le nom du site — « Limitless »,
  « ChinoizeCupStats » — dérivé du domaine. Une URL brute n'est pas de l'attribution lisible.
- **Le leader est affiché deux fois** : dans le `<summary>` du deck et dans une ligne
  « Leader : OP15-058 — 50 cartes hors leader. » juste en dessous. Garde-le dans le
  `<summary>` (avec le total de cartes) et supprime la ligne du corps.

## Interdits

- Ne modifie **aucun** fichier figé : `SPEC-site-v1.md`, `AGENTS.md`, `sitegen/model.py`,
  `sitegen/build.py`, `tests/**`, `orchestration/**`.
- Ne touche pas à `sitegen/parse.py` ni `sitegen/packs.py`. Les `deckpack.json` produits ne
  changent **pas** : la vue par écart est de l'affichage, les packs restent des listes
  complètes et verbatim (c'est un contrat de données consommé par le simulateur).
- **Aucun nom de carte** : uniquement des IDs. Le libellé d'archétype est la seule exception
  du projet, elle est déjà en place, ne l'étends pas.
- Aucun JS, aucune dépendance nouvelle, aucun accès réseau.
- Ne désactive, ne réécris, ne marque `skip`/`xfail` aucun test.
- Sortie déterministe : deux builds identiques octet pour octet.

## Terminé quand

```bash
python3 -m pytest -q tests/test_contract_archetype.py tests/test_contract_render.py
```

sort en vert, **et** `./orchestration/verify.sh` ne régresse pas (il est aujourd'hui rouge
pour une raison en amont — 18 decks du corpus contiennent une quantité > 4 — qui ne te
concerne pas : ne tente pas de la corriger ici).

## Sortie attendue

Un résumé court : l'algorithme retenu pour la modale et les égalités, ce que donne le calcul
sur `op15-058` (Purple Enel) (19 listes) et `green-blue-luffy` (17), et toute divergence constatée.
