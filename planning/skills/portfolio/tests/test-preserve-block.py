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
from contextlib import redirect_stderr, redirect_stdout
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

        # A non-UTF-8 byte must neither crash the run NOR be silently dropped.
        #
        # This assertion previously required the read to SURVIVE via
        # errors="ignore", and a review showed it certified a property the system
        # did not have: the read survived, the run still crashed later at
        # write_if_changed's own bare read, and meanwhile ignoring the bad bytes
        # returned a curated body with characters permanently gone and an empty
        # stderr — then wrote it back. On the one path whose contract is
        # byte-for-byte, "drop what I cannot read" is the corruption, not the fix.
        path.write_bytes(rollup(CURATED).encode() + b"\xff\xfe stray latin-1\n")
        err = io.StringIO()
        with redirect_stderr(err):
            region = pr.preserved_region(path)
        check(region is None,
              "an undecodable file REFUSES the rewrite rather than dropping bytes")
        check("UTF-8" in err.getvalue(),
              "...and names the decode failure, rather than failing silently")


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


def main_level_cases():
    """The REFUSAL must hold through `main()`, not only in `preserved_region`.

    This is the same "green function, regressed call site" gap that forced
    `preserved` to become a required positional — recurring one level up, and
    found the same way. A review mutated the call site to
    `render_global_backlog(vd, projects, preserved or "")`: the signature
    assertion still passed, the suite stayed green, and an ambiguous
    global-backlog.md was rewritten with an EMPTY block *while the script printed
    "REFUSING to rewrite it. Nothing was written."* The warning became an active
    lie. `preserved or ""` is not a contrived edit; it is what someone writes when
    a None surprises them.

    So this drives the real entry point against a fake vault and asserts the bytes
    on disk, which is the only thing that cannot be satisfied by a warning.
    """
    import yaml
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        vault, repo = rootp / "vault", rootp / "repo"
        (vault / "Portfolio" / "area" / "proj").mkdir(parents=True)
        (repo / ".claude").mkdir(parents=True)
        gb = vault / "Portfolio" / "global-backlog.md"

        # Ambiguous by duplicate pairs — the recovery-path shape.
        original = (rollup("") + "\n## Recovered by hand\n\n"
                    + f"{pr.PRESERVE_BEGIN}\n\n{CURATED}\n\n{pr.PRESERVE_END}\n")
        gb.write_text(original)

        cfg = rootp / "config.yaml"
        cfg.write_text(yaml.safe_dump({"version": 1, "vault_dir": str(vault)}))
        reg = rootp / "registry.yaml"
        reg.write_text(yaml.safe_dump({"projects": [
            {"path": str(repo), "name": "proj", "area": "area", "enabled": True}]}))

        old_cfg, old_reg, old_argv = pr.CONFIG, pr.REGISTRY, sys.argv
        pr.CONFIG, pr.REGISTRY = cfg, reg
        sys.argv = ["portfolio-rebuild.py", "--write"]
        try:
            with redirect_stderr(io.StringIO()) as err, redirect_stdout(io.StringIO()) as out:
                try:
                    pr.main()
                except SystemExit:
                    pass
            stderr, stdout = err.getvalue(), out.getvalue()
        finally:
            pr.CONFIG, pr.REGISTRY, sys.argv = old_cfg, old_reg, old_argv

        check(gb.read_text() == original,
              "main() --write leaves an ambiguous global-backlog.md BYTE-IDENTICAL")
        check("REFUSING" in stderr, "...and says so on stderr")
        check("SKIPPED" in stdout,
              "...and the status line reports a refusal, not a bare False")
        # The refusal must be SCOPED. Halting the whole rebuild would be a
        # different bug with the same symptom.
        check((vault / "Portfolio" / "global-maturity.md").exists(),
              "...while the other roll-ups are still written — the refusal is scoped")


if __name__ == "__main__":
    print("PRESERVE block survival:")
    cases()
    print("call-site contract:")
    call_site_cases()
    print("main()-level refusal:")
    main_level_cases()
    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")
