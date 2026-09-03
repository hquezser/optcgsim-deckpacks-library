# SPEC — site bibliothèque v1 (contrat)

Ce document est **le contrat**. Toute implémentation est jugée conforme ou non par
`orchestration/verify.sh`, pas par appréciation. En cas d'ambiguïté entre ce document et
une implémentation, ce document gagne.

## Positionnement (ce qui détermine les arbitrages)

Le site n'est **pas** une bibliothèque de decklists — Limitless fait déjà ça, mieux. C'est
**la rampe d'accès entre le méta compétitif et OPTCGSim**. La seule chose qu'on offre et
que personne d'autre n'offre, c'est une commande d'import en un clic.

Conséquence de design, non négociable : **l'action d'import est l'élément visuel principal
de chaque page**, copiable en un clic. Tout le reste est secondaire.

### Quelle action, selon la page

L'import EN BLOC n'a de sens que si le pack est **varié**. Mesuré sur le corpus :

| Pack | Contenu réel |
|---|---|
| un tournoi | 16 decks → **6 archétypes distincts** |
| le méta | 40 listes, plusieurs archétypes |
| un leader (OP16) | 72 listes → **36 variantes** à ≤ 2 cartes, un seul archétype |
| un format | 507 listes, majoritairement des variantes |

Importer 72 listes Enel remplit le simulateur de decks à deux cartes d'écart : la *page* est
utile pour comparer, l'import en bloc de cette page ne l'est pas.

- **`/tournaments/`** et **`/meta/`** : l'import en bloc est le héros. Le pack est varié, et
  l'importer sert un vrai besoin (s'entraîner contre le méta).
- **`/leaders/`** et **`/formats/`** : le héros est l'action **par deck**. Le pack complet
  reste offert — c'est un inventaire légitime, et son URL est publique — mais **relégué**,
  et accompagné du nombre de variantes réelles pour que le lecteur sache ce qu'il importe.

### Deux façons de prendre un deck seul

Un deck isolé se prend de deux manières, et les deux comptent :

1. **`studio decks import-pack <url>`** vers `/tournaments/<tslug>/decks/<dslug>.json`, comme
   ailleurs sur le site.
2. **Copier/coller la decklist au format natif** du simulateur (`Deck.text` verbatim,
   `1xOP15-058` par ligne). **Ça ne demande AUCUNE installation** — ni studio, ni terminal —
   et c'est ce qui ouvre le site à quiconque joue, pas seulement à qui a outillé sa machine.
   C'est donc un chemin de premier plan, pas un repli.

## Langue du site : anglais

**Le site est en anglais**, `lang="en"`. Décidé le 2026-09-03, et ça remplace la ligne
« hors portée v1 : i18n » ci-dessous : il ne s'agit pas de bilinguisme mais d'une seule
langue, la bonne.

Le raisonnement : **tout le contenu est déjà anglais ou neutre** — identifiants de cartes,
noms de joueurs, noms de tournois (« OP16 26th July 2026 - Treasure Cup Sofia »), et la
commande d'import elle-même. Seule l'interface était en français. Or le public est celui du
Discord OPTCGSim, de Limitless et de ChinoizeCupStats, qui est anglophone. Une version
française servirait une personne, qui connaît déjà le projet.

**La documentation interne reste en français** : cette spec, `AGENTS.md`, les specs de lots,
les messages de commit et la sortie de `verify.sh`. Deux publics différents — les lecteurs du
site et ceux qui travaillent dessus.

### Vocabulaire

Employer les termes du TCG anglophone, pas des traductions littérales :

| Notion | Terme | À éviter |
|---|---|---|
| Cartes communes à ≥ 80 % des listes | **core** | « common core », « base » |
| Cartes qui distinguent une liste du core | **flex** | « delta », « difference », « gap » |
| Une decklist au format du simulateur | **decklist** | « native decklist », « raw » |
| Nombre d'exemplaires d'une carte | `4x` | ne jamais l'appeler « quantity » en toutes lettres |
| Environnement de jeu | **format** | « meta » quand il s'agit du format |
| Le méta courant, comme instantané | **meta** | — |
| Résultat en tournoi | **placement**, `1st` | « rank », « position » |

