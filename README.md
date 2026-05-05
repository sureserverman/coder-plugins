# coder-plugins

A Claude Code plugin marketplace hosting opinionated, language- and platform-specific authoring plugins.

## Install as a marketplace

```
/plugin marketplace add sureserverman/coder-plugins
```

Then install individual plugins:

```
/plugin install rust-dev@coder-plugins
/plugin install android-dev@coder-plugins
/plugin install plugin-dev@coder-plugins
/plugin install release-promo@coder-plugins
/plugin install stingy-agents@coder-plugins
/plugin install infra-build@coder-plugins
/plugin install git-github@coder-plugins
/plugin install planning@coder-plugins
```

## Plugins

### rust-dev

Idiomatic Rust authoring. Bundles:

- **`rust-coding` skill** — triggers on `*.rs` / `Cargo.toml` edits; decision rules for unsafe discipline, async correctness, error handling, FFI, performance, edition 2024; progressive disclosure via `references/`.
- **`rust-expert` subagent** — sonnet-pinned, authoring-capable. Protocols: Stack detection, Author, Refactor, Review, Unsafe audit, Edition migration. Cites Rust API Guidelines, Microsoft Pragmatic Rust, *Effective Rust*, Sherlock 2026 Security Guide, tokio docs.
- **`/rust-review`** — dispatches rust-expert on a scoped diff (uncommitted, file, commit, PR).
- **`/rust-idiomize`** — dispatches rust-expert to refactor a path for idioms, behavior-preserving, tests green at each step.

Source: [`rust-dev/`](./rust-dev)

### android-dev

Android development toolkit. Bundles 4 skills, 1 command, and a complete bundled emulator stack under `infrastructure/`:

