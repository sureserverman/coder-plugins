#!/usr/bin/env python3
"""Every vault-writing `portfolio-*.py` leaves an unchanged vault untouched.

The vault is NFS-backed Obsidian and is NOT git-tracked. A write that changes
nothing is therefore not free: it churns the sync layer, can manufacture
conflict copies, and destroys the "nothing moved" signal an operator reads off
mtimes. `../SKILL.md` § Remember states the contract outright — "Re-running with
no upstream changes produces zero writes."

`portfolio-integrate.py` did not honour it. Both roll-ups it renders embed
`**Last rebuilt:** {TODAY}`, and `main()` persisted them with a bare
`.write_text()`, so EVERY run rewrote both files — and on a day boundary the
bytes changed too. The bug is invisible to a same-day double-run, which is
exactly how the 2026-05-23 close-out in tests/manual.md recorded it as
"byte-identical": both runs saw the same TODAY. So these cases simulate a date
change between the runs, because a same-date probe passes against the bug.

The claim is class-wide, not one-script-wide (DEC-013), so this file also pins
the two scripts that legitimately do NOT route through `write_if_changed`:

  * `portfolio-unify.py` APPENDS to a curated register — a changed-check on
    `existing + new` would compare a strictly longer string and always fire.
    Its guard sits one level up, in the dedup that leaves nothing to append.
  * `portfolio-migrate.py` performs a ONE-TIME move, guarded structurally by
    TWO independent refusals — an already-emptied repo docs/ has nothing to
    migrate, and an already-populated vault home is refused — and its two
    in-place rewriters carry their own equality checks. Both are exercised
    below, the second only because docs/ is deliberately repopulated: it sits
    behind the first, so a plain re-run never reaches it.

Each of those is a justification only because the case below proves it. A
justification with no test is an assertion, not a guard.

Every case runs against a throwaway vault and a throwaway registry; nothing here
reads or writes the real vault — see fake_env(), which refuses to proceed if the
resolved vault escapes the temp tree.

Stdlib + PyYAML only, no pytest. Run:
  python3 planning/skills/portfolio/tests/test-vault-write-idempotency.py
"""
from __future__ import annotations

import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
FIXTURES = HERE / "fixtures" / "plan-parser"

FAILURES: list[str] = []


def check(ok, msg):
    print(f"  {'ok' if ok else 'FAIL'}: {msg}")
    if not ok:
        FAILURES.append(msg)


def load(name):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pi = load("portfolio-integrate")
pu = load("portfolio-unify")
pm = load("portfolio-migrate")


# A distinctive frozen mtime, far from "now", so "this file was rewritten" is a
# positive observation rather than an inference from clock resolution: any write
# — even one producing identical bytes — moves it to the present.
MARK = 1_000_000_000_000_000_000


def freeze(*paths):
    for p in paths:
        os.utime(p, ns=(MARK, MARK))


def untouched(p: Path) -> bool:
    return p.stat().st_mtime_ns == MARK


@contextmanager
def fake_env(mod, vault: Path, registry: Path, argv):
    """Point a script's CONFIG/REGISTRY/argv at a throwaway tree, then restore.

    The scripts resolve the vault through `vault_dir()` reading the module-level
    CONFIG path, so redirecting CONFIG is what keeps a test off /mnt/vault.
    Asserting that here rather than trusting it: a test that silently ran against
    the real vault would be a destructive bug wearing a green tick.
    """
    cfg = vault.parent / f"{mod.__name__}-config.yaml"
    cfg.write_text(yaml.safe_dump({"version": 1, "vault_dir": str(vault)}))
    old = (mod.CONFIG, mod.REGISTRY, sys.argv)
    mod.CONFIG, mod.REGISTRY, sys.argv = cfg, registry, list(argv)
    try:
        resolved = mod.vault_dir()
        assert resolved == vault, f"vault_dir() escaped the fixture: {resolved}"
        yield
    finally:
        mod.CONFIG, mod.REGISTRY, sys.argv = old


