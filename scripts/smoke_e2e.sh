#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://127.0.0.1:8000/api/v1}"
KEY="${API_KEY:-demo-key}"
H=(-H "X-API-Key: $KEY" -H "Content-Type: application/json")

echo "== health =="
curl -sf "$API/health" >/dev/null

echo "== overview =="
curl -sf "${H[@]}" "$API/overview" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["shipments"]; print("OK overview", len(d["shipments"]), "shipments")'

echo "== simulate storm =="
SIM=$(curl -sf "${H[@]}" -d '{"scenario":"storm"}' "$API/shipments/shp_sct_2048/simulate")
echo "$SIM" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["missed_connection"] is True; print("OK storm delay", d["delay_hours"], "h")'

echo "== alternatives =="
curl -sf "${H[@]}" "$API/shipments/shp_sct_2048/alternatives" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert len(d["alternatives"])==3; assert d["alternatives"][1]["recommended"]; print("OK alts")'

echo "== select makhachkala =="
curl -sf "${H[@]}" -d '{"alternative_id":"alt_via_makhachkala"}' \
  "$API/shipments/shp_sct_2048/select-alternative" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("OK select", d["selected_alternative_id"])'

echo "SMOKE PASS"
