# Rust Performance

**Profile before optimizing.** Rust makes it easy to write code that looks slow and runs fast — or looks fast and runs slow. The compiler is smart enough that intuition lies.

## Profiling toolkit

| Tool | When |
|---|---|
| `criterion` | Micro-benchmarks with statistical noise handling |
| `cargo flamegraph` | CPU profiling with flame graphs (uses `perf` on Linux) |
| `samply` | Sampling profiler, upload to Firefox Profiler UI |
| `cargo-instruments` (macOS) | Instruments-backed profiling |
| `cargo bloat` | Binary size analysis — find out what's bloating the release binary |
| `cargo-show-asm` | Inspect LLVM IR and assembly for specific functions |
| `valgrind --tool=dhat` + `dhat-rs` | Heap profiling |

## Release profile

```toml
[profile.release]
opt-level = 3              # default; use 2 if compile time matters more
lto = "fat"                # link-time optimization across crates (slow compile)
codegen-units = 1          # maximize cross-function optimization (slow compile)
panic = "abort"            # smaller binary, no unwind tables, but no catch_unwind
strip = "symbols"          # smaller binary

[profile.release-with-debug]
inherits = "release"
debug = true               # symbols for profiling; use this for flame graphs
```

- `lto = "fat"` adds 30–200% to link time. Use `lto = "thin"` for a middle ground.
- `codegen-units = 1` matters for small binaries; the default `16` is fine for most.
- `panic = "abort"` saves ~5–20% binary size but you lose `catch_unwind` — important at FFI boundaries.

Don't benchmark a debug build. Ever. Debug is sometimes 100× slower than release.

## Allocation discipline

Rust doesn't hide allocations the way garbage-collected languages do, but it makes it easy to overlook them:

- `String::from(...)`, `.to_string()`, `.to_owned()`, `.clone()` on strings and vecs → allocation.
- `format!()` → allocation. Every `format!()` in a hot loop is a bug.
- `.collect::<Vec<_>>()` → allocation sized by the iterator hint.
- `Box::new(...)` → allocation.
- `vec![...]` macro → one allocation (unless empty).

Spot allocations with `cargo bloat --crates` and `#[track_caller]` profilers; on Linux, `jemalloc` with `MALLOC_CONF=prof:true` works.

**Reduce allocations:**

- `Vec::with_capacity(n)` / `String::with_capacity(n)` when you know the size.
- Reuse buffers across iterations: `buf.clear()` then `buf.extend_from_slice(...)`.
- `write!(buf, ...)` to append formatted output to an existing `String` / `Vec<u8>` without reallocating.
- `Cow<'_, str>` to return borrowed or owned as appropriate.

## Small collections

The standard `Vec`, `String`, `HashMap` all allocate on creation. For collections that are usually small:

- `smallvec::SmallVec<[T; N]>` — inline up to N elements, spill to heap beyond.
- `tinyvec::TinyVec` — all-stack variant of smallvec.
- `arrayvec::ArrayVec<T, N>` — fixed capacity, no heap.
- `ahash` / `foldhash` — faster non-DoS-resistant hashers for `HashMap`.

For very small keys: `BTreeMap` can beat `HashMap` up to ~20 entries thanks to cache locality.

## Iterators are fast (usually)

The standard-library iterator adapters compile down to the same loops a hand-written version would produce — often better because the compiler can fuse them. Don't avoid `.filter().map().sum()` on the belief it's slow.

Exceptions:

- `.collect::<Vec<_>>()` allocates; if you don't need a `Vec`, consume the iterator directly.
- `.clone()` inside `.map()` is real work.
- `.collect::<Vec<_>>().iter()` is a round-trip; remove the `.collect`.

## Common patterns that silently allocate

```rust
// BAD: allocates a new String every call
fn greet(name: &str) -> String { format!("hello {name}") }

// OK if called in a loop: take a &mut String
fn greet(name: &str, out: &mut String) { out.clear(); write!(out, "hello {name}").unwrap(); }

// BAD: collects into a Vec only to iterate
for item in items.iter().filter(|x| x.is_valid()).collect::<Vec<_>>() { ... }

// GOOD: just iterate
for item in items.iter().filter(|x| x.is_valid()) { ... }
```

## Arc / Mutex contention

`Arc<Mutex<HashMap<K, V>>>` is a frequent bottleneck. Alternatives:

