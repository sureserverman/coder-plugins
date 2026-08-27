#!/usr/bin/env python3
"""A `vault_dir` that is SET but names a missing directory is refused, everywhere.

Unset `vault_dir` has always been a loud refusal. Set-but-missing — an unmounted
NFS vault, a stale path, a machine that never had one — was undefined: every
resolver in the portfolio read the key, checked only that it was truthy, and
handed the caller a Path to nowhere. `../SKILL.md` § Configuration said in as
many words that the behavior was "not settled". It is settled now, in the same
direction as unset (§ Resolver), and this file is what keeps the two from
drifting apart again.

Why the class and not one script (DEC-013, and DEC-011's "sweep every consumer"):
the resolver was copied, not shared. Six near-identical `vault_dir()` /
`load_env()` bodies existed across three plugins, plus two command-line overrides
that bypass the config entirely and one renderer that must NOT refuse. A fix to
any one of them leaves the rest writing into a directory they created. They
cannot be collapsed into a single implementation — `business/` and `git-github/`
ship as separate plugins and cannot import from `planning/` — so the shared thing
is this test: sweep_case() below fails if a new portfolio-config reader appears
without an entry here.

The teeth are specific. Refusing "loudly" is not enough on its own: what makes a
missing vault dangerous is `mkdir(parents=True)`, which will happily build the
whole chain from nothing — so the write-path cases assert the missing directory
is still missing after the entry point has run and refused. A resolver fixed
while a downstream mkdir survived would pass an exit-code check and still
materialise a second, empty vault at an unmounted mount point.

Nothing here reads or writes the real vault. Every configured path is under a
throwaway temp tree, asserted before anything runs — see under_tmp().

Stdlib + PyYAML only, no pytest. Run:
  python3 planning/skills/portfolio/tests/test-vault-unreachable.py
"""
from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
PORTFOLIO = HERE.parent
PLANNING = PORTFOLIO.parent.parent          # …/planning
ROOT = PLANNING.parent                      # marketplace root
SCRIPTS = PORTFOLIO / "scripts"

COMPASS_SCAN = PLANNING / "skills" / "compass" / "scripts" / "compass-scan.py"
PLAN_PROGRESS = PLANNING / "skills" / "executing-plans" / "scripts" / "plan-progress.py"
DECISIONS = PLANNING / "skills" / "decisions" / "scripts" / "decisions-relevant.py"
BUSINESS_SCAN = ROOT / "business" / "scripts" / "business-scan.py"
RESOLVE_DEST = ROOT / "business" / "scripts" / "resolve-dest.py"
REPO_HEALTH = ROOT / "git-github" / "skills" / "repo-health" / "scripts" / "repo-health-scan.py"

# The exact token every refusal shares. Pinned as one string on purpose: the
# implementations are separate copies, and "they all refuse" is only a class
# claim if they refuse in a way the operator recognises as the same answer.
TOKEN = "vault unreachable"

# The refusal's INVARIANT tail, lifted from require_vault()'s own source rather
# than retyped here — a constant a test hand-copies is one more place to drift,
# and this file's whole claim is that the copies have not drifted. Matching only
# TOKEN was too weak: it pins two words, so a copy could rewrite everything after
# "vault unreachable:" and still sweep clean while breaking the sentence an
# operator actually reads. The copies interpolate a path and a config, so an
# exact string match is impossible; this is the longest static run they share.
def _squash(s):
    """Normalise source text so a message split across f-string fragments matches.

    The copies write the sentence as adjacent implicitly-concatenated f-strings,
    so the raw source carries `... is not an " f"existing directory ...` — the
    quote/prefix seam sits inside the very phrase being compared. Collapsing
    whitespace is not enough; the seam itself has to go. Both are textual
    normalisations of the SOURCE, not of the runtime message, which is the point:
    the check must work without importing nine modules.
    """
    s = " ".join(s.split())
    for seam in ('" f"', "' f'", '" "', "' '"):
        s = s.replace(seam, "")
    return s


CANON = _squash("""is not an existing directory — refusing, because a missing
vault is not an empty vault. Mount the vault or correct vault_dir.""")

FAILURES: list[str] = []


def check(ok, msg):
    print(f"  {'ok' if ok else 'FAIL'}: {msg}")
    if not ok:
        FAILURES.append(msg)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def under_tmp(*paths: Path):
    """Refuse to run a case whose fixture escaped the temp tree.

    fake_env() in test-vault-write-idempotency.py asserts the same thing by
    calling vault_dir() and comparing. That check is unavailable here — the whole
    point is that vault_dir() exits — so the containment is asserted on the paths
    themselves, before anything is invoked.
    """
    tmp = Path(tempfile.gettempdir()).resolve()
    for p in paths:
        rp = Path(p).resolve()
        assert rp == tmp or tmp in rp.parents, f"fixture escaped {tmp}: {rp}"


def write_config(path: Path, vault) -> Path:
    body = {"version": 1}
    if vault is not None:
        body["vault_dir"] = str(vault)
    path.write_text(yaml.safe_dump(body))
    return path


