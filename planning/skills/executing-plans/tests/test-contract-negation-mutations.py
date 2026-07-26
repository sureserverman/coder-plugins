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

FAILURES = []


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
    target = tmp / rel
    body = target.read_text(encoding="utf-8")
    if old not in body:
        return False
    target.write_text(body.replace(old, new, 1), encoding="utf-8")
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

    print(f"\n{len(MUTATIONS)} negated restatements, {len(PARAPHRASES)} paraphrases")
    if FAILURES:
        print("\nFAILURES:", file=sys.stderr)
        for f in FAILURES:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print("OK — every pinned claim rejects its inversion and accepts a rewording")
    return 0


if __name__ == "__main__":
    sys.exit(main())