- **`android-gradle-build`** — module wiring, Hilt/Compose/Room/Retrofit setup, test execution, security hard gates.
- **`android-ui-design-figma`** — Material 3 + Compose, optional Figma workflow, standard-first implementation.
- **`android-mcp-orchestrator`** — multi-container emulator stack (phone 6", tablet 7", tablet 10") via bundled `infrastructure/` compose root; one-command `up.sh --mock` / `down.sh`.
- **`mock-server-from-app-sources`** — analyzes app code (Retrofit/Ktor/OkHttp/fetch + DTOs) to scaffold a mock backend container.
- **`/android-screenshots`** — Play Store-style captures across all emulator form factors.

Bundled `infrastructure/` ships the emulator containers, MCP server, and a reference `mock-synapse` backend — no external repo needed.

Source: [`android-dev/`](./android-dev)

### plugin-dev

Lean, security-aware authoring kit for **other** Claude Code plugins. Positioned as the 2026-current alternative to Anthropic's existing plugin-dev (~22k lines) — same surface area in ~3.6k lines, with description-leak audit and prompt-injection screening baked in.

- **10 skills** — `plugin-structure`, `skill-development`, `command-development`, `agent-development`, `hook-development` (covers 2026 events: `PostToolUseFailure`, `PostToolBatch`, `PermissionRequest`, `StopFailure`, `Notification`, `UserPromptExpansion`, `CwdChanged`, `FileChanged`, `SubagentStart/Stop`), `mcp-integration`, `mcp-server-development`, `plugin-settings`, plus `skill-description-leak-audit` (leak-proof an existing SKILL.md), `skill-best-practices-sync` (cached research → applied), and `creating-subagents` (one definition that works on Claude Code + Codex + Cursor + OpenCode). Each SKILL.md is ≤500 lines with one-level-deep `references/`.
- **3 agents** — `plugin-validator` (haiku, read-only static checker), `skill-reviewer` (haiku, leak-audit + injection scan), `agent-creator` (sonnet, write-capable scaffolder).
- **`/create-plugin`** — guided end-to-end scaffolding: discover intent, draft components via the relevant skill, dispatch `agent-creator` per agent, finish with a `plugin-validator` pass.

Source: [`plugin-dev/`](./plugin-dev)

### release-promo

Drafts release-announcement posts for the platforms a project actually belongs on. Never autoposts — every draft is a markdown block you copy.

- **5 skills** — `reddit-promo` (subreddit-aware, with explicit guidance for Matrix subs r/matrixprotocol and r/matrixdotorg, plus r/selfhosted, r/programming, language subs, topic subs), `twim-submission` (This Week in Matrix), `hackernews-show-hn` (Show HN rules + first-comment template), `lobsters-post` (tag selection + invite-culture etiquette), `fediverse-post` (Mastodon-compatible toots with hashtag and CW guidance).
- **`post-drafter` subagent** — haiku-pinned, read-only. Drafts one post per channel from surveyed facts plus the matching SKILL.md. Dispatched in parallel so the orchestrator stays cheap.
- **`/promote-release`** — surveys the current repo (README, CHANGELOG, latest tag, language signals, Matrix detection), picks eligible channels, then fans out drafting to `post-drafter` (one invocation per channel) and concatenates the results into a single markdown bundle.

Source: [`release-promo/`](./release-promo)

### planning

Four-skill pipeline that turns a vague idea into executed work. The skills hand off to each other and were designed as a unit.

- **`brainstorming`** — vague idea → validated design via question-driven exploration (purpose, constraints, alternatives, risks).
- **`planning-projects`** — staged plan with phase gates, `Depends on` / `Blocks` / `Parallel` task fields, Red-Green max cycles, Stage gates.
- **`executing-plans`** — drives a plan file; Red-Green loops; respects stage gates; dispatches independent tasks for parallel run.
- **`dispatching-parallel-agents`** — fans out tasks marked `Parallel YES` whose dependencies are green; integrates results respecting the dependency graph.

Source: [`planning/`](./planning)

### Other plugins

- **[`git-github/`](./git-github)** — everyday git/GitHub ops: commits, PRs, code review, multi-model second opinions, comment audit, workflow audit, README review, license audit, release tags.
- **[`infra-build/`](./infra-build)** — make a project buildable by the `~/dev/infra` publishing pipelines (Debian .deb, macOS .pkg, multi-arch Docker).
- **[`stingy-agents/`](./stingy-agents)** — three scope-bounded subagents (Haiku scanner, Sonnet rewriter, Sonnet code-generator) so a skill or Opus caller can offload bulk work.

## Layout

```
coder-plugins/
├── .claude-plugin/
│   └── marketplace.json
├── README.md
├── docs/
│   └── plans/                    # staged-plan files for non-trivial additions
├── rust-dev/
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   ├── agents/
│   └── commands/
├── android-dev/
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   ├── commands/
│   └── infrastructure/           # bundled emulator + MCP + mock-synapse compose stack
├── plugin-dev/
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   ├── agents/
│   └── commands/
└── release-promo/
    ├── .claude-plugin/plugin.json
    ├── skills/
    ├── agents/
    └── commands/
```

## Contributing a new plugin

The fastest path is to use the `plugin-dev` plugin's own scaffolding:

```
/plugin install plugin-dev@coder-plugins
/create-plugin <new-plugin-name>
```

Manually:

1. Add a top-level directory named `<plugin-name>/`
2. Create `.claude-plugin/plugin.json` with `name`, `description`, and (for stable releases) `version`. Components (`skills/`, `commands/`, `agents/`, `hooks/`, `.mcp.json`) live at the **plugin root**, never inside `.claude-plugin/`.
3. Register the plugin in `.claude-plugin/marketplace.json` under `plugins` — match the existing entries' shape (`name`, `source`, `description`, `version`, `category`, `tags`, `strict`).
4. Validate with the `plugin-validator` agent from `plugin-dev`.
5. For non-trivial additions, drop a staged plan in `docs/plans/<date>-<plugin>.md` first.

## License

Each plugin carries its own LICENSE; all are MIT unless noted otherwise.
