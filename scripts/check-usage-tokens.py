#!/usr/bin/env python3
"""Assert every component docs/USAGE.md names exists AND is attributed to the right plugin.

USAGE.md is the one doc that spans plugins, so it is the easiest place to name a
skill that was renamed, or one that never existed. Both have shipped in it before:
a fabricated `/loadout tech` and a stale `/rust-review`. This guard resolves every
`/plugin:component` and bare `/command` token it mentions, plus the `/loadout set
<profile>` and `/loadout add <profile>` arguments.

Resolution is against capability-index.json, which carries a `plugin` field per
component, rather than a tree walk. (Two things still touch the filesystem, both
deliberately: the index-staleness check below, and `/loadout set|add` profiles, which
are not components and so are not in the index.) That is the difference between the two questions
this guard answers:

    existence    — does any plugin ship a component by this name?
    attribution  — does the plugin this doc CLAIMS ships it actually ship it?

Only existence was checked until BL-024. A tree walk cannot answer the second
question without re-deriving component discovery, which this file used to do in a
hand-rolled copy of the rule in scripts/build-capability-index.py. Resolving against
the index deletes that duplicate: discovery has one home, and a component moved
between plugins now fails here instead of passing silently.

Resolution targets:
    /<plugin>:<name>   -> index entry named <name> whose plugin IS <plugin>
    /<name>            -> index entry named <name> of kind "command" (bare form)
    /loadout set X     -> loadout/profiles/tech/X.json   (a profile, not a component)
    /loadout add X     -> loadout/profiles/task/X.json
    `<name>`           -> any component of any kind, or a plugin name
    **`<name>`**       -> same (the emphasised form is just bolded)

Attribution claims checked:
    | … | `comp` | `plugin` |          routing-table row (last cell names the plugin)
    `comp` (an `plugin` agent)          the prose form

The backtick forms matter because agents are never slash-invocable, so sweeping
slash and bold tokens alone left most agent, skill and plugin mentions unchecked.
Any lowercase-kebab backticked word is treated as a component reference; tokens with
a dot, slash, underscore or capital (`stack-routing.md`, `docs/USAGE.md`,
`vault_dir`, `APK_DIR`, `DEC-NNN`) are not component-shaped and are skipped, which is
what keeps the false-positive rate at zero.

Prints the number of tokens checked: an empty sweep must not read as a pass. Every
failure to resolve the index exits non-zero — unresolvable means UNKNOWN, never OK.

Staleness detection here is PLUGIN-level only: it catches a plugin directory missing
from the index entirely, not a component that moved between two plugins the index
already knows. That second case is caught by the separate freshness gate in
.github/workflows/validate-frontmatter-budget.yml (`build-capability-index.py --write`
plus `git diff --exit-code`), whose path filters cover SKILL.md / agents / commands /
plugin.json. This guard depends on that job; alone it cannot tell that the index's
truth is stale.

Usage: python3 scripts/check-usage-tokens.py   (exit 0 = every token resolves)
"""
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
USAGE = REPO / "docs" / "USAGE.md"
INDEX = REPO / "capability-index.json"

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


