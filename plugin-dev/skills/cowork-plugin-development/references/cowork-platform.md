# Cowork platform reference

What Cowork is, how it differs from Claude Code, what it has that Code doesn't, and the bugs you need to know about today.

## What Cowork is

Claude Cowork is a chat-shaped knowledge-work surface in the Claude Desktop app, launched alongside Claude Code in early 2026. It uses **the same agentic architecture** that powers Claude Code, but exposes it through a chat UX rather than a terminal. Cowork went generally available on macOS and Windows on 2026-04-09 with analytics, OpenTelemetry, and role-based access controls for enterprise teams.

Cowork's mental model:

- The user types a request in chat.
- Claude breaks it into multi-step work.
- Sub-agents handle parallel sub-tasks.
- Tools (filesystem, web, connectors) are invoked transparently.
- Long-running work fires on schedule (Scheduled Tasks) or in the cloud (Routines).

Cowork is built for knowledge workers — sales, finance, legal, marketing, HR, operations, design, data analysis — not for software engineering. The product positioning explicitly bundles plugins for those roles into a "growing library."

## Parity with Claude Code

| Capability | Code | Cowork | Notes |
|---|---|---|---|
| Plugin format (`.claude-plugin/plugin.json`) | ✅ | ✅ | Same schema |
| Skills (`skills/<name>/SKILL.md`) | ✅ | ✅ | Auto-fire on description match in both |
| Sub-agents (`agents/<name>.md`) | ✅ | ✅ | First-class in both |
| Slash commands (`commands/<name>.md`) | ✅ | ✅ | Surfaced via `/` menu in Cowork |
| MCP servers (`.mcp.json`, local + remote) | ✅ | ✅ | Local stdio MCP runs on user's machine in both |
| Filesystem read/write | ✅ (project-rooted) | ✅ (per-folder permission) | Cowork requires explicit folder grants |
| `Bash` tool | ✅ (host shell) | ✅ (sandboxed VM, separate from host OS) | Cowork's VM is per-task, not persistent |
| `WebFetch` / `WebSearch` | ✅ | ✅ | Same surfaces |
| Plugin install via `/plugin marketplace add` | ✅ | ❌ | Cowork install is UI-only (Customize → Browse plugins → upload) |
| Plugin-scope hooks (`hooks/hooks.json`) | ✅ | ❌ (broken — see Known bugs) | |
| Connectors (Gmail / Calendar / Drive / DocuSign / Slack) | ❌ | ✅ | Cowork-only; cloud-routed via Anthropic |
| Scheduled Tasks (cron-style, desktop) | ❌ | ✅ | Cowork-only; runs while desktop app open |
| Routines (cloud, schedule / webhook / GitHub event) | ❌ | ✅ | Cowork-only; runs in Anthropic cloud, laptop closed OK |
| File uploads in chat (PDF, image) | partial (via paths) | ✅ (drag-and-drop) | |
| Custom marketplace from GitHub repo | ✅ (`/plugin marketplace add owner/repo`) | ✅ (admin-only on Team / Enterprise) | Personal users upload zips |

When porting a plugin from Code to Cowork, the things most likely to bite are: hook removal, install-path documentation, `Bash`-heavy workflows that depended on host-OS tools, and skills that assumed connectors-style data was always available.

## Cowork-only primitives

### Connectors

First-party integrations with cloud services, **opt-in per user**. The user grants a connector once in Customize → Connectors; thereafter, skills and agents can read from / write to that service through the Anthropic-routed connector layer.

Common connectors as of 2026:

- **Google Calendar** — read events, create events.
- **Gmail** — read messages (often label-scoped), draft replies.
- **Google Drive** — read / write files in granted folders.
- **DocuSign** — read contracts and templates.
- **Slack** — read channels (often workspace-scoped), post messages.
- **GitHub** — read PRs / issues / files.
- **Linear / Jira** — read tickets, update status.
- **Microsoft 365** — Outlook, OneDrive, Teams.

Connectors run **cloud-routed via Anthropic**, not on the user's local network. That means:

- A connector accessing an internal Slack workspace works as long as the user's account is in that workspace.
- A connector cannot reach a service that's only accessible from inside the user's LAN unless the service exposes a public endpoint.
- Data flowing through a connector transits Anthropic's infrastructure during the call.

Plugin-author rule: **never gate a skill on a connector**. Always design the skill to work without connectors and *enrich* when one is granted. See `cowork-design-patterns.md` for the convention.

### Scheduled Tasks

