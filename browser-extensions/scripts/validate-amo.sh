#!/usr/bin/env bash
# validate-amo.sh <extension-dir> [--json]
#
# Thin determinism-lane wrapper around amo-check.py. It does NOT reimplement any
# AMO check — it runs the existing Python linter against a target browser-extension
# directory, parses its per-finding lines, and re-emits them on the plugin-dev
# shared JSON finding contract via add_finding/render_findings.
#
# amo-check.py prints lines of the form:
#   [FAIL] §<section> <Section Name>: <detail>
#   [WARN] §<section> <Section Name>: <detail>
# followed by a markdown summary table (ignored here). Its exit code is
# 0 = no FAIL, 1 = at least one FAIL, 2 = usage error.
#
# Mapping:
#   FAIL -> error,  WARN -> warn,  anything else -> info
#   §1 amo-manifest-field      §6  amo-remote-script
#   §2 amo-manifest-conditional §7  amo-code-quality
#   §3 amo-icon                §8  amo-data-privacy
#   §4 amo-file-structure      §9  amo-content-script
#   §5 amo-permission          §10 amo-mv3
#
# Semantic judgment (is <all_urls> necessary? is this obfuscation? DOM-injection
# safety) stays in the LLM lane (amo-compliance-check SKILL.md). This script only
# surfaces the mechanical, decidable findings.
set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/lib/findings.sh"
have_jq

# amo-check.py lives in the skill's scripts/ dir, one level up from this scripts/.
PY="$DIR/../skills/amo-compliance-check/scripts/amo-check.py"

JSON=0; ARGS=()
for a in "$@"; do case "$a" in --json) JSON=1 ;; *) ARGS+=("$a") ;; esac; done
[ "$JSON" = 1 ] && export FINDINGS_JSON=1

EXT="${ARGS[0]:-}"
[ -n "$EXT" ] || { echo "usage: $0 <extension-dir> [--json]" >&2; exit 2; }
EXT="$(cd "$EXT" 2>/dev/null && pwd || true)"
[ -n "$EXT" ] && [ -d "$EXT" ] || { echo "usage: $0 <extension-dir> [--json]" >&2; exit 2; }
[ -f "$PY" ] || { echo "error: amo-check.py not found at $PY" >&2; exit 2; }

# map a section number to a stable kebab-case rule id
rule_for_section() {
  case "$1" in
    1)  echo amo-manifest-field ;;
    2)  echo amo-manifest-conditional ;;
    3)  echo amo-icon ;;
    4)  echo amo-file-structure ;;
    5)  echo amo-permission ;;
    6)  echo amo-remote-script ;;
    7)  echo amo-code-quality ;;
    8)  echo amo-data-privacy ;;
    9)  echo amo-content-script ;;
    10) echo amo-mv3 ;;
    *)  echo amo-check ;;
  esac
}

# Run the existing Python linter. Capture stdout; tolerate its non-zero exit
# (1 = found FAILs) without aborting under `set -e`.
out=$(python3 "$PY" "$EXT" 2>/dev/null) || true

# Parse only the per-finding lines: "[SEV] §N <Name>: <detail>".
# The summary table and trailing note are ignored.
while IFS= read -r line; do
  case "$line" in
    '['*']'' §'*) ;;
    *) continue ;;
  esac
  sev=${line%%]*}; sev=${sev#[}
  rest=${line#*§}
  sec=${rest%%[!0-9]*}
  detail=${rest#*: }
  case "$sev" in
    FAIL) severity=error ;;
    WARN) severity=warn ;;
    *)    severity=info ;;
  esac
  add_finding "$severity" "$(rule_for_section "$sec")" amo "$EXT" 0 "$detail"
done <<EOF
$out
EOF

render_findings "validate-amo.sh" "$EXT"
exit $?
