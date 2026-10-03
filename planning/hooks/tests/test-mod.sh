#!/usr/bin/env bash
# test-mod.sh — the planning plugin's hooks module (planning/hooks/mod/), checked by
# the engine itself: `claude plugin validate` reads the manifest and the module's
# source the way a session will (including every `$.state` key against
# types/index.d.ts), and `claude plugin test` runs the mod's *.test.ts(x) files.
#
# The mod's own suites are named *.test.ts(x), which scripts/run-tests.sh does not
# discover (it finds test-*.py / test-*.sh). This wrapper is how they are reached.
#
# A missing `claude` binary is a FAILURE, never a skip (DEC-006): a runner that
# reports green without having run the mod's tests is the defect that decision exists
# to prevent.

set -uo pipefail

PLUGIN="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if ! command -v claude >/dev/null 2>&1; then
  echo "FAIL: the claude CLI is not on PATH; the mod's validate and test runs cannot execute" >&2
  exit 1
fi

rc=0

echo "== claude plugin validate $PLUGIN"
if ! claude plugin validate "$PLUGIN"; then
  echo "FAIL: claude plugin validate" >&2
  rc=1
fi

echo "== claude plugin test $PLUGIN"
if ! claude plugin test "$PLUGIN"; then
  echo "FAIL: claude plugin test" >&2
  rc=1
fi

exit "$rc"
