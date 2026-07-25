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

import datetime
TODAY_ = datetime.date(2026, 7, 25)   # fixed 'today' so date assertions never drift


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

# (i) — the `[~]` partial state (BL-001). All three Status characters asserted
# together: `[x]` emits nothing, `[ ]` → status-unexecuted, `[~]` →
# status-partial. Partial is open work, but distinguishable from never-begun.
partial = candidates("2026-07-24-partial-status-plan.md")
partial_by_signal = {}
for c in partial:
    partial_by_signal.setdefault(c["signal"], []).append(c)
check(
    "partial: `[~]` task lands in the status-partial bucket",
    [c["title"] for c in partial_by_signal.get("status-partial", [])]
    == ["PARTIAL-INFLIGHT: started but unfinished"],
    f"got: {partial}",
)
check(
    "partial: `[ ]` task still lands in status-unexecuted, not status-partial",
    [c["title"] for c in partial_by_signal.get("status-unexecuted", [])]
    == ["PARTIAL-OPEN: never started"],
    f"got: {partial}",
)
check(
    "partial: `[x]` task still emits nothing, and gate bullets excluded",
    not any(
        "PARTIAL-DONE" in c["title"] or "PARTIAL-GATE-MARKER" in c["title"]
        for c in partial
    ),
    f"got: {partial}",
)
check(
    "partial: locator + signal set are exactly the two open tasks",
    set(partial_by_signal) == {"status-unexecuted", "status-partial"}
    and len(partial) == 2,
    f"got signals: {set(partial_by_signal)}, n={len(partial)}",
)

# status_state() is the only sanctioned classifier — `!= " "` reads `[~]` as
# done, which is worse than the bug being fixed. Lock the mapping directly.
check(
    "status_state maps the three contract characters",
    (mod.status_state(" "), mod.status_state("x"), mod.status_state("X"),
     mod.status_state("~")) == ("open", "done", "done", "partial"),
    f"got: {[mod.status_state(c) for c in ' xX~']}",
)

# Lockstep guard: the authoritative-path DETECTION class must match STATUS_RE's.
# An all-partial plan previously matched neither, fell to the legacy heuristic,
# and emitted its gate bullet instead of its task.
allpartial = candidates("2026-07-24-all-partial-plan.md")
check(
    "all-partial plan takes the authoritative path, not the legacy heuristic",
    [(c["title"], c["signal"]) for c in allpartial]
    == [("ALLPARTIAL-A: in flight", "status-partial")],
    f"got: {allpartial}",
)
check(
    "all-partial plan does not leak its gate bullet",
    not any("ALLPARTIAL-GATE-MARKER" in c["title"] for c in allpartial),
    f"got: {allpartial}",
)

# (j) — abandonment: the structured marker is authoritative; banner prose is
# advisory only and must never suppress.
aband_text = (FIXTURES / "2026-07-24-abandoned-plan.md").read_text()
banner_text = (FIXTURES / "2026-07-24-banner-only-plan.md").read_text()
live_text = (FIXTURES / "2026-07-24-partial-status-plan.md").read_text()
check(
    "**Abandoned:** marker flags the plan abandoned, with no advisory",
    mod.plan_terminal_state(aband_text)[:2] == (True, None),
    f"got: {mod.plan_terminal_state(aband_text)}",
)
check(
    "the marker's REASON is returned, not discarded — compass lists a "
    "suppressed plan with its reason",
    mod.plan_terminal_state(aband_text)[2]
    == "2026-07-20 — superseded by the widget rewrite",
    f"got: {mod.plan_terminal_state(aband_text)[2]!r}",
)
ab_flag, ab_note, ab_reason = mod.plan_terminal_state(banner_text)
check(
    "banner prose WITHOUT the marker is never flagged abandoned",
    ab_flag is False,
    f"got: {(ab_flag, ab_note)}",
)
check(
    "banner prose WITHOUT the marker yields a non-suppressing advisory",
    ab_note is not None and "not suppressed" in ab_note,
    f"got: {ab_note}",
)
check(
    "banner-only plan carries no abandonment reason",
    ab_reason is None,
    f"got: {ab_reason!r}",
)
check(
    "an ordinary live plan is neither abandoned nor advised",
    mod.plan_terminal_state(live_text) == (False, None, None),
    f"got: {mod.plan_terminal_state(live_text)}",
)

