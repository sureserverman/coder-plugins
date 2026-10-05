#!/usr/bin/env python3
"""Fixture tests for loadout/scripts/loadout.py.

Runs the script as a subprocess against a temp HOME and project, so nothing on
the host is read or written. Asserts the pin rule (DEC-030): a local `true` makes
Claude Code pin the plugin's version in a local install record that nothing
refreshes, so loadout writes `true` only for a plugin user settings leave off,
and says so. Stdlib only.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent / "loadout.py"
BUNDLED_ALWAYS_ON = json.loads(
    (HERE.parent.parent / "profiles" / "always-on.json").read_text()
)["plugins"]

FAILURES = []


def check(cond, msg):
    if cond:
        print(f"  ok: {msg}")
    else:
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


USER_OFF = "android-dev@coder-plugins"  # in the loadout, off in user settings
NO_USER_INSTALL = "lsp@official"  # in the loadout, on in user settings, installed only locally
USER_ON = "rust-dev@coder-plugins"  # in the loadout, on in user settings
NOT_IN_LOADOUT = "other@market"  # installed, outside the loadout


def fixture(root):
    """A HOME and a project. User settings enable every always-on plugin and
    USER_ON, and turn USER_OFF off. The `fixture` tech profile adds USER_OFF and
    USER_ON to the loadout."""
    home = root / "home"
    project = root / "project"
    user_enabled = {k: True for k in BUNDLED_ALWAYS_ON}
    user_enabled[USER_ON] = True
    user_enabled[USER_OFF] = False
    write(home / ".claude" / "settings.json", {"enabledPlugins": user_enabled})
    installed = {k: [{"scope": "user", "version": "1.0.0"}] for k in user_enabled}
    installed[NOT_IN_LOADOUT] = [{"scope": "user", "version": "1.0.0"}]
    user_enabled[NO_USER_INSTALL] = True
    installed[NO_USER_INSTALL] = [{"scope": "local", "projectPath": "/elsewhere", "version": "1.0.0"}]
    write(home / ".claude" / "settings.json", {"enabledPlugins": user_enabled})
    write(home / ".claude" / "plugins" / "installed_plugins.json",
          {"version": 2, "plugins": installed})
    write(home / ".claude" / "loadouts" / "tech" / "fixture.json",
          {"plugins": [USER_OFF, USER_ON, NO_USER_INSTALL]})
    # A map an older loadout wrote: explicit `true` for user-enabled plugins.
    write(project / ".claude" / "settings.local.json",
          {"enabledPlugins": {"planning@coder-plugins": True, USER_ON: True},
           "keep": 1})
    return home, project


def run(home, project, *args, path=None):
    env = {"HOME": str(home), "CLAUDE_PROJECT_DIR": str(project),
           "PATH": path or os.environ.get("PATH", "")}
    return subprocess.run([sys.executable, str(SCRIPT), *args], env=env,
                          capture_output=True, text=True)


def test_writes_false_only():
    print("set: a user-enabled plugin is omitted, never written true")
    with tempfile.TemporaryDirectory() as tmp:
        home, project = fixture(pathlib.Path(tmp))
        r = run(home, project, "set", "fixture")
        check(r.returncode == 0, f"set exits 0 (got {r.returncode}: {r.stderr.strip()})")
        local = json.loads((project / ".claude" / "settings.local.json").read_text())
        written = local.get("enabledPlugins", {})
        user_on_union = set(BUNDLED_ALWAYS_ON) | {USER_ON}
        # (a) and (d): no user-enabled union plugin is written true, including
        # the two the old map carried.
        stray = sorted(k for k in user_on_union if written.get(k) is True)
        check(not stray, f"no true for user-enabled loadout plugins (found {stray})")
        check(not (user_on_union & written.keys()),
              f"user-enabled loadout plugins are omitted (found {sorted(user_on_union & written.keys())})")
        # (b) every installed plugin outside the loadout is false.
        check(written.get(NOT_IN_LOADOUT) is False, f"{NOT_IN_LOADOUT} is false")
        # (c) a loadout plugin user settings leave off is true, and loadout says it pins.
        check(written.get(USER_OFF) is True, f"{USER_OFF} is true")
        check(f"loadout: {USER_OFF} is off in user settings; enabling it here pins its version"
              in r.stderr, "the pin warning names the plugin")
        check(USER_ON not in r.stderr, "no pin warning for a user-enabled plugin")
        # A user setting is not enough: with no user-scope install there is
        # nothing to load, so omitting the plugin would drop it.
        check(written.get(NO_USER_INSTALL) is True,
              f"{NO_USER_INSTALL} (on in user settings, no user install) is true")
        check(f"loadout: {NO_USER_INSTALL} has no user-scope install; enabling it here pins its version"
              in r.stderr, "the pin warning says there is no user-scope install")
        check(local.get("keep") == 1, "other settings.local.json keys survive")
        # show still lists the whole loadout as enabled.
        check(f"+ {USER_ON}" in r.stdout and "+ planning@coder-plugins" in r.stdout,
              "show lists omitted loadout plugins as enabled")
        check(f"- {NOT_IN_LOADOUT}" in r.stdout, "show lists the false plugin as disabled")


LOCAL_ONLY = "local-only@market"  # pinned here, no user-scope install at all


def unpin_fixture(root, fail_key=None):
    """The fixture above, plus local records for this project (two redundant,
    one local-only), a record for another project, and a fake `claude` that
    logs `<cwd> <argv>` and fails for `fail_key`."""
    home, project = fixture(root)
    plugins_file = home / ".claude" / "plugins" / "installed_plugins.json"
    data = json.loads(plugins_file.read_text())
    for key in ("planning@coder-plugins", USER_ON):
        data["plugins"][key].append(
            {"scope": "local", "projectPath": str(project), "version": "0.1.0"})
    data["plugins"][LOCAL_ONLY] = [
        {"scope": "local", "projectPath": str(project), "version": "0.1.0"}]
    data["plugins"]["git-github@coder-plugins"].append(
        {"scope": "local", "projectPath": str(root / "elsewhere"), "version": "0.1.0"})
    write(plugins_file, data)
    write(project / ".claude" / "loadout.json", {"tech": "fixture", "task_overlays": []})
    log = root / "claude.log"
    bin_dir = root / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "claude"
    fake.write_text("#!/bin/sh\n"
                    f'echo "$PWD $*" >> "{log}"\n'
                    f'[ "$3" = "{fail_key or "-"}" ] && exit 3\n'
                    "exit 0\n")
    fake.chmod(0o755)
    path = f"{bin_dir}:{os.environ.get('PATH', '')}"
    return home, project, log, path


def calls(log):
    return log.read_text().splitlines() if log.exists() else []


def test_unpin():
    print("unpin: uninstalls exactly the redundant local records, then re-applies")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        home, project, log, path = unpin_fixture(root)
        r = run(home, project, "unpin", path=path)
        check(r.returncode == 0, f"unpin exits 0 (got {r.returncode}: {r.stderr.strip()})")
        got = sorted(calls(log))
        want = sorted(f"{project} plugin uninstall {k} --scope local"
                      for k in ("planning@coder-plugins", USER_ON))
        check(got == want, f"uninstall called for exactly the redundant keys, from the project (got {got})")
        check(LOCAL_ONLY in r.stdout and "kept" in r.stdout,
              "a local-only record is kept and listed")
        written = json.loads((project / ".claude" / "settings.local.json").read_text())
        check(written["enabledPlugins"].get(USER_ON) is None,
              "the loadout is re-applied afterwards (no stale true left)")


def test_unpin_dry_run():
    print("unpin --dry-run: lists, calls nothing, writes nothing")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        home, project, log, path = unpin_fixture(root)
        before = (project / ".claude" / "settings.local.json").read_text()
        r = run(home, project, "unpin", "--dry-run", path=path)
        check(r.returncode == 0, f"dry run exits 0 (got {r.returncode})")
        check(calls(log) == [], f"dry run calls nothing (got {calls(log)})")
        check(USER_ON in r.stdout and "planning@coder-plugins" in r.stdout,
              "dry run lists the redundant keys")
        check((project / ".claude" / "settings.local.json").read_text() == before,
              "dry run leaves settings.local.json alone")


def test_unpin_failure():
    print("unpin: a failing uninstall is reported and exits 1")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        home, project, log, path = unpin_fixture(root, fail_key=USER_ON)
        r = run(home, project, "unpin", path=path)
        check(r.returncode == 1, f"exit 1 on a failed uninstall (got {r.returncode})")
        check(USER_ON in r.stderr, "the failing key is named on stderr")
        check(len(calls(log)) == 2, f"the other uninstall still ran (got {calls(log)})")


def test_unpin_keeps_user_off():
    print("unpin: a record whose user-scope install is off in user settings is kept")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        home, project, log, path = unpin_fixture(root)
        plugins_file = home / ".claude" / "plugins" / "installed_plugins.json"
        data = json.loads(plugins_file.read_text())
        # USER_OFF has a user-scope install but user settings turn it off: the
        # local record is the only thing loading it here.
        data["plugins"][USER_OFF].append(
            {"scope": "local", "projectPath": str(project), "version": "0.1.0"})
        write(plugins_file, data)
        r = run(home, project, "unpin", path=path)
        check(not any(USER_OFF in c for c in calls(log)),
              f"{USER_OFF} is not uninstalled (got {calls(log)})")
        check(f"kept (off in user settings): {USER_OFF}" in r.stdout,
              "it is listed as kept, with the reason")


def test_unpin_without_state():
    print("unpin with no loadout.json: the unpinned keys' local true is dropped")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        home, project, log, path = unpin_fixture(root)
        (project / ".claude" / "loadout.json").unlink()
        r = run(home, project, "unpin", path=path)
        check(r.returncode == 0, f"exits 0 (got {r.returncode}: {r.stderr.strip()})")
        local = json.loads((project / ".claude" / "settings.local.json").read_text())
        ep = local.get("enabledPlugins", {})
        check(ep.get("planning@coder-plugins") is None and ep.get(USER_ON) is None,
              f"no true left for the unpinned keys (got {ep})")
        check(not (project / ".claude" / "loadout.json").exists(),
              "no loadout.json is created")
        check(local.get("keep") == 1, "other keys survive")


def test_unpin_rejects_unknown_flag():
    print("unpin: an unknown argument is refused before anything runs")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        home, project, log, path = unpin_fixture(root)
        r = run(home, project, "unpin", "--dryrun", path=path)
        check(r.returncode == 2, f"exit 2 (got {r.returncode})")
        check(calls(log) == [], f"nothing uninstalled (got {calls(log)})")


def test_unpin_missing_claude():
    print("unpin: no claude on PATH is a reported failure, not a traceback")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        home, project, log, path = unpin_fixture(root)
        r = run(home, project, "unpin", path=str(root / "empty-bin"))
        check(r.returncode == 1, f"exit 1 (got {r.returncode})")
        check("Traceback" not in r.stderr and "planning@coder-plugins" in r.stderr,
              "the failing keys are named, with no traceback")


TESTS = [test_writes_false_only, test_unpin, test_unpin_dry_run, test_unpin_failure,
         test_unpin_keeps_user_off, test_unpin_without_state,
         test_unpin_rejects_unknown_flag, test_unpin_missing_claude]

if __name__ == "__main__":
    for t in TESTS:
        t()
    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s)")
        sys.exit(1)
    print("\nall loadout tests passed")
