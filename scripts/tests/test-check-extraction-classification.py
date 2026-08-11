#!/usr/bin/env python3
"""Fixture tests for scripts/check-extraction-classification.py.

The load-bearing case is that this is a SET equality check, not a count check:
a table that drops one heading and invents one row has the right count and the
wrong classification, and a counting check passes it. Stdlib only.
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "check-extraction-classification.py")

spec = importlib.util.spec_from_file_location("cls", SCRIPT)
cls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cls)

FAILURES = []


def check(cond, msg):
    if cond:
        print(f"  ok: {msg}")
    else:
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


def table(rows, klass="unconditional"):
    out = [f"### {klass} — n sections", "| bytes | retained | section | reason |",
           "|---|---|---|---|"]
    for name, reason in rows:
        out.append(f"| 100 | 100 | {name} | {reason} |")
    return "\n".join(out) + "\n"


def parse_cases():
    heads = cls.trunk_headings("## Alpha\ntext\n### Beta\n#### Gamma\n##### TooDeep\n")
    check(heads == ["Alpha", "Beta", "Gamma"],
          "headings ##..#### collected, ##### ignored")

    rows = cls.table_rows(table([("Alpha", "because it binds every run")]))
    check(rows == [("Alpha", "unconditional", "because it binds every run")],
          "row carries section, class from its enclosing heading, and reason")

    # A heading inside a fence is sample content, not a section of the trunk.
    # planning-projects/SKILL.md prints a `## Decisions in force` example inside a
    # ```markdown fence to show an author what to write; a fence-blind scan reports
    # it as this skill's own section and the table then has to file a decision
    # about a code sample — a row that fails the day the example is edited.
    fenced = cls.trunk_headings(
        "## Real\ntext\n\n```markdown\n## Sample\n- not a section\n```\n\n## AlsoReal\n")
    check(fenced == ["Real", "AlsoReal"],
          "a heading inside a ``` fence is not a trunk section")

    check(cls.trunk_headings("## Real\n\n~~~\n## Tilde\n~~~\n") == ["Real"],
          "~~~ fences are honoured too")

    # An unterminated fence swallows the rest of the file. That is the correct
    # reading of the markdown, and reporting fewer headings is the safe direction:
    # it fails set equality loudly rather than certifying a section nobody classified.
    check(cls.trunk_headings("## Real\n```\n## Swallowed\n") == ["Real"],
          "an unclosed fence hides what follows, and fails loudly downstream")


def set_equality_cases():
    with tempfile.TemporaryDirectory() as root:
        t = os.path.join(root, "trunk.md")
        c = os.path.join(root, "cls.md")

        def run():
            return cls.check_pair(root, "trunk.md", "cls.md")

        open(t, "w").write("## Alpha\nx\n## Beta\ny\n")
        open(c, "w").write(table([("Alpha", "reason enough here"),
                                  ("Beta", "reason enough here")]))
        check(run() == [], "matching sets pass")

        # The end-to-end version of the fence case: a trunk whose only extra
        # heading is inside a fence needs NO row for it, and gets no complaint.
        open(t, "w").write("## Alpha\nx\n\n```markdown\n## Sample\n```\n\n## Beta\ny\n")
        open(c, "w").write(table([("Alpha", "reason enough here"),
                                  ("Beta", "reason enough here")]))
        check(run() == [], "a fenced heading demands no classification row")

        # And the converse: filing a row for one is caught, so the table cannot
        # quietly classify a code sample either.
        open(c, "w").write(table([("Alpha", "reason enough here"),
                                  ("Beta", "reason enough here"),
                                  ("Sample", "reason enough here")]))
        check(any("no such heading" in x and "Sample" in x for x in run()),
              "a row naming a fenced heading is rejected")

        # Heading present, row absent
        open(c, "w").write(table([("Alpha", "reason enough here")]))
        p = run()
        check(len(p) == 1 and "not classified" in p[0], "unclassified heading is caught")

        # THE case: one dropped, one invented — counts match, sets do not
        open(c, "w").write(table([("Alpha", "reason enough here"),
                                  ("Ghost", "reason enough here")]))
        p = run()
        check(len(p) == 2, "drop-one/invent-one is caught (a count check would pass)")
        check(any("not classified" in x for x in p) and
              any("no such heading" in x for x in p),
              "both directions reported, not just one")

        # A row with no usable reason
        open(c, "w").write(table([("Alpha", "reason enough here"), ("Beta", "x")]))
        check(any("no usable reason" in x for x in run()), "empty reason is caught")

        # A class that is not one of the three
        open(c, "w").write(table([("Alpha", "reason enough here"),
                                  ("Beta", "reason enough here")], klass="whatever"))
        check(any("no valid class" in x for x in run()),
              "an unrecognised class heading yields no rows, so its headings read unclassified")

        # Duplicate heading text defeats set equality — must be reported
        open(t, "w").write("## Alpha\nx\n## Alpha\ny\n")
        open(c, "w").write(table([("Alpha", "reason enough here")]))
        check(any("duplicate heading" in x for x in run()), "duplicate heading text is caught")

        # A missing classification file is a failure, not a skip
        os.remove(c)
        check(any("missing" in x for x in run()), "absent classification file fails")


def exit_code_cases():
    with tempfile.TemporaryDirectory() as root:
        check(cls.main(["--root", root]) == 0,
              "a tree with no classified trunks exits 0 and reports the count")


if __name__ == "__main__":
    print("parsing:")
    parse_cases()
    print("set equality:")
    set_equality_cases()
    print("exit codes:")
    exit_code_cases()
    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s)")
        sys.exit(1)
    print("\nall passed")
