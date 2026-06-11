#!/usr/bin/env bash
# validate-safety.sh <rust-project-root> [--json]
#
# Deterministic *candidate* scan over the target project's .rs sources for the
# mechanically detectable slice of rust-dev's house rules. Regexes only flag —
# whether a candidate is a real violation, and how to fix it, is the judgment
# lane's call (rust-expert). Hence every source-pattern rule here is warn/info,
# never error.
#
# Rule ids (stable, kebab-case — rust-dev's agents key off these):
#   rust-no-sources                     info  no .rs files under root
#   rust-unsafe-missing-safety-comment  warn  unsafe block/impl with no // SAFETY: nearby (house rule 1)
#   rust-unwrap-outside-tests           warn  .unwrap()/.expect( outside main.rs/tests/benches/examples/build.rs or #[cfg(test)] (house rule 5)
#   rust-unbounded-channel              warn  unbounded_channel()/::unbounded( usage (house rule 3)
#   rust-sync-lock-in-async-candidate   warn  std::sync Mutex/RwLock in a file that .awaits (house rule 2 candidate)
#   rust-box-dyn-error-in-pub-api       warn  pub fn returning Box<dyn ...Error...> (house rule 4)
#   rust-serde-missing-deny-unknown     warn  derive(Deserialize) without deny_unknown_fields nearby (house rule 12)
set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/lib/findings.sh"
have_jq

JSON=0; ARGS=()
for a in "$@"; do case "$a" in --json) JSON=1 ;; *) ARGS+=("$a") ;; esac; done
[ "$JSON" = 1 ] && export FINDINGS_JSON=1
ROOT="${ARGS[0]:-.}"
ROOT="$(cd "$ROOT" 2>/dev/null && pwd || true)"
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "usage: $0 <rust-project-root> [--json]" >&2; exit 2; }

FILES=()
while IFS= read -r f; do FILES+=("$f"); done < <(
  find "$ROOT" -name '*.rs' \
    -not -path '*/target/*' -not -path '*/.git/*' -not -path '*/vendor/*' \
    | LC_ALL=C sort
)

if [ "${#FILES[@]}" -eq 0 ]; then
  add_finding info rust-no-sources rust "$ROOT" 0 "no .rs files under root; nothing to scan"
  render_findings "validate-safety.sh" "$ROOT"
  exit $?
fi

# Per-file scan. awk emits TSV findings: rule \t line \t message.
# in_test flips at the first #[cfg(test)] and stays on — the conventional
# tests-mod-at-bottom layout; candidates inside it are suppressed.
scan_file() { # <abs-file> <is-unwrap-exempt 0|1>
  awk -v exempt="$2" '
    /#\[cfg\(test\)\]/ { in_test = 1 }
    /SAFETY:/          { last_safety = NR }

    /(^|[^[:alnum:]_])unsafe([[:space:]]*\{|[[:space:]]+impl[^[:alnum:]_])/ {
      if (!in_test && !(last_safety && NR - last_safety <= 3))
        printf "rust-unsafe-missing-safety-comment\t%d\tunsafe without a // SAFETY: comment within 3 lines — confirm and document the invariants\n", NR
    }

    /\.unwrap\(\)|\.expect\(/ {
      if (!in_test && exempt == "0" && $0 !~ /^[[:space:]]*\/\//)
        printf "rust-unwrap-outside-tests\t%d\t.unwrap()/.expect( outside main/tests — candidate; confirm a documented-panic contract or convert to ?\n", NR
    }

    /unbounded_channel[[:space:]]*\(|::unbounded[[:space:]]*\(/ {
      if (!in_test)
        printf "rust-unbounded-channel\t%d\tunbounded channel — bound it unless fanout is a compile-time small constant\n", NR
    }

    /pub([[:space:]]*\(.*\))?[[:space:]].*fn[[:space:]].*Box[[:space:]]*<[[:space:]]*dyn[[:space:]][^>]*Error/ {
      if (!in_test)
        printf "rust-box-dyn-error-in-pub-api\t%d\tpub fn exposes Box<dyn Error> — prefer a thiserror enum in public APIs\n", NR
    }

    /#\[derive\([^)]*Deserialize/ {
      if (!in_test && prev1 !~ /deny_unknown_fields/ && prev2 !~ /deny_unknown_fields/ && $0 !~ /deny_unknown_fields/)
        pending_derive = NR
    }
    /deny_unknown_fields/ { if (pending_derive && NR - pending_derive <= 3) pending_derive = 0 }
    {
      if (pending_derive && NR - pending_derive > 3) {
        printf "rust-serde-missing-deny-unknown\t%d\tderive(Deserialize) without #[serde(deny_unknown_fields)] — candidate; required if this type parses external input\n", pending_derive
        pending_derive = 0
      }
      prev2 = prev1; prev1 = $0
    }
    END {
      if (pending_derive)
        printf "rust-serde-missing-deny-unknown\t%d\tderive(Deserialize) without #[serde(deny_unknown_fields)] — candidate; required if this type parses external input\n", pending_derive
    }
  ' "$1"
}

for f in "${FILES[@]}"; do
  rel="${f#"$ROOT"/}"
  base="$(basename "$f")"

  # unwrap/expect exemptions: main.rs, build.rs, anything under tests/, benches/, examples/, fuzz/
  exempt=0
  case "/$rel" in
    */tests/*|*/benches/*|*/examples/*|*/fuzz/*) exempt=1 ;;
  esac
  case "$base" in main.rs|build.rs) exempt=1 ;; esac

  while IFS=$'\t' read -r rule line msg; do
    [ -n "$rule" ] || continue
    add_finding warn "$rule" rust "$rel" "$line" "$msg"
  done < <(scan_file "$f" "$exempt")

  # House rule 2 candidate: std::sync lock types in a file that awaits.
  if grep -q '\.await' "$f" 2>/dev/null; then
    while IFS=: read -r line _; do
      [ -n "$line" ] || continue
      add_finding warn rust-sync-lock-in-async-candidate rust "$rel" "$line" \
        "std::sync Mutex/RwLock in a file containing .await — candidate for lock-held-across-await; confirm guard scope"
    done < <(grep -n 'std::sync::\(Mutex\|RwLock\)' "$f" 2>/dev/null || true)
  fi
done

render_findings "validate-safety.sh" "$ROOT"; exit $?
