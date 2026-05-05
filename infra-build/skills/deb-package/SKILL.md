---
name: deb-package
description: Use when creating, updating, or validating the Debian `.deb` layout that the `infra/utils/pkgskel` + `publish` pipeline expects — scaffolding `deb/package/DEBIAN/control`, fixing broken control fields, writing `postinst`/`prerm` scripts, wiring systemd integration, or diagnosing `dpkg-deb` build errors. Reference for the canonical `deb/package/DEBIAN/`, `deb/package/usr/bin/`, `deb/amd64/`, `deb/arm64/` tree.
---

# Debian Package Reference

> **WARNING:** Many projects have BOTH `deb/` and `mac/` directories. The `mac/` directory (with its own `Makefile`, `payload/`, `scripts/`) belongs to the macOS .pkg installer. **Do NOT modify, move, delete, or reorganize anything under `mac/`** when working on deb packaging. They are independent packaging pipelines that happen to share the same repo.

## Project Directory Structure

Projects with compiled (Rust) binaries follow this layout:

```
<project>/
├── rust/                ← Rust source + Makefile
│   ├── Cargo.toml
│   ├── Cargo.lock
│   ├── build.rs         ← if needed
│   ├── Makefile         ← builds binary, moves to deb/
│   └── src/
├── deb/
│   ├── amd64/           ← x86_64 binary staged here by Makefile
│   ├── arm64/           ← aarch64 binary staged here by Makefile
│   └── package/
│       ├── DEBIAN/
│       │   └── control
│       └── usr/bin/     ← binary copied from amd64/ or arm64/ before dpkg-deb
├── mac/                 ← macOS .pkg (DO NOT TOUCH from deb workflow)
└── README.md
```

Non-Rust (pure bash) projects skip the `rust/` directory entirely.

## Rust Makefile Convention

The Makefile lives at `rust/Makefile` (not project root). Standard pattern:

```makefile
BINARY := <binary-name>

.PHONY: all x86_64 aarch64 clean
all: x86_64 aarch64

x86_64:
	rustup target add x86_64-unknown-linux-gnu
	CARGO_TARGET_DIR=target/x86_64 \
	  cargo build --release --target x86_64-unknown-linux-gnu
	mkdir -p $(HOME)/dev/<project>/deb/amd64
	mv target/x86_64/x86_64-unknown-linux-gnu/release/$(BINARY) \
	   $(HOME)/dev/<project>/deb/amd64/$(BINARY)

aarch64:
	rustup target add aarch64-unknown-linux-gnu
	CARGO_TARGET_DIR=target/aarch64 \
	  cargo build --release --target aarch64-unknown-linux-gnu
	mkdir -p $(HOME)/dev/<project>/deb/arm64
	mv target/aarch64/aarch64-unknown-linux-gnu/release/$(BINARY) \
	   $(HOME)/dev/<project>/deb/arm64/$(BINARY)

clean:
	rm -rf target $(HOME)/dev/<project>/deb/{amd64,arm64}/*
```

**Rules:**
- Makefile goes in `rust/`, NOT the project root
- Each arch builds into a separate `CARGO_TARGET_DIR` (e.g. `target/x86_64/`)
- Binary is moved (not copied) into `deb/amd64/` or `deb/arm64/`
- If a project only supports one arch (e.g. CUDA = x86_64 only), omit the other target

---

## Deb Package Structure

```
<project>/
└── deb/
    └── package/
        ├── DEBIAN/
        │   ├── control       ← required
        │   ├── postinst      ← required if systemd/setup needed
        │   ├── preinst       ← optional, cleanup before install
        │   └── prerm         ← optional, cleanup before remove
        └── <filesystem mirror>
            ├── usr/bin/          ← binaries (755)
            ├── usr/local/bin/    ← alternative for non-system tools
            ├── etc/systemd/user/ ← user-level .service/.path/.timer
            └── etc/             ← config files
```

**Build command:** `dpkg-deb --build deb/package <name>.deb`

> Exception: ssh-menu-deb uses `package/` directly (no `deb/` wrapper) — legacy layout, don't replicate.

---

## Control File Format

```
Package: <name>
Version: <x.y.z>
Maintainer: Server Man
Architecture: all|amd64|arm64
Description: <one-line description>
Source: <repo-name>
Depends: <optional, comma-separated>
```

**Rules:**
- No trailing whitespace on `Depends:` line
- `Architecture: all` for pure-bash packages; `amd64` or `arm64` for compiled binaries
- Multi-arch compiled binaries use separate `amd64/` and `arm64/` sibling dirs

---

## postinst Patterns

### Header (always)
```bash
#!/bin/bash
```

### Root check (when needed)
```bash
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi
```

### Console user detection (systemd user units)
```bash
CONSOLE_USER="${SUDO_USER:-$USER}"
```

### Enabling systemd user units
```bash
# Enable globally for all users on future logins
systemctl --global enable <service>.path

# Activate for the installing user's current session
if [ -n "$CONSOLE_USER" ] && [ "$CONSOLE_USER" != "root" ]; then
  USER_ID=$(id -u "$CONSOLE_USER" 2>/dev/null) || true
  if [ -n "$USER_ID" ] && [ -d "/run/user/$USER_ID" ]; then
    su - "$CONSOLE_USER" -c "systemctl --user daemon-reload && systemctl --user restart <service>.path" || true
  fi
fi
```

### Enabling systemd system units
```bash
systemctl daemon-reload
systemctl enable <service>
systemctl start <service>
```

### Removing stale system-level copies of user units
```bash
rm -f /etc/systemd/system/<service>.timer
rm -f /etc/systemd/system/<service>.service
systemctl daemon-reload
systemctl --global enable <service>.timer
```

---

## Validation and CI

See [references/validation.md](references/validation.md) for the full pre-build checklist, common mistakes table, and a GitHub Actions pack workflow snippet. Consult it when auditing a package or troubleshooting a `dpkg-deb` failure.
