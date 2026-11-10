# rust-dev

Idiomatic Rust authoring for Claude Code. Part of the [`coder-plugins`](..) marketplace.

## What it does

One **skill** (`rust-coding`) that fires on any Rust work. It carries the owner's house rules and gotchas from past incidents, and points at the deterministic lane below.

Opinionated defaults: no locks across `.await`, `// SAFETY:` on every `unsafe`, `thiserror` in libraries / `anyhow` in applications, iterators over index loops, `&str`/`&[T]` at API boundaries, `cargo clippy -- -D warnings` in CI.

## Determinism boundary

Mechanical checks live in a deterministic bash lane (`scripts/`, vendored from
the plugin-dev determinism kit); judgment stays with the skill, which
runs the scripts and consume their JSON instead of re-deriving rules in prose.

- `scripts/validate-cargo.sh` — manifest invariants: TOML parse, edition enum, edition↔MSRV consistency, wildcard deps, workspace members on disk, lockfile, toolchain channel.
- `scripts/validate-safety.sh` — regex *candidates* for the house rules over `.rs` sources (unsafe without `// SAFETY:`, `.unwrap()` outside tests, unbounded channels, std-sync-lock-in-async, `Box<dyn Error>` in pub APIs, `Deserialize` without `deny_unknown_fields`). Candidates are `warn`; the model confirms or dismisses each.
- `scripts/stack-report.sh` — deterministic Stack Report (edition, MSRV, runtime, test layout, risk surfaces, CI invocations) for stack detection.

Run the lane: `bash scripts/validate.sh <project-root> [--json]`. Rule ids
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

`rust-coding` lists the owner's house rules by the rule id the scripts flag them under, plus
eight gotchas from past incidents. Generic Rust craft is left to the model.

The 5-pass audit runner is `scripts/analyze.sh`.

## Artifacts

Nothing persisted outside your own source tree. The audit runner (`scripts/analyze.sh`, 5 passes) prints its report rather than writing
one. Prerequisite: a working Rust toolchain — `cargo`, and `clippy` / `cargo-audit` for the
lane and audit runner (their absence is reported, not silently skipped).

## Worked example

```text
/plugin install rust-dev@coder-plugins

"add a retry wrapper around the HTTP client"
```

Editing `.rs` fires `rust-coding`, which applies the house rules and gotchas. To audit a crate,
the skill runs the deterministic lane and confirms each candidate it flags.

## Related plugins

- **`planning`** — `dispatching-parallel-agents` routes Rust tasks here via `stack-routing.md`,
  loading `rust-coding` first; `decisions` is where a Rust-wide constraint gets promoted to the
  `rust` domain register so every Rust project inherits it.
- **`infra-build`** — `build-for-mac` packages Rust source repos into macOS `.pkg`.

## License

MIT
