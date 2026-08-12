#!/usr/bin/env python3
"""The hand-curated PRESERVE block survives a rebuild.

`../SKILL.md` § `rebuild` names three rules that bind whatever else changes, and
the first is that the `<!-- BEGIN PRESERVE -->` block survives **byte-for-byte**.
`references/global-formats.md` § Hard rules says the same thing operationally:
"Never delete the PRESERVE block or its sentinels … Do not silently drop
previously curated GBL items."

The script did not do that. `render_global_backlog(vd, projects)` took no
existing-file argument, never read one, and always emitted an empty sentinel
pair — so every `rebuild --write` destroyed the curated `## Cross-project items`.
Spec and script disagreed and the spec was right; found by the Stage 4 Task 4.3
determinism audit, which could not route `rebuild` to its script while it
behaved this way.

This is a DATA-LOSS regression test, so it asserts the curated bytes come back,
not merely that the sentinels are present — a check for the sentinels alone
passes against the exact bug it is meant to catch.

Stdlib only, no vault required.
"""
import importlib.util
import io
import os
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "portfolio-rebuild.py"

spec = importlib.util.spec_from_file_location("portfolio_rebuild", SCRIPT)
pr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pr)

FAILURES = []


def check(ok, msg):
    print(f"  {'ok' if ok else 'FAIL'}: {msg}")
    if not ok:
        FAILURES.append(msg)


CURATED = ("- [[obsidian-wiki]] ↔ [[coder-plugins]] — the wiki plugin's task profile\n"
           "  enables plugins by id, so a rename breaks it silently.\n"
           "- Revisit the 8-in-flight cap once the vault moves off NFS.")


def rollup(body):
    return ("# Global Backlog\n\n**Last rebuilt:** 2026-01-01\n\n---\n\n"
            "## Per-project backlogs\n\n---\n\n## Cross-project items\n\n"
            f"{pr.PRESERVE_BEGIN}\n\n{body}\n\n{pr.PRESERVE_END}\n")


def cases():
    with tempfile.TemporaryDirectory() as root:
        vd = Path(root)
        (vd / "Portfolio").mkdir()
        path = vd / "Portfolio" / "global-backlog.md"

        # The load-bearing case: curated content already on disk.
        path.write_text(rollup(CURATED))
        out = pr.render_global_backlog(vd, [], pr.preserved_region(path))
        check(CURATED in out,
              "curated PRESERVE content survives a re-render byte-for-byte")
        check(out.count(pr.PRESERVE_BEGIN) == 1 and out.count(pr.PRESERVE_END) == 1,
              "exactly one sentinel pair is emitted, not a nested duplicate")

        # Idempotence: rendering the output again must not drift or double it.
        path.write_text(out)
        again = pr.render_global_backlog(vd, [], pr.preserved_region(path))
        check(again == out, "a second rebuild over its own output is byte-identical")
        check(again.count(CURATED.splitlines()[0]) == 1,
              "the curated body is not duplicated on the second pass")

        # An empty curated block stays empty and stays well-formed.
        path.write_text(rollup(""))
        empty = pr.render_global_backlog(vd, [], pr.preserved_region(path))
        check(pr.PRESERVE_BEGIN in empty and pr.PRESERVE_END in empty,
              "an empty curated block round-trips with its sentinels intact")

        # No file yet — first run must not warn or invent content.
        missing = vd / "Portfolio" / "does-not-exist.md"
        err = io.StringIO()
        with redirect_stderr(err):
            check(pr.preserved_region(missing) == "",
                  "a first run with no existing roll-up yields an empty region")
        check(err.getvalue() == "",
              "...and does not warn — absent is not the same as damaged")

        # Sentinels missing from a NON-EMPTY file: per global-formats.md § Hard
        # rules, insert an empty block AND warn. Silence here is how curated
        # items disappear without anyone being told.
        path.write_text("# Global Backlog\n\nsomeone reformatted this by hand\n")
        err = io.StringIO()
        with redirect_stderr(err):
            region = pr.preserved_region(path)
        check(region == "", "a file with no sentinels yields an empty region")
        check("PRESERVE" in err.getvalue(),
              "...and WARNS, per the hard rule against silently dropping items")


if __name__ == "__main__":
    print("PRESERVE block survival:")
    cases()
    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")