def write_registry(path: Path, projects) -> Path:
    path.write_text(yaml.safe_dump({"projects": projects}))
    return path


@contextmanager
def env(**overrides):
    old = {k: os.environ.get(k) for k in overrides}
    os.environ.update({k: str(v) for k, v in overrides.items()})
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class Outcome:
    """How a call ended: exited, returned, or crashed — kept DISTINCT.

    A refusal reaches a caller by one of two legitimate routes here —
    `sys.exit(msg)` from the resolvers, or `print(...); return 2` from
    plan-status-audit's main(), that file's own house style for an operator
    error. Both count. Collapsing them would have scored a working `return 2` as
    "did not refuse", and the fix for that phantom would have been to change
    working code to satisfy the test.

    A raised exception is the third outcome and it is NOT a refusal, however
    non-zero it would look to a shell. This distinction is what makes the
    revert-proof readable: with the fix reverted, `main()` reaches a write and
    dies on FileNotFoundError. Treating that as "it refused" would have scored
    the unfixed code green; letting it propagate would have aborted the run at
    the first case and reported nothing about the other nine. It is captured,
    named, and scored red.
    """

    def __init__(self, kind, value, out, err, trace=""):
        self.kind, self.value, self.out, self.err, self.trace = kind, value, out, err, trace

    @property
    def refused(self):
        if self.kind == "exit":
            return self.value not in (0, None)
        if self.kind == "return":
            return isinstance(self.value, int) and self.value != 0
        return False        # "raise" — a traceback is a crash, not a refusal

    @property
    def text(self):
        head = self.value if self.kind == "exit" and isinstance(self.value, str) else ""
        return f"{head}\n{self.out}\n{self.err}\n{self.trace}"


def call(fn, *args, argv=None):
    out, err = io.StringIO(), io.StringIO()
    old_argv = sys.argv
    if argv is not None:
        sys.argv = list(argv)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            try:
                res = Outcome("return", fn(*args), "", "")
            except SystemExit as e:
                res = Outcome("exit", e.code if e.code is not None else 0, "", "")
            except Exception as e:
                res = Outcome("raise", e, "", "", trace=f"{type(e).__name__}: {e}")
    finally:
        sys.argv = old_argv
    res.out, res.err = out.getvalue(), err.getvalue()
    return res


# --------------------------------------------------------------------------
# The four in-tree portfolio resolvers, at their real entry points.
# --------------------------------------------------------------------------
WRITE_MODULES = ("portfolio-integrate", "portfolio-unify",
                 "portfolio-rebuild", "portfolio-migrate")

# Per-module argv for the main() teeth call. portfolio-migrate's parser puts
# --project/--all in a `required=True` mutually exclusive group, so a bare
# `--write` makes argparse SystemExit(2) BEFORE vault_dir() is ever called.
# That still looks like a refusal, and the filesystem assertions after it still
# pass — because nothing ran. For the one script whose mkdir(parents=True) is
# this task's motivating hazard, the teeth would have been measuring argparse.
# The wording assertion below is the real fix (it makes any such vacuity fail
# loudly for every module); this map is what lets migrate reach its guard at all.
EXTRA_ARGV = {"portfolio-migrate": ["--all"]}


def write_path_cases():
    for name in WRITE_MODULES:
        print(f"{name}:")
        mod = load(SCRIPTS / f"{name}.py", name.replace("-", "_"))
        with tempfile.TemporaryDirectory() as root:
            rootp = Path(root)
            missing = rootp / "not-mounted" / "vault"
            under_tmp(missing)
            cfg = write_config(rootp / "config.yaml", missing)
            reg = write_registry(rootp / "registry.yaml", [
                {"path": str(rootp / "repo"), "name": "alpha", "area": "ai-tools"}])
            (rootp / "repo" / "docs").mkdir(parents=True)
            (rootp / "repo" / "docs" / "backlog.md").write_text("# Backlog\n")

            old = (mod.CONFIG, mod.REGISTRY)
            mod.CONFIG, mod.REGISTRY = cfg, reg
            try:
                r = call(mod.vault_dir)
                check(r.refused,
                      f"vault_dir() refuses instead of returning a Path ({r.kind}={r.value!r})")
                check(TOKEN in r.text, f"...with the shared '{TOKEN}' wording")
                check(str(missing) in r.text and str(cfg) in r.text,
                      "...naming both the bad path and the config it came from")

                # The teeth. A resolver that exits but leaves a downstream
                # mkdir(parents=True) in place would pass every check above and
                # still build the vault. Drive main() — the real entry point —
                # and look at the filesystem.
                r = call(mod.main,
                         argv=[f"{name}.py", "--write"] + EXTRA_ARGV.get(name, []))
                check(r.refused,
                      f"main() refuses too — the guard is on the entry path "
                      f"({r.kind}: {r.trace or r.value!r})")
                # WHY it refused, not merely that it did. An arg-parsing exit,
                # an ImportError, any early SystemExit — all satisfy `refused`
                # while proving nothing about the vault guard, and the two
                # filesystem checks below would then pass because no code ran.
                # Asserting the guard's own wording is what makes this teeth
                # rather than theatre.
                check(TOKEN in r.text,
                      f"...and refuses with the vault guard's wording, not some "
                      f"earlier exit ({r.text.strip().splitlines()[-1] if r.text.strip() else r.value!r})")
                check(not missing.exists() and not missing.parent.exists(),
                      "...and creates NO part of the missing vault tree")
                check((rootp / "repo" / "docs" / "backlog.md").exists(),
                      "...and leaves the repo's docs/ alone (no fallback write)")

                # The unset case is unchanged — this file settles a second
                # question, it does not relitigate the first.
                mod.CONFIG = write_config(rootp / "unset.yaml", None)
                r = call(mod.vault_dir)
                check(r.refused and "portfolio not configured" in r.text,
                      "an UNSET vault_dir still gets the original message, not this one")
            finally:
                mod.CONFIG, mod.REGISTRY = old


