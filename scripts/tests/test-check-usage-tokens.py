#!/usr/bin/env python3
"""Fixture tests for scripts/check-usage-tokens.py.

Builds synthetic plugin trees plus a synthetic USAGE.md in temp dirs and asserts
the guard's contract: it resolves qualified slash tokens, bare commands, loadout
profile arguments and the emphasised-component form; it FAILS on each
corresponding fabrication; it does not false-positive on path fragments; and an
empty sweep is a failure rather than a pass. Stdlib only.
"""
import contextlib
import importlib.util
import io
import os
import pathlib
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "check-usage-tokens.py")

FAILURES = []


def check(cond, msg):
    if cond:
        print(f"  ok: {msg}")
    else:
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


def load(repo):
    """Import the guard fresh with REPO/USAGE pointed at a fixture tree."""
    spec = importlib.util.spec_from_file_location("usagetokens", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REPO = pathlib.Path(repo)
    mod.USAGE = pathlib.Path(repo) / "docs" / "USAGE.md"
    return mod


def write(path, text=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def fixture(root, usage_text):
    """A two-plugin marketplace: alpha (skill+command+agent), loadout (profiles)."""
    write(f"{root}/alpha/.claude-plugin/plugin.json", '{"name":"alpha"}')
    write(f"{root}/alpha/skills/do-thing/SKILL.md", "# do-thing")
    write(f"{root}/alpha/commands/run-thing.md", "# run-thing")
    write(f"{root}/alpha/agents/thing-expert.md", "# thing-expert")
    write(f"{root}/loadout/.claude-plugin/plugin.json", '{"name":"loadout"}')
    write(f"{root}/loadout/profiles/tech/rust.json", "{}")
    write(f"{root}/loadout/profiles/task/release.json", "{}")
    write(f"{root}/docs/USAGE.md", usage_text)
    return load(root)


def run(usage_text):
    """Return the guard's exit code, swallowing its own stdout.

    The guard prints "FAIL: ..." diagnostics by design; letting those through
    would litter a PASSING test run with the word FAIL and mislead anyone
    scanning CI output.
    """
    with tempfile.TemporaryDirectory() as root:
        mod = fixture(root, usage_text)
        with contextlib.redirect_stdout(io.StringIO()):
            return mod.main()


print("group 1 — valid references all resolve")
check(run("/alpha:do-thing\n") == 0, "qualified skill token resolves")
check(run("/alpha:run-thing\n") == 0, "qualified command token resolves")
check(run("/run-thing\n") == 0, "bare command token resolves")
check(run("/loadout set rust\n") == 0, "loadout tech profile resolves")
check(run("/loadout add release\n") == 0, "loadout task profile resolves")
check(run("Use **`thing-expert`** for this.\n") == 0, "emphasised agent resolves")
check(run("Use **`do-thing`** for this.\n") == 0, "emphasised skill resolves")
check(run("The **`loadout`** plugin.\n") == 0, "emphasised plugin name resolves")
check(run("Route to `thing-expert` for this.\n") == 0, "plain-backtick agent resolves")
check(run("The `alpha` plugin ships `do-thing`.\n") == 0, "plain-backtick plugin + skill resolve")

print("group 2 — every fabrication shape is caught")
check(run("/alpha:nope\n") == 1, "missing component in a real plugin fails")
check(run("/ghost:do-thing\n") == 1, "reference to a nonexistent plugin fails")
check(run("/never-existed\n") == 1, "bare command that resolves nowhere fails")
check(run("/loadout set nosuch\n") == 1, "missing tech profile fails")
check(run("/loadout add nosuch\n") == 1, "missing task profile fails")
check(run("Use **`ghost-expert`** here.\n") == 1, "emphasised nonexistent component fails")
check(run("Route to `ghost-expert` here.\n") == 1, "plain-backtick nonexistent component fails")
# The gap that shipped once: agents are usually named in PLAIN backticks, so a
# renamed agent must not slip through just because it lacks the bold form.
check(run("Route to `thing-experts` here.\n") == 1, "plain-backtick agent RENAME is caught")
# A skill referenced as though it were a command of the wrong plugin:
check(run("/loadout:do-thing\n") == 1, "component attributed to the wrong plugin fails")

print("group 3 — non-component text must not be mistaken for a reference")
for frag in ["Set `vault_dir` in ~/.claude/config.yaml\n",
             "Artifacts land in <repo>/docs/workflows/\n",
             "See [the contract](./plugin-readme-contract.md)\n",
             "Run <plugin>/skills/decisions/scripts/x.py\n",
             "It is I/O-bound work\n",
             # Backticked non-components: env vars (caps), files (dots),
             # snake_case and ID shapes must all be skipped, or the backtick
             # sweep would false-positive constantly.
             "Set `APK_DIR` and `SCREENSHOT_DIR` first\n",
             "See `stack-routing.md` and `plan-progress.json`\n",
             "Cite `ARCH-NN` and `DEC-NNN` on task lines\n",
             "Write `enabledPlugins` to settings\n"]:
    # Pair each fragment with one real token so the sweep is non-empty.
    check(run("/run-thing\n" + frag) == 0, f"no false positive: {frag.strip()[:38]}")

print("group 4 — an empty sweep is a failure, not a pass")
try:
    rc = run("Prose with no tokens at all.\n")
    check(False, f"empty sweep should exit nonzero via SystemExit (got rc={rc})")
except SystemExit as exc:
    check("swept 0 tokens" in str(exc.code), "empty sweep exits with the 0-token message")

print("group 5 — a missing USAGE.md is a failure")
try:
    with tempfile.TemporaryDirectory() as root:
        write(f"{root}/alpha/.claude-plugin/plugin.json", '{"name":"alpha"}')
        mod = load(root)
        mod.main()
    check(False, "missing USAGE.md should exit nonzero")
except SystemExit as exc:
    check("does not exist" in str(exc.code), "missing USAGE.md exits with a clear message")

print()
if FAILURES:
    print(f"FAILED — {len(FAILURES)} check(s):")
    for f in FAILURES:
        print(f"  {f}")
    sys.exit(1)
print("OK — check-usage-tokens.py resolves every valid form, catches every fabrication "
      "shape, ignores path fragments, and refuses an empty sweep")
