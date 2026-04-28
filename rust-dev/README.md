# rust-dev

Idiomatic Rust authoring for Claude Code. Part of the [`coder-plugins`](..) marketplace.

## What it does

Pairs a progressive-disclosure **skill** that fires on any Rust work with a senior-engineer **subagent** that authors, reviews, and refactors Rust code while citing sources by name (Rust API Guidelines, Microsoft Pragmatic Rust, *Effective Rust*, *Programming Rust*, tokio docs, Rust Performance Book, RustSec).

Opinionated defaults: no locks across `.await`, `// SAFETY:` on every `unsafe`, `thiserror` in libraries / `anyhow` in applications, iterators over index loops, `&str`/`&[T]` at API boundaries, `cargo clippy -- -D warnings` in CI.

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
