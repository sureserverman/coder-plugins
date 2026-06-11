#!/usr/bin/env bash
# stack-report.sh <rust-project-root> [--json]
#
# Deterministic Stack Report for a Rust project — the mechanical 90% of
# rust-expert's Protocol 1 (stack detection). Reads, decides, reports; never
# edits. Deliberately NOT named validate-*.sh: it produces facts, not findings,
# so the validate.sh orchestrator does not include it in verdicts.
#
# JSON fields: edition, msrv, toolchain, workspace {kind, members}, runtimes,
# frameworks, test_layout, risk_surfaces (pattern counts), lockfile_committed,
# ci (workflow files + cargo invocations found).
set -eu

JSON=0; ARGS=()
for a in "$@"; do case "$a" in --json) JSON=1 ;; *) ARGS+=("$a") ;; esac; done
ROOT="${ARGS[0]:-.}"
ROOT="$(cd "$ROOT" 2>/dev/null && pwd || true)"
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "usage: $0 <rust-project-root> [--json]" >&2; exit 2; }

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required for stack-report.sh" >&2
  exit 3
fi

ROOT="$ROOT" JSON="$JSON" python3 - <<'PY'
import json, os, re, sys
from pathlib import Path

root = Path(os.environ["ROOT"])
as_json = os.environ["JSON"] == "1"

report = {
    "root": str(root), "edition": None, "msrv": None, "toolchain": None,
    "workspace": {"kind": "none", "members": []}, "runtimes": [], "frameworks": [],
    "test_layout": [], "risk_surfaces": {}, "lockfile_committed": False, "ci": [],
}

try:
    import tomllib
except ImportError:
    print("error: python3 lacks tomllib (need 3.11+)", file=sys.stderr)
    sys.exit(3)

manifests = [p for p in sorted(root.rglob("Cargo.toml"))
             if "target" not in p.relative_to(root).parts
             and ".git" not in p.relative_to(root).parts]
if not manifests:
    report["workspace"]["kind"] = "no-cargo-project"
else:
    top = manifests[0]
    try:
        data = tomllib.loads(top.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    ws = data.get("workspace") or {}
    pkg = data.get("package") or {}
    ws_pkg = ws.get("package") or {}

    def resolved(key):
        v = pkg.get(key)
        if isinstance(v, dict):
            return ws_pkg.get(key)
        return v if v is not None else ws_pkg.get(key)

    report["edition"] = str(resolved("edition")) if resolved("edition") else None
    report["msrv"] = str(resolved("rust-version")) if resolved("rust-version") else None

    if ws.get("members"):
        report["workspace"] = {"kind": "workspace", "members": ws["members"]}
    else:
        report["workspace"] = {"kind": "single-crate", "members": []}

    deps = set()
    for m in manifests:
        try:
            d = tomllib.loads(m.read_text(encoding="utf-8"))
        except Exception:
            continue
        for table in ("dependencies", "dev-dependencies", "build-dependencies"):
            deps.update((d.get(table) or {}).keys())
    report["runtimes"] = sorted(deps & {"tokio", "async-std", "smol"})
    report["frameworks"] = sorted(deps & {
        "axum", "actix-web", "rocket", "warp", "tonic", "tauri",
        "wasm-bindgen", "bevy", "serde", "clap", "diesel", "sqlx", "reqwest"})

tc = root / "rust-toolchain.toml"
if tc.is_file():
    try:
        report["toolchain"] = (tomllib.loads(tc.read_text(encoding="utf-8"))
                               .get("toolchain") or {}).get("channel")
    except Exception:
        report["toolchain"] = "unparseable"
elif (root / "rust-toolchain").is_file():
    report["toolchain"] = (root / "rust-toolchain").read_text(encoding="utf-8").strip()

for name in ("tests", "benches", "examples", "fuzz"):
    if any(root.glob(f"**/{name}")) and any(
            p for p in root.glob(f"**/{name}") if p.is_dir()
            and "target" not in p.relative_to(root).parts):
        report["test_layout"].append(name)

rs_files = [p for p in root.rglob("*.rs")
            if "target" not in p.relative_to(root).parts
            and ".git" not in p.relative_to(root).parts]
if any("#[cfg(test)]" in p.read_text(encoding="utf-8", errors="replace") for p in rs_files):
    report["test_layout"].insert(0, "inline-unit")

patterns = {"unsafe": r"\bunsafe\b", "extern_c": r'extern\s+"C"', "repr_c": r"#\[repr\(C\)\]",
            "pin": r"\bPin<", "maybe_uninit": r"MaybeUninit", "transmute": r"transmute"}
counts = {k: 0 for k in patterns}
for p in rs_files:
    text = p.read_text(encoding="utf-8", errors="replace")
    for k, rx in patterns.items():
        counts[k] += len(re.findall(rx, text))
report["risk_surfaces"] = counts

report["lockfile_committed"] = (root / "Cargo.lock").is_file()

for ci in sorted(list(root.glob(".github/workflows/*.yml"))
                 + list(root.glob(".github/workflows/*.yaml"))
                 + [root / ".gitlab-ci.yml"]):
    if not ci.is_file():
        continue
    cargo_lines = sorted({ln.strip() for ln in ci.read_text(encoding="utf-8", errors="replace").splitlines()
                          if re.search(r"\bcargo\s+(test|clippy|check|build|miri|fmt|audit|deny)", ln)})
    report["ci"].append({"file": str(ci.relative_to(root)), "cargo_invocations": cargo_lines})

if as_json:
    print(json.dumps(report, indent=2))
else:
    w = report["workspace"]
    print(f"Edition: {report['edition'] or 'unspecified (defaults 2015)'}")
    print(f"MSRV: {report['msrv'] or 'unspecified'}")
    print(f"Toolchain: {report['toolchain'] or 'unpinned'}")
    print(f"Workspace: {w['kind']}" + (f" ({len(w['members'])} members)" if w["members"] else ""))
    print(f"Runtime: {', '.join(report['runtimes']) or 'none detected'}")
    print(f"Frameworks: {', '.join(report['frameworks']) or 'none detected'}")
    print(f"Test layout: {', '.join(report['test_layout']) or 'none detected'}")
    print("Risk surfaces: " + ", ".join(f"{k}={v}" for k, v in report["risk_surfaces"].items() if v) or "none")
    print(f"Cargo.lock committed: {report['lockfile_committed']}")
    for ci in report["ci"]:
        print(f"CI: {ci['file']}: " + ("; ".join(ci["cargo_invocations"]) or "no cargo invocations found"))
PY
