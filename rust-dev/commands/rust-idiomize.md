---
description: >
  Dispatch the rust-expert subagent to refactor a Rust file or module to
  idiomatic Rust — tighten API signatures, replace index loops with iterators,
  remove unnecessary clones, add `// SAFETY:` comments, fix lock-across-await,
  modernize error handling.
argument-hint: "<path-to-file-or-directory>"
allowed-tools: Bash(bash:*)
---

# /rust-idiomize

Delegates a behavior-preserving refactor to the **rust-expert** subagent (Protocol 3 — Refactor).

## Scope

`$ARGUMENTS` is the target path. If empty, ask the user for a path — do not refactor the whole repo implicitly.

## Dispatch

Call the rust-expert subagent with:

1. **Protocol 1 (Stack detection)** — run `scripts/stack-report.sh` for edition, MSRV, runtime, test invocation.
2. **Record baseline** — run `cargo test` on the relevant package (require green) and `bash "${CLAUDE_PLUGIN_ROOT}/scripts/validate-safety.sh" <root> --json` to enumerate mechanical idiom candidates by rule id.
3. **Protocol 3 (Refactor)** — triage the script's candidates (confirm or dismiss each), add judgment-only idioms, then apply fixes ONE at a time, re-running `cargo test` + `cargo clippy -- -D warnings` after each change.
4. **Re-run the safety scan** at the end — confirmed candidates should be gone; anything remaining is listed as deferred with a reason.

## Constraints (enforced by the agent)

- **Never change behavior.** If a bug is found during refactor, surface it as a separate finding and do not fix it in the same pass.
- **Never break a public API** without explicit user confirmation. If the refactor requires a signature change, stop and ask.
- **One logical change at a time**, with the test suite green at each step. No "refactored the whole module in one diff" commits.
- **MSRV-respectful.** Check `rust-version` in `Cargo.toml` before using a newer language feature.

## Expected output

1. **Stack Report**
2. **Baseline** — `cargo test` summary (pass count)
3. **Refactor Report** (from the agent's output schema):
   - Rules applied (from rust-expert's House rules list)
   - Files touched with hunk counts
   - Final test result
   - Any deferred items the user should review separately
4. **Diff** — the actual changes applied (can be reviewed via `git diff`).
5. **Safety re-scan** — `validate-safety.sh` candidate counts before vs after.

## Common targets

Use this command when:

- A module has accumulated `.unwrap()` / `.clone()` / `String` parameters that should be `&str`
- A `match` ladder could become `if let` / `let else`
- A `Vec<Result<_, _>>` collection could use `try_collect`
- A `Box<dyn Error>` public API should become a `thiserror` enum
- An `async fn` holds a lock across `.await`
- A struct's `new` has ≥ 4 args and wants a typestate builder
- `cargo fix --edition` left behind manual cleanup

## Notes

- For a *non-editing* review only, use `/rust-review`.
- For a project-wide audit (deps, clippy, cross-compile), use `/rust-project`.