def load_index():
    """Return (owners, plugins) from capability-index.json.

    `owners` maps a component name to the set of (plugin, kind) pairs that ship it;
    `plugins` is every plugin the index knows about. Resolving against the index
    rather than re-walking the tree is what makes ATTRIBUTION checkable: the tree
    walk could only answer "does this name exist somewhere", which is why a claim
    about *which* plugin ships a component went unverified. It also deletes this
    guard's hand-rolled copy of the component-discovery rule, so discovery lives in
    exactly one place (scripts/build-capability-index.py) instead of two that drift.

    Every failure path here exits non-zero. A guard that cannot resolve must not
    report a pass — an unreadable index means UNKNOWN, never OK.
    """
    if not INDEX.exists():
        sys.exit(f"FAIL: {INDEX} does not exist — run scripts/build-capability-index.py")
    try:
        data = json.loads(INDEX.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        sys.exit(f"FAIL: {INDEX} is unreadable ({exc}) — refusing to pass without resolution")
    components = data.get("components")
    if not components:
        sys.exit(f"FAIL: {INDEX} lists no components — refusing to pass vacuously")

    owners: dict[str, set] = {}
    plugins = set()
    for c in components:
        try:
            name, plugin, kind = c["name"], c["plugin"], c["kind"]
        except (KeyError, TypeError):
            sys.exit(f"FAIL: malformed entry in {INDEX}: {c!r}")
        owners.setdefault(name, set()).add((plugin, kind))
        plugins.add(plugin)

    # A plugin directory absent from the index means the index is stale, and every
    # component it ships would silently fail to resolve. That is a guard failure,
    # not a doc failure — say so rather than blaming USAGE.md.
    on_disk = {p.name for p in REPO.iterdir()
               if p.is_dir() and (p / ".claude-plugin" / "plugin.json").exists()}
    missing = sorted(on_disk - plugins)
    if missing:
        sys.exit(f"FAIL: {INDEX} is stale — plugin(s) on disk but absent from it: "
                 f"{', '.join(missing)}. Run scripts/build-capability-index.py")
    return owners, plugins


def owners_of(owners, name):
    return {plugin for plugin, _kind in owners.get(name, set())}


def resolve_qualified(owners, plugin, name):
    """/plugin:component — resolves ONLY if that plugin is the one that ships it."""
    return plugin in owners_of(owners, name)


def resolve_bare(owners, name):
    return any(kind == "command" for _p, kind in owners.get(name, set()))


def resolve_any_component(owners, plugins, name):
    """Any component of any type, in any plugin — or a plugin name itself."""
    return name in owners or name in plugins


COMPONENT_SHAPED = re.compile(r"^[a-z][a-z0-9-]*$")

# `component` (a `plugin` agent) — the prose attribution shape. The plugin may be
# backticked or bare; the kind word is what marks the claim as an attribution rather
# than an aside.
PROSE_ATTRIB = re.compile(
    r"`([a-z][a-z0-9-]*)`\s*\((?:an?|the)\s+`?([a-z][a-z0-9-]*)`?\s+(?:agent|skill|command|plugin)\)")


def attribution_claims(text, plugins):
    """Yield (component, claimed_plugin, where) for every attribution the doc makes.

    Two shapes, both named in BL-024:

      * a routing-table row whose LAST cell is a single backticked plugin name —
        every component-shaped backtick token in the row's other cells is claimed to
        be shipped by it;
      * prose of the form `ui-android` (an `android-dev` agent).

    BOTH rules require the claimed plugin to be a KNOWN plugin before yielding. That
    guard is not optional politeness: without it the prose form captures whatever word
    precedes the kind-noun, so ordinary English — "`thing-expert` (an internal agent)" —
    yields a claim against a plugin named "internal" and fails the build on correct docs.

    **Known limits, stated rather than implied.** The table rule fires only on a
    three-cell row whose FINAL cell names the plugin, which is the shape
    `docs/USAGE.md`'s routing table actually uses. A table that puts the plugin in any
    other column, or uses a different width, yields no claims at all — a silent miss,
    not a caught error. This is a heuristic keyed to one document's convention, not a
    general attribution parser.
    """
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # Exactly three: the routing table's real shape. `count("|") >= 3` also
            # matched a plain two-column row, so the "a three-column table about
            # something else contributes nothing" claim was false as written.
            if len(cells) == 3:
                last = cells[-1]
                m = re.fullmatch(r"`([a-z][a-z0-9-]*)`", last)
                if m and m.group(1) in plugins:
                    claimed = m.group(1)
                    for cell in cells[:-1]:
                        for tok in re.findall(r"`([a-z][a-z0-9-]*)`", cell):
                            if COMPONENT_SHAPED.match(tok):
                                yield tok, claimed, f"routing table, line {lineno}"
        for comp, claimed in PROSE_ATTRIB.findall(line):
            # Mirror the table branch: only a KNOWN plugin makes this an attribution
            # claim. Otherwise "(an internal agent)" reads as a claim about a plugin
            # called "internal" and fails a doc that is perfectly correct.
            if claimed in plugins:
                yield comp, claimed, f"prose, line {lineno}"


def main():
    if not USAGE.exists():
        sys.exit(f"FAIL: {USAGE} does not exist")
    text = USAGE.read_text()
    owners, plugins = load_index()

    checked, unresolved = [], []

    # /plugin:component
    for plugin, name in token_starts(text, r"/([a-z0-9-]+):([a-z0-9-]+)\b(?!/)"):
        checked.append(f"/{plugin}:{name}")
        if plugin not in plugins:
            unresolved.append(f"/{plugin}:{name} — no such plugin '{plugin}'")
        elif not resolve_qualified(owners, plugin, name):
            shipped = sorted(owners_of(owners, name))
            unresolved.append(
                f"/{plugin}:{name} — {plugin} does not ship '{name}'"
                + (f"; it is shipped by {', '.join(shipped)}" if shipped
                   else "; no plugin ships it"))

    # bare /command (no colon, so not the qualified form above)
    for (name,) in token_starts(text, r"/([a-z0-9-]+)(?![:\w/-])"):
        if name in BUILTINS or name in plugins:
            continue
        checked.append(f"/{name}")
        if not resolve_bare(owners, name):
            unresolved.append(f"/{name} — no plugin ships a command named '{name}'")

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
        if not resolve_any_component(owners, plugins, name):
            unresolved.append(
                f"`{name}` — not a plugin, and no plugin ships a component by "
                f"that name")

    # Attribution: WHICH plugin ships it, not merely that something does. Resolution
    # above answers existence; without this pass, moving a component between plugins
    # or mis-filing a routing-table row passes silently.
    for comp, claimed, where in attribution_claims(text, plugins):
        if comp in NON_COMPONENTS or comp in plugins:
            continue
        actual = owners_of(owners, comp)
        if not actual:
            continue  # existence is already reported by the backtick sweep above
        checked.append(f"{comp}@{claimed}")
        if claimed not in actual:
            unresolved.append(
                f"`{comp}` attributed to `{claimed}` ({where}) — actually shipped "
                f"by {', '.join(sorted(actual))}")

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
