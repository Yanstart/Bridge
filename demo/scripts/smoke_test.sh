#!/usr/bin/env bash
# =====================================================================
# smoke_test.sh : verifie en une passe que les routes HTML et JSON
# du bridge ne sont pas cassees apres un (re)build / redemarrage.
#
# Cible : detecter en moins de 10 s un retour du bug Starlette 1.0
# (TemplateResponse) ou tout autre crash silencieux.
#
# Usage : ./scripts/smoke_test.sh
#         echo $?    # 0 = OK, 1 = au moins une URL en erreur
# =====================================================================
set -euo pipefail

BRIDGE_URL="${BRIDGE_URL:-http://localhost:8080}"
HAPI_URL="${HAPI_URL:-http://localhost:8081/fhir}"

red()    { printf "\033[0;31m%s\033[0m\n" "$*"; }
green()  { printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[0;33m%s\033[0m\n" "$*"; }

# (route, doit_contenir)
ROUTES=(
  "$BRIDGE_URL/health|status"
  "$BRIDGE_URL/api/devices|count"
  "$BRIDGE_URL/api/profiles|profiles"
  "$BRIDGE_URL/api/plugins|plugins"
  "$BRIDGE_URL/api/queue|enabled"
  "$BRIDGE_URL/|Vue d'ensemble"
  "$BRIDGE_URL/devices/philips-mx450|Philips IntelliVue"
  "$BRIDGE_URL/config|Configuration"
  "$BRIDGE_URL/logs|Logs operationnels"
  "$BRIDGE_URL/plugins|Plugins"
  "$BRIDGE_URL/static/style.css|bridgeblue"
  "$BRIDGE_URL/fragments/devices-grid|device-card"
  "$BRIDGE_URL/fragments/recent-events|venement"
  "$HAPI_URL/metadata|CapabilityStatement"
)

failures=0
echo "Smoke test sur $BRIDGE_URL et $HAPI_URL"
echo ""

for route_pair in "${ROUTES[@]}"; do
  url="${route_pair%%|*}"
  expected="${route_pair##*|}"

  # Code HTTP
  http_code=$(curl -sS -o /tmp/smoke_resp -w "%{http_code}" "$url" 2>&1 || echo "000")

  printf "  %-65s HTTP %s  " "$url" "$http_code"

  if [ "$http_code" != "200" ]; then
    red "ECHEC"
    failures=$((failures + 1))
    continue
  fi

  if grep -q "$expected" /tmp/smoke_resp 2>/dev/null; then
    green "OK"
  else
    yellow "WARN (pas de '$expected' dans la reponse)"
    failures=$((failures + 1))
  fi
done

rm -f /tmp/smoke_resp

echo ""
if [ "$failures" -eq 0 ]; then
  green "Toutes les routes repondent et contiennent le marqueur attendu."
  exit 0
else
  red "$failures route(s) en erreur. Inspecter : docker logs bridge"
  exit 1
fi
