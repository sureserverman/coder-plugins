#!/usr/bin/env python3
"""Fixture suite for business-scan.py — run directly (CI convention):
    python3 business/scripts/tests/test-business-scan.py

Builds a throwaway HOME with a portfolio-config + registry pointing at the
fixture vault tree, runs the scanner as a subprocess, and asserts the JSON
contract every skill and the planning-plugin integration depends on: envelope
keys, per-project business fields, the nine fixture cases (happy / noassess /
malformed / newschema / partial / gtmmixed / edgey / badenum / boolschema), and
the read-only guarantee.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "business-scan.py"
FIXTURES = HERE / "fixtures"

FAILURES = []


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


CASES = ["happy", "noassess", "malformed", "newschema", "partial", "gtmmixed",
         "edgey", "badenum", "boolschema", "badtarget"]


def tree_hash(root):
    """Stable hash of every file's path + bytes under root (read-only proof)."""
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def run_scanner(tmp):
    home = tmp / "home"
    vault = tmp / "vault"
    (home / ".claude").mkdir(parents=True)
    shutil.copytree(FIXTURES / "vault", vault)
    (home / ".claude" / "portfolio-config.yaml").write_text(
        f"version: 1\nvault_dir: {vault}\n")
    reg = "projects:\n"
    for name in CASES:
        reg += (f"  - name: {name}\n"
                f"    area: ai-tools\n"
                f"    path: {tmp}/dev/ai-tools/{name}\n"
                f"    enabled: true\n")
    (home / ".claude" / "projects-registry.yaml").write_text(reg)

    before = tree_hash(vault)
    env = dict(os.environ, HOME=str(home))
    r = subprocess.run([sys.executable, str(SCRIPT)],
                       capture_output=True, text=True, env=env)
    after = tree_hash(vault)
    check(r.returncode == 0, f"scanner exits 0 (stderr: {r.stderr.strip()[:200]})")
    check(before == after, "read-only: fixture vault unchanged after scan")
    return json.loads(r.stdout), r


def by_name(doc):
    return {p["name"]: p for p in doc["projects"]}