`flex` est le terme réel : ce sont les emplacements qu'un joueur choisit librement, une fois
le core posé. C'est exactement ce que la vue par écart montre.

## Obligations légales (le site est en ligne)

Le site est publié : les obligations s'appliquent, même sans monétisation et même avec zéro
collecte. Elles sont **du contrat**, pas de la bonne volonté — une page de mentions légales
se perd exactement comme n'importe quel gabarit, et personne ne s'en aperçoit pendant un an.
D'où des tests dédiés dans `tests/test_contract_render.py`.

### `/legal/` — page obligatoire, liée depuis CHAQUE page

Une mention légale qu'on n'atteint qu'en devinant l'URL n'informe personne : le lien est
dans le pied de page commun, donc partout, et un test le vérifie **page par page** (une
profondeur `rel` mal câblée casserait le lien ailleurs que sur l'accueil).

Elle doit porter, faute de quoi le portillon échoue :

| Volet | Contenu exigé |
|---|---|
| Éditeur | Pseudonyme `hquezser`, éditeur non professionnel |
| Hébergeur | **GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107** |
| Contact | Les issues du dépôt — un moyen de contact effectif |
| Droit applicable | Droit français |
| Vie privée | Zéro cookie, zéro script, zéro sous-ressource, zéro mesure d'audience ; et la mention que l'hébergeur journalise les connexions, ce qui n'est pas le fait de l'éditeur |
| Données personnelles | Finalité, base légale (intérêt légitime), minimisation, conservation, **procédure de retrait** |
| Propriété intellectuelle | Aucun contenu de jeu reproduit ; non-affiliation à Bandai ; sources créditées et liées |
| Garantie | Contenu fourni tel quel, sans garantie |

**Pseudonymat de l'éditeur** : la LCEN (art. 6 III-2) l'autorise pour un éditeur non
professionnel dès lors que l'hébergeur détient son identité. C'est le cas. L'identité de
l'**hébergeur**, elle, n'est jamais facultative et doit figurer en toutes lettres.

### Le vrai risque, ce sont les noms de joueurs

755 noms de joueurs distincts sont publiés (dont ~153 ressemblent à des noms civils). C'est
la partie sensible du site — pas les identifiants de cartes, qui ne sont ni protégeables ni
personnels.

Position retenue : **conserver, avec un droit de retrait effectif**. Base légale l'intérêt
légitime — résultats déjà publiés par les organisateurs, finalité limitée à l'import dans le
simulateur, aucune donnée de contact, aucun profil transversal.

### Un retrait doit survivre au scraping

`removals.txt`, à la racine du dépôt **du site** : un nom par ligne, comparaison insensible
à la casse. Tout deck du joueur est écarté à la construction — pages, vues agrégées et
`deckpack.json` compris — et le retrait est tracé dans le rapport de build.

Le placement n'est pas un détail. Honorer la demande dans le dépôt de données seul la
laisserait annuler par la collecte du lendemain : **un retrait que la prochaine exécution
défait n'est pas un retrait**, et la page légale deviendrait une promesse fausse. C'est donc
au point qui décide de ce qui est *publié* que la demande est honorée. L'effacement des
données brutes de `optcgsim-deckpacks-data` (et de son historique git) reste une opération
manuelle distincte, à faire sur demande.

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
^(?P<archetype>.+?)\s+—\s+(?P<player>.+?)\s+\((?P<place>\d+)(?:st|nd|rd|th)?\)$
```

(le séparateur est un tiret cadratin U+2014, entouré d'espaces)

Le suffixe ordinal est **optionnel** : Limitless écrit `(1st)`, ChinoizeCupStats écrit `(1)`.
Exiger le suffixe rendait tout tournoi ChinoizeCup illisible — 0 deck parsé sur 4, donc absent
des pages `/leaders/` et du pack méta. Un suffixe non anglais (`(1er)`) reste non conforme :
le `?` rend le groupe facultatif, pas permissif.

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

**Format (« la méta »)** — `OP15`, `OP16`, `OP16.5`, `OP17`… C'est une propriété du
**tournoi**, pas du deck : tous les decks d'un pack partagent le même environnement de jeu.
Trois sources, dans cet ordre — **une déclaration bat toujours une déduction** :

1. une **déclaration en tête du nom de pack**, sous ses deux formes réelles :
   `"OP14.5 21st March 2026 - Regional Melbourne"` (Limitless, papier) et
   `"[OP17] ChinoizeCup #104 Tuesday"` (ChinoizeCupStats, en ligne). Ancrée en tête, jamais
   cherchée ailleurs dans le nom : un pseudo comme `OP17fan` suffirait sinon à étiqueter un
   tournoi ;
2. à défaut, un **tag** de deck de la forme `op\d+(\.\d+)?` (`op16`, `op14.5`), normalisé en
   majuscules ;
3. à défaut, une **déduction depuis le pool de cartes** (§ « Comment le format évolue »).

`""` si rien ne donne rien. Un format inconnu **exclut** le tournoi des vues par format —
il reste visible sur l'accueil et sur sa propre page : mieux vaut ne pas le classer que le
ranger au hasard.

### Comment le format évolue dans le temps

Le corpus doit suivre le calendrier de sorties sans intervention. Deux cas, et un seul
demande une décision humaine.

**Un nouveau booster est automatique, pour toujours.** `OPnn` ouvre le format `OPnn` : c'est
structurel. OP18 sortira, les tournois qui le jouent se classeront en OP18, les rôles
courant/à venir/passés suivront. Aucune ligne à ajouter nulle part.

**Un format à décimale ne l'est pas**, et ce n'est pas un manque d'effort : ce sont des
starter decks qui l'ouvrent (ST31–ST36 → OP16.5), et rien dans une decklist ne distingue
« ce ST est légal dans le format courant » de « ce ST ouvre le suivant ». Quatre signaux ont
été essayés sur les 134 tournois du corpus et **tous réfutés** :

| Signal essayé | Ce que le corpus répond |
|---|---|
| Dériver le calendrier des tournois qui déclarent | 19/134 déclarent, tous en OP14.5–OP16 : ST01 et EB01 se datent « OP14.5 » |
| Première apparition d'un set | ST14 apparaît le 2026-07-28 — c'est un starter ancien |
| Cohorte (« plusieurs sets le même jour ») | ST35 arrive seul, ST36 seul : vrais sets OP16.5 |
| Taux d'adoption | ST35 (vrai) 0,3 % ; ST14 (bruit) 1,8 % ; EB03 (bruit) 51,8 % |

La raison de fond : **le corpus est un échantillon de decks joués**. L'absence d'un set n'a
jamais voulu dire « pas encore légal », seulement « personne n'a fini en top 16 avec ».

D'où le **monde clos** de `sitegen/formats.py` : plutôt qu'une liste ouverte de sets datés,
où un set absent est muet, on déclare l'inverse — à `CALENDAR_HORIZON`, voici la liste
**complète** des sets non-boosters légaux (`LEGAL_SETS_AT_HORIZON`). Un set hors de cette
liste est donc *nécessairement* postérieur à l'horizon. La détection devient certaine, sans
heuristique.

**Ce qui se passe quand un set nouveau apparaît** : si le tournoi déclare son format, la
déclaration tranche et rien ne change. S'il ne déclare rien, il reste **non classé** et le
build émet un avertissement nommant le set, le nombre de tournois bloqués et la décision à
prendre. Déduire quand même donnerait le format du booster le plus récent, ce qui fondrait
un format neuf dans le précédent — précisément ce qui fabrique un « core » qu'aucun deck
réel ne possède.

La décision humaine tient en une ligne : ces sets ouvrent-ils un format à décimale (les
ajouter à `FORMAT_OF_SET`) ou sont-ils légaux dans le format courant (les ajouter seulement
à `LEGAL_SETS_AT_HORIZON`) ? Puis avancer `CALENDAR_HORIZON`.

Le format est la condition de justesse de toute vue agrégée. Un cœur commun calculé sur
deux formats mélangés décrit un deck qui n'a jamais existé : mesuré sur le corpus,
`green-mihawk` et `red-blue-ace` affichaient un cœur de 6 et 10 cartes qui disparaissait
entièrement dès qu'on restreignait au format dominant.

**Slug** (fonction unique, réutilisée partout) : minuscules, toute suite de caractères
non alphanumériques → `-`, tirets de tête/queue retirés.
`"Purple Enel"` → `op15-058` (Purple Enel) · `"Red/Black Koby"` → `red-black-koby` ·
`"Marc@@@1"` → `marc-1`.

**Slug de deck** : `f"{placement:02d}-{slug(archetype)}-{slug(player)}"`.
Si `placement is None` : `f"xx-{slug(raw_name)}"`.

## Carte des URLs (contrat exact)

```
/index.html                                    tournois récents + formats + index des leaders
/tournaments/<tslug>/index.html                   un tournoi : ses decks
/tournaments/<tslug>/deckpack.json                le pack complet du tournoi
/tournaments/<tslug>/decks/<dslug>.json           un deck seul, en pack d'un élément
/formats/<fslug>/index.html                    les archétypes d'un format (« la méta »)
/formats/<fslug>/deckpack.json                 pack : tout ce format
/leaders/<aslug>/index.html                    les listes de cet archétype, par format
/leaders/<aslug>/deckpack.json                 pack : toutes ses listes, tous formats
/leaders/<aslug>/<fslug>.json                  pack : ses listes dans ce format seul
/meta/index.html                               instantané du méta courant
/meta/deckpack.json                            pack : le méta courant
/style.css                                     feuille unique
/favicon.svg                                   icône de site (seul asset, cf. « Icône de site »)
```

`<fslug>` est le format slugifié (`OP14.5` → `op14-5`). Seuls les formats connus produisent
des fichiers ; un `<aslug>` n'a de `<fslug>.json` que pour les formats où il a au moins une
liste.

Aucune autre URL. Pas de `404.html`, pas de sitemap en v1.

Tout `deckpack.json` émis doit passer `../optcgsim-deckpacks/scripts/validate.py`.

### Définition du pack « méta »

Déterministe et testable — **ne pas utiliser la date du jour** :

- Date de référence = date du tournoi le plus récent du corpus.
- **Restreindre au format courant** (`Site.current_format`) en plus de la fenêtre de dates.
  Une fenêtre seule peut chevaucher un changement de format : elle mélangerait alors deux
  environnements en silence. Le corpus actuel n'y échappe que par chance.
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

**`--base-url` ne sert QU'À la commande d'import affichée.** Tous les liens internes et
toutes les ressources (feuille de style comprise) sont **relatifs au document**, jamais
absolus. Sinon `dist/` ne fonctionne que servi depuis l'URL exacte du build : changer de
domaine, déployer dans un sous-chemin — ce que fait GitHub Pages pour un dépôt de projet —
ou ouvrir un fichier en `file://` casse tout, feuille de style incluse. Le relatif au
document (et non à la racine) est le seul qui survive aux trois cas.

**La commande doit être lisible et sélectionnable en entier, sans scroll horizontal.** Mesuré
en mobile 375 px, elle était tronquée à 65 % derrière une barre de défilement de quelques
millimètres — le seul élément qui justifie le site était donc inutilisable. Le contrat exige
donc : retour à la ligne (`pre-wrap` + coupure de mot) pour que tout soit visible, et
`user-select: all` pour qu'un clic unique sélectionne la commande entière. Sans JS : c'est
le CSS qui fournit le geste de copie.

Le bloc mentionne **optcgsim-studio par un lien** : un visiteur qui découvre le site ne sait
pas ce qu'est cette commande ni où obtenir l'outil qui l'exécute.

- **`/`** : les formats en tête, **groupés par rôle** — c'est le premier repère qu'un joueur
  cherche. Puis les 20 tournois les plus récents (nom, date, **format**, nombre de decks,
  lien) ; puis les archétypes avec leur nombre de listes, décroissant ; et un lien vers
  `/meta/`.

### Rôles de format : courant, à venir, passés

Le simulateur reçoit les sets avant le circuit papier, donc un format peut déjà être joué en
ligne quand les tournois papier en sont encore au précédent — et il peut y en avoir
**plusieurs** en avance à la fois (OP16.5 puis OP17).

- **courant** = `Site.current_format`. **Le circuit papier donne l'heure tant qu'il n'a pas
  été doublé.** Pas « le format du tournoi le plus récent » : le tournoi le plus récent est
  presque toujours en ligne et en avance, et cette définition-là vidait « à venir » de sa
  substance en effaçant le décalage qu'elle devait montrer.
- **à venir** = `Site.upcoming_formats`, tous les formats postérieurs au courant, du plus
  proche au plus lointain. **Peut être vide**, et le rendu doit le supporter.
- **passés** = `Site.past_formats`, du plus récent au plus ancien.

#### Quand le papier se fait doubler

S'accrocher au papier sans condition produit le défaut inverse, mesuré au 2026-09-03 :
« courant » affichait OP16, dont le dernier tournoi datait de 38 jours, et rangeait sous
« à venir » un OP16.5 **déjà terminé** (15 juillet – 12 août) à côté d'un OP17 joué la
veille. Le site annonçait comme courant un format que plus personne ne jouait, et comme à
venir un format déjà passé.

D'où `PAPER_LAG_MAX = 1` : le papier reste la référence tant qu'il n'a **qu'un** format de
retard — le décalage normal, celui autour duquel le site est bâti. Doublé de **deux**, il a
été dépassé (un format entier est né et mort en ligne sans lui) et le relais passe au format
effectivement joué.

**Le retard se compte en formats, jamais en jours.** Un seuil de fraîcheur a été essayé et
rejeté : sur le corpus réel, le circuit papier a connu 49 jours sans tournoi *en pleine
saison* (2026-05-02 → 2026-06-20), soit plus que les 37 jours de la pause qu'on cherchait à
détecter. Aucun seuil temporel ne sépare « entre deux week-ends » de « à l'arrêt ».

Quand le courant vient du circuit en ligne (`Site.current_format_circuit == "online"`),
l'index **et** la page du format doivent l'annoncer et dire où en est le papier — sinon un
joueur qui prépare un regional construit pour un format qu'aucune table n'a encore joué.
En régime normal, aucune mention : la banaliser reviendrait à ce que personne ne la lise.

Ce sont des **rôles, pas des identités** : les formats gardent leurs codes réels (`OP16`,
`OP16.5`, `OP17`) et leurs URLs `/formats/<fslug>/`. On annote, on ne renomme jamais — et on
n'invente aucune URL du type `/formats/a-venir/`.

Chaque page `/formats/<fslug>/` annonce son propre rôle : un visiteur qui y arrive
directement doit savoir s'il regarde le méta courant ou un méta à venir.
- **`/tournaments/<tslug>/`** : bloc import du pack complet. Puis les decks triés par
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

### Regroupement des listes quasi-identiques

Troisième catégorie, distincte des deux ci-dessous : des listes **différentes**, séparées
d'un seul échange. Sur le corpus, 75 % des 106 listes `Purple Enel` OP16 sont à un échange
près d'une autre. La page les alignait, puis tronquait le surplus — à la fois répétitive et
incomplète.

**L'unité est l'échange, pas un seuil réglé.** Deux decks légaux ont 50 cartes : la distance
en cartes est donc toujours paire, et sa moitié est le nombre d'échanges (retirer un
exemplaire, en ajouter un autre). `MAX_SWAPS = 1` est la plus petite modification qu'un
joueur puisse faire. Cette propriété était nécessaire, parce que **les données n'offrent
aucun seuil naturel** : la distribution des distances par paires est unimodale et lisse, avec
un pic autour de 8 à 10 cartes d'écart, sans aucun creux où poser une frontière.

