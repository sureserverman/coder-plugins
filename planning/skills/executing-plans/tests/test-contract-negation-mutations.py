#!/usr/bin/env python3
"""Meta-suite: proves the prose-contract checks actually BIND — run directly:
    python3 planning/skills/executing-plans/tests/test-contract-negation-mutations.py

test-gate-remediation-contract.py asserts that skill prose states a set of rules. But a
check can pass for the wrong reason — a loose anchor, a window that reaches into a
neighbouring bullet, a screen that examines the wrong side of a match — and then it is
decoration: it goes green whether or not the rule survives. Three Criticals on the
dispatch-fidelity branch were exactly that, each found by a human reviewer several rounds
after the check shipped, and each time the evidence was a throwaway script that lived in
a scratchpad and was deleted.

So the evidence lives here instead. Each entry below replaces a clause with a NEGATED
RESTATEMENT — not a deletion — and asserts the named check goes red. The plan-gate rule
"each new assertion rejects a negated restatement, verified by mutation" stops being a
per-task ritual a reviewer has to re-litigate and becomes a thing CI runs.

Deletion is the easy case and every check catches it. Inversion is the case that matters,
because prose that names a rule in order to opt out of it ("a reason is NOT required")
reads perfectly natural and is how these rules actually erode.

How it works: the tree is copied to a temp dir, the mutation is applied to the copy, and
the contract suite is re-run against it via CONTRACT_SKILLS_ROOT. The real tree is never
written to, so a crash mid-run cannot leave the repo in a mutated state — which the
scratchpad harnesses this replaces could, and nearly did.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS_ROOT = HERE.parent.parent                     # planning/skills/
CONTRACT = HERE / "test-gate-remediation-contract.py"

EP = "executing-plans/SKILL.md"
PP = "planning-projects/SKILL.md"
DPA = "dispatching-parallel-agents/SKILL.md"

# (label, relative file, original, negated restatement, [checks that must go red])
#
# Keep one entry per SUBSTANTIVE claim added by the dispatch-fidelity plan. A claim with
# no negatable form — a literal trailer value, a section locator — is deliberately absent
# rather than faked with a deletion; those are presence checks and say so at their site.
MUTATIONS = [
    # --- Stage 1: the Parallel field is a directive (groups 11, 11c) ---
    ("lone task returned to the caller", DPA,
     "A lone ready task is **still dispatched**: |S| = 1 runs as a single",
     "A lone ready task is **never dispatched**: |S| = 1 does not run as a single",
     ["a lone dispatchable task is still dispatched, not returned to the caller"]),
    ("no-sibling case made discretionary", PP,
     "no concurrent sibling",
     "no concurrent sibling (in which case dispatch is optional)",
     ["a lone ready task with no concurrent sibling is still dispatched"]),

    # --- Stage 2 Task 2.1: Preflight roster + probe (group 12) ---
    ("probe not required", EP,
     "**Probe the capability.** Dispatch one throwaway subagent",
     "**Probing is unnecessary.** Do not dispatch a throwaway subagent",
     ["Preflight probes dispatch with a throwaway subagent"]),
    ("unavailable dispatch stops failing Preflight", EP,
     "dispatch is unavailable or disallowed in\nthis session and the roster lists at least one task, Preflight fails",
     "dispatch is unavailable or disallowed in\nthis session, Preflight does not fail",
     ["an unavailable dispatch is a Preflight failure"]),
    ("roster narrowed from the whole plan", EP,
     "Sweep **every task in the plan**, across all stages",
     "Sweep the current stage only, never the whole plan",
     ["the roster sweeps every task in the plan"]),

    # --- Stage 2 Task 2.2: the executor trailer (group 13) ---
    ("trailer not required", EP,
     "**Every per-task commit ends with an executor trailer**",
     "**No per-task commit needs an executor trailer**",
     ["every per-task commit carries an executor trailer"]),
    ("trailer allowed to wrap", EP,
     "**Keep the trailer to one physical line.**",
     "**A trailer may wrap onto as many lines as it needs.**",
     ["the trailer is constrained to one physical line"]),
    ("false trailer made acceptable", EP,
     "**A trailer that misstates who ran the task is worse than none**",
     "**A trailer that misstates who ran the task is no worse than none**",
     ["a misstated trailer is called worse than none"]),
    ("Status flip claimed to record the executor", EP,
     "records that the task is done, never who did it",
     "records that the task is done, including who did it",
     ["the flip's scope is stated as EXCLUDING who did it"]),

    # --- Stage 2 Task 2.3: the gate ledger (group 14) ---
    ("gate counts dropped", EP,
     "The gate report states the stage's dispatched-vs-inline counts",
     "The gate report needs no dispatched-vs-inline counts",
     ["the gate report states dispatched-vs-inline counts"]),
    # The inversion three rounds of review took to find: the object is negated, not the
    # verb, and every earlier window-based screen missed it.
    ("per-task reason negated at the object", EP,
     "and a reason for every inlined `Parallel: YES` task",
     "and no reason for every inlined `Parallel: YES` task",
     ["a reason is required per inlined Parallel: YES task"]),
    # The three a round-3 review constructed independently, all of which passed the first
    # affirms_claim: the negation TRAILS the match inside the same clause. Kept as three
    # entries rather than one because they negate by three different mechanisms —
    # a modal qualifier, a verb, and an adjective — and only the first was on NEGATION_RE.
    ("reason softened by a trailing qualifier", EP,
     "and a reason for every inlined `Parallel: YES` task.**",
     "and a reason for every inlined `Parallel: YES` task, though this is not mandatory.**",
     ["a reason is required per inlined Parallel: YES task"]),
    ("reason waived after the fact", EP,
     "and a reason for every inlined `Parallel: YES` task.**",
     "and a reason for every inlined `Parallel: YES` task is waived.**",
     ["a reason is required per inlined Parallel: YES task"]),
    ("reason marked optional after the fact", EP,
     "and a reason for every inlined `Parallel: YES` task.**",
     "and a reason for every inlined `Parallel: YES` task, which is optional.**",
     ["a reason is required per inlined Parallel: YES task"]),
    ("blank trailer read as inline", EP,
     "**An empty trailer value is `unknown`, never `inline`.**",
     "**An empty trailer value simply counts as `inline`.**",
     ["an unparseable trailer is counted as unknown, not as inline"]),
    ("unknowns absorbed into the counts", EP,
     "count it as `unknown` if it says nothing either, and report the unknowns",
     "count it as `inline` if it says nothing either, and leave the unknowns out",
     ["the unknowns are reported, not absorbed into the counts"]),
    # --- Stage 2 Task 2.4: unperformable dispatch/review stops the run (group 15) ---
    ("unperformable dispatch no longer stops the run", EP,
     "**A mandated verification or dispatch cannot be performed**",
     "**A mandated verification or dispatch need not be performed**",
     ["an unperformable mandated dispatch or review is a Stop condition"]),
    ("inline substitution re-permitted", EP,
     "Substituting inline execution, or proceeding unreviewed, is not a documented resolution; asking is",
     "Substituting inline execution, or proceeding unreviewed, is a documented resolution",
     ["inline substitution is named as not a resolution"]),
    ("decision taken back from the user", EP,
     "**The choice belongs to the user**",
     "**The choice does not belong to the user**",
     ["the decision is routed to the user, with the options named"]),
    # --- Coverage backfill. A gate review and an evaluator independently found that the
    # entries above covered only the checks someone remembered; check_coverage() now makes
    # that a failure. These are written as TRAILING qualifiers wherever the claim allows,
    # because that is the form that defeated three successive versions of the helper —
    # substring replacement is the easy case every check already catches.
    ("empty-set early return widened", DPA,
     "Only |S| = 0 returns control to the caller with nothing to do.",
     "Any |S| below 2 returns control to the caller with nothing to do.",
     ["only an EMPTY set returns control to the caller"]),
    ("banned |S| < 2 threshold reintroduced", DPA,
     "Call this set **S**. A lone ready task",
     "Call this set **S**. If |S| < 2 there is no parallelism to exploit. A lone ready task",
     ["no threshold makes a lone YES task skip dispatch"]),
    ("probe no longer scoped to this session", EP,
     "One trivial dispatch proves the mechanism works in *this* session",
     "One trivial dispatch is assumed to carry over, so nothing is proven in *this* session",
     ["the probe proves dispatch in THIS session"]),
    ("routed agent type dropped from the roster", EP,
     "with the\n   `subagent_type` it routes to per",
     "with no `subagent_type`, and never routed per",
     ["each rostered task carries its routed agent type and the routing source"]),
    ("empty roster no longer written down", EP,
     "An empty roster is a legitimate result — write `0 tasks`",
     "An empty roster is a legitimate result — write nothing at all",
     ["an empty roster is written down, not omitted"]),
    ("Preflight's inline substitution re-permitted", EP,
     "Substituting inline execution on your own authority is not a\nresolution",
     "Substituting inline execution on your own authority is a documented\nresolution",
     ["inline substitution is refused as a resolution"]),
    ("trailer allowed to name the routed agent instead", EP,
     "Name the actual `subagent_type` that ran the work, not the routing table's suggestion for it",
     "Name the `subagent_type` the routing table suggests, never the one that actually ran",
     ["the trailer names the agent that actually ran, not the routed one"]),
    ("failed-dispatch form and prose both dropped", EP,
     [("   Executor: inline (dispatch failed)                          (the body says why)\n",
       "   Executor: inline                                            (however it ran)\n"),
      ("and a dispatch that failed and was finished inline says so",
       "and a dispatch that did not succeed needs no mention")],
     None,
     ["a failed dispatch finished inline is recorded as such"]),
    ("Status-flip pointer to the trailer removed", EP,
     "Rule 7's executor trailer is what carries that",
     "no executor trailer is needed beyond it",
     ["the Status flip is stated NOT to record the executor"]),
    ("reconciliation against the roster dropped", EP,
     "and reconcile against the roster Preflight declared",
     "and never reconcile against the roster Preflight declared",
     ["the counts are reconciled against Preflight's roster"]),
    ("counts taken from memory after all", EP,
     "Read them off the executor trailers rather than from memory",
     "Recall them from memory rather than reading the executor trailers",
     ["the counts are read off the executor trailers, not from memory"]),
    ("fully-dispatched stage allowed to stay silent", EP,
     "A stage that dispatched everything it marked says `dispatch: 4 of 4` rather than saying nothing",
     "A stage that dispatched everything it marked omits the line, since silence is unambiguous",
     ["a fully-dispatched stage still states its count"]),
    # The authoring side, both sites, as a set — fixing one and leaving the other is the
    # sibling-survival pattern group 12b exists to catch, so the mutation tests it as one.
    ("authoring sites drop the probe", PP,
     "throwaway subagent",
     "throwaway subagent is unnecessary and no",
     ["dispatch probe required at: planning-projects Phase 1 checklist",
      "dispatch probe required at: planning-projects plan template"]),
    # Both capitalisations, because the two sites word it differently ("Every" in the
    # Phase 1 checklist, "every" in the template). Mutating one spelling left the other
    # site intact and its check green — the sibling-survival pattern, inside the mutation
    # meant to prove the sibling pair is checked as a set.
    ("authoring sites drop the roster", PP,
     [("Every `Parallel: YES` task", "No `Parallel: YES` task"),
      ("every `Parallel: YES` task", "no `Parallel: YES` task")],
     None,
     ["dispatch roster required at: planning-projects Phase 1 checklist",
      "dispatch roster required at: planning-projects plan template"]),
    ("stated reason turned into authorisation", EP,
     "so an inlined YES task is a **deviation being disclosed**, not a choice being ratified",
     "so an inlined YES task with a stated reason is a choice the gate ratifies",
     ["a stated reason is disclosure, not authorisation"]),
]

# A faithful rewording must PASS. A guard that only accepts one sentence is over-fit
# (BL-031) and will reject the next legitimate clarification instead of the next
# regression — which is a slower, quieter failure than a missing check.
PARAPHRASES = [
    ("gate ledger reworded", EP,
     "**The gate report states the stage's dispatched-vs-inline counts, and a reason for every inlined `Parallel: YES` task.**",
     "**The gate report discloses, for the stage, how many `Parallel: YES` tasks were dispatched versus run inline, and why every inlined one was.**"),
    ("trailer requirement reworded", EP,
     "**Every per-task commit ends with an executor trailer**",
     "**An executor trailer is required on every per-task commit**"),
    # The false-positive direction of the same span bug: a comma-joined independent
    # clause carrying its own (unrelated) negation must not reject the claim beside it.
    ("neighbouring negated clause added", EP,
     "**The gate report states the stage's dispatched-vs-inline counts, and a reason",
     "**The gate report never skips a stage, and it states the stage's dispatched-vs-inline counts, and a reason"),
]

# The checks this plan added, computed once by diffing the suite's own printed check
# names against the branch base (796ec3f, "Stage 1 green") and pinned here. Scope is
# deliberately this plan's additions rather than all 120 assertions: the older ones
# predate the rule and retro-failing them would only teach authors to route around the
# harness — the same reasoning validate-gate-checks.py uses for pre-existing plans.
SCOPE = [
    'Preflight probes dispatch with a throwaway subagent',
    'Preflight section present',
    'Step 3.3 Status-flip rule located',
    'Step 3.3 commit rule located',
    'Step 3.5 gate-report block located',
    'Stop-conditions list located',
    'a failed dispatch finished inline is recorded as such',
    'a fully-dispatched stage still states its count',
    'a lone dispatchable task is still dispatched, not returned to the caller',
    'a misstated trailer is called worse than none',
    'a reason is required per inlined Parallel: YES task',
    'a stated reason is disclosure, not authorisation',
    'an empty roster is written down, not omitted',
    'an unavailable dispatch is a Preflight failure',
    'an unparseable trailer is counted as unknown, not as inline',
    'an unperformable mandated dispatch or review is a Stop condition',
    'dispatch probe required at: planning-projects Phase 1 checklist',
    'dispatch probe required at: planning-projects plan template',
    'dispatch roster required at: planning-projects Phase 1 checklist',
    'dispatch roster required at: planning-projects plan template',
    'dispatching-parallel-agents/SKILL.md is readable',
    'each rostered task carries its routed agent type and the routing source',
    'every per-task commit carries an executor trailer',
    'inline substitution is named as not a resolution',
    'inline substitution is refused as a resolution',
    'no threshold makes a lone YES task skip dispatch',
    'only an EMPTY set returns control to the caller',
    'site present: planning-projects Phase 1 checklist',
    'site present: planning-projects plan template',
    'the Status flip is stated NOT to record the executor',
    'the counts are read off the executor trailers, not from memory',
    'the counts are reconciled against Preflight\'s roster',
    'the decision is routed to the user, with the options named',
    "the flip's scope is stated as EXCLUDING who did it",
    'the gate report states dispatched-vs-inline counts',
    'the probe proves dispatch in THIS session',
    'the roster sweeps every task in the plan',
    'the trailer is constrained to one physical line',
    'the trailer names the agent that actually ran, not the routed one',
    'the unknowns are reported, not absorbed into the counts',
    'trailer form documented: dispatched — <subagent_type>',
    'trailer form documented: inline',
]

# Checks added by the dispatch-fidelity plan that are deliberately NOT mutation-tested,
# each with the reason. A gate reviewer and an evaluator independently found that the
# harness silently covered only the checks someone remembered to declare — so coverage is
# now asserted (see check_coverage), and an exemption has to be written down here rather
# than achieved by forgetting. "It has no negatable form" is the only accepted reason.
EXEMPT = {
    # Section locators: they assert a slice was found. Their inverse is deletion of a
    # heading, which they already catch; there is no way to word "this heading exists"
    # negatively while it still exists.
    "Preflight section present": "locator",
    "Step 3.3 commit rule located": "locator",
    "Step 3.3 Status-flip rule located": "locator",
    "Step 3.5 gate-report block located": "locator",
    "Stop-conditions list located": "locator",
    "site present: planning-projects Phase 1 checklist": "locator",
    "site present: planning-projects plan template": "locator",
    "dispatching-parallel-agents/SKILL.md is readable": "file-readable guard",
    # Literal trailer values. `Executor: inline` is a token, not a proposition; there is
    # no negated restatement of a string that still leaves the string documented.
    "trailer form documented: inline": "literal token",
    "trailer form documented: dispatched — <subagent_type>": "literal token",
}

FAILURES = []


def check_coverage(scope_names, covered):
    """Every in-scope check must have a declared inversion, or a written exemption.

    This is the meta-suite's own class-predicate. Without it the harness proves exactly
    as much as its author remembered to type, which is how ~12 checks reached a stage
    gate with the gate bullet "each new assertion rejects a negated restatement"
    asserting something nobody had tested. A coverage number nobody computes is the same
    defect as a dispatch count nobody counts — the thing this whole plan is about.
    """
    missing = sorted(n for n in scope_names if n not in covered and n not in EXEMPT)
    stale = sorted(n for n in EXEMPT if n not in scope_names)
    if missing:
        FAILURES.append("no declared inversion (and no exemption) for: "
                        + "; ".join(missing))
    if stale:
        FAILURES.append("EXEMPT names a check that no longer exists (renamed or "
                        "removed, so its exemption is silently covering nothing): "
                        + "; ".join(stale))


def run_contract(root):
    env = dict(os.environ, CONTRACT_SKILLS_ROOT=str(root))
    p = subprocess.run([sys.executable, str(CONTRACT)],
                       capture_output=True, text=True, env=env)
    # Keep the WHOLE failure line and match expectations by prefix. Splitting name from
    # detail on ":" looks obvious and is wrong — check names contain colons themselves
    # ("a reason is required per inlined Parallel: YES task"), so it silently truncates
    # them and every expectation misses. Caught on this file's first run.
    red = [ln.strip().lstrip("✗").strip()
           for ln in (p.stdout + p.stderr).splitlines() if ln.strip().startswith("✗")]
    return p.returncode, red


def apply_to_copy(tmp, rel, old, new):
    """`old` may be a list of (old, new) pairs — some requirements are stated at two
    sites (a form list AND the prose), and negating one while leaving the other is a
    partial deletion, not a restatement. Those must be mutated together or the check is
    right to stay green.
    """
    pairs = old if isinstance(old, list) else [(old, new)]
    target = tmp / rel
    body = target.read_text(encoding="utf-8")
    if any(o not in body for o, _ in pairs):
        return False
    for o, n in pairs:
        # EVERY occurrence, not the first. A requirement stated at N sites has to be
        # negated at all N or the mutation is a partial deletion, and the check is right
        # to stay green — which is exactly what happened when the two planning-projects
        # Preflight sites were mutated one at a time: the surviving sibling satisfied the
        # check. That is the instance-vs-class rule, applied to the mutation itself.
        body = body.replace(o, n)
    target.write_text(body, encoding="utf-8")
    return True


def main():
    rc, red = run_contract(SKILLS_ROOT)
    if rc != 0:
        print("baseline contract suite is RED — fix it before mutation-testing",
              file=sys.stderr)
        for r in sorted(red):
            print(f"  ✗ {r}", file=sys.stderr)
        return 1

    for label, rel, old, new, expect in MUTATIONS:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "skills"
            shutil.copytree(SKILLS_ROOT, tmp,
                            ignore=shutil.ignore_patterns("__pycache__"))
            if not apply_to_copy(tmp, rel, old, new):
                FAILURES.append(f"{label}: anchor text not found in {rel} — the "
                                f"mutation never applied, so nothing was proven")
                continue
            rc, red = run_contract(tmp)
            missed = [e for e in expect if not any(ln.startswith(e) for ln in red)]
            if rc == 0:
                FAILURES.append(f"{label}: suite stayed GREEN under a negated "
                                f"restatement — the rule is unguarded")
            elif missed:
                FAILURES.append(f"{label}: went red, but not at {missed} — some other "
                                f"check caught it, so the intended guard is unproven")
            print(f"  {'ok ' if not missed and rc else 'BAD'}  {label}")

    for label, rel, old, new in PARAPHRASES:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "skills"
            shutil.copytree(SKILLS_ROOT, tmp,
                            ignore=shutil.ignore_patterns("__pycache__"))
            if not apply_to_copy(tmp, rel, old, new):
                FAILURES.append(f"{label}: paraphrase anchor not found in {rel}")
                continue
            rc, red = run_contract(tmp)
            if rc != 0:
                FAILURES.append(f"{label}: a faithful rewording turned the suite RED at "
                                f"{red} — the guard is over-fit (BL-031)")
            print(f"  {'ok ' if rc == 0 else 'BAD'}  paraphrase: {label}")

    covered = {name for _, _, _, _, expects in MUTATIONS for name in expects}
    rc0, _ = run_contract(SKILLS_ROOT)
    ran = subprocess.run([sys.executable, str(CONTRACT)], capture_output=True, text=True)
    live = {ln.strip()[2:] for ln in ran.stdout.splitlines() if ln.startswith("  - ")}
    gone = sorted(n for n in SCOPE if n not in live)
    if gone:
        FAILURES.append("SCOPE names a check the suite no longer runs (renamed or "
                        "deleted, so its coverage is fictional): " + "; ".join(gone))
    check_coverage(SCOPE, covered)

    print(f"\n{len(MUTATIONS)} negated restatements, {len(PARAPHRASES)} paraphrases, "
          f"{len(SCOPE)} checks in scope ({len(EXEMPT)} exempt)")
    if FAILURES:
        print("\nFAILURES:", file=sys.stderr)
        for f in FAILURES:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print("OK — every pinned claim rejects its inversion and accepts a rewording")
    return 0


if __name__ == "__main__":
    sys.exit(main())
