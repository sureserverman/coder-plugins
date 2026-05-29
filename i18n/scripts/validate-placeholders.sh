#!/usr/bin/env bash
# validate-placeholders.sh <target-project-root> [--json] [--framework <name>] [--source-locale <code>]
#
# Thin deterministic-lane wrapper over the existing Python placeholder/CLDR-plural
# validator
#   skills/i18n-translate/scripts/validate-placeholders.py
# and the catalog collector inside
#   skills/i18n-audit/scripts/diff-catalogs.py
#
# It does NOT re-implement any placeholder or plural logic. It:
#   1. collects each locale's catalog (reusing diff-catalogs.collect_catalogs),
#   2. builds the {key, source, translation} workpacket the Python expects,
#   3. runs validate-placeholders.py over it (the real validator),
#   4. re-emits each defect as a finding on the shared plugin-dev contract.
#
# Rule ids (stable, kebab-case):
#   i18n-placeholder-mismatch        placeholder set in translation != source
#   i18n-missing-plural-categories   target locale missing required CLDR plurals
#   i18n-unbalanced-braces           truncated/unbalanced ICU braces
#   i18n-html-tag-mismatch           HTML tag set differs from source
#   i18n-printf-type-mismatch        printf type signature differs (%s vs %d)
#   i18n-empty-translation           translation present in catalog but empty
#
# Framework: auto-detected via detect-framework.py when --framework is omitted.
set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/findings.sh
. "$DIR/lib/findings.sh"
have_jq

PLUGIN_ROOT="$(cd "$DIR/.." && pwd)"
DETECT_PY="$PLUGIN_ROOT/skills/i18n-audit/scripts/detect-framework.py"
DIFF_PY="$PLUGIN_ROOT/skills/i18n-audit/scripts/diff-catalogs.py"
PH_PY="$PLUGIN_ROOT/skills/i18n-translate/scripts/validate-placeholders.py"

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
  echo "error: python3 is required to run validate-placeholders.py" >&2
  exit 3
fi

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
    "no i18n framework detected; nothing to validate"
  render_findings "validate-placeholders.sh" "$ROOT"
  exit $?
fi

# Build a {target_locale, framework, entries:[{key,source,translation}]} workpacket
# for one (framework, target-locale) pair, reusing diff-catalogs.collect_catalogs.
# Emits the workpacket JSON on stdout, or nothing if there is no target catalog.
build_workpacket() {
  local fw="$1" target="$2"
  DIFF_PY="$DIFF_PY" SOURCE_LOCALE="$SOURCE_LOCALE" FW="$fw" TARGET="$target" ROOT="$ROOT" \
    python3 - <<'PY'
import importlib.util, json, os
from pathlib import Path

spec = importlib.util.spec_from_file_location("_diff_catalogs", os.environ["DIFF_PY"])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

root = Path(os.environ["ROOT"])
fw = os.environ["FW"]
target = os.environ["TARGET"]
src_locale = os.environ["SOURCE_LOCALE"]

catalogs = mod.collect_catalogs(root, fw)
if not catalogs:
    raise SystemExit(0)
if src_locale not in catalogs:
    src_locale = max(catalogs, key=lambda l: len(catalogs[l]))
src = catalogs[src_locale]
tgt = catalogs.get(target, {})

entries = []
for k in sorted(set(src.keys()) & set(tgt.keys())):
    entries.append({"key": k, "source": src[k], "translation": tgt[k]})

print(json.dumps({"target_locale": target, "framework": fw, "entries": entries}))
PY
}

list_target_locales() {
  local fw="$1"
  DIFF_PY="$DIFF_PY" SOURCE_LOCALE="$SOURCE_LOCALE" FW="$fw" ROOT="$ROOT" \
    python3 - <<'PY'
import importlib.util, os
from pathlib import Path

spec = importlib.util.spec_from_file_location("_diff_catalogs", os.environ["DIFF_PY"])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

root = Path(os.environ["ROOT"])
fw = os.environ["FW"]
src_locale = os.environ["SOURCE_LOCALE"]
catalogs = mod.collect_catalogs(root, fw)
if catalogs:
    if src_locale not in catalogs:
        src_locale = max(catalogs, key=lambda l: len(catalogs[l]))
    for loc in sorted(catalogs):
        if loc != src_locale:
            print(loc)
PY
}

# Map a Python defect 'kind' to a (severity, rule-id) on the shared contract.
emit_defect() {
  local fw="$1" locale="$2" kind="$3" key="$4" detail="$5"
  local sev rule
  case "$kind" in
    placeholder-mismatch)      sev=error; rule=i18n-placeholder-mismatch ;;
    missing-plural-categories) sev=error; rule=i18n-missing-plural-categories ;;
    unbalanced-braces)         sev=error; rule=i18n-unbalanced-braces ;;
    unbalanced-html)           sev=error; rule=i18n-unbalanced-html ;;
    html-tag-mismatch)         sev=warn;  rule=i18n-html-tag-mismatch ;;
    printf-type-mismatch)      sev=error; rule=i18n-printf-type-mismatch ;;
    empty-translation)         sev=warn;  rule=i18n-empty-translation ;;
    *)                         sev=warn;  rule="i18n-$kind" ;;
  esac
  local msg="[$fw] locale '$locale' key '$key': $kind"
  [ -n "$detail" ] && msg="$msg ($detail)"
  add_finding "$sev" "$rule" i18n "$ROOT" 0 "$msg"
}

any_catalog=0
for fw in "${frameworks[@]}"; do
  while IFS= read -r target; do
    [ -n "$target" ] || continue
    wp="$(build_workpacket "$fw" "$target" || true)"
    [ -n "$wp" ] || continue
    printf '%s' "$wp" | jq -e . >/dev/null 2>&1 || continue
    any_catalog=1

    report="$(printf '%s' "$wp" | python3 "$PH_PY" 2>/dev/null || true)"
    [ -n "$report" ] && printf '%s' "$report" | jq -e . >/dev/null 2>&1 || continue

    while IFS=$'\t' read -r kind key detail; do
      [ -n "$kind" ] || continue
      emit_defect "$fw" "$target" "$kind" "$key" "$detail"
    done < <(printf '%s' "$report" | jq -r '
      .defects[]? | [
        .kind,
        (.key // "?"),
        ([ (if .missing_in_translation then "missing="+(.missing_in_translation|join(",")) else empty end),
           (if .missing then "missing="+(.missing|join(",")) else empty end),
           (if .source_tags then "src_tags="+(.source_tags|join(",")) else empty end)
         ] | join("; "))
      ] | @tsv')
  done < <(list_target_locales "$fw")
done

if [ "$any_catalog" -eq 0 ]; then
  add_finding info i18n-no-catalogs i18n "$ROOT" 0 \
    "no target catalogs found to validate placeholders against"
fi

render_findings "validate-placeholders.sh" "$ROOT"
exit $?