def expanduser_case():
    """`vault_dir: ~/vault` resolves against $HOME, not the cwd.

    Not a stylistic tidy-up: unexpanded, `Path("~/vault")` is RELATIVE, so every
    write lands in `<cwd>/~/vault` — a fallback write wearing a different name,
    and one the new existence check would have reported as a missing vault while
    the real one sat mounted. plan-progress.py has always expanded; the rest had
    not, which made "the vault" two different corpora (DEC-011).
    """
    print("expanduser:")
    mod = load(SCRIPTS / "portfolio-rebuild.py", "portfolio_rebuild_expand")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        real = rootp / "vault"
        (real / "Portfolio").mkdir(parents=True)   # a REACHABLE vault: see require_vault
        under_tmp(real)
        cfg = write_config(rootp / "config.yaml", "~/vault")
        old = mod.CONFIG
        mod.CONFIG = cfg
        try:
            with env(HOME=rootp):
                r = call(mod.vault_dir)
            check(r.kind == "return" and r.value == real,
                  f"a `~/vault` config resolves to $HOME/vault, not a cwd-relative "
                  f"path, and is not refused (got {r.kind}={r.value!r})")
        finally:
            mod.CONFIG = old
        # The refusal still fires for a `~` path that does not exist, so this is
        # expansion, not a hole punched in the check.
        cfg2 = write_config(rootp / "config2.yaml", "~/absent")
        mod.CONFIG = cfg2
        try:
            with env(HOME=rootp):
                r = call(mod.vault_dir)
            check(r.refused and TOKEN in r.text and str(rootp / "absent") in r.text,
                  "...and an expanded path that is still missing is refused, by its expanded name")
        finally:
            mod.CONFIG = old


# --------------------------------------------------------------------------
# CLI entry points, run as processes with a throwaway HOME.
# --------------------------------------------------------------------------
def run_script(script: Path, home: Path, extra_env=None, args=()):
    e = {**os.environ, "HOME": str(home)}
    e.pop("PORTFOLIO_CONFIG", None)
    e.pop("SECURITY_REGISTRY", None)
    e.update(extra_env or {})
    return subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True, timeout=120, env=e,
                          stdin=subprocess.DEVNULL)


def fake_home(root: Path, vault, projects) -> Path:
    home = root / "home"
    (home / ".claude").mkdir(parents=True)
    write_config(home / ".claude" / "portfolio-config.yaml", vault)
    write_registry(home / ".claude" / "projects-registry.yaml", projects)
    return home


def cli_cases():
    """The read-only scanners: refusal, and NOTHING that parses as a result."""
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        missing = rootp / "not-mounted" / "vault"
        under_tmp(missing)
        repo = rootp / "repo"
        repo.mkdir()
        home = fake_home(rootp, missing, [
            {"path": str(repo), "name": "alpha", "area": "ai-tools"}])

        for label, script, extra in (
                ("compass-scan", COMPASS_SCAN, None),
                ("business-scan", BUSINESS_SCAN, None),
                ("resolve-dest", RESOLVE_DEST, None),
                ("security-scan", SCRIPTS / "security-scan.py",
                 {"PORTFOLIO_CONFIG": str(home / ".claude" / "portfolio-config.yaml"),
                  "SECURITY_REGISTRY": str(home / ".claude" / "projects-registry.yaml")}),
        ):
            print(f"{label} (read-only entry point):")
            r = run_script(script, home, extra)
            blob = r.stdout + r.stderr
            check(r.returncode != 0, "exits non-zero on an unreachable vault")
            check(TOKEN in blob, f"...saying '{TOKEN}'")
            check(str(missing) in blob, "...and naming the path that is not there")
            check(r.stdout.strip() == "",
                  "...and prints nothing on stdout — no empty envelope to mistake for an answer")
        check(not missing.exists(),
              "no read-only scanner created the missing vault directory")


