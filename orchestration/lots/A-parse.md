# LOT A — `sitegen/parse.py` (corpus scrapé → modèle)

## Objectif

Écrire `sitegen/parse.py` : lire les `deckpack.json` scrapés d'un dossier et les convertir
en objets `Site`/`Tournament`/`Deck` définis dans `sitegen/model.py`.

## Contexte

Tu travailles dans `/Users/hugoq/playground/optcgsim-deckpacks-library`, un générateur de
site statique qui expose des decklists One Piece TCG comme rampe d'accès vers le
simulateur OPTCGSim.

Lis d'abord, dans cet ordre :

1. `SPEC-site-v1.md` — le contrat. La section « Règles de parsing » te concerne directement.
2. `AGENTS.md` — les invariants du projet.
3. `sitegen/model.py` — les dataclasses à produire (déjà écrites, **figées**).
4. `tests/test_contract_parse.py` — **ta spécification exécutable**. Chaque test y décrit un
   comportement attendu, cas limites inclus.
5. `tests/fixtures/packs/` — le corpus de test.

Le format d'entrée est spécifié dans `../optcgsim-deckpacks/SPEC-deckpack.md` (dépôt
sibling). Le vrai corpus est dans `../optcgsim-deckpacks-data/packs/`.

## Tâche

Créer **uniquement** `sitegen/parse.py`, exposant :

```python
def parse_deck_name(name: str) -> tuple[str, str, int | None]
    """-> (archétype, joueur, placement). ("", "", None) si non conforme. Jamais d'exception."""

def parse_text(text: str) -> tuple[str, tuple[tuple[str, int], ...]]
    """-> (leader_id, ((card_id, qty), ...)). Le leader est la 1re ligne, exclu des cartes."""

def load_site(packs_dir: Path) -> Site
    """Lit packs_dir/*/deckpack.json -> Site. Lève OSError/ValueError si un pack est illisible."""

def parse_format(pack_name: str, tags: tuple[str, ...]) -> str
    """Le format (« la méta ») du tournoi : « OP16 », « OP14.5 »… "" si indéterminable."""
```

### Extraction du format (nouveau)

Le format est une propriété du **tournoi** — tous les decks d'un pack partagent le même
environnement. `load_site` doit renseigner `Tournament.format`. Deux sources, dans cet ordre :

1. le **préfixe du nom de pack** : `"OP14.5 21st March 2026 - Regional Melbourne"` → `OP14.5`.
   C'est la source primaire, elle porte la casse et le point ;
2. à défaut, un **tag** de deck de la forme `op\d+(\.\d+)?` (`op16`, `op14.5`), à normaliser
   en majuscules. Prends les tags du premier deck qui en porte un.

`""` si aucune ne donne rien. Attention au piège réel : les tournois ChinoizeCupStats
portent un tag `op` **nu**, qui ne désigne aucun format — il ne doit pas matcher. Ne devine
jamais un format : un tournoi non classé est préférable à un tournoi mal classé.

Points d'attention, tous couverts par les tests :

- Le séparateur du nom de deck est un **tiret cadratin U+2014** (`—`), pas un tiret court.
  Un tiret court doit être traité comme non conforme.
- Le **suffixe ordinal du placement est optionnel** : Limitless écrit `(1st)`,
  ChinoizeCupStats écrit `(1)`. Les deux doivent parser. Exiger le suffixe rendait tout
  tournoi ChinoizeCup illisible (0 deck parsé sur 4). Attention à ne pas devenir permissif
  pour autant : `(1er)` reste non conforme.
- Le slug de tournoi est **le nom du dossier**, pas un champ du manifeste. La date se
  déduit d'un préfixe `AAAA-MM-JJ` sur ce slug ; `None` s'il n'y en a pas.
- Un nom de deck non parsable ne fait **jamais** échouer le chargement : le deck est
  conservé avec `raw_name` verbatim et des champs vides. Il reste visible sur la page de
  son tournoi.
- `text` est conservé **verbatim** dans `Deck.text` : c'est cette chaîne qu'on réexporte
  telle quelle dans les packs dérivés, elle ne doit pas être normalisée.
- Si la quantité de la première ligne n'est pas `1`, ajouter un `BuildWarning` au `Site`
  (le leader est censé être en tête) — sans échouer.
- Sortie **déterministe** : trier explicitement tout parcours de dossier, ne jamais
  dépendre de l'ordre de `os.listdir` ou d'un `set`.
- Bibliothèque standard uniquement dans ce module.

## Interdits

- Ne modifie **aucun** fichier figé : `SPEC-site-v1.md`, `sitegen/model.py`,
  `sitegen/build.py`, `tests/**`, `orchestration/**`.
- N'ajoute aucune dépendance.
- Ne désactive, ne réécris, ne marque `skip`/`xfail` aucun test. Si un test te paraît faux,
  **dis-le dans ta sortie** et implémente quand même le reste.
- Ne crée pas `sitegen/render.py` ni `sitegen/packs.py` (autres lots, en parallèle).
- Aucun accès réseau.

## Terminé quand

```bash
python3 -m pytest -q tests/test_contract_model.py tests/test_contract_parse.py
```

sort en vert. Lance-le toi-même et itère jusqu'au vert avant de conclure.

## Sortie attendue

Un résumé court : ce que tu as implémenté, les décisions non triviales, et toute
divergence que tu as constatée entre la spec, les tests et le corpus réel.
