#!/usr/bin/env python3
"""Structure suite for the background-work rules (BL-120) — run directly (CI convention):

    python3 planning/skills/executing-plans/tests/test-background-work-contract.py

PROSE contracts, not behavior: the suite asserts the rules are stated where the
executor and a dispatched agent read them, using the shared negation screening
(DEC-008, test-gate-remediation-contract.py's affirms_claim). What it pins:

  1. task-execution.md waits on a background job by its own completion (the harness
     notification, `wait <pid>`, or a sentinel file the job writes last), and says why
     a process-name search is not that: `pgrep -f` matches its own command line.
  2. close-out.md and session-handoff.md § On `handoff` both carry the reap step: list
     what this run started (`TaskList`), stop each whose result was used (`TaskStop`),
     and name any still running in the report.
  3. The return-clean clause — an agent returns only after its own background work has
     finished or been stopped, and says which — stands in all three places a dispatched
     agent is briefed: the dispatch template's `## Return` block, and stage-gate.md's
     evaluator and Tier-2 sections.

The incident (BL-120): a gate waited on `until ! pgrep -f run-tests.sh` — which matched
its own shell for ever — and a background reviewer kept running after its verdict had
been used, its commands still writing into the tree.
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
REFS = os.path.join(SKILLS, "executing-plans", "references")
TASKEXEC = os.path.join(REFS, "task-execution.md")
CLOSEOUT = os.path.join(REFS, "close-out.md")
HANDOFF = os.path.join(REFS, "session-handoff.md")
STAGEGATE = os.path.join(REFS, "stage-gate.md")
DISPATCH = os.path.join(SKILLS, "dispatching-parallel-agents", "SKILL.md")
HELPER = os.path.join(HERE, "test-gate-remediation-contract.py")

spec = importlib.util.spec_from_file_location("_gate_contract", HELPER)
_helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_helper)
affirms_claim = _helper.affirms_claim

FAILED = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f" — {detail}"))
    if not ok:
        FAILED.append(name)


def ws(pattern):
    """Every space may be any whitespace run: the references are hard-wrapped."""
    return re.sub(r" ", r"\\s+", pattern)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def section(text, start_pat, end_pat):
    m = re.search(start_pat, text, re.M)
    if not m:
        return ""
    rest = text[m.start():]
    e = re.search(end_pat, rest[1:], re.M)
    return rest[: e.start() + 1] if e else rest


RETURN_CLEAN = ws(r"returns only after its own background work has finished or been stopped")


def main():
    # --- 1. the wait rule -------------------------------------------------------------
    wait = section(read(TASKEXEC), r"^## Waiting on background work", r"^## ")
    check("task-execution: § Waiting on background work located", bool(wait))
    check("task-execution: wait on a background job by its own completion",
          affirms_claim(wait, ws(r"wait on a background job by its own completion")),
          "no non-negated 'wait on a background job by its own completion'")
    check("task-execution: names the three completion signals",
          all(re.search(p, wait) for p in (ws(r"harness"), r"`wait <pid>`", ws(r"sentinel file"))),
          "one of: harness notification / `wait <pid>` / sentinel file is absent")
    check("task-execution: names the `pgrep -f` self-match",
          "`pgrep -f`" in wait and affirms_claim(wait, ws(r"matches its own command line")),
          "`pgrep -f` … 'matches its own command line' absent or negated")

    # --- 2. the reap step at close-out and handoff --------------------------------------
    closeout = read(CLOSEOUT)
    handoff = section(read(HANDOFF), r"^## On `handoff`", r"^## ")
    for name, text in (("close-out", closeout), ("handoff", handoff)):
        check(f"{name}: lists what the run started with `TaskList`",
              "`TaskList`" in text and affirms_claim(text, ws(r"list the background tasks and agents this run started")),
              "'list the background tasks and agents this run started' + `TaskList` absent")
        check(f"{name}: stops each whose result was used with `TaskStop`",
              "`TaskStop`" in text and affirms_claim(text, ws(r"stop each whose result was used")),
              "'stop each whose result was used' + `TaskStop` absent")
        check(f"{name}: names any still running in the report",
              affirms_claim(text, ws(r"name each one still running")),
              "'name each one still running' absent or negated")

    # --- 3. return-clean in the three briefs --------------------------------------------
    ret = section(read(DISPATCH), r"^## Return", r"^```")
    stagegate = read(STAGEGATE)
    evaluator = section(stagegate, r"^## Independent evaluator for non-command checks", r"^## ")
    tier2 = section(stagegate, r"^## Deep code review \(Tier 2\)", r"^## ")
    for name, text in (("dispatch template ## Return", ret),
                       ("stage-gate evaluator brief", evaluator),
                       ("stage-gate Tier-2 brief", tier2)):
        check(f"{name}: an agent returns only after its own background work finished or stopped",
              bool(text) and affirms_claim(text, RETURN_CLEAN),
              "return-clean clause absent or negated")
        check(f"{name}: ...and says which",
              bool(text) and re.search(RETURN_CLEAN + r"[^.]{0,40}" + ws(r"and says which"),
                                       text) is not None,
              "'and says which' absent")

    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed:")
        for f in FAILED:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
