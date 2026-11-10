---
name: rust-coding
description: Use when authoring, scaffolding, refactoring, or reviewing Rust code. Triggers on greenfield requests like "create a Rust app" or "cargo new", *.rs edits, unsafe blocks, async/tokio code, and questions like "is this idiomatic Rust" or "thiserror or anyhow".
---

# rust-coding

## Owner rules the scripts check

`validate-safety.sh` flags candidates for these by stable rule id. Confirming each candidate and writing the fix is your call.

- `unsafe` carries a `// SAFETY:` comment (`rust-unsafe-missing-safety-comment`).
- No `std::sync` lock held across `.await` (`rust-sync-lock-in-async-candidate`).
- Channels are bounded (`rust-unbounded-channel`).
- No `Box<dyn Error>` in a pub API (`rust-box-dyn-error-in-pub-api`).
- No `.unwrap()` outside tests (`rust-unwrap-outside-tests`).
- `Deserialize` types use `deny_unknown_fields` (`rust-serde-missing-deny-unknown`).

`validate-cargo.sh` decides manifest invariants: edition enum, edition↔MSRV consistency, wildcard deps, workspace members, lockfile, toolchain channel. `stack-report.sh` produces the project Stack Report.

When auditing existing code, run the lane instead of grepping by hand:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh" <project-root> --json
```

Rule ids and severities: `${CLAUDE_PLUGIN_ROOT}/scripts/README.md`.

## Gotchas (from prior incidents — see vault [[Rust]])

1. **`#[cfg(test)]` items in a library are invisible to integration tests** in `tests/`. Cargo compiles integration tests as a *separate crate* that links the lib as a downstream user. Fix: drop the gate and mark `#[doc(hidden)]`, or gate behind a `testing` Cargo feature with `[[test]] required-features = ["testing"]`.
2. **`BufRead::read_line() == 0` means EOF, not "nothing yet".** Treating it as no-op → infinite loop that appends empty strings until OOM. Always `break` on `n == 0`.
3. **`Command::new("x").arg("y")` without `.status()` / `.output()` / `.spawn()` does nothing.** The builder drops silently with no warning. Always chain an execution method.
4. **`reqwest`'s `json` Cargo feature is not default.** `resp.json::<T>()` fails compile with "method not found". Enable with `reqwest = { version = "0.12", features = ["json"] }`.
5. **Circular module dependencies in workspaces** are rejected by the compiler. Fix: move the shared item into the more semantically-appropriate module.
6. **NVPTX (CUDA) builds require nightly.** `ptx-linker` was removed from stable; use `llvm-bitcode-linker`. Old `ptx-linker` installs break new builds. First NVPTX build takes minutes — use `-vv` to see progress.
7. **Rust edition changes are opt-in.** `cargo fix --edition` walks a crate forward one edition at a time. Edition 2024 (released with 1.85.0, 2025-02-20) changed `if let` temp-scope rules, RPIT hidden-lifetime capture, and unsafe-attribute syntax.
8. **Feature-flag deprecations cascade.** Before a version bump, `grep -r 'features = \["'` across the repo and align with upstream rename (e.g., `collab` → `multi_agent` in matrix-rust-sdk).

## Related

- Security review: `sec-review` skill → `sec-review:rust-runner` subagent.
