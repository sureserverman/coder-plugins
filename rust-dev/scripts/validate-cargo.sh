#!/usr/bin/env bash
# validate-cargo.sh <rust-project-root> [--json]
#
# Deterministic checks for the cargo domain: Cargo.toml / rust-toolchain.toml /
# Cargo.lock invariants of the *target Rust project* (not this plugin's own
# structure — that is plugin-dev's job). Emits the shared JSON contract.
#
# Rule ids (stable, kebab-case — rust-dev's agents key off these):
#   cargo-no-manifest             info   no Cargo.toml under root; nothing to validate
#   cargo-manifest-parse-error    error  Cargo.toml fails TOML parse
#   cargo-missing-edition         warn   [package] has no edition (silently defaults to 2015)
#   cargo-invalid-edition         error  edition not one of 2015|2018|2021|2024
#   cargo-edition-2015            info   crate still on edition 2015 — migration nudge
#   cargo-missing-rust-version    warn   no rust-version (MSRV unspecified)
#   cargo-edition-msrv-mismatch   error  edition requires newer MSRV than rust-version
#   cargo-wildcard-dependency     warn   dependency version "*" (supply-chain risk)
#   cargo-workspace-member-missing error declared member path has no Cargo.toml
#   cargo-workspace-glob-empty    warn   member glob matches nothing
#   cargo-lockfile-missing        warn   binary crate without a Cargo.lock
#   cargo-toolchain-invalid-channel warn rust-toolchain.toml channel not a known form
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

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required for validate-cargo.sh (TOML parsing)" >&2
  exit 3
fi

# The python emits one finding per line as TSV: severity \t rule \t path \t line \t message.
# All decision logic lives here; bash only maps lines onto add_finding.
while IFS=$'\t' read -r sev rule path line msg; do
  [ -n "$sev" ] || continue
  add_finding "$sev" "$rule" cargo "$path" "$line" "$msg"
done < <(ROOT="$ROOT" python3 - <<'PY'
import os, re, sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # python < 3.11
    print("info\tcargo-toml-parser-unavailable\t.\t0\tpython3 lacks tomllib (need 3.11+); cargo checks skipped")
    sys.exit(0)

root = Path(os.environ["ROOT"])

def emit(sev, rule, path, msg, line=0):
    msg = msg.replace("\t", " ").replace("\n", " ")
    print(f"{sev}\t{rule}\t{path}\t{line}\t{msg}")

EDITIONS = {"2015", "2018", "2021", "2024"}
EDITION_MIN_MSRV = {"2018": (1, 31), "2021": (1, 56), "2024": (1, 85)}

def parse_ver(s):
    m = re.match(r"^(\d+)\.(\d+)", str(s))
    return (int(m.group(1)), int(m.group(2))) if m else None

manifests = []
for p in sorted(root.rglob("Cargo.toml")):
    parts = p.relative_to(root).parts
    if "target" in parts or ".git" in parts:
        continue
    manifests.append(p)

if not manifests:
    emit("info", "cargo-no-manifest", ".", "no Cargo.toml found under root; nothing to validate")
    sys.exit(0)

parsed = {}
for p in manifests:
    rel = str(p.relative_to(root))
    try:
        parsed[p] = tomllib.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        emit("error", "cargo-manifest-parse-error", rel, f"Cargo.toml fails TOML parse: {e}")

# workspace.package table for inheritance resolution (first manifest defining one)
ws_pkg = {}
for p, data in parsed.items():
    wp = (data.get("workspace") or {}).get("package") or {}
    if wp:
        ws_pkg = wp
        break

def resolved(pkg, key):
    """Resolve a possibly workspace-inherited package field."""
    v = pkg.get(key)
    if isinstance(v, dict):  # {workspace = true}
        return ws_pkg.get(key)
    return v

for p, data in parsed.items():
    rel = str(p.relative_to(root))
    pkg = data.get("package") or {}
    ws = data.get("workspace") or {}

    if pkg:
        edition = resolved(pkg, "edition")
        if edition is None:
            emit("warn", "cargo-missing-edition", rel,
                 "[package] has no edition — cargo silently defaults to 2015")
        else:
            edition = str(edition)
            if edition not in EDITIONS:
                emit("error", "cargo-invalid-edition", rel,
                     f"edition '{edition}' is not one of 2015|2018|2021|2024")
            elif edition == "2015":
                emit("info", "cargo-edition-2015", rel,
                     "crate is on edition 2015 — consider cargo fix --edition")

        msrv = resolved(pkg, "rust-version")
        if msrv is None:
            emit("warn", "cargo-missing-rust-version", rel,
                 "no rust-version — MSRV unspecified; downstream breakage is silent")
        elif edition in EDITION_MIN_MSRV:
            need = EDITION_MIN_MSRV[edition]
            got = parse_ver(msrv)
            if got and got < need:
                emit("error", "cargo-edition-msrv-mismatch", rel,
                     f"edition {edition} requires rust-version >= {need[0]}.{need[1]}, found {msrv}")

        for table in ("dependencies", "dev-dependencies", "build-dependencies"):
            for name, spec in (data.get(table) or {}).items():
                ver = spec if isinstance(spec, str) else (spec.get("version") if isinstance(spec, dict) else None)
                if ver == "*":
                    emit("warn", "cargo-wildcard-dependency", rel,
                         f"[{table}] {name} = \"*\" — pin a version range (supply-chain risk)")

    for member in ws.get("members", []):
        base = p.parent
        if any(ch in member for ch in "*?["):
            matches = [m for m in base.glob(member) if (m / "Cargo.toml").is_file()]
            if not matches:
                emit("warn", "cargo-workspace-glob-empty", rel,
                     f"workspace member glob '{member}' matches no directory with a Cargo.toml")
        elif not (base / member / "Cargo.toml").is_file():
            emit("error", "cargo-workspace-member-missing", rel,
                 f"workspace member '{member}' has no Cargo.toml on disk")

# Cargo.lock: a binary crate (src/main.rs, src/bin/, or [[bin]]) should commit its lockfile.
top = manifests[0]
for p, data in parsed.items():
    d = p.parent
    is_bin = (d / "src" / "main.rs").is_file() or (d / "src" / "bin").is_dir() or bool(data.get("bin"))
    if is_bin and not (d / "Cargo.lock").is_file() and not (top.parent / "Cargo.lock").is_file():
        rel = str(p.relative_to(root))
        emit("warn", "cargo-lockfile-missing", rel,
             "binary crate without a Cargo.lock — commit the lockfile for reproducible builds")

# rust-toolchain.toml channel sanity
for tc in [root / "rust-toolchain.toml", root / "rust-toolchain"]:
    if not tc.is_file():
        continue
    rel = str(tc.relative_to(root))
    if tc.suffix == ".toml":
        try:
            channel = (tomllib.loads(tc.read_text(encoding="utf-8")).get("toolchain") or {}).get("channel")
        except Exception as e:
            emit("error", "cargo-manifest-parse-error", rel, f"rust-toolchain.toml fails TOML parse: {e}")
            continue
    else:
        channel = tc.read_text(encoding="utf-8").strip()
    if channel and not re.match(r"^(stable|beta|nightly)(-\d{4}-\d{2}-\d{2})?$|^\d+\.\d+(\.\d+)?$", str(channel)):
        emit("warn", "cargo-toolchain-invalid-channel", rel,
             f"channel '{channel}' is not stable|beta|nightly[-date]|X.Y[.Z]")
    break
PY
)

render_findings "validate-cargo.sh" "$ROOT"; exit $?
