#!/bin/bash
# statusline-chain — wraps a base statusline with the executing-plans plan
# progress bar.
#
# Why: users already have a statusline command configured; this shim leaves
# it untouched on line 1 and appends the plan-progress bar (present only
# while a plan is executing) on line 2, without editing the base script.
# Both consumers read the SAME stdin bytes (Claude Code's statusline JSON),
# captured once here so neither one starves the other.
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
STDIN_JSON="$(cat)"

BASE="${PLAN_STATUSLINE_BASE:-$HOME/.claude/statusline.sh}"
BASE_OUT=""
if [ -f "$BASE" ] && [ -r "$BASE" ]; then
  BASE_OUT="$(printf '%s' "$STDIN_JSON" | bash "$BASE" 2>/dev/null)"
fi
printf '%s' "$BASE_OUT"

PLAN_OUT="$(printf '%s' "$STDIN_JSON" | python3 "$HERE/plan-progress.py" 2>/dev/null)"
if [ -n "$PLAN_OUT" ]; then
  [ -n "$BASE_OUT" ] && printf '\n'
  printf '%s' "$PLAN_OUT"
fi

exit 0
