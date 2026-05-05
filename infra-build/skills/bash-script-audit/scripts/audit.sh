#!/bin/bash
# bash-script-audit audit.sh — static checks + URL health + version currency
# Usage: ./audit.sh <script-path>
# Output: per-finding lines then a summary. Exit 0 if no ERROR, 1 if ERROR, 2 on usage error.

set -u

SCRIPT="${1:-}"
if [ -z "$SCRIPT" ] || [ ! -f "$SCRIPT" ]; then
  echo "usage: audit.sh <script-path>" >&2
  exit 2
fi

ERRORS=0
WARNS=0
INFOS=0

report() {
  # report <severity> <line> <msg>
  local sev="$1" line="$2" msg="$3"
  echo "[$sev] line $line: $msg"
  case "$sev" in
    ERROR) ERRORS=$((ERRORS + 1)) ;;
    WARN)  WARNS=$((WARNS + 1)) ;;
    INFO)  INFOS=$((INFOS + 1)) ;;
  esac
}

echo "=== Section 1: Structural & Syntax ==="

# Shebang count + validity
shebang_count=$(grep -c '^#!' "$SCRIPT" || true)
if [ "$shebang_count" -gt 1 ]; then
  lines=$(grep -n '^#!' "$SCRIPT" | cut -d: -f1 | tr '\n' ',' | sed 's/,$//')
  report WARN "$lines" "duplicate shebang lines"
fi
first=$(head -n1 "$SCRIPT")
case "$first" in
  '#!/bin/bash'|'#!/usr/bin/env bash'|'#!/bin/sh'|'#!/usr/bin/env sh') : ;;
  '#!'*) report WARN 1 "unusual shebang: $first" ;;
  *) report WARN 1 "no shebang on line 1" ;;
esac
# Malformed shebangs mid-script
while IFS=: read -r ln content; do
  case "$content" in
    '#!/binbash'*|'#!/bin/bahs'*|'#!/bin/bas'*) report ERROR "$ln" "malformed shebang: $content" ;;
  esac
done < <(grep -n '^#!' "$SCRIPT" | tail -n +2)

# bash -n parse check
if ! bash -n "$SCRIPT" 2> /tmp/audit-bashn.$$; then
  while IFS= read -r line; do
    report ERROR "?" "bash -n: $line"
  done < /tmp/audit-bashn.$$
fi
rm -f /tmp/audit-bashn.$$

# Tilde inside double quotes won't expand
while IFS=: read -r ln content; do
  report WARN "$ln" "tilde inside double quotes won't expand: ${content:0:100}"
done < <(grep -nE '"~/' "$SCRIPT" || true)

# sudo inconsistency on && pipelines — flag lines that have sudo on one side but not the other
while IFS=: read -r ln content; do
  # Match: "sudo CMD && CMD2" where CMD2 starts without sudo and looks like a privileged op
  if echo "$content" | grep -qE 'sudo[^&]+&&\s*(apt|apt-get|dpkg|systemctl|rm|chmod|chown|mkdir|mv|cp)\b'; then
    report WARN "$ln" "possible missing sudo after &&: ${content:0:100}"
  fi
done < <(grep -nE 'sudo.*&&' "$SCRIPT" || true)

# apt-get install without -y in a script
while IFS=: read -r ln content; do
  if echo "$content" | grep -qE 'apt(-get)?\s+install' && ! echo "$content" | grep -qE '\-y\b|--yes\b|--assume-yes\b'; then
    report WARN "$ln" "apt install without -y: ${content:0:100}"
  fi
done < <(grep -nE 'apt(-get)?\s+install' "$SCRIPT" || true)

echo
echo "=== Section 2: URL Health ==="

# Extract URLs (dedupe preserving order)
urls=$(grep -oE 'https?://[^\s"'\''<>)[:space:]]+' "$SCRIPT" | sed 's/[,;]$//' | awk '!seen[$0]++')
if [ -z "$urls" ]; then
  echo "  (no URLs found)"
fi

