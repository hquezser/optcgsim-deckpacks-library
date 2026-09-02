# LOT B — `sitegen/render.py` + `sitegen/templates/` (modèle → HTML)

## Objectif

Écrire le rendu HTML statique du site : `sitegen/render.py` et les gabarits Jinja2 de
`sitegen/templates/`, plus la feuille `style.css`.

## Contexte

Tu travailles dans le dépôt courant (`optcgsim-deckpacks-library`, dans l'écosystème optcgsim), un générateur de
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
studio decks import-pack https://exemple.org/leaders/op15-058/deckpack.json
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
| `tournaments/<tslug>/index.html` | bloc import du pack ; decks par placement croissant (non parsés en fin) ; par deck : placement, archétype, joueur, leader, cartes, et sa commande d'import individuelle |
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

## Plafond d'affichage et identité par ID de leader (tests rouges)

Le corpus a été élargi à **114 tournois et 1823 listes**, ce qui change les ordres de grandeur.

1. **Au plus 24 listes affichées par section de format**, les plus récentes d'abord, en
   indiquant combien sont omises et le total réel. Un archétype atteint 234 listes, soit une
   page de plus d'un demi-mégaoctet : illisible et lente en mobile. Le cœur commun et les
   écarts restent calculés sur **toutes** les listes, et le `deckpack.json` en contient
   toujours l'intégralité — c'est un plafond d'affichage, pas de données.

2. **L'identité d'un archétype est désormais l'ID de la carte de leader** (`op16-022`), plus
   un nom. `Deck.archetype_slug` le fournit déjà, et `Site.archetype_label(aslug)` donne le
   libellé lisible à afficher. Continue d'afficher le libellé, jamais le slug brut, sauf là
   où une URL est attendue.

3. **Affiche le circuit** (`Tournament.circuit` / `.is_online`) sur les entrées de tournoi et
   de liste : 100 des 114 tournois sont des coupes en ligne, 14 des tournois papier. La
   provenance n'a pas la même valeur de preuve dans les deux cas, et le lecteur doit pouvoir
   la distinguer d'un coup d'œil.

## Accords et redites (tests rouges)

1. **Supprime tous les pluriels parenthésés** — `carte(s)`, `liste(s)`, `deck(s)`,
   `tournoi(s)`, `format(s)`, `autre(s)`, `sélectionnée(s)`. Il y en a 1705 sur le corpus
   réel. Le nombre est toujours connu au rendu : accorde-le. Un filtre Jinja unique est
   préférable à des `{% if %}` dispersés — attention à « tournoi » → « tournois ».

2. **Le compte d'écart d'une liste ne doit être annoncé qu'une fois.** Il figure aujourd'hui
   dans le résumé (`3 d'écart`) *et* en titre juste en dessous (`3 carte(s) d'écart`).
   Garde-le dans le **résumé**, qui reste visible quand la liste est repliée, en l'accordant
   (« 3 cartes d'écart », « 1 carte d'écart »), et supprime le titre.

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

## Habillage : registre « outil de joueur » (tests rouges)

Le site est propre mais plat — il ressemble à un bon document technique, pas à un produit.
Le public est celui d'OPTCGSim et le produit est **une commande** : le registre visé est
celui d'un outil de joueur, proche d'un terminal, pas celui d'une publication.

Lis d'abord la section « Registre visuel » de `SPEC-site-v1.md`, qui fait foi.

1. **Fond sombre PAR DÉFAUT**, pas seulement sous `prefers-color-scheme: dark`. Un thème
   clair reste servi à qui le demande explicitement (`prefers-color-scheme: light`).
2. **Chiffres tabulaires** (`font-variant-numeric: tabular-nums`) partout. Le site est
   rempli de `4x`, `50/50`, `234 listes` : sans largeur fixe, rien ne s'aligne.
3. **Le bloc d'import traité comme un terminal** : surface sombre distincte, police à
   espacement fixe, et un **marqueur de prompt injecté en CSS** (`::before { content: "$" }`)
   — jamais dans le HTML, sinon il serait copié avec la commande et la casserait.
4. **La puce de carte distingue la quantité de l'identifiant** : la quantité dans son propre
   élément, avec une classe (`qty`). Un 4-of doit se lire comme la colonne vertébrale du
   deck, et un `9x` (carte sans limite) doit sauter aux yeux — c'est de l'information.
5. **Le placement de tête est distingué** discrètement, via une classe stylée (`rank`,
   `place` ou `podium`) ; le reste reste calme.
6. **`favicon.svg`, écrit à la main**, référencé en relatif sur toutes les pages. Aucune
   référence externe dedans. C'est la seule exception à « aucun asset », et elle est
   assumée : l'invariant vise les assets de CARTES, pas une icône de projet.
7. **Corrige la duplication de libellé de source** : « Source : Limitless · Limitless ». Deux
   URL d'un même domaine donnent deux fois le même libellé, ce qui ressemble à un bug.
   Distingue-les (par exemple par leur rôle : le listing et le tournoi) ou n'en garde qu'une.

Accents saturés mais **parcimonieux** : la couleur signale, elle ne décore pas. Pas de
codage couleur par archétype — seuls 21 des 62 libellés portent une couleur, et un accent
qui ne marche qu'au tiers est pire que pas d'accent.

## Annoncer la convergence (test rouge)

Sur une page `/leaders/`, plusieurs joueurs jouent parfois la **même liste au caractère
près**. C'est le signal le plus fort qu'une liste est résolue — jusqu'à neuf joueurs sur le
corpus réel — et l'annoncer vaut mieux que d'aligner des entrées identiques : plus informatif
et plus court.

`Site.converging_players(aslug, fslug)` renvoie `signature -> (joueurs triés)` pour les seules
listes partagées par au moins deux joueurs. Le modèle fait déjà tout le calcul.

À faire : sur chaque liste concernée, annoncer le partage avec le **nombre de joueurs** et
une classe contenant `converg` (pour le style et pour les tests). Les joueurs restent
**nommés** — on signale le partage, on ne fusionne pas les voix.

Ne pas confondre avec la déduplication, qui est déjà faite dans le modèle et qui porte sur le
cas inverse (même joueur rejouant sa liste). Lis la section « Redondance et convergence » de
`SPEC-site-v1.md`.

## Prendre UN deck, et l'import en bloc remis à sa place (tests rouges)

Mesuré sur le corpus : un tournoi donne 16 decks pour **6 archétypes distincts** — de la
variété, dont l'import en bloc sert un vrai besoin. Une page de leader donne 72 listes pour
**36 variantes réelles** à ≤ 2 cartes, toutes du même archétype : les importer en bloc remplit
le simulateur de decks à deux cartes d'écart. La *page* est utile pour comparer, son import
en bloc non.

Lis la section « Quelle action, selon la page » de `SPEC-site-v1.md`, qui fait foi.

1. **Sur `/leaders/` et `/formats/`, l'action par deck devient le héros.** Chaque liste porte
   sa propre commande, vers `/tournaments/<tslug>/decks/<dslug>.json` — ces packs existent déjà
   (2 059 dans `dist/`), il n'y a rien à générer. Le tournoi de chaque liste est connu :
   `Site.leaders()` renvoie des paires `(Tournament, Deck)`.
2. **L'import en bloc y est RELÉGUÉ**, pas supprimé : le pack complet reste un inventaire
   légitime et son URL est publique. Il doit passer APRÈS les actions par deck, et annoncer
   ce qu'il contient réellement.
3. **Chaque deck offre sa decklist au format NATIF**, copiable d'un geste : `Deck.text`
   verbatim (`1xOP15-058` par ligne, leader compris), dans un bloc de classe contenant
   `natif`, `native` ou `decklist`, avec `user-select: all`.

   **C'est le point le plus important de ce lot** : le copier/coller natif ne demande AUCUNE
   installation — ni studio, ni terminal. Il ouvre le site à quiconque joue, et non
   seulement à qui a outillé sa machine. Traite-le comme un chemin de premier plan, pas
   comme un repli.

   Attention : le texte natif ne doit pas subir le tri d'affichage par quantité. C'est ce
   qu'on colle dans le simulateur, il reste **verbatim**.

## Le site passe en ANGLAIS (tests rouges)

Décision du 2026-09-03 : **le site est en anglais**, `lang="en"`. Ce n'est pas du
bilinguisme — il n'y a qu'une langue, et c'est l'anglais.

Pourquoi : tout le CONTENU l'est déjà (identifiants de cartes, noms de joueurs, noms de
tournois « OP16 26th July 2026 - Treasure Cup Sofia ») et la commande d'import aussi. Seule
l'interface était en français, alors que le public est celui du Discord OPTCGSim, de
Limitless et de ChinoizeCupStats.

