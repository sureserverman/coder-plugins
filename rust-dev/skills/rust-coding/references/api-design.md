# Rust API Design

The Rust API Guidelines (rust-lang.github.io/api-guidelines) are the baseline. This file extracts the rules that matter most and adds project-specific opinions.

## Argument types

| You need | Take |
|---|---|
| Read-only string | `&str` |
| Owned string you'll keep | `String` — but prefer `impl Into<String>` |
| Either-or string | `impl AsRef<str>` |
| Read-only slice | `&[T]` |
| Iterator of items | `impl IntoIterator<Item = T>` |
| File path | `impl AsRef<Path>` |
| Any function | `impl Fn(...)` / `impl FnMut(...)` / `impl FnOnce(...)` |

**Never demand `String` / `Vec<T>` the caller has to construct** unless you're moving it into a struct or across a thread.

## Return types

- Owned `T` when the caller needs flexibility.
- `Cow<'_, T>` when the function may or may not allocate based on input.
- `impl Trait` when you want to hide the concrete type and there's only one return shape:
  ```rust
  pub fn lines(&self) -> impl Iterator<Item = &str> + '_ { ... }
  ```
- `Box<dyn Trait>` when the caller needs a heterogeneous storage (e.g., `Vec<Box<dyn Plugin>>`).

Edition 2024 changed the hidden-lifetime capture rules for `impl Trait` in return position — assume the return captures every generic lifetime in scope unless you opt out with `use<>`.

## Generics vs trait objects

- **Generic `<T: Trait>`** — monomorphized, zero-cost, but inflates binary size. Use for small inline functions and hot paths.
- **`&dyn Trait` / `Box<dyn Trait>`** — one vtable indirection, no monomorphization blowup. Use when values are heterogeneous or the API is already allocation-heavy.

## Trait design

- **Sealed traits** prevent downstream impls on your public trait:
  ```rust
  mod private { pub trait Sealed {} }
  pub trait Foo: private::Sealed { ... }
  impl private::Sealed for Bar {}
  impl Foo for Bar { ... }
  ```
  Anyone outside the crate cannot add `impl Foo for Whatever` — you retain freedom to extend.
- **Object-safe traits** (no `Self` in return position, no generic methods) can be used as `dyn Trait`. Sometimes you want to split: `trait Foo: FooObj` where `FooObj` is the object-safe subset.
- **Marker traits** (`Send`, `Sync`, `Copy`) have semantics the compiler relies on — implement them manually only with `unsafe` and a `// SAFETY:` comment.

## Newtype pattern for invariants

See `idioms.md`. Use newtypes whenever a primitive (`u64`, `String`, `Vec<u8>`) has domain semantics: `UserId`, `SessionToken`, `PoolAddr`. `#[repr(transparent)]` gives zero ABI cost.

## `#[non_exhaustive]`

Mark public structs and enums you want to evolve:

```rust
#[non_exhaustive]
pub enum Event { Connected, Disconnected, Error(ErrorKind) }
```

Downstream `match` statements must include a `_ => ...` arm, so adding a variant is non-breaking.

## Constructors

- `new` — canonical constructor. Takes the minimal valid args.
- `with_foo` — constructor taking an optional parameter explicitly (`Vec::with_capacity`).
- `try_new` — fallible constructor returning `Result<Self, E>`.
- `from` — takes exactly one argument of a related type (`Path::from`).
- Builders for ≥ 4 optional parameters. Use typestate (see `idioms.md`) if the build must be in a specific order.

## Error type placement

- One error enum per module boundary, not per function.
- Variants carry structured fields, not formatted strings:
  ```rust
  // bad
  MyError::Parse(String)
  // good
  MyError::Parse { input: String, position: usize, reason: ParseReason }
  ```
- Re-export the top-level error at the crate root: `pub use error::Error;`.

## Semver discipline

Breaking changes (require a major version bump):

- Removing or renaming a public item.
- Changing a public function signature.
- Adding a required method to a trait (add a *default* method instead, or use a new trait).
- Adding a variant to a public enum **without** `#[non_exhaustive]`.
- Tightening a trait bound (`T: Clone` → `T: Clone + Send`).
- Making a previously `Send`/`Sync` type not-`Send`/`Sync`.

Non-breaking:

- Adding a new public item.
- Adding a variant to a `#[non_exhaustive]` enum.
- Relaxing a trait bound.
- Adding a trait impl, unless it triggers coherence conflicts downstream.

## MSRV (Minimum Supported Rust Version)

- Commit to an MSRV in the README and `Cargo.toml` (`rust-version = "1.85"`).
- Run CI against the MSRV, not just stable.
- Bumping the MSRV is a breaking change for some orgs; for pre-1.0 crates, bumping with a minor version is acceptable if documented.

## Doc conventions

- Every public item has a `///` doc comment.
- Include a `# Examples` section; `cargo test --doc` runs them.
- Document panics (`# Panics`), errors (`# Errors`), and unsafe preconditions (`# Safety`).
- Crate-level doc goes at the top of `lib.rs` with `//!`.

## Send / Sync

- Make types `Send + Sync` when safe — it's the default expectation for library types.
- Document non-`Send` or non-`Sync` types prominently: "This type is `!Send` because it owns a `Rc<...>`."
- `PhantomData<*const ()>` to opt out of `Send`/`Sync` intentionally.