def repo_health_case():
    """The first justified divergence: keep scanning, but say the check is off.

    repo-health's corpus is GitHub; the vault is a side cross-check, so an
    unmounted vault is not a reason to abandon a CI sweep. What it may NOT do is
    let `backlog_cross_check: false` stand alone, because that is also what a
    portfolio with no vault at all reports — and an unmeasured cross-check would
    then read as one that was never asked for.
    """
    print("repo-health-scan (divergence: optional corpus, structured signal):")
    mod = load(REPO_HEALTH, "repo_health_scan")
    # FOUR configurations, because the claim is that they stay DISTINCT — and the
    # fourth is the one this case previously got wrong in a way that PINNED a bug.
    # `present` used to be a bare mkdir() with no Portfolio/ beneath it, i.e. an
    # unmounted-shaped vault, asserted as `expect_vault=True`. When the shared
    # guard gained the Portfolio/ sentinel this file was left on the old bare
    # is_dir(), and this fixture is what made the suite stay green over it: the
    # test encoded the defect as the expected result. A fixture that is itself
    # the wrong shape cannot fail on the right one.
    for label, vault, expect_vault, expect_unreachable in (
            ("configured and present", "present", True, False),
            ("configured but missing", "missing", False, True),
            ("configured but UNMOUNTED (exists, no Portfolio/)", "unmounted", False, True),
            ("not configured at all", None, False, False)):
        with tempfile.TemporaryDirectory() as root:
            rootp = Path(root)
            missing = rootp / "not-mounted" / "vault"
            present = rootp / "vault"
            (present / "Portfolio").mkdir(parents=True)   # a REACHABLE vault
            unmounted = rootp / "mnt" / "vault"
            unmounted.mkdir(parents=True)                 # mountpoint, nothing mounted
            under_tmp(missing, present, unmounted)
            repo = rootp / "repo"
            repo.mkdir()
            chosen = {"present": present, "missing": missing,
                      "unmounted": unmounted, None: None}[vault]
            home = fake_home(rootp, chosen, [
                {"path": str(repo), "name": "alpha", "area": "ai-tools"}])
            err = io.StringIO()
            # Unpacked defensively for the same reason call() catches: before
            # this change load_env() returned a 2-tuple, and letting the
            # ValueError escape would abort the whole file at this case instead
            # of scoring it red — which is exactly what a revert-proof must not
            # do.
            try:
                with env(HOME=home), redirect_stderr(err):
                    v, unreachable, projects = mod.load_env()
            except (ValueError, TypeError) as e:
                check(False, f"{label}: load_env() returns (vault, unreachable, projects) ({e})")
                continue
            check((v is not None) is expect_vault,
                  f"{label}: vault {'resolves' if expect_vault else 'is None'}")
            check((unreachable is not None) is expect_unreachable,
                  f"{label}: vault_unreachable {'is reported' if expect_unreachable else 'is absent'}")
            check(len(projects) == 1, f"{label}: the sweep still has its projects")
            if expect_unreachable:
                # Against `chosen`, not a hardcoded `missing`: an assertion that
                # names one fixture can only ever describe one case, and would
                # have reported the unmounted case as broken while it worked.
                check(unreachable == str(chosen) and TOKEN in err.getvalue(),
                      f"{label}: the reason names the path, on stderr and in the return")
                check(not missing.exists() and not (unmounted / "Portfolio").exists(),
                      f"{label}: read-only — nothing was created at either bad path")


def plan_progress_case():
    """The second justified divergence: a statusline renderer degrades silently.

    It runs on every prompt render, where sys.exit is a broken shell prompt. The
    thing it must NOT do is take the in-tree `docs/plans` fallback, which belongs
    to `vault_dir` UNSET — bars built from in-tree plans while the configured
    vault is unreachable would be confidently wrong. Both branches are asserted
    here, because "silently degrades" is only correct if they stay distinct.
    """
    print("plan-progress (divergence: statusline degrades, never falls back):")
    mod = load(PLAN_PROGRESS, "plan_progress")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        missing = rootp / "not-mounted" / "vault"
        under_tmp(missing)
        repo = rootp / "repo"
        (repo / "docs" / "plans").mkdir(parents=True)
        (repo / "docs" / "plans" / "2026-01-01-a-plan.md").write_text("# Plan\n")
        home = fake_home(rootp, missing, [
            {"path": str(repo), "name": "alpha", "area": "ai-tools"}])

        old = (mod.CONFIG_PATH, mod.REGISTRY_PATH)
        mod.CONFIG_PATH = home / ".claude" / "portfolio-config.yaml"
        mod.REGISTRY_PATH = home / ".claude" / "projects-registry.yaml"
        try:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                got = mod.portfolio_plans_dir(repo)
            check(got is None, "an unreachable vault yields no plans dir — no bars")
            check(got != repo / "docs" / "plans",
                  "...and specifically NOT the in-tree fallback, which exists here")
            check(out.getvalue() == "" and err.getvalue() == "",
                  "...silently: a statusline may not print or exit")
            check(not missing.exists(), "...and creates nothing")

            # The fallback is alive for the case it belongs to. Without this the
            # assertion above would also pass against a renderer that had simply
            # stopped resolving anything.
            mod.CONFIG_PATH = write_config(rootp / "unset.yaml", None)
            got = mod.portfolio_plans_dir(repo)
            check(got == repo / "docs" / "plans",
                  "an UNSET vault_dir still falls back to <repo>/docs/plans — the two differ")
        finally:
            mod.CONFIG_PATH, mod.REGISTRY_PATH = old


