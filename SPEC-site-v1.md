# SPEC — site bibliothèque v1 (contrat)

Ce document est **le contrat**. Toute implémentation est jugée conforme ou non par
`orchestration/verify.sh`, pas par appréciation. En cas d'ambiguïté entre ce document et
une implémentation, ce document gagne.

## Positionnement (ce qui détermine les arbitrages)

Le site n'est **pas** une bibliothèque de decklists — Limitless fait déjà ça, mieux. C'est
**la rampe d'accès entre le méta compétitif et OPTCGSim**. La seule chose qu'on offre et
que personne d'autre n'offre, c'est une commande d'import en un clic.

Conséquence de design, non négociable : **la commande d'import est l'élément visuel
principal de chaque page**, copiable en un clic. Tout le reste est secondaire.

## Portée v1

Générateur statique. **Zéro** JS, auth, base de données, cookie, analytics, publicité,
compte utilisateur. Sortie = fichiers dans `dist/`, servables tels quels.

Hors portée v1 (ne pas implémenter) : panier de sélection à la carte, pages HTML par deck,
recherche, liens d'affiliation, i18n.

## Entrée

Les packs scrapés du dépôt sibling, par défaut `../optcgsim-deckpacks-data/packs/*/deckpack.json`
(surchargeable par `--packs-dir`). Format défini par `../optcgsim-deckpacks/SPEC-deckpack.md`.

Le slug de tournoi est **le nom du dossier** contenant le manifeste
(ex. `2026-07-04-regional-bielefeld`).

## Modèle de données

Le contrat Python est `sitegen/model.py` — **il est figé, aucun worker ne le modifie**.
Les implémentations produisent et consomment ces dataclasses.

### Règles de parsing (la partie fragile)

Les champs structurés n'existent pas dans le format : ils sont encodés dans la chaîne
`name` de chaque deck. Le parsing est donc **best-effort avec dégradation propre**.

**Nom de deck** — regex unique :

```
^(?P<archetype>.+?)\s+—\s+(?P<player>.+?)\s+\((?P<place>\d+)(?:st|nd|rd|th)\)$
```