def run_main(mod, vault, registry, argv):
    out, err = io.StringIO(), io.StringIO()
    with fake_env(mod, vault, registry, argv):
        with redirect_stdout(out), redirect_stderr(err):
            try:
                mod.main()
            except SystemExit:
                pass
    return out.getvalue(), err.getvalue()


def write_registry(path: Path, vault: Path, projects) -> Path:
    path.write_text(yaml.safe_dump({"projects": projects}))
    return path


def integration_md(project, depends=(), impacts=()):
    fm = {"project": project}
    if depends:
        fm["depends_on"] = [{"target": f"[[{t}]]", "why": w} for t, w in depends]
    if impacts:
        fm["impacts"] = [{"target": f"[[{t}]]", "why": w} for t, w in impacts]
    return f"---\n{yaml.safe_dump(fm, sort_keys=False)}---\n\n# integration\n"


# --------------------------------------------------------------------------
def generated_stamp_case():
    """`write_if_changed` treats a bare `Generated:` line-2 stamp as a timestamp.

    BL-074's own subject, and the half that had no mutant: dropping the second `re.sub`
    from `strip_ts` left the entire harness green. `global-business.md` comes from
    business-rollup.py, a separately versioned plugin that stamps `Generated:` instead of
    `**Last rebuilt:**`, so it was the one roll-up still rewriting itself on every date
    change — exactly the churn the stage set out to stop, invisible to a same-day run.
    """
    pr = load("portfolio-rebuild")
    with tempfile.TemporaryDirectory() as root:
        f = Path(root) / "global-business.md"
        day1 = "# Global Business\nGenerated: 2026-01-01\n\nbody unchanged\n"
        day2 = "# Global Business\nGenerated: 2026-06-30\n\nbody unchanged\n"
        f.write_text(day1)
        freeze(f)
        pr.write_if_changed(f, day2)
        check(untouched(f) and f.read_text() == day1,
              "a `Generated:` stamp change alone rewrites nothing — the second half of "
              "strip_ts is what makes global-business.md idempotent across days")

        changed = "# Global Business\nGenerated: 2026-06-30\n\nbody CHANGED\n"
        pr.write_if_changed(f, changed)
        check(f.read_text() == changed,
              "and a real content change still writes — the normalisation must not "
              "swallow the diff it exists to detect")

        # count=1 is load-bearing: a `Generated:` in a project's own content further down
        # is content, not a header stamp, and must still register as a change.
        f.write_text("# G\nGenerated: 2026-01-01\n\nrow\nGenerated: 2026-01-01\n")
        pr.write_if_changed(f, "# G\nGenerated: 2026-06-30\n\nrow\nGenerated: 2026-06-30\n")
        check("row\nGenerated: 2026-06-30" in f.read_text(),
              "a second `Generated:` in the body is content, not a stamp — count=1 keeps "
              "the normalisation to the header region")


def io_vs_decode_case():
    """An I/O failure and a decode failure are different facts with different answers.

    BL-100. `read_utf8` reported ANY `OSError` — EACCES, EIO, NFS ESTALE — as "not readable
    as UTF-8", naming the one cause it probably was not, and `write_if_changed` then
    truncated the file. On an NFS-backed vault the transient I/O fault is the likely cause,
    and a file we could not read tells us nothing about what is in it.
    """
    pr = load("portfolio-rebuild")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)

        bad = rootp / "bad.md"
        bad.write_bytes(b"# roll-up\n\xff\xfe not utf-8\n")
        text, why = pr.read_utf8(bad)
        check(text is None and why == "decode",
              f"invalid UTF-8 is reported as a DECODE failure (got {why!r})")

        unreadable = rootp / "adir"
        unreadable.mkdir()
        text, why = pr.read_utf8(unreadable)
        check(text is None and why == "io",
              f"an unreadable path is reported as an I/O failure, not a decode one "
              f"(got {why!r})")

        # The branch where the distinction changes BEHAVIOUR, not just the message.
        wrote = pr.write_if_changed(unreadable, "replacement content")
        check(wrote is False and unreadable.is_dir(),
              "write_if_changed REFUSES on an I/O failure — overwriting a file we could "
              "not read is a guess dressed as a repair")

        # And the decode branch still regenerates: these roll-ups carry no curated content,
        # and that was a deliberate exception, not an oversight.
        wrote = pr.write_if_changed(bad, "# roll-up\n\nregenerated\n")
        check(wrote is True and bad.read_text() == "# roll-up\n\nregenerated\n",
              "a DECODE failure still regenerates — narrowing the I/O case must not "
              "narrow this one too")


