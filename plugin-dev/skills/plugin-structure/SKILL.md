---
name: plugin-structure
description: Use when authoring or modifying Claude Code plugin structure. Triggers on "create a plugin", "what goes in .claude-plugin/", "plugin.json schema", "manifest fields", "marketplace.json", "where do hooks live", "how do skills get discovered", "component discovery", "plugin directory layout", "CLAUDE_PLUGIN_ROOT".
---

# plugin-structure

Decision rules for laying out a Claude Code plugin correctly: what goes where, which fields the manifest requires, and how the runtime discovers each component.

## Reference map

| When you need… | Read first |
|---|---|
| Full plugin.json field list with examples | `references/manifest.md` |
| Per-component discovery rules and validity criteria | `references/discovery.md` |

## Directory layout

A plugin is a directory. The only required subdirectory is `.claude-plugin/`, which holds exactly one file: `plugin.json`. Every other component lives at the **plugin root**, not inside `.claude-plugin/`.

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          ← manifest; ONLY file here
├── skills/
│   └── <name>/
│       └── SKILL.md
├── commands/
│   └── <name>.md
├── agents/
│   └── <name>.md
├── hooks/
│   └── hooks.json
├── monitors/
│   └── monitors.json
├── bin/                     ← added to PATH while plugin active
├── .mcp.json                ← plugin root; manual config, not auto-discovered
├── .lsp.json                ← plugin root
└── README.md
```

## Manifest fields (`plugin.json`)

**Required**

| Field | Rules |
|---|---|
| `name` | kebab-case; becomes the skill namespace prefix (e.g. `my-plugin:skill-name`) |
| `description` | One sentence; shown in marketplace and `/plugin list` |

**Optional**

| Field | Notes |
|---|---|
| `version` | Semver. If omitted, the git commit SHA is used. Set explicitly for any stable release. |
| `author.name` | String |
| `author.email` | String |
| `homepage` | URL |
| `repository` | URL |
| `license` | SPDX identifier, e.g. `"MIT"` |
| `keywords` | Array of strings |
| `skills` | Array of explicit skill paths; use only to override auto-discovery order |

Minimal valid manifest:
```json
{
  "name": "my-plugin",
  "description": "Does something useful."
}
```

## Component discovery

| Component | Path | Format | Discovery |
|---|---|---|---|
| Skills | `skills/<name>/SKILL.md` | Markdown + YAML frontmatter | Auto |
| Commands | `commands/<name>.md` | Markdown + YAML frontmatter | Auto |
| Agents | `agents/<name>.md` | Markdown + YAML frontmatter | Auto |
| Hooks | `hooks/hooks.json` | JSON (one file per plugin) | Auto |
| MCP servers | `.mcp.json` | JSON, plugin root | **Manual only** |
| LSP servers | `.lsp.json` | JSON, plugin root | Auto |
| Monitors | `monitors/monitors.json` | JSON array | Auto |
| Executables | `bin/` | Any executable file | Auto (PATH injection) |

MCP servers are the only component that requires explicit user configuration — they are never auto-discovered because they carry connection credentials.

## Environment variables available to hooks and commands

| Variable | Value |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}` | Absolute path to the plugin install directory. Use for all bundled-asset references. |
| `${CLAUDE_PLUGIN_DATA}` | Plugin-persistent data directory; survives updates. |
| `${CLAUDE_PROJECT_DIR}` | Current project root at invocation time. |
| `CLAUDE_ENV_FILE` | Path to a file where `SessionStart`/`CwdChanged` hooks can write `KEY=VALUE` lines for session-persistent env vars. |

Always use `${CLAUDE_PLUGIN_ROOT}` rather than a relative path when referencing bundled files from a hook or command.

## Marketplace publishing

Add a `marketplace.json` at the marketplace repository root:

```json
{
  "plugins": [
    {
      "name": "my-plugin",
      "source": "https://github.com/you/my-plugin",
      "description": "One sentence.",
      "version": "1.2.0",
      "category": "development",
      "tags": ["rust", "linting", "refactor", "cli"]
    }
  ]
}
```

Valid categories: `development`, `languages`, `security`, `productivity`, `database`, `deployment`, `monitoring`, `design`, `learning`.

Tags: lowercase, 4–8, mix technology names with capability words.

Install flow: `/plugin marketplace add <repo>` then `/plugin install <plugin>@<marketplace>`.

## Anti-patterns

**Wrong location for components.** Only `plugin.json` belongs inside `.claude-plugin/`. Placing `commands/`, `agents/`, `skills/`, `hooks/`, `.mcp.json`, or `.lsp.json` inside `.claude-plugin/` means they are never discovered.

**Relative paths in hook commands.** A hook like `./bin/check.sh` breaks when the plugin is installed at a different path. Use `${CLAUDE_PLUGIN_ROOT}/bin/check.sh`.

**Omitting `version` in stable releases.** Without an explicit semver version the runtime falls back to the git commit SHA. Users cannot pin or reproduce the version. Set `"version"` before any public release.

**Missing README.** The README is the first thing users open after installing. Always include one at the plugin root.

**Skill `name:` mismatches with command wrapper name.** The `name` field in `SKILL.md` frontmatter becomes the internal skill ID. If it diverges from the corresponding command wrapper name, the skill appears twice in autocomplete. Keep them identical.

## Targeting Cowork? Distribution differs

The plugin **format** is the same in Claude Code and Claude Cowork (same `plugin.json`, same skills / agents / commands directories, same discovery rules). What changes is **how users install**: Cowork has no `/plugin marketplace add` command — install is UI-only via Customize → Browse plugins → upload custom plugin file.

For Cowork distribution patterns — GitHub Actions release workflow, single-zip vs per-plugin tradeoff, README install-section shape — see the `cowork-plugin-development` skill in this plugin. The structure rules above still apply; only the install flow and a few platform-specific gotchas (broken plugin-scope hooks, optional Connectors / Scheduled Tasks / Routines) are different.

## References

- https://code.claude.com/docs/en/plugins.md
- https://code.claude.com/docs/en/plugins-reference.md
- https://code.claude.com/docs/en/plugin-marketplaces.md
- https://github.com/anthropics/claude-plugins-official
