#!/usr/bin/env bash
# validate-catalog-diff.sh <target-project-root> [--json] [--framework <name>] [--source-locale <code>]
#
# Thin deterministic-lane wrapper over the existing Python catalog differ
#   skills/i18n-audit/scripts/diff-catalogs.py
# It does NOT re-implement the diff — it runs the Python against the target
# project, parses its JSON, and re-emits the gaps as findings on the shared
# plugin-dev contract (lib/findings.sh).
#
# Rule ids (stable, kebab-case):
#   i18n-missing-key            key in source locale, absent from a target locale
#   i18n-stale-key              key whose placeholder set differs from source
#                               (translation exists but is structurally wrong)
#   i18n-extra-key              key in a target locale with no source counterpart
#
# Framework: auto-detected via detect-framework.py when --framework is omitted.
# All detected frameworks are diffed.
set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/findings.sh
. "$DIR/lib/findings.sh"
have_jq

PLUGIN_ROOT="$(cd "$DIR/.." && pwd)"
DETECT_PY="$PLUGIN_ROOT/skills/i18n-audit/scripts/detect-framework.py"
DIFF_PY="$PLUGIN_ROOT/skills/i18n-audit/scripts/diff-catalogs.py"

JSON=0
FRAMEWORK=""
SOURCE_LOCALE="en"
ROOT=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --json) JSON=1 ;;
    --framework) FRAMEWORK="${2:-}"; shift ;;
    --source-locale) SOURCE_LOCALE="${2:-}"; shift ;;
    *) [ -z "$ROOT" ] && ROOT="$1" ;;
  esac
  shift
done

[ "$JSON" = 1 ] && export FINDINGS_JSON=1
ROOT="$(cd "${ROOT:-.}" 2>/dev/null && pwd || true)"
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "usage: $0 <target-project-root> [--json] [--framework <name>] [--source-locale <code>]" >&2; exit 2; }

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required to run diff-catalogs.py" >&2
  exit 3
fi

# Determine which frameworks to diff.
frameworks=()
if [ -n "$FRAMEWORK" ]; then
  frameworks+=("$FRAMEWORK")
else
  detected="$(python3 "$DETECT_PY" "$ROOT" 2>/dev/null || echo '{}')"
  while IFS= read -r fw; do
    [ -n "$fw" ] && frameworks+=("$fw")
  done < <(printf '%s' "$detected" | jq -r '(.frameworks // [])[].framework' 2>/dev/null || true)
fi

if [ "${#frameworks[@]}" -eq 0 ]; then
  add_finding info i18n-no-framework i18n "$ROOT" 0 \
    "no i18n framework detected; nothing to diff"
  render_findings "validate-catalog-diff.sh" "$ROOT"
  exit $?
fi

for fw in "${frameworks[@]}"; do
  out="$(python3 "$DIFF_PY" "$ROOT" --framework "$fw" --source-locale "$SOURCE_LOCALE" 2>/dev/null || true)"
  if [ -z "$out" ] || ! printf '%s' "$out" | jq -e . >/dev/null 2>&1; then
    add_finding warn i18n-diff-failed i18n "$ROOT" 0 \
      "diff-catalogs.py produced no parseable output for framework $fw"
    continue
  fi
  if printf '%s' "$out" | jq -e 'has("error")' >/dev/null 2>&1; then
    add_finding info i18n-no-catalogs i18n "$ROOT" 0 \
      "no catalogs found for framework $fw"
    continue
  fi

  # missing[locale] = [keys]
  while IFS=$'\t' read -r locale key; do
    [ -n "$key" ] || continue
    add_finding error i18n-missing-key i18n "$ROOT" 0 \
      "[$fw] locale '$locale' is missing key '$key' (present in source '$SOURCE_LOCALE')"
  done < <(printf '%s' "$out" | jq -r '.missing | to_entries[] | .key as $l | .value[] | [$l, .] | @tsv')

  # placeholder_mismatch[locale] = [keys]  -> stale
  while IFS=$'\t' read -r locale key; do
    [ -n "$key" ] || continue
    add_finding error i18n-stale-key i18n "$ROOT" 0 \
      "[$fw] locale '$locale' key '$key' has a placeholder set differing from source — translation is stale/structurally wrong"
  done < <(printf '%s' "$out" | jq -r '.placeholder_mismatch | to_entries[] | .key as $l | .value[] | [$l, .] | @tsv')

  # extra[locale] = [keys]
  while IFS=$'\t' read -r locale key; do
    [ -n "$key" ] || continue
    add_finding warn i18n-extra-key i18n "$ROOT" 0 \
      "[$fw] locale '$locale' has key '$key' with no source counterpart (likely stale/removed)"
  done < <(printf '%s' "$out" | jq -r '.extra | to_entries[] | .key as $l | .value[] | [$l, .] | @tsv')
done

render_findings "validate-catalog-diff.sh" "$ROOT"
exit $?
