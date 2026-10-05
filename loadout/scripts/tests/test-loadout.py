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
    write(home / ".claude" / "plugins" / "installed_plugins.json",
          {"version": 2, "plugins": installed})
    write(home / ".claude" / "loadouts" / "tech" / "fixture.json",
          {"plugins": [USER_OFF, USER_ON]})
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
        check(local.get("keep") == 1, "other settings.local.json keys survive")
        # show still lists the whole loadout as enabled.
        check(f"+ {USER_ON}" in r.stdout and "+ planning@coder-plugins" in r.stdout,
              "show lists omitted loadout plugins as enabled")
        check(f"- {NOT_IN_LOADOUT}" in r.stdout, "show lists the false plugin as disabled")


TESTS = [test_writes_false_only]

if __name__ == "__main__":
    for t in TESTS:
        t()
    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s)")
        sys.exit(1)
    print("\nall loadout tests passed")
