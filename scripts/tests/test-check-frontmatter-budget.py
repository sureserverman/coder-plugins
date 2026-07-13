#!/usr/bin/env python3
"""Fixture tests for scripts/check-frontmatter-budget.py.

Builds a synthetic plugin tree in a temp dir and asserts the scanner's
contract: budget comparison, folded-YAML parsing, missing frontmatter,
tests/fixtures exclusion, allowlist handling, and exit codes. Stdlib only.
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "check-frontmatter-budget.py")

spec = importlib.util.spec_from_file_location("budget", SCRIPT)
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)

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


def fm(desc, folded=False):
    if folded:
        body = "description: >\n  " + desc.replace(" ", " ")
        return f"---\n{body}\nother: x\n---\n\n# body\n"
    return f"---\ndescription: {desc}\nother: x\n---\n\n# body\n"


def extract_cases():
    # Plain single-line
    check(budget.extract_description(fm("hello world")) == "hello world",
          "plain single-line description parsed")
    # Folded block collapses to one line
    long = "a" * 50 + " " + "b" * 50
    got = budget.extract_description(fm(long, folded=True))
    check(got == long, "folded (>) block collapsed to single line")
    # Missing frontmatter
    check(budget.extract_description("# just a body\n") is None,
          "no frontmatter -> None")
    # Frontmatter without description
    check(budget.extract_description("---\nname: x\n---\n") is None,
          "frontmatter without description -> None")


def scan_cases():
    with tempfile.TemporaryDirectory() as root:
        # under budget
        write(os.path.join(root, "p1/skills/a/SKILL.md"), fm("x" * 100))
        # exactly at budget (300) -> not a violation
        write(os.path.join(root, "p1/skills/b/SKILL.md"), fm("y" * 300))
        # over budget skill
        write(os.path.join(root, "p1/skills/c/SKILL.md"), fm("z" * 301))
        # over budget agent
        write(os.path.join(root, "p2/agents/agt.md"), fm("w" * 400))
        # over budget command
        write(os.path.join(root, "p2/commands/cmd.md"), fm("v" * 350))
        # excluded: under tests/
        write(os.path.join(root, "p2/skills/x/tests/SKILL.md"), fm("t" * 500))
        # excluded: under fixtures/
        write(os.path.join(root, "p2/skills/x/fixtures/deep/SKILL.md"), fm("f" * 500))

        allow = os.path.join(root, "allow.txt")
        with open(allow, "w") as fh:
            fh.write("# reasons\np2/commands/cmd.md  # legacy\n")

        violations, allowed = budget.scan(root, 300, budget.load_allowlist(allow))
        vpaths = {v["path"] for v in violations}
        apaths = {a["path"] for a in allowed}

        check("p1/skills/b/SKILL.md" not in vpaths, "exactly-300 is not a violation")
        check("p1/skills/a/SKILL.md" not in vpaths, "under-budget is not a violation")
        check("p1/skills/c/SKILL.md" in vpaths, "over-budget skill flagged")
        check("p2/agents/agt.md" in vpaths, "over-budget agent flagged")
        check(not any("tests" in p for p in vpaths), "tests/ path excluded")
        check(not any("fixtures" in p for p in vpaths), "fixtures/ path excluded")
        check("p2/commands/cmd.md" in apaths, "allowlisted path reported as allowed")
        check("p2/commands/cmd.md" not in vpaths, "allowlisted path not a violation")
        check(all("kind" in v and "plugin" in v and "chars" in v for v in violations),
              "violation records carry kind/plugin/chars")
        vc = next(v for v in violations if v["path"] == "p1/skills/c/SKILL.md")
        check(vc["chars"] == 301 and vc["plugin"] == "p1" and vc["kind"] == "skill",
              "violation record fields correct")


def exit_code_cases():
    with tempfile.TemporaryDirectory() as root:
        write(os.path.join(root, "p/skills/a/SKILL.md"), fm("x" * 100))
        rc = budget.main(["--root", root, "--max", "300", "--allowlist", os.path.join(root, "none.txt")])
        check(rc == 0, "clean tree exits 0")
        write(os.path.join(root, "p/skills/b/SKILL.md"), fm("x" * 500))
        rc = budget.main(["--root", root, "--max", "300", "--allowlist", os.path.join(root, "none.txt")])
        check(rc == 1, "tree with violation exits 1")


if __name__ == "__main__":
    print("extract_description:")
    extract_cases()
    print("scan:")
    scan_cases()
    print("exit codes:")
    exit_code_cases()
    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s)")
        sys.exit(1)
    print("\nall passed")
