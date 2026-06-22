#!/usr/bin/env python3
"""Validate references/stack-routing.md against what this marketplace ships.

Every subagent type and stack skill named in the routing table must resolve to
one of:
  - a built-in subagent (general-purpose, Explore),
  - a plugin agent shipped by this marketplace (*/agents/*.md),
  - a skill shipped by this marketplace (*/skills/*/SKILL.md), or
  - an agent explicitly marked "(if installed)" — a declared external dependency.

Anything else is drift: a renamed/removed agent, a typo, or an *undeclared*
external dependency that will silently fall through to general-purpose for any
user who installs only this marketplace.

Exit 0 = clean, 1 = drift found. No third-party deps; stdlib only.
"""

import os
import re
import sys

BUILTINS = {"general-purpose", "Explore"}

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(HERE, "..", "references", "stack-routing.md")
# scripts/ -> dispatching-parallel-agents/ -> skills/ -> planning/ -> ROOT
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

TOKEN = re.compile(r"`([^`]+)`")


def collect_marketplace():
    """Return (agents: name->plugin, skills: set[name])."""
    agents, skills = {}, set()
    for dirpath, _dirs, files in os.walk(ROOT):
        if "/.git" in dirpath:
            continue
        for fn in files:
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT)
            if "/agents/" in ("/" + rel) and fn.endswith(".md"):
                plugin = rel.split(os.sep)[0]
                with open(path, encoding="utf-8") as fh:
                    for line in fh:
                        m = re.match(r"name:\s*(\S+)", line)
                        if m:
                            agents[m.group(1)] = plugin
                            break
            if rel.endswith("SKILL.md") and "/skills/" in ("/" + rel):
                # skills/<name>/SKILL.md
                parts = rel.split(os.sep)
                i = parts.index("skills")
                skills.add(parts[i + 1])
    return agents, skills


def table_rows(text):
    """Yield (agent_cell, skill_cell) for each data row of the routing table."""
    in_table = False
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        if set("".join(cells)) <= set("-: "):  # separator row
            in_table = True
            continue
        if cells[0].lower().startswith("task"):  # header row
            continue
        if in_table:
            yield cells[1], cells[2]


def classify(name, declared_external, agents, skills, want_skill):
    if name in BUILTINS:
        return "OK", f"built-in subagent"
    if want_skill:
        if name in skills:
            return "OK", "marketplace skill"
        return "FAIL", "skill not shipped by this marketplace"
    # agent side
    if ":" in name:  # namespaced plugin:agent — the form Claude Code dispatches
        plugin, _, bare = name.partition(":")
        if agents.get(bare) == plugin:
            return "OK", "plugin agent (namespaced)"
        if bare in agents:
            return "FAIL", f"'{name}' but '{bare}' ships in '{agents[bare]}'"
        return "FAIL", f"namespaced agent '{name}' not shipped by this marketplace"
    if name in agents:
        plugin = agents[name]
        return "WARN", f"plugin agent — use namespaced '{plugin}:{name}', table uses bare '{name}'"
    if declared_external:
        return "OK", "declared external — '(if installed)'"
    return "FAIL", "agent not shipped here and not marked '(if installed)'"


def main():
    with open(TABLE, encoding="utf-8") as fh:
        text = fh.read()
    agents, skills = collect_marketplace()

    results = []
    for agent_cell, skill_cell in table_rows(text):
        ext = "if installed" in agent_cell.lower()
        for tok in TOKEN.findall(agent_cell):
            sev, why = classify(tok, ext, agents, skills, want_skill=False)
            results.append((sev, "agent", tok, why))
        for tok in TOKEN.findall(skill_cell):
            sev, why = classify(tok, False, agents, skills, want_skill=True)
            results.append((sev, "skill", tok, why))

    # de-dup, keep worst severity per (kind, token)
    rank = {"FAIL": 0, "WARN": 1, "OK": 2}
    best = {}
    for sev, kind, tok, why in results:
        key = (kind, tok)
        if key not in best or rank[sev] < rank[best[key][0]]:
            best[key] = (sev, why)

    fails = warns = 0
    for (kind, tok), (sev, why) in sorted(best.items()):
        if sev == "OK":
            continue
        if sev == "FAIL":
            fails += 1
        else:
            warns += 1
        print(f"  [{sev}] {kind:5} {tok:32} {why}")

    total = len({k for k in best})
    print(f"\n{total} unique references checked — {fails} FAIL, {warns} WARN")
    if fails:
        print("\nFix each FAIL by either shipping the agent/skill in this marketplace,")
        print("or marking it '(if installed)' in the routing table (declared external).")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
