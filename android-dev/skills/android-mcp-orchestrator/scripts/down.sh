#!/bin/bash
# android-mcp-orchestrator down.sh — tear down the MCP stack
# Usage: ./down.sh [--mock] [compose-dir]
#   --mock       also tear down the mock profile (if the stack was started with --mock)
#   compose-dir  override compose root (default: bundled <plugin>/infrastructure)

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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

cd "$COMPOSE_DIR"
if [ "$MOCK" -eq 1 ]; then
  podman compose --profile mock down
else
  podman compose down
fi