def atomic_write_case():
    """A crash mid-write leaves the old file, not half a new one.

    BL-100's second half. `path.write_text()` is truncate-then-write, so an interrupted run
    left a truncated roll-up in a tree with no version control.
    """
    pr = load("portfolio-rebuild")
    with tempfile.TemporaryDirectory() as root:
        target = Path(root) / "global-backlog.md"
        target.write_text("original content\n")

        class Boom(Exception):
            pass

        real_replace = os.replace

        def exploding_replace(*a, **k):
            raise Boom("interrupted between write and rename")

        os.replace = exploding_replace
        try:
            try:
                # Through write_if_changed, NOT atomic_write directly: the first version of
                # this case called the helper straight and so never pinned that the caller
                # uses it — reverting the call site to path.write_text stayed green.
                pr.write_if_changed(target, "new content that never lands\n")
            except Boom:
                pass
        finally:
            os.replace = real_replace

        check(target.read_text() == "original content\n",
              "an interruption before the rename leaves the ORIGINAL intact — the old "
              "truncate-then-write left a half-file that still looked like a file")
        leftovers = [f.name for f in Path(root).iterdir() if f.name != "global-backlog.md"]
        check(leftovers == [],
              f"and no temp file is left beside it ({leftovers})")

        pr.atomic_write(target, "new content\n")
        check(target.read_text() == "new content\n", "the normal path still writes")


def vault_vanishes_mid_run_case():
    """The vault disappearing AFTER the check must not be rebuilt from nothing.

    BL-099, reproduced verbatim at the Stage 4 gate: with the root removed after a passing
    `require_vault()`, `migrate_project` returned `ok` and recreated
    `<vault>/Portfolio/<area>/<name>/` with the repo's docs inside it. `require_vault` runs
    once in `main()`; the writes follow it, and every `mkdir(parents=True)` downstream is
    happy to build the chain.
    """
    pr = load("portfolio-rebuild")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        vault = rootp / "vault"
        (vault / "Portfolio").mkdir(parents=True)
        check(pr.vault_live(vault), "a mounted vault is live")

        shutil.rmtree(vault)
        check(not pr.vault_live(vault),
              "a vault whose root is gone is NOT live — this is the state the run was in "
              "when it recreated the tree")

        (vault).mkdir()
        check(not pr.vault_live(vault),
              "an existing root with no Portfolio/ is not live either — that is what an "
              "UNMOUNTED mountpoint looks like, and it is the case a plain exists() misses")

        repo = rootp / "repo"
        (repo / "docs" / "plans").mkdir(parents=True)
        (repo / "docs" / "plans" / "p.md").write_text("# plan\n")
        shutil.rmtree(vault)

        pm = load("portfolio-migrate")
        status, label, msg = pm.migrate_project(
            {"path": str(repo), "area": "ai-tools", "name": "demo"}, vault, True)
        check(status == "fail",
              f"migrate_project REFUSES when the vault went away after the check "
              f"(got {status!r}: {msg})")
        check(not vault.exists(),
              "and the vault tree is NOT recreated — the reproduced defect was that it was, "
              "and that the run reported ok")
        check((repo / "docs" / "plans" / "p.md").exists(),
              "the repo's only copy of its docs is still in the repo")


