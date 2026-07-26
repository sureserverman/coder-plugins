#!/bin/bash
# Regression guard for up.sh's mount-source validation.
#
# What it protects: podman creates an EMPTY directory for a bind-mount source
# that does not exist, so a wrong APK_DIR would otherwise surface as "no APK
# found" from inside the container minutes later instead of as an error. up.sh
# validates both mount sources up front, and must resolve them the same way
# compose does — shell environment first, then the .env file. An earlier draft
# checked only the environment, which rejected the .env-only configuration the
# READMEs recommend; cases 5-8 exist to keep that bug from returning.
#
# Runs the SHIPPED code: the validation block is extracted verbatim from up.sh
# (from `cd "$COMPOSE_DIR"` through the screenshot-dir guard) so the test cannot
# drift from the real script, and running it in isolation builds no image and
# starts no container.
#
# Usage: ./test-mount-validation.sh    (exit 0 = pass)
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UP_SH="$SCRIPT_DIR/../up.sh"
# scripts/tests -> scripts -> skill -> skills -> plugin-root -> repo-root
REPO="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
COMPOSE_YAML="$REPO/android-dev/infrastructure/compose.yaml"

[ -f "$UP_SH" ] || { echo "FAIL: cannot find up.sh at $UP_SH"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

BLOCK="$TMP/block.sh"
awk '/^cd "\$COMPOSE_DIR"$/{f=1} f{print} f&&/^# Skip-build guard/{exit}' "$UP_SH" >"$BLOCK"
grep -q 'APK directory does not exist' "$BLOCK" || { echo "FAIL: extraction missed the validation block"; exit 1; }
grep -q 'ENV_FILE' "$BLOCK" || { echo "FAIL: extraction missed the .env fold-in"; exit 1; }

fail=0
DOTENV=""   # optional .env content for the next run()
LAST_DIR=""
run() {  # run(env-assignments...) in a fresh compose dir; echoes "<exit>|<output>"
  local d="$TMP/case$RANDOM$RANDOM"; mkdir -p "$d"
  [ -n "$DOTENV" ] && printf '%s\n' "$DOTENV" >"$d/.env"
  local out rc=0
  out="$(cd "$d" && env "$@" COMPOSE_DIR="$d" ENV_FILE="$d/.env" bash -c "source '$BLOCK'" 2>&1)" || rc=$?
  printf '%s|%s' "$rc" "$out"
  LAST_DIR="$d"
}
expect() { # expect <label> <want-rc> <want-substring> <result>
  local label="$1" want_rc="$2" want_sub="$3" res="$4"
  local rc="${res%%|*}" out="${res#*|}"
  if [ "$rc" != "$want_rc" ]; then
    echo "FAIL: $label — exit $rc, wanted $want_rc"; echo "  output: $out"; fail=1; return
  fi
  if ! grep -qF "$want_sub" <<<"$out"; then
    echo "FAIL: $label — output lacks '$want_sub'"; echo "  output: $out"; fail=1; return
  fi
  echo "  ok: $label (exit $rc)"
}

good="$TMP/apks"; mkdir -p "$good"

UNSET=(-u APK_DIR -u SCREENSHOT_DIR)   # truly unset, not exported-empty

echo "case 1 — APK_DIR unset, placeholder default absent => loud failure"
expect "unset APK_DIR errors" 4 "set neither in the environment nor in" "$(run "${UNSET[@]}")"
expect "names the bundled-plugin cause" 4 "not your project" "$(run "${UNSET[@]}")"

echo "case 2 — APK_DIR set but nonexistent => loud failure naming the value"
expect "bad APK_DIR errors" 4 "APK_DIR is set to '/tmp/definitely-not-here'" \
  "$(run -u SCREENSHOT_DIR APK_DIR=/tmp/definitely-not-here)"

echo "case 3 — APK_DIR exists => passes, and SCREENSHOT_DIR is created"
shots="$TMP/shots-created"
expect "valid APK_DIR proceeds" 0 "creating screenshot output dir" \
  "$(run APK_DIR="$good" SCREENSHOT_DIR="$shots")"
[ -d "$shots" ] && echo "  ok: screenshot dir created" || { echo "FAIL: screenshot dir not created"; fail=1; }

echo "case 4 — an existing screenshot dir is left alone, no spurious message"
shots2="$TMP/shots-existing"; mkdir -p "$shots2"; : >"$shots2/keep.png"
res="$(run APK_DIR="$good" SCREENSHOT_DIR="$shots2")"
rc="${res%%|*}"; out="${res#*|}"
ok4=1
[ "$rc" = 0 ] || { echo "FAIL: existing screenshot dir gave exit $rc"; fail=1; ok4=0; }
grep -q 'creating screenshot output dir' <<<"$out" && { echo "FAIL: re-created an existing dir"; fail=1; ok4=0; }
[ -f "$shots2/keep.png" ] || { echo "FAIL: clobbered existing screenshot content"; fail=1; ok4=0; }
[ "$ok4" = 1 ] && echo "  ok: existing dir untouched, contents preserved"

echo "case 5 — APK_DIR set ONLY in .env is honored (compose reads .env; so must we)"
DOTENV="APK_DIR=$good"
res="$(run -u APK_DIR SCREENSHOT_DIR="$TMP/shots-dotenv")"; DOTENV=""
rc="${res%%|*}"
[ "$rc" = 0 ] && echo "  ok: .env-only APK_DIR accepted" \
  || { echo "FAIL: .env-only APK_DIR rejected (exit $rc) — validation ignores .env"; fail=1; }

echo "case 6 — quoted .env value is unquoted the way compose unquotes it"
DOTENV="APK_DIR=\"$good\""
res="$(run -u APK_DIR SCREENSHOT_DIR="$TMP/shots-quoted")"; DOTENV=""
rc="${res%%|*}"
[ "$rc" = 0 ] && echo "  ok: quoted .env value accepted" || { echo "FAIL: quoted .env value rejected (exit $rc)"; fail=1; }

echo "case 7 — shell env WINS over .env, matching compose precedence"
DOTENV="APK_DIR=/tmp/definitely-not-here-either"
res="$(run APK_DIR="$good" SCREENSHOT_DIR="$TMP/shots-prec")"; DOTENV=""
rc="${res%%|*}"
[ "$rc" = 0 ] && echo "  ok: shell value took precedence over .env" || { echo "FAIL: .env overrode the shell value (exit $rc)"; fail=1; }

echo "case 8 — a COMMENTED .env line is not treated as a value"
DOTENV="# APK_DIR=$good"
res="$(run -u APK_DIR SCREENSHOT_DIR="$TMP/shots-commented")"; DOTENV=""
expect "commented .env line ignored" 4 "set neither in the environment nor in" "$res"

echo "case 9 — unwritable SCREENSHOT_DIR exits 5, distinct from 4"
expect "output-dir failure is exit 5" 5 "could not create screenshot directory" \
  "$(run APK_DIR="$good" SCREENSHOT_DIR=/proc/cannot/create/here)"

echo "case 11 — APK_DIR exported EMPTY counts as set, so .env is NOT consulted"
# Verified against `podman compose config`: an exported-empty var makes compose
# ignore .env and fall through to the compose-file default. Reading .env here
# would validate a path compose was never going to mount — the only direction
# that yields the silent empty mount this guard exists to prevent.
DOTENV="APK_DIR=$good"
res="$(run -u SCREENSHOT_DIR APK_DIR=)"; DOTENV=""
expect "exported-empty APK_DIR ignores .env" 4 "APK directory does not exist" "$res"

echo "case 10 — the defaults mirrored in up.sh match the ones in compose.yaml"
# up.sh hardcodes these to validate them; compose.yaml is the source of truth.
# If either moves without the other, validation silently checks the wrong path.
for pair in 'APK_DIR:./app/build/outputs/apk/debug' 'SCREENSHOT_DIR:./play-screenshots'; do
  var="${pair%%:*}"; def="${pair#*:}"
  grep -qF "\${${var}:-${def}}" "$COMPOSE_YAML" \
    || { echo "FAIL: compose.yaml no longer defaults $var to $def"; fail=1; }
done
grep -qF 'apk_dir="${APK_DIR:-./app/build/outputs/apk/debug}"' "$UP_SH" \
  || { echo "FAIL: up.sh APK default no longer matches compose.yaml"; fail=1; }
grep -qF 'screenshot_dir="${SCREENSHOT_DIR:-./play-screenshots}"' "$UP_SH" \
  || { echo "FAIL: up.sh screenshot default no longer matches compose.yaml"; fail=1; }
[ "$fail" -eq 0 ] && echo "  ok: up.sh defaults mirror compose.yaml"

[ "$fail" -eq 0 ] || { echo; echo "FAILED"; exit 1; }
echo
echo "OK — 11 cases: missing APK_DIR fails loudly (exit 4), screenshot dir created (exit 5 on failure),"
echo "     env-then-.env precedence matches compose, defaults stay in sync with compose.yaml"
