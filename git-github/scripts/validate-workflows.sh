#!/usr/bin/env bash
# validate-workflows.sh <repo-root> [--json]
#
# Thin wrapper that normalizes the github-workflow-audit mechanical lane onto the
# shared JSON finding contract. It does NOT re-implement any checks: it runs the
# existing audit-workflows.py against <repo-root>/.github/workflows, parses the
# Python's severity-sorted markdown table, and re-emits each row as a contract
# finding via add_finding (stable kebab-case rule-ids), ending with render_findings.
#
# The Python remains the single source of mechanical truth. Cross-workflow parity,
# reusable-workflow input/secret matching, and any fix authoring stay with the LLM
# (the github-workflow-audit SKILL).
set -eu

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/findings.sh
. "$DIR/lib/findings.sh"
have_jq

JSON=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --json) JSON=1 ;;
    *) ARGS+=("$a") ;;
  esac
done
[ "$JSON" = 1 ] && export FINDINGS_JSON=1

ROOT="${ARGS[0]:-.}"
ROOT="$(cd "$ROOT" 2>/dev/null && pwd || true)"
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "usage: $0 <repo-root> [--json]" >&2; exit 2; }

WF_DIR="$ROOT/.github/workflows"
PY="$DIR/../skills/github-workflow-audit/scripts/audit-workflows.py"

# Absent workflows directory: one info finding, clean exit.
if [ ! -d "$WF_DIR" ]; then
  add_finding info gha-no-workflows workflow ".github/workflows" 0 \
    "no .github/workflows/ directory under repo-root — nothing to audit"
  render_findings "validate-workflows.sh" "$ROOT"
  exit $?
fi

[ -f "$PY" ] || { echo "error: audit-workflows.py not found at $PY" >&2; exit 2; }

# Map a Python finding's severity + message to a stable kebab-case rule-id.
# The message text is the Python's; only the rule-id is our contract surface.
rule_for() {
  local sev="$1" msg="$2"
  case "$msg" in
    *"YAML parse error"*)                 echo "gha-syntax" ;;
    *"no on: trigger"*)                   echo "gha-syntax" ;;
    *"has no name"*)                      echo "gha-syntax" ;;
    *"has no jobs"*)                      echo "gha-syntax" ;;
    *"neither runs-on"*)                  echo "gha-syntax" ;;
    *"has no ref"*)                       echo "gha-syntax" ;;
    *"mutable branch"*)                   echo "gha-mutable-ref" ;;
    *"outdated"*)                         echo "gha-action-outdated" ;;
    *"expression injection"*)             echo "gha-injection" ;;
    *"interpolated"*)                     echo "gha-injection" ;;
    *"secret echoed"*)                    echo "gha-secret-echo" ;;
    *"hardcoded credential"*)             echo "gha-hardcoded-cred" ;;
    *"write-all"*)                        echo "gha-permissions" ;;
    *"permissions:"*)                     echo "gha-permissions" ;;
    *"broad token scope"*)                echo "gha-permissions" ;;
    *"malformed"*)                        echo "gha-malformed-if" ;;
    *"GITHUB_ENV"*)                       echo "gha-github-env-same-step" ;;
    *"needs:"*|*"not defined"*)           echo "gha-needs-undefined" ;;
    *"no timeout-minutes"*)               echo "gha-no-timeout" ;;
    *"concurrency"*)                      echo "gha-no-concurrency" ;;
    *"reusable workflow not referenced"*) echo "gha-unreferenced-reusable" ;;
    *) case "$sev" in
         error) echo "gha-error" ;;
         warn)  echo "gha-warn" ;;
         *)     echo "gha-info" ;;
       esac ;;
  esac
}

# Run the existing Python by its real path. Capture output; exit 1 (errors found)
# is expected — do not let it abort us under set -e.
RAW="$(python3 "$PY" "$ROOT" 2>/dev/null || true)"

# Parse the markdown table rows: "| # | SEV | file | line | message |".
# Skip the header row and the separator row.
while IFS= read -r line; do
  case "$line" in
    '|'*'|') : ;;
    *) continue ;;
  esac
  # Split on the pipe delimiter into fields.
  body="${line#|}"
  body="${body%|}"
  IFS='|' read -r f_num f_sev f_file f_line f_msg <<< "$body"
  # Trim surrounding whitespace.
  f_num="$(printf '%s' "$f_num" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  f_sev="$(printf '%s' "$f_sev" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  f_file="$(printf '%s' "$f_file" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  f_line="$(printf '%s' "$f_line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  f_msg="$(printf '%s' "$f_msg" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  # Header / separator / non-data rows: skip anything whose # column isn't numeric.
  case "$f_num" in
    ''|*[!0-9]*) continue ;;
  esac
  # Normalize severity vocabulary: ERROR->error, WARN->warn, INFO->info.
  case "$f_sev" in
    ERROR) sev=error ;;
    WARN)  sev=warn ;;
    INFO)  sev=info ;;
    *)     continue ;;
  esac
  rule="$(rule_for "$sev" "$f_msg")"
  add_finding "$sev" "$rule" workflow ".github/workflows/$f_file" "$f_line" "$f_msg"
done <<< "$RAW"

render_findings "validate-workflows.sh" "$ROOT"
exit $?
