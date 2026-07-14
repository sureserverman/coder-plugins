#!/usr/bin/env python3
"""Fixture tests for the portfolio-unify deterministic plan parser.

Locks the master-plan format invariants documented in
references/plan-parser.md § "Master plans" and
planning-projects/references/master-plan-format.md § "Parser-safety rules",
plus the Status-authoritative path (§ "Authoritative signal: per-task Status"):

  (a) a master plan authored per the canonical format yields ZERO candidates
  (b) an in-progress sub-plan (a modern Status-field plan) yields exactly one
      candidate per `Status: [ ]` task (signal status-unexecuted, title = the
      task description) — its raw body bullets are NOT candidates
  (c) a completed sub-plan yields zero candidates
  (d) a legacy single plan's heuristic candidates are unchanged (regression)
  (e) master **Gate:** bullets never surface as candidates
  (f) a stray `- [ ]` bullet inside a DONE (`Status: [x]`) task is suppressed
  (g) Deferred bullets still surface from Status-authoritative plans
  (h) a Light plan (single-stage Status-field plan, light-plan-format.md) is
      parser-safe by construction: in progress it yields one candidate per
      undone task + its Deferred bullets, gate bullets and a stray bullet in a
      done task excluded; completed it yields zero

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

# (b) + (f) + (g) — in-progress sub-plan is a modern Status-field plan: the
# authoritative path fires. One candidate per `Status: [ ]` task; raw body
# bullets (in done AND undone tasks), preflight, and gate bullets are all
# ignored; Deferred bullets still surface.
sub1 = candidates("2026-07-04-bigproj-sub-01-api-plan.md")
sub1_by_signal = {}
for c in sub1:
    sub1_by_signal.setdefault(c["signal"], []).append(c)
check(
    "status plan: one status-unexecuted candidate per undone task",
    [c["title"] for c in sub1_by_signal.get("status-unexecuted", [])]
    == ["Harden the endpoint"],
    f"got: {sub1}",
)
check(
    "status-unexecuted source locator is Stage N / Task N.N",
    sub1_by_signal["status-unexecuted"][0]["source"]
    == "plans/2026-07-04-bigproj-sub-01-api-plan.md — Stage 1 / Task 1.2",
    f"got: {sub1_by_signal['status-unexecuted'][0]['source']}",
)
sub1_titles = {c["title"] for c in sub1}
check(
    "stray bullet in DONE task suppressed; body bullets of undone task not "
    "emitted as separate candidates",
    not any(
        "STRAY-LEFTOVER" in t or "SUB1-CANDIDATE" in t for t in sub1_titles
    ),
    f"got: {sorted(sub1_titles)}",
)
check(
    "sub-plan preflight/gate bullets excluded",
    not any("PREFLIGHT-MARKER" in t or "GATE-MARKER" in t for t in sub1_titles),
    f"got: {sorted(sub1_titles)}",
)
check(
    "Deferred bullets still surface from a Status-authoritative plan",
    [c["title"] for c in sub1_by_signal.get("deferred-section", [])]
    == ["SUB1-DEFERRED-A: telemetry for the retry path"],
    f"got: {sub1}",
)
check(
    "status plan emits nothing beyond status-unexecuted + deferred-section",
    set(sub1_by_signal) == {"status-unexecuted", "deferred-section"},
    f"got signals: {set(sub1_by_signal)}",
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

# Edge cases on the authoritative path: bare `Task N.N` locator for a task
# with no enclosing Stage header, and one-candidate-per-task under a malformed
# double-Status task.
edges = candidates("2026-07-05-status-edge-cases-plan.md")
check(
    "no-stage task uses bare Task N.N locator",
    any(
        c["source"] == "plans/2026-07-05-status-edge-cases-plan.md — Task 0.1"
        for c in edges
    ),
    f"got: {edges}",
)
check(
    "double-Status malformed task emits exactly one candidate",
    sum("EDGE-DOUBLE" in c["title"] for c in edges) == 1,
    f"got: {edges}",
)
check(
    "edge fixture emits nothing else",
    len(edges) == 2,
    f"got: {edges}",
)

# Detection requires the checkbox: a checkbox-less `- **Status:** Draft` field
# must NOT capture the file for the authoritative path — its legacy unchecked
# bullets still surface via the heuristic.
BARE_STATUS_PLAN = """\
# Project Plan: Bare status field, no checkboxes
Date: 2026-07-05

