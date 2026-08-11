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

A gate passes when **no Critical finding remains**. Remediation budget: 2 rounds.

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
| Stop conditions | Stop immediately and escalate |
| Step 3.5 — Stage gate | A gate passes when **no Critical finding remains** |
| Step 3.5 — Stage gate | Remediation budget: 2 rounds |

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

    # Silencing the row by deleting its markers must fail, not pass. Since markers
    # became list-valued, silencing means deleting them ALL — dropping one of two
    # leaves the section marked, and the surviving marker keeps doing its job (the
    # "dropping a section's SECOND obligation" case below asserts that directly).
    one_left = TABLE_OK.replace(
        "| Step 3.5 — Stage gate | A gate passes when "
        "**no Critical finding remains** |\n", "")
    p = run(demoted, one_left)
    check(not any("UNMARKED-SECTION" in x for x in p),
          "dropping one of two markers does not unmark the section")

    stripped = one_left.replace(
        "| Step 3.5 — Stage gate | Remediation budget: 2 rounds |\n", "")
    p = run(demoted, stripped)
    check(any("UNMARKED-SECTION" in x for x in p),
          "deleting ALL of a section's markers to silence a demotion is "
          "UNMARKED-SECTION")

    # A marker naming a section nobody classified is a stale row.
    extra = TABLE_OK.replace(
        "## Where the conditional material went",
        "| Ghost section | anything |\n\n## Where the conditional material went")
    check(any("names no classified section" in x for x in run(TRUNK_OK, extra)),
          "a marker for an unclassified section is reported")

    # The 2-column table further down the file must not be read as markers.
    check(not any("moved from" in x for x in run(TRUNK_OK, TABLE_OK)),
          "the 'where it went' table is not mistaken for a marker table")

    # An UNCONDITIONAL section gutted to a stub while its heading survives. This is
    # the class the module docstring opens by naming, and it was uncovered until the
    # Stage 2 gate: `unconditional` rows were exempt from the marker requirement, so
    # the only check on them was heading presence — exactly the check that cannot see
    # this. Two reviewers found it independently.
    gutted = TRUNK_OK.replace(
        "Stop immediately and escalate when the plan says so.",
        "See `references/stop-conditions.md`.")
    p = run(gutted, TABLE_OK)
    check(any("MISSING-RULE" in x and "Stop conditions" in x for x in p),
          "gutting an UNCONDITIONAL section to a pointer is MISSING-RULE")

    # An unconditional row with no marker cannot silently opt out of the check.
    unmarked = TABLE_OK.replace(
        "| Stop conditions | Stop immediately and escalate |\n", "")
    p = run(gutted, unmarked)
    check(any("UNMARKED-SECTION" in x and "Stop conditions" in x for x in p),
          "an unconditional row with no marker is UNMARKED-SECTION, not a free pass")

    # SECOND marker on a multi-obligation section. One marker per section is
    # instance-shaped: a section retaining eight obligations pinned by one string
    # lets seven be demoted with the sweep still green.
    dropped_second = TRUNK_OK.replace(" Remediation budget: 2 rounds.", "")
    p = run(dropped_second, TABLE_OK)
    check(any("MISSING-RULE" in x and "Remediation budget" in x for x in p),
          "dropping a section's SECOND obligation is caught (markers are list-valued)")
    check(not any("no Critical finding remains" in x for x in p),
          "...while its first marker still passes — the two are checked independently")

    # A trunk with no classification at all.
    with tempfile.TemporaryDirectory() as root:
        write(os.path.join(root, "p/skills/s/SKILL.md"), TRUNK_OK)
        p = retention.check_pair(root, "p/skills/s/SKILL.md",
                                 "p/skills/s/references/extraction-classification.md")
    check(len(p) == 1 and "no classification" in p[0],
          "a trunk with no classification file is reported, not skipped")


