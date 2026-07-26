---
description: Capture Play Store screenshots across all emulators (phone + tablets)
argument-hint: '[login|capture|full] [--tabs "Accounts,Rooms,Info,Config"]'
allowed-tools: [
  "Read",
  "Write",
  "Glob",
  "Grep",
  "Bash(podman:*)",
  "Bash(podman compose:*)",
  "Bash(curl:*)",
  "Bash(date:*)",
  "Bash(ls:*)",
  "Bash(cd:*)",
  "Bash(./skills/android-mcp-orchestrator/scripts/run.sh:*)",
  "Bash(./skills/android-mcp-orchestrator/scripts/up.sh:*)",
  "Bash(./skills/android-mcp-orchestrator/scripts/down.sh:*)",
  "Bash(./skills/android-mcp-orchestrator/scripts/mcp-call.sh:*)"
]
---

# Android Screenshots

Capture screenshots of an Android app across all emulator form factors (phone 6", tablet 7", tablet 10" landscape) using the Android MCP emulator stack.

The stack is **off by default**. This command brings it up via `scripts/run.sh`, does its work, and tears it down on exit. After the command finishes, there must be no `infrastructure_*` containers left running.

## Arguments

The user invoked this command with: $ARGUMENTS

## Modes

- **full** (default): Clear app data, run login flow, then capture all tabs
- **login**: Only run the login flow (add server + sign in) on all emulators
- **capture**: Only capture screenshots of current screen state (no login)

## Instructions

### 1. Run the ephemeral stack

Always use `scripts/run.sh` from the orchestrator skill. It auto-generates the auth token on first run, builds and starts the stack, runs your JSON-RPC sequence, and tears everything down (even on error) via an EXIT trap. Do NOT call `up.sh` without arranging teardown.

**Resolve the two mount paths before invoking.** `APK_DIR` is the host directory mounted at `/apks` and
has no working default — omit it and the stack exits **4** before starting anything. `SCREENSHOT_DIR` is
where the PNGs land on the host (mounted at `/screenshots`); it is created if missing. Use absolute paths
for both, taken from the project under test, or set them in `infrastructure/.env`. The examples below show
them inline; always set `SCREENSHOT_DIR` too when the mode captures screenshots, or the PNGs land inside
the installed plugin.

For modes `full` / `login`, pass `--mock` so the mock-synapse container is started.

Example invocation for `full`:

```bash
APK_DIR=/abs/path/to/project/app/build/outputs/apk/debug \
SCREENSHOT_DIR=/abs/path/to/project/play-screenshots \
skills/android-mcp-orchestrator/scripts/run.sh --mock <<'EOF'
tools/call start-android-tablet-emulators {}
tools/call install-app-on-emulators {"apkPath":"/apks/app-debug.apk"}
tools/call matrix-synapse-login {}
tools/call capture-emulator-screenshots {"loginFlow":"matrix-synapse","navItemCount":5,"tabLabels":["Accounts","Rooms","Info","Config"]}
EOF
```

For `capture` (no login, current screen):

```bash
APK_DIR=/abs/path/to/project/app/build/outputs/apk/debug \
SCREENSHOT_DIR=/abs/path/to/project/play-screenshots \
skills/android-mcp-orchestrator/scripts/run.sh <<'EOF'
tools/call start-android-tablet-emulators {}
tools/call capture-emulator-screenshots {"loginFlow":"none","navItemCount":5,"tabLabels":["Accounts","Rooms","Info","Config"]}
EOF
```

For `login` only:

```bash
APK_DIR=/abs/path/to/project/app/build/outputs/apk/debug \
skills/android-mcp-orchestrator/scripts/run.sh --mock <<'EOF'
tools/call start-android-tablet-emulators {}
tools/call install-app-on-emulators {"apkPath":"/apks/app-debug.apk"}
tools/call matrix-synapse-login {}
EOF
```

If the user passes `--tabs "A,B,C"`, substitute that list into the `tabLabels` JSON array.

If the user passes `--clear` or mode is `full`, the `capture-emulator-screenshots` tool will be combined with a preliminary clear step. Either extend the JSON-RPC sequence to call any clear-data tool the server exposes (`tools/call` schema is available via `scripts/mcp-call.sh tools/list`), or do it inline before `run.sh` exits — but never side-step the teardown trap.

### 2. Verify teardown

After `run.sh` returns, confirm the stack is gone:

```bash
podman ps --filter label=io.podman.compose.project=infrastructure --format '{{.Names}}'
```

It MUST be empty. If any containers remain, run `skills/android-mcp-orchestrator/scripts/down.sh --mock` explicitly.

### 3. Report results

Show the user:
- How many screenshots were captured
- The file paths under `$SCREENSHOT_DIR` on the host (the container's `/screenshots/` is volume-mounted there) — report the resolved path you actually used, not a fixed directory name
- Read and display one screenshot from each device as a sample

### Emulator details

| Device | IP | Resolution | Orientation |
|--------|----|-----------|-------------|
| phone6in | 10.89.0.10 | 1440x2560 | Portrait |
| tablet7in | 10.89.0.11 | 800x1280 | Portrait |
| tablet10in | 10.89.0.12 | 2560x1800 | Landscape |
