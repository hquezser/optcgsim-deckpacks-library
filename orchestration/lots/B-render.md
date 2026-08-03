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

## Exigences d'ergonomie (mesurées sur le rendu actuel, à corriger)

Une première version de ce lot est déjà en place et fonctionne. Ces six points viennent
d'un examen du rendu réel en mobile 375 px — chacun a un test qui échoue aujourd'hui.

1. **La commande d'import était tronquée à 65 %** (297 px visibles sur 847 réels) derrière
   une barre de défilement horizontal de quelques millimètres. C'est le seul élément qui
   justifie l'existence du site. Corrige en CSS : retour à la ligne (`pre-wrap` +
   `word-break`) pour que tout soit visible, et **`user-select: all`** pour qu'un clic
   unique sélectionne la commande entière. Sans JS, c'est le CSS qui fournit le geste.
2. **La description brute ne doit plus être affichée** : c'est un champ de métadonnées de
   scraper, il répète le titre et expose des paramètres internes (`region=Europe`,
   `time=3months`) sur cinq lignes. Extrais-en seulement les **URL**, et rends-les en une
   ligne d'attribution compacte. L'attribution reste obligatoire (`rel="noreferrer nofollow"`).
3. **Replie chaque deck dans un `<details>`** avec un `<summary>` portant placement,
   archétype, joueur et leader ; le premier `open`. Une page tournoi faisait **8 écrans** de
   défilement. `<details>` est natif : n'introduis aucun JS.
4. **Trie les cartes par quantité décroissante puis par identifiant** à l'affichage. L'ordre
   du fichier source empêche de comparer deux listes d'un même archétype, ce qui est
   pourtant l'usage d'une page `/leaders/`. **Ce tri est d'affichage uniquement** : ne touche
   pas à `sitegen/packs.py` ni à `Deck.text`, qui sont un contrat de données verbatim.
5. **Lie `optcgsim-studio`** (https://github.com/hquezser/optcgsim-studio) : aujourd'hui
   c'est du texte mort, et un visiteur qui découvre le site ne sait ni ce qu'est cette
   commande ni où obtenir l'outil.
6. **Supprime le `<sup>` du placement** : `1<sup>st</sup>` s'affiche « 1 st » et se lit comme
   une coquille. Rends `1st` en texte contigu.

## Nouveau : le format (« la méta ») comme axe de navigation

Tous les sites de référence (onepiecetopdecks, chinoizecupstats, limitless) offrent un
sélecteur de méta : `OP15`, `OP16`, `OP16.5`, `OP17`. C'est le premier repère qu'un joueur
cherche. Sans JS, l'équivalent statique est une rangée de liens.

Le modèle fournit tout : `Tournament.format` / `.format_slug`, `Site.formats()`,
`Site.current_format`, `Site.format_label(fslug)`, et **`Site.leaders(format_slug)`** qui
restreint à un format.

À produire :

- **`/formats/<fslug>/index.html`** : bloc import du format entier
  (`/formats/<fslug>/deckpack.json`, écrit par le lot C), puis les archétypes de ce format
  triés par nombre de listes décroissant. Un archétype absent de ce format n'y figure pas.
- **`/index.html`** : les formats **en tête**, groupés par rôle (voir ci-dessous), avec leur
  nombre de tournois et de listes, chacun lié à sa page. Et le format de chaque tournoi dans
  la liste des tournois.

### Rôles : courant, à venir, passés

Le simulateur reçoit les sets avant le circuit papier : un format peut donc être déjà joué en
ligne quand les tournois papier en sont encore au précédent, et il peut y en avoir
**plusieurs** en avance à la fois (OP16.5 puis OP17). Le modèle les fournit déjà :
`Site.current_format`, `Site.upcoming_formats` (du plus proche au plus lointain) et
`Site.past_formats`.

Groupe-les sous ces trois rôles sur l'accueil, le courant d'abord, puis les à venir, puis les
passés. Et fais annoncer à chaque page `/formats/<fslug>/` son propre rôle — un visiteur qui
y arrive directement doit savoir s'il regarde le méta courant ou un méta à venir.

**Ce sont des rôles, pas des identités.** Les formats gardent leurs codes réels (`OP16`,
`OP16.5`, `OP17`) comme libellés affichés et leurs URLs `/formats/<fslug>/` inchangées.
N'invente aucune étiquette ni aucune URL du type `/formats/a-venir/`, et ne renomme rien.
- **`/leaders/<aslug>/index.html`** : **une section par format**, du plus récent au plus
  ancien. Chaque section a son propre cœur commun, ses propres écarts, et sa propre commande
  d'import pointant `/leaders/<aslug>/<fslug>.json`.

**C'est une exigence de justesse, pas de présentation.** Un cœur commun calculé sur deux
formats mélangés décrit un deck qui n'a jamais existé : mesuré sur le corpus réel,
`green-mihawk` et `red-blue-ace` affichaient un cœur de 6 et 10 cartes qui disparaissait
entièrement dès qu'on restreignait au format dominant. Appelle donc
`archetype.core_cards()` sur `site.leaders(fslug)[aslug]`, **jamais** sur `site.leaders()[aslug]`.

Les tournois de format indéterminé (ChinoizeCupStats aujourd'hui) n'apparaissent dans
aucune page de format. Ils restent visibles sur leur propre page de tournoi et à l'accueil.

## Correctif de portabilité (test rouge)

Les liens internes et la feuille de style sont aujourd'hui **absolus** contre `--base-url`
(`<link rel="stylesheet" href="https://exemple.org/style.css">`). Conséquence : `dist/` ne
fonctionne que servi depuis l'URL exacte du build — changer de domaine, déployer dans un
sous-chemin (ce que fait GitHub Pages pour un dépôt de projet) ou ouvrir un fichier en
`file://` et la feuille de style meurt, le site s'affiche brut.

Rends **relatifs au document** tous les `href`/`src` internes, feuille de style comprise
(`../../style.css` depuis `/leaders/<aslug>/`, etc.). Le relatif au document, et non à la
racine, est le seul qui survive aux trois cas.

`--base-url` ne doit plus servir qu'à **une** chose : l'URL affichée dans la commande
d'import, qui doit rester absolue pour être collable dans un terminal.

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