**Liaison complète, jamais chaînage.** Une liste ne rejoint un groupe que si elle est à
≤ 1 échange de **toutes** ses membres, donc le diamètre du groupe est borné par
construction — et la promesse faite au lecteur est vraie de n'importe quelle paire qu'il
compare. Le chaînage (A~B et B~C ⇒ A,B,C) a été essayé et réfuté : il réunissait 58 des 106
listes `Purple Enel` OP16 dans une grappe de **5 échanges de diamètre**.

Le partitionnement glouton n'est pas canonique — un autre ordre donnerait d'autres groupes,
tous valides. L'ordre est donc fixé : **meilleur placement d'abord**, ce qui rend la sortie
déterministe et donne à chaque groupe le meilleur résultat pour représentant.

**Un groupe doit dire QUEL échange le distingue.** Annoncer « un échange » sans nommer les
cartes ferait disparaître de la page celles qui n'appartiennent qu'à un membre : c'est de
l'information perdue, pas de la compression. Chaque membre affiche donc son écart carte par
carte, l'entrant et le sortant distingués visuellement.

**Le plafond d'affichage se compte en groupes** (`LEADER_GROUPS_CAP = 24`), plus en listes.
Le poids d'une page est porté par les decklists affichées, pas par les noms de joueurs :
30 listes identiques ne coûtent qu'une decklist. Ce qui reste hors page se compte en
**listes**, parce que c'est ce que le lecteur perd. Mesuré en changeant de règle : +7 % de
poids sur les pages `/leaders/`, +1 % sur le site entier, et **270 listes qui étaient
purement et simplement jetées redeviennent visibles**.

