#!/bin/bash
# Auto-detect a tech baseline the first time loadout sees a project.
# No-op if .claude/loadout.json already exists. Silent on failure — never
# blocks session start. When it detects, emits a JSON systemMessage so the
# user is told to restart (plain stdout would only reach Claude, not the TUI).
set -eu

project="${CLAUDE_PROJECT_DIR:-$PWD}"
state_file="$project/.claude/loadout.json"

if [ -f "$state_file" ]; then
    exit 0
fi

if ! out=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/loadout.py" detect 2>/dev/null); then
    exit 0
fi

# detect prints "auto-detected tech baseline → <name>" on success;
# extract the name and surface a systemMessage.
tech=$(printf '%s\n' "$out" | sed -n 's/^auto-detected tech baseline → //p' | head -n1)
if [ -n "$tech" ]; then
    printf '{"systemMessage": "loadout: detected tech=%s. Restart or /clear to apply the scoped plugin set."}\n' "$tech"
fi
exit 0