def override_cases():
    """`--vault` / `--vault-dir` bypass the config; they may not bypass the rule."""
    print("plan-status-audit --vault:")
    mod = load(SCRIPTS / "plan-status-audit.py", "plan_status_audit")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        missing = rootp / "not-mounted" / "vault"
        under_tmp(missing)
        reg = write_registry(rootp / "registry.yaml", [
            {"path": str(rootp / "repo"), "name": "alpha", "area": "ai-tools"}])
        r = call(mod.main, argv=["plan-status-audit.py", "--vault", str(missing),
                                 "--registry", str(reg), "--fix"])
        blob = r.text
        check(r.refused,
              f"--vault at a missing directory is refused ({r.kind}: {r.trace or r.value!r})")
        check(TOKEN in blob and "--vault" in blob,
              "...naming the flag as the source, not the config file")
        check(not missing.exists(), "...and no .audit-backups tree is created under it")

    print("decisions-relevant (delegation + --vault-dir):")
    dmod = load(DECISIONS, "decisions_relevant")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        missing = rootp / "not-mounted" / "vault"
        under_tmp(missing)
        # Delegation, verified rather than assumed: this script has no resolver
        # of its own, it calls portfolio-rebuild's. Redirecting THAT module's
        # CONFIG is what proves the delegation is real and live.
        cfg = write_config(rootp / "config.yaml", missing)
        old = dmod.pr.CONFIG
        dmod.pr.CONFIG = cfg
        try:
            r = call(dmod.main, ["--list-domains"])
            blob = r.text
            check(r.refused and TOKEN in blob,
                  f"the configured path refuses through the imported resolver "
                  f"({r.kind}: {r.trace or r.value!r})")
            check(str(cfg) in blob,
                  "...and the message names the config, proving it came from the delegate")
        finally:
            dmod.pr.CONFIG = old
        r = call(dmod.main, ["--list-domains", "--vault-dir", str(missing)])
        blob = r.text
        check(r.refused and TOKEN in blob and "--vault-dir" in blob,
              "--vault-dir at a missing directory is refused, not read as an empty register")
        check("no domain registers found" not in blob,
              "...specifically NOT reported as 'no domain registers found'")


# --------------------------------------------------------------------------
def unmounted_case():
    """The scenario the guard is NAMED for, which `is_dir()` alone cannot see.

    A mountpoint is a directory whether or not anything is mounted on it. So an
    unmounted NFS vault — `/mnt/vault` on the machine this was written for is
    `192.168.0.209:/home/rumata/vault` over nfs4 — presents as a local, empty,
    EXISTING directory, and sails through an existence check. The original guard
    therefore missed its own headline case while its docstring claimed to cover
    it, and `portfolio-migrate --all --write` would then mkdir(parents=True) a
    phantom tree and move a repo's only copy of its docs into it, leaving the
    real vault holding the divergent original and nothing git-tracked to recover
    from. A vault is defined by CONTENT — it contains `Portfolio/`.

    Driven through the real entry points as subprocesses, and asserted at the
    FILESYSTEM: rc and message are not enough, because the whole failure mode is
    a tree that gets built anyway.
    """
    print("unmounted mountpoint — an existing empty dir is not a vault:")
    scripts = [
        ("portfolio-rebuild", SCRIPTS / "portfolio-rebuild.py", ["--write"]),
        ("portfolio-unify", SCRIPTS / "portfolio-unify.py", ["--write"]),
        ("portfolio-migrate", SCRIPTS / "portfolio-migrate.py", ["--all", "--write"]),
        ("portfolio-integrate", SCRIPTS / "portfolio-integrate.py", ["--write"]),
        ("security-scan", SCRIPTS / "security-scan.py", []),
        ("compass-scan", ROOT / "planning" / "skills" / "compass" / "scripts"
         / "compass-scan.py", []),
        ("business-scan", ROOT / "business" / "scripts" / "business-scan.py", []),
    ]
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        home = rootp / "home"
        (home / ".claude").mkdir(parents=True)
        vault = rootp / "mnt" / "vault"
        vault.mkdir(parents=True)                  # the mountpoint, nothing mounted
        under_tmp(vault)
        repo = rootp / "dev" / "proj"
        (repo / "docs" / "plans").mkdir(parents=True)
        (repo / "docs" / "plans" / "2026-01-01-a-plan.md").write_text("# Plan\n")
        (repo / "docs" / "backlog.md").write_text("# Backlog\n")
        (repo / "docs" / "MATURITY.md").write_text("# Maturity\n")
        write_config(home / ".claude" / "portfolio-config.yaml", vault)
        write_registry(home / ".claude" / "projects-registry.yaml",
                       [{"path": str(repo), "name": "proj", "area": "ai-tools"}])
        env = dict(os.environ, HOME=str(home))
        env.pop("PORTFOLIO_NO_STALE_WARNING", None)
        for name, path, args in scripts:
            r = subprocess.run([sys.executable, str(path)] + args, env=env,
                               capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=120)
            blob = r.stdout + r.stderr
            check(r.returncode != 0 and TOKEN in blob,
                  f"{name}: refuses an unmounted mountpoint (rc={r.returncode})")
        check(not (vault / "Portfolio").exists(),
              "...and NO part of a phantom vault tree was created")
        survivors = sorted(q.name for q in (repo / "docs").rglob("*") if q.is_file())
        check(survivors == ["2026-01-01-a-plan.md", "MATURITY.md", "backlog.md"],
              f"...and the repo's docs/ is untouched — nothing was moved ({survivors})")

        # Teeth: the SAME vault with Portfolio/ present is accepted, so the checks
        # above are the sentinel firing and not the scripts failing for some other
        # reason. portfolio-integrate is the cheapest real writer to prove it with.
        (vault / "Portfolio").mkdir()
        r = subprocess.run([sys.executable, str(SCRIPTS / "portfolio-integrate.py"),
                            "--write"], env=env, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=120)
        check(r.returncode == 0 and TOKEN not in (r.stdout + r.stderr),
              f"...while the same vault WITH Portfolio/ is accepted (rc={r.returncode})")


