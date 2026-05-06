---
name: cowork-plugin-development
description: Use when authoring or porting a plugin for Claude Cowork specifically — the chat-shaped knowledge-work surface in Claude Desktop. Triggers on "build a Cowork plugin", "ship to Cowork", "make this plugin Cowork-first", "Cowork zip upload", "release plugin via GitHub Actions", "Cowork connectors / Scheduled Tasks / Routines", "Cowork hooks not firing", "/plugin marketplace add doesn't work in Cowork", "multilingual skill triggers", "connector-aware enrichment", "privacy posture for cloud Routines". Decision rules for how Cowork differs from Claude Code, what does and doesn't work, the canonical zip-upload distribution path, and the design patterns that make a Cowork plugin feel native to the chat surface rather than ported from a CLI.
---

# cowork-plugin-development

Cowork is a chat-shaped surface in Claude Desktop, launched alongside Claude Code and using the same agentic architecture. It runs the same plugin format (`.claude-plugin/plugin.json`, `skills/`, `agents/`, `commands/`, `hooks/`), but several things differ enough to bite plugin authors who only target Code:

- Plugin install is **UI-driven (zip upload)**, not slash-command-driven (`/plugin marketplace add` does not exist in Cowork).
- Plugin-scope hooks are **broken in Cowork** as of 2026-Q2 (anthropics/claude-code#27398). Don't ship them; degrade gracefully if you must.
- **Connectors** (Gmail / Calendar / Drive / DocuSign / Slack), **Scheduled Tasks** (desktop, cron-style), and **Routines** (cloud, webhook/event-driven) are Cowork-only primitives. Designing for them changes the shape of skills.
- The **chat register** dominates. Skills designed for terminal-resident users tend to feel wrong; skills designed for chat-resident users tend to feel right.

This skill teaches the patterns that make a Cowork plugin feel native, the distribution path that actually works today, and the gotchas that aren't documented anywhere central.

## Reference map

| When you need… | Read first |
|---|---|
| Cowork-vs-Code parity matrix, primitives (connectors / scheduled tasks / routines), known bugs with citations | `references/cowork-platform.md` |
| Zip-upload install flow, GitHub Actions release workflow, single-zip vs per-plugin distribution tradeoff | `references/cowork-distribution.md` |
| Multilingual triggers, connector-aware enrichment, privacy posture, refuse-without-prereq, save-and-resume, "## In Cowork" skill convention | `references/cowork-design-patterns.md` |
| Copy-paste release.yml that builds a single all-in-one zip on tag | `examples/release-workflow.yml` |
| Sample skill demonstrating multilingual triggers + connector-aware enrichment + In Cowork section | `examples/cowork-aware-skill.md` |

## Decision rules

### Should this plugin target Code, Cowork, or both?

| Signal | Pick |
|---|---|
| User runs commands in a terminal, edits files via shell, uses git constantly | **Code** |
| User talks in chat, attaches PDFs, asks for daily rhythms (briefings, digests, summaries) | **Cowork** |
| Plugin uses Connectors (Gmail / Calendar / Drive / DocuSign / Slack) | **Cowork-only** — Connectors are not available in Code |
| Plugin uses Scheduled Tasks or Routines | **Cowork-only** — these primitives don't exist in Code |
| Plugin needs `/plugin marketplace add` to install programmatically | **Code-only** — Cowork uses UI-only install |
| Plugin runs primarily through `Bash` for non-trivial system work | **Code** — Cowork runs Bash in a sandboxed VM separate from the host OS |
| Multilingual user-facing prompts, knowledge-work register, no terminal idioms | **Cowork** |

If the plugin works in both, **target Cowork-first** in the README and golden paths, and let Code be the implicit fallback. The reverse (Code-first with Cowork as a footnote) ages badly because Cowork has primitives Code doesn't.

### Should this plugin ship hooks?

**No, not for Cowork.** Plugin-scope `hooks/hooks.json` files do not fire in Cowork as of 2026-Q2 (see `references/cowork-platform.md` for the issue link). If your design depends on hooks, redesign:

- **Replace SessionStart hooks** with skill descriptions that pick up first-message signal (e.g., a welcome skill that fires on "show me what you do").
- **Replace PreToolUse / PostToolUse policy hooks** with explicit confirmation steps inside skills ("Save? (yes / no / edit)").
- **Replace Stop hooks** with closing-block discipline inside skills' final phase.

When upstream fixes the issue, hooks become an enrichment layer; until then, they are not part of the working plugin contract.

### How will users install this plugin?

Default to GitHub-release-zip distribution. The user:

1. Downloads one zip from `github.com/<org>/<repo>/releases/latest`.
2. Unzips locally to get one inner zip per plugin.
3. Uploads each inner zip via Cowork → Customize → Browse plugins → upload custom plugin file.
4. Restarts Cowork.

This works because (a) it sidesteps the known marketplace skill-loading bug (anthropics/claude-code#39400), (b) it works for personal-plan users without org-admin rights (custom GitHub-marketplace setup is admin-only on Team/Enterprise plans), and (c) it gives you full control over what each release contains.

The release workflow is mechanical — see `examples/release-workflow.yml` for a copy-paste version that builds a single `<plugin-bundle>-<version>.zip` containing per-plugin inner zips on every tag push matching `v*`.

### Should the plugin's marketplace.json describe a multi-plugin bundle?

Optional. `marketplace.json` is read by `/plugin marketplace add` in Code. In Cowork, it's only consulted by org admins setting up a custom marketplace. Personal users uploading zips don't need it.

If you ship one, keep it accurate (every plugin source path resolves), and treat it as a Code-side convenience rather than a load-bearing piece of Cowork distribution.

### Should skills auto-fire, or wait for `/<command>`?

For Cowork, **skill auto-trigger is the dominant pattern**. The user is in chat, they don't know your slash commands, they describe their need in natural language. Slash commands are a fallback for power users.

Design rule: every workflow that should be reachable from natural-language phrasing has a **skill with a multilingual `description`**. Slash commands are thin wrappers when an explicit invocation is useful (e.g., `/welcome:tour` mirrors the `marketplace-tour` skill).

For description discipline (length, leak risk, multilingual triggers), see `cowork-design-patterns.md` and the existing `skill-development` and `skill-description-leak-audit` skills in this plugin.

### Where do connectors fit in?

Connectors are Cowork-only and **opt-in per user**. Never gate a skill on a connector being available — design skills to work without connectors and **enrich** when one is granted.

The convention this plugin recommends: every skill that benefits from a connector grows a `## In Cowork (connector-aware enrichment)` section in the body. The section says "this skill gains <X> when <connector> is granted" without making it required. See `cowork-design-patterns.md` for the full convention with examples.

### Should this plugin ship Routine templates?

Maybe. Routines are cloud-hosted Cowork automations (run with the laptop closed, fire on schedule / webhook / GitHub event). They transit Anthropic's cloud, which changes the privacy posture.

Ship Routine templates **as documentation**, not as auto-installed automations. Put them under `routines/` in the plugin. Each template:

- Has a privacy header naming what data crosses the cloud boundary during execution.
- Is named `<workflow>-routine.md` so users find them.
- Names the connectors it expects (Gmail, Drive, etc.).
- Names the trigger (cron, webhook, GitHub event).

Some workflows should **not** be routinable for privacy reasons — e.g., a reflection or therapy-style skill, or a profile-edit skill. Make this explicit in the routines/README.md.

### Is `Bash` use safe in Cowork?

Bash runs in Cowork's sandboxed VM, separate from the host OS. That's good for safety but means:

- **Filesystem access is granular per-folder** — the user grants specific folders. Don't assume `~/.claude/` is readable; check.
- **Network access is sandboxed** — most outbound HTTP works; some host-resolved connections may not.
- **Long-running processes are constrained** — the VM is per-task, not persistent. Don't design skills that need a daemon.
- **Host-OS-specific tooling is unavailable** — no `launchctl`, no `crontab` (use Cowork's Scheduled Tasks instead), no `osascript`.

When in doubt, prefer Cowork's first-class primitives (connectors, scheduled tasks, routines, file uploads) over Bash automation.

## Anti-patterns this skill catches

- Documentation that says **"install via `/plugin marketplace add`"** — that command doesn't exist in Cowork. Replace with the zip-upload flow.
- A `setup-X.md` command that prints a `crontab -e` snippet — Cowork has no crontab. Use the `/schedule` UI flow.
- A skill that **assumes connector data is always available** — connectors are opt-in. Skill must work without them.
- A `hooks/hooks.json` shipped in the plugin — broken in Cowork. Redesign as in-skill confirmation steps.
- A SKILL.md description that's >800 chars and lists 8+ language triggers verbatim — risks UI truncation. Move the long list to a "Triggers" section in the body; keep the description's trigger semantics short.
- A Routine template without a privacy header — users can't tell which workflows are safe for cloud transit.
- A README install section that buries the Cowork upload flow under terminal idioms — Cowork users won't read past the `/plugin` line.

## Sources

- Anthropic, *Use plugins in Claude Cowork* — Customize → Browse plugins → upload custom plugin file flow ([support.claude.com](https://support.claude.com/en/articles/13837440-use-plugins-in-claude-cowork)).
- Anthropic, *Get started with Claude Cowork* — same agentic architecture, sub-agent coordination, sandboxed VM, folder-permission filesystem ([support.claude.com](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork)).
- Anthropic, *Schedule recurring tasks in Claude Cowork* — Scheduled Tasks UI ([support.claude.com](https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork)).
- Anthropic, *Manage Claude Cowork plugins for your organization* — admin marketplace setup, GitHub sync, zip upload (org-admin only on Team / Enterprise plans) ([support.claude.com](https://support.claude.com/en/articles/13837433-manage-claude-cowork-plugins-for-your-organization)).
- Claude Code Docs, *Automate work with routines* — cloud-hosted Routines, scheduled / webhook / GitHub-event triggers ([code.claude.com](https://code.claude.com/docs/en/web-scheduled-tasks)).
- Cowork product page — chat-shaped knowledge-work surface using Code's agentic architecture ([claude.com/product/cowork](https://claude.com/product/cowork)).
- Bug: plugin-scope hooks/hooks.json never fire in Cowork (`--setting-sources user` excludes plugin scope) ([anthropics/claude-code#27398](https://github.com/anthropics/claude-code/issues/27398)).
- Bug: marketplace plugins fail to load skills in Cowork; zip upload of the same plugin works ([anthropics/claude-code#39400](https://github.com/anthropics/claude-code/issues/39400)).

These are the primary sources every claim in the references folder rests on. When upstream behavior changes (the bugs get fixed, new primitives ship), update the references — not this SKILL.md.
