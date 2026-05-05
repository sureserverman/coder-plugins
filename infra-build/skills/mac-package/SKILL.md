---
name: mac-package
description: Use when creating, updating, or validating the `mac/` layout that the `infra/build-for-mac` GitHub Actions pipeline expects — scaffolding `mac/Makefile`, `mac/payload/`, `mac/scripts/`, fixing Makefile targets (`build`, `package`, `install`, `clean`), writing postinstall scripts, wiring `launchctl bootout`/`bootstrap`, setting up `LaunchAgent` plists, or diagnosing `pkgbuild` failures.
---

# macOS Package Reference

## Canonical Directory Structure

```
<project>/
└── mac/
    ├── Makefile
    ├── payload/                         ← mirrors / filesystem, .gitkeep placeholders
    │   ├── Library/
    │   │   ├── LaunchAgents/            ← user-level daemons (plist files)
    │   │   └── LaunchDaemons/           ← system-level daemons (plist files)
    │   └── usr/local/
    │       └── bin/                     ← .gitkeep (binary copied at build time)
    └── scripts/
        ├── postinstall                  ← always present
        └── preinstall                   ← optional, stops existing instance
```

**Build commands:**
```bash
make -C mac pkg           # full build
make -C mac clean         # clean build artifacts
```

---

## Makefile Pattern

```makefile
BINARY   := <name>
PKG_ID   ?= com.sureserverman.<name>
VERSION  ?= 1.0.0
TARGET   := aarch64-apple-darwin        # Apple Silicon

.PHONY: build payload pkg clean

build:
	cd ../rust && cargo build --release --target $(TARGET)
	# or: cd ../swift && swift build -c release --arch arm64

payload: build
	rm -rf build
	mkdir -p build/payload/usr/local/bin
	rsync -a --exclude='.gitkeep' payload/ build/payload/
	cp ../rust/target/$(TARGET)/release/$(BINARY) build/payload/usr/local/bin/

pkg: payload
	pkgbuild \
	  --root build/payload \
	  --identifier $(PKG_ID) \
	  --version $(VERSION) \
	  --install-location / \
	  --scripts scripts \
	  $(BINARY).pkg

clean:
	rm -rf build *.pkg
```

**Critical:** `--scripts scripts` must be present in `pkgbuild`. Missing it is the most common packaging bug — scripts run but package contents are wrong/empty.

---

## postinstall Script Pattern

```zsh
#!/bin/zsh

# Always set PATH for Homebrew compatibility
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Console user detection — never use $USER (it's root during install)
CONSOLE_USER=$(stat -f "%Su" /dev/console)
CONSOLE_UID=$(id -u "$CONSOLE_USER")

PLIST="/Library/LaunchAgents/com.sureserverman.<name>.plist"

# Set correct plist ownership and permissions
chmod 644 "$PLIST"
chown root:wheel "$PLIST"

# Unload existing instance (idempotent)
launchctl bootout "gui/$CONSOLE_UID/$PLIST_LABEL" 2>/dev/null || true

# Load the agent
launchctl bootstrap "gui/$CONSOLE_UID" "$PLIST"

exit 0
```

---

## preinstall Script Pattern

```bash
#!/bin/bash
PLIST_LABEL="com.sureserverman.<name>"
CONSOLE_USER=$(stat -f "%Su" /dev/console)
CONSOLE_UID=$(id -u "$CONSOLE_USER")

# Stop existing instance before upgrade
launchctl bootout "gui/$CONSOLE_UID/$PLIST_LABEL" 2>/dev/null || true
killall <name> 2>/dev/null || true

exit 0
```

---

## LaunchAgent vs LaunchDaemon

| Use | Directory | Runs as |
|-----|-----------|---------|
| User-level daemon (tray, watcher) | `Library/LaunchAgents/` | console user |
| System-level daemon (network, security) | `Library/LaunchDaemons/` | root |

**Plist label convention:** `com.sureserverman.<name>`

**Plist permissions:**
- `chmod 644`
- `chown root:wheel`

**setuid binary** (when binary needs root): `chmod 4755 /usr/local/bin/<name>`

---

## Validation Checklist

When auditing or before building, verify:

- [ ] `Makefile` has all 4 targets: `build`, `payload`, `pkg`, `clean`
- [ ] `pkgbuild` includes `--scripts scripts` flag
- [ ] `PKG_ID` follows `com.sureserverman.<name>` convention
- [ ] Binary is copied to `build/payload/` not directly into `payload/`
- [ ] `postinstall` uses `#!/bin/zsh` (not bash)
- [ ] `postinstall` has Homebrew PATH export
- [ ] Console user uses `stat -f "%Su" /dev/console` (not `$USER` or `$SUDO_USER`)
- [ ] launchctl uses `bootstrap`/`bootout` (never deprecated `load`/`unload`)
- [ ] Plist files: `chmod 644`, `chown root:wheel`
- [ ] `payload/usr/local/bin/` contains `.gitkeep` (binary added at build time, not committed)

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Missing `--scripts scripts` in pkgbuild | Add `--scripts scripts` — most common bug |
| `$USER` in postinstall | Use `stat -f "%Su" /dev/console` |
| `launchctl load/unload` | Use `launchctl bootstrap/bootout` |
| Binary committed to `payload/` | Use `.gitkeep`, copy in `payload:` Makefile target |
| `#!/bin/bash` in postinstall | Use `#!/bin/zsh` |
| Homebrew `tor`/`brew services` without PATH | Always export Homebrew PATH first |
| `chmod 644` on setuid binary | setuid binaries need `chmod 4755` |
