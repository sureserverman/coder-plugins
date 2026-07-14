#!/bin/bash
# rust-project analyze.sh — run the 5-pass analysis sequence
# Usage: ./analyze.sh [project-root]
# If no arg given, auto-detects: uses ./rust if present, else current dir.

set -u

PROJECT_ROOT="${1:-}"
if [ -z "$PROJECT_ROOT" ]; then
  if [ -f "rust/Cargo.toml" ]; then
    PROJECT_ROOT="rust"
  elif [ -f "Cargo.toml" ]; then
    PROJECT_ROOT="."
  else
    echo "error: no Cargo.toml found in . or ./rust — pass a path explicitly" >&2
    exit 2
  fi
fi

cd "$PROJECT_ROOT" || { echo "error: cannot cd to $PROJECT_ROOT" >&2; exit 2; }
echo "=== rust-project analyze @ $(pwd) ==="

section() { echo; echo "--- $1 ---"; }

# Pass 0 — Tooling Preflight
section "Pass 0: Tooling Preflight"
rustup target list --installed | grep -q aarch64-apple-darwin \
  || rustup target add aarch64-apple-darwin
for tool in cargo-outdated cargo-audit cargo-machete cargo-tarpaulin; do
  short="${tool#cargo-}"
  if cargo "$short" --version &>/dev/null; then
    echo "ok: $tool already installed"
  else
    echo "installing: $tool"
    cargo install "$tool"
  fi
done

# Pass 1 — Code Quality
section "Pass 1: Code Quality — cargo fmt --check"
cargo fmt --check || true
section "Pass 1: Code Quality — cargo clippy -- -D warnings"
cargo clippy -- -D warnings || true
section "Pass 1: Code Quality — cargo check --target aarch64-apple-darwin"
cargo check --target aarch64-apple-darwin || true

# Pass 2 — Dependency Health
section "Pass 2: Dependency Health — cargo outdated"
cargo outdated || true
section "Pass 2: Dependency Health — cargo audit"
cargo audit || true
section "Pass 2: Dependency Health — cargo machete"
cargo machete || true

# Pass 3 — Tests + Coverage
section "Pass 3: cargo test"
if cargo test; then
  section "Pass 3: cargo tarpaulin --out Stdout"
  if [ "$(uname)" = "Darwin" ]; then
    echo "note: tarpaulin is Linux-only; skipping. Use 'cargo llvm-cov' on macOS."
  else
    cargo tarpaulin --out Stdout 2>&1 || true
  fi
else
  echo "tests failed — skipping tarpaulin"
fi

echo
echo "=== done. Synthesize findings into the unified report (see SKILL.md Pass 4) ==="
