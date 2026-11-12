#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Backend: venv + deps"
cd "$ROOT/backend"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created backend/.env from .env.example"
fi

echo "==> Frontend: npm install"
cd "$ROOT/frontend"
npm install

chmod +x "$ROOT/scripts/codespaces-up.sh" "$ROOT/scripts/codespaces-down.sh" 2>/dev/null || true
echo "==> Codespace ready. Run: ./scripts/codespaces-up.sh"
