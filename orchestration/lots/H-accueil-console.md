# LOT H — l'accueil : l'état du format, et la commande qui en découle

## Objectif

Refaire `index.html` d'après la maquette « Home » du canevas. L'accueil cesse d'être un
répertoire de quatre sections pour répondre à une question : **où en est le format, et quelle
commande en découle.**

## Contexte

Aujourd'hui l'accueil empile Formats, Current meta, 20 tournois récents, Archetypes. Il
duplique `/tournaments/` et `/meta/` sans rien ajouter. Son titre a déjà été corrigé (il
annonçait « Recent tournaments » alors que la première section est Formats) mais la structure
reste un menu.

Dépend du LOT G : `circuit_timeline`, `concentration`, `corpus_concentration_median`.

## Tâche

Quatre blocs, dans cet ordre, dans `sitegen/templates/index.html` :

1. **L'état du format** — le code du format courant en grand, son rôle, et la phrase qui dit
   d'où il vient (`current_format_circuit`, `paper_format`, date du dernier tournoi papier).
   À côté, les trois compteurs du corpus. Tout existe déjà au modèle.

2. **La commande méta**, en encadré accentué. C'est la seule action primaire de la page.
   Reprend `_import.html` tel quel — ne pas en faire une variante.

3. **Les deux circuits dans le temps** — deux pistes horizontales, papier et en ligne,
   peintes depuis `circuit_timeline()`. Les segments sont des `<div>` en `position: absolute`
   dont `left`/`width` viennent des pourcentages calculés en Python. Une ligne de repères de
   mois en dessous.

   C'est le bloc qui porte le lot : le fait le plus distinctif du site — le simulateur court
   devant le papier — n'est aujourd'hui qu'une phrase de prose. Sous la frise, une ligne dit
   lesquels des formats n'ont JAMAIS été joués sur papier, calculée et non écrite en dur.

4. **Deux aperçus** côte à côte, chacun menant à sa page : le champ (les trois premiers
   archétypes, composant de `/meta/`) et les derniers tournois (trois lignes, avec leur
   concentration affichée comme valeur, jamais comme étiquette).

## Interdits

- Aucun script, aucune sous-ressource externe : les deux sont bannis par le portillon et
  démentiraient la page légale.
- Aucun pourcentage calculé dans le gabarit : `{{ }}` n'évalue pas d'expression, et un
  `calc()` sur une valeur absente échoue en silence — vérifié en production, toutes les barres
  étaient tombées sur leur `min-width`.
- Aucune valeur en dur qu'un build futur rendrait fausse : « trente-sept jours », « OP16.5 et
  OP17 » se calculent.

## Terminé quand

`./orchestration/verify.sh` est vert, et sur le corpus réel la frise montre bien quatre
segments en ligne et deux segments papier suivis d'un vide.

Contrôle visuel obligatoire avant de conclure — c'est une modification d'APPARENCE, et deux
régressions purement visuelles sont passées à travers le texte et les tests sur ce dépôt le
même jour : ouvrir la page déployée en 375 px et en 1440 px et regarder, en contournant le
cache de GitHub Pages (`max-age=600`).

## Sortie attendue

Ce que la frise donne sur le corpus réel (segments, positions), et tout écart constaté entre
la maquette et ce que la donnée permet.
