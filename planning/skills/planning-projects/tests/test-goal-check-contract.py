#!/usr/bin/env python3
"""Structure suite for the `(goal)` gate-check rule (DEC-033) — run directly (CI convention):

    python3 planning/skills/planning-projects/tests/test-goal-check-contract.py

PROSE contract, not behavior: it asserts that every planning-projects file carrying a part
of the rule states that part, using the shared negation screening (DEC-008). What it pins:

  1. gate-authoring.md owns the rule: the goal check sweeps the WHOLE artifact, never a
     subset by category; it sits in every gate from the first whose artifact exists; it is
     cheap; `(judgment)` is allowed on it only where no command decides the goal; and the
     measured incident is cited.
  2. The three templates (Standard, master register entry, Light) carry a `(goal)` line in
     their gate blocks, and master-plan-format.md says the sub-plan's own gates carry one too.
  3. authoring-checklist.md asks for zero GOAL-CHECK-MISSING on Standard, master and Light
     plans, and the Light "goal-level end-to-end check" item is gone — replaced, not doubled.
  4. set-valued-checks.md names the filtered-subset shape and `(scoped)` as its answer.
  5. SKILL.md's validator checklist line names GOAL-CHECK-MISSING.

The incident: engineering-skills 2026-10-07 sub-01 passed every gate while two `-fork` rows
had no ruling; its sweep was `awk -F'|' '$3 ~ /-new/'`, and the close-out evaluator — the
first reader of the plan goal — found the gap after 4 remediation rounds.
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
PP = os.path.join(SKILLS, "planning-projects")
REF = os.path.join(PP, "references")
HELPER = os.path.join(SKILLS, "executing-plans", "tests", "test-gate-remediation-contract.py")

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


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def section(text, heading_re):
    m = re.search(heading_re, text, re.M)
    if not m:
        return ""
    level = len(re.match(r"#+", text[m.start():]).group(0))
    nxt = re.search(rf"^#{{1,{level}}} ", text[m.end():], re.M)
    return text[m.start(): m.end() + nxt.start()] if nxt else text[m.start():]


def gate_blocks(text):
    """Every gate block's checkbox lines: under a `### … Gate` heading or a `**Gate:**`."""
    out = []
    for m in re.finditer(r"^(?:#{2,4}\s+(?:Stage\s+\S+\s+)?Gates?\b.*|\*\*Gates?:\*\*)\s*$",
                         text, re.M):
        seg = text[m.end():]
        end = re.search(r"^(?:#{1,4} |\*\*Gates?:\*\*|```)", seg, re.M)
        out.append(seg[: end.start()] if end else seg)
    return out


def main():
    ga = read(REF, "gate-authoring.md")
    sec = section(ga, r"^## The plan's goal is a check from the first gate")
    check("gate-authoring: the (goal) section is present", bool(sec))
    check("gate-authoring: every plan format and master entry carries a (goal) check",
          affirms_claim(sec, ws(r"Every Standard plan, Light plan and master register entry "
                                r"carries at least one gate check marked `\(goal\)`")),
          "the obligation is absent or negated")
    check("gate-authoring: the goal check sweeps the whole artifact",
          affirms_claim(sec, ws(r"The goal check sweeps the whole artifact")),
          "whole-artifact scope is absent or negated")
    check("gate-authoring: never a subset by category",
          re.search(ws(r"never a subset by category"), sec) is not None,
          "the subset prohibition is absent")
    check("gate-authoring: it sits in every gate from the first one whose artifact exists",
          affirms_claim(sec, ws(r"It sits in every gate from the first one whose artifact exists")),
          "the DEC-017 position is absent or negated")
    check("gate-authoring: it must be cheap",
          affirms_claim(sec, ws(r"It must be cheap")), "the cost bound is absent or negated")
    check("gate-authoring: (judgment) only where no command can decide the goal",
          re.search(ws(r"`\(judgment\)` is allowed on it only where no command can decide the goal"),
                    sec) is not None,
          "the (judgment) bound is absent")
    check("gate-authoring: a new plan is presented with zero GOAL-CHECK-MISSING",
          affirms_claim(sec, ws(r"A \*\*new\*\* plan is presented with zero GOAL-CHECK-MISSING")),
          "the new-plan bar is absent or negated")
    check("gate-authoring: cites the measured incident",
          "2026-10-07-upstream-delta-sub-01" in sec and re.search(ws(r"4 remediation rounds"), sec)
          and "$3 ~ /-new/" in sec,
          "the incident (plan, rounds, filter) is not cited")

    tpl = read(REF, "plan-document-template.md")
    check("plan-document-template: a gate block carries a (goal) line",
          any("**(goal)**" in b for b in gate_blocks(tpl)), "no (goal) line in a gate block")

    mpf = read(REF, "master-plan-format.md")
    blocks = gate_blocks(mpf)
    check("master-plan-format: every register **Gate:** block in the template carries (goal)",
          bool(blocks) and all("**(goal)**" in b for b in blocks
                               if re.search(r"^- \[ \]", b, re.M)),
          "a template register entry's Gate block has no (goal) line")
    check("master-plan-format: the sub-plan's own gates carry one too",
          affirms_claim(mpf, ws(r"the sub-plan's own gates carry a `\(goal\)` check")),
          "the sub-plan half of the rule is absent or negated")

    lpf = read(REF, "light-plan-format.md")
    check("light-plan-format: the gate template carries a (goal) line",
          any("**(goal)**" in b for b in gate_blocks(lpf)), "no (goal) line in the gate template")
    check("light-plan-format: the old 'goal proven end-to-end' placeholder is replaced",
          "the plan's goal proven end-to-end]" not in lpf, "the old placeholder survives")

    ac = read(REF, "authoring-checklist.md")
    std = section(ac, r"^## Checklist — Standard plans")
    mas = section(ac, r"^## Additionally, for a decomposed project")
    lig = section(ac, r"^## Checklist — Light plans")
    for name, part in (("Standard", std), ("master", mas), ("Light", lig)):
        check(f"authoring-checklist: the {name} list asks for zero GOAL-CHECK-MISSING",
              re.search(r"^- \[ \] .*zero GOAL-CHECK-MISSING", part, re.M) is not None,
              f"no {name} item")
    check("authoring-checklist: the Light 'goal-level end-to-end check' item is gone",
          "goal-level end-to-end check" not in ac, "the replaced item survives beside the new one")

    svc = read(REF, "set-valued-checks.md")
    fs = section(svc, r"^### The sixth error")
    check("set-valued-checks: the filtered-subset section is present", bool(fs))
    check("set-valued-checks: names FILTERED-SUBSET and (scoped) as its answer",
          "FILTERED-SUBSET" in fs and affirms_claim(fs, ws(r"`\(scoped\)` is the answer")),
          "the finding or its answer is absent or negated")

    sk = read(PP, "SKILL.md")
    check("SKILL.md: the validator checklist line names GOAL-CHECK-MISSING",
          re.search(r"^- \[ \] .*validate-gate-checks\.py.*GOAL-CHECK-MISSING", sk, re.M)
          is not None, "the trunk checklist does not name it")

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
