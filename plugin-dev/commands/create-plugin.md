---
description: Guided end-to-end Claude Code plugin scaffold — discover intent, draft components, validate.
argument-hint: [plugin-name] (optional)
allowed-tools: ["Read", "Write", "Edit", "Glob", "Grep", "AskUserQuestion", "Skill", "Agent", "Bash(jq:*)", "Bash(find:*)", "Bash(ls:*)", "Bash(mkdir:*)", "Bash(python3:*)", "Bash(test:*)"]
model: inherit
---

# /create-plugin

Scaffolds a new Claude Code plugin under a marketplace directory the user names. Walks the user through the high-leverage decisions, drafts each component using the relevant `plugin-dev:*` skill, dispatches `agent-creator` for any agents, and finishes with a `plugin-validator` pass.

The user invoked this command with: `$ARGUMENTS`

## Phase 1 — Discover intent

If `$ARGUMENTS` already names a plugin, use it. Otherwise ask the user (one `AskUserQuestion`):

- What is the plugin name? (kebab-case)
- Where is it going? (target marketplace dir, e.g., `~/dev/coder-plugins/` — must already have a `.claude-plugin/marketplace.json` you can register the new plugin in)
- One-sentence purpose.

Then ask which components to scaffold (multi-select):

- Skills (which domains?)
- Slash commands
- Subagents (read-only? write-capable?)
- Hooks (which events?)
- MCP server bundle?

Don't overplan. The user can add more later.

## Phase 2 — Foundation (always)

Create the plugin skeleton:

```
<marketplace-root>/<plugin-name>/
├── .claude-plugin/plugin.json
├── README.md
└── LICENSE
```

`plugin.json` template:

```json
{
  "name": "<plugin-name>",
  "description": "<one-line purpose>",
  "version": "0.1.0",
  "author": {"name": "<from marketplace owner>", "email": "<from marketplace owner>"},
  "license": "MIT",
  "keywords": ["<3-8 lowercase tags>"]
}
```

Register the plugin in the marketplace's `marketplace.json` `plugins:` array. Match the existing entries' shape (category, tags, source, strict).

## Phase 3 — Components (per user choice)

For each component type the user picked, **load the matching skill via the Skill tool** and follow its guidance to draft files. The skills are:

| Component | Load this skill |
|---|---|
| Skills | `plugin-dev:skill-development` |
| Commands | `plugin-dev:command-development` |
| Agents | `plugin-dev:agent-development` (then dispatch `plugin-dev:agent-creator` per agent) |
| Hooks | `plugin-dev:hook-development` |
| MCP | `plugin-dev:mcp-integration` |
| Layout / manifest questions | `plugin-dev:plugin-structure` |

For agents specifically: after the user lists the agents they want, dispatch the `agent-creator` agent (Agent tool, `subagent_type: agent-creator`) once per agent with a tight brief: target path, purpose, scope, model preference. Don't write agent files inline — that's `agent-creator`'s job.

## Phase 4 — Self-validate

Run the `plugin-validator` agent (Agent tool, `subagent_type: plugin-validator`) on the new plugin root. Address any **errors**. Surface **warnings** to the user — let them decide whether to fix now.

For each new skill, run `plugin-dev:skill-reviewer` and triage its critical findings.

## Phase 5 — Wrap up

Show the user:

1. The new plugin's tree (`find <plugin-root> -maxdepth 3 -type f | sort`).
2. The validator verdict.
3. Install instructions: `/plugin marketplace add <marketplace-source>` then `/plugin install <plugin-name>@<marketplace-name>`.
4. Suggested next steps (write the README body, add tests for any bash hooks, push to remote when the marketplace has one).

## Defaults you can apply without asking

- `version: 0.1.0` for new plugins.
- `LICENSE` matches the marketplace's existing LICENSE (copy from a sibling plugin).
- `keywords` starts with kebab-case versions of the plugin's domain (the user said "rust", you start with `["rust"]` and ask them to extend).
- Skills and agents get model tier `inherit` and `haiku` respectively unless the user signals otherwise (read-only audits get haiku; write-capable get sonnet — see `agent-creator`'s model decision matrix).

## Anti-patterns to refuse

- Creating a plugin outside an existing marketplace (no `.claude-plugin/marketplace.json` to register in).
- Naming a plugin that already exists in the target marketplace.
- Putting components inside `.claude-plugin/` (only `plugin.json` belongs there — the validator will catch this, but you should preempt it).
- Skipping the validator pass at the end. Even on a fresh scaffold, run it.

## Out of scope

- Publishing the marketplace to GitHub (user does this).
- Pushing commits (user does this).
- Building binaries for `bin/` (user does this).
- Authoring substantive skill or agent content beyond a stub — your job is the scaffold and the wiring; the user fills in domain content.
