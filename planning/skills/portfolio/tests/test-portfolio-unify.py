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


# --- `## Decisions in force` sections must never manufacture candidates ---------
# The section is documentation-shaped, so the hazard is silent: a raw `- [ ]`
# there would become a false backlog candidate on EVERY plan that records a
# decision, corrupting the roll-up across ~30 projects. These three lock the
# non-checkbox rule at each format rung.
dec_std = candidates("2026-07-25-decisions-standard-plan.md")
check(
    "Standard: decisions section yields no candidates",
    not any("DECISIONS-SECTION-MARKER" in c["title"] for c in dec_std),
    f"got: {[c['title'] for c in dec_std]}",
)
check(
    "Standard: exactly the one real unchecked task survives",
    [c["title"] for c in dec_std] == ["REAL-CANDIDATE-MARKER the one deferred task"],
    f"got: {[c['title'] for c in dec_std]}",
)
check(
    "Standard: decisions-conformance gate bullet never surfaces",
    not any("contradicts a decision in force" in c["title"] for c in dec_std),
    f"got: {[c['title'] for c in dec_std]}",
)

dec_light = candidates("2026-07-25-decisions-light-plan.md")
check(
    "Light: Context-line decision yields no candidate",
    not any("LIGHTCTX-MARKER" in c["title"] for c in dec_light),
    f"got: {[c['title'] for c in dec_light]}",
)
check(
    "Light: only the unchecked task survives",
    [c["title"] for c in dec_light] == ["LIGHT-CANDIDATE-MARKER first task"],
    f"got: {[c['title'] for c in dec_light]}",
)

# Falsifiability: the three fixtures above obey the non-checkbox convention, so
# they would pass even with no exclusion at all — they prove the format is safe,
# NOT that the parser enforces it. This one breaks the convention deliberately on
# the legacy heuristic path (no `- **Status:**` fields anywhere), which is where a
# stray checkbox in the decisions section really did surface as a false candidate.
dec_legacy = candidates("2026-05-02-decisions-legacy-plan.md")
_legacy_titles = [c["title"] for c in dec_legacy]
check(
    "legacy path: a checkbox smuggled into `Decisions in force` is EXCLUDED",
    not any("LEGACYDEC-CHECKBOX-MARKER" in x for x in _legacy_titles),
    f"got: {_legacy_titles}",
)
check(
    "legacy path: the prose decision bullet never surfaces either",
    not any("LEGACYDEC-PROSE-MARKER" in x for x in _legacy_titles),
    f"got: {_legacy_titles}",
)
check(
    "legacy path: a genuine unchecked item OUTSIDE the section still surfaces "
    "(the exclusion is scoped, not a blanket mute)",
    any("LEGACY-REAL-MARKER" in x for x in _legacy_titles),
    f"got: {_legacy_titles}",
)

dec_master = candidates("2026-07-25-decisions-master-plan.md")
check(
    "Master with a decisions section still yields zero candidates",
    dec_master == [],
    f"got: {dec_master}",
)

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


def case_gate_item_contract():
    """Task 2.1 / BL-077 — the gate-checkbox state is defined ONCE, here.

    STATUS_RE lives in portfolio-unify.py because a change to it silently alters
    done/total math in every consumer at once. A gate checkbox is the same kind
    of shared marker and was NOT here: plan-status-audit.py had defined its own
    GATE_ITEM_RE, so the two could drift with nothing to catch it. That is the
    lockstep break this task closes, not merely the missing state.
    """
    print("gate-item contract — single owner, `[~]` is BLOCKED:")
    check("portfolio-unify.py owns GATE_ITEM_RE (the contract's single definition)",
          hasattr(mod, "GATE_ITEM_RE"))
    if not hasattr(mod, "GATE_ITEM_RE"):
        return
    for mark, want in ((" ", "open"), ("x", "done"), ("X", "done"), ("~", "blocked")):
        m = mod.GATE_ITEM_RE.match(f"- [{mark}] a gate check")
        got = mod.gate_item_state(m.group(1)) if m else None
        check(f"`- [{mark}]` -> {want}", got == want, f"got {got}")
    check("an out-of-contract marker matches nothing, as with STATUS_RE",
          mod.GATE_ITEM_RE.match("- [!] out of contract") is None)
    check("the contract exposes plan_has_blocked_gate() for its consumers",
          hasattr(mod, "plan_has_blocked_gate"))
    if not hasattr(mod, "plan_has_blocked_gate"):
        return
    # The SCOPING boundary, which is the whole risk in this predicate: a `[~]`
    # anywhere else in a plan — a Preflight checklist, a research list — is not
    # gate state, and counting it would block plans that are merely mid-flight.
    inside = ("# P\n\n### Stage 1 Gate\n\n- [x] ok\n- [~] could not run\n")
    outside = ("# P\n\n### Preflight\n\n- [~] could not run\n\n"
               "### Stage 1 Gate\n\n- [x] ok\n")
    after = ("# P\n\n### Stage 1 Gate\n\n- [x] ok\n\n### Task 1.1: t\n\n- [~] a bullet\n")
    check("a `[~]` INSIDE a Stage N Gate block is blocked",
          mod.plan_has_blocked_gate(inside) is True)
    check("a `[~]` under Preflight is NOT gate state",
          mod.plan_has_blocked_gate(outside) is False,
          "a Preflight checklist item would block every plan that has one")
    check("a `[~]` after the gate block closes is NOT gate state",
          mod.plan_has_blocked_gate(after) is False,
          "the scope must end at the next ### heading")