- **Status:** Draft

## Stage 1: Work

### Task 1.1: Ship it
- [ ] BARE-CANDIDATE-A: still a heuristic candidate
"""
bare = parse_plan(BARE_STATUS_PLAN, "plans/bare-status.md", set())
check(
    "checkbox-less Status field degrades to the legacy heuristic",
    [c["title"] for c in bare]
    == ["BARE-CANDIDATE-A: still a heuristic candidate"]
    and bare[0]["signal"] == "unchecked-open",
    f"got: {bare}",
)

# (h) — Light plans (light-plan-format.md) take the authoritative path with no
# parser change: a single-stage Status-field plan. In progress → one
# status-unexecuted candidate per undone task + Deferred bullets; gate bullets
# and a stray bullet in a done task are excluded. Completed → zero candidates.
light = candidates("2026-07-14-light-inprogress-plan.md")
light_by_signal = {}
for c in light:
    light_by_signal.setdefault(c["signal"], []).append(c)
check(
    "light plan: one status-unexecuted candidate per undone task",
    [c["title"] for c in light_by_signal.get("status-unexecuted", [])]
    == ["Add the parser fixture", "Bump the version"],
    f"got: {light}",
)
check(
    "light plan status-unexecuted locators are Stage 1 / Task 1.N",
    [c["source"] for c in light_by_signal.get("status-unexecuted", [])]
    == [
        "plans/2026-07-14-light-inprogress-plan.md — Stage 1 / Task 1.2",
        "plans/2026-07-14-light-inprogress-plan.md — Stage 1 / Task 1.3",
    ],
    f"got: {[c['source'] for c in light_by_signal.get('status-unexecuted', [])]}",
)
light_titles = {c["title"] for c in light}
check(
    "light plan: stray bullet in DONE task and gate bullets excluded",
    not any(
        "LIGHT-STRAY" in t or "LIGHT-GATE-MARKER" in t for t in light_titles
    ),
    f"got: {sorted(light_titles)}",
)
check(
    "light plan: Deferred bullets still surface",
    [c["title"] for c in light_by_signal.get("deferred-section", [])]
    == ["LIGHT-DEFERRED-A: compass badge for light plans"],
    f"got: {light}",
)
check(
    "light plan emits nothing beyond status-unexecuted + deferred-section",
    set(light_by_signal) == {"status-unexecuted", "deferred-section"},
    f"got signals: {set(light_by_signal)}",
)
light_done = candidates("2026-07-14-light-completed-plan.md")
check(
    "completed light plan yields zero candidates",
    light_done == [],
    f"got: {light_done}",
)

# Architecture docs (architecting-projects skill) land in the same plans/ dir
# and are scanned like any file; safety is by construction — no unchecked
# bullets, no Status fields (plan-parser.md § "Architecture docs").
arch = candidates("sample-architecture.md")
check(
    "architecture doc yields zero candidates",
    arch == [],
    f"got: {arch}",
)

# Inverse guard: the invariant is falsifiable — one raw `- [ ]` smuggled into
# the doc MUST surface via the legacy heuristic (proves the check can fail).
ARCH_TEXT = (FIXTURES / "sample-architecture.md").read_text()
mutated = ARCH_TEXT + "\n- [ ] ARCH-MUTANT: smuggled deferred work\n"
mut = parse_plan(mutated, "plans/sample-architecture.md", set())
check(
    "mutated architecture doc (raw unchecked bullet) DOES emit a candidate",
    [c["title"] for c in mut] == ["ARCH-MUTANT: smuggled deferred work"],
    f"got: {mut}",
)

if failures:
    print(f"\n{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("\nOK — all plan-parser fixture checks passed "
      "(master, sub-plans, legacy regression, architecture docs)")
