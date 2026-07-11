#!/usr/bin/env python3
"""Fixture suite for business-rollup.py — run directly (CI convention):
    python3 business/scripts/tests/test-business-rollup.py

Feeds hand-crafted business-scan JSON into business-rollup.py via subprocess and
asserts the rendered global-business.md: assessed table (verdict/model/stage/
reviewed/actuals), the triage-gap list, and the degrade-loudly Couldn't-assess /
Errors sections.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "business-rollup.py"

FAILURES = []


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


DOC = {
    "generated": "2026-07-11",
    "vault_dir": "/x",
    "supported_schema": 1,
    "projects": [
        {   # tracked: metrics present → highest stage
            "name": "alpha", "area": "ai-tools", "assessed": True,
            "verdict": "monetize", "monetization": {"model": "paid"},
            "targets": [{"metric": "installs", "target": 1000, "by": "2026-12-31"}],
            "last_reviewed_age_days": 0,
            "metrics": {"date": "2026-07-11", "values": {"github.stars": 5,
                        "manual.installs": 500, "note": "x"}},
            "gtm": {"done": 1, "total": 4, "pct": 25}, "errors": [],
        },
        {   # launched: gtm but no metrics
            "name": "bravo", "area": "ai-tools", "assessed": True,
            "verdict": "free-for-reputation", "monetization": {"model": "oss-services"},
            "last_reviewed_age_days": 3, "metrics": None,
            "gtm": {"done": 0, "total": 5, "pct": 0}, "errors": [],
        },
        {   # assessed only, park
            "name": "charlie", "area": "ai-tools", "assessed": True,
            "verdict": "park", "monetization": {"model": None},
            "last_reviewed_age_days": 40, "metrics": None, "gtm": None, "errors": [],
        },
        {   # assessed but errored (malformed BUSINESS.md)
            "name": "delta", "area": "ai-tools", "assessed": True,
            "verdict": None, "monetization": None,
            "last_reviewed_age_days": None, "metrics": None, "gtm": None,
            "errors": ["BUSINESS.md: verdict 'someday' not one of [...]"],
        },
        {   # not assessed
            "name": "echo", "area": "ai-tools", "assessed": False, "errors": []},
    ],
    "couldnt_assess": [{"name": "foxtrot", "area": "x", "reason": "scan error: boom"}],
}


def run(doc):
    r = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(doc),
                       capture_output=True, text=True)
    return r


def test_render():
    r = run(DOC)
    check(r.returncode == 0, f"exit 0 (stderr {r.stderr.strip()[:120]})")
    md = r.stdout
    check("# Global Business Roll-up" in md, "has title")
    check("Generated: 2026-07-11" in md, "has generated date")
    # assessed count = 4 (alpha, bravo, charlie, delta)
    check("## Assessed (4)" in md, f"assessed count 4")
    # stage derivation
    check("| [[alpha]] | monetize | paid | tracked | 0d | 2026-07-11 (2) |" in md,
          "alpha row: tracked, 2 non-note metrics")
    check("| [[bravo]] | free-for-reputation | oss-services | launched | 3d | — |" in md,
          "bravo row: launched, no actuals")
    check("| [[charlie]] | park | — | assessed | 40d | — |" in md,
          "charlie row: park, model dash, assessed stage")
    # triage gap
    check("## Not yet assessed (1) — triage gap" in md, "unassessed count 1")
    check("[[echo]]" in md, "echo listed as unassessed")
    # degrade-loudly sections
    check("## Couldn't assess (1)" in md and "foxtrot: scan error: boom" in md,
          "couldnt_assess surfaced")
    check("## Errors (1)" in md and "[[delta]]: BUSINESS.md: verdict" in md,
          "errored project surfaced")


def test_empty():
    r = run({"generated": "2026-07-11", "projects": [], "couldnt_assess": []})
    md = r.stdout
    check(r.returncode == 0, "empty: exit 0")
    check("## Assessed (0)" in md and "_None assessed yet._" in md, "empty: none assessed")
    check("_All registry projects have a verdict._" in md, "empty: no triage gap line")
    check("Couldn't assess" not in md and "## Errors" not in md,
          "empty: degrade sections omitted when empty")


def main():
    test_render()
    test_empty()
    if FAILURES:
        print(f"\nFAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("\nOK — all business-rollup fixture checks passed")


if __name__ == "__main__":
    main()
