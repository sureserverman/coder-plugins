#!/usr/bin/env python3
"""Assert every component docs/USAGE.md names actually exists on disk.

USAGE.md is the one doc that spans plugins, so it is the easiest place to name a
skill that was renamed, or one that never existed. Both have shipped in it before:
a fabricated `/loadout tech` and a stale `/rust-review`. This guard resolves every
`/plugin:component` and bare `/command` token it mentions, plus the `/loadout set
<profile>` and `/loadout add <profile>` arguments, against the tree.

Resolution targets:
    /<plugin>:<name>   -> <plugin>/{skills/<name>/SKILL.md,commands/<name>.md}
    /<name>            -> any <plugin>/commands/<name>.md   (bare command form)
    /loadout set X     -> loadout/profiles/tech/X.json
    /loadout add X     -> loadout/profiles/task/X.json
    `<name>`           -> any component of any type, or a plugin name
    **`<name>`**       -> same (the emphasised form is just bolded)

The backtick forms matter because agents are never slash-invocable: of the 15 agent
names this file mentions, only 4 use the emphasised form, so sweeping slash tokens
and bold tokens alone left 11 agents plus every skill and plugin mention unchecked.
Any lowercase-kebab backticked word is treated as a component reference — measured
against the real file, 53 of 54 such tokens are components, and the one that isn't
is allow-listed below. Tokens with a dot, slash, underscore or capital (`stack-routing.md`,
`docs/USAGE.md`, `vault_dir`, `APK_DIR`, `DEC-NNN`) are not component-shaped and are
skipped, which is what keeps the false-positive rate at zero.

Prints the number of tokens checked: an empty sweep must not read as a pass.

Usage: python3 scripts/check-usage-tokens.py   (exit 0 = every token resolves)
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
USAGE = REPO / "docs" / "USAGE.md"

# Slash tokens Claude Code itself provides, or that name a marketplace action
# rather than a component in this repo.
BUILTINS = {"plugin", "clear", "help", "config", "loadout"}

# Backticked lowercase-kebab words that are legitimately NOT components. Keep this
# list short and justified: each entry is a hole in the sweep, so prefer rewording
# the doc over adding one.
NON_COMPONENTS = {
    "promote",   # a `decisions` subcommand, not a component of its own
}


# Punctuation that may precede the "/" of a real component token, IN ADDITION to any
# whitespace. Deliberately an ALLOW-list of characters that cannot be part of a path,
# not a deny-list and not "any punctuation": widening it that way readmits
# `<repo>/docs/`, `~/dev/`, `./foo.md` and `<plugin>/skills/`, which are exactly the
# false positives this boundary exists to reject. Adding a character here means
# asserting it never appears mid-path.
#
# Whitespace is tested with str.isspace() rather than listed, because listing it is
# how the first cut of this dropped 31 of 89 tokens: it enumerated space and tab but
# not newline, silently un-checking every token that begins a line.
TOKEN_START_PUNCT = set("`([{\"'*|,;")


def token_starts(text, body):
    """Yield the group tuples of `body` matches whose "/" genuinely starts a token.

    Splitting the boundary decision out of the token-body regex is the point. The
    previous form folded both into one lookbehind that recognised only line-start,
    whitespace and backtick, so a token written directly after other punctuation —
    `(/planning:compass)`, `[/loadout set rust]` — was never extracted at all and a
    fabrication in that position passed silently.
    """
    for m in re.finditer(body, text, re.MULTILINE):
        i = m.start()
        if i == 0 or text[i - 1].isspace() or text[i - 1] in TOKEN_START_PUNCT:
            yield m.groups()


def plugin_dirs():
    return {p.name for p in REPO.iterdir()
            if p.is_dir() and (p / ".claude-plugin" / "plugin.json").exists()}


def resolve_qualified(plugin, name):
    return ((REPO / plugin / "skills" / name / "SKILL.md").exists()
            or (REPO / plugin / "commands" / f"{name}.md").exists())


def resolve_bare(name, plugins):
    return any((REPO / p / "commands" / f"{name}.md").exists() for p in plugins)


def resolve_any_component(name, plugins):
    """Any component of any type, in any plugin — or a plugin name itself."""
    if name in plugins:
        return True
    for p in plugins:
        if ((REPO / p / "skills" / name / "SKILL.md").exists()
                or (REPO / p / "agents" / f"{name}.md").exists()
                or (REPO / p / "commands" / f"{name}.md").exists()):
            return True
    return False


def main():
    if not USAGE.exists():
        sys.exit(f"FAIL: {USAGE} does not exist")
    text = USAGE.read_text()
    plugins = plugin_dirs()

    checked, unresolved = [], []

    # /plugin:component
    for plugin, name in token_starts(text, r"/([a-z0-9-]+):([a-z0-9-]+)\b(?!/)"):
        checked.append(f"/{plugin}:{name}")
        if plugin not in plugins:
            unresolved.append(f"/{plugin}:{name} — no such plugin '{plugin}'")
        elif not resolve_qualified(plugin, name):
            unresolved.append(
                f"/{plugin}:{name} — no {plugin}/skills/{name}/SKILL.md "
                f"and no {plugin}/commands/{name}.md")

    # bare /command (no colon, so not the qualified form above)
    for (name,) in token_starts(text, r"/([a-z0-9-]+)(?![:\w/-])"):
        if name in BUILTINS or name in plugins:
            continue
        checked.append(f"/{name}")
        if not resolve_bare(name, plugins):
            unresolved.append(f"/{name} — no <plugin>/commands/{name}.md anywhere")

    # /loadout set <tech> and /loadout add <task> name profile files, not components
    for verb, profile in re.findall(r"/loadout\s+(set|add)\s+([a-z0-9-]+)", text):
        kind = "tech" if verb == "set" else "task"
        checked.append(f"/loadout {verb} {profile}")
        if not (REPO / "loadout" / "profiles" / kind / f"{profile}.json").exists():
            unresolved.append(
                f"/loadout {verb} {profile} — no "
                f"loadout/profiles/{kind}/{profile}.json")

    # `name` (bolded or not) — the backtick-component form. Agents are never
    # slash-invocable and most are named only this way, so without this an agent
    # rename ships silently. Component-shaped means lowercase kebab: no dot, slash,
    # underscore or capital, which is what excludes file names and env vars.
    for name in set(re.findall(r"`([a-z][a-z0-9-]*)`", text)):
        if name in NON_COMPONENTS:
            continue
        checked.append(f"`{name}`")
        if not resolve_any_component(name, plugins):
            unresolved.append(
                f"`{name}` — not a plugin, and no skills/{name}/SKILL.md, "
                f"agents/{name}.md or commands/{name}.md in any plugin")

    if not checked:
        sys.exit("FAIL: swept 0 tokens — the extraction is broken, not the doc")

    if unresolved:
        print(f"FAIL: {len(unresolved)} of {len(checked)} token(s) do not resolve:")
        for u in unresolved:
            print(f"  {u}")
        return 1

    print(f"OK — {len(checked)} token(s) checked in docs/USAGE.md, all resolve "
          f"({len(set(checked))} distinct)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
