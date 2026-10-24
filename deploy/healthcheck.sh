#!/bin/bash
# Health check validation for PhoenixCI deployed service
set -euo pipefail

PORT="${APP_PORT:-3000}"
HEALTH_URL="http://localhost:${PORT}/health"
MAX_ATTEMPTS=10
SLEEP_INTERVAL=2

echo "=== [PhoenixCI] Probing Service Health at ${HEALTH_URL} ==="

for (( i=1; i<=MAX_ATTEMPTS; i++ )); do
    echo "Health check attempt ${i}/${MAX_ATTEMPTS}..."
    if curl -s -f -m 3 "${HEALTH_URL}" | grep -q '"status":"ok"'; then
        echo "[✓] Health check passed successfully! Service is operational."
        exit 0
    fi
    sleep "${SLEEP_INTERVAL}"
done

echo "[✗] Health check failed after ${MAX_ATTEMPTS} attempts!"
exit 1
