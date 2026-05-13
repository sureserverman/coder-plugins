#!/bin/bash
# mcp-call.sh — authenticated JSON-RPC client for the in-container MCP server.
#
# Reads MCP_AUTH_TOKEN from <compose-dir>/.env. Assumes the stack is already
# up (use up.sh or run.sh first).
#
# Usage:
#   ./mcp-call.sh tools/list
#   ./mcp-call.sh tools/call <tool-name> <args-json>
#
# Env overrides:
#   MCP_URL       default http://127.0.0.1:8000/mcp
#   COMPOSE_DIR   default <plugin>/infrastructure (for .env lookup)

set -Eeuo pipefail

if [ $# -lt 1 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
: "${COMPOSE_DIR:=$SCRIPT_DIR/../../../infrastructure}"
: "${MCP_URL:=http://127.0.0.1:8000/mcp}"

ENV_FILE="$COMPOSE_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "error: $ENV_FILE not found — run up.sh first" >&2
  exit 2
fi
# shellcheck disable=SC1090
. "$ENV_FILE"
if [ -z "${MCP_AUTH_TOKEN:-}" ]; then
  echo "error: MCP_AUTH_TOKEN not set in $ENV_FILE" >&2
  exit 2
fi

method="$1"; shift
id="$RANDOM"

case "$method" in
  tools/list)
    body=$(printf '{"jsonrpc":"2.0","id":%s,"method":"tools/list","params":{}}' "$id")
    ;;
  tools/call)
    if [ $# -lt 1 ]; then
      echo "error: tools/call requires <tool-name> [args-json]" >&2
      exit 2
    fi
    tool="$1"; shift
    args_json="${1:-{\}}"
    body=$(printf '{"jsonrpc":"2.0","id":%s,"method":"tools/call","params":{"name":"%s","arguments":%s}}' \
      "$id" "$tool" "$args_json")
    ;;
  *)
    # Pass-through for any other JSON-RPC method; args read from stdin as raw JSON.
    if [ -t 0 ]; then
      echo "error: unknown convenience method '$method' — pipe full JSON-RPC body on stdin to use a raw method" >&2
      exit 2
    fi
    body=$(cat)
    ;;
esac

curl -fsS \
  -H "Authorization: Bearer ${MCP_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  --data-raw "$body" \
  --max-time 120 \
  "$MCP_URL"
echo