def integrate_cases():
    """Two `integrate --write` runs on an unchanged vault, on different days."""
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        vault = rootp / "vault"
        alpha = vault / "Portfolio" / "ai-tools" / "alpha"
        beta = vault / "Portfolio" / "ai-tools" / "beta"
        alpha.mkdir(parents=True)
        beta.mkdir(parents=True)
        (alpha / "integration.md").write_text(
            integration_md("alpha", impacts=[("beta", "alpha's schema binds beta")]))
        (beta / "integration.md").write_text(
            integration_md("beta", depends=[("alpha", "consumes alpha's schema")]))
        (alpha / "backlog.md").write_text(
            "# Backlog\n\n## BL-001 — teach beta the new schema\n\n"
            "- **Tags:** integration, edge=alpha-schema\n\n---\n")
        reg = write_registry(rootp / "registry.yaml", vault, [
            {"path": str(rootp / "repo-alpha"), "name": "alpha", "area": "ai-tools"},
            {"path": str(rootp / "repo-beta"), "name": "beta", "area": "ai-tools"},
        ])

        graph = vault / "Portfolio" / "integration-graph.md"
        ibl = vault / "Portfolio" / "integration-backlog.md"

        old_today = pi.TODAY
        try:
            # Run 1 — a fresh vault on day one.
            pi.TODAY = "2026-01-01"
            run_main(pi, vault, reg, ["portfolio-integrate.py", "--write"])
            check(graph.exists() and ibl.exists(),
                  "the first --write creates both roll-ups")
            first_graph, first_ibl = graph.read_text(), ibl.read_text()
            check("**Last rebuilt:** 2026-01-01" in first_graph,
                  "...stamped with the simulated date, so the date IS the variable")

            # Run 2 — months later, nothing upstream changed. TODAY is bound at
            # import in portfolio-integrate.py, so rebinding the module global is
            # what makes this a different DAY rather than a repeat of run 1.
            freeze(graph, ibl)
            pi.TODAY = "2026-06-15"
            out, _ = run_main(pi, vault, reg, ["portfolio-integrate.py", "--write"])
            check(graph.read_text() == first_graph and ibl.read_text() == first_ibl,
                  "a second run on a LATER date leaves both roll-ups byte-identical")
            check(untouched(graph) and untouched(ibl),
                  "...and does not write them at all (frozen mtimes survive)")
            check("unchanged" in out and "integration-graph.md" in out,
                  "...and the run reports the files as unchanged rather than 'wrote'")

            # Teeth. If the mtime probe could not see a write, every assertion
            # above would pass against the original bare-write_text() bug.
            # Edit the `depends_on` reason specifically: render_graph() emits the
            # depends_on adjacency, so an impacts-only edit would change nothing
            # and the probe would prove nothing.
            (beta / "integration.md").write_text(
                integration_md("beta", depends=[("alpha", "consumes alpha's schema v2")]))
            freeze(graph, ibl)
            out, _ = run_main(pi, vault, reg, ["portfolio-integrate.py", "--write"])
            check(not untouched(graph),
                  "a real upstream edit DOES rewrite the graph — the probe is live")
            check("consumes alpha's schema v2" in graph.read_text(),
                  "...with the new edge reason, so the rewrite carried the change")
            check(untouched(ibl),
                  "...while the untouched roll-up stays untouched — the write is scoped")
        finally:
            pi.TODAY = old_today


