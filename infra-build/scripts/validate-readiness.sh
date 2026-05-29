#!/usr/bin/env bash
# validate-readiness.sh <project-root> [--json]
# Deterministic source-repo readiness signals for the build-for-mac (Rust→.pkg)
# and publish-images (Docker) pipelines — the project-side file checks from the
# build-readiness-check skill. Cross-repo registration sync (programs.txt /
# images.yml / workflow YAML in the infra repos) stays judgment and is NOT
# checked here. Absent = info (pipeline not applicable), malformed-when-present
# = warn/error.
set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/lib/findings.sh"
have_jq

JSON=0; ARGS=()
for a in "$@"; do case "$a" in --json) JSON=1 ;; *) ARGS+=("$a") ;; esac; done
[ "$JSON" = 1 ] && export FINDINGS_JSON=1
ROOT="${ARGS[0]:-.}"
ROOT="$(cd "$ROOT" 2>/dev/null && pwd || true)"
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "usage: $0 <project-root> [--json]" >&2; exit 2; }

# --- build-for-mac (Rust → macOS .pkg) ---------------------------------------
if [ ! -d "$ROOT/mac" ]; then
  add_finding info mac-absent readiness "mac/" 0 "no mac/ tree (fine if not shipping a macOS .pkg)"
else
  [ -f "$ROOT/Cargo.toml" ] \
    || add_finding warn mac-no-cargo readiness "Cargo.toml" 0 "mac/ present but no Cargo.toml at root — the build-for-mac workflow builds with cargo"
  mk="$ROOT/mac/Makefile"
  if [ ! -f "$mk" ]; then
    add_finding error mac-no-makefile readiness "mac/Makefile" 0 "mac/ present but mac/Makefile is missing"
  else
    for t in build package clean; do
      grep -Eq "^$t:" "$mk" \
        || add_finding warn mac-makefile-target readiness "mac/Makefile" 0 "mac/Makefile has no '$t:' target (the workflow runs make $t)"
    done
  fi
  [ -d "$ROOT/mac/payload" ] \
    || add_finding warn mac-no-payload readiness "mac/payload/" 0 "no mac/payload/ — pkgbuild --root has nothing to package"
fi

# --- publish-images (multi-arch Docker) --------------------------------------
if [ -f "$ROOT/Dockerfile" ]; then
  # source-side dispatch wiring is recommended; grep for it (judgment to fix)
  if [ -d "$ROOT/.github/workflows" ] && ! grep -rqs 'repository_dispatch' "$ROOT/.github/workflows" 2>/dev/null; then
    add_finding info images-no-dispatch readiness ".github/workflows/" 0 "Dockerfile present but no repository_dispatch wiring found — tag→republish won't be automatic (optional)"
  fi
else
  add_finding info images-absent readiness "Dockerfile" 0 "no Dockerfile (fine if not publishing a container image)"
fi

render_findings "validate-readiness.sh" "$ROOT"; exit $?
