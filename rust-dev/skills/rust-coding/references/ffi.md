# FFI in Rust

FFI is where Rust's safety guarantees end and the other language's begin. Every FFI boundary is an `unsafe` contract that the human must verify — the compiler can only check the Rust side.

## Tool choice

| Target | Tool |
|---|---|
| Consume C / C++ headers | `bindgen` (generates Rust bindings from headers) |
| Expose Rust to C | `cbindgen` (generates C headers from Rust) |
| Rust ↔ C++ bidirectional, safe idioms | `cxx` |
| Rust ↔ Python | `PyO3` |
| Rust ↔ Node.js | `napi-rs` |
| Rust ↔ JVM (JNI) | `jni` crate |
| Rust ↔ Swift / Obj-C | `swift-bridge` or manual `extern "C"` |

Prefer `cxx` when both sides are Rust+C++ — it encodes the ownership contract in types so many classes of UB are impossible. `cxx` won't compile mismatched lifetimes.

## The rules

### 1. `#[repr(C)]` on everything crossing the boundary

Default Rust layout is unspecified — the compiler can reorder fields, change padding, and pick any discriminant size for enums. FFI requires `#[repr(C)]`:

```rust
#[repr(C)]
pub struct Point { pub x: f64, pub y: f64 }

#[repr(C)]
pub enum Status {
    Ok = 0,
    Invalid = 1,
    OutOfMemory = 2,
}
```

For enums with data: `#[repr(C)]` or `#[repr(i32)]` / specific integer type. For tagged unions, `#[repr(C)]` gives the C layout of "tag followed by union".

### 2. `extern "C"` on every exported function

```rust
#[unsafe(no_mangle)]  // edition 2024 syntax
pub unsafe extern "C" fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

- `#[unsafe(no_mangle)]` (was `#[no_mangle]` pre-2024) — prevents Rust's name mangling.
- `#[unsafe(export_name = "custom_name")]` — explicit symbol name.
- `extern "C"` — use the C calling convention.

### 3. Never panic across an FFI boundary

