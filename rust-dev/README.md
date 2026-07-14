# rust-dev

Idiomatic Rust authoring for Claude Code. Part of the [`coder-plugins`](..) marketplace.

## What it does

Pairs a thin progressive-disclosure **skill** (`rust-coding`) that fires on any Rust work and routes to shared `references/`, with a senior-engineer **subagent** (`rust-expert`) that authors, reviews, refactors, audits, and migrates Rust while citing sources by name (Rust API Guidelines, Microsoft Pragmatic Rust, *Effective Rust*, *Programming Rust*, tokio docs, Rust Performance Book, RustSec). Both read the same plugin-level `references/`, so the domain knowledge has one source of truth.

Opinionated defaults: no locks across `.await`, `// SAFETY:` on every `unsafe`, `thiserror` in libraries / `anyhow` in applications, iterators over index loops, `&str`/`&[T]` at API boundaries, `cargo clippy -- -D warnings` in CI.

## Determinism boundary

Mechanical checks live in a deterministic bash lane (`scripts/`, vendored from
the plugin-dev determinism kit); judgment stays with the skill and agent, which
run the scripts and consume their JSON instead of re-deriving rules in prose.

- `scripts/validate-cargo.sh` — manifest invariants: TOML parse, edition enum, edition↔MSRV consistency, wildcard deps, workspace members on disk, lockfile, toolchain channel.
- `scripts/validate-safety.sh` — regex *candidates* for the house rules over `.rs` sources (unsafe without `// SAFETY:`, `.unwrap()` outside tests, unbounded channels, std-sync-lock-in-async, `Box<dyn Error>` in pub APIs, `Deserialize` without `deny_unknown_fields`). Candidates are `warn`; rust-expert confirms or dismisses each.
- `scripts/stack-report.sh` — deterministic Stack Report (edition, MSRV, runtime, test layout, risk surfaces, CI invocations) consumed by rust-expert's Protocol 1.

Run the lane: `bash scripts/validate.sh <project-root> [--json]`. Rule ids
and severities are documented in [`scripts/README.md`](scripts/README.md).

## Installation

```bash
/plugin marketplace add sureserverman/coder-plugins
/plugin install rust-dev@coder-plugins
```

## Components

Two components — a thin skill and a full agent — over one shared `references/` set.

### Skill

| Skill | Triggers when |
|---|---|
| `rust-coding` | greenfield Rust requests, `*.rs`/`Cargo.toml` edits, `unsafe`/async/FFI changes, clippy warnings, borrow-checker errors, edition migration, idiom questions |

`rust-coding` is a lean **knowledge router**: it maps the situation to the matching
`references/` file (API design, error handling, async, unsafe, FFI, performance, edition-2024,
idioms — one level deep at `references/`) and hands deep or output-heavy work to `rust-expert`.

### Agent

| Agent | Model | Tools | Purpose |
|---|---|---|---|
| `rust-expert` | sonnet | Read, Grep, Glob, Edit, Write, Bash, WebFetch | Authors, reviews, refactors, audits, and migrates Rust. Six protocols (Stack Detection → Author / Refactor / Review / Migrate / Audit) plus three direct **modes**: `review`, `idiomize`, `project-audit`. Reads the shared `references/`; cites sources. |

### Migration note

The `rust-project` skill and the `/rust-review` and `/rust-idiomize` commands were **folded into
`rust-expert`** as its `project-audit`, `review`, and `idiomize` modes — one agent, invoked
directly, instead of separate entry points. The 5-pass audit runner moved to `scripts/analyze.sh`.
When `rust-dev` isn't enabled in a session, `rust-expert` is still reachable from disk via
`capability-index.json` (see the marketplace's capability-router) — its `.md` body is injected
into a generic subagent with its `model` pin, so the expertise doesn't require enabling the plugin.

## License

MIT
