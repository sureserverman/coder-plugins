# rust-dev

Idiomatic Rust authoring for Claude Code. Part of the [`coder-plugins`](..) marketplace.

## What it does

A deterministic lane for Rust work, behind two commands: `rust-dev-validate <project-root> --json` runs it, `rust-dev-stack-report` prints the stack report. The owner's house rules and gotchas from past incidents live in the vault stack page `Portfolio/stacks/rust.md`; vault-context adds it to a session that starts in a project holding a Rust file (CP DEC-043). The commands exist only where this plugin is enabled.

House rules: `// SAFETY:` on every `unsafe`, no locks across `.await`, bounded channels, `thiserror` in libraries / `anyhow` in binaries, no `.unwrap()` outside `main` and tests, `deny_unknown_fields` on types deserialized from external input.

## Determinism boundary

Mechanical checks live in a deterministic bash lane (`scripts/`, vendored from
the plugin-dev determinism kit); judgment stays with the model, which runs the
scripts and consumes their JSON instead of re-deriving rules in prose.

- `scripts/validate-cargo.sh` — manifest invariants: TOML parse, edition enum, edition↔MSRV consistency, wildcard deps, workspace members on disk, lockfile, toolchain channel.
- `scripts/validate-safety.sh` — regex *candidates* for the house rules over `.rs` sources (unsafe without `// SAFETY:`, `.unwrap()` outside tests, unbounded channels, std-sync-lock-in-async, `Box<dyn Error>` in pub APIs, `Deserialize` without `deny_unknown_fields`). Candidates are `warn`; the model confirms or dismisses each.
- `scripts/stack-report.sh` — deterministic Stack Report (edition, MSRV, runtime, test layout, risk surfaces, CI invocations) for stack detection.

Run the lane: `rust-dev-validate <project-root> [--json]` (or `bash scripts/validate.sh`). Rule ids
and severities are documented in [`scripts/README.md`](scripts/README.md).

## Installation

```bash
/plugin marketplace add sureserverman/coder-plugins
/plugin install rust-dev@coder-plugins
```

## Components

### Commands

| Command | What it runs |
|---|---|
| `rust-dev-validate <root> [--json]` | `scripts/validate.sh`: manifest invariants and house-rule candidates |
| `rust-dev-stack-report <root>` | `scripts/stack-report.sh` |

The house rules, by the rule id the scripts flag them under, and eight gotchas from past
incidents are in the vault stack page, not in this plugin. Generic Rust craft is left to the model.

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

The session already holds the Rust stack page (vault-context adds it at start), so the
house rules and gotchas apply. To audit a crate, the model runs `rust-dev-validate . --json`
and confirms each candidate it flags.

## Related plugins

- **`vault-context`** (obsidian-wiki) — adds the vault's Rust stack page to a session that
  starts in a Rust project.
- **`planning`** — `decisions` is where a Rust-wide constraint gets promoted to the `rust`
  domain register so every Rust project inherits it.
- **`infra-build`** — `build-for-mac` packages Rust source repos into macOS `.pkg`.

## License

MIT
