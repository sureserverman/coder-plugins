---
name: android-mcp-orchestrator
description: Use when the user asks to run the Android MCP, test an app on emulators, capture Play-style screenshots, or run any emulator/screenshot flow for an Android app. Also trigger on "android-mcp", "phone6in/tablet7in/tablet10in", or mentions of the multi-emulator stack.
---

# Android MCP Orchestrator

Owns the **ephemeral** lifecycle of the Android MCP multi-container stack: the stack is **off by default** (no podman containers, no listener), the skill brings it up for one task, runs the user's calls, and tears it down on exit — even on error.

## Lifecycle rule

The Android emulator stack must be **off** between tasks. There is no always-on MCP registration: this skill is the lifecycle owner. Every `up.sh` must be paired with a `down.sh`, and the canonical entrypoint is `scripts/run.sh`, which trap-guarantees teardown.

If you are tempted to call `up.sh` without arranging teardown, use `run.sh` instead.

## Architecture (multi-container)

- **3 emulator containers** (phone6in, tablet7in, tablet10in): each bakes the Android SDK into the image, creates its AVD on first boot, and runs the emulator with an adb server on `0.0.0.0:5037`.
- **1 MCP server container** (android-mcp): connects to emulators via `adb -H <ip> -P 5037`. Depends on all 3 emulators being healthy. Listens on `127.0.0.1:8000` on the host (loopback only).
- **1 optional mock-synapse container** (behind `mock` profile): for testing Matrix Synapse Manager.
- **Static IPs** on a custom bridge network (10.89.0.0/24).

The "MCP server" is **not** registered with Claude Code as an MCP. It is a private JSON-RPC backend the skill talks to over loopback via `scripts/mcp-call.sh`. There is no `.mcp.json` for this stack.

## Auth

`scripts/up.sh` generates `infrastructure/.env` with a random `MCP_AUTH_TOKEN` on first run (mode 600, gitignored). `mcp-call.sh` reads it and sends the bearer header. Operators do not need to manage the token by hand.

## Canonical flow — `scripts/run.sh`

`run.sh` is the one-shot wrapper: brings the stack up, executes a sequence of JSON-RPC calls from stdin, then **always** tears the stack down via an `EXIT` trap.

```bash
# Any Android app (no mock-synapse):
skills/android-mcp-orchestrator/scripts/run.sh <<'EOF'
tools/call start-android-tablet-emulators {}
tools/call install-app-on-emulators {"apkPath":"/apks/app-debug.apk"}
tools/call launch-app {"packageName":"com.example.app.debug"}
tools/call capture-emulator-screenshots {"loginFlow":"none","navItemCount":5,"launchPackage":"com.example.app.debug"}
EOF

# Matrix Synapse Manager (needs mock-synapse):
skills/android-mcp-orchestrator/scripts/run.sh --mock <<'EOF'
tools/call start-android-tablet-emulators {}
tools/call install-app-on-emulators {"apkPath":"/apks/app-debug.apk"}
tools/call matrix-synapse-login {}
tools/call capture-emulator-screenshots {"loginFlow":"matrix-synapse","navItemCount":5}
EOF
```

After `run.sh` exits — for any reason — there must be no `infrastructure_*` containers running. If you spot some, run `scripts/down.sh [--mock]` to clean them up.

## When to split `up.sh` + `mcp-call.sh` + `down.sh`

Use the paired form **only** when you need to call the MCP from multiple separate shell invocations (e.g., interactive iteration during development). You are then responsible for the matching `down.sh`. Wrap it in your own trap if at all possible:

```bash
trap 'skills/android-mcp-orchestrator/scripts/down.sh --mock' EXIT
skills/android-mcp-orchestrator/scripts/up.sh --mock
skills/android-mcp-orchestrator/scripts/mcp-call.sh tools/list
# ... more calls ...
```

## Available MCP tools (called via `mcp-call.sh tools/call`)

| Tool | Use |
|------|-----|
| `start-android-tablet-emulators` | Verify adb connectivity to all 3 emulators. Call this first to confirm readiness. AVDs are created automatically by the container entrypoint. |
| `install-app-on-emulators` | Install APK; pass `apkPath` (default: `/apks/app-debug.apk`). Mount the app's APK dir in compose. |
| `launch-app` | Launch **any** app: `packageName`, optional `activity`. |
| `capture-emulator-screenshots` | Capture N screenshots per device. For any app: set `launchPackage`, `loginFlow: "none"`, `navItemCount` (3–10). For Matrix Synapse Manager: `loginFlow: "matrix-synapse"` (requires mock-synapse). |
| `matrix-synapse-login` | **Only for Matrix Synapse Manager:** add server + login (mock Synapse). Ignore for other apps. |

`mcp-call.sh tools/list` prints the full live schema.

## Path resolution

- `scripts/run.sh` / `up.sh` / `down.sh` / `mcp-call.sh` resolve the bundled `infrastructure/` directory relative to their own location. No manual path math needed.
- For an out-of-tree compose stack, pass its directory as the trailing positional arg to `up.sh` / `down.sh`.

## Checklist

- [ ] Decide if Matrix Synapse Manager is in play; if yes, pass `--mock`.
- [ ] Use `run.sh` with a here-doc of JSON-RPC calls — do NOT call `up.sh` without a matching teardown plan.
- [ ] If you must use `up.sh` directly, install a `trap '... down.sh ...' EXIT` first.
- [ ] After the script exits, confirm `podman ps` shows no `infrastructure_*` containers.
