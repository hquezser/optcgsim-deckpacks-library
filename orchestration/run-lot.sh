#!/usr/bin/env bash
# Boucle de développement autonome pour UN lot — FIGÉ.
#
#   ./orchestration/run-lot.sh A [tentatives]
#
# Une itération = worker DevinCLI (GLM-5.2, gratuit) puis exécution du portillon du lot.
# Vert -> on sort. Rouge -> la sortie du portillon est réinjectée telle quelle dans le
# prompt du tour suivant, ce qui est tout le mécanisme d'autocorrection : le worker voit
# ses propres échecs, pas une reformulation.
#
# Chaque lot a son PROPRE portillon : verify.sh complet ne peut pas passer avant que tous
# les lots soient finis, il ne peut donc pas servir de critère par lot.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 2
ROOT="$PWD"

LOT="${1:?usage: run-lot.sh <A|B|C|D> [tentatives]}"
MAX="${2:-4}"
MODEL="${MODEL:-glm-5-2}"          # gratuit, 200K de contexte
PY="python3"; [ -x .venv/bin/python ] && PY=.venv/bin/python

LOG_DIR="$ROOT/orchestration/logs"
mkdir -p "$LOG_DIR"

# ── Registre des lots : spec, répertoire de travail, portillon ────────────────────────
case "$LOT" in
  A) SPEC="$ROOT/orchestration/lots/A-parse.md";  WORKDIR="$ROOT"
     GATE="$PY -m pytest -q tests/test_contract_model.py tests/test_contract_parse.py" ;;
  B) SPEC="$ROOT/orchestration/lots/B-render.md"; WORKDIR="$ROOT"
     GATE="$PY -m pytest -q tests/test_contract_render.py" ;;
  C) SPEC="$ROOT/orchestration/lots/C-packs.md";  WORKDIR="$ROOT"
     GATE="$PY -m pytest -q tests/test_contract_packs.py" ;;
  D) SPEC="$ROOT/orchestration/lots/D-studio-json-url.md"
     WORKDIR="$ROOT/../optcgsim-studio"
     GATE="python3 -m pytest -q tests/test_packlib.py tests/test_deckpack.py" ;;
  *) echo "lot inconnu : $LOT (attendu A, B, C ou D)"; exit 2 ;;
esac

[ -f "$SPEC" ] || { echo "spec introuvable : $SPEC"; exit 2; }
[ -d "$WORKDIR" ] || { echo "répertoire de travail introuvable : $WORKDIR"; exit 2; }

PROMPT="$LOG_DIR/lot-$LOT.prompt.md"
FEEDBACK=""

for tour in $(seq 1 "$MAX"); do
  echo "════════ lot $LOT — tentative $tour/$MAX (modèle $MODEL)"

  # Prompt = spec du lot, augmentée des échecs du tour précédent.
  cp "$SPEC" "$PROMPT"
  if [ -n "$FEEDBACK" ]; then
    {
      printf '\n\n---\n\n## Échecs de ta tentative précédente\n\n'
      printf 'Le portillon a été exécuté et a échoué. Sortie brute :\n\n```\n%s\n```\n\n' \
        "$FEEDBACK"
      printf 'Corrige la cause. Ne modifie aucun fichier figé, ne désactive aucun test.\n'
    } >> "$PROMPT"
  fi

  ( cd "$WORKDIR" && devin -p --permission-mode=dangerous --model="$MODEL" \
      --prompt-file "$PROMPT" ) 2>&1 | tee "$LOG_DIR/lot-$LOT.tour$tour.worker.log"

  echo "──────── portillon lot $LOT"
  GATE_OUT="$( cd "$WORKDIR" && eval "$GATE" 2>&1 )"
  GATE_RC=$?
  echo "$GATE_OUT" | tee "$LOG_DIR/lot-$LOT.tour$tour.gate.log"

  if [ "$GATE_RC" -eq 0 ]; then
    echo "✓ lot $LOT VERT à la tentative $tour"
    exit 0
  fi

  # On ne garde que la queue : un pytest verbeux noierait la spec dans le prompt suivant.
  FEEDBACK="$(printf '%s' "$GATE_OUT" | tail -c 6000)"
  echo "✗ lot $LOT rouge — réinjection dans la tentative suivante"
done

echo "✗ lot $LOT toujours rouge après $MAX tentatives — intervention humaine requise"
echo "  journaux : $LOG_DIR/lot-$LOT.tour*.{worker,gate}.log"
exit 1