Unwinding into a C caller is undefined behavior (historically; the `C-unwind` ABI stabilizes some cases but don't rely on it). Catch panics at the boundary:

```rust
pub unsafe extern "C" fn foo(ptr: *const u8, len: usize) -> i32 {
    let result = std::panic::catch_unwind(|| {
        // SAFETY: caller promises ptr..ptr+len is valid for reads
        let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
        process(slice)
    });
    match result {
        Ok(Ok(_)) => 0,
        Ok(Err(_)) => -1,    // application error
        Err(_) => -2,         // panic
    }
}
```

Or set `panic = "abort"` in `Cargo.toml`:

```toml
[profile.release]
panic = "abort"
```

This avoids unwinding entirely, simplifying the story at the cost of losing destructor runs.

### 4. Ownership conventions

Document in a header comment **who owns what and who frees it**:

```rust
/// Returns a newly-allocated string. Caller must call `free_str` on the
/// returned pointer. Returns NULL on allocation failure.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn make_greeting(name: *const c_char) -> *mut c_char {
    // SAFETY: caller promises name is a valid null-terminated C string.
    let name_str = unsafe { CStr::from_ptr(name) }.to_string_lossy();
    CString::new(format!("hello {name_str}"))
        .map(|s| s.into_raw())  // transfers ownership to caller
        .unwrap_or(std::ptr::null_mut())
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn free_str(p: *mut c_char) {
    if !p.is_null() {
        // SAFETY: p came from make_greeting's CString::into_raw.
        unsafe { drop(CString::from_raw(p)) };
    }
}
```

**Common ownership mistakes:**

- Returning a pointer into a Rust-owned `String`'s buffer — the `String` drops at function return, pointer dangles.
- Accepting a pointer and freeing with Rust's allocator when it came from C's `malloc` — mismatched allocators = UB.
- Forgetting that `CString::into_raw` → `CString::from_raw` is the only correct round-trip. Don't free the pointer with `libc::free`.

### 5. Null and validity checks

C pointers can be null, misaligned, dangling, or point to the wrong type. Check before deref:

```rust
if ptr.is_null() { return ErrorCode::InvalidArgument as i32; }
// SAFETY: non-null checked above. Caller documented that ptr is a valid `Foo`.
let foo: &Foo = unsafe { &*ptr };
```

Alignment: `ptr.is_aligned()` (stable since 1.79). Misaligned reads are UB even if the hardware tolerates them.

### 6. Error reporting

Return an error code + out-parameter, or a last-error `thread_local!`:

```rust
thread_local! {
    static LAST_ERROR: RefCell<Option<CString>> = RefCell::new(None);
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn last_error_message() -> *const c_char {
    LAST_ERROR.with(|e| e.borrow().as_ref().map(|s| s.as_ptr()).unwrap_or(std::ptr::null()))
}
```

Never pass Rust error types (including `Box<dyn Error>`) across FFI. They're not `#[repr(C)]` and their layout is unstable.

## C string conventions

- `CStr` — borrowed, null-terminated, immutable. Built from a raw pointer via `CStr::from_ptr` (unsafe).
- `CString` — owned, null-terminated. Built from a `&str` via `CString::new` (returns `Err` if interior nulls present).
- Never pass `String` or `&str` across the FFI boundary — they're not null-terminated.

## `cxx` crate (Rust ↔ C++)

```rust
#[cxx::bridge]
mod ffi {
    extern "Rust" {
        type MyRustType;
        fn do_something(self: &MyRustType, input: &str) -> String;
    }
    unsafe extern "C++" {
        include!("my_header.h");
        type MyCppType;
        fn cpp_method(self: Pin<&mut MyCppType>, arg: i32) -> i32;
    }
}
```

`cxx` encodes ownership and lifetimes in the bridge macro. Mismatches produce compile errors, not runtime UB. Prefer `cxx` whenever both sides are under your control.

## Validation tools

- **`cargo miri test`** — catches UB on the Rust side.
- **Sanitizers** — ASan, TSan across the FFI boundary catch memory bugs in the C side.
- **Fuzzing** — `cargo fuzz` on decoders, parsers, anything that accepts adversarial input from C.
- **`valgrind`** — for binaries where sanitizers aren't available.

Pair sanitizer builds with fuzzing for FFI: many bugs only trigger with specific byte patterns.

## Common UB patterns at FFI

1. **Double-free** — Rust's `Drop` ran, then C's `free` ran.
2. **Wrong allocator** — Rust allocated with `Box`, C freed with `free`, or vice versa.
3. **Dangling pointer** — function returned a pointer into a dropped `String`.
4. **Panic across boundary** — Rust panicked into a C caller; `catch_unwind` missing.
5. **Lifetime confusion** — Rust gave C a `&str` and assumed the caller would copy it; C kept it past the Rust lifetime.
6. **Thread boundary** — Rust assumed `!Send` invariants; C passed the value to another thread.
7. **Reentrancy** — C called back into Rust while Rust still held a `&mut T` to the same data → UB.

## Checklist before shipping FFI

- [ ] `#[repr(C)]` on every public type crossing the boundary
- [ ] `extern "C"` on every exported function, with `#[unsafe(no_mangle)]` or explicit `#[unsafe(export_name = ...)]`
- [ ] `// SAFETY:` comment on every `unsafe` block and every `unsafe fn`
- [ ] `catch_unwind` at every C-callable function *or* `panic = "abort"` globally
- [ ] Ownership documented at every pointer-returning and pointer-accepting function
- [ ] `const` / `mut` in the C header matches Rust's `*const` / `*mut`
- [ ] Null checks before deref
- [ ] Miri passes on the pure-Rust exercises of the FFI surface
- [ ] ASan + fuzzing run on the mixed Rust/C harness