def case_blocked_acceptance_and_propagation():
    """The author's answer-back, and a master inheriting its sub-plans' state.

    A `[~]` gate overrules a human-authored `**Completed:**`, which is right —
    proof outranks claim — but as first shipped it left the author no way to
    say "I know, and I closed it anyway": 22 real vault plans went onto the
    in-flight board permanently, and the ones penalised hardest were the ones
    that had used `[~]` most honestly. `**Blocked-accepted:**` is that answer.

    And a master carries no gate section of its own — 0 of 38 in the live vault
    do — so without propagation the master half of BL-077 never fires at all.
    """
    print("blocked acceptance + master propagation:")
    import tempfile as _t
    check("the contract owns BLOCKED_ACCEPTED_RE", hasattr(mod, "BLOCKED_ACCEPTED_RE"))
    check("and exposes plan_blocked() as the one question consumers ask",
          hasattr(mod, "plan_blocked"))
    if not (hasattr(mod, "BLOCKED_ACCEPTED_RE") and hasattr(mod, "plan_blocked")):
        return

    gate = "### Stage 1 Gate\n\n- [x] host suite\n- [~] device suite\n"
    plain = "# P\n\n### Task 1.1: a\n- **Status:** [x]\n\n" + gate

    b, why = mod.plan_blocked(plain, None)
    check("an unaccepted `[~]` gate is blocked", b is True, f"got {b}")
    check("and the reason names the gate", bool(why) and "gate" in why.lower(),
          f"got {why!r}")

    accepted = plain + "\n**Blocked-accepted:** 2026-08-27 — no CM4 in this lab; shipping anyway\n"
    b2, _ = mod.plan_blocked(accepted, None)
    check("an ACCEPTED blocked gate is not blocked", b2 is False,
          "the author answered back and the tool must stop arguing")
    check("acceptance carries its reason",
          mod.blocked_acceptance(accepted, ) is not None
          and "CM4" in mod.blocked_acceptance(accepted),
          "the marker's own text is the record of why")

    print("  a master inherits a blocked sub-plan, and only an unaccepted one:")
    d = Path(_t.mkdtemp(prefix="unify-master-"))
    (d / "x-sub-01-plan.md").write_text(plain)
    (d / "x-sub-02-plan.md").write_text(accepted)
    master = ("# Master Plan: x\n\n## Sub-plans\n\n"
              "### Sub-plan 1: one\n- **Status:** [x]\n"
              "- **Plan:** ./x-sub-01-plan.md\n\n"
              "### Sub-plan 2: two\n- **Status:** [x]\n"
              "- **Plan:** ./x-sub-02-plan.md\n")
    mp = d / "x-master-plan.md"
    mp.write_text(master)
    b3, why3 = mod.plan_blocked(master, mp)
    check("a master with a blocked sub-plan is blocked", b3 is True, f"got {b3}")
    check("and the reason names the sub-plan",
          bool(why3) and "sub-01" in why3, f"got {why3!r}")

    (d / "x-sub-01-plan.md").write_text(accepted)
    b4, _ = mod.plan_blocked(master, mp)
    check("a master whose sub-plans are all accepted is not blocked", b4 is False,
          "acceptance propagates upward exactly as blockage does")

    print("  and the master's own acceptance closes it whatever its sub-plans say:")
    (d / "x-sub-01-plan.md").write_text(plain)
    b5, _ = mod.plan_blocked(master + "\n**Blocked-accepted:** 2026-08-27 — known\n", mp)
    check("an accepted master is not blocked", b5 is False)

    print("  a missing or unreadable sub-plan file degrades, never raises:")
    mp2 = d / "y-master-plan.md"
    mp2.write_text("# Master Plan: y\n\n## Sub-plans\n\n### Sub-plan 1: one\n"
                   "- **Status:** [x]\n- **Plan:** ./nope-plan.md\n")
    try:
        b6, _ = mod.plan_blocked(mp2.read_text(), mp2)
        ok = b6 is False
    except Exception as e:
        ok = False
        b6 = f"RAISED {type(e).__name__}"
    check("an unresolvable sub-plan link is not blockage", ok, f"got {b6}")


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

