# Edition 2024

Rust editions are opt-in, backwards-incompatible language evolutions. Edition 2024 was released with **Rust 1.85.0 on 2025-02-20**. Each crate declares its edition in `Cargo.toml`:

```toml
[package]
edition = "2024"
```

Crates of different editions interoperate freely — a 2021 crate can depend on a 2024 crate and vice versa.

## Migrating

```
cargo fix --edition
```

`cargo fix` walks a crate forward one edition at a time, rewriting the code where changes are deterministic. Review the diff, run tests, commit, repeat until at 2024.

Run `cargo fix --edition` on a clean working tree. Fix any manual issues it reports. Then bump `edition = "2024"` in `Cargo.toml` and re-run `cargo check`.

## What changed in 2024

### `if let` temporary scope

Edition 2021 extended the temporary in an `if let` scrutinee to the end of the enclosing block. Edition 2024 ends the temporary at the end of the `if let` itself. This fixes a class of hard-to-spot deadlocks:

```rust
// pre-2024: the MutexGuard lived until end of enclosing fn — deadlock with inner lock
if let Some(x) = self.map.lock().unwrap().get(&key).cloned() { ... }
// another self.map.lock() call below deadlocks

// 2024: guard released at end of if let — fine
```

Audit every `if let` that scrutinizes a `MutexGuard`, `RefMut`, or other lock-like object when migrating.

### RPIT hidden-lifetime capture

`impl Trait` in return position now captures **all** in-scope generic lifetimes by default. Pre-2024, some lifetimes were hidden, causing surprising "borrowed value does not live long enough" errors.

Opt out with `use<>`:

```rust
// captures 'a
fn foo<'a>(x: &'a str) -> impl Debug { ... }

// explicitly captures nothing (edition 2024+)
fn foo<'a>(x: &'a str) -> impl Debug + use<> { ... }
```

Rare in practice; the new default matches intuition.

### Unsafe attributes

Attributes that can cause UB (`#[no_mangle]`, `#[export_name]`, `#[link_section]`) now require `unsafe(...)` syntax:

```rust
// pre-2024
#[no_mangle]
pub extern "C" fn foo() { ... }

// 2024
#[unsafe(no_mangle)]
pub extern "C" fn foo() { ... }
```

`cargo fix --edition` adds the `unsafe(...)` wrapper automatically.

### `gen` blocks (iterators)

`gen` blocks produce iterators with ergonomic syntax:

```rust
fn primes_below(n: u64) -> impl Iterator<Item = u64> {
    gen {
        for candidate in 2..n {
            if is_prime(candidate) { yield candidate; }
        }
    }
}
```

`yield` is a keyword; named `gen` is reserved. As of 1.95.0, `gen` blocks are stabilized for the synchronous case; `async gen` remains nightly.

### `#[expect]` attribute

Complement to `#[allow]`: lints your code *expects* to emit. If the lint stops firing (because you fixed the underlying issue), you get a warning:

```rust
#[expect(clippy::too_many_arguments)]
fn big_fn(a: u32, b: u32, c: u32, d: u32, e: u32, f: u32, g: u32, h: u32) { ... }
```

Useful during migrations where you *plan* to clean up later.

### Other 2024 changes

- **Disjoint closure captures** now fully consistent with struct field access — closures capture the minimum necessary fields, not the whole struct.
- **Reserved prefix syntax** — `k#keyword`, `c"null-terminated"`, reserved since 2021 edition.
- **Make `Box<T>`, `Vec<T>` / etc. iterators into `IntoIterator` by value** when appropriate — matches intuition.
- **Macro fragment specifier `$expr`** now accepts `const { ... }` and `_` — rarely affects user code.

## Stabilizations worth knowing (1.85 → 1.95)

- **`cfg_select!`** (1.95) — built-in replacement for the `cfg-if` crate.
- **`if let` chains** — chain `if let` with `&&` and other `if let`:
  ```rust
  if let Some(a) = x && let Some(b) = y && a + b > 10 { ... }
  ```
- **`Vec::push_mut` / `insert_mut`** (1.95) — return `&mut T` to the newly-inserted element.
- **`AtomicPtr::update` / `AtomicBool::try_update`** (1.95).
- **`let chains` in `while let`** — similar to `if let` chains.
- **`async fn` in traits** — stable since 1.75; no need for `async-trait` crate for most cases.
- **`Return position impl Trait in Trait (RPITIT)`** — stable since 1.75.

## MSRV hygiene when migrating

- Commit MSRV in `Cargo.toml` (`rust-version = "1.85"`).
- Bump MSRV deliberately — it's a breaking change for some org policies.
- Run CI against both MSRV and stable.
- `cargo check --locked --all-targets` in CI catches accidental feature-use from a newer compiler.

## Workspaces and editions

- Workspaces can have mixed editions across members.
- Set `edition = "2024"` in `[workspace.package]` and have members use `edition.workspace = true` to keep them aligned:
  ```toml
  # workspace Cargo.toml
  [workspace.package]
  edition = "2024"
  rust-version = "1.85"

  # member Cargo.toml
  [package]
  edition.workspace = true
  rust-version.workspace = true
  ```
- `resolver = "3"` (available in edition 2024) improves workspace dep-feature unification.

## Common migration gotchas

1. **`if let` temp-scope change exposes latent deadlocks** — audit lock-holding `if let`s.
2. **`impl Trait` captures more lifetimes** — some code that compiled on 2021 errors on 2024 with "type `Foo<'a>` does not live long enough". Fix: add the lifetime to the return type explicitly or use `+ use<>` to opt out.
3. **`#[unsafe(no_mangle)]` is mandatory** — `cargo fix` handles it, but hand-written procedural macros may need updating.
4. **`gen` is now a keyword** — any identifier named `gen` must be renamed or escaped as `r#gen`.