# --- signal 3: stale-plan candidates (--include-stale, BL-016) --------------
# Opt-in, keyed on the filename YYYY-MM-DD stamp (NOT git — the vault is not a
# repo; NOT mtime — a migration reset five plans to one date). plan-parser.md § 3.

# Date arithmetic, with `today` injected so these never drift with the calendar.
check("90-day boundary: 91 days is stale",
      mod.stale_age_days("2026-04-25-x-plan.md", TODAY_) > mod.STALE_DAYS,
      f"got {mod.stale_age_days('2026-04-25-x-plan.md', TODAY_)}")
check("90-day boundary: exactly 90 days is NOT stale",
      not (mod.stale_age_days("2026-04-26-x-plan.md", TODAY_) > mod.STALE_DAYS),
      "90 days must sit inside the window")
check("unstamped filename -> staleness UNKNOWN, never assumed",
      mod.stale_age_days("unstamped-legacy-plan.md") is None,
      "an unstamped name must not read as infinitely old")
check("plan_date's 0000-00-00 sentinel is NOT reused for staleness",
      mod.plan_date("unstamped-legacy-plan.md") == "0000-00-00"
      and mod.stale_age_days("unstamped-legacy-plan.md") is None,
      "reusing the sentinel would flag every unstamped legacy file stale")
check("invalid date in a filename -> unknown, not a crash",
      mod.stale_age_days("2026-13-45-x-plan.md") is None, "must catch ValueError")
check("future-dated stamp is not stale",
      mod.stale_age_days("2099-01-01-x-plan.md", TODAY_) < 0, "negative age")


def run_unify(names, include_stale, evidence, extra=None):
    """unify_project end-to-end over a throwaway vault home. git_stage_evidence
    is stubbed because signal 3 only ADDS items the git-stage suppression hid —
    without stage evidence there is nothing for it to surface, so a test that
    skipped the stub would pass no matter what the flag did."""
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as td:
        home = Path(td) / "h"
        (home / "plans").mkdir(parents=True)
        for n in names:
            shutil.copy(FIXTURES / n, home / "plans" / n)
        for fname, body in (extra or {}).items():
            (home / "plans" / fname).write_text(body)
        orig = mod.git_stage_evidence
        mod.git_stage_evidence = lambda _p: evidence
        try:
            return mod.unify_project(home, False, td, include_stale)
        finally:
            mod.git_stage_evidence = orig


STALE_FIXTURE = ["2020-01-01-stale-legacy-plan.md"]
DONE_STAGE = {("2026-01-01", 1)}          # a commit that marks Stage 1 executed

_, _, off = run_unify(STALE_FIXTURE, False, DONE_STAGE)
_, _, on = run_unify(STALE_FIXTURE, True, DONE_STAGE)
check("flag OFF: a git-suppressed old plan stays silent",
      off == 0, f"expected 0, got {off}")
check("flag ON: the old plan's suppressed items surface",
      on > off, f"expected >{off}, got {on}")

# The signal LABEL itself, read back out of unify_project's real output rather
# than reconstructed here — the earlier version built the label in the test, so
# it could not have caught a mislabel in the script. Documented in three places
# and asserted in none until close-out mutation testing found the gap.
import tempfile as _tf, shutil as _sh
_labels = []
with _tf.TemporaryDirectory() as _td:
    _h = Path(_td) / "h"
    (_h / "plans").mkdir(parents=True)
    _sh.copy(FIXTURES / STALE_FIXTURE[0], _h / "plans" / STALE_FIXTURE[0])
    _bl = _h / "backlog.md"
    _orig = mod.git_stage_evidence
    mod.git_stage_evidence = lambda _p: DONE_STAGE
    try:
        mod.unify_project(_h, True, _td, True)      # --write, so entries render
        _labels = [ln for ln in _bl.read_text().splitlines() if "Reason:" in ln]
    finally:
        mod.git_stage_evidence = _orig
