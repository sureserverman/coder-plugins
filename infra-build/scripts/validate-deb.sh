#!/usr/bin/env bash
# validate-deb.sh <project-root> [--json]
# Deterministic validation of a project's deb/ packaging tree against the
# infra/utils pipeline's expectations (the deb-package skill's validation.md
# checklist, made executable). Emits the shared JSON finding contract.
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

# A project may legitimately ship no deb/ tree (mac-only / image-only). Treat an
# absent tree as info, not error — only validate what is present.
if [ ! -d "$ROOT/deb" ]; then
  add_finding info deb-absent deb "deb/" 0 "no deb/ tree (fine if this project is not Debian-packaged)"
  render_findings "validate-deb.sh" "$ROOT"; exit $?
fi

# structure must be deb/package/DEBIAN/, not deb/DEBIAN/ or package/DEBIAN/
if [ ! -d "$ROOT/deb/package/DEBIAN" ]; then
  add_finding error deb-structure deb "deb/" 0 "expected deb/package/DEBIAN/ layout — not found"
  render_findings "validate-deb.sh" "$ROOT"; exit $?
fi

CONTROL="$ROOT/deb/package/DEBIAN/control"
if [ ! -f "$CONTROL" ]; then
  add_finding error deb-no-control deb "deb/package/DEBIAN/control" 0 "DEBIAN/control is missing"
else
  for field in Package Version Architecture Maintainer Description; do
    grep -Eq "^$field:[[:space:]]*[^[:space:]]" "$CONTROL" \
      || add_finding error deb-control-field deb "deb/package/DEBIAN/control" 0 "control is missing required field: $field"
  done
  # trailing whitespace breaks some dpkg-deb versions
  if grep -nq '[[:space:]]$' "$CONTROL"; then
    ln=$(grep -n '[[:space:]]$' "$CONTROL" | head -1 | cut -d: -f1)
    add_finding warn deb-control-trailing-ws deb "deb/package/DEBIAN/control" "${ln:-0}" "control has trailing whitespace"
  fi
  # Architecture: all is wrong for a compiled binary if usr/bin has files
  arch=$(grep -E '^Architecture:' "$CONTROL" | head -1 | sed 's/^Architecture:[[:space:]]*//')
  if [ "$arch" = "all" ] && [ -n "$(find "$ROOT/deb/package/usr/bin" -type f 2>/dev/null)" ]; then
    add_finding warn deb-arch-all deb "deb/package/DEBIAN/control" 0 "Architecture: all but usr/bin/ ships binaries — use amd64/arm64"
  fi
fi

# maintainer scripts: shebang + executable bit
for s in postinst preinst prerm postrm; do
  f="$ROOT/deb/package/DEBIAN/$s"
  [ -f "$f" ] || continue
  head -1 "$f" | grep -Eq '^#!/' \
    || add_finding error deb-script-no-shebang deb "deb/package/DEBIAN/$s" 1 "$s has no shebang"
  [ -x "$f" ] \
    || add_finding error deb-script-not-exec deb "deb/package/DEBIAN/$s" 0 "$s is not executable (chmod 755)"
  # user-level systemd must use --global; bare $USER is a known footgun
  if grep -Eq 'systemctl[[:space:]]+enable' "$f" && [ -d "$ROOT/deb/package/etc/systemd/user" ]; then
    add_finding warn deb-systemctl-not-global deb "deb/package/DEBIAN/$s" 0 "use 'systemctl --global enable' for user units, not 'systemctl enable'"
  fi
  if grep -Eq '(^|[^A-Z_])\$USER\b' "$f" && ! grep -q 'SUDO_USER' "$f"; then
    add_finding warn deb-bare-user deb "deb/package/DEBIAN/$s" 0 "bare \$USER under sudo resolves to root — use \"\${SUDO_USER:-\$USER}\""
  fi
done

# user-level systemd units belong under etc/systemd/user/, not system/
if [ -d "$ROOT/deb/package/etc/systemd/system" ] && [ ! -d "$ROOT/deb/package/etc/systemd/user" ]; then
  add_finding info deb-systemd-system deb "deb/package/etc/systemd/system" 0 "units under systemd/system/ — confirm these are system daemons, not user units (those go in systemd/user/)"
fi

# per-arch staging dirs the publish pipeline stages into
for a in amd64 arm64; do
  [ -d "$ROOT/deb/$a" ] || add_finding info deb-no-arch-dir deb "deb/$a/" 0 "no deb/$a/ staging dir (pkgskel creates it; fine pre-scaffold)"
done

render_findings "validate-deb.sh" "$ROOT"; exit $?
