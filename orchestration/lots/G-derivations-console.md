# LOT G — les dérivations que la refonte Console demande

## Objectif

Trois dérivations manquent au modèle pour que les maquettes Console soient constructibles.
Elles sont **pures, déterministes, sans accès réseau**, et ne changent RIEN au rendu : ce lot
se termine avec le site inchangé octet pour octet et des tests neufs au vert.

## Contexte

`sitegen/model.py` est figé — l'orchestrateur l'amende, aucun worker n'y touche. Ce lot
concerne `sitegen/variants.py`, `sitegen/meta.py` et un nouveau `sitegen/readings.py`.

Le corpus : 134 tournois, 2140 listes, 69 archétypes, 7 formats.

## Tâche

### 1. `timeline()` — les deux circuits dans le temps

Dans `sitegen/readings.py` (nouveau) :

```python
def circuit_timeline(site, days: int = 180) -> dict
```

Pour chaque circuit (`paper`, `online`) et chaque format, la première et la dernière date de
tournoi dans la fenêtre, plus la position en POURCENTAGE de la fenêtre (le gabarit ne peut
pas calculer — pas de JS, et `{{ }}` n'évalue aucune expression).

Renvoie de quoi peindre deux pistes : `{"start": date, "end": date, "tracks": {"paper":
[{fslug, label, from, to, left_pct, width_pct, n}], "online": [...]}, "months": [{label,
left_pct}]}`.

Attendu sur le corpus au 2026-09-01, fenêtre depuis 2026-03-23 : en ligne quatre segments
continus (OP15, OP16, OP16.5, OP17) ; papier deux segments (OP15 le 05-02, OP16 du 06-20 au
07-26) puis rien. Les pourcentages sont arrondis à une décimale, stables d'un build à l'autre.

### 2. `concentration()` — la part du premier archétype d'un tournoi

```python
def concentration(tournament) -> tuple[int, str] | None
```

Part entière du premier archétype parmi les decks PARSÉS, et son slug. `None` en dessous de
`MIN_DECKS_FOR_CONCENTRATION` — à fixer par la mesure, pas au jugé : sur 8 decks, un
archétype à 3 exemplaires fait déjà 38 % sans rien vouloir dire.

Plus `corpus_concentration_median(site) -> int` : la médiane, pour SITUER la valeur. Mesurée
aujourd'hui à 25 %.

### 3. `core_reading()` — la taille du core, et son rang

```python
def core_reading(pairs) -> dict | None
```

`{"core_cards": int, "deck_size": 51, "lists": int, "builds": int}`, ou `None` sous
l'effectif minimum. C'est tout : **aucune étiquette**, aucun jugement. La spec § « Lectures
comparatives » explique pourquoi — les deux distributions sont des continuums sans creux, et
trois seuils ont déjà été réfutés sur ce projet.

Fixer l'effectif minimum PAR LA MESURE et le justifier en commentaire : le cas
`Marshall.D.Teach / OP14` (core 51 sur 6 listes) doit tomber en dessous.

## Interdits

- Toute étiquette qualitative dérivée d'un seuil (« solved », « warped », « unsettled »).
- Toute modification de `render.py`, des gabarits ou de `packs.py` : ce lot ne rend rien.
- Toute dépendance nouvelle, tout accès réseau, toute dépendance à `date.today()`.

## Terminé quand

```bash
python3 -m pytest -q
./orchestration/verify.sh
```

sortent en vert, ET `git diff --stat dist/` est vide après reconstruction : le site ne bouge
pas encore.

## Sortie attendue

Les trois seuils d'effectif retenus, avec la mesure qui les justifie, et la liste des cas du
corpus réel qui tombent en dessous.
