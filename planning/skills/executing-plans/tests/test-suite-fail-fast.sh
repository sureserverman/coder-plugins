#!/usr/bin/env bash
# Fail-fast suite — run directly (repo convention):
#
#     bash planning/skills/executing-plans/tests/test-suite-fail-fast.sh
#
# WHAT THIS SUITE IS REALLY GUARDING. The mutation battery (battery-proof-tools.py) runs
# the four proof-tool suites once per mutation, and a killed mutation needs only the
# FIRST failing check. With SUITE_FAIL_FAST=1 each suite prints its first `  FAIL` line
# and exits 1 at once. Two failures matter: a suite that runs on past its first failure
# (the battery saves nothing), and a suite whose DEFAULT mode changed (every other caller
# — run-tests.sh, a person reading a red suite — now sees less).
#
# For each suite, a copy of the plugin tree gets one known guard broken: the battery's
# own mutation, by label, chosen because it makes that suite report several failures.
# The suite then runs three ways on that broken copy: as committed at `Stage 3 green`
# (before fail-fast existed), as it is now in default mode, and now with
# SUITE_FAIL_FAST=1.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
BATTERY="$HERE/battery-proof-tools.py"
pass=0; fail=0
ok()  { pass=$((pass+1)); echo "  ok    $1"; }
bad() { fail=$((fail+1)); echo "  FAIL  $1"; [ -n "${2:-}" ] && printf '        | %s\n' "${2:0:700}"; }

# The tree as it was before this change: the suites' pre-fail-fast text.
BASE="$(git -C "$REPO" log --format=%H -1 --grep='^Stage 3 green$' 2>/dev/null)"
[ -n "$BASE" ] || { echo "FAIL: no 'Stage 3 green' commit to read the pre-change suites from"; exit 1; }

echo "suite fail-fast — SUITE_FAIL_FAST=1 stops at the first FAIL; default mode unchanged"
echo

# suite (relative to planning/) | battery label whose mutation that suite reports several times
CASES=(
  "skills/executing-plans/tests/test-plan-flip-audit.py|strong tier voids alone -> demoted to advisory"
  "skills/executing-plans/tests/test-prove-claim.py|prove: green under the break is recorded"
  "hooks/tests/test-git-ref-gate.sh|ref gate: acts in the committed phase, where a refusal aborts nothing"
  "hooks/tests/test-proof-guard.sh|guard: the hooksPath rule off"
)

for case in "${CASES[@]}"; do
  suite="${case%%|*}"; label="${case#*|}"
  name="$(basename "$suite")"
  # copy + break, using the battery's own copy_skill() and its entry for `label`
  d="$(python3 - "$BATTERY" "$label" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("bat", sys.argv[1])
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
entry = [e for e in b.M if e[0] == sys.argv[2]]
if len(entry) != 1:
    sys.exit(f"no battery entry labelled {sys.argv[2]!r}")
_label, target, old, new = entry[0]
d = b.copy_skill()
f = d / "planning" / target
f.write_text(f.read_text().replace(old, new))
print(d)
PY
)" || { bad "$name: the battery entry '$label' could not be applied" "$d"; continue; }
  root="$d/planning"
  runner=python3; case "$suite" in *.sh) runner=bash ;; esac
  # the pre-change suite, beside the current one so it finds the same scripts
  orig="${suite%.*}.orig.${suite##*.}"
  git -C "$REPO" show "$BASE:planning/$suite" > "$root/$orig"

  out_old="$(env -u SUITE_FAIL_FAST $runner "$root/$orig" 2>/dev/null)"
  out_def="$(env -u SUITE_FAIL_FAST $runner "$root/$suite" 2>/dev/null)"; rc_def=$?
  out_ff="$(SUITE_FAIL_FAST=1 $runner "$root/$suite" 2>/dev/null)"; rc_ff=$?
  n_old="$(printf '%s\n' "$out_old" | grep -c '^  FAIL')"
  n_def="$(printf '%s\n' "$out_def" | grep -c '^  FAIL')"
  n_ff="$(printf '%s\n' "$out_ff" | grep -c '^  FAIL')"
  rm -rf "$d"

  # Catches: the fixture measuring nothing — a break the suite reports once cannot show
  # fail-fast stopping early.
  if [ "$n_old" -ge 2 ]; then ok "$name: the broken copy fails $n_old checks before the change"
  else bad "$name: the chosen break must make the suite report >=2 failures" "got $n_old"; fi
  # Catches: a suite running on past its first failure.
  if [ "$n_ff" = 1 ] && [ "$rc_ff" = 1 ]; then ok "$name: SUITE_FAIL_FAST=1 prints one FAIL and exits 1"
  else bad "$name: SUITE_FAIL_FAST=1 must print exactly one FAIL and exit 1" "FAIL lines $n_ff, exit $rc_ff"; fi
  # Catches: default mode changed.
  if [ "$n_def" = "$n_old" ] && [ "$rc_def" != 0 ]; then
    ok "$name: default mode reports the same $n_def failures as before the change"
  else
    bad "$name: default mode must be unchanged" "before $n_old, now $n_def (exit $rc_def)"
  fi
done

echo
echo "$pass passed, $fail failed"
[ "$fail" = 0 ]
