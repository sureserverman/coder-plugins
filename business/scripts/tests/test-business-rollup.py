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
            # revenue_usd is null (blank/failed parse) → must NOT count toward (N);
            # actuals stays 2 (github.stars + manual.installs), proving BL-004.
            "metrics": {"date": "2026-07-11", "values": {"github.stars": 5,
                        "manual.installs": 500, "manual.revenue_usd": None,
                        "note": "x"}},
            "gtm": {"done": 1, "total": 4, "pct": 25},
            # alpha carries both new artifacts → Plan/Research columns populated
            "plan": {"exists": True, "date": "2026-07-06", "age_days": 5, "status": "active"},
            "research": {"exists": True, "date": "2026-07-06", "age_days": 5,
                         "depth": "full", "confidence": "high"},
            "errors": [],
        },
        {   # launched: gtm but no metrics
            "name": "bravo", "area": "ai-tools", "assessed": True,
            "verdict": "free-for-reputation", "monetization": {"model": "oss-services"},
            "last_reviewed_age_days": 3, "metrics": None,
            "gtm": {"done": 0, "total": 5, "pct": 0},
            # research exists but its date didn't parse (age_days None) → "yes";
            # no plan → "—". Proves the two columns are independent.
            "research": {"exists": True, "date": None, "age_days": None,
                         "depth": "full", "confidence": "low"},
            "errors": [],
        },
        {   # assessed only, park; plan.md exists but its status didn't parse →
            # Plan column "yes" (malformation surfaced in Errors separately), no
            # research → Research "—"
            "name": "charlie", "area": "ai-tools", "assessed": True,
            "verdict": "park", "monetization": {"model": None},
            "last_reviewed_age_days": 40, "metrics": None, "gtm": None,
            "plan": {"exists": True, "date": None, "age_days": None, "status": None},
            "errors": ["plan.md: status 'published' not one of ['active', 'draft']"],
        },
        {   # assessed but errored (malformed BUSINESS.md)
            "name": "delta", "area": "ai-tools", "assessed": True,
            "verdict": None, "monetization": None,
            "last_reviewed_age_days": None, "metrics": None, "gtm": None,
            "errors": ["BUSINESS.md: verdict 'someday' not one of [...]"],
        },
        {   # not assessed
            "name": "echo", "area": "ai-tools", "assessed": False, "errors": []},
        {   # same name, different area (both assessed) — must disambiguate
            "name": "proxy", "area": "servers", "assessed": True,
            "verdict": "monetize", "monetization": {"model": "paid"},
            "last_reviewed_age_days": 1, "metrics": None, "gtm": None, "errors": []},
        {   "name": "proxy", "area": "containers", "assessed": True,
            "verdict": "park", "monetization": {"model": None},
            "last_reviewed_age_days": 1, "metrics": None, "gtm": None, "errors": []},
        {   # markdown-hostile free-text — must be escaped, not break the table
            "name": "weird|pipe", "area": "ai-tools", "assessed": True,
            "verdict": "monetize", "monetization": {"model": "paid|x"},
            "last_reviewed_age_days": 1, "metrics": None, "gtm": None, "errors": []},
        {   # unassessed AND errored — errors must still surface (degrade-loudly)
            "name": "ghost", "area": "ai-tools", "assessed": False,
            "errors": ["scan glitch: partial write"]},
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
    # assessed = alpha, bravo, charlie, delta, proxy(servers), proxy(containers), weird|pipe = 7
    check("## Assessed (7)" in md, "assessed count 7")
    check("| Project | Verdict | Model | Stage | Reviewed | Actuals | Plan | Research |" in md,
          "assessed table header carries the two new columns")
    # stage derivation, now area-qualified wikilinks
    check("| ai-tools/[[alpha]] | monetize | paid | tracked | 0d | 2026-07-11 (2) | active | 5d |" in md,
          "alpha row: tracked + plan active + research 5d, area-qualified")
    check("| ai-tools/[[bravo]] | free-for-reputation | oss-services | launched | 3d | — | — | yes |" in md,
          "bravo row: launched, no plan (—), research exists w/o date (yes)")
    check("| ai-tools/[[charlie]] | park | — | assessed | 40d | — | yes | — |" in md,
          "charlie row: plan exists w/o status (yes), no research (—)")
    # same-name-different-area disambiguation
    check("servers/[[proxy]]" in md and "containers/[[proxy]]" in md,
          "same-name projects disambiguated by area")
    # markdown injection escaped — the whole row is one intact line with escaped pipes
    check("| ai-tools/[[weird\\|pipe]] | monetize | paid\\|x | modeled | 1d | — | — | — |" in md,
          "pipe in name/model escaped, row stays a single 8-cell line")
    # triage gap = echo, ghost, with leading bullet
    check("## Not yet assessed (2) — triage gap" in md, "unassessed count 2")
    check("- ai-tools/[[echo]]" in md and "ai-tools/[[ghost]]" in md, "triage list bulleted + area-qualified")
    # degrade-loudly sections
    check("## Couldn't assess (1)" in md and "foxtrot: scan error: boom" in md,
          "couldnt_assess surfaced")
    check("## Errors (3)" in md, "all three errored projects counted (delta, charlie, ghost)")
    check("ai-tools/[[delta]]: BUSINESS.md: verdict" in md, "assessed+errored surfaced")
    check("ai-tools/[[ghost]] (unassessed): scan glitch" in md,
          "unassessed+errored surfaced (degrade-loudly gap closed)")


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