# --------------------------------------------------------------------------
def unify_cases():
    """The justified exception: an append whose guard is the dedup, not a diff."""
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        vault = rootp / "vault"
        repo = rootp / "repo"
        repo.mkdir()
        home = vault / "Portfolio" / "ai-tools" / "alpha"
        (home / "plans").mkdir(parents=True)
        shutil.copy(FIXTURES / "2026-05-01-legacy-single-plan.md",
                    home / "plans" / "2026-05-01-legacy-single-plan.md")
        reg = write_registry(rootp / "registry.yaml", vault, [
            {"path": str(repo), "name": "alpha", "area": "ai-tools"}])
        backlog = home / "backlog.md"

        old_today = pu.TODAY
        try:
            pu.TODAY = "2026-01-01"
            run_main(pu, vault, reg, ["portfolio-unify.py", "--write"])
            check(backlog.exists() and "BL-001" in backlog.read_text(),
                  "unify's first --write appends candidates to the backlog")
            first = backlog.read_text()

            # render_entry() stamps TODAY into every entry it emits, so a naive
            # re-render on a later date would differ. It never gets that far:
            # dedup keys on **Source:**, so there is nothing new to append and
            # the file is not opened.
            freeze(backlog)
            pu.TODAY = "2026-06-15"
            run_main(pu, vault, reg, ["portfolio-unify.py", "--write"])
            check(backlog.read_text() == first,
                  "a second unify on a LATER date leaves backlog.md byte-identical")
            check(untouched(backlog),
                  "...and does not write it at all, despite TODAY having moved")
            check("2026-06-15" not in first,
                  "...so no entry carries the second run's date")

            # Teeth: a genuinely new candidate must still be appended.
            shutil.copy(FIXTURES / "2026-07-24-partial-status-plan.md",
                        home / "plans" / "2026-07-24-partial-status-plan.md")
            freeze(backlog)
            run_main(pu, vault, reg, ["portfolio-unify.py", "--write"])
            check(not untouched(backlog) and len(backlog.read_text()) > len(first),
                  "a new plan DOES append — the no-write above is a guard, not inertia")
            check(backlog.read_text().startswith(first),
                  "...purely by append: the previously curated bytes are carried through")
        finally:
            pu.TODAY = old_today


# --------------------------------------------------------------------------
def migrate_cases():
    """The other justified exception: a one-time move plus two equality-guarded
    in-place rewriters."""
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        vault = rootp / "vault"
        repo = rootp / "repo"
        (repo / "docs" / "plans").mkdir(parents=True)
        (repo / "docs" / "plans" / "2026-05-01-a-plan.md").write_text("# Plan\n")
        (repo / "docs" / "backlog.md").write_text("# Backlog\n")
        (repo / "docs" / "MATURITY.md").write_text(
            "# Maturity\n\n- [x] auto:docs/README.md\n")
        (vault / "Portfolio").mkdir(parents=True)
        proj = {"path": str(repo), "name": "alpha", "area": "ai-tools"}
        home = vault / "Portfolio" / "ai-tools" / "alpha"

        status, _, _ = pm.migrate_project(proj, vault, True)
        check(status == "ok", "migrate's first --write moves the docs into the vault")
        moved = sorted(p for p in home.rglob("*") if p.is_file())
        check(len(moved) == 3, f"...all three files landed ({len(moved)})")
        before = {p: p.read_bytes() for p in moved}

        freeze(*moved)
        status2, _, why2 = pm.migrate_project(proj, vault, True)
        check(status2 == "skip",
              "a second migrate is refused structurally, not re-run")
        check("nothing to migrate" in why2,
              "...by the emptied-docs guard — WHICH guard fired, not merely that one did")
        check(all(p.read_bytes() == before[p] for p in moved)
              and all(untouched(p) for p in moved),
              "...and touches nothing already in the vault")

        # The already-populated preflight, reached on its own. It sits BEHIND the
        # emptied-docs guard (migrate_set() is checked first), and on a real re-run
        # docs/ is always empty by then — so the case above can never exercise it,
        # and a comment claiming both guards were tested would have been false.
        # Repopulating docs/ is what puts this guard in front: migrate_set() is
        # non-empty again, and the refusal has to come from the vault side.
        (repo / "docs" / "plans").mkdir(parents=True, exist_ok=True)
        (repo / "docs" / "plans" / "2026-05-02-b-plan.md").write_text("# Plan B\n")
        freeze(*moved)
        status3, _, why3 = pm.migrate_project(proj, vault, True)
        check(status3 == "skip" and "already populated" in why3,
              "a populated vault home refuses even when docs/ has new files to move")
        check(all(untouched(p) for p in moved),
              "...without touching what is already there")
        shutil.rmtree(repo / "docs" / "plans")

        # The two in-place rewriters, driven directly: both are equality-guarded,
        # which is `write_if_changed` minus the timestamp strip neither needs.
        sidecar = repo / ".claude" / "vault-context.md"
        check(sidecar.exists(), "the sidecar was created by the first migrate")
        freeze(sidecar)
        pm.write_sidecar_home(repo, home)
        check(untouched(sidecar),
              "write_sidecar_home is a no-op when the recorded home is unchanged")
        pm.write_sidecar_home(repo, vault / "Portfolio" / "ai-tools" / "moved")
        check(not untouched(sidecar),
              "...and DOES write when the home changes — the guard is not inertia")

        mat = home / "MATURITY.md"
        check("auto:repo:docs/README.md" in mat.read_text(),
              "the evidence rewrite ran on the migrated MATURITY.md")
        freeze(mat)
        pm.rewrite_maturity_evidence(mat)
        check(untouched(mat),
              "rewrite_maturity_evidence is a no-op once every line is prefixed")
        mat.write_text("# Maturity\n\n- [x] auto:docs/CHANGELOG.md\n")
        freeze(mat)
        pm.rewrite_maturity_evidence(mat)
        check(not untouched(mat) and "auto:repo:docs/CHANGELOG.md" in mat.read_text(),
              "...and DOES rewrite an unprefixed line — the guard is not inertia")


