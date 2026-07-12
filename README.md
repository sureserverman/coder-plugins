# coder-plugins

A Claude Code plugin marketplace hosting opinionated, language- and platform-specific authoring plugins.

## Install

```text
/plugin marketplace add sureserverman/coder-plugins
/plugin install <plugin>@coder-plugins        # e.g. planning@coder-plugins
```

> **Authoring plugins for AI coding agents** (Claude Code, Cursor, Codex,
> OpenCode, Cowork, Hermes, OpenClaw) lives in the sibling
> [`agent-tooling`](https://github.com/sureserverman/agent-tooling) marketplace —
> `plugin-dev` and its six platform siblings moved there. Add it with
> `/plugin marketplace add sureserverman/agent-tooling`.

## Plugins

| Plugin | What you get |
|--------|--------------|
| [`planning`](./planning) | Idea → validated design → staged plan → gated execution. Brainstorming, architecture research, Red-Green plan execution with stage gates, parallel task dispatch, portfolio `compass`, design-handoff reproduction. |
| [`business`](./business) | Business-planning pipeline, sibling to `planning`: assess viability (optionally with market research), revenue-model, launch, track, portfolio roll-up. |
| [`git-github`](./git-github) | Everyday git/GitHub ops: commits and PRs in the repo's style, code review, multi-model second opinions, comment/workflow/license/README audits, release tags. |
| [`testing`](./testing) | `testing-expert` subagent: run and triage tests, author new ones, audit coverage and test smells. Test pyramid, mutation-over-line-coverage opinions. |
| [`rust-dev`](./rust-dev) | Idiomatic Rust: `rust-coding` skill (fires on `*.rs`/`Cargo.toml` edits), `rust-expert` subagent, `/rust-review`, `/rust-idiomize`. |
| [`android-dev`](./android-dev) | Gradle build management, per-stage on-device verify gate, bundled multi-emulator + MCP + mock-server stack under `infrastructure/`, `/android-screenshots`. |
| [`game-dev`](./game-dev) | Source-cited skills for mechanics, feel/juice, camera, UX/FTUE, accessibility, and architecture, plus Godot/Unity/Unreal skills, `/game-review`, `/game-mechanic`. |
| [`browser-extensions`](./browser-extensions) | WebExtensions authoring for Chrome, Firefox, and Firefox for Android, plus an AMO compliance preflight (`scripts/amo-check.py` linter). |
| [`ui-design`](./ui-design) | Per-platform UI design, review, and facelift subagents — one expert per surface. |
| [`i18n`](./i18n) | Framework detection, hardcoded-string and catalog audits, placeholder/CLDR-plural-safe translation via a translator subagent, new-locale scaffolding. |
| [`release-promo`](./release-promo) | Drafts release-announcement posts (Reddit, Show HN, Lobsters, TWIM, Fediverse) for the channels a project actually belongs on. Never autoposts. |
| [`infra-build`](./infra-build) | Registers a project with the `~/dev/infra` publishing pipelines: Debian `.deb`, macOS `.pkg`, multi-arch Docker images. |
| [`stingy-agents`](./stingy-agents) | Three scope-bounded subagents (Haiku scanner, Sonnet rewriter, Sonnet code-generator) so a skill or Opus caller can offload bulk work cheaply. |
| [`loadout`](./loadout) | Per-project + per-task plugin scoping: a sticky tech baseline layered with on-demand task overlays. |

Each plugin's directory has its own README with full component detail.

## Usage

Every plugin ships some mix of three component types, and each is used differently:

**Skills fire automatically.** Once a plugin is installed, its skills load when
the context matches — editing a `.rs` file activates `rust-coding`, saying
"plan this feature" activates `planning-projects`, touching a translation
catalog activates the `i18n` skills. You can also invoke a skill explicitly by
its namespaced name:

```text
/planning:brainstorming
/i18n:i18n-audit
/planning:compass next
```

**Commands are explicit.** Slash commands run a defined workflow when you type
them:

```text
/rust-review HEAD~1        # review a scoped diff for Rust idioms
/game-mechanic grapple     # guided design session for a new mechanic
/promote-release           # survey the repo, draft posts per channel
/android-screenshots       # Play Store captures across emulator form factors
```

**Subagents are delegated.** Claude dispatches them on its own when a task
matches (e.g. `testing-expert` for a flaky test), or you can ask directly:
"have `rust-expert` audit the unsafe blocks in src/ffi.rs".

A typical end-to-end flow with the `planning` plugin:

```text
/plugin install planning@coder-plugins
"I want to add offline sync"    # brainstorming fires, validates a design
"plan it"                       # planning-projects writes a staged plan with gates
"execute the plan"              # executing-plans drives it to completion
```

Install only what a project needs — or install `loadout` and let its task
profiles enable and disable plugins per project.

## Contributing a new plugin

The fastest path is `plugin-dev`'s scaffolding (it lives in `agent-tooling`):

```text
/plugin marketplace add sureserverman/agent-tooling
/plugin install plugin-dev@agent-tooling
/create-plugin <new-plugin-name>
```

Manually:

1. Add a top-level directory shaped like this:

   ```text
   <plugin-name>/
   ├── .claude-plugin/
   │   └── plugin.json           # name, description, version
   ├── skills/
   ├── agents/
   └── commands/
   ```

2. Components (`skills/`, `commands/`, `agents/`, `hooks/`, `.mcp.json`) live at the **plugin root**, never inside `.claude-plugin/`.
3. Register the plugin in `.claude-plugin/marketplace.json` under `plugins` — match the existing entries' shape (`name`, `source`, `description`, `version`, `category`, `tags`, `strict`).
4. Validate with the `plugin-validator` agent from `plugin-dev`.
5. For non-trivial additions, write a staged plan first (the `planning-projects` skill).

## License

MIT unless a plugin's own LICENSE states otherwise; most plugins carry their own LICENSE file.
