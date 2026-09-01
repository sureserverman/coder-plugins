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
import json
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
    mod.INDEX = pathlib.Path(repo) / "capability-index.json"
    return mod


def write(path, text=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# The synthetic marketplace every fixture resolves against. Mirrors the real
# capability-index.json shape (components[].{name,kind,plugin,path}) because that is
# now the guard's resolution source: a fixture that only built a TREE would exercise
# a code path the guard no longer has.
FIXTURE_COMPONENTS = [
    {"name": "do-thing", "kind": "skill", "plugin": "alpha",
     "path": "alpha/skills/do-thing/SKILL.md"},
    {"name": "run-thing", "kind": "command", "plugin": "alpha",
     "path": "alpha/commands/run-thing.md"},
    {"name": "thing-expert", "kind": "agent", "plugin": "alpha",
     "path": "alpha/agents/thing-expert.md"},
    # Lives in beta, NOT alpha — the fixture that makes mis-attribution detectable.
    {"name": "beta-only", "kind": "agent", "plugin": "beta",
     "path": "beta/agents/beta-only.md"},
]


def fixture(root, usage_text, components=None, index_text=None):
    """A three-plugin marketplace: alpha, beta, loadout (profiles)."""
    write(f"{root}/alpha/.claude-plugin/plugin.json", '{"name":"alpha"}')
    write(f"{root}/alpha/skills/do-thing/SKILL.md", "# do-thing")
    write(f"{root}/alpha/commands/run-thing.md", "# run-thing")
    write(f"{root}/alpha/agents/thing-expert.md", "# thing-expert")
    write(f"{root}/beta/.claude-plugin/plugin.json", '{"name":"beta"}')
    write(f"{root}/beta/agents/beta-only.md", "# beta-only")
    write(f"{root}/loadout/.claude-plugin/plugin.json", '{"name":"loadout"}')
    write(f"{root}/loadout/profiles/tech/rust.json", "{}")
    write(f"{root}/loadout/profiles/task/release.json", "{}")
    write(f"{root}/docs/USAGE.md", usage_text)
    if index_text is None:
        comps = FIXTURE_COMPONENTS if components is None else components
        # loadout owns no components but must be a known plugin, or the staleness
        # check below would fire on every fixture.
        comps = comps + [{"name": "loadout-noop", "kind": "command",
                          "plugin": "loadout", "path": "loadout/commands/x.md"}]
        index_text = json.dumps({"schema": 1, "components": comps})
    write(f"{root}/capability-index.json", index_text)
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

print("group 3b — punctuation-adjacent tokens ARE extracted (BL-023)")
# The old lookbehind recognised a token only at line start, after whitespace, or
# after a backtick, so a token written directly after other punctuation was never
# extracted — and a fabrication in that position passed silently. Each positive
# below pairs a REAL token shape with a FABRICATED one: the real form must pass and
# the fabricated form must fail, which together prove the token is being read rather
# than merely tolerated.
for opener, closer, label in [("(", ")", "parentheses"),
                              ("[", "]", "square brackets"),
                              ("{", "}", "braces"),
                              ('"', '"', "double quotes"),
                              ("'", "'", "single quotes"),
                              ("*", "*", "markdown emphasis"),
                              ("|", "|", "table cell"),
                              (",", "", "comma"),
                              (";", "", "semicolon")]:
    check(run(f"See {opener}/alpha:do-thing{closer} here.\n") == 0,
          f"real token after {label} resolves")
    check(run(f"See {opener}/alpha:nope{closer} here.\n") == 1,
          f"FABRICATED token after {label} is caught")
check(run("Try [/loadout set rust] now.\n") == 0, "bracketed loadout profile resolves")
check(run("Try [/loadout set nosuch] now.\n") == 1, "bracketed BAD loadout profile is caught")

print("group 3b2 — tokens at every whitespace boundary, not just offset 0")
# The bug this group exists for: the first tokenizer enumerated space and tab but
# not newline, so every token beginning a LINE stopped being checked — 31 of 89 on
# the real file — while every fixture above still passed, because a fixture token
# sits at offset 0 where the i==0 branch carries it. A positive-only test at offset
# 0 cannot see this class at all.
check(run("Intro line.\n/alpha:nope\n") == 1, "fabrication at the start of a LATER line is caught")
check(run("Intro line.\n/alpha:do-thing\n") == 0, "real token at the start of a later line resolves")
check(run("Intro.\r\n/alpha:nope\r\n") == 1, "fabrication after a CRLF line break is caught")
check(run("a\t/alpha:nope\n") == 1, "fabrication after a tab is caught")
check(run("a  /alpha:nope\n") == 1, "fabrication after a space is caught")

print("group 3c — widening the boundary did not readmit path fragments")
# These are the regression risk, not the positives above: every one of them sits
# directly before a "/" and must still be rejected as a path, not a token.
for frag in ["Clone into ~/dev/coder-plugins today\n",
             "Artifacts land in <repo>/docs/workflows/ here\n",
             "See [the contract](./plugin-readme-contract.md)\n",
             "Run <plugin>/skills/decisions/scripts/x.py now\n",
             "Paths like a/b/c and x-y/z should be inert\n",
             "Version 1.2/3.4 is not a command\n"]:
    check(run("/run-thing\n" + frag) == 0, f"still no false positive: {frag.strip()[:40]}")

print("group 3d — attribution: WHICH plugin ships it (BL-024)")
TABLE = "| Task | Routes to | Shipped by |\n|---|---|---|\n| {} | `{}` | `{}` |\n"
check(run(TABLE.format("Thing", "thing-expert", "alpha")) == 0,
      "routing-table row with the CORRECT plugin passes")
check(run(TABLE.format("Thing", "thing-expert", "beta")) == 1,
      "routing-table row attributing a real component to the WRONG plugin FAILS")
check(run(TABLE.format("Beta", "beta-only", "beta")) == 0,
      "a component in the other plugin, correctly attributed, passes")
check(run(TABLE.format("Beta", "beta-only", "alpha")) == 1,
      "the same component mis-attributed to alpha FAILS")
check(run("Route via `thing-expert` (an `alpha` agent) here.\n") == 0,
      "prose attribution with the correct plugin passes")
check(run("Route via `thing-expert` (a `beta` agent) here.\n") == 1,
      "prose attribution with the WRONG plugin FAILS")
check(run("Route via `beta-only` (an alpha agent) here.\n") == 1,
      "unbackticked prose attribution is checked too")
# The qualified slash form is now attribution-checked by the same index lookup.
check(run("/beta:beta-only\n") == 0, "qualified token matching its real plugin resolves")
check(run("/alpha:beta-only\n") == 1, "qualified token naming the wrong plugin FAILS")
# A table whose last cell is a real component but NOT a plugin must contribute no
# attribution claims — otherwise every 3-column table in the doc becomes noise. Uses
# `do-thing` (a real skill) so the existence sweep stays green and this case isolates
# the attribution rule rather than accidentally testing resolution.
check(run("/run-thing\n| a | `thing-expert` | `do-thing` |\n") == 0,
      "a 3-column table whose last cell is a component, not a plugin, generates no claims")

print("group 3d2 — attribution heuristics must not misfire on ordinary prose")
# Reproduced by a Tier-2 review: the prose branch captured whatever word preceded the
# kind-noun, so plain English yielded a claim against a plugin named "internal" and
# failed a perfectly correct doc. Both branches now require a KNOWN plugin.
for phrase in ["Use `thing-expert` (an internal agent) for this.\n",
               "Use `thing-expert` (a legacy command) for this.\n",
               "Use `do-thing` (the primary skill) here.\n"]:
    check(run("/run-thing\n" + phrase) == 0,
          f"ordinary prose is not an attribution claim: {phrase.strip()[:44]}")
check(run("Use `thing-expert` (a `beta` agent) for this.\n") == 1,
      "but a KNOWN plugin in the same position is still checked")
# The table rule matches the routing table's real 3-cell shape; a 2-column row whose
# last cell happens to name a real plugin must not become an attribution claim.
check(run("/run-thing\n| `thing-expert` | `beta` |\n") == 0,
      "a two-column row is not read as an attribution claim")
check(run("| Task | `thing-expert` | `beta` |\n") == 1,
      "a three-column row still is")

print("group 3c2 — single-segment absolute paths in the new openers")
# The widened opener set newly tokenizes /etc, /tmp, /var when wrapped. It fails SAFE
# (a spurious FAIL, never a silent pass), but shipped with zero coverage.
for frag in ["Logs land in (/tmp) during the run\n",
             "Config lives in [/etc] on this host\n",
             "State is under '/var' here\n"]:
    rc = run("/run-thing\n" + frag)
    check(rc == 1, f"single-segment path in a new opener fails LOUD, not silent: {frag.strip()[:40]}")

print("group 3e — the guard refuses to pass when it cannot resolve")


def run_with_index(usage_text, index_text):
    with tempfile.TemporaryDirectory() as root:
        mod = fixture(root, usage_text, index_text=index_text)
        with contextlib.redirect_stdout(io.StringIO()):
            return mod.main()


for label, bad_index in [("absent", None),
                         ("malformed JSON", "{not json"),
                         ("no components key", '{"schema":1}'),
                         ("empty components", '{"schema":1,"components":[]}')]:
    try:
        if bad_index is None:
            with tempfile.TemporaryDirectory() as root:
                mod = fixture(root, "/alpha:do-thing\n")
                os.remove(f"{root}/capability-index.json")
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = mod.main()
            check(False, f"an {label} index should refuse, got rc={rc}")
        else:
            rc = run_with_index("/alpha:do-thing\n", bad_index)
            check(False, f"an index with {label} should refuse, got rc={rc}")
    except SystemExit as exc:
        check(exc.code != 0, f"an index that is {label} exits non-zero rather than passing")
# A plugin on disk but missing from the index means STALE — the guard must say so
# rather than reporting every component it ships as a fabrication in USAGE.md.
try:
    rc = run_with_index("/alpha:do-thing\n", json.dumps(
        {"schema": 1, "components": [c for c in FIXTURE_COMPONENTS
                                     if c["plugin"] != "beta"]}))
    check(False, f"a stale index should refuse, got rc={rc}")
except SystemExit as exc:
    check("stale" in str(exc.code), "a plugin missing from the index is reported as STALE")

print("group 6 — a token after an em-dash is extracted (BL-033)")
# TOKEN_START_PUNCT enumerated quotes and brackets but no dash, so a fabrication
# written directly after ordinary sentence punctuation was never extracted at all.
check(run("Use the router \u2014 /alpha:do-thing picks it up.\n") == 0,
      "a real token after an em-dash still resolves")
check(run("Use the router \u2014 /alpha:ghost-skill picks it up.\n") == 1,
      "a FABRICATION after an em-dash is caught (was silently unextracted)")
check(run("Use the router \u2013 /alpha:ghost-skill picks it up.\n") == 1,
      "same for an en-dash")
check(run("A code-review token keeps its hyphen: /alpha:do-thing\n") == 0,
      "a hyphen is not a token boundary — component names contain them")

print("group 7 — USAGE.md's purpose statement matches its flows (BL-029)")
CROSS = "## 1. Cross\n\nRun `/alpha:do-thing` then ask `beta-only`.\n"
SINGLE = "## 2. Single\n\nRun `/alpha:do-thing` and `/alpha:run-thing`.\n"

check(run(CROSS) == 0, "a cross-plugin flow with no claim to check passes")
check(run(CROSS + SINGLE) == 1,
      "a single-plugin flow the purpose statement does not admit FAILS")
check(run("**flow 2** is a layer.\n\n" + CROSS + SINGLE) == 0,
      "admitting it in the purpose statement clears it")
check(run("**flow 1** is a layer.\n\n" + CROSS + SINGLE) == 1,
      "admitting the WRONG flow does not clear it")
check(run("**flow 1** is a layer.\n\n" + CROSS) == 1,
      "a flow admitted as single-plugin that actually spans two FAILS")
check(run("**flow 3** is a layer.\n\nProse only, `/alpha:do-thing`.\n") == 1,
      "a claim with no numbered flow behind it is a broken extraction, not a pass")

# The property that keeps this from being silenced: deleting the sentence must
# make the guard fire, not fall quiet.
check(run("**flow 2** is a layer.\n\n" + CROSS + SINGLE) == 0
      and run(CROSS + SINGLE) == 1,
      "removing the purpose statement makes the guard FIRE, never go silent")

# The treadmill guard: adding an ordinary cross-plugin flow must not turn it red,
# or someone starts hand-editing numbers back in every time the doc grows.
check(run(CROSS + "## 3. Another cross\n\n`/alpha:run-thing` and `beta-only`.\n") == 0,
      "adding a normal cross-plugin flow needs no edit to the purpose statement")

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
