#!/bin/bash
# android-mcp-orchestrator up.sh — build + start the MCP stack
# Usage: ./up.sh [--mock] [compose-dir]
#   --mock       also start the mock-synapse container (for Matrix Synapse Manager testing)
#   compose-dir  override compose root (default: bundled <plugin>/infrastructure)

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# scripts/ -> skill/ -> skills/ -> plugin-root/infrastructure
DEFAULT_COMPOSE_DIR="$SCRIPT_DIR/../../../infrastructure"

MOCK=0
COMPOSE_DIR=""
for arg in "$@"; do
  case "$arg" in
    --mock) MOCK=1 ;;
    *) COMPOSE_DIR="$arg" ;;
  esac
done
: "${COMPOSE_DIR:=$DEFAULT_COMPOSE_DIR}"

if [ ! -f "$COMPOSE_DIR/compose.yaml" ] && [ ! -f "$COMPOSE_DIR/docker-compose.yaml" ]; then
  echo "error: no compose file in $COMPOSE_DIR" >&2
  exit 2
fi

cd "$COMPOSE_DIR"
echo "=== building MCP stack in $(pwd) ==="
podman compose build

if [ "$MOCK" -eq 1 ]; then
  echo "=== starting with --profile mock ==="
  podman compose --profile mock up -d
else
  echo "=== starting (no mock) ==="
  podman compose up -d
fi

echo "=== waiting for MCP on http://localhost:8000/mcp (expect 405 when ready) ==="
# Emulator boot + MCP startup: ~60-120s first run, ~30-60s subsequent.
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:8000/mcp || echo "000")
  if [ "$code" = "405" ] || [ "$code" = "200" ]; then
    echo "MCP is up (HTTP $code) after ${i}0s"
    exit 0
  fi
  sleep 10
done
echo "error: MCP did not come up within 600s" >&2
exit 1
