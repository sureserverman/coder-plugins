#!/usr/bin/env python3
"""Fixture tests for scripts/check-trunk-retention.py.

The load-bearing cases are the ones proving the sweep actually rejects. A
retention check that only ever passes is worse than none: it certifies that the
extraction kept its obligations while the trunk quietly demotes them to pointers,
which is the exact failure the token-efficiency plan exists to prevent.

So the cases that matter are: a heading deleted, a heading kept but its RULE
gone, and a marker deleted to silence the row. Stdlib only.
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "check-trunk-retention.py")

spec = importlib.util.spec_from_file_location("retention", SCRIPT)
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)

FAILURES = []


def check(cond, msg):
    if cond:
        print(f"  ok: {msg}")
    else:
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


TRUNK_OK = """---
name: t
---

# T

## Stop conditions

Stop immediately and escalate when the plan says so.

## Step 3.5 — Stage gate

A gate passes when **no Critical finding remains**.

## Phase Close-out

Pointer only: `references/close-out.md`.
"""

TABLE_OK = """# Extraction classification

### unconditional — 1 section

| bytes | retained | section | reason |
|---|---|---|---|
| 100 | 100 | Stop conditions | must bind every run, whole |

### rule+elaboration — 1 section

| bytes | retained | section | reason |
|---|---|---|---|
| 900 | 300 | Step 3.5 — Stage gate | exit criterion stays, hooks are branch-taken |

### conditional — 1 section

| bytes | retained | section | reason |
|---|---|---|---|
| 800 | 50 | Phase Close-out | reached once, at the very end of a plan |

## Retention markers

| section | must appear in the trunk |
|---|---|
| Step 3.5 — Stage gate | A gate passes when **no Critical finding remains** |

## Where the conditional material went

| moved from | now lives in |
|---|---|
| Phase Close-out | `../references/close-out.md` |
"""


def run(trunk, table):
    """check_pair against a temp tree; returns the problem list."""
    with tempfile.TemporaryDirectory() as root:
        t_rel = "p/skills/s/SKILL.md"
        c_rel = "p/skills/s/references/extraction-classification.md"
        write(os.path.join(root, t_rel), trunk)
        write(os.path.join(root, c_rel), table)
        return retention.check_pair(root, t_rel, c_rel)


def cases():
    check(run(TRUNK_OK, TABLE_OK) == [],
          "a faithful extraction passes")

    # A conditional section may leave entirely — that is what conditional means.
    gone = TRUNK_OK.replace("## Phase Close-out\n\nPointer only: "
                            "`references/close-out.md`.\n", "")
    check(run(gone, TABLE_OK) == [],
          "a conditional section leaving the trunk is not a problem")

    # An unconditional heading deleted outright.
    p = run(TRUNK_OK.replace("## Stop conditions", "## Something else"), TABLE_OK)
    check(any("MISSING-HEADING" in x and "Stop conditions" in x for x in p),
          "deleting an unconditional heading is MISSING-HEADING")

    # The heading survives; the RULE under it is replaced by a pointer. This is
    # the case set equality cannot see, and the reason this script exists.
    demoted = TRUNK_OK.replace(
        "A gate passes when **no Critical finding remains**.",
        "How a gate passes: `references/stage-gate.md`.")
    p = run(demoted, TABLE_OK)
    check(any("MISSING-RULE" in x for x in p),
          "demoting a rule to a pointer under a surviving heading is MISSING-RULE")
    check(not any("MISSING-HEADING" in x for x in p),
          "...and it is NOT reported as a missing heading (the heading is there)")

    # Silencing the row by deleting its marker must fail, not pass.
    stripped = TABLE_OK.replace(
        "| Step 3.5 — Stage gate | A gate passes when "
        "**no Critical finding remains** |\n", "")
    p = run(demoted, stripped)
    check(any("UNMARKED-SECTION" in x for x in p),
          "deleting a marker to silence a demotion is UNMARKED-SECTION")

    # A marker naming a section nobody classified is a stale row.
    extra = TABLE_OK.replace(
        "## Where the conditional material went",
        "| Ghost section | anything |\n\n## Where the conditional material went")
    check(any("names no classified section" in x for x in run(TRUNK_OK, extra)),
          "a marker for an unclassified section is reported")

    # The 2-column table further down the file must not be read as markers.
    check(not any("moved from" in x for x in run(TRUNK_OK, TABLE_OK)),
          "the 'where it went' table is not mistaken for a marker table")

    # A trunk with no classification at all.
    with tempfile.TemporaryDirectory() as root:
        write(os.path.join(root, "p/skills/s/SKILL.md"), TRUNK_OK)
        p = retention.check_pair(root, "p/skills/s/SKILL.md",
                                 "p/skills/s/references/extraction-classification.md")
    check(len(p) == 1 and "no classification" in p[0],
          "a trunk with no classification file is reported, not skipped")


def real_tree():
    """The shipped trunk must satisfy its own classification."""
    check(retention.main([]) == 0, "the real executing-plans trunk passes the sweep")


if __name__ == "__main__":
    print("check-trunk-retention fixtures:")
    cases()
    print("real tree:")
    real_tree()
    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")
