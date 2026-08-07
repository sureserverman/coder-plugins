#!/bin/bash
# Silence-when-broken sweep for plan-progress.py — the Stage 2 gate check.
#
# The renderer runs inside the user's status line on every redraw, in every
# project. Its one hard contract is that a broken environment produces a
# MISSING bar, never a noisy one: empty stdout, empty stderr, exit 0.
#
# Why a sweep and not a sampled case: Stage 2 added a whole new surface
# (portfolio config, registry, vault path, scan cache) and the existing suite
# checks a few inputs it happened to think of. This enumerates the corpus and
# runs EVERY member, so the claim "silence holds across the new surface" is an
# executed sweep rather than an assertion about one input (DEC-005).
#
# EVERY CASE RUNS TWO LANES, and the second one is the point:
#
#   lane A — `python3 plan-progress.py`, the shipped entry point. Proves the
#            live redraw path stays silent with garbage sitting nearby.
#   lane B — a driver that calls portfolio_plans_dir() -> discover_plans()
#            DIRECTLY, with no guard around them.
#
# Lane B exists because lane A alone made this sweep a test that cannot fail.
# main() calls find_state() and render(); it does not call any Stage 2 function
# (that wiring is Stage 3 Task 3.1). So the config/registry/vault/cache cases
# were passing because the code they name was never reached — the artifact
# certifying the stage was asserting coverage it did not have.
#
# Lane B is deliberately UNGUARDED, and that is not an oversight. main() ends in
# `except Exception: sys.exit(0)`, so once Stage 3 wires discovery in, lane A
# would go green whether these functions degrade gracefully or throw — the same
# vacuity in a new costume. Calling them raw means an escaping exception lands on
# stderr as a traceback and the assertion below fails. What is under test is that
# the new surface degrades INTERNALLY, not that a catch-all hides it.
#
# Usage: bash test-plan-progress-corpus.sh    (exit 0 = pass)
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/plan-progress.py"
[ -f "$SCRIPT" ] || { echo "FAIL: cannot find plan-progress.py at $SCRIPT"; exit 1; }

TMP="$(mktemp -d)"
trap 'chmod -R u+rwX "$TMP" 2>/dev/null; rm -rf "$TMP"' EXIT

fail=0
cases=0

# Lane B's driver. Only the stdin parsing is guarded — everything from
# portfolio_plans_dir() onward is the surface under test and must degrade on its
# own, so anything it raises escapes here as a traceback on stderr.
DRIVER="$TMP/discovery-driver.py"
cat > "$DRIVER" <<'PYEOF'
import importlib.util, json, os, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("pp", os.environ["PP_SCRIPT"])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)          # unguarded: import itself must not raise

try:
    data = json.loads(sys.stdin.read() or "{}")
    if not isinstance(data, dict):
        data = {}
except Exception:
    data = {}
cwd = data.get("cwd") or "."

root = Path(cwd)
state = m.find_state(cwd)
pinned = None
if state is not None:
    try:
        pinned = Path(json.loads(state.read_text())["plan"])
    except Exception:
        pinned = None                # a corrupt state file pins nothing

plans = m.portfolio_plans_dir(root)
if plans is None:
    print("RESOLVED=none")           # a degraded resolve, reached without raising
else:
    found = m.discover_plans(plans, pinned=pinned,
                             cache_file=root / ".claude" / m.CACHE_NAME)
    print("DISCOVERED=%d" % len(found))
PYEOF

PLAN_BODY='### Task 1.1: a
- **Status:** [x]

### Task 1.2: b
- **Status:** [ ]
'

# build_env <name> -> echoes the repo root; sets up a HOME + repo pair
build_env() {
  local name="$1"
  local root="$TMP/$name"
  mkdir -p "$root/home/.claude" "$root/repo/.claude" "$root/vault/Portfolio/a/p/plans"
  printf '%s' "$PLAN_BODY" > "$root/vault/Portfolio/a/p/plans/2026-01-01-x-plan.md"
  cat > "$root/home/.claude/portfolio-config.yaml" <<EOF
version: 1
vault_dir: $root/vault
EOF
  cat > "$root/home/.claude/projects-registry.yaml" <<EOF
version: 1
projects:
  - path: $root/repo
    name: p
    area: a
    enabled: true
EOF
  cat > "$root/repo/.claude/plan-progress.json" <<EOF
{"plan": "$root/vault/Portfolio/a/p/plans/2026-01-01-x-plan.md", "phase": "task", "stage": 1, "task": "1.1", "task_desc": "x"}
EOF
  echo "$root"
}