Quand un groupe est identique, c'est la mention de convergence qui l'annonce (« N players run
this list ») et non la puce de groupe : ce qui compte n'est pas que les listes coïncident,
c'est que des joueurs **différents** y soient arrivés. On ne le dit qu'une fois.

### Redondance et convergence

Les coupes en ligne sont **quotidiennes**, et un joueur assidu y rejoue sa liste jour après
jour. Deux situations que la ressemblance des listes confond, et qu'il faut séparer :

- **Redondance** — *même joueur, même liste.* Aucune information nouvelle. `Site.leaders()`
  **déduplique** par (joueur, signature) en gardant l'occurrence la plus récente. Sans cela
  un joueur pèserait autant de fois dans le cœur commun : mesuré sur le corpus, 221 entrées
  redondantes, un joueur à 39 entrées, et **18 groupes agrégés sur 48 dont le cœur change**
  une fois la déduplication faite. C'est une correction de justesse, pas d'encombrement.
- **Convergence** — *joueurs différents, même liste.* C'est le signal le plus fort qu'une
  liste est résolue, et chacun garde sa voix : jamais dédupliqué. 96 listes partagées sur le
  corpus, couvrant 13 % des entrées, avec des cas jusqu'à neuf joueurs.

La page `/leaders/` **annonce** la convergence (« N joueurs jouent cette liste ») plutôt que
d'aligner des entrées identiques : plus informatif et plus court à la fois.
`Site.converging_players(aslug, fslug)` la fournit.