tor_running=0
if systemctl is-active tor >/dev/null 2>&1 || pgrep -x tor >/dev/null 2>&1; then
  tor_running=1
fi

while IFS= read -r url; do
  [ -z "$url" ] && continue
  # Find first line number where the URL appears
  ln=$(grep -nF "$url" "$SCRIPT" | head -n1 | cut -d: -f1)
  ln="${ln:-?}"
  case "$url" in
    *.onion*|*.onion/*)
      if [ "$tor_running" -eq 0 ]; then
        report INFO "$ln" ".onion skipped (tor not running): $url"
        continue
      fi
      code=$(curl -sI -o /dev/null -w '%{http_code}' -x socks5h://127.0.0.1:9050 --connect-timeout 30 "$url" 2>/dev/null || echo "000")
      if [ "$code" = "000" ]; then
        code=$(torsocks curl -sI -o /dev/null -w '%{http_code}' --connect-timeout 30 "$url" 2>/dev/null || echo "000")
      fi
      case "$code" in
        200|204|301|302) echo "  [PASS] $code  $url" ;;
        000)             report WARN "$ln" ".onion unreachable (tor circuit): $url" ;;
        *)               report WARN "$ln" ".onion HTTP $code: $url" ;;
      esac
      ;;
    *)
      code=$(curl -sI -o /dev/null -w '%{http_code}' -L --max-time 15 "$url" 2>/dev/null || echo "000")
      case "$code" in
        200|204)     echo "  [PASS] $code  $url" ;;
        301|302|307) echo "  [PASS-redirect] $code  $url" ;;
        403)         report WARN  "$ln" "HTTP 403 (may require auth/UA): $url" ;;
        404|410)     report ERROR "$ln" "HTTP $code broken link: $url" ;;
        000)         report WARN  "$ln" "unreachable (timeout/DNS): $url" ;;
        *)           report WARN  "$ln" "HTTP $code: $url" ;;
      esac
      ;;
  esac
done <<< "$urls"

echo
echo "=== Section 3: Version Currency (GitHub releases only) ==="

# Find github.com/<owner>/<repo> URLs, resolve latest release
gh_repos=$(echo "$urls" | grep -oE 'github\.com/[^/]+/[^/?#]+' | sort -u)
while IFS= read -r repo; do
  [ -z "$repo" ] && continue
  effective=$(curl -sI -o /dev/null -w '%{url_effective}' -L --max-time 15 "https://$repo/releases/latest" 2>/dev/null || echo "")
  latest=$(echo "$effective" | grep -oE 'tag/[^/]+$' | sed 's|tag/||; s|^v||')
  if [ -z "$latest" ]; then
    echo "  [INFO]  $repo — no releases or unreachable"
    continue
  fi
  # Find any version-like string in the script that matches download URLs from this repo
  script_versions=$(grep -oE "$repo/[^\" ]*" "$SCRIPT" | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | sort -u)
  if [ -z "$script_versions" ]; then
    echo "  [INFO]  $repo — latest $latest (no version in script URL)"
    continue
  fi
  while IFS= read -r sv; do
    if [ "$sv" = "$latest" ]; then
      echo "  [PASS]  $repo — $sv (current)"
    else
      ln=$(grep -nF "$sv" "$SCRIPT" | head -n1 | cut -d: -f1)
      report WARN "${ln:-?}" "$repo — script uses $sv, latest is $latest"
    fi
  done <<< "$script_versions"
done <<< "$gh_repos"

echo
echo "=== Summary ==="
echo "ERRORS: $ERRORS   WARNINGS: $WARNS   INFO: $INFOS"
echo
echo "Note: sections covered automatically — shebang, bash -n, tilde-in-quotes, sudo-in-pipelines,"
echo "apt -y, URL health (clearnet + .onion), GitHub version currency."
echo "Re-read SKILL.md for manual checks that need judgment (logic errors, rm -rf safety,"
echo "mkdir vs cp-destination mismatches, heredoc expansion intent, Flatpak ID sanity)."

[ "$ERRORS" -gt 0 ] && exit 1
exit 0