def test_contract(tmp):
    doc, r = run_scanner(tmp)

    # envelope
    for k in ("generated", "vault_dir", "supported_schema", "projects", "couldnt_assess"):
        check(k in doc, f"envelope has '{k}'")
    check(doc["supported_schema"] == 1, "supported_schema == 1")
    check(len(doc["projects"]) == len(CASES), f"all {len(CASES)} projects present")
    check(doc["couldnt_assess"] == [], "couldnt_assess empty for well-formed registry")

    P = by_name(doc)

    # happy — fully populated
    h = P.get("happy", {})
    check(h.get("assessed") is True, "happy: assessed true")
    check(h.get("schema") == 1, "happy: schema 1")
    check(h.get("verdict") == "monetize", "happy: verdict monetize")
    check(h.get("evidence") == "researched", "happy: evidence researched")
    check(h.get("monetization", {}).get("model") == "paid", "happy: model paid")
    check("f-droid" in (h.get("monetization", {}).get("channels") or []),
          "happy: channels include f-droid")
    check(len(h.get("targets") or []) == 2, "happy: 2 targets")
    check(isinstance(h.get("last_reviewed_age_days"), int)
          and h["last_reviewed_age_days"] >= 0, "happy: last_reviewed_age_days int >= 0")
    check((h.get("metrics") or {}).get("date") == "2026-07-01",
          "happy: latest metrics block 2026-07-01")
    check((h.get("metrics") or {}).get("values", {}).get("github.stars") == 61,
          "happy: latest github.stars 61")
    check(h.get("gtm") == {"done": 2, "total": 5, "pct": 40},
          f"happy: gtm 2/5/40 (got {h.get('gtm')})")
    check(h.get("errors") == [], "happy: no errors")

    # noassess — triage gap, not an error
    n = P.get("noassess", {})
    check(n.get("assessed") is False, "noassess: assessed false")
    check(n.get("errors") == [], "noassess: no errors")
    check("verdict" not in n, "noassess: no business fields emitted")

    # malformed — parse error captured, project still assessed, verdict null
    m = P.get("malformed", {})
    check(m.get("assessed") is True, "malformed: assessed true")
    check(m.get("verdict") is None, "malformed: verdict null")
    check(any("BUSINESS.md" in e for e in m.get("errors", [])),
          f"malformed: BUSINESS.md error recorded (got {m.get('errors')})")

    # newschema — explicit upgrade error, not a misparse
    s = P.get("newschema", {})
    check(s.get("schema") == 2, "newschema: schema 2 surfaced")
    check(s.get("verdict") is None, "newschema: verdict null (not misparsed)")
    check(any("upgrade" in e.lower() for e in s.get("errors", [])),
          f"newschema: upgrade error (got {s.get('errors')})")

    # partial — assessed, no metrics/gtm, no error
    pa = P.get("partial", {})
    check(pa.get("verdict") == "park", "partial: verdict park")
    check(pa.get("metrics") is None, "partial: metrics null")
    check(pa.get("gtm") is None, "partial: gtm null")
    check(pa.get("errors") == [], "partial: no errors")

    # gtmmixed — checkbox counting ignores headers and plain bullets
    g = P.get("gtmmixed", {})
    check(g.get("verdict") == "free-for-reputation", "gtmmixed: verdict free-for-reputation")
    check(g.get("gtm") == {"done": 3, "total": 4, "pct": 75},
          f"gtmmixed: gtm 3/4/75, note bullet excluded (got {g.get('gtm')})")

    # edgey — parser-hardening regressions (all four review fixes)
    e = P.get("edgey", {})
    check(e.get("assessed") is True, "edgey: assessed true")
    # Critical 2: inline '---' in audience must NOT truncate frontmatter
    check(e.get("verdict") == "monetize", "edgey: verdict survives inline '---' in audience")
    check("basically anyone" in (e.get("audience") or ""),
          f"edgey: audience scalar intact (got {e.get('audience')!r})")
    check(e.get("evidence") == "local-only",
          "edgey: field after the inline '---' still parsed (no silent truncation)")
    check(e.get("last_reviewed") == "2026-07-01",
          "edgey: last_reviewed after inline '---' still parsed")
    # Critical 1: date-shaped pricing serializes as a string, no crash
    check((e.get("monetization") or {}).get("pricing") == "2026-07-01",
          f"edgey: date-shaped pricing normalized to string (got {(e.get('monetization') or {}).get('pricing')!r})")
    check(e.get("errors") == [], f"edgey: no errors (got {e.get('errors')})")
    # Important: stray non-date '## notes' block must not become 'latest'
    check((e.get("metrics") or {}).get("date") == "2026-07-01",
          f"edgey: latest metrics is the dated block, not stray '## notes' (got {(e.get('metrics') or {}).get('date')})")
    check((e.get("metrics") or {}).get("values", {}).get("github.stars") == 5,
          "edgey: latest github.stars 5, not 999 from the stray block")
    # Important: inf/nan rejected → JSON stays RFC-8259 valid
    vals = (e.get("metrics") or {}).get("values", {})
    check(vals.get("volatility") is None, "edgey: 'nan' metric rejected to null")
    check(vals.get("growth") is None, "edgey: 'inf' metric rejected to null")
    # Important: a non-finite float ANYWHERE (here a target's `.inf`) is nulled
    tgts = e.get("targets") or []
    reach = next((t for t in tgts if t.get("metric") == "reach"), {})
    check(reach.get("target") is None,
          f"edgey: non-finite target '.inf' normalized to null (got {reach.get('target')!r})")
    # And prove the raw output carries no bare Infinity/NaN tokens anywhere
    check("Infinity" not in r.stdout and "NaN" not in r.stdout,
          "edgey: no bare Infinity/NaN tokens in the JSON stream")

    # badenum — every documented-required field validated symmetrically
    b = P.get("badenum", {})
    check(b.get("assessed") is True, "badenum: assessed true")
    check(b.get("verdict") is None, "badenum: invalid verdict nulled")
    check(b.get("evidence") is None, "badenum: invalid evidence nulled")
    errs = " | ".join(b.get("errors", []))
    check("verdict" in errs, "badenum: verdict enum error recorded")
    check("evidence" in errs, "badenum: evidence enum error recorded")
    check("last_reviewed" in errs, "badenum: missing last_reviewed error recorded")
    check("does not match registry" in errs,
          f"badenum: project-mismatch error recorded (got {b.get('errors')})")
    check("channels" in errs, "badenum: channels-not-a-list error recorded")

    # boolschema — schema: true (bool subclasses int) rejected, not treated as 1
    bs = P.get("boolschema", {})
    check(bs.get("assessed") is True, "boolschema: assessed true")
    check(bs.get("verdict") is None, "boolschema: not parsed as schema 1")
    check(any("integer" in e for e in bs.get("errors", [])),
          f"boolschema: schema-must-be-integer error (got {bs.get('errors')})")

    # badtarget — targets[] item shape validated (BL-002): scalar fields fine,
    # only the two malformed targets error, assessment not aborted
    bt = P.get("badtarget", {})
    check(bt.get("assessed") is True, "badtarget: assessed true")
    check(bt.get("verdict") == "monetize", "badtarget: scalar fields still parse")
    bterrs = " | ".join(bt.get("errors", []))
    check("targets[0].by" in bterrs,
          f"badtarget: target missing `by` flagged (got {bt.get('errors')})")
    check("targets[1].target" in bterrs,
          f"badtarget: non-numeric target flagged (got {bt.get('errors')})")


def test_gtm_degrades_without_portfolio_unify():
    """Important #1: if portfolio-unify isn't importable (business is a
    separately-versioned plugin), the scanner must degrade per-project — gtm
    progress becomes an error — never crash the whole sweep."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("business_scan_mod", SCRIPT)
    bs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bs)
    bs.pu = None
    try:
        bs.parse_gtm("- [x] done\n- [ ] open\n")
        check(False, "parse_gtm raises when portfolio-unify missing")
    except RuntimeError:
        check(True, "parse_gtm degrades (raises, caught per-project) when portfolio-unify missing")


def main():
    with tempfile.TemporaryDirectory() as td:
        test_contract(Path(td))
    test_gtm_degrades_without_portfolio_unify()
    if FAILURES:
        print(f"\nFAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("\nOK — all business-scan fixture checks passed")


if __name__ == "__main__":
    main()
