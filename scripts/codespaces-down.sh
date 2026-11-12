#!/usr/bin/env bash
set -euo pipefail
LOG_DIR="${TMPDIR:-/tmp}/sct-codespaces"
PID_FILE="$LOG_DIR/pids"
if [[ -f "$PID_FILE" ]]; then
  while read -r pid; do
    kill "$pid" 2>/dev/null || true
  done < "$PID_FILE"
  rm -f "$PID_FILE"
  echo "Stopped Codespaces stack."
else
  # Fallback: kill by port
  for port in 8002 5173; do
    pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [[ -n "${pids:-}" ]]; then
      kill $pids 2>/dev/null || true
    fi
  done
  echo "Stopped processes on :8002 and :5173 (if any)."
fi