def bad_value_cases():
    """A relative path, and a value that is not a path at all."""
    print("malformed vault_dir — refused with a message naming the knob:")
    mod = load(SCRIPTS / "portfolio-rebuild.py", "portfolio_rebuild_badval")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        old = mod.CONFIG
        try:
            # Relative: one config means a different vault per cwd. Refused rather
            # than resolved, because resolving it would silently pick one.
            mod.CONFIG = write_config(rootp / "rel.yaml", "vault")
            r = call(mod.vault_dir)
            check(r.refused and "relative path" in r.text,
                  f"a relative vault_dir is refused, not resolved against cwd ({r.text[:60]!r})")

            # Not a string. Guarded on the RAW value: Path(12345) raises inside
            # pathlib, so a guard placed after it could never speak.
            (rootp / "int.yaml").write_text("version: 1\nvault_dir: 12345\n")
            mod.CONFIG = rootp / "int.yaml"
            r = call(mod.vault_dir)
            check(r.refused and "must be a path" in r.text,
                  f"a non-path vault_dir gets the shared refusal, not a TypeError "
                  f"({r.kind}: {r.text[:60]!r})")
        finally:
            mod.CONFIG = old


# The phrase unique to each guard branch. Comparing these rather than a bare
# refuse/accept is what makes a deleted condition visible: a missing branch still
# refuses, just one condition later and with a different sentence.
BRANCH_PHRASE = {
    "missing": "is not an existing directory",
    "unmounted (no Portfolio/)": "has no Portfolio/",
    "relative": "relative path",
    "not a path": "must be a path",
    "unreadable (OSError)": "could not be read",
}


