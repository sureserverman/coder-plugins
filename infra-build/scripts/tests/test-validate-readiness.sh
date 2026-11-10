#!/usr/bin/env bash
# test-validate-readiness.sh — the mac/Makefile target check must match the
# build-for-mac workflow, which runs `make -C "<program>/mac" pkg`.
# A Makefile with `pkg:` must get no mac-makefile-target warning; one with only
# `package:` must get a warning that names `pkg`. Asserts on output, not on the
# script's exit code (warnings exit 0, errors exit 1).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/../validate-readiness.sh"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-validate-readiness.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

make_fixture() { # <dir> <makefile-target>
  local d="$1" target="$2"
  mkdir -p "$d/mac/payload"
  printf '[package]\nname = "fixture"\nversion = "0.1.0"\n' > "$d/Cargo.toml"
  printf 'build:\n\t@true\n\n%s: build\n\t@true\n\nclean:\n\t@true\n' "$target" > "$d/mac/Makefile"
}

FAILS=0
fail() { echo "FAIL: $*" >&2; FAILS=$((FAILS + 1)); }

make_fixture "$TMP/has-pkg" pkg
make_fixture "$TMP/has-package" package

out_pkg="$(bash "$SCRIPT" "$TMP/has-pkg" 2>&1 || true)"
out_package="$(bash "$SCRIPT" "$TMP/has-package" 2>&1 || true)"

# Guard against a vacuous pass: the script must have actually run and rendered.
for o in "$out_pkg" "$out_package"; do
  grep -q 'validate-readiness' <<<"$o" || fail "script produced no rendered findings: $o"
done

if grep -q 'mac-makefile-target' <<<"$out_pkg"; then
  fail "pkg: fixture got a mac-makefile-target warning:"
  grep 'mac-makefile-target' <<<"$out_pkg" >&2
fi

target_lines="$(grep 'mac-makefile-target' <<<"$out_package" || true)"
if ! grep -q "'pkg:'" <<<"$target_lines"; then
  fail "package:-only fixture did not get a mac-makefile-target warning naming pkg:"
  echo "$out_package" >&2
fi

# The workflow runs only `make pkg`; the project's Makefile does its own cargo
# build, wherever its Cargo.toml lives (multitor keeps it in rust/). A crate
# outside the repo root must not draw a warning about the workflow.
make_fixture "$TMP/nested-crate" pkg
mkdir -p "$TMP/nested-crate/rust"
mv "$TMP/nested-crate/Cargo.toml" "$TMP/nested-crate/rust/Cargo.toml"
out_nested="$(bash "$SCRIPT" "$TMP/nested-crate" 2>&1 || true)"
grep -q 'validate-readiness' <<<"$out_nested" || fail "script produced no rendered findings: $out_nested"
if grep -q 'mac-no-cargo' <<<"$out_nested"; then
  fail "a crate outside the repo root got a mac-no-cargo warning:"
  grep 'mac-no-cargo' <<<"$out_nested" >&2
fi

if [ "$FAILS" -gt 0 ]; then
  echo "test-validate-readiness: $FAILS failure(s)" >&2
  exit 1
fi
echo "test-validate-readiness: OK"
