# plugin-dev

Lean, security-aware authoring kit for Claude Code plugins. Part of the [`coder-plugins`](..) marketplace.

## Why another plugin-dev?

Anthropic ships a [`plugin-dev`](https://github.com/anthropics/claude-plugins-official) (≈22k lines, v0.1.x). It's comprehensive but heavy and predates several 2026 surfaces. This one is positioned as:

- **2026-current** — covers the new hook events (`PostToolUseFailure`, `PostToolBatch`, `PermissionRequest`, `StopFailure`, `Notification`, `UserPromptExpansion`, `CwdChanged`, `FileChanged`, `SubagentStart/Stop`), new directories (`monitors/`, `bin/`, `.lsp.json`), and new env vars (`${CLAUDE_PLUGIN_DATA}`, `CLAUDE_ENV_FILE`).
- **Lean** — every `SKILL.md` is ≤500 lines; depth lives in `references/`, one level deep. Hard caps enforced at review.
- **Security-aware** — bakes in the description-leak audit pattern (Snyk ToxicSkills 2025, Repello SkillCheck) and prompt-injection screening for any user-controlled content in skills and agents.

If you want maximum coverage with examples, install Anthropic's. If you want a fast on-ramp that won't ship you a leaky skill, install this.

## Installation

```bash
/plugin marketplace add sureserverman/coder-plugins
/plugin install plugin-dev@coder-plugins
```

## Components

### Skills (6)

| Skill | Triggers when you ask |
|---|---|
| `plugin-structure` | "how do I lay out a plugin", "what goes in `.claude-plugin/`", "marketplace.json schema" |
| `skill-development` | "write a skill", "improve this SKILL.md", "skill description triggering" |
| `command-development` | "create a slash command", "command frontmatter", "$ARGUMENTS in commands" |
| `agent-development` | "create a subagent", "agent frontmatter", "model pinning for agents" |
| `hook-development` | "add a hook", "PreToolUse / PostToolUse", "session-end auto-capture", "block dangerous bash" |
| `mcp-integration` | "add an MCP server to my plugin", ".mcp.json", "stdio / SSE / HTTP MCP" |

### Agents (3)

| Agent | Model | Tools | Purpose |
|---|---|---|---|
| `plugin-validator` | haiku | Read, Grep, Glob, Bash | Static validation of manifest, structure, frontmatter, hooks. Read-only. |
| `skill-reviewer` | haiku | Read, Grep, Glob | Description leak-audit + injection scan + best-practice review on a SKILL.md. Read-only. |
| `agent-creator` | sonnet | Write, Read | Generates a new agent file from a brief. |

### Commands (1)

- `/create-plugin` — guided flow: discover intent, draft components via skills, dispatch `agent-creator` for each agent, finish with a `plugin-validator` pass.

## Anti-patterns this plugin will catch

- Components placed inside `.claude-plugin/` (only `plugin.json` belongs there).
- `Stop` hooks without a `stop_hook_active` guard (#1 newbie infinite-loop bug).
- SKILL.md `description:` fields that contain executable instructions (description-leak risk — Claude may run a shortened version of the description and skip the body).
- First-person POV in skill descriptions.
- Hook commands with relative paths instead of `${CLAUDE_PLUGIN_ROOT}`.
- PostToolUse hooks that block on error instead of injecting feedback.

## License

MIT
