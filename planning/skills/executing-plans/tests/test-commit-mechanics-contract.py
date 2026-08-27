#!/usr/bin/env python3
"""Structure suite for the commit-mechanics contract — run directly (CI convention):
    python3 planning/skills/executing-plans/tests/test-commit-mechanics-contract.py

A PROSE contract, not behavior. The suite asserts that the skill text states the
execution-discipline rules Stage 1 of the session-mined-flaws plan added — the
commit mechanics for a plan that lives outside the repo, the turn discipline that
keeps an announcement from standing in for the work, and the single form a report
uses to ask the user for something. It cannot verify that an executor obeys any of
them — stated plainly, because a structure suite that implies behavioral coverage
is the falsehood class `honest-gates` exists to catch. The file keeps its original
name so the plan's Task 1.1 `Test:` field still resolves.

What it pins (Task 1.1):
  1. The trunk NAMES the vault-resident-plan case — that a plan can live outside
     the repo it plans, which is the portfolio convention, not an edge case.
  2. It mandates editing the plan at an ABSOLUTE PATH and forbids `cd`-ing to the
     plan's directory to do it.
  3. It mandates running the commit FROM THE REPO ROOT.
  4. It names the observed failure (`fatal: not a git repository`), so the rule
     reads as a report of something that happened rather than as a style note.
  5. `references/task-execution.md` carries the elaboration, so the reference the
     trunk points at is not a dead end.

Why the rule needs to exist at all: rule 7 mandates committing "the flipped
`Status: [x]`" in the same commit as the work, which silently assumes the plan
file is inside the repo. With a vault-resident plan it is not, and the observed
executor behaviour was to chain a directory change into the plan's directory
before the git command — ~20-25 failed commits across four sessions.

What it pins (Task 1.2 — turn discipline):
  6. § Run to completion forbids ending a turn on a stage or task announcement,
     and requires the tool call that opens the next stage/task in the SAME turn
     as the sentence announcing it, or instead of it.
  7. It names the observed shape — a turn whose last words are "Starting Stage
     N." with no tool call — so the rule is evidenced rather than stylistic.

What it pins (Task 1.3 — the ACTION NEEDED callout):
  8. Both report-owning references — stage-gate.md and close-out.md — define an
     `ACTION NEEDED:` block with NUMBERED options.
  9. Both forbid a report that carries one from also announcing that it is
     proceeding.
 10. Both state that a report carries at most ONE such block.
     Checked as a SET across the two files, because a gate report and a close-out
     report are two instances of one defect class and a check naming only one of
     them cannot fail on the other.

     **Coverage limit, stated because overstating it is the defect this suite
     exists to catch.** The plan's `Test:` field calls for "a single isolated"
     form. What is checked is that each reference *states* the one-block rule —
     a prose contract has no report to count blocks in. A report that violates
     the rule at runtime is not something any assertion here can see.

The three tasks share one suite because they share one failure mode: a rule the
executor reads and then does not apply at the moment of pressure. Rule text is
the only artifact any of them can be checked against.

Read-only. Exit 0 when every promise holds, 1 otherwise.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / "SKILL.md"
TASK_EXECUTION = HERE.parent / "references" / "task-execution.md"

FAILURES = []
RAN = []


def check(name, ok, detail=""):
    RAN.append(name)
    if not ok:
        FAILURES.append(f"{name}: {detail}" if detail else name)


def flat(s):
    """Collapse whitespace so a matcher is not defeated by a line wrap.

    The trunk is hard-wrapped at ~95 columns, so any phrase this suite looks for
    may carry a newline plus indentation in the middle of it. Matching the raw
    text makes every assertion depend on where the paragraph happened to wrap —
    it reports "the rule is missing" for a rule that is present, which is the one
    failure mode a prose contract must not have. The sibling suite
    test-gate-remediation-contract.py normalizes for the same reason.
    """
    return re.sub(r"\s+", " ", s)


def slice_between(text, start, end, label):
    """Return the span between two anchors, or the whole text if either is absent.

    Falling back to the whole text is deliberate: a missing anchor is reported by
    its own assertion, and a slice that silently became empty would make every
    assertion using it fail for the wrong stated reason.
    """
    i = text.find(start)
    if i < 0:
        return text, False
    j = text.find(end, i + len(start))
    if j < 0:
        return text[i:], False
    return text[i:j], True


def main():
    text = flat(SKILL.read_text(encoding="utf-8"))

    # The rules must land where the executor is when it needs them: inside the
    # Red-Green loop, at the commit rule. A correct rule stated in a section the
    # executor has already passed is the "buried decision point" failure wearing a
    # different hat.
    loop, loop_anchored = slice_between(
        text, "### Step 3.3 — Red-Green loop", "### Step 3.4", "Step 3.3")
    check("Step 3.3's anchors both resolve", loop_anchored,
          "the Red-Green loop section could not be sliced — its heading or "
          "Step 3.4's heading moved, and every assertion below read the whole file")

    # (1) The vault-resident case is NAMED, not left to be inferred from "the repo".
    check("Step 3.3 names the plan-outside-the-repo case",
          re.search(r"outside the repo it plans", loop) is not None,
          "rule 7 still assumes the plan file is inside the repo being committed to; "
          "the vault-resident case (the portfolio convention) is not named")
    check("Step 3.3 names the vault as where that happens",
          "vault" in loop.lower(),
          "the case is described abstractly but the vault — the place it actually "
          "happens, every time — is not named")

    # (2) Absolute-path edit, and no directory change to perform it.
    check("Step 3.3 mandates editing the plan at an absolute path",
          re.search(r"absolute path", loop) is not None,
          "no rule tells the executor to address the plan file by absolute path")
    nocd = re.search(r"[Nn]ever `cd`|do not `cd`|without `cd`", loop)
    check("Step 3.3 forbids cd-ing to the plan's directory",
          nocd is not None,
          "nothing forbids changing directory into the plan's own directory, which "
          "is the shape that produced the failed commits")

    # (3) The commit runs from the repo root.
    check("Step 3.3 mandates committing from the repo root",
          re.search(r"from the repo root", loop) is not None,
          "no rule says where the git command runs; 'commit after each green task' "
          "does not say from where, which is the whole defect")

    # (4) The observed failure is named, so the rule is evidenced rather than stylistic.
    check("Step 3.3 names the observed failure",
          "not a git repository" in loop,
          "the error the rule prevents (`fatal: not a git repository`) is not named, "
          "so a future editor cannot tell what the rule is protecting")

    # (5) The reference the trunk points at actually carries the elaboration.
    ref = flat(TASK_EXECUTION.read_text(encoding="utf-8"))
    check("task-execution.md elaborates the commit mechanics",
          "outside the repo it plans" in ref or "vault-resident" in ref,
          f"{TASK_EXECUTION.name} does not discuss the plan-outside-the-repo case, so "
          "the trunk's pointer leads nowhere")
    check("task-execution.md states what happens to the Status flip",
          re.search(r"Status: \[x\]|`Status:` flip|Status flip", ref) is not None,
          f"{TASK_EXECUTION.name} does not say what becomes of the Status flip when "
          "the plan file is not in the repo — the question rule 7 raises and does not answer")

    # ---- Task 1.2: turn discipline ----------------------------------------
    # Scoped to § Run to completion rather than to the whole trunk: the rule
    # belongs with the other rules about not handing the turn back, and a
    # trunk-wide match would pass on a sentence buried anywhere at all.
    rtc, rtc_anchored = slice_between(
        text, "## Run to completion", "## The plan is the authorization", "Run to completion")
    check("§ Run to completion's anchors both resolve", rtc_anchored,
          "the section could not be sliced — its heading or the next section's heading "
          "moved, and the turn-discipline assertions read the whole file instead")

    check("§ Run to completion forbids ending a turn on an announcement",
          re.search(r"end a turn on an announcement|end a turn on a (stage|task)", rtc)
          is not None,
          "nothing forbids a turn whose last words announce work it never started")
    check("§ Run to completion requires the opening tool call in the same turn",
          re.search(r"same turn", rtc) is not None,
          "the rule does not say WHEN the announced work must start, so 'Starting "
          "Stage 3.' followed by nothing still satisfies it")
    check("§ Run to completion allows the announcement to be dropped entirely",
          re.search(r"instead of it|or instead", rtc) is not None,
          "the rule mandates an announcement-plus-call pairing without saying the "
          "announcement is optional, which reads as requiring the announcement")
    check("§ Run to completion names the observed shape",
          re.search(r"Starting Stage", rtc) is not None,
          "the literal shape the rule prevents is not quoted, so a future editor "
          "cannot tell what the rule is protecting against")

    # ---- Task 1.3: the ACTION NEEDED callout -------------------------------
    # Checked as a SET over both report-owning references rather than one at a
    # time: the defect is that a report buries what it wants from the user, and
    # a gate report and a close-out report are two instances of one class. A
    # check naming only one of them cannot fail on the other.
    report_sites = {
        "stage-gate.md": HERE.parent / "references" / "stage-gate.md",
        "close-out.md": HERE.parent / "references" / "close-out.md",
    }
    missing_form, missing_numbered, missing_exclusive = [], [], []
    missing_single = []
    for label, path in report_sites.items():
        body = flat(path.read_text(encoding="utf-8"))
        if "ACTION NEEDED" not in body:
            # Recorded against all three lists, not skipped with `continue`: a
            # site with no callout at all has no numbered options and no
            # exclusivity rule either, and letting those two assertions go quiet
            # would report two passes for a site that carries nothing.
            missing_form.append(label)
            missing_numbered.append(label)
            missing_exclusive.append(label)
            missing_single.append(label)
            continue
        # The options are numbered, so the user answers with a number rather
        # than by reconstructing the choice from prose.
        if re.search(r"ACTION NEEDED.{0,600}?1\.\s", body) is None:
            missing_numbered.append(label)
        # And the report may not both ask and proceed. The phrasing is pinned
        # loosely (any of the proceeding/next-stage forms) because what must not
        # happen is the PAIRING, not one particular sentence.
        if re.search(
                r"(does not also|never also|not).{0,80}(proceed|proceeding)"
                r"|(proceed|proceeding).{0,120}(and|while).{0,60}ACTION NEEDED",
                body) is None:
            missing_exclusive.append(label)
        # "Single isolated" is the plan's Test: wording. What a PROSE contract can
        # check is that the rule is stated — a report is not an artifact this suite
        # can count blocks in. Stated here rather than left implied, because a
        # docstring claiming more coverage than the assertions carry is the exact
        # honest-gates falsehood this suite exists to catch.
        if re.search(r"[Oo]ne block per report|[Oo]ne block, last", body) is None:
            missing_single.append(label)

    check("both report references define the ACTION NEEDED form",
          not missing_form,
          "no ACTION NEEDED callout at: " + ", ".join(missing_form))
    check("the ACTION NEEDED form carries numbered options",
          not missing_numbered,
          "no numbered options under the callout at: "
          + ", ".join(missing_numbered))
    check("a report may not both ask and announce it is proceeding",
          not missing_exclusive,
          "nothing forbids pairing an unresolved decision with 'proceeding to the "
          "next stage' in one report at: " + ", ".join(missing_exclusive))
    check("both references mandate ONE such block per report",
          not missing_single,
          "the form is defined but nothing says a report carries at most one of them, "
          "so three asks in three paragraphs still satisfies it at: "
          + ", ".join(missing_single))

    print(f"assertions run ({len(RAN)}):")
    for name in RAN:
        print(f"  - {name}")
    if FAILURES:
        print("\nFAILURES:", file=sys.stderr)
        for f in FAILURES:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print("\nOK — commit-mechanics contract present in skill text (prose contract only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
