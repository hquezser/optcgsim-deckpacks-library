# LOT B — `sitegen/render.py` + `sitegen/templates/` (modèle → HTML)

## Objectif

Écrire le rendu HTML statique du site : `sitegen/render.py` et les gabarits Jinja2 de
`sitegen/templates/`, plus la feuille `style.css`.

## Contexte

Tu travailles dans `/Users/hugoq/playground/optcgsim-deckpacks-library`, un générateur de
site statique qui expose des decklists One Piece TCG scrapées de tournois.

Lis d'abord, dans cet ordre :

1. `SPEC-site-v1.md` — le contrat. Les sections « Carte des URLs », « Contenu des pages » et
   « Rendu HTML » te concernent directement.
2. `AGENTS.md` — les invariants (zéro copyright, zéro requête sortante, déterminisme).
3. `sitegen/model.py` — les données que tu consommes (**figé**). Note `Site.sorted_tournaments`,
   `Site.leaders()`, `Site.archetype_label()`, `Deck.slug`, `Deck.archetype_slug` : les
   dérivations et les tris existent déjà, ne les réimplémente pas.
4. `tests/test_contract_render.py` — **ta spécification exécutable**.
5. `sitegen/parse.py` s'il existe déjà (lot A, en amont) — sinon les tests te le fourniront
   via la fixture.

## Le point le plus important

Le site n'existe que pour **une** raison : donner une commande d'import copiable vers
OPTCGSim. Ce bloc doit être l'élément visuellement dominant de chaque page, en haut, dans un
`<pre>`/`<code>` sélectionnable d'un geste :

```
studio decks import-pack https://exemple.org/leaders/purple-enel/deckpack.json
```

Tout le reste de la page est secondaire. Ne l'enterre pas en bas de page ni dans une
barre latérale.

## Tâche

Créer `sitegen/render.py`, exposant :

```python
def write_pages(site: Site, out: Path, base_url: str) -> list[Path]
    """Écrit les pages HTML + style.css sous `out`. Renvoie la liste exacte des chemins écrits."""
```

Pages à produire (et **rien d'autre** — l'ensemble exact est vérifié) :

| Chemin | Contenu |
|---|---|
| `index.html` | 20 tournois les plus récents ; archétypes triés par nombre de listes décroissant ; lien vers `/meta/` |
| `tournois/<tslug>/index.html` | bloc import du pack ; decks par placement croissant (non parsés en fin) ; par deck : placement, archétype, joueur, leader, cartes, et sa commande d'import individuelle |
| `leaders/<aslug>/index.html` | bloc import ; les listes de l'archétype tous tournois confondus, avec **la provenance de chacune** (nom du tournoi + date) |
| `meta/index.html` | bloc import ; composition du pack méta, groupée par archétype |
| `style.css` | une seule feuille, ~200 lignes max |

Les `deckpack.json` sont produits par le lot C — **tu ne les écris pas**, tu pointes vers
leurs URLs.

Contraintes de rendu :

- Jinja2, avec `autoescape=True` (un nom de joueur peut contenir `<`, `&`).
- HTML5 : `<!doctype html>`, `lang`, `<title>`, `<meta name="viewport">`.
- **Zéro sous-ressource externe** : aucun `<script>`, `@import`, `url()`, `src=` ou
  `<link>` pointant hors du `base_url`. Une sous-ressource est chargée automatiquement et
  exposerait l'IP du visiteur à un tiers.
- **En revanche, les liens externes sont exigés** : la `description` d'un pack contient les
  URL de la source (Limitless, ChinoizeCupStats). Rends-les **cliquables**, avec
  `rel="noreferrer nofollow"` et `target="_blank"`. Créditer la source est un choix
  délibéré du projet — c'est ce qui le distingue d'une reprise de données non créditée —
  et `noreferrer`/`nofollow` évitent de lui envoyer le référent du visiteur ou du poids SEO.
  Attention à l'échappement : la description est du texte libre, seule l'URL devient une
  balise, le reste reste échappé.
- Mobile d'abord : une colonne, pas de largeur en pixels figée. Sobre, lisible, sans
  framework CSS.
- **Aucun nom de carte** — uniquement des IDs type `OP15-058`. C'est un invariant légal du
  projet, pas une limite d'affichage à contourner.
- Sortie déterministe : deux appels produisent des octets identiques. Pas d'horodatage
  dans les pages, aucun parcours de `set` non trié.

## Interdits

- Ne modifie **aucun** fichier figé : `SPEC-site-v1.md`, `sitegen/model.py`,
  `sitegen/build.py`, `tests/**`, `orchestration/**`.
- Ne touche pas à `sitegen/parse.py` ni `sitegen/packs.py` (autres lots, en parallèle —
  y toucher provoquerait un conflit).
- Aucune dépendance au-delà de Jinja2. Pas de Node, pas de build CSS.
- Ne désactive, ne réécris, ne marque `skip`/`xfail` aucun test. Si un test te paraît faux,
  dis-le dans ta sortie et implémente quand même le reste.
- Aucun accès réseau.

## Terminé quand

```bash
python3 -m pytest -q tests/test_contract_render.py
```

sort en vert. Lance-le toi-même et itère jusqu'au vert avant de conclure.

## Sortie attendue

Un résumé court : les gabarits créés, les choix de mise en page, et toute divergence entre
la spec et les tests.
