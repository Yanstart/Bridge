#!/usr/bin/env bash
# =====================================================================
# Test E2E de la demo IoT Edge Bridge.
#
# Lance docker compose up -d, attend les healthchecks, verifie le bridge,
# attend que les simulateurs aient envoye au moins un message chacun,
# verifie que les Observations FHIR sont creees sur HAPI.
# =====================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

BRIDGE_URL="http://localhost:8080"
HAPI_URL="http://localhost:8081/fhir"
WAIT_SECONDS=60

red()    { printf "\033[0;31m%s\033[0m\n" "$*"; }
green()  { printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[0;33m%s\033[0m\n" "$*"; }
blue()   { printf "\033[0;34m%s\033[0m\n" "$*"; }

check() {
  local label="$1"; local cmd="$2"
  printf "  %-50s " "$label"
  if eval "$cmd" >/dev/null 2>&1; then
    green "OK"
    return 0
  else
    red "ECHEC"
    return 1
  fi
}

blue "[1/5] Lancement des conteneurs..."
docker compose up -d --build

blue "[2/5] Attente des healthchecks (${WAIT_SECONDS}s max)..."
for i in $(seq 1 $WAIT_SECONDS); do
  if curl --fail --silent "$BRIDGE_URL/health" >/dev/null 2>&1 \
     && curl --fail --silent "$HAPI_URL/metadata" >/dev/null 2>&1; then
    green "  Healthchecks OK apres ${i}s"
    break
  fi
  sleep 1
done

blue "[3/5] Verification des endpoints du bridge"
check "GET /health"               "curl -fs $BRIDGE_URL/health"
check "GET /api/devices"          "curl -fs $BRIDGE_URL/api/devices"
check "GET / (dashboard HTML)"    "curl -fs $BRIDGE_URL/ | grep -q 'IoT Edge Bridge'"
check "GET /api/queue"            "curl -fs $BRIDGE_URL/api/queue"
check "GET /api/plugins"          "curl -fs $BRIDGE_URL/api/plugins"

blue "[4/5] Attente de production de messages (60s)..."
sleep 60

blue "[5/5] Verification des Observations FHIR sur HAPI"
COUNT_RESPONSE=$(curl --silent "$HAPI_URL/Observation?_count=200&_summary=count" || echo "")
TOTAL=$(echo "$COUNT_RESPONSE" | grep -oE '"total":[[:space:]]*[0-9]+' | grep -oE '[0-9]+' || echo "0")
if [ -n "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
  green "  $TOTAL Observation(s) trouvee(s) sur HAPI"
else
  red   "  Aucune Observation trouvee sur HAPI"
  yellow "  Inspecter les logs : docker compose logs --tail=50 bridge"
  exit 1
fi

green "Tests E2E reussis."
echo ""
yellow "Pour explorer :"
echo "  - Dashboard      : $BRIDGE_URL/"
echo "  - HAPI FHIR      : $HAPI_URL/Observation"
echo "  - File de repli  : $BRIDGE_URL/api/queue"
echo "  - Plugins        : $BRIDGE_URL/plugins"
echo ""
yellow "Pour arreter : docker compose down -v"
