#!/usr/bin/env python3
"""Structure suite for the proof-by-tool contract — run directly (CI convention):
    python3 planning/skills/executing-plans/tests/test-proof-contract.py

A PROSE contract, not behavior. It asserts that the skill text routes a task's
proof through `prove-claim.py` and positions the record audit at the stage gate.
It cannot verify that an executor obeys either — stated plainly, because a
structure suite that implies behavioral coverage is the falsehood class
`honest-gates` exists to catch. The tools' behavior is pinned by their own
suites (test-prove-claim.py, test-plan-flip-audit.py) and the battery.

Every prose requirement is pinned with the shared clause screening
(test-gate-remediation-contract.py's `affirms_claim`, DEC-008), so a sentence that
names the tool only to opt out of it ("you need not run prove-claim.py claim")
does not satisfy the check.

What it pins (Task 2.1 — executing-plans):
  1. Rule 4a records the proof with `prove-claim.py claim`, for the first claim and
     every claim marked `(red if …)`, and stages `git add proof/` with the commit.
  2. Rule 4a no longer asks for the hand-written mutation sentence.
  3. Rule 4a routes a requirement through `prove-claim.py req` or
     `prove-claim.py deviation`, and the device-only case to a deviation.
  4. Step 3.5 runs `plan-flip-audit.py … --repo` at every stage gate, and a
     blocking finding fails the gate.
"""
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1]
EP = SKILLS / "executing-plans" / "SKILL.md"


def _load_helper():
    spec = importlib.util.spec_from_file_location(
        "_gate_contract", HERE / "test-gate-remediation-contract.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_helper = _load_helper()
affirms_claim = _helper.affirms_claim
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'ok' if ok else 'FAIL'}: {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


def flat(s):
    return re.sub(r"\s+", " ", s)


def section(text, start, end, label):
    m = re.search(start, text)
    if not m:
        check(f"{label}: section start found", False, start)
        return ""
    e = re.search(end, text[m.end():])
    if not e:
        check(f"{label}: section end found", False, end)
        return ""
    return flat(text[m.start(): m.end() + e.start()])


def main():
    print("executing-plans — rule 4a and the stage gate use the proof tools:")
    ep = EP.read_text()
    r4a = section(ep, r"4a\. \*\*Prove it", r"\n5\. \*\*Flip the task", "rule 4a")
    check("rule 4a records the proof with `prove-claim.py claim`",
          affirms_claim(r4a, r"prove-claim\.py claim"))
    check("rule 4a names the claim set: the first claim and each `(red if …)` claim",
          affirms_claim(r4a, r"first claim") and "(red if" in r4a)
    check("rule 4a stages the records with the task commit (`git add proof/`)",
          affirms_claim(r4a, r"git add proof/"))
    check("rule 4a no longer asks for a hand-written mutation sentence",
          not re.search(r"record the mutation and count in the commit", r4a, re.I))
    check("rule 4a routes a checkable requirement to `prove-claim.py req`",
          affirms_claim(r4a, r"prove-claim\.py req"))
    check("rule 4a routes an uncheckable one, and the device-only case, to a deviation",
          affirms_claim(r4a, r"prove-claim\.py deviation") and re.search(r"device", r4a))
    gate = section(ep, r"### Step 3\.5", r"\n## Context resets", "Step 3.5")
    check("Step 3.5 runs `plan-flip-audit.py … --repo` at the stage gate",
          affirms_claim(gate, r"plan-flip-audit\.py[^.;]{0,60}--repo"))
    check("Step 3.5: a blocking audit finding fails the gate",
          affirms_claim(gate, r"blocking[^.;]{0,40}fails the gate"))

    print()
    if FAILED:
        print(f"FAIL: {len(FAILED)} check(s) failed")
        for n in FAILED:
            print(f"  - {n}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
