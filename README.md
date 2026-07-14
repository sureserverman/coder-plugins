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
| [`business`](./business) | Business-planning pipeline, sibling to `planning`: assess viability, revenue-model, deep cited market-research, compose a full business plan, launch, track, portfolio roll-up. |
| [`git-github`](./git-github) | Everyday git/GitHub ops: commits and PRs in the repo's style, code review, multi-model second opinions, comment/workflow/license/README audits, release tags. |
| [`testing`](./testing) | `testing-expert` subagent: run and triage tests, author new ones, audit coverage and test smells. Test pyramid, mutation-over-line-coverage opinions. |
| [`rust-dev`](./rust-dev) | Idiomatic Rust: `rust-coding` knowledge-router skill (fires on `*.rs`/`Cargo.toml` edits) + `rust-expert` subagent (author/review/idiomize/audit/migrate modes), over one shared `references/` set. |
| [`android-dev`](./android-dev) | Gradle build management, per-stage on-device verify gate, bundled multi-emulator + MCP + mock-server stack under `infrastructure/`, `/android-screenshots`. |
| [`game-dev`](./game-dev) | Source-cited game design/dev: a `game-dev` knowledge-router skill + `game-design-expert` subagent (mechanics, feel/juice, camera, UX/FTUE, accessibility, architecture across Godot/Unity/Unreal) over one shared `references/` set, plus `/game-review`, `/game-mechanic`. |
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

### Description budget

Every enabled plugin's skill/agent/command `description` frontmatter is injected
into model context at session start, whether or not the component is used, so
descriptions are a shared always-on cost. Keep each **≤ 300 characters**: lead
with the use case, then the 3–4 strongest trigger phrases. Don't add a
`commands/` wrapper whose description just duplicates a skill's — a skill is
already invocable as `/<plugin>:<skill>`, so the wrapper only doubles the cost.

`scripts/check-frontmatter-budget.py` enforces this (and rejects invalid-YAML
frontmatter — an unquoted description containing `: ` needs single-quoting).
Run it before opening a PR:

```bash
python3 scripts/check-frontmatter-budget.py --max 300   # exits non-zero on any violation
python3 scripts/check-frontmatter-budget.py --summary    # per-plugin injected vs dispatch-only chars
```

Two further levers keep the footprint down:

- **Dispatch-only components** (`disable-model-invocation: true`) ship and stay
  user-invocable but their descriptions aren't injected — for skills only ever reached
  through an orchestrator (release-promo's channel skills, `i18n-formats`).
- **`capability-index.json`** (generated by `scripts/build-capability-index.py`, kept fresh
  in CI) maps every component to its on-disk path, so plan execution and the
  `planning:capability-router` skill can resolve a skill or agent **from disk without its
  plugin being enabled** — Read-and-follow a skill, or inject an agent's body with its
  `model` pin. This lets a plugin stay agent-centric (a few big components) instead of many
  always-on skill descriptions.

CI runs it on every push via `.github/workflows/validate-frontmatter-budget.yml`.
Rare, justified exceptions go in `scripts/frontmatter-budget-allow.txt` with a
reason.

## License

MIT unless a plugin's own LICENSE states otherwise; most plugins carry their own LICENSE file.
