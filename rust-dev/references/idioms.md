# Idiomatic Rust

What "idiomatic" means here: the borrow checker agrees, clippy is silent on pedantic, and a reader two years from now can follow the code without reading the compiler manual.

## Ownership and borrowing

- **Default to taking `&T` or `&mut T`.** Take owned `T` only when you must move it into a structure or a thread.
- **Return owned `T`** when the caller needs to mutate or keep the value past the call. Return `&T` only when the lifetime is obviously tied to an input.
- **Clone is a code smell, not a crime.** One `.clone()` on a small value is fine; a loop of `.clone()` in a hot path is a red flag. Profile before removing; don't contort the code for premature optimization.
- **Reach for `Cow<'_, str>` / `Cow<'_, [T]>`** when the function may or may not allocate based on input — e.g., unescaping a string that's already clean.

## Iterators

Prefer iterator chains over manual index loops. LLVM optimizes iterators at least as well, they compose, and they don't index-out-of-bounds.

```rust
// not idiomatic
let mut out = Vec::new();
for i in 0..items.len() {
    if items[i].is_valid() {
        out.push(items[i].transform());
    }
}

// idiomatic
let out: Vec<_> = items.iter()
    .filter(|x| x.is_valid())
    .map(|x| x.transform())
    .collect();
```

- `.filter_map()` combines filter + map when the map is fallible.
- `.try_fold()` / `.try_for_each()` short-circuit on the first `Err`.
- `.collect::<Result<Vec<_>, _>>()` turns an iterator of `Result` into a `Result<Vec, _>`.
- Use `Iterator::peekable` instead of index bookkeeping.
- `Vec::retain()` for in-place filter; avoid rebuild-then-assign.

## Newtypes and type-state

A **newtype** is a zero-cost wrapper that pushes invariants into the type system:

```rust
#[repr(transparent)]
pub struct UserId(u64);

impl UserId {
    pub fn new(id: u64) -> Option<Self> {
        (id != 0).then_some(Self(id))
    }
}
```

This prevents accidentally passing a `RoomId` where a `UserId` was expected — the compiler catches it. `#[repr(transparent)]` guarantees no ABI overhead.

**Type-state** encodes a state machine in the type parameter:

```rust
pub struct Builder<S> { /* fields */ _state: PhantomData<S> }
pub struct Empty;
pub struct HasHost;
pub struct Ready;

impl Builder<Empty> { pub fn host(self, h: &str) -> Builder<HasHost> { /* ... */ } }
impl Builder<HasHost> { pub fn port(self, p: u16) -> Builder<Ready> { /* ... */ } }
impl Builder<Ready> { pub fn build(self) -> Client { /* ... */ } }
```

Calling `.build()` before `.host(...).port(...)` is a compile error, not a runtime `.expect()`.

## Pattern matching

- `match` is exhaustive — use it whenever a value has more than two shapes. Add `#[non_exhaustive]` on enums you expose publicly if you plan to extend them without breaking downstream.
- `if let` / `let else` for single-branch destructure:
  ```rust
  let Some(config) = load_config() else {
      return Err(Error::MissingConfig);
  };
  ```
- `matches!(x, Pat)` returns `bool` — cleaner than `if let ... else false`.
- Guards in match arms: `Some(n) if n > 0 => ...`. Edition 2024 stabilizes `if let` guards.

## Error-handling micro-idioms

- `?` at every fallible call. Never wrap a `Result` in a `match` just to return it.
- `.ok_or(err)` / `.ok_or_else(|| err)` to turn `Option` into `Result`.
- `.context("what I was doing")` (from `anyhow` or `eyre`) at every `?` boundary in binaries.

## Visibility and module layout

- `pub(crate)` is the default for anything used across modules inside the crate.
- `pub` is a public commitment — semver applies.
- Private-by-default: if you're not sure, keep it private.
- Re-export with `pub use` to curate the public surface:
  ```rust
  // lib.rs
  mod internal_graph;
  pub use internal_graph::Node;  // Node is public; internal_graph isn't
  ```

## Small-but-sharp habits

- `#[must_use]` on types whose results are easy to drop on the floor (`Result`, `Future`, builders, `MutexGuard`, iterator adapters).
- `#[inline]` sparingly — only across crate boundaries for small hot functions. The compiler inlines within a crate aggressively without hints.
- `Default::default()` is ugly — prefer `T::default()` or a named constructor.
- `Into` for ergonomics, `From` for the actual conversion. Write `impl From<A> for B`, and `Into` comes free.
- `Deref`/`DerefMut` only for smart-pointer-like types (`Arc`, `MutexGuard`). Using `Deref` for inheritance is an anti-pattern.

## Closures

- `Fn` for immutable capture, `FnMut` for `&mut` capture, `FnOnce` for move-consume.
- Prefer `impl Fn(...) -> T` in parameters; box as `Box<dyn Fn>` only for heterogeneous storage.
- Edition 2021+ has disjoint closure captures — closures capture only the fields they use, not the whole struct.

## What NOT to do

- **No `.unwrap()`** outside `main`, tests, `OnceCell::get`, or where the panic is the documented contract. Use `?` or `.expect("invariant: X cannot be empty here because Y")`.
- **No `Box<dyn Error>` in public APIs.** Define a concrete error enum.
- **No `String` where `&str` works.** No `Vec<T>` where `&[T]` works.
- **No `.collect::<Vec<_>>().iter()`** — the `.collect` is wasted allocation. Keep the iterator going.
- **No `.clone()` on `Arc` in a hot loop** — `Arc::clone(&x)` is cheap but an atomic RMW; hoist it outside.