La **quasi**-similarité n'est jamais dédupliquée : à quelques cartes d'écart, deux listes
diffèrent réellement, et la vue par écart existe précisément pour le montrer.

### Affichage des cartes

Les cartes d'un deck sont affichées **triées par quantité décroissante, puis par identifiant**.
L'ordre du fichier source empêchait de comparer visuellement deux listes d'un même
archétype, ce qui est précisément l'usage d'une page `/leaders/`. Les 4-of remontent en tête :
c'est la colonne vertébrale du deck.

Ce tri est **d'affichage uniquement**. `Deck.text` et les `deckpack.json` produits
conservent l'ordre source verbatim — c'est un contrat de données consommé par un autre
programme.

#### Lien par carte (optionnel, désactivé par défaut)

`--card-link-base <gabarit>`, où `<gabarit>` contient `{id}` : chaque identifiant de carte
affiché devient un lien vers `<gabarit>` avec `{id}` remplacé par l'ID (`OP15-061`).

- **Drapeau absent = comportement d'avant l'amendement du 2026-09-03.** La puce reste un
  `<code>` nu et la sortie est identique octet pour octet. C'est le défaut, CI incluse.
- **Seul l'identifiant est lié, pas la quantité.** La quantité n'appartient pas à la carte,
  et la puce doit continuer de distinguer les deux (cf. « Registre visuel »).
