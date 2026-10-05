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

loadout writes only what turns a plugin **off**: everything not in the union is set to `false` for this project. A plugin in the union that is installed and enabled at user scope is omitted, so it loads from your user-scope install and stays current. Changes apply on next session start (restart or `/clear`).

**Why loadout writes no `true`.** A local `true` makes Claude Code create a local install record for that project, and that record pins the plugin's version. Nothing refreshes it: `claude plugin update` at user scope leaves it alone, and later sessions reuse it (DEC-030). So the model is: user settings enable every plugin you install, and loadout turns plugins off. A plugin in the union that user settings leave **off**, or that has no user-scope install, still needs a local `true`. loadout writes it and prints a warning that it pins that plugin's version. Turn the plugin on in user settings to avoid the pin.

## Commands

```text
/loadout                       show current loadout for this project
/loadout list                  list available tech and task profiles (authoritative)
/loadout set android           set sticky tech baseline
/loadout add security-audit    add a task overlay (also: /loadout +security-audit)
/loadout remove security-audit drop a task overlay (also: /loadout -security-audit)
/loadout clear                 drop all task overlays (keep tech)
/loadout reset                 drop tech + overlays — back to global enabledPlugins
/loadout detect                auto-pick tech from Cargo.toml / build.gradle / etc.
/loadout unpin [--dry-run]     remove this project's version-pinned plugin records
```

`unpin` removes the project's local install records for plugins that also have a user-scope install (`claude plugin uninstall <key> --scope local`), then re-applies the loadout. A record with no user-scope install is kept and listed, because removing it would take the plugin away. `--dry-run` only lists.

## Bundled profiles

Profile names are **typed arguments** to `set` and `add`, so they are part of the interface.
`/loadout list` is authoritative; these are what ships today:

| Tech baselines (`/loadout set <name>`) | Task overlays (`/loadout add <name>`) |
|---|---|
| `android`, `rust`, `python`, `web-ext`, `docs`, `plugin-dev`, `none` | `security-audit`, `release`, `refactor`, `wiki`, `web`, `e2e-test`, `plugin-authoring` |

`none` is a real baseline, not the absence of one — it pins "this project has no tech
baseline" so `detect` stops re-guessing on every fresh clone.

User profiles in `~/.claude/loadouts/` **override** a bundled profile of the same name
(full replacement, not a merge); the bundled and user `always-on.json` are unioned instead.

## Hook

### `hooks/hooks.json` → `hooks/auto-detect.sh`

Registers one **`SessionStart`** hook. This is the only thing in the plugin that runs without you asking, so it is worth knowing exactly what it does:

- **No-ops when `.claude/loadout.json` already exists** — it only ever acts on a project it has never seen.
- Runs `scripts/loadout.py detect` to infer a tech baseline from project markers (`Cargo.toml`, `build.gradle`, …).
- **Silent on any failure, and never blocks session start** — `set -eu` plus explicit `exit 0` on both the already-configured and detection-failed paths.
- On success emits a JSON `systemMessage` rather than plain stdout, so the notice reaches *you* in the TUI and not just the model.

On detection it writes **both** `.claude/loadout.json` (the baseline, committed) and
`.claude/settings.local.json` (`enabledPlugins`, gitignored) — `detect` calls the same
`apply()` every other write path uses, so the hook is not read-only. To opt out entirely, uninstall the plugin or commit a `loadout.json` yourself — the hook will then no-op forever.

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
- **A plugin off in user settings pins.** Enabling it through a loadout writes a local `true`, which pins its version for this project (loadout warns). Turn it on in user settings instead, then run `/loadout unpin`.
- **Profiles are bundled with this plugin.** Adjust them by editing your `~/.claude/loadouts/` overrides; don't fork the plugin for personal preferences.


## Worked example

```text
/plugin install loadout@coder-plugins

/loadout
```

With no arguments it reports the current project's loadout and what is enabled. Set a sticky tech
baseline and layer a task overlay on top:

```text
/loadout set rust             # sticky baseline — persists in .claude/loadout.json, committed
/loadout add security-audit   # task overlay (also: /loadout +security-audit)
/loadout remove security-audit
/loadout clear                # drop overlays, keep the baseline
/loadout reset                # drop both — back to global enabledPlugins
```

The baseline answers "what is this project built in"; overlays answer "what am I doing right now".
They compose, and the union is written to the gitignored `settings.local.json`.

**Remember the restart.** Claude Code reads `enabledPlugins` once at startup, so a loadout change
applies to your *next* session, not the current one — the single most common source of "I enabled
it and nothing happened".

## Related plugins

- Every other plugin in this marketplace is a candidate for a profile.
- **`planning`** — `capability-router` solves the adjacent problem from the other direction: it
  reaches one skill or agent from disk **without** enabling its plugin, via `capability-index.json`.
  Use `loadout` for a durable per-project set; use `capability-router` for a one-off need.
