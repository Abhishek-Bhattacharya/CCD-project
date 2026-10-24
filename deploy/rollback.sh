#!/bin/bash
# Rollback script executed if health checks fail
set -euo pipefail

cd ~/phoenixci

echo "=== [PhoenixCI] Initiating Rollback ==="

if [ ! -f state/previous_version.txt ]; then
    echo "[!] No previous version record found. Cannot rollback automatically."
    exit 1
fi

PREV_VERSION=$(cat state/previous_version.txt)
echo "Restoring previous working version: ${PREV_VERSION}"

export RELEASE_COMMIT="${PREV_VERSION}"
docker compose -f deploy/docker-compose.prod.yml up -d --remove-orphans

# Restore active version file
echo "${PREV_VERSION}" > state/active_version.txt

echo "=== [PhoenixCI] Rollback Complete. Active version is now ${PREV_VERSION} ==="