- Chaque lien porte `rel="noreferrer nofollow"` et `target="_blank"`, comme l'attribution
  de source.
- Le gabarit doit être une URL absolue `http(s)://` contenant `{id}`. Il ne doit contenir
  aucun des motifs interdits par `check_dist.py` — `cdn.` notamment, qui est cherché comme
  simple sous-chaîne sur toute la page.
- **Le libellé reste l'ID.** Aucun nom de carte n'entre dans le HTML : c'est la page cible
  qui nomme la carte.

Cible retenue : `https://onepiece.limitlesstcg.com/cards/{id}`. C'est déjà la source amont
que le site crédite, la page y nomme et illustre la carte légalement, et sa durabilité ne
repose pas sur un service personnel. Le gabarit étant un paramètre, en changer n'est pas
une modification de code.

**Coût mesuré, à connaître avant d'activer** : sur le corpus réel la page la plus lourde
(`/leaders/op14-020/`) porte 1066 puces pour 248 Ko ; les liens y ajoutent ~90 Ko, soit
+36 %. C'est précisément la raison pour laquelle le drapeau est opt-in et non le défaut —
le plafond de 24 listes par section existe déjà parce qu'une page d'un demi-mégaoctet est
illisible en mobile.

### Accords et redites

- **Aucun pluriel parenthésé** (`carte(s)`, `liste(s)`, `tournoi(s)`…). Le nombre est
  toujours connu au moment du rendu : accorder est gratuit, et laisser le lecteur choisir
  n'est pas du français. Il y en avait 1705 sur le corpus réel.
