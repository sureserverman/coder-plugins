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
