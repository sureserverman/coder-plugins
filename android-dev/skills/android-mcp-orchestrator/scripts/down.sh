#!/bin/bash
# android-mcp-orchestrator down.sh — tear down the MCP stack and verify clean state.
#
# Usage: ./down.sh [--mock] [compose-dir]
#   --mock       also tear down the mock profile (if the stack was started with --mock)
#   compose-dir  override compose root (default: bundled <plugin>/infrastructure)
#
# Always exits 0 if the stack is already gone — safe to call from a cleanup trap.

set -Eeuo pipefail

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_COMPOSE_DIR="$SCRIPT_DIR/../../../infrastructure"

MOCK=0
COMPOSE_DIR=""
for arg in "$@"; do
  case "$arg" in
    --mock) MOCK=1 ;;
    *)      COMPOSE_DIR="$arg" ;;
  esac
done
: "${COMPOSE_DIR:=$DEFAULT_COMPOSE_DIR}"

if [ ! -d "$COMPOSE_DIR" ]; then
  echo "warn: compose dir $COMPOSE_DIR does not exist; nothing to tear down" >&2
  exit 0
fi

cd "$COMPOSE_DIR"

# A missing .env would make podman compose refuse to evaluate the
# ${MCP_AUTH_TOKEN:?...} expansion even for `down`. Provide a transient dummy
# so teardown always succeeds, even if the user deleted the .env first.
DUMMY_ENV=0
if [ ! -f ".env" ]; then
  DUMMY_ENV=1
  echo "MCP_AUTH_TOKEN=teardown-only" >.env
  chmod 600 .env
fi

set +e
if [ "$MOCK" -eq 1 ]; then
  podman compose --profile mock down -v
else
  podman compose down -v
fi
rc=$?
set -e

if [ "$DUMMY_ENV" -eq 1 ]; then
  rm -f .env
fi

# Sanity: warn if any containers from this compose project remain.
project="$(basename "$(pwd)")"
remaining="$(podman ps --filter "label=io.podman.compose.project=${project}" --format '{{.Names}}' 2>/dev/null || true)"
if [ -n "$remaining" ]; then
  echo "warn: containers still running after down:" >&2
  echo "$remaining" >&2
  exit 1
fi

exit "$rc"
