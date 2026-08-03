# optcgsim-deckpacks-library — guide agent

Générateur de site statique qui expose les deckpacks scrapés comme **rampe d'accès vers
OPTCGSim**. Le contrat exécutable est [SPEC-site-v1.md](SPEC-site-v1.md) ; les notes
produit sont [IDEAS-library-site.md](IDEAS-library-site.md).

## Rôle dans l'écosystème

| Dépôt sibling | Rôle vis-à-vis d'ici |
|---|---|
| `../optcgsim-deckpacks` | **Spec** du format `deckpack.json` + validateur (arbitre unique) |
| `../optcgsim-deckpacks-data` | **Données** : les packs scrapés, l'entrée du générateur |
| `../optcgsim-studio` | **Consommateur** : `studio decks import-pack <url>` |

Ce dépôt ne définit pas le format et ne scrape rien. Il **rend**.

## Invariants — ne jamais violer

- **Zéro contenu copyright** : uniquement des IDs de cartes, quantités, et méta publique de
  tournoi. Aucun nom de carte, aucun texte de carte, aucune image, aucun asset. Cet
  invariant est ce qui rend le projet publiable ; il n'est pas négociable pour du confort
  d'affichage.
- **Zéro monétisation** : pas de publicité, pas de tracker, pas d'analytics, pas de lien
  d'affiliation. Le projet est une contribution à l'écosystème, pas un produit.
- **Zéro donnée utilisateur** : pas d'auth, pas de compte, pas de cookie, pas de
  formulaire. Il n'y a donc rien à protéger et aucune obligation RGPD.
- **Zéro requête réseau sortante** depuis les pages produites : pas de CDN, pas de police
  distante, pas d'image externe. Un site qui ne parle à personne ne fuit rien.
- **Sortie déterministe** : deux builds sur la même entrée produisent des fichiers
  identiques octet pour octet. Ne jamais utiliser la date du jour, un hash d'itération, ni
  un ordre de `set`/`dict` non trié dans la sortie.
- **Zéro dépendance réseau au build** : le générateur ne fait aucune requête HTTP.

## Fichiers figés (aucun worker ne les modifie)

- `SPEC-site-v1.md` — le contrat
- `sitegen/model.py` — le modèle de données
- `sitegen/build.py` — le câblage CLI
- `tests/test_contract_*.py` — les tests de contrat
- `orchestration/**` — les specs de lots et les scripts de boucle

Un besoin de modifier un fichier figé signale un désaccord avec le contrat : le signaler
en sortie, ne pas contourner.

## Développement

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

.venv/bin/python -m sitegen.build --out dist          # build
.venv/bin/python -m pytest -q                          # tests
./orchestration/verify.sh                              # la définition de « terminé »
python3 -m http.server -d dist 8000                    # prévisualiser
```

## Dépendances

Jinja2 pour le rendu, pytest pour les tests. **Rien d'autre** — pas de framework web, pas
de Node, pas de client HTTP. Toute dépendance supplémentaire doit être justifiée dans la
sortie du worker et validée par l'orchestrateur.
