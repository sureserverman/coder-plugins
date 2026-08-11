#!/usr/bin/env python3
"""An extraction kept every obligation it promised to keep.

`check-extraction-classification.py` proves the classification and the trunk
describe the same set of headings. It cannot prove the trunk still carries the
RULES those headings stand for: a section reduced to `## Stop conditions` plus a
pointer satisfies set equality perfectly and has lost the obligation.

That gap is the whole failure mode the token-efficiency plan was written to
avoid — a `references/` file is a definition site the executor may never open,
so an unconditional rule moved out of the trunk stops binding while every
structural check stays green. This script closes it in two directions:

  MISSING-HEADING   a section classified `unconditional` or `rule+elaboration`
                    is not in the trunk at all.
  MISSING-RULE      the section is there, but the sentence its classification
                    row promised to keep is not. This catches the demotion a
                    heading check cannot see.
  UNMARKED-SECTION  a binding row carries no retention marker, so nothing pins
                    what "the rule stayed" means for it. Set equality against the
                    marker table is deliberate: without it, a row could be
                    silenced by deleting its marker rather than by keeping its
                    rule. Both binding classes are covered — `unconditional` rows
                    need markers most, being the ones that may never move at all.

`conditional` sections are exempt by construction — they are the ones that were
supposed to leave, and their retained pointer is checked by the DEAD-PATH half of
check-extraction-integrity.py instead.

Read-only. Exit 0 when every promise holds, 1 otherwise.
"""
import argparse
import collections
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Same pairing as check-extraction-classification.py. Kept as its own list rather
# than imported because these two checks answer different questions and a trunk
# may sensibly gain one before the other.
PAIRS = [
    ("planning/skills/executing-plans/SKILL.md",
     "planning/skills/executing-plans/references/extraction-classification.md"),
]

HEADING_RE = re.compile(r"^#{2,4} (.+)$", re.M)
VALID_CLASSES = ("unconditional", "rule+elaboration", "conditional")
# Sections that must keep a named rule. `conditional` is excluded on purpose.
BINDING_CLASSES = ("unconditional", "rule+elaboration")


def trunk_headings(text):
    return {h.strip() for h in HEADING_RE.findall(text)}


def _rows(text, want_cells):
    """Table rows with exactly `want_cells` columns, as stripped cell lists."""
    out = []
    for line in text.split("\n"):
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == want_cells:
            out.append(cells)
    return out


def classified(text):
    """{section: class} from the 4-column classification tables."""
    out, klass = {}, None
    for line in text.split("\n"):
        m = re.match(r"^### (\S+)", line)
        if m and m.group(1) in VALID_CLASSES:
            klass = m.group(1)
            continue
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 4 and cells[0].isdigit():
            out[cells[2]] = klass
    return out


def markers(text):
    """{section: [required substrings]} from the `## Retention markers` table.

    Scoped to that section so the 2-column "where the conditional material went"
    table cannot be mistaken for a marker table — they have the same shape and
    only their position distinguishes them.

    LIST-valued, because one marker per section is instance-shaped. `Step 3.5 —
    Stage gate` retains eight distinct obligations; pinned by a single string,
    seven of them could be demoted to pointers with this sweep still green —
    which is the defect class this repo's gate rules exist to reject, reproduced
    inside the guard meant to enforce them. A dict keyed by section silently kept
    only the last row for a repeated section, so the table could not express what
    the rule required.
    """
    out = collections.defaultdict(list)
    if "## Retention markers" not in text:
        return out
    tail = text.split("## Retention markers", 1)[1].split("\n## ", 1)[0]
    for cells in _rows(tail, 2):
        if cells[0] != "section":
            out[cells[0]].append(cells[1])
    return out


def check_pair(root, trunk_rel, table_rel):
    problems = []
    trunk_path = os.path.join(root, trunk_rel)
    table_path = os.path.join(root, table_rel)
    if not os.path.exists(table_path):
        return [f"{table_rel}: missing — {trunk_rel} has no classification"]

    with open(trunk_path, encoding="utf-8") as fh:
        trunk = fh.read()
    with open(table_path, encoding="utf-8") as fh:
        table = fh.read()

    heads = trunk_headings(trunk)
    klasses = classified(table)
    marks = markers(table)

    binding = {s for s, k in klasses.items() if k in BINDING_CLASSES}
    for section in sorted(binding):
        if section not in heads:
            problems.append(
                f"{trunk_rel}: MISSING-HEADING — {section!r} is classified "
                f"{klasses[section]!r} and must stay in the trunk")

    # EVERY binding section needs at least one marker, and every marker needs a row.
    #
    # `unconditional` rows were exempt in the first cut, on the reasoning that they
    # may never move so heading presence is enough. That is backwards, and an
    # independent evaluator and a Tier-2 review reached it separately at the Stage 2
    # gate: those rows carry the STRONGEST guarantee in the table, and heading
    # presence is precisely the check that cannot see a section gutted to a stub —
    # the demotion this script's own docstring opens by promising to catch. The guard
    # was blind on the class it calls most dangerous.
    for section in sorted(binding - set(marks)):
        problems.append(
            f"{table_rel}: UNMARKED-SECTION — {section!r} is {klasses[section]!r} "
            "but names no retention marker")
    for section in sorted(set(marks) - set(klasses)):
        problems.append(
            f"{table_rel}: marker names no classified section — {section!r}")

    for section in sorted(marks):
        for needle in marks[section]:
            if not needle:
                problems.append(f"{table_rel}: {section!r} has an empty marker")
                continue
            if needle not in trunk:
                problems.append(
                    f"{trunk_rel}: MISSING-RULE — {section!r} promised to keep "
                    f"{needle!r} in the trunk and it is not there")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(prog="check-trunk-retention")
    ap.add_argument("--root", default=REPO_ROOT)
    args = ap.parse_args(argv)

    pairs = [(t, c) for t, c in PAIRS
             if os.path.exists(os.path.join(args.root, t))]
    problems, checked = [], 0
    for trunk_rel, table_rel in pairs:
        problems += check_pair(args.root, trunk_rel, table_rel)
        table_path = os.path.join(args.root, table_rel)
        if os.path.exists(table_path):
            with open(table_path, encoding="utf-8") as fh:
                table = fh.read()
            checked += len({s for s, k in classified(table).items()
                            if k in BINDING_CLASSES})

    # honest-gates: name the population swept, so a table that lost its rows
    # cannot report a pass over nothing.
    print(f"{len(pairs)} trunk(s), {checked} binding section(s) swept; "
          f"{len(problems)} problem(s).")
    for p in problems:
        print(f"  {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