def branch_parity_case():
    """Every copy of the guard classifies every vault shape the same way.

    This exists because the `CANON` sweep below cannot do it. That sweep matches
    one SENTENCE — the existing-directory refusal — so a copy that is missing an
    entire CONDITION still passes it. Measured, not supposed, twice over:

      * `business-scan.py` was left behind when the `OSError` branch was added and
        emitted a raw traceback where every other consumer emitted the shared
        refusal, with the wording sweep green throughout.
      * Deleting BOTH the `isinstance` and `is_absolute` branches from
        repo-health's copy left all 41 suites green.

    So the pin has to be over the branch SET, driven through each copy's real
    entry point. Sentence-level agreement is not behavioural agreement, and the
    thing that keeps drifting is a branch, not a phrase.

    The `OSError` shape is the one this most needed: it was added by a remediation
    round and had zero coverage in any of the three copies — reverting the
    canonical `try/except` left the whole suite green.
    """
    print("branch parity — every copy agrees on every vault shape:")
    consumers = [
        ("portfolio-rebuild", SCRIPTS / "portfolio-rebuild.py", ["--write"]),
        ("portfolio-unify", SCRIPTS / "portfolio-unify.py", ["--write"]),
        ("portfolio-integrate", SCRIPTS / "portfolio-integrate.py", ["--write"]),
        ("portfolio-migrate", SCRIPTS / "portfolio-migrate.py", ["--all", "--write"]),
        ("security-scan", SCRIPTS / "security-scan.py", []),
        ("compass-scan", ROOT / "planning" / "skills" / "compass" / "scripts"
         / "compass-scan.py", []),
        ("business-scan", ROOT / "business" / "scripts" / "business-scan.py", []),
    ]
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        home = rootp / "home"
        (home / ".claude").mkdir(parents=True)
        write_registry(home / ".claude" / "projects-registry.yaml", [])
        cfg = home / ".claude" / "portfolio-config.yaml"

        outer = rootp / "outer"
        unreadable = outer / "vault"
        (unreadable / "Portfolio").mkdir(parents=True)
        unmounted = rootp / "mnt" / "vault"
        unmounted.mkdir(parents=True)
        under_tmp(unreadable, unmounted)

        # (label, configured value, chmod-target or None)
        # BRANCH_PHRASE below maps each to the phrase ONLY its branch emits.
        shapes = [
            ("missing", str(rootp / "not-mounted" / "vault"), None),
            ("unmounted (no Portfolio/)", str(unmounted), None),
            ("relative", "somevault", None),
            ("not a path", 12345, None),
            ("unreadable (OSError)", str(unreadable), outer),
        ]
        env_ = dict(os.environ, HOME=str(home))
        env_.pop("PORTFOLIO_NO_STALE_WARNING", None)
        for label, value, chmod_target in shapes:
            body = {"version": 1, "vault_dir": value}
            cfg.write_text(yaml.safe_dump(body))
            if chmod_target:
                os.chmod(chmod_target, 0o000)
            try:
                verdicts = {}
                for name, path, args in consumers:
                    r = subprocess.run([sys.executable, str(path)] + args, env=env_,
                                       capture_output=True, text=True,
                                       stdin=subprocess.DEVNULL, timeout=120)
                    blob = r.stdout + r.stderr
                    verdicts[name] = (r.returncode != 0,
                                      TOKEN in blob,
                                      "Traceback (most recent call last)" in blob)
            finally:
                if chmod_target:
                    os.chmod(chmod_target, 0o755)

            refused = [n for n, v in verdicts.items() if v[0]]
            tokened = [n for n, v in verdicts.items() if v[1]]
            crashed = [n for n, v in verdicts.items() if v[2]]
            check(len(refused) == len(consumers),
                  f"{label}: every copy refuses "
                  f"({len(refused)}/{len(consumers)}; not: "
                  f"{[n for n in verdicts if n not in refused] or 'none'})")
            check(len(tokened) == len(consumers),
                  f"{label}: ...with the SHARED refusal, not each its own "
                  f"({[n for n in verdicts if n not in tokened] or 'none'} missing it)")
            check(not crashed,
                  f"{label}: ...and none of them crashes instead of refusing "
                  f"({crashed or 'none'})")

        # repo-health's copy cannot join the subprocess loop: its posture is
        # continue-and-signal, so it exits 0 by design, and the real CLI bails
        # early when `gh` is unauthenticated. Compared FUNCTION to function
        # instead, against the canonical guard, on the same shapes — without this
        # the loop above silently excluded it, and deleting a whole branch from it
        # went undetected exactly as before.
        canon = load(SCRIPTS / "portfolio-rebuild.py", "pr_parity")
        rh = load(REPO_HEALTH, "rh_parity")
        # Compared by WHICH branch fired, not merely that one did. Refuse-vs-accept
        # is too weak to pin a branch set: strip `is_absolute` and a relative path
        # still refuses — one condition later, as "not an existing directory". Both
        # copies would agree, and the deletion would pass. Each shape therefore
        # names the phrase only its own branch produces.
        for label, value, chmod_target in shapes:
            if chmod_target:
                os.chmod(chmod_target, 0o000)
            try:
                verdicts = {}
                for who, fn in (("canonical", canon.vault_problem),
                                ("repo-health", rh._vault_problem)):
                    try:
                        verdicts[who] = fn(value, "cfg")[1] or ""
                    except Exception as e:
                        # A raised exception is a CRASH, not a refusal — the same
                        # distinction the write-path cases draw. Scored red rather
                        # than allowed to abort the file.
                        verdicts[who] = f"<crashed: {type(e).__name__}>"
            finally:
                if chmod_target:
                    os.chmod(chmod_target, 0o755)
            want = BRANCH_PHRASE[label]
            for who, got in verdicts.items():
                check(want in got,
                      f"{label}: {who} refuses via its own branch "
                      f"(want {want!r}, got {got[:70]!r})")
        good = rootp / "rh-good"
        (good / "Portfolio").mkdir(parents=True)
        _, c_ok = canon.vault_problem(str(good), "cfg")
        _, r_ok = rh._vault_problem(str(good), "cfg")
        check(c_ok is None and r_ok is None,
              "reachable vault: both accept — the agreements above discriminate")

        # Teeth: the reachable shape must be accepted by all of them, or the three
        # assertions above would pass for a guard that simply refuses everything.
        reachable = rootp / "good"
        (reachable / "Portfolio").mkdir(parents=True)
        cfg.write_text(yaml.safe_dump({"version": 1, "vault_dir": str(reachable)}))
        accepted = []
        for name, path, args in consumers:
            r = subprocess.run([sys.executable, str(path)] + args, env=env_,
                               capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=120)
            if TOKEN not in (r.stdout + r.stderr):
                accepted.append(name)
        check(len(accepted) == len(consumers),
              f"reachable vault: every copy ACCEPTS it — the refusals above "
              f"discriminate ({[n for n, _, _ in consumers if n not in accepted] or 'none'} refused)")


