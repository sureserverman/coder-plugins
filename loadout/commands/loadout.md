---
description: Show, set, or change the plugin loadout for the current project. Layers a sticky tech baseline with on-demand task overlays.
argument-hint: "[show|list|set <tech>|add <task>|remove <task>|clear|reset|detect]"
allowed-tools: ["Bash(python3:*)"]
model: inherit
---

# /loadout

Manages **which plugins are enabled in this project** by writing `enabledPlugins` to `.claude/settings.local.json`. The plugin set is a union of three layers:

1. **always-on** — plugins loaded in every project (e.g. `git-github`, `planning`).
2. **tech** — one sticky baseline per project (`android`, `rust`, `web-ext`, `python`, `plugin-dev`, `docs`, `none`). Stored in `.claude/loadout.json`.
3. **task** — overlays you toggle on demand (`security-audit`, `release`, `wiki`, `refactor`, `web`, `plugin-authoring`).

Everything **not in the union** is set to `false` for this project, so the session only loads what's relevant. Changes take effect on the next session start (restart or `/clear`).

## Run

The user invoked this with: `$ARGUMENTS`

Parse `$ARGUMENTS` and dispatch:

| Pattern | Run |
|---|---|
| empty | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loadout.py show` |
| `list` | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loadout.py list` |
| `<tech>` matching a tech profile name | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loadout.py set <tech>` |
| `+<task>` or `add <task>` | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loadout.py add <task>` |
| `-<task>` or `remove <task>` | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loadout.py remove <task>` |
| `clear` | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loadout.py clear` |
| `reset` | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loadout.py reset` |
| `detect` | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loadout.py detect` |

Always run with `CLAUDE_PROJECT_DIR` set in the env if it isn't already, so the script writes to the right project. Display the script's stdout verbatim — it is already formatted for the user.

If the script exits non-zero, surface its stderr to the user without rephrasing it.

After a successful state-changing command (`set`, `add`, `remove`, `clear`, `reset`), remind the user with one line: **"Restart the session or `/clear` to apply."** Do not run anything else.

## Examples

```
/loadout                       # show what's currently scoped in for this project
/loadout list                  # list available tech and task profiles
/loadout set android           # make android the sticky baseline here
/loadout add security-audit    # bring sec-audit in for the current task
/loadout remove security-audit # take it back out
/loadout clear                 # drop all task overlays (keep tech)
/loadout reset                 # go back to global enabledPlugins
/loadout detect                # auto-pick tech from Cargo.toml / build.gradle / etc.
```

## Adding your own profiles

Drop JSON files under `~/.claude/loadouts/tech/<name>.json` or `~/.claude/loadouts/task/<name>.json`:

```json
{ "description": "...", "plugins": ["plugin@marketplace", "..."] }
```

User profiles override bundled ones with the same name.
