#!/usr/bin/env bash
# Orchestration complète des lots — FIGÉ.
#
#   ./orchestration/run-all.sh
#
# Ordonnancement dicté par les dépendances de fichiers, pas par le confort :
#
#   D (dépôt studio, indépendant) ──────────────────────────────┐
#   A (parse) ──> B (render)  ∥  C (packs) ──> verify.sh complet ┘
#
# A d'abord : les portillons de B et C consomment la fixture `site`, qui appelle
# parse.load_site. B et C ensuite en parallèle — ils touchent des fichiers disjoints
# (render.py + templates/ d'un côté, packs.py de l'autre), donc pas de collision dans un
# répertoire de travail partagé. D vit dans un autre dépôt : lancé d'emblée.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 2
LOG_DIR="orchestration/logs"
mkdir -p "$LOG_DIR"

echo "════════ D (patch studio) en tâche de fond"
./orchestration/run-lot.sh D 3 >"$LOG_DIR/run-D.log" 2>&1 &
PID_D=$!

echo "════════ A (parse) — bloquant"
if ! ./orchestration/run-lot.sh A 4 2>&1 | tee "$LOG_DIR/run-A.log"; then
  echo "✗ A en échec : B et C ne peuvent pas démarrer (leurs portillons dépendent de parse)."
  wait "$PID_D" || true
  exit 1
fi

echo "════════ B (rendu) et C (packs) en parallèle"
./orchestration/run-lot.sh B 4 >"$LOG_DIR/run-B.log" 2>&1 &
PID_B=$!
./orchestration/run-lot.sh C 4 >"$LOG_DIR/run-C.log" 2>&1 &
PID_C=$!

rc=0
wait "$PID_B" || { echo "✗ lot B en échec (cf. $LOG_DIR/run-B.log)"; rc=1; }
wait "$PID_C" || { echo "✗ lot C en échec (cf. $LOG_DIR/run-C.log)"; rc=1; }
wait "$PID_D" || { echo "⚠ lot D en échec (cf. $LOG_DIR/run-D.log) — n'empêche pas le site"; }

echo "════════ verify.sh — la définition de « terminé »"
./orchestration/verify.sh 2>&1 | tee "$LOG_DIR/verify.log" || rc=1

exit "$rc"
