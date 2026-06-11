# rust-dev

Idiomatic Rust authoring for Claude Code. Part of the [`coder-plugins`](..) marketplace.

## What it does

Pairs a progressive-disclosure **skill** that fires on any Rust work with a senior-engineer **subagent** that authors, reviews, and refactors Rust code while citing sources by name (Rust API Guidelines, Microsoft Pragmatic Rust, *Effective Rust*, *Programming Rust*, tokio docs, Rust Performance Book, RustSec).

Opinionated defaults: no locks across `.await`, `// SAFETY:` on every `unsafe`, `thiserror` in libraries / `anyhow` in applications, iterators over index loops, `&str`/`&[T]` at API boundaries, `cargo clippy -- -D warnings` in CI.

## Determinism boundary

Mechanical checks live in a deterministic bash lane (`scripts/`, vendored from
the plugin-dev determinism kit); judgment stays with the skill and agent, which
run the scripts and consume their JSON instead of re-deriving rules in prose.

- `scripts/validate-cargo.sh` — manifest invariants: TOML parse, edition enum, edition↔MSRV consistency, wildcard deps, workspace members on disk, lockfile, toolchain channel.
- `scripts/validate-safety.sh` — regex *candidates* for the house rules over `.rs` sources (unsafe without `// SAFETY:`, `.unwrap()` outside tests, unbounded channels, std-sync-lock-in-async, `Box<dyn Error>` in pub APIs, `Deserialize` without `deny_unknown_fields`). Candidates are `warn`; rust-expert confirms or dismisses each.
- `scripts/stack-report.sh` — deterministic Stack Report (edition, MSRV, runtime, test layout, risk surfaces, CI invocations) consumed by rust-expert's Protocol 1.

Run the lane: `bash scripts/validate.sh <rust-project-root> [--json]`. Rule ids
and severities are documented in [`scripts/README.md`](scripts/README.md).

## Installation

```bash
/plugin marketplace add sureserverman/coder-plugins
/plugin install rust-dev@coder-plugins
```

## Components

### Skill

| Skill | Triggers when |
|---|---|
| `rust-coding` | greenfield Rust requests, `*.rs`/`Cargo.toml` edits, `unsafe`/async/FFI changes, clippy warnings, borrow-checker errors, edition migration, idiom questions |

The skill body is lean; depth lives in `references/` (one level deep) covering API design, error handling, async, unsafe, FFI, performance, and CI policy.

### Agent

| Agent | Model | Tools | Purpose |
|---|---|---|---|
| `rust-expert` | sonnet | Read, Grep, Glob, Edit, Write, Bash, WebFetch | Authors and refactors Rust through six protocols (Stack Detection → Author / Refactor / Review / Migrate / Audit). Cites sources. |

### Commands

- `/rust-review [file | commit | PR]` — dispatch `rust-expert` to review a scoped Rust diff for idiom, safety, concurrency, and performance.
- `/rust-idiomize <path>` — dispatch `rust-expert` to refactor a file or module to idiomatic Rust (tighten signatures, replace index loops with iterators, remove unnecessary clones, add `// SAFETY:` comments, fix lock-across-await, modernize error handling).

## License

MIT
