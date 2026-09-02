# LOT C — `sitegen/packs.py` (modèle → `deckpack.json` dérivés)

## Objectif

Écrire `sitegen/packs.py` : produire les manifestes `deckpack.json` que le simulateur
importera — par tournoi, par archétype de leader, un pack « méta », et un pack par deck.

## Contexte

Tu travailles dans le dépôt courant (`optcgsim-deckpacks-library`, dans l'écosystème optcgsim). Les fichiers que
tu produis sont **le produit réel du site** : ce sont eux que `studio decks import-pack
<url>` consomme. Les pages HTML (lot B) ne sont que leur vitrine.

Lis d'abord, dans cet ordre :

1. `SPEC-site-v1.md` — le contrat. Les sections « Carte des URLs » et « Définition du pack
   méta » te concernent directement.
2. `../optcgsim-deckpacks/SPEC-deckpack.md` — **le format de sortie**, dépôt sibling. À
   respecter à la lettre : c'est un contrat versionné consommé par un autre programme.
3. `AGENTS.md` — les invariants.
4. `sitegen/model.py` — les données que tu consommes (**figé**). `Site.leaders()` fait déjà
   le regroupement par archétype et le tri : ne le réimplémente pas.
5. `tests/test_contract_packs.py` — **ta spécification exécutable**.

## Tâche

Créer `sitegen/packs.py`, exposant :

```python
META_WINDOW_DAYS = 60
META_MAX_DECKS = 40

def meta_pairs(site: Site) -> tuple[tuple[Tournament, Deck], ...]
    """Les decks du pack méta, déjà triés. () si le corpus n'a aucune date."""

def build_pack(name: str, pairs: tuple[tuple[Tournament, Deck], ...],
               author: str = "optcgsim-deckpacks-library") -> dict
    """Manifeste deckpack v1. Chaque entrée utilise `text` inline, jamais `file`/`source_url`."""

def write_packs(site: Site, out: Path) -> list[Path]
    """Écrit tous les packs sous `out`. Renvoie la liste exacte des chemins écrits."""
```

Fichiers à produire (l'ensemble exact est vérifié) :

| Chemin | Contenu |
|---|---|
| `tournaments/<tslug>/deckpack.json` | tous les decks du tournoi, y compris les non parsables |
| `tournaments/<tslug>/decks/<dslug>.json` | un pack d'un seul deck (pour l'import unitaire) |
| `leaders/<aslug>/deckpack.json` | toutes les listes de cet archétype, tous tournois |
| `meta/deckpack.json` | l'instantané du méta courant |

### Nouveaux packs : par format (« la méta »)

Le format d'un tournoi est désormais dans `Tournament.format` / `.format_slug`
(`OP14.5` → `op14-5`), et `Site.formats()` regroupe les tournois par format.

| Chemin | Contenu |
|---|---|
| `formats/<fslug>/deckpack.json` | tous les decks de ce format |
| `leaders/<aslug>/<fslug>.json` | les listes d'un archétype **dans ce format seul** |

N'émets un `leaders/<aslug>/<fslug>.json` que si l'archétype a **au moins une liste** dans
ce format — pas de fichier vide. `Site.leaders(format_slug)` fait déjà le filtrage, ne le
réimplémente pas. Les formats indéterminés (`format_slug == ""`) ne produisent aucun
fichier.

Règles du pack méta — **déterministes, ne jamais utiliser la date du jour** :

- Date de référence = `site.reference_date` (le tournoi le plus récent du corpus).
- **Restreindre aussi à `site.current_format`.** Une fenêtre de dates seule peut chevaucher
  un changement de format et mélangerait alors deux environnements de jeu sans que rien ne
  le signale. Le corpus actuel n'y échappe que par chance.
- Garder les decks des tournois dans les `META_WINDOW_DAYS` jours précédant cette
  référence, avec `placement <= 8` et `deck.parsed` vrai.
- Trier par date de tournoi décroissante puis placement croissant.
- Plafonner à `META_MAX_DECKS`.
- `name` = `f"Méta {ref:%Y-%m}"`, `author` = `"optcgsim-deckpacks-library"`.

Autres contraintes :

- `Deck.text` est réexporté **verbatim**, sans renormalisation : c'est le format natif
  attendu par le simulateur.
- Tout fichier produit doit passer le validateur de la spec :
  `python3 ../optcgsim-deckpacks/scripts/validate.py <dossier-contenant-deckpack.json>`
  (les packs de deck isolé ne s'appelant pas `deckpack.json`, teste-les en copiant le
  fichier sous ce nom dans un dossier temporaire).
- Écriture JSON déterministe : `indent=2`, `ensure_ascii=False`, ordre de clés stable,
  et un `\n` final. Deux exécutions doivent produire des octets identiques.
- Bibliothèque standard uniquement dans ce module.

## Interdits

- Ne modifie **aucun** fichier figé : `SPEC-site-v1.md`, `sitegen/model.py`,
  `sitegen/build.py`, `tests/**`, `orchestration/**`.
- Ne touche pas à `sitegen/parse.py` ni `sitegen/render.py` (autres lots, en parallèle —
  y toucher provoquerait un conflit).
- N'ajoute aucun champ au format `deckpack` : c'est un contrat partagé, versionné dans un
  autre dépôt. Si un champ te manque, dis-le dans ta sortie.
- Ne désactive, ne réécris, ne marque `skip`/`xfail` aucun test. Si un test te paraît faux,
  dis-le dans ta sortie et implémente quand même le reste.
- Aucun accès réseau.

## Terminé quand

```bash
python3 -m pytest -q tests/test_contract_packs.py
```

sort en vert. Lance-le toi-même et itère jusqu'au vert avant de conclure.

## Sortie attendue

Un résumé court : ce que tu as implémenté, le résultat du validateur de la spec sur les
packs produits, et toute divergence constatée.