# BL-017: backlog/SKILL.md documents `Tags: auto-unified` PLUS the plan's filename
# date stamp. render_entry emitted only `auto-unified` from the start, and nothing
# asserted the line — which is exactly how the claim drifted unnoticed for months.
_tag_lines, _unstamped_tags = [], []
with _tf.TemporaryDirectory() as _td:
    _h = Path(_td) / "h"
    (_h / "plans").mkdir(parents=True)
    _sh.copy(FIXTURES / STALE_FIXTURE[0], _h / "plans" / STALE_FIXTURE[0])
    _sh.copy(FIXTURES / "unstamped-legacy-plan.md", _h / "plans" / "unstamped-legacy-plan.md")
    mod.unify_project(_h, True, _td, False)
    for _ln in (_h / "backlog.md").read_text().splitlines():
        if _ln.startswith("- **Tags:**"):
            (_unstamped_tags if "2020-01-01" not in _ln else _tag_lines).append(_ln)

check("a unified entry is tagged with its plan's filename date stamp",
      _tag_lines and all("auto-unified" in ln and "2020-01-01" in ln for ln in _tag_lines),
      f"got {_tag_lines}")
check("an unstamped plan contributes no fake date tag",
      _unstamped_tags and all(ln.strip() == "- **Tags:** auto-unified" for ln in _unstamped_tags),
      f"the 0000-00-00 sentinel must never be emitted as a tag; got {_unstamped_tags}")

# The stamp is attached in ONE place — the loop over parse_plan's full return — so
# every signal family gets it for free. That is the design's virtue and its risk:
# a future edit that special-cases one branch would regress silently. Assert the
# tag on each family rather than trusting the single-loop invariant to hold.
def _tags_for(fixture, include_stale=False, evidence=None):
    with _tf.TemporaryDirectory() as _d:
        _hh = Path(_d) / "h"
        (_hh / "plans").mkdir(parents=True)
        _sh.copy(FIXTURES / fixture, _hh / "plans" / fixture)
        _o = mod.git_stage_evidence
        mod.git_stage_evidence = lambda _p: (evidence or set())
        try:
            mod.unify_project(_hh, True, _d, include_stale)
        finally:
            mod.git_stage_evidence = _o
        body = (_hh / "backlog.md").read_text()
        return [l for l in body.splitlines() if l.startswith("- **Tags:**")], body

for _fx, _stamp, _sig in (
        ("2026-07-24-partial-status-plan.md", "2026-07-24", "status-"),
        ("2026-07-14-light-inprogress-plan.md", "2026-07-14", "deferred-section"),
):
    _t, _body = _tags_for(_fx)
    check(f"{_sig} entries carry the plan's date stamp ({_fx})",
          _t and all(_stamp in l for l in _t) and _sig in _body,
          f"tags={_t}")

_t, _body = _tags_for(STALE_FIXTURE[0], include_stale=True, evidence=DONE_STAGE)
check("stale-plan-unchecked entries carry the plan's date stamp too",
      _t and all("2020-01-01" in l for l in _t) and "stale-plan-unchecked" in _body,
      f"tags={_t}")

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

case_gate_item_contract()
case_blocked_acceptance_and_propagation()