**La documentation interne du projet reste en FRANÇAIS** : cette spec, `AGENTS.md`, les
commentaires de code, les messages d'erreur de `verify.sh`. Ne traduis que ce que le
visiteur voit. Deux publics différents.

### Vocabulaire — employer les termes du TCG anglophone

Lis le tableau « Vocabulaire » de `SPEC-site-v1.md`, qui fait foi. L'essentiel :

| Aujourd'hui | Devient | Ne pas écrire |
|---|---|---|
| Cœur commun | **core** | « common core », « base » |
| N cartes d'écart | **N flex** | « delta », « difference », « gap » |
| Decklist native | **decklist** | « native », « raw » |
| Tournois / Méta courant / Formats à venir | Tournaments / Current meta / Upcoming formats | — |
| N joueurs jouent cette liste | N players run this list | — |

`flex` est le terme réel du TCG : les emplacements qu'un joueur choisit librement une fois
le core posé. C'est exactement ce que la vue par écart montre — d'où le choix, plutôt qu'une
traduction littérale de « écart ».

Attention aux **accords** : le filtre de pluriel existant est français (`fr_plur`). En
anglais la règle est différente et bien plus simple ; ne laisse pas de « 1 tournaments » ni
de « card(s) ».

### Écrire en anglais, pas traduire mot à mot

Un test verrouille des tournures relevées sur un rendu réel — ce sont des calques du
français, pas des hypothèses :

| Ne pas écrire | Écrire |
|---|---|
| in one gesture (« en un geste ») | **in one click** |
| is offered (« est offert ») | **is available** |
| native decklist | **decklist** |
| Import to OPTCGSim | **Import into OPTCGSim** |

Plus généralement : relis chaque phrase en te demandant si un joueur anglophone l'écrirait
ainsi. Les tests peuvent passer avec un anglais mot-à-mot, ils ne le rattraperont pas.

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
