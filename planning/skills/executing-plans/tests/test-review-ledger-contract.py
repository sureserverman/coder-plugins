#!/usr/bin/env python3
"""Structure suite for the review-ledger close-out contract — run directly (CI convention):
    python3 planning/skills/executing-plans/tests/test-review-ledger-contract.py

These are PROSE contracts, not behavior. The suite asserts that the skill text
states the rules a master close-out must follow when it reconciles the review
ledger; it cannot and does not verify that a close-out obeys them. The ledger
itself lives in gate-report prose that no script reads (DEC-022), so what IS
mechanically checkable is that the rule is stated where it is consumed.

What it pins (BL-093 + the report-line half of BL-094):
  1. master-plans.md step 5 reconciles the review ledger plan-wide — for each
     sub-plan, which tiers ran, over which diff, and a count against what the
     declared tier owed — in the literal `reviews: <n> of <owed>` form, and the
     paragraph sits BEFORE the `**Completed:**` line instruction. The incident:
     under `review-scope: high`, the gate evaluator ran for sub-plan 1 and never
     again, and every per-gate report was individually honest — the failure is
     one level up, which is why this is a close-out rule and not a validator.
  2. close-out.md step 9's "Reviews that ran" bullet points a master plan at that
     per-sub-plan reconciliation, in the same form.
  3. stage-gate.md § "The gate report's review line" says every evidence line
     names its substrate (host / emulator / container / target device) and CITES
     honest-gates § Reporting for what that changes rather than restating the
     BLOCKED rule — the one negative check here, since the requirement's subject
     is an absence.

Deliberately small — one assertion per rule. These catch DELETION of a rule,
which is the failure that actually happens; they do not pretend to catch every
rewording.
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
REFS = os.path.join(SKILL_DIR, "references")
MASTER = os.path.join(REFS, "master-plans.md")
CLOSEOUT = os.path.join(REFS, "close-out.md")
STAGEGATE = os.path.join(REFS, "stage-gate.md")
HELPER = os.path.join(HERE, "test-gate-remediation-contract.py")


def _load_helper():
    spec = importlib.util.spec_from_file_location("_gate_contract", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_helper = _load_helper()
affirms_claim = _helper.affirms_claim

FAILED = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f" — {detail}"))
    if not ok:
        FAILED.append(name)


def ws(pattern):
    """A literal phrase as a wrap-tolerant pattern: every space may be any whitespace run.
    The references are hard-wrapped, so a pinned phrase can break at any word; a pattern
    that guesses the break point is a test that fails on true prose after a reflow."""
    return re.sub(r" ", r"\\s+", pattern)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def section(text, start_pat, end_pat):
    """Slice between two anchors; '' when the start is missing."""
    m = re.search(start_pat, text, re.M)
    if not m:
        return ""
    rest = text[m.start():]
    e = re.search(end_pat, rest[1:], re.M)
    return rest[: e.start() + 1] if e else rest


def main():
    master = read(MASTER)
    closeout = read(CLOSEOUT)
    stagegate = read(STAGEGATE)

    # --- 1. master-plans.md step 5 ---------------------------------------------------
    step5 = section(master, r"^5\. \*\*Master close-out", r"^(6\.|## )")
    check("master step 5 located", bool(step5), "no '5. **Master close-out' step")

    check("master step 5: reconciles the review ledger across sub-plans",
          affirms_claim(step5, ws(r"reconciles the review ledger")),
          "no non-negated 'reconciles the review ledger' clause")
    check("master step 5: names tiers ran / diff range / count against what the tier owed",
          affirms_claim(step5, ws(r"which review tiers ran"))
          and affirms_claim(step5, ws(r"over which diff range"))
          and affirms_claim(step5, ws(r"count against what"))
          and re.search(ws(r"declared tier owed"), step5) is not None,
          "missing one of: which review tiers ran / over which diff range / "
          "count against what … declared tier owed")
    check("master step 5: literal form `reviews: <n> of <owed>`",
          "`reviews: <n> of <owed>`" in step5,
          "literal `reviews: <n> of <owed>` absent")
    check("master step 5: one line per sub-plan, then the total",
          re.search(ws(r"one line per sub-plan, then the total"), step5) is not None,
          "'one line per sub-plan, then the total' absent")
    check("master step 5: the incident is stated (evaluator ran for sub-plan 1 and never again)",
          re.search(ws(r"sub-plan 1 and never again"), step5) is not None
          and re.search(ws(r"one level up"), step5) is not None,
          "incident clause ('sub-plan 1 and never again' … 'one level up') absent")
    check("master step 5: stated as a close-out rule, not a validator (DEC-022)",
          re.search(ws(r"close-out rule, not a validator"), step5) is not None
          and "DEC-022" in step5,
          "'close-out rule, not a validator' + DEC-022 absent")

    # Step 5 opens with the ordered procedure ("run X, run Y, then append `**Completed:**`"),
    # and the detail paragraphs follow it. So the placement that matters is the FIRST
    # non-negated mention of the ledger in that procedure landing before the append
    # instruction — a ledger named only after "append **Completed:**" is a sum taken too late.
    first = next((m for m in re.finditer(ws(r"review ledger"), step5, re.I)
                  if affirms_claim(step5[max(0, m.start() - 80):m.end() + 80], ws(r"review ledger"))),
                 None)
    ledger_pos = first.start() if first else -1
    completed_pos = step5.find("`**Completed:** YYYY-MM-DD — sub-plans:")
    check("master step 5: ledger reconciliation is ordered BEFORE the **Completed:** append",
          ledger_pos != -1 and completed_pos != -1 and ledger_pos < completed_pos,
          f"ledger at {ledger_pos}, Completed instruction at {completed_pos}")

    # --- 2. close-out.md step 9 review bullet ------------------------------------------
    step9 = section(closeout, r"^9\. Report to the user", r"^(10\.|## )")
    bullet = section(step9, r"- Reviews that ran:", r"^\s+- ")
    check("close-out step 9 review bullet located", bool(bullet),
          "no 'Reviews that ran' bullet in step 9")
    check("close-out step 9: master plan → per-sub-plan reconciliation of master-plans.md step 5",
          affirms_claim(bullet, ws(r"per-sub-plan reconciliation"))
          and re.search(ws(r"master-plans\.md.{0,20}step 5"), bullet, re.S) is not None,
          "no 'per-sub-plan reconciliation' pointing at master-plans.md step 5")
    check("close-out step 9: literal form `reviews: <n> of <owed>`",
          "`reviews: <n> of <owed>`" in bullet,
          "literal `reviews: <n> of <owed>` absent from the bullet")

    # --- 3. stage-gate.md § The gate report's review line -------------------------------
    review_line = section(stagegate, r"^## The gate report's review line", r"^## ")
    check("stage-gate review-line section located", bool(review_line))
    check("stage-gate: each evidence line names its substrate",
          affirms_claim(review_line, ws(r"evidence\*\* line[^.]{0,40}names the \*\*substrate")),
          "no non-negated 'each **evidence** line … names the **substrate**' clause")
    check("stage-gate: the four substrates are listed",
          re.search(ws(r"host, emulator, container, or target device"), review_line) is not None,
          "'host, emulator, container, or target device' absent")
    check("stage-gate: cites honest-gates/SKILL.md § Reporting",
          re.search(r"`\.\./\.\./honest-gates/SKILL\.md`\s*§\s*Reporting", review_line) is not None,
          "citation `../../honest-gates/SKILL.md` § Reporting absent")
    # Negative check — the requirement's subject is an absence: the BLOCKED rule is
    # cited, not restated, so a second copy here would be the drift this pins against.
    check("stage-gate: does NOT restate 'BLOCKED, not green'",
          re.search(ws(r"BLOCKED, not green"), review_line) is None,
          "the BLOCKED rule is restated here instead of cited")
    check("stage-gate: example block carries an `evidence:` line naming substrates",
          re.search(r"^evidence: .*— host.*— container.*— target device", review_line, re.M)
          is not None,
          "no `evidence: … — host … — container … — target device` example line")

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
