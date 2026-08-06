#!/bin/bash
# statusline-chain — wraps a base statusline with the executing-plans plan
# progress bar.
#
# Why: users already have a statusline command configured; this shim leaves
# it untouched and appends the plan-progress bar (present only while a plan is
# executing) on the NEXT line — not "line 2", since a base statusline may
# itself emit several lines (Claude Code's own bundled one embeds a newline in
# its "Update available" notice). Both consumers read the SAME stdin bytes
# (Claude Code's statusline JSON), captured once here so neither one starves
# the other.
#
# Accepted limitation: command substitution strips trailing newlines, so a base
# that deliberately ends in a blank line for spacing loses it. Preserving it
# would need a sentinel-and-strip dance; the spacing is not worth that.
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
STDIN_JSON="$(cat)"

# A statusline is redrawn constantly, so a base that blocks (a network-backed
# prompt, a stuck filesystem call) would freeze the redraw indefinitely — worse
# than a missing line, and with nothing to explain it. Bound both subprocesses.
# `timeout` is GNU coreutils and absent from a stock macOS, a platform this repo
# supports; fall back to gtimeout, then to running unbounded rather than losing
# the statusline entirely. Unquoted on purpose: empty must expand to no words.
if command -v timeout >/dev/null 2>&1; then
  TO="timeout 2"
elif command -v gtimeout >/dev/null 2>&1; then
  TO="gtimeout 2"
else
  TO=""
fi

BASE="${PLAN_STATUSLINE_BASE:-$HOME/.claude/statusline.sh}"
BASE_OUT=""
if [ -f "$BASE" ] && [ -r "$BASE" ]; then
  BASE_OUT="$(printf '%s' "$STDIN_JSON" | $TO bash "$BASE" 2>/dev/null)"
fi
printf '%s' "$BASE_OUT"

PLAN_OUT="$(printf '%s' "$STDIN_JSON" | $TO python3 "$HERE/plan-progress.py" 2>/dev/null)"
if [ -n "$PLAN_OUT" ]; then
  [ -n "$BASE_OUT" ] && printf '\n'
  printf '%s' "$PLAN_OUT"
fi

exit 0
