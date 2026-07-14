# Unsafe Rust

`unsafe` is a contract you sign with the compiler: "I've verified that this code upholds Rust's safety invariants, which the compiler can't check here."

## The Microsoft Pragmatic Rust rules

From the Microsoft Pragmatic Rust Guidelines (microsoft.github.io/rust-guidelines):

- **M-UNSAFE: Unsafe needs a reason.** Only three valid reasons to reach for `unsafe`:
  1. **Novel abstractions** — new smart pointers, lock-free collections, arena allocators. Something where safe Rust genuinely cannot express the API.
  2. **Performance** — bypassing bounds checks in a proven-hot loop with evidence from a benchmark.
  3. **FFI / platform calls** — talking to C, syscalls, platform intrinsics.

  Never reach for `unsafe` to simplify safe code, bypass trait bounds, or dodge the borrow checker. That's not "using the tool wrong" — that's bug-farming.

- **M-UNSOUND: Unsound code is never acceptable.** A function is *unsound* if safe code calling it can produce undefined behavior. No exceptions. If you can't safely encapsulate the operation, expose an `unsafe fn` with a `# Safety` contract instead.

- **M-UNSAFE-IMPLIES-UB: `unsafe` marks UB risk, not danger in general.** A function that deletes files is dangerous but not `unsafe` — `unsafe` is reserved for operations where misuse produces undefined behavior.

## The `// SAFETY:` rule

**Every `unsafe` block carries a `// SAFETY:` comment** stating the invariants that make the block sound:

```rust
// SAFETY: `ptr` is non-null (checked above), points to an initialized `T`
// (we allocated it with `Box::into_raw` and have not freed it), and is
// uniquely owned by this function (the `Box` was consumed on line 42).
let value: T = unsafe { *Box::from_raw(ptr) };
```

Rules for the comment:

- State **what is true** and **why** — not "trust me".
- Reference the code that establishes each invariant (a line, a function, a type).
- Rewrite the comment when the surrounding code changes. Stale SAFETY comments are worse than none.
- If you can't write the comment clearly, the code probably isn't sound.

`unsafe fn` declarations get a `/// # Safety` docstring with the same structure — it lists the preconditions callers must uphold.

## Minimize the block

```rust
// bad: wide unsafe, hard to audit
unsafe {
    let p = raw_ptr;
    let v = *p;
    let result = process(v);      // this doesn't need unsafe
    write_back(p, result);         // this does
}

// good: each unsafe block is exactly what needs to be
let v = unsafe { *raw_ptr };       // SAFETY: ...
let result = process(v);
unsafe { write_back(raw_ptr, result) };  // SAFETY: ...
```

Smaller `unsafe` blocks = smaller blast radius.

## Soundness boundaries

**Module boundaries are soundness boundaries.** Safe functions inside a module may rely on invariants established elsewhere in the *same* module (e.g., a field never being zero because a private constructor rejects zero). Once you `pub` something across the module boundary, safe callers must be unable to break the invariant.

This is why encapsulation matters for soundness: private fields + constructors are the enforcement mechanism for invariants that `unsafe` blocks downstream rely on.

## Tools

### Miri

Miri is an interpreter for Rust's mid-level IR that catches undefined behavior — alignment violations, use-after-free, invalid pointer arithmetic, Stacked/Tree Borrows aliasing violations.

```
rustup +nightly component add miri
cargo +nightly miri test
```

Run Miri in CI on any test that exercises `unsafe` code. Miri is slow (10-100× slower than native) but catches bugs that `cargo test` silently misses.

### `cargo-geiger`

Maps `unsafe` usage across your full dependency graph:

```
cargo install cargo-geiger
cargo geiger
```

A dep with lots of `unsafe` isn't inherently bad — `tokio`, `rayon`, `std` all use plenty — but a *random small crate* with lots of `unsafe` is a review target.

### `cargo-careful`

Builds `std` with extra runtime checks (debug assertions, overflow checks, uninit memory detection):

```
cargo install cargo-careful
cargo +nightly careful test
```

Catches UB that Miri might miss because it reached a "this is fast code" shortcut.

### Sanitizers

ASan (AddressSanitizer), TSan (ThreadSanitizer), LSan (LeakSanitizer), UBSan (UndefinedBehaviorSanitizer):

```
RUSTFLAGS="-Zsanitizer=address" cargo +nightly test
```

Nightly-only. Especially useful at FFI boundaries where Miri doesn't reach.

## Common unsafe tasks

### Raw pointer deref

```rust
// SAFETY: ptr is from Box::into_raw in this module; guaranteed non-null,
// initialized, and unaliased for the lifetime of `guard`.
let value = unsafe { &*ptr };
```

### Uninitialized memory

```rust
let mut buf: [MaybeUninit<u8>; 1024] = unsafe { MaybeUninit::uninit().assume_init() };
let len = read(&mut buf)?;
// SAFETY: `read` returned `len`, so the first `len` bytes are initialized.
let init: &[u8] = unsafe {
    std::slice::from_raw_parts(buf.as_ptr() as *const u8, len)
};
```

Never construct `MaybeUninit<T>` arrays of non-`MaybeUninit` types via `assume_init` — that's UB.

### Transmutes

Prefer `.cast()` or `bytemuck` over `std::mem::transmute`. `transmute` is the sharpest tool in the shed. If you must:

```rust
// SAFETY: both types are #[repr(C)] with identical field layout
let as_other: OtherType = unsafe { std::mem::transmute(input) };
```

The `bytemuck` crate offers `Pod` / `Zeroable` traits for zero-unsafe transmutes of "plain-old-data" types.

### `Send` / `Sync` manual impls

```rust
// SAFETY: the inner `Cell<T>` is only accessed behind a Mutex, which
// establishes the happens-before relationship needed for Send.
unsafe impl<T: Send> Send for MyType<T> {}
```

Document the invariant; don't just `impl`.

## Concurrency-related UB

- **Data races** — `unsafe` + `*mut T` + threads without synchronization = data race = UB. Use atomics or locks.
- **Aliasing rules** — you may not have `&mut T` and `&T` (or another `&mut T`) to the same memory at the same time, even if you're not actually using one. `UnsafeCell` is the only legal way to have interior mutability.
- **Pointer provenance** — a pointer derived from A cannot legally access memory belonging to B. `as` casts lose provenance in some cases; use `.wrapping_add` and similar with care.

## Unsafe in async

Holding raw pointers across `.await` points is usually UB — the future may be moved (Pinned or not), and the raw pointer still pointing at the old location is dangling.

`Pin<Self>` projects fields; don't `&mut` a field of a pinned struct without a SAFETY justification (use `pin-project-lite` or `pin-project` to do it correctly).

## What to tell yourself before every `unsafe` block

1. Is there a safe alternative? (`bytemuck`, `ouroboros`, `owned-refs`, `std::pin`.)
2. If I'm the last person to touch this code in 18 months, will the SAFETY comment still be accurate?
3. Does Miri pass?
4. Is there a test that would fail if the invariant breaks?

If the answer to any of these is "not sure," stop and find out.
