#!/usr/bin/env python3
"""Fixture tests for the portfolio-unify deterministic plan parser.

Locks the master-plan format invariants documented in
references/plan-parser.md § "Master plans" and
planning-projects/references/master-plan-format.md § "Parser-safety rules":

  (a) a master plan authored per the canonical format yields ZERO candidates
  (b) an in-progress sub-plan yields exactly its own unchecked-task candidates
  (c) a completed sub-plan yields zero candidates
  (d) a legacy single plan's candidates are unchanged (regression guard)
  (e) master **Gate:** bullets never surface as candidates

No pytest dependency — plain assertions, non-zero exit on any failure. Wired
into CI via `.github/workflows/validate-plan-parser.yml`.

Run locally:  python3 planning/skills/portfolio/tests/test-portfolio-unify.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "portfolio-unify.py"
FIXTURES = HERE / "fixtures" / "plan-parser"

spec = importlib.util.spec_from_file_location("portfolio_unify", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
parse_plan = mod.parse_plan

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok  {name}")
    else:
        failures.append(name)
        print(f"FAIL  {name}  {detail}")


def candidates(fname):
    text = (FIXTURES / fname).read_text()
    return parse_plan(text, f"plans/{fname}", set())


# (a) + (e) — master plan: zero candidates, gate bullets excluded
master = candidates("2026-07-04-bigproj-master-plan.md")
check("master yields zero candidates", master == [], f"got: {master}")
check(
    "master gate bullets never surface",
    not any("MASTER-GATE-MARKER" in c["title"] for c in master),
    f"got: {master}",
)

# (b) — in-progress sub-plan: exactly its unchecked task bullets, nothing else
sub1 = candidates("2026-07-04-bigproj-sub-01-api-plan.md")
sub1_titles = {c["title"] for c in sub1}
check(
    "in-progress sub-plan yields exactly its unchecked-task candidates",
    sub1_titles
    == {
        "SUB1-CANDIDATE-A: add retry logic to the upload handler",
        "SUB1-CANDIDATE-B: rate-limit the v2 endpoint",
    },
    f"got: {sorted(sub1_titles)}",
)
check(
    "sub-plan preflight/gate bullets excluded",
    not any("PREFLIGHT-MARKER" in t or "GATE-MARKER" in t for t in sub1_titles),
    f"got: {sorted(sub1_titles)}",
)

# (c) — completed sub-plan: zero candidates
sub2 = candidates("2026-07-04-bigproj-sub-02-client-plan.md")
check("completed sub-plan yields zero candidates", sub2 == [], f"got: {sub2}")

# (d) — legacy single plan: regression guard on both heuristic signals
legacy = candidates("2026-05-01-legacy-single-plan.md")
legacy_titles = {c["title"] for c in legacy}
legacy_signals = {c["signal"] for c in legacy}
check(
    "legacy plan candidates unchanged",
    legacy_titles
    == {
        "LEGACY-CANDIDATE-A: document the widget",
        "LEGACY-DEFERRED-A: widget telemetry",
        "LEGACY-DEFERRED-B: widget dark mode",
    },
    f"got: {sorted(legacy_titles)}",
)
check(
    "legacy plan uses both heuristic signals",
    legacy_signals == {"unchecked-open", "deferred-section"},
    f"got: {legacy_signals}",
)
check(
    "legacy preflight/gate bullets excluded",
    not any("PREFLIGHT-MARKER" in t or "GATE-MARKER" in t for t in legacy_titles),
    f"got: {sorted(legacy_titles)}",
)

if failures:
    print(f"\n{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("\nOK — all plan-parser fixture checks passed "
      "(master, sub-plans, legacy regression)")
