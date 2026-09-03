# LOT I — le rail : deux panneaux sans une ligne de script

## Objectif

Donner aux pages `/leaders/` et `/tournaments/` la forme à deux panneaux des maquettes
Console : un rail de contexte à gauche, la chose choisie à droite. **Sans JavaScript** — la
sélection est une page, pas un événement.

## Contexte

C'est le lot le plus structurant, et le seul qui touche la carte des URLs. Lire d'abord
SPEC § « Refonte Console — ce que le zéro-JS impose ».

Le point à comprendre : ce n'est PAS un modèle d'interaction nouveau. Les pages existent
déjà — `/leaders/<aslug>/`, `/tournaments/<tslug>/`. On leur ajoute un rail commun, et le
« clic qui change le panneau droit » est un lien vers la page voisine. L'URL redevient
partageable, et la page reste légère : mesuré, 14 Ko transférés pour 277 Ko brut.

Dépend des LOTS G et H.

## Tâche

### 1. Le partiel `_rail.html`

Un rail générique : un titre, une ligne de compte, une liste d'entrées dont une est
courante. Il sert les deux pages, avec des données différentes — un seul partiel, pas deux
qui divergeront (cette semaine, `meta_pairs` en double a divergé sans que rien ne le
signale, et la même famille de défaut a été trouvée dans le studio le même jour).

L'entrée courante n'est pas un lien : elle est marquée, et c'est la seule différence
visuelle qui compte.

### 2. `/leaders/<aslug>/` passe à UN format

La page porte le format de son URL au lieu d'empiler toutes ses sections :

```
/leaders/<aslug>/index.html          format courant + rail du champ
/leaders/<aslug>/<fslug>/index.html  autre format, même page
```

Le rail est le champ du format affiché. À droite : la lecture comparative du LOT G (valeur et
rang, jamais d'étiquette), le build de consensus avec core et flex, les autres groupes.

Des puces de format en tête mènent aux autres formats de l'archétype. Elles viennent de la
direction « Archetype browser » écartée, et répondent à ce que Console laissait ouvert.

`/leaders/<aslug>/deckpack.json` et `<fslug>.json` ne bougent pas.

### 3. `/tournaments/<tslug>/` reçoit le rail des tournois

Rail = les tournois du même format, le courant marqué. À droite, la page actuelle enrichie :
la concentration en valeur située, et le champ de CE tournoi peint avec le composant de
`/meta/` — pas un graphique nouveau.

### 4. Les circuits deviennent un axe, pas une étiquette

Sur `/tournaments/`, papier et en ligne sont filtrables. Sans JS, un filtre est une URL :

```
/tournaments/paper/index.html
/tournaments/online/index.html
```

Papier reprend l'or des placements, en ligne l'accent — la distinction sur laquelle repose
toute la logique de format cesse d'être un petit mot gris.

### 5. `orchestration/check_dist.py` (FIGÉ — l'orchestrateur s'en charge)

`expected_paths()` doit couvrir les nouveaux chemins. Signaler dans la sortie du lot ce qui
manque plutôt que de modifier le fichier.

## Interdits

- `<script`, `onclick=`, `javascript:`, `navigator.clipboard` : bannis, et démentiraient la
  page légale.
- Faire coexister l'ancienne vue « tous formats empilés » avec la nouvelle. Deux vues de la
  même chose divergent — le lot les remplace, il ne les additionne pas.
- Répéter le rail en dupliquant son gabarit dans les deux pages.

## Terminé quand

`./orchestration/verify.sh` est vert, `check_internal_links` compris — c'est lui qui attrape
une carte d'URLs à moitié migrée, et il a été écrit pour ça.

Contrôle visuel obligatoire en 375 px : le rail à deux panneaux DOIT se replier en une
colonne, et le rail passer derrière le contenu plutôt que devant.

## Sortie attendue

Les chemins ajoutés et retirés de la carte des URLs, le nombre de pages produites avant et
après, et le poids transféré (gzip) de la page leader la plus lourde, avant et après.
