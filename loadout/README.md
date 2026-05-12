# loadout

Per-project **and** per-task plugin scoping for Claude Code.

Layers a sticky tech baseline (one per project) with on-demand task overlays, then writes the resulting `enabledPlugins` map to the project's `.claude/settings.local.json`. Only the plugins relevant to the current work load at session start — instead of every plugin you've ever installed.

## Why

Claude Code reads `enabledPlugins` once at session start. The global map enables every plugin you've installed, which means every plugin's command/skill/agent descriptions sit in the system prompt of every session. `loadout` lets you scope that down without losing access to plugins you only need *sometimes*.

## How

Three layers, unioned:

1. **always-on** — plugins enabled in every project (`git-github`, `planning`, ...).
2. **tech** — one sticky baseline per project (`android`, `rust`, `web-ext`, ...). Stored in `.claude/loadout.json` (commit-safe — it's a project fact).
3. **task** — overlays you toggle on demand (`security-audit`, `release`, `wiki`, `refactor`, ...). Stored in `.claude/settings.local.json` (per-machine, gitignored).

Everything **not** in the union is set to `false` for this project. Changes apply on next session start (restart or `/clear`).

## Commands

```text
/loadout                       show current loadout for this project
/loadout list                  list available tech and task profiles
/loadout set android           set sticky tech baseline
/loadout add security-audit    add a task overlay (also: /loadout +security-audit)
/loadout remove security-audit drop a task overlay (also: /loadout -security-audit)
/loadout clear                 drop all task overlays (keep tech)
/loadout reset                 drop tech + overlays — back to global enabledPlugins
/loadout detect                auto-pick tech from Cargo.toml / build.gradle / etc.
```

A `SessionStart` hook runs `detect` automatically on first entry to any project. Subsequent sessions read the saved baseline. The hook surfaces a `systemMessage` like *"loadout: detected tech=rust. Restart or /clear to apply"* — the very first session in a new project loads with the global default, then scopes down on the second.

## Custom profiles

Drop JSON files under `~/.claude/loadouts/`:

```text
~/.claude/loadouts/
├── always-on.json           (merged with bundled always-on)
├── tech/
│   └── my-tech.json
└── task/
    └── my-task.json
```

Each file:

```json
{
  "description": "What this profile is for.",
  "plugins": [
    "some-plugin@some-marketplace",
    "another@elsewhere"
  ]
}
```

User profiles **override** bundled profiles with the same name (full replacement, not merge). The bundled `always-on.json` and the user `always-on.json` are unioned.

## State files

| Path | Owner | Contains |
|---|---|---|
| `<project>/.claude/loadout.json` | committed | `{ "tech": "...", "task_overlays": [...] }` |
| `<project>/.claude/settings.local.json` | gitignored | `{ "enabledPlugins": { ... }, ... }` |

`reset` removes `loadout.json` and strips `enabledPlugins` from `settings.local.json`.

## Tradeoffs

- **Session restart required to apply.** Claude Code reads `enabledPlugins` once at startup; mid-session toggling needs the `/plugin` UI manually.
- **First entry loads with global defaults.** The auto-detect hook can't influence the current session — only the next one.
- **Profiles are bundled with this plugin.** Adjust them by editing your `~/.claude/loadouts/` overrides; don't fork the plugin for personal preferences.
