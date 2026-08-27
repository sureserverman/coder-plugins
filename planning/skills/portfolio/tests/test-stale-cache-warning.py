#!/usr/bin/env python3
"""A script running from a superseded plugin cache says so, once, on stderr.

Claude Code keeps every plugin version it has ever installed under
`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` — seven `planning/` trees
on the machine this was written against. Nothing pins which one an invocation resolves
to, so a fixed bug can keep reproducing out of a stale copy while the checkout has been
correct for weeks. The stale copy passes its own tests; that is what makes it invisible.

Two properties are tested, and the second is the one that is easy to fake:

  1. `warn_if_stale()` warns when, and only when, the checkout is genuinely ahead.
  2. The probe is actually WIRED into the real entry points — driven by copying a real
     script into a real cache-shaped tree and running it as a subprocess. A suite that
     only exercised the helper would pass in full while no script called it, which is
     the failure this plan has already hit once (see the Task 4.3 review notes: a
     `main()` teeth-call that argparse short-circuited before the guard was reached).

Nothing here touches the real vault, the real registry, or the user's real HOME — the
subprocess cases run with HOME redirected into the temp tree, which is also what makes
the registry lookup resolve to a fixture instead of the operator's own file.

Stdlib + PyYAML only, no pytest. Run:
  python3 planning/skills/portfolio/tests/test-stale-cache-warning.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
ROOT = HERE.parents[3]          # …/coder-plugins

FAILURES: list[str] = []


def check(ok, msg):
    print(f"  {'ok' if ok else 'FAIL'}: {msg}")
    if not ok:
        FAILURES.append(msg)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ss = load(SCRIPTS / "_staleness.py", "_staleness")


def make_registry(path: Path, name: str, target: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(
        {"projects": [{"path": str(target), "name": name, "area": "ai-tools",
                       "enabled": True}]}))
    return path


def make_checkout(root: Path, plugin: str, version: str):
    """A checkout whose marketplace.json advertises `version` for `plugin`."""
    root.mkdir(parents=True, exist_ok=True)
    man = root / ".claude-plugin"
    man.mkdir(exist_ok=True)
    (man / "marketplace.json").write_text(json.dumps({
        "name": "coder-plugins",
        "metadata": {"version": "0.27.0"},
        "plugins": [{"name": "other-plugin", "version": "9.9.9"},
                    {"name": plugin, "version": version}],
    }))
    return root


def cached_script(root: Path, plugin: str, version: str, name="portfolio-unify.py"):
    """A path shaped like an installed plugin cache. The file need not exist for
    the coordinate parse; cases that RUN it create it themselves."""
    return (root / "plugins" / "cache" / "coder-plugins" / plugin / version
            / "skills" / "portfolio" / "scripts" / name)


def capture(fn, *a, **kw):
    """(result, stderr-text) — the helper must never write to stdout.

    Clears PORTFOLIO_NO_STALE_WARNING first. A successful warn SETS that variable
    (to silence child processes), so without this every case after the first would
    pass by being suppressed rather than by the property it claims to test — the
    suite would go green while measuring nothing, which is the failure mode this
    plan keeps finding. `dedupe_cases()` is where the variable's effect is tested
    on purpose; everywhere else it is reset.
    """
    os.environ.pop("PORTFOLIO_NO_STALE_WARNING", None)
    err = io.StringIO()
    with redirect_stderr(err):
        res = fn(*a, **kw)
    return res, err.getvalue()


# --------------------------------------------------------------------------
def helper_cases():
    print("warn_if_stale — warns exactly when the checkout is ahead:")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        checkout = make_checkout(rootp / "checkout", "planning", "0.44.0")
        reg = make_registry(rootp / "registry.yaml", "coder-plugins", checkout)
        script = cached_script(rootp, "planning", "0.43.1")

        msg, err = capture(ss.warn_if_stale, script, registry=reg)
        check(msg is not None and "0.43.1" in msg and "0.44.0" in msg,
              f"a newer checkout warns, naming both versions ({msg!r})")
        check(msg is not None and msg in err and err.count("\n") == 1,
              "...exactly one line, on stderr")
        check(str(checkout) in (msg or ""),
              "...and names the checkout, so the operator knows which tree is ahead")

        # Same version — the common case, and the one that must stay quiet.
        same = cached_script(rootp, "planning", "0.44.0")
        msg, err = capture(ss.warn_if_stale, same, registry=reg)
        check(msg is None and err == "",
              "an up-to-date cache says nothing at all")

        # Checkout BEHIND the cache is a real state, not staleness.
        ahead = cached_script(rootp, "planning", "0.99.0")
        msg, err = capture(ss.warn_if_stale, ahead, registry=reg)
        check(msg is None and err == "",
              "a checkout BEHIND the cache is silent — that is not stale")

        # A plugin the manifest does not list at all.
        other = cached_script(rootp, "not-a-plugin", "0.1.0")
        msg, _ = capture(ss.warn_if_stale, other, registry=reg)
        check(msg is None, "a plugin absent from the manifest is silent")

    print("warn_if_stale — equal versions written at different widths:")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        # "0.44" and "0.44.0" are the SAME version. Compared as raw tuples,
        # (0, 44) < (0, 44, 0), so the shorter form would be read as older and a
        # warning invented for a cache that is perfectly current.
        short = make_checkout(rootp / "short", "planning", "0.44")
        sreg = make_registry(rootp / "short.yaml", "coder-plugins", short)
        check(ss._version_tuple("0.44") == ss._version_tuple("0.44.0")
              == ss._version_tuple("0.44.0.0"),
              "0.44, 0.44.0 and 0.44.0.0 parse to ONE tuple — the padding itself, "
              "asserted directly because the behavioural case below cannot see it")
        msg, _ = capture(ss.warn_if_stale,
                         cached_script(rootp, "planning", "0.44.0"), registry=sreg)
        # Honest note: this direction was never broken. Unpadded, (0, 44) <= (0, 44, 0)
        # is already True because a strict prefix compares less-or-equal, so this case
        # passes with or without the fix. Kept as a regression pin, NOT as teeth — the
        # mirror case below is what fails on a revert.
        check(msg is None, "checkout '0.44' vs cache '0.44.0' is silent — same version "
                           "(pin, not teeth: this direction never failed)")

        long_ = make_checkout(rootp / "long", "planning", "0.44.0")
        lreg = make_registry(rootp / "long.yaml", "coder-plugins", long_)
        msg, _ = capture(ss.warn_if_stale,
                         cached_script(rootp, "planning", "0.44"), registry=lreg)
        check(msg is None, "...and the mirror image is silent too, not a warning "
                           "in the other direction")

        # Teeth: a genuinely newer checkout at a different width still warns.
        msg, _ = capture(ss.warn_if_stale,
                         cached_script(rootp, "planning", "0.43"), registry=lreg)
        check(msg is not None,
              "...while 0.43 vs 0.44.0 still warns — width-tolerance is not blindness")

    print("warn_if_stale — the registry honours CLAUDE_CONFIG_DIR:")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        checkout = make_checkout(rootp / "checkout", "planning", "0.44.0")
        cfgdir = rootp / "relocated"
        make_registry(cfgdir / "projects-registry.yaml", "coder-plugins", checkout)
        script = cached_script(rootp, "planning", "0.43.1")
        # No `registry=` argument: this exercises the DEFAULT path, which is the
        # one that used to hardcode ~/.claude while _cache_coords argued against it.
        # HOME is redirected for the WHOLE block, not just the subprocess cases.
        # Without it the `unset` half below falls through to the operator's own
        # ~/.claude/projects-registry.yaml — which on this machine resolves to this
        # very checkout — so it would pass or fail on the repo's real planning
        # version rather than on anything this test controls. It passed by
        # coincidence (real version == the fixture's "old cache" version) and would
        # have started failing at this plan's own close-out bump. A test that reads
        # host state is not a test of the fallback; it is a test of the host.
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(rootp / "no-such-home")
        os.environ["CLAUDE_CONFIG_DIR"] = str(cfgdir)
        try:
            msg, _ = capture(ss.warn_if_stale, script)
            check(msg is not None,
                  "a relocated config dir is found by the default registry lookup")
            del os.environ["CLAUDE_CONFIG_DIR"]
            msg, _ = capture(ss.warn_if_stale, script)
            check(msg is None,
                  "...and with it unset the lookup goes to $HOME/.claude, which here "
                  "holds no registry — so the probe was genuinely reading the variable")
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

    print("warn_if_stale — every degraded input is silent, never fatal:")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        checkout = make_checkout(rootp / "checkout", "planning", "0.44.0")
        reg = make_registry(rootp / "registry.yaml", "coder-plugins", checkout)
        script = cached_script(rootp, "planning", "0.43.1")

        msg, _ = capture(ss.warn_if_stale, SCRIPTS / "portfolio-unify.py", registry=reg)
        check(msg is None, "a script running from a CHECKOUT is not cached — silent")

        msg, _ = capture(ss.warn_if_stale, script, registry=rootp / "nope.yaml")
        check(msg is None, "a missing registry is silent")

        bad = rootp / "bad.yaml"
        bad.write_text("{{{ not yaml")
        msg, _ = capture(ss.warn_if_stale, script, registry=bad)
        check(msg is None, "an unparseable registry is silent")

        gone = make_registry(rootp / "gone.yaml", "coder-plugins", rootp / "absent")
        msg, _ = capture(ss.warn_if_stale, script, registry=gone)
        check(msg is None, "a registry pointing at an absent checkout is silent")

        nomani = make_registry(rootp / "nomani.yaml", "coder-plugins", rootp / "empty")
        (rootp / "empty").mkdir()
        msg, _ = capture(ss.warn_if_stale, script, registry=nomani)
        check(msg is None, "a checkout with no marketplace.json is silent")

        weird = make_checkout(rootp / "weird", "planning", "not-a-version")
        wreg = make_registry(rootp / "weird.yaml", "coder-plugins", weird)
        msg, _ = capture(ss.warn_if_stale, script, registry=wreg)
        check(msg is None, "an unparseable manifest version is silent, never a guess")

        os.environ["PORTFOLIO_NO_STALE_WARNING"] = "1"
        try:
            err = io.StringIO()          # not capture(): that clears the variable
            with redirect_stderr(err):
                msg = ss.warn_if_stale(script, registry=reg)
            check(msg is None and err.getvalue() == "",
                  "PORTFOLIO_NO_STALE_WARNING silences a genuine warning")
        finally:
            os.environ.pop("PORTFOLIO_NO_STALE_WARNING", None)

        # Teeth for the whole silence block: with the env var gone and a good
        # registry, the SAME inputs must warn — otherwise every check above
        # could be passing because the probe is simply dead.
        msg, _ = capture(ss.warn_if_stale, script, registry=reg)
        check(msg is not None,
              "...and with it unset the same call warns — the silences are guards, "
              "not a dead probe")


# --------------------------------------------------------------------------
def dedupe_cases():
    """One user invocation, one warning — across process boundaries.

    portfolio-rebuild spawns security-scan, security-rollup, business-scan and
    business-rollup; compass-scan spawns business-scan. Of those, the two SECURITY
    scripts carry this probe (the business pair does not — see _staleness.py, it is
    a recorded gap, not a covered case), so without suppression a single
    `portfolio rebuild` from a stale cache printed the identical line three times:
    itself plus those two. The mechanism is an inherited env var, so it has to be
    tested across a real fork, not just within one process.
    """
    print("dedupe — one invocation warns once, children stay quiet:")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        checkout = make_checkout(rootp / "checkout", "planning", "0.44.0")
        reg = make_registry(rootp / "registry.yaml", "coder-plugins", checkout)
        script = cached_script(rootp, "planning", "0.43.1")

        first, err1 = capture(ss.warn_if_stale, script, registry=reg)
        err2 = io.StringIO()
        with redirect_stderr(err2):      # deliberately NOT capture(): keep the state
            second = ss.warn_if_stale(script, registry=reg)
        check(first is not None and second is None and err2.getvalue() == "",
              "a second call in the same process is silent — having warned sets the flag")
        check(os.environ.get("PORTFOLIO_NO_STALE_WARNING") == "1",
              "...via the env var children inherit, not a module-local flag")
        os.environ.pop("PORTFOLIO_NO_STALE_WARNING", None)

        # Across a real process boundary: parent warns, then spawns a child that
        # runs the same probe on the same stale path.
        home = rootp / "home"
        (home / ".claude").mkdir(parents=True)
        make_registry(home / ".claude" / "projects-registry.yaml",
                      "coder-plugins", checkout)
        cache = (rootp / "plugins" / "cache" / "coder-plugins" / "planning"
                 / "0.43.1" / "skills" / "portfolio" / "scripts")
        shutil.copytree(SCRIPTS, cache, ignore=shutil.ignore_patterns("__pycache__"))
        driver = rootp / "driver.py"
        driver.write_text(
            "import subprocess, sys, importlib.util\n"
            f"spec = importlib.util.spec_from_file_location('_s', {str(cache / '_staleness.py')!r})\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            f"got = m.warn_if_stale({str(cache / 'portfolio-unify.py')!r})\n"
            "print('PARENT-WARNED' if got else 'PARENT-SILENT', file=sys.stderr)\n"
            f"subprocess.run([sys.executable, {str(cache / 'security-scan.py')!r}],\n"
            "               stdin=subprocess.DEVNULL)\n")
        env = dict(os.environ, HOME=str(home))
        env.pop("PORTFOLIO_NO_STALE_WARNING", None)
        r = subprocess.run([sys.executable, str(driver)], env=env,
                           capture_output=True, text=True, timeout=120,
                               stdin=subprocess.DEVNULL)
        check("PARENT-WARNED" in r.stderr and r.stderr.count("warning: running") == 1,
              f"a parent that warned silences the child it spawns — and the one "
              f"line is the PARENT's, not a silent parent plus a loud child "
              f"(parent={'warned' if 'PARENT-WARNED' in r.stderr else 'silent'}, "
              f"lines={r.stderr.count('warning: running')})")

        # Teeth: without the parent's warn, the child warns on its own — so the
        # count above is suppression, not a child that never had the probe.
        driver.write_text(
            "import subprocess, sys\n"
            f"subprocess.run([sys.executable, {str(cache / 'security-scan.py')!r}],\n"
            "               stdin=subprocess.DEVNULL)\n")
        r = subprocess.run([sys.executable, str(driver)], env=env,
                           capture_output=True, text=True, timeout=120,
                               stdin=subprocess.DEVNULL)
        check(r.stderr.count("warning: running") == 1,
              "...and an unsuppressed child warns by itself — the probe is live in it")


# --------------------------------------------------------------------------
# Every entry point that should carry the probe. Kept as a list so a new
# entry-point script fails the wiring sweep below until it is considered.
WIRED = [
    ("portfolio", "portfolio-unify.py"),
    ("portfolio", "portfolio-rebuild.py"),
    ("portfolio", "portfolio-integrate.py"),
    ("portfolio", "portfolio-migrate.py"),
    ("portfolio", "plan-status-audit.py"),
    ("portfolio", "security-scan.py"),
    ("portfolio", "security-rollup.py"),
    ("compass", "compass-scan.py"),
    ("decisions", "decisions-relevant.py"),
]


def wiring_case():
    """Drive a REAL script from a REAL cache-shaped tree, as a subprocess.

    This is the half that cannot be faked. `helper_cases()` proves the function
    behaves; only this proves anything calls it. The scripts are copied into a
    cache-shaped path with HOME redirected, so the registry lookup resolves to a
    fixture — no dependence on the operator's own registry or vault.

    Each script is run with no arguments. Every one of them fails shortly after
    (unconfigured vault, or a required argument), which is deliberate and is the
    point: the probe runs FIRST in main(), so the warning must appear even on a
    run that goes on to refuse. A warning that only survived a fully successful
    run would be untested on every path an operator actually hits when something
    is wrong.
    """
    print("wiring — the probe is reached from the real entry points:")
    with tempfile.TemporaryDirectory() as root:
        rootp = Path(root)
        home = rootp / "home"
        (home / ".claude").mkdir(parents=True)
        checkout = make_checkout(rootp / "checkout", "planning", "0.44.0")
        make_registry(home / ".claude" / "projects-registry.yaml",
                      "coder-plugins", checkout)

        cache = (rootp / "plugins" / "cache" / "coder-plugins" / "planning"
                 / "0.43.1" / "skills")
        # Copy whatever WIRED names, not a hardcoded pair — otherwise adding an
        # entry point in a new skill silently fails the fixture rather than the
        # thing under test, which is how a wiring test starts reporting on itself.
        for skill in sorted({s for s, _ in WIRED}):
            shutil.copytree(ROOT / "planning" / "skills" / skill / "scripts",
                            cache / skill / "scripts",
                            ignore=shutil.ignore_patterns("__pycache__"))

        env = dict(os.environ, HOME=str(home))
        env.pop("PORTFOLIO_NO_STALE_WARNING", None)
        for skill, name in WIRED:
            target = cache / skill / "scripts" / name
            check(target.exists(), f"{name}: copied into the cache tree")
            r = subprocess.run([sys.executable, str(target)], env=env,
                               capture_output=True, text=True, timeout=120,
                               stdin=subprocess.DEVNULL)
            check("0.43.1" in r.stderr and "0.44.0" in r.stderr,
                  f"{name}: warns from a stale cache, even on a run that then refuses")
            check("0.44.0" not in r.stdout,
                  f"{name}: ...on stderr, never stdout (stdout is parsed JSON for some)")

        # Teeth: same tree, same scripts, cache version EQUAL to the checkout's.
        # If these still "warn", the assertions above are matching something else.
        fresh = (rootp / "plugins" / "cache" / "coder-plugins" / "planning"
                 / "0.44.0" / "skills")
        for skill in sorted({s for s, _ in WIRED}):
            shutil.copytree(ROOT / "planning" / "skills" / skill / "scripts",
                            fresh / skill / "scripts",
                            ignore=shutil.ignore_patterns("__pycache__"))
        quiet = True
        for skill, name in WIRED:
            r = subprocess.run([sys.executable, str(fresh / skill / "scripts" / name)],
                               env=env, capture_output=True, text=True, timeout=120,
                               stdin=subprocess.DEVNULL)
            if "warning: running" in r.stderr:
                quiet = False
        check(quiet, "an up-to-date cache warns from none of them — the wiring "
                     "checks above are reading the probe, not noise")


def wiring_sweep():
    """No entry point quietly skips the probe.

    A script gains a main() and ships without the warning: nothing else in this
    suite would notice, because every case above enumerates WIRED by hand. This
    compares that list against what is actually on disk.
    """
    print("wiring sweep — every entry point is listed and every listed one calls it:")
    # Swept across EVERY skill in the planning plugin, not just the two this task
    # named, and matching `def main(` rather than the exact `def main():` — the
    # earlier form was blind on both counts at once, and `decisions-relevant.py`
    # (a third directory, and `def main(argv=None):`) sat in the gap: same plugin,
    # same per-version cache tree, reads the vault, carries no probe.
    found = set()
    for d in sorted((ROOT / "planning" / "skills").glob("*/scripts")):
        skill = d.parent.name
        for p in sorted(d.glob("*.py")):
            if p.name.startswith("_"):
                continue                     # helper module, not an entry point
            text = p.read_text(encoding="utf-8", errors="replace")
            if re.search(r"^def main\(", text, re.M):
                found.add((skill, p.name))
    # Considered and deliberately NOT wired, each with its reason. An entry point
    # is in exactly one of these two tables — that is what makes the sweep a
    # decision record rather than a list of whatever happened to get wired.
    not_wired = {
        ("executing-plans", "plan-progress.py"):
            "statusline renderer — runs on EVERY prompt render; a warning there is "
            "noise on every keystroke, and this script already diverges deliberately "
            "on the vault refusal for the same reason",
        ("executing-plans", "statusline-install.py"):
            "one-shot installer, run by hand from a checkout",
        ("planning-projects", "validate-gate-checks.py"):
            "validator: takes plan paths, reports on them, reads no vault state",
        ("dispatching-parallel-agents", "validate-stack-routing.py"):
            "validator over in-repo routing tables; no vault, no cache-sensitive output",
        ("applying-design-handoff", "validate-handoff-pack.py"):
            "validator over a handoff pack path; no vault",
        ("project-maturity", "audit-detectors.py"):
            "detector library run against a repo path; no vault",
    }
    listed = set(WIRED) | set(not_wired)
    check(not (found - listed),
          f"no unlisted entry point (unlisted: {sorted(found - listed) or 'none'})")
    check(not (listed - found),
          f"no stale listing (gone: {sorted(listed - found) or 'none'})")
    missing = []
    for skill, name in sorted(set(WIRED) & found):
        text = (ROOT / "planning" / "skills" / skill / "scripts"
                / name).read_text(encoding="utf-8", errors="replace")
        if "warn_if_stale" not in text:
            missing.append(name)
    check(not missing, f"every entry point calls warn_if_stale (missing: {missing or 'none'})")


def main():
    helper_cases()
    dedupe_cases()
    wiring_case()
    wiring_sweep()
    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