check("stale candidates render the documented signal label into the backlog",
      _labels and all("stale-plan-unchecked" in ln for ln in _labels),
      f"got {_labels}")

# A plan dated today can never be stale — written at run time so it cannot age
# into staleness the way a committed fixture would.
import datetime as _dt
_today_name = f"{_dt.date.today().isoformat()}-fresh-plan.md"
_fresh = ("# Project Plan: Fresh\n\n## Stage 1: S\n\n### Task 1.1: T\n"
          "- [ ] a recent unresolved item\n")
_, _, fresh_off = run_unify([], False, DONE_STAGE, extra={_today_name: _fresh})
_, _, fresh_on = run_unify([], True, DONE_STAGE, extra={_today_name: _fresh})
check("a plan dated today contributes no STALE extras",
      fresh_on == fresh_off,
      f"off={fresh_off} on={fresh_on} — a same-day plan must never be stale "
      f"(its own normal candidates are expected and unaffected by the flag)")

# The 90-day boundary through unify_project, not just the helper. Both plans are
# written at run time and dated relative to today, so the pair straddles the
# threshold forever instead of ageing across it like a committed fixture would.
_body = ("# Project Plan: Boundary\n\n## Stage 1: S\n\n### Task 1.1: T\n"
         "- [ ] a suppressed unresolved item\n")
_at90 = (_dt.date.today() - _dt.timedelta(days=mod.STALE_DAYS)).isoformat()
_at91 = (_dt.date.today() - _dt.timedelta(days=mod.STALE_DAYS + 1)).isoformat()
# Stage evidence must post-date each plan for the suppression to apply, which is
# what leaves anything for signal 3 to surface.
_ev = {(_dt.date.today().isoformat(), 1)}
_, _, b90_off = run_unify([], False, _ev, extra={f"{_at90}-boundary-plan.md": _body})
_, _, b90_on = run_unify([], True, _ev, extra={f"{_at90}-boundary-plan.md": _body})
_, _, b91_off = run_unify([], False, _ev, extra={f"{_at91}-boundary-plan.md": _body})
_, _, b91_on = run_unify([], True, _ev, extra={f"{_at91}-boundary-plan.md": _body})
check(f"exactly {mod.STALE_DAYS} days old is NOT stale (no extras under the flag)",
      b90_on == b90_off, f"off={b90_off} on={b90_on} — the window must be exclusive")
check(f"{mod.STALE_DAYS + 1} days old IS stale (extras appear under the flag)",
      b91_on > b91_off, f"off={b91_off} on={b91_on} — one day past must surface")

# The unstamped fallback, through the real code path rather than the helper.
_, _, uns_off = run_unify(["unstamped-legacy-plan.md"], False, DONE_STAGE)
_, _, uns_on = run_unify(["unstamped-legacy-plan.md"], True, DONE_STAGE)
check("an unstamped plan contributes no stale candidates even with a done stage",
      uns_on == uns_off, f"off={uns_off} on={uns_on} — unknown age must not surface")

# Tier-1 raised a Source-key collision (the legacy locator encodes the Stage but
# not Task N.N). Verified UNREACHABLE here: `normal` and the stale re-parse differ
# only at whole-stage granularity, so a colliding pair is always wholly in both or
# wholly in neither. The dedup key is (source, title) anyway as defence in depth;
# this locks the property the reachability argument rests on.
_, _, all_suppressed = run_unify(STALE_FIXTURE, True, DONE_STAGE)
_, _, none_suppressed = run_unify(STALE_FIXTURE, True, set())
check("stale diff is whole-stage: every item surfaces when its stage is done",
      all_suppressed == none_suppressed,
      f"done-stage={all_suppressed} no-evidence={none_suppressed} — a partial "
      f"difference would make the Source-key collision reachable")

if failures:
    print(f"\n{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("\nOK — all plan-parser fixture checks passed "
      "(master, sub-plans, legacy regression, architecture docs)")
