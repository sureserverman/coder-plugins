---
name: rust-project
description: Use when analyzing, auditing, or improving a Rust project in this ecosystem — dependency updates, security vulnerabilities, clippy lints, unused dependencies, test coverage, or cross-compile target validation for aarch64-apple-darwin. Trigger on "update my rust deps", "run clippy", "cargo audit", "cross-compile to aarch64-apple-darwin", "any unused crates", "bump my toolchain".
---

# Rust Project Analysis

Full analysis across 5 passes. Report all findings first, fix nothing until the user approves.

## Running the analysis

**Preferred — use the bundled script.** `scripts/analyze.sh` runs passes 0–3 end-to-end (tool preflight, fmt/clippy/check, outdated/audit/machete, tests/tarpaulin) and prints each section clearly labelled so you can paste findings straight into the Pass 4 summary.

```bash
skills/rust-project/scripts/analyze.sh            # auto-detects ./rust or .
skills/rust-project/scripts/analyze.sh path/to/crate
```

It auto-detects the project layout (standalone vs `rust/` subdirectory), adds the `aarch64-apple-darwin` target if missing, and installs `cargo-outdated`/`audit`/`machete`/`tarpaulin` if not present. It skips `tarpaulin` on macOS with a note to use `cargo llvm-cov`. It does **not** apply fixes — that still needs your judgment and user approval at Pass 4.

<details>
<summary>Manual pass-by-pass commands (fallback — only if the script isn't available)</summary>

## Project Layout Detection

These projects follow two layouts — detect before running any commands:

```
Standalone:          With rust/ subdirectory:
<project>/           <project>/
└── Cargo.toml       ├── rust/
                     │   └── Cargo.toml
                     ├── deb/
                     └── mac/
```

All `cargo` commands run from the directory containing `Cargo.toml`.

**Standalone projects:** hist-lens, usb-check, tor-v3-vanity
**rust/ subdirectory projects:** exit-node-flag, multitor, metabrush, pick-a-boo, usb-lock

---

## Pass 0 — Tooling Preflight

Check and install missing tools before running analysis:

```bash
# Cross-compile target
rustup target list --installed | grep -q aarch64-apple-darwin \
  || rustup target add aarch64-apple-darwin

# Analysis tools (install only if missing)
cargo outdated --version &>/dev/null || cargo install cargo-outdated
cargo audit    --version &>/dev/null || cargo install cargo-audit
cargo machete  --version &>/dev/null || cargo install cargo-machete
cargo tarpaulin --version &>/dev/null || cargo install cargo-tarpaulin
```

Report which tools were already present vs newly installed.

---

## Pass 1 — Code Quality

```bash
# Formatting drift
cargo fmt --check

# Lints (treat warnings as errors to surface everything)
cargo clippy -- -D warnings

# Cross-compile target check (catches target-specific issues early)
cargo check --target aarch64-apple-darwin
```

For each clippy lint: note rule name, file:line, and the suggested fix.
For cross-compile errors: note whether the issue is a missing target feature, platform API, or dependency that doesn't support the target.

---

## Pass 2 — Dependency Health

```bash
# Outdated crates (direct and transitive)
cargo outdated

# Known CVEs
cargo audit

# Declared but unused dependencies
cargo machete
```

For `cargo outdated`: group by **direct** (in `[dependencies]`) vs **transitive**. Only direct deps need manual bumping in `Cargo.toml`.

For `cargo audit`: include the advisory ID, affected versions, severity (critical/high/medium/low), and link.

For `cargo machete`: list each unused dep with the line in `Cargo.toml` to remove.

---

## Pass 3 — Test Coverage

```bash
# Run tests first — don't run tarpaulin if tests fail
cargo test 2>&1

# Coverage (only if tests pass)
cargo tarpaulin --out Stdout 2>&1
```

Report:
- Overall line coverage %
- Files below 50% coverage (flag as WARN)
- Files with 0% coverage (flag as ERROR if they contain non-trivial logic)

Note: `cargo tarpaulin` is Linux-only. If running on macOS, use `cargo llvm-cov` instead (requires `cargo install cargo-llvm-cov`).

</details>

---

## Pass 4 — Summary Report

After all passes complete, output a unified findings table:

```
| Pass | Severity | Finding                                      |
|------|----------|----------------------------------------------|
| 1    | ERROR    | clippy: unused variable `x` in src/main.rs:42|
| 1    | WARN     | fmt: 3 files have formatting drift           |
| 1    | WARN     | cross: missing cfg for unix target in lib.rs |
| 2    | ERROR    | audit: RUSTSEC-2024-XXXX in openssl 0.10.55  |
| 2    | WARN     | outdated: serde 1.0.150 → 1.0.219 (direct)  |
| 2    | INFO     | machete: `rand` declared but not used        |
| 3    | WARN     | coverage: src/parser.rs at 31%               |
```

Then ask:
> "Which of these do you want me to fix? I can handle: fmt fixes, clippy auto-fixes, Cargo.toml dependency bumps, removing unused deps. Clippy warnings requiring logic changes and coverage gaps need your input."

**Do not apply any fix until the user responds.**

---

## Applying Fixes (after approval)

| Fix type | Command |
|----------|---------|
| Formatting | `cargo fmt` |
| Clippy auto-fix | `cargo clippy --fix -- -D warnings` |
| Bump direct dep | Edit `Cargo.toml` version, then `cargo update` |
| Remove unused dep | Remove line from `Cargo.toml`, then `cargo update` |
| Update all direct deps to latest | Edit each version in `Cargo.toml` manually (don't use `cargo upgrade` blindly) |

After applying fixes, re-run the relevant pass to confirm the finding is resolved before reporting it as fixed.

---

## Common Issues in This Ecosystem

| Issue | Likely cause |
|-------|-------------|
| `aarch64-apple-darwin` linker error | Need `x86_64-apple-darwin` linker via `osxcross` or cross-rs |
| Dep doesn't compile for aarch64 | Check crate's supported targets in docs.rs |
| tarpaulin fails | Check if running in container (needs `--engine llvm` flag) |
| `cargo outdated` slow | First run downloads index — normal |
| machete false positive | Check `#[allow(unused)]` or feature-gated usage |
