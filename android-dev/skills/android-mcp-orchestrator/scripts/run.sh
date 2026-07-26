#!/bin/bash
# run.sh — trap-guarded ephemeral lifecycle wrapper.
#
# Brings the stack UP, runs one or more JSON-RPC calls, then ALWAYS tears it
# DOWN (even on error or signal). This is the canonical way for a skill or
# command to use the Android MCP — the host returns to its idle state when
# run.sh exits.
#
# Usage:
#   ./run.sh [--mock] [--keep-on-error]
#
#   Reads a sequence of calls from stdin, one per line, in either form:
#     tools/list
#     tools/call <tool-name> <args-json>
#
# Example:
#   APK_DIR=/abs/path/to/project/app/build/outputs/apk/debug \
#   SCREENSHOT_DIR=/abs/path/to/project/play-screenshots \
#   ./run.sh --mock <<'EOF'
#   tools/call start-android-tablet-emulators {}
#   tools/call install-app-on-emulators {"apkPath":"/apks/app-debug.apk"}
#   tools/call launch-app {"packageName":"com.example.app"}
#   tools/call capture-emulator-screenshots {"loginFlow":"none","navItemCount":5}
#   EOF
#
# Options:
#   --mock            also start the mock-synapse container
#   --keep-on-error   leave the stack up if a call fails (for interactive debug);
#                     normal exit still tears down
#
# Environment (passed through to up.sh, which resolves the shell first, then
# <compose-dir>/.env — the same precedence compose uses):
#   APK_DIR         host dir mounted read-only at /apks. No working default: the
#                   fallback is relative to the bundled infrastructure/ dir, so
#                   set an absolute path to your project's
#                   app/build/outputs/apk/debug or up.sh stops at exit 4.
#   SCREENSHOT_DIR  host dir mounted at /screenshots. Same defaulting, but it is
#                   created if missing — leave it unset and screenshots land
#                   inside the installed plugin.
#
# Exit codes: this wrapper propagates up.sh's, notably
#   4 APK_DIR does not exist   5 SCREENSHOT_DIR could not be created
# (run `./up.sh --help` for the full list); teardown still runs either way.

set -Eeuo pipefail

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  # Derived from the leading comment block rather than a hardcoded line range,
  # so editing the header above cannot silently truncate --help.
  awk 'NR==1 {next} /^#/ {sub(/^# ?/, ""); print; next} {exit}' "$0"
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

MOCK=0
KEEP_ON_ERROR=0
for arg in "$@"; do
  case "$arg" in
    --mock)           MOCK=1 ;;
    --keep-on-error)  KEEP_ON_ERROR=1 ;;
    *)
      echo "error: unknown arg: $arg" >&2
      exit 2
      ;;
  esac
done

mock_flag=()
[ "$MOCK" -eq 1 ] && mock_flag=(--mock)

CALL_FAILED=0
teardown() {
  local rc=$?
  if [ "$KEEP_ON_ERROR" -eq 1 ] && [ "$CALL_FAILED" -eq 1 ]; then
    echo "=== --keep-on-error: skipping teardown (stack left running) ===" >&2
    return "$rc"
  fi
  echo "=== tearing down stack ==="
  "$SCRIPT_DIR/down.sh" "${mock_flag[@]}" || true
  return "$rc"
}
trap teardown EXIT

"$SCRIPT_DIR/up.sh" "${mock_flag[@]}"

# Read calls from stdin and dispatch each through mcp-call.sh.
if [ -t 0 ]; then
  echo "=== no calls on stdin; stack is up — exiting (will tear down) ==="
else
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    case "$line" in \#*) continue ;; esac  # ignore comment lines
    echo "=== call: $line ==="
    # shellcheck disable=SC2086
    if ! "$SCRIPT_DIR/mcp-call.sh" $line; then
      CALL_FAILED=1
      echo "error: call failed: $line" >&2
      exit 1
    fi
  done
fi
