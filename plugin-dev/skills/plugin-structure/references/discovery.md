# Component Discovery Reference

How the Claude Code plugin runtime finds and validates each component type. "Auto-discovered" means the runtime scans the well-known path without any manifest entry. "Manual" means the user must configure the component explicitly.

## Contents

- [Discovery summary](#discovery-summary)
- [Skills — `skills/<name>/SKILL.md`](#skills--skillsnameskillmd)
- [Commands — `commands/<name>.md`](#commands--commandsnamemd)
- [Agents — `agents/<name>.md`](#agents--agentsnamemd)
- [Hooks — `hooks/hooks.json`](#hooks--hookshooksjson)
- [MCP Servers — `.mcp.json` (manual only)](#mcp-servers--mcpjson-manual-only)
- [LSP Servers — `.lsp.json`](#lsp-servers--lspjson)
- [Monitors — `monitors/monitors.json`](#monitors--monitorsmonitorsjson)
- [Executables — `bin/`](#executables--bin)

## Discovery summary

| Component | Scan path | Auto? | Single or multiple |
|---|---|---|---|
| Skills | `skills/*/SKILL.md` | Yes | One per subdirectory |
| Commands | `commands/*.md` | Yes | One per file |
| Agents | `agents/*.md` | Yes | One per file |
| Hooks | `hooks/hooks.json` | Yes | One file; array inside |
| MCP servers | `.mcp.json` | **No** | One file; map inside |
| LSP servers | `.lsp.json` | Yes | One file; map inside |
| Monitors | `monitors/monitors.json` | Yes | One file; array inside |
| Executables | `bin/*` | Yes | All files in dir |

---

## Skills — `skills/<name>/SKILL.md`

**Valid when:**
- File exists at exactly `skills/<name>/SKILL.md` (the directory name is the local identifier, not the frontmatter `name`).
- File opens with a `---`-delimited YAML frontmatter block.
- Frontmatter contains at least `name` (string) and `description` (string).
- `name` in frontmatter becomes the full skill ID as `<plugin-name>:<name>`.

**Discovery behavior:**
The runtime walks `skills/`, treating each immediate subdirectory as a candidate. It reads `SKILL.md` from the subdirectory root. Deeply nested skill files (e.g. `skills/foo/bar/SKILL.md`) are not discovered.

**Override with `skills` manifest field:**
If `plugin.json` lists explicit paths in `"skills"`, those are loaded in order first. Any `skills/*/SKILL.md` not already listed is then auto-discovered and appended.

---

## Commands — `commands/<name>.md`

**Valid when:**
- File matches `commands/<name>.md` at the plugin root level (no subdirectories).
- File has YAML frontmatter with at least a `name` field.
- The `name` field matches the filename stem — mismatches cause duplicate autocomplete entries.

**Command name convention:** the `/` prefix is added by the runtime. A file `commands/rust-review.md` with `name: rust-review` registers as `/rust-review`.

---

## Agents — `agents/<name>.md`

**Valid when:**
- File matches `agents/<name>.md` at the plugin root level.
- File has YAML frontmatter. Required fields vary by host (Claude Code, Cursor, Codex); at minimum `name` and `description` are expected by Claude Code.

**Multi-host note:** If the plugin must target multiple hosts, use subdirectories per host (`agents/claude-code/<name>.md`, `agents/cursor/<name>.md`) and list them explicitly in the manifest `skills` field — auto-discovery only scans the flat `agents/` directory.

---

## Hooks — `hooks/hooks.json`

**Valid when:**
- File exists at `hooks/hooks.json`.
- Content is valid JSON.
- Top-level structure is an object keyed by hook event name.

Typical structure:
```json
{
  "SessionStart": [
    { "command": "${CLAUDE_PLUGIN_ROOT}/bin/init.sh" }
  ],
  "PostToolUse": [
    { "command": "${CLAUDE_PLUGIN_ROOT}/bin/post-tool.sh", "tools": ["Bash"] }
  ]
}
```

**Interpreter note:** Hook commands run under `/bin/sh`, not `/bin/bash`. Use `#!/bin/bash` as the first line of any hook script that uses bash-specific syntax, or write the hook as a separate script file.

Recognized event names: `SessionStart`, `SessionEnd`, `CwdChanged`, `PreToolUse`, `PostToolUse`, `Stop`.

---

## MCP Servers — `.mcp.json` (manual only)

**Not auto-discovered.** The user must run `/mcp add` or edit their Claude Code settings to register an MCP server. The `.mcp.json` file at the plugin root is a template/hint; it is not loaded automatically.

Reason: MCP servers carry connection credentials and may have side effects. The runtime requires explicit user consent for each server.

Typical file structure (for documentation purposes):
```json
{
  "servers": {
    "my-server": {
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/mcp-server",
      "args": [],
      "env": {}
    }
  }
}
```

---

## LSP Servers — `.lsp.json`

**Valid when:**
- File exists at `.lsp.json` at the plugin root.
- Content is valid JSON with a `"servers"` object.

Each entry names a language server the plugin provides. The runtime starts it when a file matching the registered language is opened.

```json
{
  "servers": {
    "my-lsp": {
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/my-lsp",
      "filetypes": ["myext"]
    }
  }
}
```

---

## Monitors — `monitors/monitors.json`

**Valid when:**
- File exists at `monitors/monitors.json`.
- Content is a valid JSON array of monitor objects.

Monitors are background watchers that can emit events into the session. Each object must have at least `name` and `command`.

```json
[
  {
    "name": "file-watcher",
    "command": "${CLAUDE_PLUGIN_ROOT}/bin/watch.sh",
    "events": ["on_change"]
  }
]
```

---

## Executables — `bin/`

**Valid when:**
- File exists anywhere directly under `bin/` (not in subdirectories).
- File has the executable bit set (`chmod +x`).

The entire `bin/` directory is prepended to the Bash `PATH` environment variable for the duration of the session while the plugin is active. This makes plugin-bundled tools available to hooks, commands, and any Bash tool calls without absolute paths — though within hook scripts you should still use `${CLAUDE_PLUGIN_ROOT}/bin/<name>` for clarity.
