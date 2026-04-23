---
name: rust-coding
description: Use when authoring, scaffolding, refactoring, or reviewing Rust code. Triggers on greenfield requests like "create a Rust app", "create a Rust CLI", "new Rust project", "scaffold a Rust crate", "cargo new", "start a Rust library", "initialize a Rust workspace", "build a Rust binary that...", "write me a Rust service", or any "in Rust" / "using Rust" request to build something from scratch. Also triggers on `*.rs` edits, `Cargo.toml` or `Cargo.lock` changes, `unsafe` blocks, `async`/`tokio` code, FFI bindings (`extern "C"`, `#[repr(C)]`, cxx, bindgen), `serde` derives, `thiserror`/`anyhow` error enums, `clippy` warnings, borrow-checker errors (E0382, E0502, E0505, E0597, E0716), edition 2024 migration, and `cargo fix` output. Also triggers on questions like "is this idiomatic Rust", "why does the borrow checker reject this", "should this be `Arc` or `Rc`", "how do I avoid lifetime 'a here", "should I use `thiserror` or `anyhow`", "is this unsafe block sound", "this tokio task deadlocks", "my clippy lint is complaining".
---

# rust-coding

Opinionated decision rules for writing high-quality Rust. Consult the matching `references/` file when the decision gets deep.

## Reference map (progressive disclosure)

| When you're… | Read first |
|---|---|
| Designing a public API or trait | `references/api-design.md` |
| Writing new Rust code of any kind | `references/idioms.md` |
| Building error types or `?`-using code | `references/error-handling.md` |
| Writing or reviewing `unsafe` | `references/unsafe.md` |
| Writing `async`/`await` or `tokio` code | `references/async.md` |
| Writing `extern "C"`, `cxx`, `bindgen`, `cbindgen` | `references/ffi.md` |
| Optimizing a hot path or reading a flamegraph | `references/performance.md` |
| Migrating a crate edition or reading 2024 features | `references/edition-2024.md` |

## Non-negotiable rules

These apply to every Rust change. No exceptions without an explicit `// NOTE:` explaining why.

1. **Every `unsafe` block carries a `// SAFETY:` comment** stating the invariants the caller relies on. Minimize block scope — smaller block, smaller blast radius.
2. **Never hold a lock across `.await`.** Release the guard or switch to a lock-free design. This serializes entire services under load.
3. **Bound every channel.** `tokio::mpsc::unbounded_channel()` is for compile-time-known-small fanout only. Attacker-controlled fanout → DoS.
4. **`#[serde(deny_unknown_fields)]` on every type deserialized from external input.** Fail closed.
5. **Errors: `thiserror` in libraries, `anyhow` in binaries.** `Box<dyn Error>` in public APIs is an anti-pattern.
6. **No `.unwrap()` / `.expect()` outside `main`, tests, `OnceCell::get`, or where a panic is the documented contract.** Everything else uses `?`.
7. **`&str` and `&[T]` at API boundaries.** Take `impl AsRef<str>` / `impl Into<String>` when you must; never demand `String` you don't own.
8. **Iterators over index loops.** LLVM optimizes them equal-or-better; they compose; they don't OOB.
9. **Run `cargo clippy -- -D warnings` in CI.** Treat clippy warnings as bugs.
10. **`rustfmt` default config.** No bikeshedding; commit `rustfmt.toml` only when a specific hard constraint forces it.

## Decision shortcuts

### Which smart pointer?
- Single-owner, heap-allocated value → `Box<T>`
- Shared ownership, single-threaded → `Rc<T>` (rare outside trees/graphs)
- Shared ownership, threads → `Arc<T>`
- Interior mutability, single-threaded → `RefCell<T>`, `Cell<T>`
- Interior mutability, threads → `Mutex<T>` / `RwLock<T>` (or `parking_lot` for non-poisoning)
- **Default to owned `T` or `&T`.** `Rc`/`Arc` is almost never the first answer.

### Which error strategy?
- Library crate that others depend on → `thiserror` enum per module with variants that carry context fields, never `String`
- Binary crate at the top level → `anyhow::Result` + `.context("what I was doing")` chains
- FFI boundary → opaque error code + `thread_local` last-error buffer (see `references/ffi.md`)

### `impl Trait` vs generic vs `dyn`?
- Return position: `impl Trait` unless you need trait objects in a collection
- Argument position: generic (`fn foo<T: Read>`) unless dynamic dispatch is a hard requirement
- `dyn Trait`: heap-allocated trait objects; cost is one vtable indirection — acceptable when values are heterogeneous or the API already requires `Box`

### Async runtime?
- `tokio` for network services (ecosystem dominance, multi-thread scheduler)
- `smol` / `async-std` only when a tight dep surface is mandatory
- **Never mix runtimes.** Crates that pick a runtime must document it.

## Gotchas (from prior incidents — see vault [[Rust]])

1. **`#[cfg(test)]` items in a library are invisible to integration tests** in `tests/`. Cargo compiles integration tests as a *separate crate* that links the lib as a downstream user. Fix: drop the gate and mark `#[doc(hidden)]`, or gate behind a `testing` Cargo feature with `[[test]] required-features = ["testing"]`.
2. **`BufRead::read_line() == 0` means EOF, not "nothing yet".** Treating it as no-op → infinite loop that appends empty strings until OOM. Always `break` on `n == 0`.
3. **`Command::new("x").arg("y")` without `.status()` / `.output()` / `.spawn()` does nothing.** The builder drops silently with no warning. Always chain an execution method.
4. **`reqwest`'s `json` Cargo feature is not default.** `resp.json::<T>()` fails compile with "method not found". Enable with `reqwest = { version = "0.12", features = ["json"] }`.
5. **Circular module dependencies in workspaces** are rejected by the compiler. Fix: move the shared item into the more semantically-appropriate module.
6. **NVPTX (CUDA) builds require nightly.** `ptx-linker` was removed from stable; use `llvm-bitcode-linker`. Old `ptx-linker` installs break new builds. First NVPTX build takes minutes — use `-vv` to see progress.
7. **Rust edition changes are opt-in.** `cargo fix --edition` walks a crate forward one edition at a time. Edition 2024 (released with 1.85.0, 2025-02-20) changed `if let` temp-scope rules, RPIT hidden-lifetime capture, and unsafe-attribute syntax.
8. **Feature-flag deprecations cascade.** Before a version bump, `grep -r 'features = \["'` across the repo and align with upstream rename (e.g., `collab` → `multi_agent` in matrix-rust-sdk).

## When to hand off to the subagent

Invoke `rust-expert` (via `/rust-review` or `/rust-idiomize`) when:

- The change spans more than ~3 files — main-context authoring loses global view
- An `unsafe` block needs an extracted safety contract with Miri-runnable tests
- A migration to edition 2024 is being planned
- Clippy output has more than ~5 lints and you want a prioritized triage
- Refactoring a module from imperative loops → iterator chains
- Typestate or sealed-trait design is on the table

Otherwise, apply the rules above inline and move on.

## Related

- Authoring subagent: `rust-expert` (in this plugin)
- Slash commands: `/rust-review`, `/rust-idiomize`
- Project-wide audit: the existing `rust-project` skill (clippy + cargo audit + cargo deny + unused deps + cross-compile)
- Security review: `sec-review` skill → `sec-review:rust-runner` subagent