def scoping_cases():
    """A marker must hold in the section that CLAIMS it, not anywhere in the trunk.

    Matching against the whole file made four live rows unfalsifiable, found by an
    adversarial review rather than by this suite. The worst shape: `Staged rollout`
    pinned `--include-maturity`, a string that also occurs in `Default flow`, so
    the entire Staged rollout section could be gutted with the guard still green.
    """
    # The rule moves OUT of its section but stays in the trunk. Whole-file
    # matching passes this; section-scoped matching must not.
    moved = TRUNK_OK.replace(
        "A gate passes when **no Critical finding remains**. Remediation budget: 2 rounds.",
        "See `references/stage-gate.md`.").replace(
        "Stop immediately and escalate when the plan says so.",
        "Stop immediately and escalate when the plan says so.\n\n"
        "A gate passes when **no Critical finding remains**. Remediation budget: 2 rounds.")
    p = run(moved, TABLE_OK)
    check(any("MISSING-RULE" in x and "Step 3.5" in x for x in p),
          "a rule relocated to ANOTHER section is MISSING-RULE, not a pass")
    check(any("elsewhere in the trunk" in x for x in p),
          "and the message says the rule is elsewhere, so the fix is obvious")

    # A marker satisfied by the section's own HEADING pins nothing: MISSING-HEADING
    # already guarantees the heading. This was a live row (`| Subcommands | Subcommands |`).
    self_pin = TABLE_OK.replace(
        "| Stop conditions | Stop immediately and escalate |",
        "| Stop conditions | Stop conditions |")
    p = run(TRUNK_OK, self_pin)
    check(any("MISSING-RULE" in x and "Stop conditions" in x for x in p),
          "a marker satisfied only by its own heading does not count as a rule")

    # THE GUTTING PROBE, as a committed test rather than a one-off: replace each
    # binding section's body with a pointer and require the guard to reject it.
    for section, body in (
            ("Stop conditions", "Stop immediately and escalate when the plan says so."),
            ("Step 3.5 — Stage gate",
             "A gate passes when **no Critical finding remains**. "
             "Remediation budget: 2 rounds.")):
        gutted = TRUNK_OK.replace(body, "See `references/x.md`.")
        p = run(gutted, TABLE_OK)
        check(any("MISSING-RULE" in x and section in x for x in p),
              f"gutting {section!r} to a pointer is caught")


def malformed_row_cases():
    """A non-numeric bytes cell must be REPORTED, never silently skipped.

    The two guards disagreed about what a row is: this one required
    `cells[0].isdigit()`, check-extraction-classification.py did not. So editing a
    bytes cell to `n/a` and deleting the row's markers dropped a section out of
    this sweep entirely with BOTH guards green — the only trace a population count
    nothing asserted.
    """
    bad = TABLE_OK.replace("| 100 | 100 | Stop conditions |",
                           "| n/a | 100 | Stop conditions |")
    p = run(TRUNK_OK, bad)
    check(any("MALFORMED-ROW" in x and "Stop conditions" in x for x in p),
          "a non-numeric bytes cell is reported, not skipped")

    # And the shared parser must agree with the other guard about the row set.
    rows = retention._sections.class_rows(TABLE_OK)
    check(len(rows) == 3 and not any(bad_flag for *_, bad_flag in rows),
          "the shared row parser sees all three well-formed rows")


def real_tree():
    """The shipped trunks must satisfy their own classifications."""
    check(retention.main([]) == 0, "the real trunks pass the sweep")

    # The probe the Stage 2 handoff told Stage 3 to run, now permanent: gut every
    # binding section of every shipped trunk and require ALL of them to be caught.
    # A survivor is a row whose marker pins nothing.
    survivors = []
    for trunk_rel, table_rel in retention.PAIRS:
        root = retention.REPO_ROOT
        trunk = open(os.path.join(root, trunk_rel), encoding="utf-8").read()
        table = open(os.path.join(root, table_rel), encoding="utf-8").read()
        klasses, _ = retention.classified(table)
        bodies = retention._sections.section_bodies(trunk)
        for section, klass in klasses.items():
            if klass not in retention.BINDING_CLASSES:
                continue
            body = bodies.get(section)
            if not body or not body.strip():
                continue
            gutted = trunk.replace(body, "\nSee `references/x.md`.\n", 1)
            if gutted == trunk:
                continue
            with tempfile.TemporaryDirectory() as tmp:
                write(os.path.join(tmp, trunk_rel), gutted)
                write(os.path.join(tmp, table_rel), table)
                if not retention.check_pair(tmp, trunk_rel, table_rel):
                    survivors.append(f"{trunk_rel}::{section}")
    check(not survivors,
          f"every binding section of every shipped trunk fails when gutted "
          f"({len(survivors)} survivor(s): {survivors[:4]})")


if __name__ == "__main__":
    print("check-trunk-retention fixtures:")
    cases()
    print("marker scoping:")
    scoping_cases()
    print("malformed rows:")
    malformed_row_cases()
    print("real tree:")
    real_tree()
    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")
