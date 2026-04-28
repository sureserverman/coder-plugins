---
name: android-mcp-orchestrator
description: Use when the user asks to run the Android MCP, test an app on emulators, capture Play-style screenshots, take emulator screenshots, install an APK on emulators, or run any emulator/screenshot flow for an Android app. Also trigger on "android-mcp", "phone6in/tablet7in/tablet10in", or mentions of the multi-emulator stack.
---

# Android MCP Orchestrator

Orchestrates the Android MCP multi-container stack: ensure built and running, run the user's task via MCP tools (for **any** Android app), then tear down.

## When to use

- User wants to use the Android MCP, test an app on emulators, capture screenshots, or run the "full emulator flow."
- User expects the MCP (and mock Synapse, if needed) to be **started for the task and stopped when done**.

## Architecture (multi-container)

- **3 emulator containers** (phone6in, tablet7in, tablet10in): each bakes the Android SDK into the image, creates its AVD on first boot, and runs the emulator with an adb server on `0.0.0.0:5037`.
- **1 MCP server container** (android-mcp): connects to emulators via `adb -H <ip> -P 5037`. Depends on all 3 emulators being healthy.
- **1 optional mock-synapse container** (behind `mock` profile): for testing Matrix Synapse Manager.
- **Static IPs** on a custom bridge network (10.89.0.0/24). No DNS dependency.

## Compose location

- **Compose root:** `infrastructure/` — bundled inside this plugin. Resolves to `~/.claude/plugins/android-dev/infrastructure` (marketplace install) or `~/.claude/plugins/local/android-dev/infrastructure` (local install). The bundled `up.sh` / `down.sh` resolve this automatically; pass an explicit path only when running against an out-of-tree compose stack.
- **Services:** `emulator-phone6in`, `emulator-tablet7in`, `emulator-tablet10in`, `android-mcp`, `mock-synapse` (profile: mock).

## Workflow (in order)

### 1. Ensure stack is built and running

**Preferred — use the bundled scripts** (they wrap the build + health-wait loop so there's no copy-paste of the polling curl):

```bash
# Matrix Synapse Manager (needs the mock-synapse profile):
skills/android-mcp-orchestrator/scripts/up.sh --mock
# Any other app:
skills/android-mcp-orchestrator/scripts/up.sh
```

`up.sh` builds the stack, starts containers, and polls `http://localhost:8000/mcp` every 10s (up to ~10 min) until HTTP 405 or 200 is returned — first launch takes ~60-120s (AVD creation + boot), subsequent ~30-60s. The compose root defaults to the bundled `infrastructure/` (resolved relative to the script); pass a different path as the second argument to use an out-of-tree stack.

<details>
<summary>Manual steps (fallback — only if the script isn't available)</summary>

- **Check MCP:** `curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/mcp` (405 = running).
- **If MCP not running**, resolve the bundled infrastructure dir:
  - Marketplace install: `INFRA_DIR=~/.claude/plugins/android-dev/infrastructure`
  - Local install: `INFRA_DIR=~/.claude/plugins/local/android-dev/infrastructure`
- Then start the stack:
  - **Testing Matrix Synapse Manager:**
    ```bash
    cd "$INFRA_DIR"
    podman compose build
    podman compose --profile mock up -d
    ```
  - **Any other app:**
    ```bash
    cd "$INFRA_DIR"
    podman compose build
    podman compose up -d
    ```
- Wait until MCP responds (retry curl if needed; the emulator boot + MCP startup takes 1-2 minutes).

</details>

### 2. Fulfill the user's request via MCP tools

Call MCP tools at `http://localhost:8000/mcp`. Use `Accept: application/json, text/event-stream` header. These work for **any** Android app:

| Tool | Use |
|------|-----|
| `start-android-tablet-emulators` | Verify adb connectivity to all 3 emulators. Call this first to confirm readiness. AVDs are created automatically by the container entrypoint. |
| `install-app-on-emulators` | Install APK; pass `apkPath` (default: `/apks/app-debug.apk`). Mount the app's APK dir in compose or override volume. |
| `launch-app` | Launch **any** app: `packageName` (e.g. `com.example.app.debug`), optional `activity`. |
| `capture-emulator-screenshots` | Capture N screenshots per device. **Any app:** set `launchPackage` to app's package, `loginFlow: "none"`, `navItemCount` to match bottom nav (3–10). Optionally `autoNavigate: false` and `delayMs` to switch screens manually. **Matrix Synapse Manager only:** set `loginFlow: "matrix-synapse"` (requires mock-synapse). |
| `matrix-synapse-login` | **Only for Matrix Synapse Manager:** add server + login (mock Synapse). Ignore for other apps. |

**Typical flow for any app:** `start-android-tablet-emulators` → `install-app-on-emulators` → `launch-app` with package → `capture-emulator-screenshots` with `launchPackage`, `navItemCount`, `loginFlow: "none"`.

**For Matrix Synapse Manager:** Same, but use `loginFlow: "matrix-synapse"` in capture (and ensure mock-synapse is up), or call `matrix-synapse-login` before capture.

### 3. Shut down the stack

**Preferred:**

```bash
skills/android-mcp-orchestrator/scripts/down.sh          # matches a plain up.sh
skills/android-mcp-orchestrator/scripts/down.sh --mock   # matches up.sh --mock
```

<details>
<summary>Manual steps (fallback — only if the script isn't available)</summary>

From compose directory:
```bash
# If mock-synapse was started:
podman compose --profile mock down
# Otherwise:
podman compose down
```

</details>

## Path resolution

- The bundled `infrastructure/` ships inside this plugin and is resolved automatically by `up.sh`/`down.sh` relative to the script's own location — no manual path math needed.
- To run against an out-of-tree compose stack, pass its directory as the second argument: `up.sh --mock /path/to/your/compose-root`.

## Key differences from v1

- **No `create-android-tablet-avds` tool** — AVDs are created automatically by each emulator container's entrypoint on first boot. Per-device AVD volumes persist across restarts.
- **Emulators are containers**, not adb-managed on the host.
- **SDK baked into image** — first build downloads ~2GB (cached for subsequent builds).
- **Static IPs** — podman-compose DNS is unreliable; containers use fixed IPs on 10.89.0.0/24.

## Checklist

- [ ] Determine if Matrix Synapse Manager is being tested (matrix-synapse-login or loginFlow matrix-synapse). If yes, use `--profile mock`; otherwise start without mock.
- [ ] Check MCP is up (curl); if not, run `up.sh [--mock]` (resolves to bundled `infrastructure/`).
- [ ] Wait for emulators to boot (~1-2 min) and verify MCP is responding.
- [ ] Run the user's operations (install/launch/capture; use package name, apkPath, navItemCount, loginFlow as needed).
- [ ] Run `down.sh [--mock]` when done (or `podman compose [--profile mock] down` from the bundled `infrastructure/` dir).
