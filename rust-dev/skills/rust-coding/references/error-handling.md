# Error Handling

The Rust principle: **errors are values, not control flow**. If a function can fail, it returns `Result<T, E>`. `panic!` is for bugs, not for failure modes the caller should handle.

## The split rule

| Crate type | Error strategy |
|---|---|
| Library (published on crates.io or consumed by other crates) | `thiserror` — typed enum per module |
| Binary / application top level | `anyhow` — opaque `anyhow::Error` with `.context()` chains |
| FFI boundary | Opaque `enum ErrorCode { Ok, Invalid, OutOfMemory, ... } `, last-error in `thread_local!` |

**Never mix them in the same crate.** `anyhow::Error` in a library's public API forces every downstream consumer to take `anyhow` as a dep; `thiserror` in a top-level binary is busywork.

## `thiserror` in libraries

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("config file not found at {path}")]
    NotFound { path: PathBuf },

    #[error("failed to parse {path}: {source}")]
    Parse { path: PathBuf, #[source] source: toml::de::Error },

    #[error("missing required field `{field}`")]
    MissingField { field: &'static str },
}
```

Rules:

- **Variants carry structured data**, not formatted strings. `Parse { path, source }`, not `Parse(String)`.
- Use `#[source]` to chain — downstream `anyhow::Error` will print the full cause chain.
- **No `Box<dyn Error>`** in variants; convert at the boundary.
- Avoid over-merging — if `FooError::Io` and `FooError::Network` come from the same `io::Error`, split them when the caller would handle them differently.

## `anyhow` in applications

```rust
use anyhow::{Context, Result};

fn run() -> Result<()> {
    let cfg = load_config()
        .context("loading config")?;
    let conn = connect(&cfg.url)
        .with_context(|| format!("connecting to {}", cfg.url))?;
    Ok(())
}
```

Rules:

- `.context("doing X")` at every `?` — the error message reads as a story: "connecting to db: TCP refused: connection reset by peer".
- `.with_context(|| ...)` (closure form) when the context contains a formatted string — lazy eval, avoids allocating on the happy path.
- `anyhow::bail!("message")` for ad-hoc errors.
- `anyhow::ensure!(cond, "message")` for guards.

## The `?` operator

- `?` works on any `Result<T, E>` where `E: Into<OuterError>` (there's an `impl From<E> for OuterError`).
- Chain `From` impls via `#[from]` in `thiserror`:
  ```rust
  #[derive(Error, Debug)]
  pub enum MyError {
      #[error("io: {0}")] Io(#[from] io::Error),
  }
  ```
  Now `io::Result<T>?` promotes automatically.
- `?` on `Option<T>` converts `None` to the function's error (must impl `From<NoneError>`, which in stable means explicit `.ok_or(err)?`).

## No `.unwrap()` / `.expect()` in production paths

Acceptable call sites:

- `main()` (or anywhere returning `Result` where the message will be printed and the process will exit).
- Tests and benches.
- `OnceCell::get().unwrap()` — after proving initialization.
- Where the panic is the documented contract: `Mutex::lock().unwrap()` when the lock is never poisoned, or `expect("invariant: queue non-empty; we just pushed")`.

Every `.expect()` gets a message explaining the invariant in natural language. "should never fail" is not acceptable.

## Panic vs Result — where's the line?

- **Panic:** programmer bugs, invariant violations, impossible-in-principle states. `.unwrap()` on a `Some` you just inserted. Index-out-of-bounds.
- **Result:** anything the environment can cause — file missing, network timeout, malformed input, permission denied, resource exhaustion.

User input failing validation is a `Result`, not a panic.

## `From` implementations

Prefer `#[from]` (thiserror) or manual `impl From` over `.map_err(...)` chains:

```rust
// busywork
let s: String = something().map_err(|e| MyError::Foo(e.to_string()))?;

// idiomatic
let s: String = something()?;  // via #[from] on MyError::Foo
```

Exceptions: when you need to *add information* at the boundary, explicit `.map_err(|e| MyError::FooContext { input, source: e })?` is clearer than a `From` impl.

## Panic safety (library authors)

If your library holds an invariant across an `unsafe` block or a state machine, consider panic safety:

- **Unwind-safe:** data structures remain valid after an unwinding panic.
- **Abort-safe:** data structures remain valid even if the process aborts (e.g., for `catch_unwind` across FFI).
- Mark types `UnwindSafe` / `RefUnwindSafe` only with intention.
- In `no_std` or embedded: `panic = "abort"` avoids unwinding entirely, simplifying the story.

## Propagation layer cake

A typical service:

```
pub fn handle_request(req: Request) -> Result<Response, anyhow::Error> {
    let parsed: ParsedReq = parse(&req).context("parse request")?;
    let data = db::load(parsed.id).context("load from db")?;     // db::Error -> anyhow via From
    let transformed = transform(data).context("transform")?;      // my own error via ?
    Ok(Response::ok(transformed))
}
```

- Domain errors (`db::Error`, `transform::Error`) are `thiserror` enums.
- The handler wraps with `anyhow::Context`.
- Logs emit `{:#}` (alternate Display) to get the full chain.

## Common mistakes

1. **Stringly-typed errors** — `MyError(String)` loses all structure. Never do this.
2. **Catch-all `Unknown` variant** — invites noise and hides real categories.
3. **`Result<T, ()>`** — use `Option<T>` instead; `()` as an error type carries no information.
4. **Logging AND returning the error** — log at one level, usually the top of the stack. Double-logging spam is real.
5. **`.ok()` to swallow errors silently** — at least log the error before dropping it. Better: propagate.
6. **`Result<Result<T, E1>, E2>`** — flatten; usually one of the errors can be merged into the other.
