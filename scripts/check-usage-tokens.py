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
    **`<name>`**       -> any component of any type, or a plugin name

That last form matters because agents are never slash-invocable, so a renamed or
deleted agent is invisible to the slash-token sweep. The file's convention is to
emphasise a named thing as ``**`name`**`` — used for agents (`ui-android`), skills
(`capability-router`) and plugins (`loadout`) alike — so all three resolve here.

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

    # A slash token is only a command when the "/" begins a word — at line start,
    # after whitespace, or after a backtick — and is not itself a path segment
    # (nothing may follow the name that continues a path). Without this, path
    # fragments like ~/dev/, <repo>/docs/ and ./foo.md all look like commands.
    START = r"(?:(?<=^)|(?<=\s)|(?<=`))"

    # /plugin:component
    for plugin, name in re.findall(START + r"/([a-z0-9-]+):([a-z0-9-]+)\b(?!/)",
                                   text, re.MULTILINE):
        checked.append(f"/{plugin}:{name}")
        if plugin not in plugins:
            unresolved.append(f"/{plugin}:{name} — no such plugin '{plugin}'")
        elif not resolve_qualified(plugin, name):
            unresolved.append(
                f"/{plugin}:{name} — no {plugin}/skills/{name}/SKILL.md "
                f"and no {plugin}/commands/{name}.md")

    # bare /command (no colon, so not the qualified form above)
    for name in re.findall(START + r"/([a-z0-9-]+)(?![:\w/-])", text, re.MULTILINE):
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

    # **`name`** — the emphasised-component form. Agents appear only this way
    # (they are not slash-invocable), so without this an agent rename ships silently.
    for name in re.findall(r"\*\*`([a-z0-9-]+)`\*\*", text):
        checked.append(f"**`{name}`**")
        if not resolve_any_component(name, plugins):
            unresolved.append(
                f"**`{name}`** — not a plugin, and no skills/{name}/SKILL.md, "
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
