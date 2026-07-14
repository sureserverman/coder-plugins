# Async Rust

Safe Rust prevents data races at compile time. It does **not** prevent deadlocks, starvation, livelocks, or resource exhaustion. Async Rust inherits all of these — and adds a few specific footguns.

## Runtime choice

- **`tokio`** — dominant; multi-thread scheduler, full ecosystem (hyper, reqwest, tonic, sqlx, axum). Default choice.
- **`smol` / `async-std`** — smaller; use when minimal dependency surface is a hard requirement.
- **`embassy`** — embedded / no_std.
- **`monoio`** — io_uring-only, linux-only, thread-per-core.

**Never mix runtimes in one binary.** A `tokio::spawn` from inside a `smol` task won't work; futures that block on a runtime that isn't running deadlock.

Libraries should be runtime-agnostic where possible (`async-std`'s `async-io` + `futures-util`, or generic over an executor). When you must pick one, document it: "Requires a tokio runtime."

## The top four footguns

### 1. Holding a lock across `.await`

```rust
// BAD
let guard = shared.lock().await;
let result = fetch_remote(&guard.url).await;  // lock held for network RTT
*guard = result;
```

Any other task that wants the lock blocks for as long as the network call takes. Under load this serializes the whole service.

**Fixes:**
- Clone what you need and drop the guard:
  ```rust
  let url = shared.lock().await.url.clone();
  let result = fetch_remote(&url).await;
  *shared.lock().await = result;
  ```
- Use a lock-free design (channels, `Arc<AtomicX>`, `ArcSwap`).
- If you really must hold across await, document why, use `tokio::sync::Mutex` (not `std::sync::Mutex` — it's not designed for it), and measure.

### 2. Unbounded channels with attacker-controlled fanout

```rust
// BAD
let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
for req in incoming_requests {
    tx.send(req)?;  // attacker floods, memory unbounded
}
```

**Fixes:**
- `tokio::sync::mpsc::channel(capacity)` — back-pressure via `send().await` blocking when full.
- `.try_send()` to fail fast when full instead of blocking.
- Drop oldest / drop newest semantics via `tokio::sync::mpsc` + a dedicated dropper task.
- `flume` or `async-channel` for MPMC with bounded semantics.

### 3. Cancellation safety

A future can be dropped mid-`.await` — at any `.await` point, the runtime may cancel it. Your future must be safe to drop at every such point.

Unsafe pattern:
```rust
// BAD: if this future is cancelled between read and write, the buffer is dropped mid-way
async fn copy(reader: &mut R, writer: &mut W) -> io::Result<()> {
    let mut buf = vec![0u8; 4096];
    let n = reader.read(&mut buf).await?;
    writer.write_all(&buf[..n]).await?;  // if cancelled here, bytes are lost
    Ok(())
}
```

Use `tokio::select!` with care: only cancellation-safe futures should be branches:

```rust
tokio::select! {
    result = fetch() => { ... }
    _ = tokio::time::sleep(timeout) => { /* timeout */ }
}
```

`fetch()` must be cancellation-safe — re-runnable without side effects if it's dropped. Most `io::Read` / `io::Write` are *not* cancellation-safe (partial reads/writes). See `tokio::io::AsyncReadExt` docs for per-method notes.

### 4. Send bounds on futures

A `tokio` multi-thread future must be `Send`. Holding a non-`Send` value (`Rc`, `RefCell`, raw pointers, `MutexGuard` from `std::sync::Mutex` on some platforms) across an `.await` makes the future non-`Send` and often triggers confusing error messages:

```
error: future cannot be sent between threads safely
  --> src/lib.rs:42:5
   |
42 |     tokio::spawn(async move {
   |     ^^^^^^^^^^^^ future created by async block is not `Send`
```

Scope the non-`Send` value to a non-await region:
```rust
let val = {
    let guard = local_cell.borrow();
    compute_without_await(&*guard)
};
fetch_remote(val).await
```

## `select!` pitfalls

- `tokio::select!` polls branches in the *order they appear* (biased variant); default is pseudo-random to avoid starvation. Don't rely on either unless you use `biased;`.
- Every branch future is either completed, dropped, or continues on the *next* iteration. Dropped futures must be cancellation-safe.
- **Never call a non-cancellation-safe function directly in a `select!` branch.** Wrap in `tokio::pin!` + `poll` or hoist to a clearly-owned `tokio::task::JoinHandle`.

## Spawning tasks

- `tokio::spawn(future)` detaches the task — the returned `JoinHandle` can be dropped, and the task still runs. If you drop the handle and the task panics, you lose the panic.
- `tokio::task::JoinSet` lets you spawn many and collect results / panics.
- **Always `.await` a `JoinHandle` you care about** — otherwise panics are silent.
- `tokio::task::spawn_blocking` for CPU-bound or blocking-syscall work — never do heavy compute on the async executor threads.
- `tokio::task::yield_now()` in a long-running CPU loop to let other tasks run.

## Streams

- `futures::Stream` is the async iterator. `tokio_stream` has utilities (`StreamExt::throttle`, `chunks_timeout`, etc.).
- `ReceiverStream::new(rx)` adapts an `mpsc::Receiver` to a `Stream`.
- Prefer streams over "pull next" loops for cancellation and back-pressure semantics.

## Shared state patterns

| Pattern | When |
|---|---|
| `Arc<tokio::sync::Mutex<T>>` | Mutable shared state, low contention, possibly held across `.await` |
| `Arc<parking_lot::Mutex<T>>` | Mutable shared state, *never held across `.await`*, lower overhead than `std::sync::Mutex` |
| `Arc<RwLock<T>>` | Many readers, rare writers |
| `Arc<AtomicU64>` / `AtomicBool` | Single scalar, lock-free |
| `ArcSwap<T>` | Whole-struct swaps, read-mostly config |
| `tokio::sync::watch` | Single-producer-broadcast of the latest value |
| `tokio::sync::broadcast` | Multi-producer-fanout, bounded |
| `dashmap::DashMap` | Sharded concurrent hashmap, sync API but safe across `.await` because no guard |

## Testing async code

- `#[tokio::test]` (or `#[tokio::test(flavor = "multi_thread")]`) for per-test runtimes.
- `tokio::time::pause()` + `advance()` for virtual time — reliable and fast.
- `tokio::test::io::Builder` for scripted I/O.
- `loom` for model-checking concurrency bugs in your algorithms (`[dev-dependencies] loom = "0.7"`).

## Error propagation in async

`?` works the same way. Be careful with `JoinHandle`:

```rust
// JoinHandle<T> where T is Result<...>
let handle = tokio::spawn(async move { do_it().await });
let inner: Result<...> = handle.await?;  // outer Result is JoinError (panic or cancellation)
let value = inner?;                       // inner Result is your business error
```

Flatten with `?` twice or use `handle.await??` when both are convertible into your error type.

## Logging in async

- `tracing` over `log` — span context survives across `.await` boundaries.
- Attach spans to spawned tasks: `tokio::spawn(do_work().instrument(span))`.
- Don't `println!` in a hot async loop — stdout lock contention is real.

## Graceful shutdown

- `tokio::signal::ctrl_c()` for SIGINT.
- `CancellationToken` from `tokio-util` for cooperative shutdown:
  ```rust
  let token = CancellationToken::new();
  let cloned = token.clone();
  tokio::spawn(async move {
      tokio::select! {
          _ = do_work() => {}
          _ = cloned.cancelled() => {}
      }
  });
  token.cancel();
  ```
- Drain channels before exit to avoid losing buffered work.

## Quick checklist before merging async code

- [ ] No `std::sync::Mutex` guard held across `.await`
- [ ] Every spawned task's `JoinHandle` is awaited or explicitly detached-with-comment
- [ ] Every `mpsc` channel is bounded unless capacity is a compile-time constant
- [ ] `select!` branches are cancellation-safe
- [ ] `spawn_blocking` wraps any `std::fs::*`, `std::io` blocking, or CPU loop > ~1ms
- [ ] Graceful shutdown path exists for long-running tasks
- [ ] No `block_on` inside an async context
