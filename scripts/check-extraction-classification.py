#!/usr/bin/env python3
"""Every trunk heading is classified, and every classified row is a real heading.

An extraction classification decides what may leave a trunk. A heading missing
from the table is a section nobody decided about, and it will be moved or kept by
whoever happens to be editing — which is exactly the ungoverned drift the
classification exists to replace. A row naming no real heading is a decision
about nothing, usually a heading that was renamed after the table was written.

Both directions matter, so this is a SET EQUALITY check, not a count comparison:
two mistakes that cancel (one heading dropped, one row invented) leave the counts
identical and the classification wrong.

Pairs a trunk with its `references/extraction-classification.md`. Read-only.
Exit 0 when the sets match and every row carries a class and a reason, 1 otherwise.
"""
import argparse
import importlib.util
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Trunks that must carry a classification, and where it lives.
PAIRS = [
    ("planning/skills/executing-plans/SKILL.md",
     "planning/skills/executing-plans/references/extraction-classification.md"),
    ("planning/skills/planning-projects/SKILL.md",
     "planning/skills/planning-projects/references/extraction-classification.md"),
    ("planning/skills/portfolio/SKILL.md",
     "planning/skills/portfolio/references/extraction-classification.md"),
]

VALID_CLASSES = ("unconditional", "rule+elaboration", "conditional")

# Fence-aware heading extraction, shared with check-trunk-retention.py so the two
# guards cannot disagree about what counts as a section. See that module's
# docstring for why a `^#{2,4} ` regex alone is wrong here.
_spec = importlib.util.spec_from_file_location(
    "_skill_sections", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "_skill_sections.py"))
_sections = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sections)


def trunk_headings(text):
    return _sections.headings(text)


def table_rows(text):
    """(section, klass, reason) per table row, keyed off the section column.

    Rows live under `### <class> — ...` headings; the class comes from the
    enclosing heading rather than a column, so a row cannot disagree with the
    section it is filed under.
    """
    rows, klass = [], None
    for line in text.split("\n"):
        m = re.match(r"^### (\S+)", line)
        if m and m.group(1) in VALID_CLASSES:
            klass = m.group(1)
            continue
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4 or cells[0] in ("bytes",):
            continue
        rows.append((cells[2], klass, cells[3]))
    return rows


def check_pair(root, trunk_rel, table_rel):
    problems = []
    trunk_path = os.path.join(root, trunk_rel)
    table_path = os.path.join(root, table_rel)
    if not os.path.exists(table_path):
        return [f"{table_rel}: missing — {trunk_rel} has no classification"]

    heads = trunk_headings(open(trunk_path, encoding="utf-8").read())
    rows = table_rows(open(table_path, encoding="utf-8").read())

    in_table = {r[0] for r in rows}
    in_trunk = set(heads)
    for missing in sorted(in_trunk - in_table):
        problems.append(f"{table_rel}: heading not classified — {missing!r}")
    for extra in sorted(in_table - in_trunk):
        problems.append(f"{table_rel}: row names no such heading — {extra!r}")

    if len(heads) != len(in_trunk):
        dupes = [h for h in in_trunk if heads.count(h) > 1]
        problems.append(f"{trunk_rel}: duplicate heading text {sorted(dupes)!r} — "
                        "set equality cannot distinguish them")

    for section, klass, reason in rows:
        if klass not in VALID_CLASSES:
            problems.append(f"{table_rel}: {section!r} has no valid class")
        if not reason or len(reason) < 12:
            problems.append(f"{table_rel}: {section!r} has no usable reason")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(prog="check-extraction-classification")
    ap.add_argument("--root", default=REPO_ROOT)
    args = ap.parse_args(argv)

    pairs = [(t, c) for t, c in PAIRS
             if os.path.exists(os.path.join(args.root, t))]
    problems = []
    for trunk_rel, table_rel in pairs:
        problems += check_pair(args.root, trunk_rel, table_rel)

    # honest-gates: state the population examined, so an empty sweep cannot read
    # as a pass over something.
    print(f"{len(pairs)} classified trunk(s) checked; {len(problems)} problem(s).")
    for p in problems:
        print(f"  {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
