# LOT F — lien par carte (`sitegen/render.py` + gabarits)

## Objectif

Rendre chaque identifiant de carte affiché cliquable **quand et seulement quand** le
drapeau `--card-link-base` est passé. Sans le drapeau, la sortie doit rester identique
octet pour octet à celle d'aujourd'hui.

## Contexte

Tu travailles dans `optcgsim-deckpacks-library` (écosystème optcgsim), un générateur de
site statique qui expose des decklists One Piece TCG comme rampe d'accès vers le
simulateur OPTCGSim.

Lis d'abord, dans cet ordre :

1. `AGENTS.md` § « Invariants » — **lis le paragraphe sur le lien par carte en entier.**
   Ce lot est une ouverture *bornée* d'un invariant zéro-copyright, amendée le 2026-09-03.
   Les bornes ne sont pas des préférences de style : elles sont la raison pour laquelle
   l'ouverture est acceptable.
2. `SPEC-site-v1.md` § « Affichage des cartes » → sous-section « Lien par carte » : le
   contrat exact.
3. `tests/test_contract_render.py`, section « LOT F » en fin de fichier — **ta
   spécification exécutable** (3 tests).
4. `sitegen/build.py` (figé) : le drapeau y est déjà câblé et transmis à `write_pages`.

## Tâche

### 1. `sitegen/render.py`

Étendre la signature :

```python
def write_pages(site, out: Path, base_url: str, card_link_base: str = "") -> list[Path]
```

Le défaut `""` est obligatoire : les tests existants appellent `write_pages` sans ce
paramètre, et `build.py` ne le transmet que s'il est non vide.

Exposer aux gabarits un moyen de rendre une puce de carte. Deux formes acceptables — le
choix t'appartient, mais il doit être **unique** (une seule implémentation, pas une par
gabarit) :

- un filtre Jinja `card_link` qui prend un `card_id` et rend soit l'ID nu, soit le lien ;
- ou une variable de contexte portant le gabarit, et un `{% macro %}` partagé.

Contraintes de rendu, toutes couvertes par les tests :

- `{id}` du gabarit est remplacé par l'identifiant (`OP15-061`).
- La balise porte `rel="noreferrer nofollow"` **et** `target="_blank"`.
- Le **libellé du lien est l'ID**, rien d'autre. Aucun nom de carte n'entre dans le HTML.
- **La quantité reste hors du lien.** La puce doit rester structurée comme aujourd'hui :
  `<span class="qty">4</span>x` en dehors de l'`<a>`, l'ID à l'intérieur.
- Rien ne doit apparaître comme **sous-ressource** : ni `<img>`, ni `src`, ni `srcset`, ni
  `data-src`. Le lien est un `<a href>`, un point. C'est la frontière exacte de
  l'amendement, et `check_dist.py` la vérifie.
- L'autoescape reste actif : l'ID passe par le pipeline normal de Jinja.

### 2. Les gabarits — 6 puces, 3 fichiers

Le motif actuel est identique partout :

```html
<li><code><span class="qty">{{ qty }}</span>x {{ card_id }}</code></li>
```

Emplacements (vérifier au `grep`, les numéros de ligne bougent) :

- `sitegen/templates/tournoi.html` — 2 puces (liste de deck, deux blocs)
- `sitegen/templates/leader.html` — 3 puces (core, écart/flex, liste complète)
- `sitegen/templates/meta.html` — 1 puce

**Les six doivent passer par la même implémentation.** Une puce oubliée donne un site où
certaines cartes sont cliquables et d'autres pas, sans logique visible pour le lecteur.

Attention au bloc d'écart de `leader.html` : la puce y est suivie de
`<span class="d-core-qty">(core {{ qty_core }}x)</span>`, qui reste **hors du lien** —
c'est une annotation de comparaison, pas la carte.

### 3. `sitegen/templates/style.css`

Un style de lien discret pour `.card-list a` : le registre visuel du site réserve la
couleur au signal (cf. SPEC § « Registre visuel »), et 1066 liens colorés sur une page
transformeraient une liste de cartes en sapin de Noël. Soulignement au survol plutôt que
couleur permanente, et la puce doit rester lisible comme un bloc de code monospace.

## Interdits

- Ne modifie **aucun** fichier figé : `SPEC-site-v1.md`, `AGENTS.md`, `sitegen/model.py`,
  `sitegen/build.py`, `tests/**`, `orchestration/**`.
- N'ajoute aucune dépendance.
- **N'introduis aucune image, aucune sous-ressource, aucun `<script>`.** Si l'idée te
  vient d'afficher la carte en survol ou en `<img loading="lazy">` : c'est explicitement
  écarté, et le vérificateur le refuse.
- **N'introduis aucune table ID→nom de carte**, ni aucun appel réseau au build.
- Ne change pas la structure de la puce hors du strict nécessaire : le tri d'affichage,
  la classe `qty`, les chiffres tabulaires et le `<code>` restent.
- Ne désactive, ne réécris, ne marque `skip`/`xfail` aucun test. Si un test te paraît
  faux, **dis-le dans ta sortie** et implémente quand même le reste.

## En cas de désaccord

Si l'implémentation révèle que le contrat est intenable tel qu'écrit — par exemple si une
puce ne peut pas garder la quantité hors du lien sans casser la mise en page — **écris le
constat dans ta sortie et n'invente pas de compromis**. L'arbitrage appartient à
l'orchestrateur : c'est un invariant produit, pas un détail de rendu.

## Terminé quand

```bash
python3 -m pytest -q tests/test_contract_render.py
./orchestration/verify.sh
```

sortent en vert. `verify.sh` vérifie en plus que le build **par défaut** (donc sans le
drapeau) reste déterministe et sans sous-ressource externe.

Contrôle manuel du chemin activé, qui n'est pas couvert par `verify.sh` (il ne construit
que le défaut) :

```bash
python3 -m sitegen.build --out /tmp/dist-liens --base-url https://exemple.org \
                         --card-link-base 'https://onepiece.limitlesstcg.com/cards/{id}'
grep -c 'limitlesstcg.com/cards/' /tmp/dist-liens/leaders/*/index.html | head
```

## Sortie attendue

Un résumé court : la forme retenue (filtre ou macro) et pourquoi, les 6 puces traitées,
et toute divergence constatée entre la spec, les tests et le corpus réel.