CALL_RE = re.compile(r"\bwrite_if_changed\s*\(")


def routes_through_helper(path: Path) -> bool:
    """True when the script actually CALLS write_if_changed.

    A bare `grep write_if_changed` would answer this question wrongly. The two
    justified exceptions explain themselves by naming the helper and its home
    file, and a mention in a comment is not a call — a sweep that could not tell
    the two apart would report the class clean the moment someone documented why
    it was not. So: a call-shaped match, on a line that is not a comment.
    """
    return any(CALL_RE.search(line) and not line.lstrip().startswith("#")
               for line in path.read_text().splitlines())


# --------------------------------------------------------------------------
def sweep_case():
    """The class claim itself: no `portfolio-*.py` writes the vault unexamined.

    Reproduces the stage gate's own sweep so the exception list cannot grow
    silently. A new script that writes the vault without `write_if_changed`
    fails here until it is either routed through it or added below WITH a case
    in this file — which is what the two current entries have.
    """
    justified = {"portfolio-unify.py": unify_cases,
                 "portfolio-migrate.py": migrate_cases}
    unrouted = sorted(p.name for p in SCRIPTS.glob("portfolio-*.py")
                      if not routes_through_helper(p))
    unexplained = [n for n in unrouted if n not in justified]
    check(not unexplained,
          f"every portfolio-*.py either routes through write_if_changed or is a "
          f"tested exception (unexplained: {unexplained or 'none'})")
    check(all(n in unrouted for n in justified),
          "and every listed exception is still an exception — a script that "
          "gained write_if_changed must lose its entry here, not keep a dead one")


if __name__ == "__main__":
    print("vault liveness — a mount that drops mid-run:")
    vault_vanishes_mid_run_case()
    print("read_utf8 — I/O failure is not a decode failure:")
    io_vs_decode_case()
    print("atomic_write — an interrupted write leaves the original:")
    atomic_write_case()
    print("write_if_changed — both stamp forms:")
    generated_stamp_case()
    print("integrate — byte-idempotent roll-ups across a date change:")
    integrate_cases()
    print("unify — justified append exception:")
    unify_cases()
    print("migrate — justified one-time-move exception:")
    migrate_cases()
    print("class sweep — the exception list is closed:")
    sweep_case()
    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")
