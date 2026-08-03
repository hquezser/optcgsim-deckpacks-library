# LOT D — `optcgsim-studio` : accepter une URL de `deckpack.json` nu

## Objectif

Faire fonctionner `studio decks import-pack https://…/deckpack.json` — aujourd'hui seules
les URLs de `.zip` et de dépôt GitHub fonctionnent.

## Contexte

Tu travailles dans `/Users/hugoq/playground/optcgsim-studio`, **un dépôt mature** avec de
l'historique et une suite de tests fournie. Tu es sur la branche `feat/import-pack-json-url`,
créée pour ce lot : reste dessus, ne la fusionne pas, ne touche pas à `main`.

### Le défaut, tracé dans le code

`studio decks import-pack <source>` appelle
`studio/decks/deckpack.py:from_source` → `studio/assets/packlib.py:ingest`.

Pour une URL `http(s)`, `ingest` fait :

```python
zpath = work_dir / "download.zip"       # nom en dur, quelle que soit la source
url = _resolve_url(s)
_download(url, zpath, ...)
out, corrupted = _materialize(zpath, work_dir / "extracted", None, on_progress)
```

Et `_materialize` (`packlib.py:249`) ne dézippe que si `zipfile.is_zipfile()` est vrai ;
sinon il copie le fichier sous `orig_name or archive.name` — c'est-à-dire `download.zip`.
Ensuite `deckpack.py:find_manifest` cherche `deckpack.json` à la racine ou à un niveau
d'emballage, ne le trouve pas, et lève `DeckPackError`.

Autrement dit : le cas le plus évident pour un utilisateur — coller l'URL du `deckpack.json`
qu'il voit dans son navigateur — échoue avec un message trompeur.

## Tâche

Faire en sorte qu'une URL http(s) désignant un `deckpack.json` (ou tout JSON) soit
matérialisée sous le nom `deckpack.json`, pour que `find_manifest` le trouve.

Approche attendue : la plus petite modification qui traite le cas général, dans `ingest`
et/ou `_materialize`. Détecte le JSON de façon robuste — pas seulement sur l'extension de
l'URL (une URL peut porter une query string, ou servir du JSON sans extension). Les
signaux disponibles : le `Content-Type` de la réponse, l'extension du chemin de l'URL, et
le premier octet non blanc du fichier téléchargé (`{`).

Le comportement existant ne doit pas bouger d'un iota : les URLs de `.zip`, de dépôt
GitHub, de Google Drive et de Dropbox, ainsi que les dossiers et `.zip` locaux, continuent
de fonctionner exactement comme avant.

Ajoute des tests dans `tests/test_packlib.py` (et `tests/test_deckpack.py` si le
comportement bout-en-bout s'y prête), en suivant les conventions de test déjà en place dans
ces fichiers — notamment la façon dont le réseau est simulé. **N'introduis aucun test qui
touche le réseau réel** : `tests/test_no_external_deps.py` existe et le projet y tient.

## Interdits

- Ne quitte pas la branche `feat/import-pack-json-url`. Ne fusionne rien, ne pousse rien.
- N'ajoute aucune dépendance : le projet est en bibliothèque standard pour cette couche.
- Ne refactore rien au-delà du nécessaire. Ce dépôt a de l'historique ; un diff large sera
  rejeté même s'il est vert.
- Ne modifie ni ne supprime aucun test existant. S'il en échoue un, c'est ta modification
  qui est en cause.
- Aucun accès réseau dans les tests.

## Terminé quand

```bash
python3 -m pytest -q tests/test_packlib.py tests/test_deckpack.py
```

sort en vert — **et** la suite complète reste verte :

```bash
python3 -m pytest -q
```

Lance les deux toi-même et itère jusqu'au vert avant de conclure.

## Sortie attendue

Le diff que tu as appliqué (`git diff main...HEAD`), la stratégie de détection du JSON que
tu as retenue et pourquoi, et la liste des tests ajoutés.
