#!/usr/bin/env bash
# Canonical test runner for this repo — every suite, regardless of language.
#
# Why this exists: the repo's suites live in five homes and two languages, and the
# invocation that plans used to carry in their Preflight block globbed only
# `planning/skills/*/tests/test-*.py scripts/tests/test-*.py`. That glob cannot see a
# bash suite, so `android-dev/skills/android-mcp-orchestrator/scripts/tests/test-mount-validation.sh`
# was silently skipped by anyone running "the suite" locally. Discovery here is by
# filename over the whole tree rather than by an enumerated list of directories, so a
# suite added in a new home or a new language is picked up without editing this file.
#
# Usage:
#   bash scripts/run-tests.sh          run every suite, then every validator
#   bash scripts/run-tests.sh --list   print discovered suite paths, run nothing
#
# --list prints suites only (the test-*.py / test-*.sh set). Validators are named
# explicitly below: they are checks over the tree rather than test suites, so counting
# them as suites would make the discovery contract in
# scripts/tests/test-run-tests-discovery.py compare two different sets.
#
# Exit 0 only when every suite and every validator passed.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1

# Checks over the tree, not test suites. Run after the suites, reported the same way.
VALIDATORS=(
  "planning/skills/dispatching-parallel-agents/scripts/validate-stack-routing.py"
)

discover() {
  find . -path ./node_modules -prune -o \
       \( -name 'test-*.py' -o -name 'test-*.sh' \) -print \
    | sed 's|^\./||' \
    | sort
}

# A suite written in a language this runner cannot execute must FAIL, never be
# skipped. Silently ignoring it is precisely BL-020 in a new language: the bash
# suite was invisible to a python-only glob and nobody noticed for weeks. Scoped
# to tests/ directories so it cannot fire on test-scope-tiers.md or a
# test-fixtures/ data directory, and __pycache__ is excluded so stale .pyc files
# are not mistaken for suites.
unsupported() {
  find . -path ./node_modules -prune -o -path '*/__pycache__' -prune -o \
       -type f -path '*/tests/*' -name 'test-*' \
       ! -name '*.py' ! -name '*.sh' -print \
    | sed 's|^\./||' \
    | sort
}

mapfile -t SUITES < <(discover)
mapfile -t UNSUPPORTED < <(unsupported)

if [ "${#UNSUPPORTED[@]}" -ne 0 ]; then
  echo "FAIL: ${#UNSUPPORTED[@]} suite file(s) in a language this runner cannot run:" >&2
  printf '  %s\n' "${UNSUPPORTED[@]}" >&2
  echo "Supported suite extensions: .py, .sh. Add an interpreter to run_one() in $0." >&2
  exit 1
fi

# An empty sweep must never read as a pass — the same rule validate-plan-progress.yml
# states in its own words ("the glob is wrong, not the tree"). A runner that finds
# nothing and exits 0 is worse than no runner: it reports success for zero coverage.
if [ "${#SUITES[@]}" -eq 0 ]; then
  echo "FAIL: discovered 0 test suites under $REPO — the discovery glob is wrong, not the tree." >&2
  exit 1
fi

if [ "${1:-}" = "--list" ]; then
  printf '%s\n' "${SUITES[@]}"
  exit 0
fi

if [ "$#" -gt 0 ]; then
  echo "FAIL: unknown argument '$1' (accepts no arguments, or --list)" >&2
  exit 1
fi

failed=()

run_one() {
  local path="$1"
  case "$path" in
    *.py) python3 "$path" ;;
    *.sh) bash "$path" ;;
    *)
      # Unreachable via discover(), which only emits .py/.sh — kept as a guard so
      # adding an extension to discover() without adding an interpreter here fails
      # loudly instead of running nothing.
      echo "FAIL: $path has no known interpreter (expected .py or .sh)" >&2
      return 1
      ;;
  esac
}

echo "Running ${#SUITES[@]} suite(s):"
for suite in "${SUITES[@]}"; do
  echo "== $suite"
  if ! run_one "$suite" > /dev/null 2>&1; then
    # Re-run visibly so the failure output is the last thing on screen, not swallowed.
    echo "-- FAILED, re-running with output:"
    run_one "$suite"
    failed+=("$suite")
  fi
done

echo "Running ${#VALIDATORS[@]} validator(s):"
for validator in "${VALIDATORS[@]}"; do
  echo "== $validator"
  if [ ! -f "$validator" ]; then
    echo "FAIL: validator $validator does not exist" >&2
    failed+=("$validator")
    continue
  fi
  if ! python3 "$validator" > /dev/null 2>&1; then
    echo "-- FAILED, re-running with output:"
    python3 "$validator"
    failed+=("$validator")
  fi
done

if [ "${#failed[@]}" -ne 0 ]; then
  echo
  echo "FAIL: ${#failed[@]} of $(( ${#SUITES[@]} + ${#VALIDATORS[@]} )) checks failed:" >&2
  printf '  %s\n' "${failed[@]}" >&2
  exit 1
fi

echo
echo "OK — ${#SUITES[@]} suite(s) and ${#VALIDATORS[@]} validator(s) passed."