def case_contract_warnings():
    """The parser stays strict; the mistake is reported where it is made.

    Five backlog entries (BL-044/053/054/059/107) asked one question — authors
    write a marker several ways, the parser accepts one — and it was answered
    three separate times before anyone noticed it was one question. Decided
    2026-09-01: do NOT widen the regexes, warn instead. Each widening trades a
    rare miss for a routine false read in the OPTIMISTIC direction, which is the
    worse failure: it reports work as finished.

    Every warning below was measured over 620 vault plans before shipping and
    fires 0 or 1 times per document corpus-wide, with zero false positives. The
    close-out rule needed two rounds of narrowing to get there — see its regex.
    """
    codes = lambda t, p=None: sorted({c for c, _l, _e in mod.contract_warnings(t, p)})

    check("a well-formed plan warns about nothing",
          codes("# Plan: x\n\n### Task 1.1: a\n- **Status:** [x] done\n") == [])

    # BL-044 — not miscounted, ABSENT: the plan reads as fully complete.
    check("an out-of-contract Status marker warns",
          codes("### Task 1.1: a\n- **Status:** [!] blocked on the owner\n")
          == ["STATUS-OUT-OF-CONTRACT"])
    check("a Status line with no brackets at all warns too",
          codes("- **Status:** done\n") == ["STATUS-OUT-OF-CONTRACT"])

    # BL-107 — parses only at column 0; indented under the gate item it accepts
    # (the natural place) it parses as absent and the plan stays on the board.
    check("an indented **Blocked-accepted:** warns",
          codes("  **Blocked-accepted:** 2026-08-27 — why\n")
          == ["ACCEPTANCE-INDENTED"])
    check("the same marker at column 0 does not",
          codes("**Blocked-accepted:** 2026-08-27 — why\n") == [])

    # BL-053 — a close-out in an unrecognised dialect reads as in flight forever.
    check("a qualified **Completed (...):** warns",
          codes("**Completed (through Stage 7):** 2026-07-03\n")
          == ["CLOSE-OUT-DIALECT"])
    check("a dated **Close-out (YYYY-MM-DD):** warns",
          codes("**Close-out (2026-08-03):** Complete.\n") == ["CLOSE-OUT-DIALECT"])
    check("the plain **Completed:** form does not",
          codes("**Completed:** 2026-08-30 — commits: abc\n") == [])
    # The narrowing that took this from 25 hits to 5. "Close-out" is a common
    # SECTION LABEL here, and labelling a section is not claiming completion.
    check("a **Close-out evaluator:** section label does NOT warn",
          codes("**Close-out evaluator:** PASS, 0 Blocking, 4 Material\n") == [])
    check("prose beginning with the bare word does NOT warn",
          codes("close-out, each against evidence available now: a claim\n") == [])

    # BL-054 — a bare-ordinal register opens on nothing, so the master reads 0/0.
    master = "# Master Plan: x\n\n### 01. Foundation and domain contracts\n"
    check("a bare-ordinal register heading warns in a master",
          codes(master) == ["REGISTER-DIALECT"])
    check("the recognised Sub-plan form does not",
          codes("# Master Plan: x\n\n### Sub-plan 1: Foundation\n") == [])
    check("the same ordinal heading in a NON-master is not a register at all",
          codes("# Plan: x\n\n### 01. Research summary\n") == [])

    # BL-059 — zero occurrences vault-wide when filed; the parsers are
    # deliberately NOT taught about fences, because changing five regexes'
    # scanning model on a corpus with no instance exceeds its evidence.
    fenced = "# Plan: x\n\n```\n- **Status:** [x] an EXAMPLE, not a real marker\n```\n"
    check("a marker inside a fence warns", codes(fenced) == ["MARKER-IN-FENCE"])
    check("and the parser still reads it, which is exactly why the warning exists",
          mod.STATUS_RE.match("- **Status:** [x] an EXAMPLE, not a real marker") is not None)

    # Line numbers make it actionable rather than merely true.
    w = mod.contract_warnings("a\nb\n  **Blocked-accepted:** 2026-01-01 — w\n")
    check("a warning carries its line number", w and w[0][1] == 3, str(w))


case_contract_warnings()

if failures:
    print(f"\n{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("\nOK — all plan-parser fixture checks passed "
      "(master, sub-plans, legacy regression, architecture docs)")
