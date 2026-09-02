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

printf '\n════ '
if [ "$fail" -eq 0 ]; then
  echo "VERT — le lot est terminé."
else
  echo "ROUGE — non terminé, corriger les points ci-dessus."
fi
exit "$fail"