def sweep_case():
    """The class claim: every portfolio-config reader in the tree is accounted for.

    The resolver is a copied contract, not a shared one — three plugins ship
    independently and cannot import each other — so nothing structural stops a
    seventh copy appearing without the check. This sweep is the stop: a new
    non-test .py that reads `vault_dir` out of `portfolio-config.yaml` fails here
    until it is listed below WITH a case above, exactly as
    test-vault-write-idempotency.py closes its own exception list.

    KNOWN LIMIT, stated rather than left for a reader to discover: the predicate
    is textual — it matches a file that names `portfolio-config.yaml` AND
    `vault_dir`. A consumer that reaches the vault by DELEGATING to one of these
    readers names neither, so this sweep is structurally blind to it.
    `business/scripts/resolve-dest.py` is exactly that shape (it calls
    business-scan's load_env()) and is covered only because it is hand-wired into
    cli_cases() — the mechanical guard did not find it and could not. So: this
    closes the class of DIRECT config readers, not the class of vault consumers.
    A new delegating wrapper that swallows the refusal would ship with this sweep
    reporting the tree fully covered. Widening the predicate to trace importlib
    delegation is the real fix and is not attempted here; saying so is the
    minimum, because a check that overstates its coverage is worse than one that
    admits its scope.
    """
    print("class sweep — every portfolio-config reader is covered:")
    # rel → (case that exercises it, how it refuses).
    #   literal   — carries the shared wording itself
    #   delegates — calls portfolio-rebuild.require_vault(), which carries it
    #   structured/silent — the two justified divergences, which by design do not
    #                       emit the refusal at all
    covered = {
        "planning/skills/portfolio/scripts/portfolio-integrate.py": ("write_path_cases", "delegates"),
        "planning/skills/portfolio/scripts/portfolio-unify.py": ("write_path_cases", "delegates"),
        "planning/skills/portfolio/scripts/portfolio-rebuild.py": ("write_path_cases", "literal"),
        "planning/skills/portfolio/scripts/portfolio-migrate.py": ("write_path_cases", "delegates"),
        "planning/skills/portfolio/scripts/security-scan.py": ("cli_cases", "delegates"),
        "planning/skills/compass/scripts/compass-scan.py": ("cli_cases", "delegates"),
        "business/scripts/business-scan.py": ("cli_cases", "literal"),
        "git-github/skills/repo-health/scripts/repo-health-scan.py": ("repo_health_case", "structured"),
        "planning/skills/executing-plans/scripts/plan-progress.py": ("plan_progress_case", "silent"),
    }
    # Reached through an imported resolver or a CLI flag rather than by reading
    # the config, so the sweep predicate cannot see them. Listed here so the
    # wording check still binds them, and exercised by override_cases().
    off_sweep = {
        "planning/skills/portfolio/scripts/plan-status-audit.py": "delegates",
    }
    found = set()
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        if "/tests/" in f"/{rel}" or "__pycache__" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "portfolio-config.yaml" in text and "vault_dir" in text:
            found.add(rel)
    unlisted = sorted(found - set(covered))
    stale = sorted(set(covered) - found)
    check(not unlisted,
          f"no unlisted portfolio-config reader (unlisted: {unlisted or 'none'})")
    check(not stale,
          f"every listed reader still exists and still reads the config "
          f"(stale entries: {stale or 'none'})")

    # And the wording really is shared. Each refusal is its own literal, so a
    # copy that drifts to a different phrase would still "refuse" while breaking
    # the one thing an operator matches on.
    kinds = {**{rel: k for rel, (_, k) in covered.items()}, **off_sweep}
    missing = [rel for rel, kind in sorted(kinds.items())
               if kind == "literal"
               and CANON not in _squash((ROOT / rel).read_text(
                   encoding="utf-8", errors="replace"))]
    check(not missing,
          f"every reader that refuses in its own words carries the WHOLE shared "
          f"sentence, not just '{TOKEN}' "
          f"(missing: {missing or 'none'})")
    # The delegating one must still actually delegate: a copy-paste that dropped
    # the call would leave it silently returning a Path to nowhere while the
    # wording check above kept passing (it was never asked about that file).
    # Either entry point into the shared guard counts: require_vault() exits, and
    # vault_problem() returns (path, message) for the one caller that must return
    # its own rc instead. Accepting only the exiting form would have pushed
    # plan-status-audit back to a hand-copied condition to keep its rc 2 — which
    # is exactly how it came to be the last reader still on the v1 check.
    delegating = [rel for rel, kind in sorted(kinds.items()) if kind == "delegates"]
    missing_call = [rel for rel in delegating
                    if not any(fn in (ROOT / rel).read_text(encoding="utf-8",
                                                            errors="replace")
                               for fn in ("require_vault(", "vault_problem("))]
    check(delegating and not missing_call,
          f"every delegating reader calls require_vault() or vault_problem() "
          f"(missing: {missing_call or 'none'})")


if __name__ == "__main__":
    write_path_cases()
    unmounted_case()
    bad_value_cases()
    branch_parity_case()
    expanduser_case()
    cli_cases()
    repo_health_case()
    plan_progress_case()
    override_cases()
    sweep_case()
    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")