- `DashMap` — sharded concurrent hashmap, lock-free reads usually.
- `ArcSwap<T>` — whole-struct atomic swap; great for read-mostly config.
- Shard by key: `Vec<Mutex<HashMap<K, V>>>` with `hash(k) % shards`.
- `evmap` — eventually-consistent multi-reader map.

`Arc::clone(&x)` is cheap but is an atomic RMW. Don't clone `Arc`s in tight loops — hoist outside.

## Dispatch: generics vs trait objects

- **Monomorphization** (`fn foo<T: Trait>`) inlines and specializes per type; zero runtime cost, but bigger binary.
- **Dynamic dispatch** (`fn foo(x: &dyn Trait)`) has one vtable indirection; small cost, no binary bloat.
- For hot paths where the trait is called in a tight loop: generics.
- For infrequent calls on heterogeneous types: `dyn Trait`.

## SIMD

For numeric hot loops:

- `std::simd` (nightly, portable) — `Simd<f32, 8>` etc.
- `wide` crate (stable, cross-platform wrapper).
- `packed_simd` (maintenance mode, superseded by `std::simd`).
- Explicit intrinsics: `std::arch::x86_64::*`, `std::arch::aarch64::*` — platform-specific, `unsafe`.

For autovectorization: pass `target-cpu=native` or a specific CPU target in `RUSTFLAGS`. Keep inner loops straight-line (no branches, no function calls). Avoid `unwrap()` on slice indexing; use `chunks_exact` / `windows`.

## Inlining

`#[inline]` is a hint, not a command. Use it:

- On very small functions called from other crates (LLVM won't otherwise see the body).
- On getter/setter-like methods.

Don't sprinkle `#[inline]` on everything — it inflates compile time and doesn't guarantee inlining.

`#[inline(always)]` forces the inline even in debug builds; use extremely sparingly, usually only for very small `unsafe` helpers.

## Binary size

If binary size matters:

- `panic = "abort"` saves unwind tables.
- `strip = "symbols"` in release profile.
- `opt-level = "z"` trades speed for size (rarely worth it for normal apps).
- `#[inline]` aggressively on trait methods that get monomorphized everywhere can *grow* the binary. Check with `cargo bloat`.
- Replace big deps: `serde_json` is ~800KB; `simd-json` ~2MB; for a small tool, `tinyjson` might be enough.

## Benchmarks that don't lie

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn bench_parse(c: &mut Criterion) {
    let input = include_str!("sample.txt");
    c.bench_function("parse", |b| {
        b.iter(|| parse(black_box(input)))
    });
}

criterion_group!(benches, bench_parse);
criterion_main!(benches);
```

- `black_box(x)` prevents the compiler from constant-folding away the input.
- `b.iter(|| { ... })` timing-aware loop.
- Criterion reports mean + variance + outliers. Variance > 5% is suspicious — CPU frequency scaling, noisy neighbors, thermal throttling.

Run benches on a quiet machine (no browsers, no indexers), with CPU governor set to `performance`:

```
sudo cpupower frequency-set -g performance
```

## Cache locality

- Struct-of-Arrays (SoA) beats Array-of-Structs (AoS) when you iterate one field at a time.
- `#[repr(C)]` controls field order; default Rust layout may reorder for padding efficiency but is unpredictable.
- Hot fields first, cold fields last — helps the first cache line load cover more accesses.
- For linked structures: reconsider. `Vec<T>` is almost always faster than `LinkedList<T>`.

## Async-specific perf

- Don't `spawn` per request at very high QPS; consider a task pool.
- `block_on` inside async code is a deadlock risk *and* a perf smell.
- Blocking I/O on the runtime thread stalls all concurrent work → use `spawn_blocking`.
- Profile async code with `tokio-console` to see task state and scheduling.

## Quick triage ladder

When something is slow:

1. Is this a debug or release build? (Release only.)
2. Is the perf issue reproducible and measurable? (Benchmark, don't guess.)
3. Where is the time going? (Flame graph.)
4. Is the hot function allocating? (Heap profile.)
5. Is there lock contention? (`perf lock`, `tokio-console`.)
6. Is the code vectorized? (`cargo asm` or Godbolt with matching compiler flags.)
7. Can the algorithm change? (O(n²) → O(n log n) always beats micro-optimization.)

Start at the top. 80% of the time the fix is higher in the ladder than you'd guess.