# run_lane <label> <lane-name> <repo-root> <home> <python-target>
# Asserts exit 0 and EMPTY stderr. stdout may be empty or a bar, but must never
# carry a traceback — a rendered bar is fine, a Python traceback never is.
# Only `Traceback` is matched: the earlier `*"Error"*` pattern would have failed
# on a legitimate task description containing the word (e.g. "Handle Error
# case"), and stderr being empty already catches the real thing.
run_lane() {
  local label="$1" lane="$2" repo="$3" home="$4" target="$5"
  local out err rc bad=0
  err="$TMP/err.$cases.$lane"
  out="$(printf '{"cwd": "%s"}' "$repo" | HOME="$home" PP_SCRIPT="$SCRIPT" \
         python3 "$target" 2>"$err")"
  rc=$?
  [ "$rc" != 0 ] && { echo "FAIL: $label [$lane] — exit $rc, wanted 0"; bad=1; }
  [ -s "$err" ] && { echo "FAIL: $label [$lane] — stderr not empty: $(head -c 300 "$err")"; bad=1; }
  case "$out" in
    *Traceback*) echo "FAIL: $label [$lane] — traceback on stdout: $out"; bad=1 ;;
  esac
  return $bad
}

# expect_quiet <label> <repo-root> <home>
# Both lanes must be silent. Lane B is what makes this a claim about the Stage 2
# surface rather than about code the entry point never reaches.
expect_quiet() {
  local label="$1" repo="$2" home="$3"
  cases=$((cases + 1))
  local bad=0
  run_lane "$label" "entry" "$repo" "$home" "$SCRIPT"  || bad=1
  run_lane "$label" "discovery" "$repo" "$home" "$DRIVER" || bad=1
  if [ "$bad" = 1 ]; then fail=1; else echo "  ok: $label"; fi
}

echo "silence-when-broken corpus:"

# 0. the healthy baseline — proves each lane can actually reach its subject, so a
#    green sweep is not just "everything is broken everywhere". One guard per
#    lane: a lane that silently no-ops would otherwise report every case as a
#    pass, which is the exact failure this whole file was rewritten to close.
R="$(build_env healthy)"
out="$(printf '{"cwd": "%s"}' "$R/repo" | HOME="$R/home" python3 "$SCRIPT" 2>/dev/null)"
if [ -z "$out" ]; then
  echo "FAIL: baseline [entry] — expected a rendered bar, got nothing (lane A would be vacuous)"
  fail=1
else
  echo "  ok: baseline renders a bar (lane A is not vacuously green)"
fi
cases=$((cases + 1))

drv="$(printf '{"cwd": "%s"}' "$R/repo" | HOME="$R/home" PP_SCRIPT="$SCRIPT" \
       python3 "$DRIVER" 2>/dev/null)"
case "$drv" in
  DISCOVERED=[1-9]*)
    echo "  ok: baseline reaches discovery — $drv (lane B is not vacuously green)" ;;
  *)
    echo "FAIL: baseline [discovery] — expected DISCOVERED=<n>=1, got '${drv:-<nothing>}'."
    echo "      Lane B is not reaching discover_plans, so every silence claim it"
    echo "      makes below is about code it never ran."
    fail=1 ;;
esac
cases=$((cases + 1))

# 1. absent portfolio config
R="$(build_env no-config)"; rm -f "$R/home/.claude/portfolio-config.yaml"
expect_quiet "absent portfolio-config.yaml" "$R/repo" "$R/home"

# 2. absent registry
R="$(build_env no-registry)"; rm -f "$R/home/.claude/projects-registry.yaml"
expect_quiet "absent projects-registry.yaml" "$R/repo" "$R/home"

