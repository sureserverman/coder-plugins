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

        # --- The two cases the FIRST fix still lost data on. ---
        #
        # A: the recovery path this tool's own warning prescribes. Told the
        # sentinels were missing, an operator pastes the recovered section back —
        # sentinels included — below the generated empty pair. Taking the first
        # pair returns the EMPTY one and destroys the recovery, on the run where
        # they have already lost it once. The vault is not git-tracked.
        path.write_text(rollup("") + "\n## Recovered by hand\n\n"
                        + f"{pr.PRESERVE_BEGIN}\n\n{CURATED}\n\n{pr.PRESERVE_END}\n")
        err = io.StringIO()
        with redirect_stderr(err):
            region = pr.preserved_region(path)
        check(region is None,
              "duplicate sentinel pairs REFUSE the rewrite (None), never return ''")
        check("2 BEGIN" in err.getvalue() and "REFUSING" in err.getvalue(),
              "...and the warning names the counts and says nothing was written")

        # B: a curated item quoting the end sentinel — exactly the kind of note
        # that documents this mechanism — truncated the region and dropped
        # everything after it.
        path.write_text(rollup(f"- GBL-001 the sentinel {pr.PRESERVE_END} appears here\n"
                               "- GBL-002 second item"))
        err = io.StringIO()
        with redirect_stderr(err):
            region = pr.preserved_region(path)
        check(region is None,
              "an end sentinel inside the curated body REFUSES rather than truncating")

        # Sentinels present but reversed.
        path.write_text("# Global Backlog\n\n## Cross-project items\n\n"
                        f"{pr.PRESERVE_END}\n\n{CURATED}\n\n{pr.PRESERVE_BEGIN}\n")
        err = io.StringIO()
        with redirect_stderr(err):
            region = pr.preserved_region(path)
        check(region is None, "out-of-order sentinels REFUSE the rewrite")

        # A non-UTF-8 byte must not abort the whole rebuild. Every other vault
        # read in the script uses errors="ignore"; this one did not, and the
        # traceback landed AFTER the sidecar pass had written to every repo.
        path.write_bytes(rollup(CURATED).encode() + b"\xff\xfe stray latin-1\n")
        try:
            region = pr.preserved_region(path)
            check(CURATED in region, "a non-UTF-8 byte does not abort the read")
        except UnicodeDecodeError:
            check(False, "a non-UTF-8 byte does not abort the read")


def call_site_cases():
    """The bug had two halves; the guard must cover both.

    The original defect was `render_global_backlog` ignoring existing content AND
    `main()` not passing it. A test that drives the composition directly stays
    green when only the call site regresses — mutation-probed by a review, which
    reverted `main()` to `render_global_backlog(vd, projects)` and watched the
    suite pass. `preserved` is now a REQUIRED positional, so that edit is a
    TypeError rather than a silent revert. This asserts the signature, because the
    signature is what makes the call site checkable.
    """
    import inspect
    sig = inspect.signature(pr.render_global_backlog)
    p = sig.parameters.get("preserved")
    check(p is not None and p.default is inspect.Parameter.empty,
          "render_global_backlog takes `preserved` with NO default, so dropping it "
          "at the call site fails loudly instead of silently restoring the bug")
    try:
        pr.render_global_backlog(Path("/nonexistent"), [])
        check(False, "calling without `preserved` raises TypeError")
    except TypeError:
        check(True, "calling without `preserved` raises TypeError")


if __name__ == "__main__":
    print("PRESERVE block survival:")
    cases()
    print("call-site contract:")
    call_site_cases()
    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")