- **Le compte d'écart d'une liste est annoncé une seule fois**, dans son résumé — c'est le
  seul endroit qui reste visible quand la liste est repliée. Le titre qui le répétait juste
  en dessous est supprimé.

### Placement

Rendu en texte simple contigu (`1st`, `2nd`, `11th`), **sans `<sup>`** : la mise en exposant
produisait un espace visible (« 1 st ») qui se lit comme une coquille.
- **`/formats/<fslug>/`** : bloc import du format entier. Puis ses archétypes triés par
  nombre de listes décroissant, avec le nombre de tournois couverts et la période.
  C'est l'équivalent statique du sélecteur de méta des sites de référence.
- **`/leaders/<aslug>/`** : bloc import. Puis **une section par format**, du plus récent au
  plus ancien, chacune avec son propre cœur commun, ses écarts et sa propre commande
  d'import (`<fslug>.json`). Les listes y sont triées par date décroissante puis placement ;
  chaque entrée indique son tournoi.

  Le cloisonnement par format est une exigence de **justesse**, pas de présentation :
  agréger deux formats fabrique un cœur qui ne correspond à aucun deck réel.

  **Au plus 24 listes affichées par section de format**, les plus récentes d'abord, avec le
  nombre d'omises indiqué. Sur le corpus réel un archétype atteint 234 listes, soit une page
  de plus d'un demi-mégaoctet — illisible et lente en mobile. Le cœur commun et les écarts
  restent calculés sur **toutes** les listes, et le `deckpack.json` en contient toujours
  l'intégralité : c'est un plafond d'affichage, pas de données.

