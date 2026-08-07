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
# Usage: bash test-plan-progress-corpus.sh    (exit 0 = pass)
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/plan-progress.py"
[ -f "$SCRIPT" ] || { echo "FAIL: cannot find plan-progress.py at $SCRIPT"; exit 1; }

TMP="$(mktemp -d)"
trap 'chmod -R u+rwX "$TMP" 2>/dev/null; rm -rf "$TMP"' EXIT

fail=0
cases=0

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

# expect_quiet <label> <repo-root> <home> [<allow-output>]
# Asserts exit 0 and EMPTY stderr. stdout may be empty or a bar, but must never
# contain a traceback — a rendered bar is fine, a Python traceback never is.
expect_quiet() {
  local label="$1" repo="$2" home="$3"
  cases=$((cases + 1))
  local out err rc
  err="$TMP/err.$cases"
  out="$(printf '{"cwd": "%s"}' "$repo" | HOME="$home" python3 "$SCRIPT" 2>"$err")"
  rc=$?
  local bad=0
  [ "$rc" != 0 ] && { echo "FAIL: $label — exit $rc, wanted 0"; bad=1; }
  [ -s "$err" ] && { echo "FAIL: $label — stderr not empty: $(head -c 200 "$err")"; bad=1; }
  case "$out" in
    *Traceback*|*"Error"*) echo "FAIL: $label — traceback/error leaked to stdout: $out"; bad=1 ;;
  esac
  if [ "$bad" = 1 ]; then fail=1; else echo "  ok: $label"; fi
}

echo "silence-when-broken corpus:"

# 0. the healthy baseline — proves the harness can actually produce a bar, so a
#    green sweep is not just "everything is broken everywhere".
R="$(build_env healthy)"
out="$(printf '{"cwd": "%s"}' "$R/repo" | HOME="$R/home" python3 "$SCRIPT" 2>/dev/null)"
if [ -z "$out" ]; then
  echo "FAIL: baseline — expected a rendered bar, got nothing (the corpus would be vacuous)"
  fail=1
else
  echo "  ok: baseline renders a bar (sweep is not vacuously green)"
fi
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
