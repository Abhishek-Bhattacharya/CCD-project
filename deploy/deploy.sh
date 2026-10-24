#!/bin/bash
# Deployment script executed on the Ubuntu EC2 target
set -euo pipefail

RELEASE_COMMIT="${1:-latest}"
cd ~/phoenixci

echo "=== [PhoenixCI] Deploying Release Commit: ${RELEASE_COMMIT} ==="

# Record previous version for rollback
if [ -f state/active_version.txt ]; then
    PREV_VERSION=$(cat state/active_version.txt)
    echo "${PREV_VERSION}" > state/previous_version.txt
    echo "Recorded previous release version: ${PREV_VERSION}"
fi

# Build and start the container with new release commit tag
export RELEASE_COMMIT
docker compose -f deploy/docker-compose.prod.yml build
docker compose -f deploy/docker-compose.prod.yml up -d --remove-orphans

# Update active version marker
echo "${RELEASE_COMMIT}" > state/active_version.txt
echo "=== [PhoenixCI] Deployment Started for ${RELEASE_COMMIT} ==="
