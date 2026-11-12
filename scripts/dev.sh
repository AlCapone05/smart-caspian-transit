#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/Users/adam/Library/Application Support/Zed/node/node-v24.11.0-darwin-arm64/bin:${PATH:-}"

API_PORT="${API_PORT:-8002}"
UI_PORT="${UI_PORT:-5173}"

kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "Stopping processes on :$port ($pids)"
    kill $pids 2>/dev/null || true
    sleep 1
  fi
}

kill_port "$API_PORT"
kill_port "$UI_PORT"

cd "$ROOT/backend"
# shellcheck disable=SC1091
source .venv/bin/activate
export PYTHONPATH=.
echo "Starting API on http://127.0.0.1:$API_PORT ..."
uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" --reload &
API_PID=$!

cd "$ROOT/frontend"
echo "Starting UI on http://127.0.0.1:$UI_PORT (proxy /api → :$API_PORT) ..."
npm run dev -- --host 127.0.0.1 --port "$UI_PORT" &
UI_PID=$!

cleanup() {
  kill "$API_PID" "$UI_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo
echo "Ready:"
echo "  UI  → http://127.0.0.1:$UI_PORT"
echo "  API → http://127.0.0.1:$API_PORT/docs"
echo "  key → X-API-Key: demo-key"
echo
wait