(le séparateur est un tiret cadratin U+2014, entouré d'espaces)

- Si ça matche : `archetype`, `player`, `placement` renseignés.
- Si ça ne matche pas : `archetype=""`, `player=""`, `placement=None`, et
  `raw_name` conserve la chaîne d'origine **verbatim**. Le deck reste affiché sur la page
  de son tournoi, mais est **exclu** des pages `/leaders/` et de `/meta/`.
- Ne jamais lever d'exception sur un nom non conforme. Ne jamais inventer de valeur.

**Leader** — première ligne du `text`, au format `1xOP15-058` → `leader_id = "OP15-058"`.
Si la quantité de la première ligne n'est pas `1`, enregistrer un avertissement dans le
rapport de build (le leader est garanti en première position par le scraper amont) ; ne
pas échouer.

**Cartes** — lignes suivantes, `4xOP15-061` → `("OP15-061", 4)`, dans l'ordre du fichier,
leader exclu.

**Slug** (fonction unique, réutilisée partout) : minuscules, toute suite de caractères
non alphanumériques → `-`, tirets de tête/queue retirés.
`"Purple Enel"` → `purple-enel` · `"Red/Black Koby"` → `red-black-koby` ·
`"Marc@@@1"` → `marc-1`.

**Slug de deck** : `f"{placement:02d}-{slug(archetype)}-{slug(player)}"`.
Si `placement is None` : `f"xx-{slug(raw_name)}"`.

## Carte des URLs (contrat exact)

```
/index.html                                    tournois récents + index des leaders
/tournois/<tslug>/index.html                   un tournoi : ses decks
/tournois/<tslug>/deckpack.json                le pack complet du tournoi
/tournois/<tslug>/decks/<dslug>.json           un deck seul, en pack d'un élément
/leaders/<aslug>/index.html                    toutes les listes de cet archétype
/leaders/<aslug>/deckpack.json                 pack : toutes ses listes
/meta/index.html                               instantané du méta courant
/meta/deckpack.json                            pack : le méta courant
/style.css                                     feuille unique, ~200 lignes max
```

Aucune autre URL. Pas de `404.html`, pas de sitemap en v1.

Tout `deckpack.json` émis doit passer `../optcgsim-deckpacks/scripts/validate.py`.

### Définition du pack « méta »

Déterministe et testable — **ne pas utiliser la date du jour** :

- Date de référence = date du tournoi le plus récent du corpus.
- Retenir les decks des tournois dans les **60 jours** précédant cette référence,
  `placement <= 8`, `archetype != ""`.
- Trier par date de tournoi décroissante, puis placement croissant.
- Plafonner à **40 decks**.

`name` du pack : `f"Méta {ref_date:%Y-%m}"`. `author` : `"optcgsim-deckpacks-library"`.

## Contenu des pages

Chaque page HTML porte, en haut et visuellement dominant, un bloc « import » :

```
studio decks import-pack https://<base-url>/<chemin>/deckpack.json
```

L'URL de base vient de `--base-url` (défaut `http://localhost:8000`).

**La commande doit être lisible et sélectionnable en entier, sans scroll horizontal.** Mesuré
en mobile 375 px, elle était tronquée à 65 % derrière une barre de défilement de quelques
millimètres — le seul élément qui justifie le site était donc inutilisable. Le contrat exige
donc : retour à la ligne (`pre-wrap` + coupure de mot) pour que tout soit visible, et
`user-select: all` pour qu'un clic unique sélectionne la commande entière. Sans JS : c'est
le CSS qui fournit le geste de copie.

Le bloc mentionne **optcgsim-studio par un lien** : un visiteur qui découvre le site ne sait
pas ce qu'est cette commande ni où obtenir l'outil qui l'exécute.

- **`/`** : les 20 tournois les plus récents (nom, date, nombre de decks, lien) ; la liste
  des archétypes avec leur nombre de listes, décroissant ; un lien vers `/meta/`.
- **`/tournois/<tslug>/`** : bloc import du pack complet. Puis les decks triés par
  placement croissant (non parsés en fin de liste) ; par deck : placement, archétype,
  joueur, leader, la liste des cartes, et sa commande d'import individuelle.

  **Chaque deck est replié dans un `<details>`** dont le `<summary>` porte placement,
  archétype, joueur et leader ; le premier est `open`. Déplié, un tournoi faisait 8 écrans
  de défilement en mobile, ce qui rendait la page inutilisable comme index. `<details>` est
  natif : aucun JS.

  **La `description` brute n'est pas affichée.** C'est un champ de métadonnées de scraper :
  il répète le titre et expose des paramètres internes (`region=Europe, time=3months`).
  Seules les **URL** qu'elle contient sont extraites et rendues en une ligne d'attribution
  compacte (`rel="noreferrer nofollow"`, `target="_blank"`) — créditer la source reste
  obligatoire, l'étaler ne l'est pas.

### Affichage des cartes

Les cartes d'un deck sont affichées **triées par quantité décroissante, puis par identifiant**.
L'ordre du fichier source empêchait de comparer visuellement deux listes d'un même
archétype, ce qui est précisément l'usage d'une page `/leaders/`. Les 4-of remontent en tête :
c'est la colonne vertébrale du deck.

Ce tri est **d'affichage uniquement**. `Deck.text` et les `deckpack.json` produits
conservent l'ordre source verbatim — c'est un contrat de données consommé par un autre
programme.

### Placement

Rendu en texte simple contigu (`1st`, `2nd`, `11th`), **sans `<sup>`** : la mise en exposant
produisait un espace visible (« 1 st ») qui se lit comme une coquille.
- **`/leaders/<aslug>/`** : bloc import. Puis les listes de cet archétype, tous tournois,
  triées par date décroissante puis placement ; chaque entrée indique son tournoi.
- **`/meta/`** : bloc import. La composition du pack méta, groupée par archétype.

Pas de nom de carte affiché — **uniquement des IDs**. C'est un invariant, pas un manque
(cf. `AGENTS.md`).

## Rendu HTML

Jinja2, gabarits dans `sitegen/templates/`. HTML5 valide, une seule `style.css`, lisible
en mobile (une colonne, pas de largeur fixe). Sobre : pas de framework CSS, pas de police
distante, pas de requête réseau sortante depuis les pages produites.

## CLI

```bash
python3 -m sitegen.build --packs-dir ../optcgsim-deckpacks-data/packs \
                         --out dist --base-url https://exemple.org
```

Sortie sur stdout : nombre de tournois, decks, archétypes, pages écrites, et la liste des
avertissements. Code de sortie `0` si tout est écrit, `1` si un pack d'entrée est
illisible.

`sitegen/build.py` est **figé** (écrit par l'orchestrateur) : il câble les modules et
n'est modifié par aucun worker.

## Définition de « terminé »

`orchestration/verify.sh` passe au vert. Il vérifie, dans l'ordre :

1. `pytest -q` (tous les tests verts)
2. le build s'exécute sur le corpus réel sans erreur
3. tous les `deckpack.json` produits passent le validateur de la spec
4. l'ensemble exact des chemins produits correspond à la carte des URLs ci-dessus
5. aucune page ne charge de **sous-ressource** externe (`src`, `<link>`, `@import`,
   `url()`) — les `<a href>` externes sont autorisés, et doivent porter
   `rel="noreferrer nofollow"`

Rien d'autre ne compte comme « terminé ». Un worker ne déclare pas la victoire :
`verify.sh` la déclare.