# 3. malformed config / registry
R="$(build_env bad-config)"; printf 'vault_dir: {{{ nope\n' > "$R/home/.claude/portfolio-config.yaml"
expect_quiet "malformed portfolio-config.yaml" "$R/repo" "$R/home"
R="$(build_env bad-registry)"; printf 'projects: [[[\n' > "$R/home/.claude/projects-registry.yaml"
expect_quiet "malformed projects-registry.yaml" "$R/repo" "$R/home"

# 4. vault path missing, and vault path unreadable
R="$(build_env no-vault)"; rm -rf "$R/vault"
expect_quiet "vault directory does not exist" "$R/repo" "$R/home"
R="$(build_env locked-vault)"; chmod 000 "$R/vault"
expect_quiet "vault directory unreadable" "$R/repo" "$R/home"
chmod 755 "$R/vault" 2>/dev/null

# 5. corrupt scan cache, in several shapes
for shape in 'truncated' 'binary' 'wrongtype'; do
  R="$(build_env "bad-cache-$shape")"
  case "$shape" in
    truncated) printf '{"version": 1, "signat' > "$R/repo/.claude/plan-progress-cache.json" ;;
    binary)    printf '\x00\x01\x02 junk'      > "$R/repo/.claude/plan-progress-cache.json" ;;
    wrongtype) printf '[1,2,3]'                > "$R/repo/.claude/plan-progress-cache.json" ;;
  esac
  expect_quiet "corrupt scan cache ($shape)" "$R/repo" "$R/home"
done

# 6. corrupt / empty / wrong-shaped state file
R="$(build_env bad-state)"; printf '{not json' > "$R/repo/.claude/plan-progress.json"
expect_quiet "corrupt state file" "$R/repo" "$R/home"
R="$(build_env empty-state)"; : > "$R/repo/.claude/plan-progress.json"
expect_quiet "empty state file" "$R/repo" "$R/home"
R="$(build_env array-state)"; printf '[]' > "$R/repo/.claude/plan-progress.json"
expect_quiet "state file is a JSON array, not an object" "$R/repo" "$R/home"

# 7. the plan the state file names is gone
R="$(build_env plan-deleted)"; rm -f "$R/vault/Portfolio/a/p/plans/2026-01-01-x-plan.md"
expect_quiet "plan file deleted out from under the state file" "$R/repo" "$R/home"

# 8. plans dir unreadable mid-run
R="$(build_env locked-plans)"; chmod 000 "$R/vault/Portfolio/a/p/plans"
expect_quiet "plans directory unreadable" "$R/repo" "$R/home"
chmod 755 "$R/vault/Portfolio/a/p/plans" 2>/dev/null

# 9. plan file present but unreadable
R="$(build_env locked-plan)"; chmod 000 "$R/vault/Portfolio/a/p/plans/2026-01-01-x-plan.md"
expect_quiet "plan file unreadable" "$R/repo" "$R/home"
chmod 644 "$R/vault/Portfolio/a/p/plans/2026-01-01-x-plan.md" 2>/dev/null

# 10. read-only .claude (cache cannot be written)
R="$(build_env ro-claude)"; chmod 500 "$R/repo/.claude"
expect_quiet "read-only .claude (cache unwritable)" "$R/repo" "$R/home"
chmod 700 "$R/repo/.claude" 2>/dev/null

# 11. HOME itself unset / pointing nowhere
R="$(build_env no-home)"
expect_quiet "HOME points at a nonexistent directory" "$R/repo" "$TMP/does-not-exist"

# 12. garbage on stdin
for stdin_val in '' 'not json at all' '{}' '[]' '{"cwd": null}'; do
  cases=$((cases + 1))
  err="$TMP/err.stdin.$cases"
  out="$(printf '%s' "$stdin_val" | HOME="$TMP/healthy/home" python3 "$SCRIPT" 2>"$err")"
  rc=$?
  if [ "$rc" != 0 ] || [ -s "$err" ]; then
    echo "FAIL: stdin=${stdin_val:-<empty>} — exit $rc, stderr: $(head -c 120 "$err")"; fail=1
  else
    echo "  ok: stdin=${stdin_val:-<empty>} handled quietly"
  fi
done

echo
if [ "$fail" -eq 0 ]; then
  echo "OK — $cases corpus members, every one silent (exit 0, clean stderr, no traceback)"
  exit 0
fi
echo "FAILED"
exit 1
