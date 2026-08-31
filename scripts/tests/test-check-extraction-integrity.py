#!/usr/bin/env python3
"""Fixture tests for scripts/check-extraction-integrity.py.

Builds a synthetic plugin tree in a temp dir and asserts the scanner's
contract: dead relative paths, unresolved positional deixis, unresolved
section refs, the comparison/qualified exclusions that keep it honest,
allowlist suppression, --scope, --list-allowlisted, and exit codes.

The exclusion cases are the load-bearing ones. A guard that flags
"opt in below `high`" as deixis trains its readers to allowlist
everything, which is how a guard stops guarding. Stdlib only.
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "check-extraction-integrity.py")

spec = importlib.util.spec_from_file_location("integrity", SCRIPT)
integrity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integrity)

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


def codes(findings):
    return sorted(f["code"] for f in findings)


def scan(text, name="p/skills/s/references/r.md", root=None):
    """Scan one synthetic file; returns findings."""
    return integrity.scan_file(name, text, root or "/nonexistent")


def dead_path_cases():
    with tempfile.TemporaryDirectory() as root:
        ref = "p/skills/s/references/r.md"
        write(os.path.join(root, ref), "x")
        write(os.path.join(root, "p/skills/s/references/sibling.md"), "x")
        write(os.path.join(root, "p/skills/s/SKILL.md"), "x")

        # Resolves from the file's own directory -> clean
        f = integrity.scan_file(ref, "See `sibling.md` for detail.\n", root)
        check(codes(f) == [], "existing sibling path not flagged")

        f = integrity.scan_file(ref, "See `../SKILL.md` for detail.\n", root)
        check(codes(f) == [], "existing ../ path not flagged")

        # Does not resolve under any convention -> DEAD-PATH
        f = integrity.scan_file(ref, "See `../references/missing.md` for detail.\n", root)
        check(codes(f) == ["DEAD-PATH"], "unresolvable internal reference flagged")
        check(f[0]["token"] == "../references/missing.md", "DEAD-PATH token is the path")

        # Markdown link form
        f = integrity.scan_file(ref, "See [detail](./references/gone.md).\n", root)
        check(codes(f) == ["DEAD-PATH"], "markdown link to missing file flagged")

        # Absolute/external are not our business
        f = integrity.scan_file(ref, "See [x](https://example.com) and `/etc/hosts`.\n", root)
        check(codes(f) == [], "http and absolute paths not flagged")

        # A path inside a fenced command block still resolves the same way
        f = integrity.scan_file(ref, "```bash\npython3 ../scripts/missing.py\n```\n", root)
        check(codes(f) == ["DEAD-PATH"], "unresolvable path inside a fence flagged")

        # --- the corrected contract: only THIS repo's own files are in scope ---
        # Measured: treating every path-ish token as internal produced 847
        # findings on this tree, ~829 of them target-project paths. These cases
        # pin that narrowing so it cannot silently regress.
        for text, why in [
            ("Write `fastlane/metadata/android/en-US/title.txt` (<= 50 chars).\n",
             "target-project path"),
            ("Draft `docs/f-droid/<applicationId>.yml` with the hash.\n",
             "templated <placeholder> path"),
            ("|   +-- `short_description.txt`\n", "bare filename in a tree diagram"),
            ("Scans `*/agents/*.md` from the repo root.\n", "glob pattern"),
            ("See `~/.claude/skills/code-review/SKILL.md`.\n", "home-relative path"),
        ]:
            check(codes(integrity.scan_file(ref, text, root)) == [],
                  f"not flagged: {why}")

    # Plugin-rooted citation resolves against the plugin dir (DEC-009 form)
    with tempfile.TemporaryDirectory() as root:
        write(os.path.join(root, "biz/skills/plan/SKILL.md"), "x")
        write(os.path.join(root, "biz/references/plan-format.md"), "x")
        f = integrity.scan_file("biz/skills/plan/SKILL.md",
                                "Format in `references/plan-format.md`.\n", root)
        check(codes(f) == [], "plugin-rooted reference resolves from the plugin dir")
        f = integrity.scan_file("biz/skills/plan/SKILL.md",
                                "Format in `references/absent.md`.\n", root)
        check(codes(f) == ["DEAD-PATH"], "plugin-rooted reference to a missing file flagged")


def positional_deixis_cases():
    # Real deixis in a reference file -> flagged
    for text, why in [
        ("Stop when the exit criterion above is met.\n", "'criterion above'"),
        ("Execute it via the normal flow below.\n", "'flow below'"),
        ("See Context resets below, scaled up.\n", "'resets below'"),
        ("The gate rules above close this.\n", "'rules above'"),
    ]:
        check(codes(scan(text)) == ["DEIXIS-POSITIONAL"], f"deixis flagged: {why}")

    # Comparisons are not deixis -> must NOT flag
    for text, why in [
        ("A task may opt in below `high` with Review: required.\n", "below `high`"),
        ("skipped when the tier is below `standard`.\n", "below `standard`"),
        ("narrows it only if it crosses above ~5 minutes.\n", "above ~5 minutes"),
        ("one rung below the standard staged plan\n", "below the standard (tier word)"),
        ("anything above 200 changed lines\n", "above 200"),
    ]:
        check(codes(scan(text)) == [], f"comparison not flagged: {why}")

    # Trunks are checked too. An earlier cut exempted them, reasoning that
    # "above" resolves inside one file — true before an extraction and false
    # after it, leaving the guard blind at the moment it is needed. Measured:
    # 66 unchecked instances, 21 in the trunk the next stage would split.
    f = scan("Follow the escalation rules below when this fires.\n",
             name="p/skills/s/SKILL.md")
    check(codes(f) == ["DEIXIS-POSITIONAL"], "positional deixis in a trunk IS flagged")

    # The six false positives an independent evaluator found, each pinned so
    # the fix cannot silently regress.
    for text, why in [
        ("A game cannot ship without meeting every Basic-tier item below.\n"
         "| M1 | requirement | test |\n", "'item below' with rows below it"),
        ("Only build custom when no entry below fits the requirement.\n"
         "| Need | Standard | DIY |\n", "'entry below' with a table below it"),
        ("Write XML following the structure above, then generate.\n"
         "```xml\n<adaptive-icon/>\n```\n", "'structure above' with a block present"),
        ("The parse contract accepts any key (see above), so these work.\n",
         "bare '(see above)' — no noun phrase to resolve"),
    ]:
        check(codes(scan(text)) == [], f"not flagged: {why}")

    # A shell-quoted path inside a fence resolves to a real file
    with tempfile.TemporaryDirectory() as root:
        write(os.path.join(root, "p/skills/s/scripts/down.sh"), "x")
        write(os.path.join(root, "p/skills/s/SKILL.md"), "x")
        f = integrity.scan_file(
            "p/skills/s/SKILL.md",
            "```bash\ntrap 'skills/s/scripts/down.sh --mock' EXIT\n```\n", root)
        check(codes(f) == [], "shell-quoted path in a fence is stripped and resolves")


def section_ref_cases():
    # Unqualified § naming no local heading -> flagged
    f = scan("Applies the class rule — § A bug found during execution is a class.\n")
    check(codes(f) == ["DEIXIS-SECTION"], "unqualified § with no local heading flagged")

    # Same ref, heading present in this file -> clean
    f = scan("## A bug found during execution is a class\n\nSee § A bug found during execution is a class.\n")
    check(codes(f) == [], "§ resolving to a local heading not flagged")

    # Qualified by a backticked path -> the reader can follow it
    f = scan("See `../../planning-projects/references/task-fields.md` § Scope marking.\n")
    check("DEIXIS-SECTION" not in codes(f), "§ qualified by a path not flagged")

    # Qualified by the word 'trunk' -> names where it lives
    f = scan("counted (trunk, § Remediation budget), never free.\n")
    check(codes(f) == [], "§ qualified by 'trunk' not flagged")

    # A trunk's own dangling § is still a dead pointer
    f = scan("See § Light plans, rule 2 for the detail.\n", name="p/skills/s/SKILL.md")
    check(codes(f) == ["DEIXIS-SECTION"], "dangling § in a trunk flagged")

    # Qualified by a filename in BARE prose, not backticks — the reader can
    # still open it, so the finding's premise would have been false.
    f = scan("as metrics-format.md § Target linkage requires, apply the rule.\n")
    check("DEIXIS-SECTION" not in codes(f), "§ qualified by a bare filename not flagged")

    # ...but the filename must be ADJACENT to the §, not merely nearby. A
    # proximity-only window suppresses a genuinely dangling reference whenever
    # an unrelated filename happens to precede it within 70 chars.
    f = scan("After the config.yml rewrite, the § Legacy Format section was dropped.\n")
    check(codes(f) == ["DEIXIS-SECTION"],
          "an unrelated nearby filename does NOT qualify a dangling §")

    # Containment must not let a SHORT dangling ref hide inside a LONG heading
    f = scan("## Scope of the review pass\n\nThe § Scope rules moved elsewhere.\n")
    check(codes(f) == ["DEIXIS-SECTION"],
          "short dangling § not masked by a longer unrelated heading")


def allowlist_cases():
    with tempfile.TemporaryDirectory() as root:
        ref = "p/skills/s/references/r.md"
        write(os.path.join(root, ref), "The gate rules above close this.\n")
        allow = os.path.join(root, "allow.txt")

        rc = integrity.main(["--root", root, "--allowlist", allow])
        check(rc == 1, "unallowlisted finding exits 1")

        entry = "p/skills/s/references/r.md:DEIXIS-POSITIONAL:rules above"
        write(allow, f"# reason\n{entry}  # BL-039, burned down in Task 2.3\n")
        rc = integrity.main(["--root", root, "--allowlist", allow])
        check(rc == 0, "exact allowlist entry suppresses the finding")

        # Near-miss must NOT suppress — exact match only
        write(allow, "p/skills/s/references/r.md:DEIXIS-POSITIONAL:rules below\n")
        rc = integrity.main(["--root", root, "--allowlist", allow])
        check(rc == 1, "near-miss allowlist entry does not suppress")

        # A bare path is not an entry — suppression is per finding, not per file
        write(allow, "p/skills/s/references/r.md\n")
        rc = integrity.main(["--root", root, "--allowlist", allow])
        check(rc == 1, "bare path does not suppress a whole file")

    # --- the allowlist is a MULTISET, not a set -------------------------------
    # The header's contract ("allowlisting one instance cannot hide the next one
    # in the same file") was false under set membership: tokens are low-entropy,
    # so a NEW dead pointer reusing an allowlisted token vanished. Measured by an
    # evaluator: three fresh dead pointers absorbed, exit 0. These pin the fix.
    with tempfile.TemporaryDirectory() as root:
        ref = "p/skills/s/references/r.md"
        allow = os.path.join(root, "allow.txt")
        entry = "p/skills/s/references/r.md:DEIXIS-POSITIONAL:rules below"

        write(os.path.join(root, ref), "Follow the escalation rules below now.\n")
        write(allow, entry + "\n")
        check(integrity.main(["--root", root, "--allowlist", allow]) == 0,
              "one line suppresses one occurrence")

        # A SECOND, genuinely new instance of the same token must surface
        write(os.path.join(root, ref),
              "Follow the escalation rules below now.\n"
              "Apply the escalation rules below again.\n")
        check(integrity.main(["--root", root, "--allowlist", allow]) == 1,
              "a second occurrence of an allowlisted token is NOT absorbed")

        # Two lines cover two occurrences
        write(allow, entry + "\n" + entry + "\n")
        check(integrity.main(["--root", root, "--allowlist", allow]) == 0,
              "two lines suppress two occurrences")


def list_allowlisted_cases():
    with tempfile.TemporaryDirectory() as root:
        ref = "p/skills/s/references/r.md"
        write(os.path.join(root, ref), "The gate rules above close this.\n")
        allow = os.path.join(root, "allow.txt")
        entry = "p/skills/s/references/r.md:DEIXIS-POSITIONAL:rules above"
        write(allow, entry + "\n")
        out = integrity.list_allowlisted(allow)
        check(out == [entry], "--list-allowlisted returns the entries verbatim")
        check(integrity.list_allowlisted(os.path.join(root, "none.txt")) == [],
              "missing allowlist file lists nothing")


def scope_cases():
    with tempfile.TemporaryDirectory() as root:
        write(os.path.join(root, "a/skills/s/references/r.md"),
              "The gate rules above close this.\n")
        write(os.path.join(root, "b/skills/s/references/r.md"),
              "The gate rules above close this.\n")
        allow = os.path.join(root, "none.txt")

        rc = integrity.main(["--root", root, "--allowlist", allow, "--scope", "a"])
        check(rc == 1, "--scope a still sees a's finding")

        write(os.path.join(root, "a/skills/s/references/r.md"), "clean text\n")
        rc = integrity.main(["--root", root, "--allowlist", allow, "--scope", "a"])
        check(rc == 0, "--scope a ignores b's finding")
        rc = integrity.main(["--root", root, "--allowlist", allow])
        check(rc == 1, "unscoped run still sees b's finding")


def empty_sweep_cases():
    """An empty sweep must not read as a pass (BL-067).

    This case previously pinned the DEFECT: it asserted "empty tree exits 0",
    which is exactly the silent clean pass a typo'd --scope degrades to. The
    assertion is inverted here deliberately, not relaxed — the old expectation
    was the bug, recorded as a test.
    """
    with tempfile.TemporaryDirectory() as root:
        allow = os.path.join(root, "n.txt")
        rc = integrity.main(["--root", root, "--allowlist", allow])
        check(rc == 2, "empty tree exits 2, not a silent clean 0")
        files = integrity.discover(root, None)
        check(files == [], "empty tree discovers no files (count is reported, not implied)")
        rc = integrity.main(["--root", root, "--allowlist", allow, "--min-files", "0"])
        check(rc == 0, "--min-files 0 opts a legitimately empty scope back in")

    # The scenario BL-067 actually names: a scope typo over a NON-empty tree.
    # Without the floor this is the worst shape, because the tree really does
    # hold findings and the run still reports a clean pass.
    with tempfile.TemporaryDirectory() as root:
        allow = os.path.join(root, "n.txt")
        write(os.path.join(root, "a/skills/s/references/r.md"),
              "The gate rules above close this.\n")
        check(integrity.main(["--root", root, "--allowlist", allow, "--scope", "a"]) == 1,
              "the real scope sees the finding")
        check(integrity.main(["--root", root, "--allowlist", allow, "--scope", "aa"]) == 2,
              "a typo'd --scope fails loudly instead of passing clean")

    # The floor is a number, not a bare non-empty test: a scope matching FEWER
    # files than the caller expects is the same failure, one step subtler.
    with tempfile.TemporaryDirectory() as root:
        allow = os.path.join(root, "n.txt")
        write(os.path.join(root, "a/skills/s/references/r.md"), "clean\n")
        check(integrity.main(["--root", root, "--allowlist", allow]) == 0,
              "one clean file clears the default floor of 1")
        check(integrity.main(["--root", root, "--allowlist", allow, "--min-files", "5"]) == 2,
              "a floor above the discovered count fails")


def exclusion_cases():
    with tempfile.TemporaryDirectory() as root:
        write(os.path.join(root, "p/skills/s/references/r.md"), "clean\n")
        write(os.path.join(root, "p/skills/s/tests/fixtures/references/bad.md"),
              "The gate rules above close this.\n")
        rc = integrity.main(["--root", root, "--allowlist", os.path.join(root, "n.txt")])
        check(rc == 0, "tests/fixtures trees excluded from the scan")


if __name__ == "__main__":
    print("dead paths:")
    dead_path_cases()
    print("positional deixis:")
    positional_deixis_cases()
    print("section refs:")
    section_ref_cases()
    print("allowlist:")
    allowlist_cases()
    print("--list-allowlisted:")
    list_allowlisted_cases()
    print("--scope:")
    scope_cases()
    print("empty sweep:")
    empty_sweep_cases()
    print("exclusions:")
    exclusion_cases()
    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s)")
        sys.exit(1)
    print("\nall passed")
