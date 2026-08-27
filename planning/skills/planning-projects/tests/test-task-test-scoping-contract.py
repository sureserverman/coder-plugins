#!/usr/bin/env python3
"""Structure suite for the task-level `Test:` scoping contract — run directly:
    python3 planning/skills/planning-projects/tests/test-task-test-scoping-contract.py

A PROSE contract, not behavior. It asserts that the authoring text no longer
claims a task-level `Test:` field is scoped automatically, and that it states the
authoring rule that replaced the claim. It cannot verify that an author obeys the
rule — that is Task 3.2's validator, and saying so here is the honest-gates
disclosure a structure suite owes.

What it pins (Task 3.1):
  1. The falsified assumption is gone from the WHOLE TREE, in EVERY wording the
     sweep found — the "by-construction" claim, the "already task-scope" one, and
     the table cell's "already targeted". (The first is not spelled out anywhere
     in this file, including here: the plan's Stage 3 gate greps that literal
     phrase across `planning/`, so a suite quoting it would redden the gate it
     was written to serve. The matcher below is assembled from fragments for the
     same reason.)

     The third wording was added after a Tier-1 review: the first draft swept the
     tree for one wording and checked the other only inside a regex-extracted
     table cell, so a third file restating "already targeted" would have passed
     while this suite's docstring claimed tree-wide coverage. A check whose
     stated scope exceeds its real one is the failure this repo tracks hardest,
     and it had reproduced it inside the assertion written to prevent it.

     The plan's own `Test:` field was that literal grep, and it cannot fail: the
     phrase is hard-wrapped across a newline at its only site, so it returns
     nothing whether or not the claim is present. Normalizing whitespace is what
     makes the sweep able to fail; widening from `planning/` to the whole tree is
     DEC-013.
  2. `test-scope-tiers.md` states the replacement rule — on a project whose suite
     is expensive, a task `Test:` is path- or suite-scoped, or carries an explicit
     `full-suite: accepted`.
  3. It names the token `full-suite: accepted` verbatim, because the flag is what
     Task 3.2's validator matches on: a rule naming no exact token leaves the
     validator free to invent one, and then the rule and the check disagree.
  4. It names the measured failure the retraction rests on (a task-level `Test:`
     running ~3.5 h against a 3132-test collection), so the reversal reads as a
     report of something that happened rather than as a change of mind.
  5. The task-scope table row no longer asserts the field is "already targeted".
     The row is where an executor looks the tier up, so a corrected § Plan-authoring
     declaration with an uncorrected row leaves the claim standing at the site that
     is actually read — the connective-prose class Stages 1-2 kept finding, in its
     table form.
  6. The authoring checklist carries the obligation as an item, naming the same
     token, so the rule is checked at the moment a plan is authored rather than
     stated only in the reference a hurried author may not open.
  7. The item names its gating tier (authoring-time), per DEC-017: a new mandate
     states what gates it, or it is an unbounded cost.
  8. BOTH checklists carry it — Standard and Light. Found while implementing, not
     while planning: the Light list's own closing paragraph says it is "shorter
     rather than softer" because every item it drops is a field the Light format
     does not have. A task `Test:` is a field it does have, so a rule present in
     one list and absent from the other contradicts that paragraph and leaves a
     Light plan on an expensive-suite project with exactly the defect this task
     retracts. DEC-013 - the class, not the instance.

Read-only. Exit 0 when every promise holds, 1 otherwise.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TIERS = HERE.parent / "references" / "test-scope-tiers.md"
CHECKLIST = HERE.parent / "references" / "authoring-checklist.md"

FAILURES = []
RAN = []

# Built from parts so this suite is not itself a hit for the sweep in check 1 —
# and skipped by path anyway, belt and braces.
# Both wordings, swept tree-wide. The second alternation is context-bound rather
# than bare: "already targeted" is an ordinary English phrase, and a matcher that
# flagged every use of it would be a false-positive generator rather than a guard.
# What is falsified is the claim made ABOUT A TASK FIELD, so the context is the
# window in which that subject appears.
FALSIFIED = re.compile(
    r"task-scope\s+by\s+" + "construction"
    r"|already\s+task" + r"-scope"
    r"|(?:task(?:-level)?|`Test:`)[^.]{0,140}?already\s+targeted"
    r"|already\s+targeted[^.]{0,140}?(?:task(?:-level)?|`Test:`)",
    re.I,
)

SKIP_DIRS = (".git", "__pycache__", "node_modules")


def check(name, ok, detail=""):
    RAN.append(name)
    if not ok:
        FAILURES.append(f"{name}: {detail}" if detail else name)


def flat(s):
    """Collapse whitespace and blockquote markers so a matcher is not defeated by
    a line wrap. Every file here is hard-wrapped, and the phrase this suite must
    be able to find spans a newline at its only real site — which is exactly why
    the plan's literal grep could not fail."""
    return re.sub(r"\s+", " ", re.sub(r"(?m)^\s*>\s?", "", s))


