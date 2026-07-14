---
name: rust-coding
description: Use when authoring, scaffolding, refactoring, or reviewing Rust code. Triggers on greenfield requests like "create a Rust app" or "cargo new", *.rs edits, unsafe blocks, async/tokio code, and questions like "is this idiomatic Rust" or "thiserror or anyhow".
---

# rust-coding

Opinionated decision rules for writing high-quality Rust. Consult the matching `../../references/` file when the decision gets deep.

## Reference map (progressive disclosure)

| When you're… | Read first |
|---|---|
| Designing a public API or trait | `../../references/api-design.md` |
| Writing new Rust code of any kind | `../../references/idioms.md` |
| Building error types or `?`-using code | `../../references/error-handling.md` |
| Writing or reviewing `unsafe` | `../../references/unsafe.md` |
| Writing `async`/`await` or `tokio` code | `../../references/async.md` |
| Writing `extern "C"`, `cxx`, `bindgen`, `cbindgen` | `../../references/ffi.md` |
| Optimizing a hot path or reading a flamegraph | `../../references/performance.md` |
| Migrating a crate edition or reading 2024 features | `../../references/edition-2024.md` |

## Determinism boundary

The mechanically detectable slice of the rules below is script-owned, not
prose-owned. When *auditing* existing code (not authoring new code), run the
plugin's deterministic lane instead of grepping by hand:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh" <project-root> --json
```

`validate-cargo.sh` decides manifest invariants (edition enum, edition↔MSRV
consistency, wildcard deps, workspace members, lockfile, toolchain channel).
`validate-safety.sh` flags *candidates* for rules 1–7 below by stable rule id
(`rust-unsafe-missing-safety-comment`, `rust-unwrap-outside-tests`,
`rust-unbounded-channel`, `rust-sync-lock-in-async-candidate`,
`rust-box-dyn-error-in-pub-api`, `rust-serde-missing-deny-unknown`) — confirming
each candidate and writing the fix is judgment and stays here.
`stack-report.sh` produces the project Stack Report. See `scripts/README.md`.

The full rules, decision shortcuts (smart-pointer / error-strategy / `impl Trait` vs `dyn` /
runtime choice), and citations for each domain live in the reference files mapped above —
**Read the matching one** rather than working from memory; this skill no longer restates
them. The mechanically-checkable subset (rules for `unsafe`, locks-across-await, unbounded
channels, `deny_unknown_fields`, `Box<dyn Error>`, `.unwrap()` outside tests) is enforced by
the deterministic lane above — run it when auditing, don't grep by hand.

## Gotchas (from prior incidents — see vault [[Rust]])

1. **`#[cfg(test)]` items in a library are invisible to integration tests** in `tests/`. Cargo compiles integration tests as a *separate crate* that links the lib as a downstream user. Fix: drop the gate and mark `#[doc(hidden)]`, or gate behind a `testing` Cargo feature with `[[test]] required-features = ["testing"]`.
2. **`BufRead::read_line() == 0` means EOF, not "nothing yet".** Treating it as no-op → infinite loop that appends empty strings until OOM. Always `break` on `n == 0`.
3. **`Command::new("x").arg("y")` without `.status()` / `.output()` / `.spawn()` does nothing.** The builder drops silently with no warning. Always chain an execution method.
4. **`reqwest`'s `json` Cargo feature is not default.** `resp.json::<T>()` fails compile with "method not found". Enable with `reqwest = { version = "0.12", features = ["json"] }`.
5. **Circular module dependencies in workspaces** are rejected by the compiler. Fix: move the shared item into the more semantically-appropriate module.
6. **NVPTX (CUDA) builds require nightly.** `ptx-linker` was removed from stable; use `llvm-bitcode-linker`. Old `ptx-linker` installs break new builds. First NVPTX build takes minutes — use `-vv` to see progress.
7. **Rust edition changes are opt-in.** `cargo fix --edition` walks a crate forward one edition at a time. Edition 2024 (released with 1.85.0, 2025-02-20) changed `if let` temp-scope rules, RPIT hidden-lifetime capture, and unsafe-attribute syntax.
8. **Feature-flag deprecations cascade.** Before a version bump, `grep -r 'features = \["'` across the repo and align with upstream rename (e.g., `collab` → `multi_agent` in matrix-rust-sdk).

## When to hand off to rust-expert

Apply the reference rules inline for focused changes. **Hand off to the `rust-expert`
subagent** (its review / idiomize / project-audit modes) —
delegate-by-signal: independent + output-heavy + not latency-critical — when
the change spans more than ~3 files, an `unsafe` block needs an extracted safety contract
with Miri-runnable tests, an edition-2024 migration is being planned, clippy has more than
~5 lints to triage, or typestate / sealed-trait design is on the table. It runs the same
`references/` plus the deterministic lane (and its project-audit / review / idiomize modes)
in its own context window.

## Related

- Authoring subagent `rust-expert` (this plugin) — its **review**, **idiomize**, and
  **project-audit** modes cover scoped review, behavior-preserving refactor, and whole-project audit.
- Security review: `sec-review` skill → `sec-review:rust-runner` subagent.