### Identité d'un archétype

Le slug d'archétype est **l'identifiant de la carte de leader** (`op16-022`), jamais un nom.
Les sources ne nomment pas pareil : ChinoizeCupStats écrit « Monkey D. Luffy », qui recouvre
au moins dix cartes de leader distinctes, là où Limitless écrit « Green/Blue Luffy ».
Regrouper sur le nom mélangeait 271 listes sans rapport ; l'ID sépare ce qui doit l'être et
**réunit les deux sources** sur la même carte.

Le libellé affiché reste le nom lisible, choisi parmi ceux des sources en préférant le
circuit papier (« Green/Blue Luffy » décrit le deck, « Monkey D. Luffy » le personnage).
- **`/meta/`** : bloc import. La composition du pack méta, groupée par archétype.

Pas de nom de carte affiché — **uniquement des IDs**. C'est un invariant, pas un manque
(cf. `AGENTS.md`).

## Registre visuel

**Sombre par défaut, néon discret.** Le public est celui d'OPTCGSim, et le produit est une
commande : le site doit ressembler à un outil de joueur, pas à une publication.

- **Fond sombre en défaut**, pas seulement sous `prefers-color-scheme: dark`. Un thème clair
  reste servi à qui le demande explicitement.
- **Accents saturés mais parcimonieux** : la couleur signale, elle ne décore pas. Réservée
  aux liens, au placement de tête et à la mise en valeur de la commande.
- **Le bloc d'import est traité comme un terminal** : surface sombre distincte, marqueur de
  prompt, police à espacement fixe. C'est une commande shell ; la faire ressembler à autre
  chose brouille le seul message du site.
- **Chiffres tabulaires** (`font-variant-numeric: tabular-nums`) partout. Le site est rempli
  de `4x`, `50/50`, `234 listes` : sans cela, rien ne s'aligne et l'ensemble paraît bâclé.
- **La puce de carte distingue la quantité de l'identifiant.** Un 4-of doit se lire comme la
  colonne vertébrale du deck, et une quantité inhabituelle (les cartes sans limite se jouent
  à 8 ou 9) doit sauter aux yeux — c'est de l'information, pas du décor.
- **Le placement de tête est distingué** discrètement (poids, teinte), le reste reste calme :
  une page de 16 decks doit se parcourir des yeux.

Pas de codage couleur par archétype : seuls 21 des 62 libellés portent une couleur (les
autres viennent de ChinoizeCupStats, qui nomme par personnage), et un accent qui ne
fonctionne qu'au tiers est pire que pas d'accent.

### Icône de site

`favicon.svg`, écrit à la main, servi depuis le même domaine. **Seule exception à
« aucun asset »**, et elle est délibérée : l'invariant vise les assets de CARTES sous
copyright, pas une icône de projet. Aucun contenu tiers, aucune requête externe.

## Rendu HTML

Jinja2, gabarits dans `sitegen/templates/`. HTML5 valide, une seule `style.css`, lisible
en mobile (une colonne, pas de largeur fixe). Sobre : pas de framework CSS, pas de police
distante, pas de requête réseau sortante depuis les pages produites.

## CLI

```bash
python3 -m sitegen.build --packs-dir ../optcgsim-deckpacks-data/packs \
                         --out dist --base-url https://exemple.org

# avec le lien par carte (opt-in, cf. § « Lien par carte »)
python3 -m sitegen.build --out dist --base-url https://exemple.org \
                         --card-link-base 'https://onepiece.limitlesstcg.com/cards/{id}'
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