def slice_between(text, start, end):
    """Return the span between two anchors, and whether both were found."""
    i = text.find(start)
    if i < 0:
        return text, False
    j = text.find(end, i + len(start))
    if j < 0:
        return text[i:], False
    return text[i:j], True


def sweep_tree():
    hits = []
    for p in sorted(REPO.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.resolve() == Path(__file__).resolve():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if FALSIFIED.search(flat(text)):
            hits.append(str(p.relative_to(REPO)))
    return hits


def main():
    tiers = flat(TIERS.read_text(encoding="utf-8"))
    checklist = flat(CHECKLIST.read_text(encoding="utf-8"))

    hits = sweep_tree()
    check("the falsified 'scoped by construction' claim is gone tree-wide",
          not hits,
          "still asserted at: " + ", ".join(hits))

    check("test-scope-tiers.md states the expensive-suite scoping rule for task `Test:`",
          re.search(r"expensive[^.]{0,200}?task[^.]{0,120}?`?Test:?`?[^.]{0,200}?scoped"
                    r"|task[^.]{0,120}?`Test:`[^.]{0,300}?scoped[^.]{0,200}?expensive",
                    tiers, re.I) is not None,
          "no rule ties a task `Test:` on an expensive-suite project to being scoped")

    check("test-scope-tiers.md names the `full-suite: accepted` token verbatim",
          "full-suite: accepted" in tiers,
          "the escape hatch has no exact spelling, so Task 3.2's validator would "
          "have to invent one")

    check("the retraction cites the measured run it rests on",
          re.search(r"3132|3\.5\s*h|200\+?\s*min", tiers, re.I) is not None,
          "no evidence is cited, so the reversal reads as a change of mind")

    row = re.search(r"\|\s*\*\*task-scope\*\*\s*\|(.{0,600}?)\|\s*\*\*fix-scope\*\*", tiers)
    check("the task-scope table row exists and drops the 'already targeted' claim",
          row is not None and not re.search(r"already\s+targeted", row.group(1), re.I),
          "the row still asserts the field is already targeted"
          if row else "the task-scope row could not be located")

    check("the authoring checklist carries the obligation as an item",
          re.search(r"-\s*\[\s*\][^|]{0,400}?full-suite:\s*accepted", checklist) is not None,
          "the rule is stated only in the reference; an author following the "
          "checklist would never meet it")

    item = re.search(r"-\s*\[\s*\][^\[]{0,600}?full-suite:\s*accepted[^\[]{0,400}", checklist)
    check("the checklist item names its gating tier (authoring-time), per DEC-017",
          item is not None and re.search(r"authoring[- ]time", item.group(0), re.I),
          "the new mandate does not say what gates it")

    # Checked as a SET across the two lists. A Light plan has task `Test:` fields
    # and can be authored for an expensive-suite project, so a rule that reaches
    # only the Standard list is instance-shaped in the way this repo rejects
    # everywhere else.
    light, found = slice_between(checklist, "## Checklist - Light plans",
                                 "Why the Light list is shorter")
    if not found:
        light, found = slice_between(checklist, "## Checklist \u2014 Light plans",
                                     "Why the Light list is shorter")
    check("the Light checklist carries the same obligation",
          found and "full-suite: accepted" in light,
          "the Light list could not be located" if not found else
          "a Light plan on an expensive-suite project keeps the defect this task "
          "retracts, and the list's own 'shorter rather than softer' paragraph "
          "says that is not a legitimate omission")

    print(f"assertions run ({len(RAN)}):")
    for name in RAN:
        print(f"  - {name}")
    if FAILURES:
        print("\nFAILURES:", file=sys.stderr)
        for f in FAILURES:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print("\nOK — task-`Test:` scoping contract present in authoring text "
          "(prose contract only; enforcement is Task 3.2's validator)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
