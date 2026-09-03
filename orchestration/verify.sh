#!/usr/bin/env bash
# LA définition de « terminé » — FIGÉ.
#
# Aucun worker ne déclare la victoire : ce script la déclare. Sortie 0 = le lot est fini.
# Toute sortie non nulle est réinjectée dans le worker au tour de boucle suivant, donc les
# messages doivent être exploitables tels quels par un agent (chemins + cause).
#
#   ./orchestration/verify.sh            # corpus réel
#   PACKS_DIR=tests/fixtures/packs ./orchestration/verify.sh
set -uo pipefail

cd "$(dirname "$0")/.." || exit 2

PACKS_DIR="${PACKS_DIR:-../optcgsim-deckpacks-data/packs}"
DIST="${DIST:-dist}"
BASE_URL="${BASE_URL:-https://exemple.org}"
# Le venv local est pratique en développement, mais un `PY` fourni explicitement doit
# gagner : sinon la variable est mensongère, et un appelant qui croit choisir l'interpréteur
# se fait silencieusement ignorer.
if [ -z "${PY:-}" ]; then
  PY=python3
  [ -x .venv/bin/python ] && PY=.venv/bin/python
fi

fail=0
step() { printf '\n──── %s\n' "$1"; }

# Empreinte du corpus : somme de contrôle du CONTENU de chaque manifeste.
#
# Le corpus appartient à un AUTRE dépôt, que ce script ne verrouille pas. S'il change en
# cours de route — un `git pull` dans deckpacks-data, un scraping qui se termine — les deux
# builds de l'étape 4 lisent deux corpus différents, et le script accuse le générateur de
# non-déterminisme. C'est arrivé le 2026-09-03 : deux rouges consécutifs pendant un rebase
# du dépôt de données, puis cinq verts d'affilée sans qu'une ligne ait changé. Le diagnostic
# a coûté plus cher que la panne.
#
# On ne verrouille pas (ce n'est pas notre dépôt) : on DÉTECTE, pour que le message dise la
# vérité au lieu de désigner un innocent.
#
# `cksum` et non `stat` : `stat -f` est du BSD (macOS) et signifie « système de fichiers »
# sur GNU/Linux, où le contrôle serait devenu un no-op silencieux en CI — le défaut que ce
# dépôt traque partout ailleurs. `cksum` est POSIX et se comporte pareil des deux côtés.
#
# Le contenu, et pas la date de modification : un `touch` n'est pas un changement de corpus,
# une réécriture par git en est un.
empreinte_corpus() {
  find "$PACKS_DIR" -name deckpack.json -type f | LC_ALL=C sort | tr '\n' '\0' \
    | xargs -0 cksum 2>/dev/null
}
EMPREINTE_AVANT="$(empreinte_corpus | LC_ALL=C sort)"

# Une empreinte VIDE se comparerait égale à elle-même : le contrôle deviendrait un no-op
# silencieux, et c'est précisément ce que ce dépôt refuse — un contrôle doit distinguer
# « rien n'a changé » de « je n'ai rien mesuré ». On échoue donc tout de suite si le corpus
# existe et contient des manifestes sans qu'on ait su les empreindre.
if [ -d "$PACKS_DIR" ] && [ -z "$EMPREINTE_AVANT" ] \
   && [ -n "$(find "$PACKS_DIR" -name deckpack.json -type f -print -quit 2>/dev/null)" ]; then
  echo "✗ impossible d'empreindre le corpus ($PACKS_DIR) alors qu'il contient des manifestes"
  echo "  find/sort/cksum indisponibles ou incompatibles : le contrôle de stabilité du"
  echo "  corpus serait aveugle, donc mensonger. Corriger l'environnement."
  exit 2
fi

step "1/4  tests unitaires"
if "$PY" -m pytest -q; then
  echo "✓ pytest"
else
  echo "✗ pytest en échec"
  fail=1
fi

step "2/4  build sur le corpus réel ($PACKS_DIR)"
if [ ! -d "$PACKS_DIR" ]; then
  echo "✗ corpus introuvable : $PACKS_DIR"
  echo "  (dépôt sibling optcgsim-deckpacks-data absent ?)"
  fail=1
else
  rm -rf "$DIST"
  if "$PY" -m sitegen.build --packs-dir "$PACKS_DIR" --out "$DIST" --base-url "$BASE_URL"; then
    echo "✓ build"
  else
    echo "✗ build en échec"
    fail=1
  fi
fi

step "3/4  contrôles structurels sur $DIST"
if [ -d "$DIST" ]; then
  "$PY" orchestration/check_dist.py "$DIST" "$PACKS_DIR" "$BASE_URL" || fail=1
else
  echo "✗ pas de dist/ à contrôler"
  fail=1
fi

step "4/4  reproductibilité du build"
if [ -d "$DIST" ]; then
  rm -rf .verify-dist2
  if "$PY" -m sitegen.build --packs-dir "$PACKS_DIR" --out .verify-dist2 \
        --base-url "$BASE_URL" >/dev/null 2>&1 \
     && diff -r "$DIST" .verify-dist2 >/dev/null 2>&1; then
    echo "✓ deux builds identiques"
  else
    echo "✗ build non déterministe (diff entre deux exécutions)"
    diff -rq "$DIST" .verify-dist2 2>&1 | head -10
    fail=1
  fi
  rm -rf .verify-dist2
fi

# Le corpus a-t-il bougé sous nos pieds ? À vérifier AVANT le verdict : si oui, ni le vert
# ni le rouge ne veut dire ce qu'il prétend.
if [ "$(empreinte_corpus | sort)" != "$EMPREINTE_AVANT" ]; then
  printf '\n'
  echo "✗ le corpus a CHANGÉ pendant l'exécution ($PACKS_DIR)"
  echo "  Un autre processus l'a modifié — git pull dans le dépôt de données, scraping en"
  echo "  cours. Aucun résultat ci-dessus n'est concluant, y compris un « deux builds"
  echo "  identiques » : les deux builds n'ont pas lu le même corpus."
  echo "  Relancer une fois le corpus stable."
  fail=1
fi

printf '\n════ '
if [ "$fail" -eq 0 ]; then
  echo "VERT — le lot est terminé."
else
  echo "ROUGE — non terminé, corriger les points ci-dessus."
fi
exit "$fail"