Cron-style recurring tasks that fire while the user's Cowork desktop app is open (or whenever the next launch happens, if the scheduled time elapsed while closed). Created via:

- The `/schedule` slash command in any Cowork chat, OR
- The Scheduled sidebar item → + New task.

A Scheduled Task is **a saved prompt + a cadence** (hourly / daily / weekly / weekdays / custom cron). When it fires, Cowork opens a fresh chat session, runs the prompt, and stops. Tasks have access to the same connectors, plugins, and skills as a regular Cowork session.

Plugins that need a daily rhythm (briefings, digests, scans) should ship a **`setup-<rhythm>.md` slash command** that asks the user about cadence and walks them through pasting the right prompt into `/schedule`. The plugin does **not** call `/schedule` directly — that's a UI authorisation surface the user owns.

### Routines

Cloud-hosted Cowork automations introduced 2026-04-14. Routines run in Anthropic's cloud (laptop closed, network disconnected, OS asleep), and trigger on:

- **Schedule** (cron-style, like Scheduled Tasks but cloud-hosted).
- **Webhook** (Cowork generates a unique URL; external system POSTs to it).
- **GitHub event** (PR opened, issue labeled, push to a branch).
- **Linear event** (ticket status change), other connector-driven events.

A Routine bundles: a prompt, optionally a code repo (for Code-style work), and a set of granted connectors.

Privacy posture: Routines transit Anthropic's cloud. Plugin authors must surface this when a workflow is sensitive. The pattern in this plugin's `cowork-design-patterns.md` calls for a privacy header on every Routine template.

Some workflows should **not** be Routine-able by design — anything involving reflection content, profile edits with material identity claims, or contracts under NDA. Make non-Routinable explicit in the plugin's `routines/README.md`.

## Known bugs to design around (2026-Q2)

### Plugin-scope hooks don't fire in Cowork

[`anthropics/claude-code#27398`](https://github.com/anthropics/claude-code/issues/27398)

Cowork spawns Claude Code with `--setting-sources user`, which excludes plugin-scope hook discovery. This means a plugin shipping `hooks/hooks.json` will see those hooks **never fire** when the plugin is installed in Cowork. They work fine in Code.

Workaround: don't ship plugin-scope hooks for Cowork. Redesign as:

- In-skill confirmation steps for what would have been PreToolUse policy hooks.
- Skill descriptions that pick up first-message signal for what would have been SessionStart hooks.
- Closing-block discipline inside skills' final phase for what would have been Stop hooks.

When upstream fixes this, hooks become an enrichment layer for Cowork. Until then, treat hooks as Code-only.

### Marketplace-installed plugins may fail to load skills in Cowork

[`anthropics/claude-code#39400`](https://github.com/anthropics/claude-code/issues/39400)

Plugins installed via Cowork's marketplace surface (admin-set-up GitHub-synced marketplace) sometimes fail to load skills in Cowork sessions, while a zip-upload of the **exact same plugin** works fine. The bug appears related to skill discovery during marketplace sync.

Workaround: distribute via zip upload. Even when an org admin has set up a custom marketplace, recommend the zip-upload path as a fallback if skills don't fire.

### `/plugin` slash commands don't exist in Cowork

Not a bug — by design. `/plugin marketplace add`, `/plugin install`, `/plugin uninstall` are Code-only. Cowork uses the Customize → Browse plugins UI for everything plugin-related.

Plugin-author rule: don't put `/plugin` commands in a Cowork-targeted README. Use the zip-upload flow instead. If you maintain one README that serves both surfaces, name the install paths explicitly: "**In Cowork** … **In Code** …".

## Sources

- *Use plugins in Claude Cowork* — [support.claude.com](https://support.claude.com/en/articles/13837440-use-plugins-in-claude-cowork)
- *Get started with Claude Cowork* — [support.claude.com](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork)
- *Schedule recurring tasks in Claude Cowork* — [support.claude.com](https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork)
- *Manage Claude Cowork plugins for your organization* — [support.claude.com](https://support.claude.com/en/articles/13837433-manage-claude-cowork-plugins-for-your-organization)
- *Automate work with routines* — [code.claude.com](https://code.claude.com/docs/en/web-scheduled-tasks)
- *Cowork product page* — [claude.com/product/cowork](https://claude.com/product/cowork)
- Bug 27398 — [anthropics/claude-code#27398](https://github.com/anthropics/claude-code/issues/27398)
- Bug 39400 — [anthropics/claude-code#39400](https://github.com/anthropics/claude-code/issues/39400)
