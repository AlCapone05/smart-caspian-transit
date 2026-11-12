#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${TMPDIR:-/tmp}/sct-codespaces"
mkdir -p "$LOG_DIR"
PID_FILE="$LOG_DIR/pids"

stop_if_running() {
  if [[ -f "$PID_FILE" ]]; then
    while read -r pid; do
      kill "$pid" 2>/dev/null || true
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi
}

stop_if_running
: > "$PID_FILE"

echo "==> Starting API on :8002"
cd "$ROOT/backend"
# shellcheck disable=SC1091
source .venv/bin/activate
export PYTHONPATH=.
nohup uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload \
  >"$LOG_DIR/api.log" 2>&1 &
echo $! >> "$PID_FILE"

echo "==> Starting frontend on :5173"
cd "$ROOT/frontend"
nohup npm run dev -- --host 0.0.0.0 --port 5173 \
  >"$LOG_DIR/web.log" 2>&1 &
echo $! >> "$PID_FILE"

sleep 2
echo ""
echo "API:       http://127.0.0.1:8002/docs"
echo "Frontend:  http://127.0.0.1:5173"
echo "Logs:      $LOG_DIR/api.log , $LOG_DIR/web.log"
echo "Stop:      ./scripts/codespaces-down.sh"
echo ""
echo "In Codespaces: Ports → 5173 → Open in Browser"
