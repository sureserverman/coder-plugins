# Android MCP + Mock Synapse

Two separate services:

- **android-mcp** — MCP server for Android emulators (6", 7", 10" AVDs). Use for **any** app: create AVDs, start emulators, install/launch apps, capture screenshots.
- **mock-synapse** — Minimal mock Matrix Synapse server. Start **only** when testing **Matrix Synapse Manager** (so the app can log in at http://10.0.2.2:8008).

## Prerequisites

- **Podman** (or Docker)
- **KVM** on the host (for fast emulators; `/dev/kvm` is passed into the container)
- App repo **matrix-synapse-manager-android** as a sibling of **mcp** (e.g. `../../matrix-synapse-manager-android` from this directory)

## Quick start

1. **Start services** (from this directory, `mcp/android`):

   - **MCP only** (for any app):  
     `podman compose up --build -d android-mcp`  
     → http://localhost:8000/mcp
   - **MCP + mock Synapse** (for Matrix Synapse Manager):  
     `podman compose up --build -d`  
     → MCP at http://localhost:8000/mcp, mock at http://localhost:8008 (example.com)

2. **Connect a client to the MCP server**

   - **Claude Code (preferred):** Installing the `android-dev` plugin auto-registers the server via the bundled `.mcp.json` at the plugin root. Run `/mcp` to confirm `android-emulator-mcp` appears. If `MCP_AUTH_TOKEN` is set on the compose service, also export `ANDROID_MCP_AUTH_TOKEN` in the shell that launches Claude Code — `.mcp.json` expands it into the `Authorization: Bearer …` header. Restart Claude Code after toggling the compose stack.

   - **Cursor (fallback):** Add the following to `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

     ```json
     {
       "mcpServers": {
         "android-emulator-mcp": {
           "type": "streamableHttp",
           "url": "http://localhost:8000/mcp"
         }
       }
     }
     ```

     Restart Cursor after changing MCP config.

3. **MCP tools** (work for any Android app; server running and Cursor connected):

   | Tool | Purpose |
   |------|---------|
   | `create-android-tablet-avds` | Create AVDs: phone6in, tablet7in, tablet10in. Optional: `optimizeConfig: true` (default) patches config.ini to disable sensors/audio/Play Store for faster, more stable runs. |
   | `start-android-tablet-emulators` | Start all three AVDs **in parallel**; wait for device state + boot. By default **useVirtualDisplay: true** so the emulator renders to Xvfb and **screencap is not black** (with `-no-window` only, screencap returns black). AVDs live in volume. |
   | `install-app-on-emulators` | Install APK from `/apks` (pass `apkPath` for any app) |
   | `launch-app` | Launch any app by `packageName` (and optional `activity`) on all emulators |
   | `capture-emulator-screenshots` | Capture N screenshots per device. For Matrix Synapse Manager use `loginFlow: "matrix-synapse"`, `navItemCount: 5`. **No fixed boot sleep:** waits for `sys.boot_completed` and for app in foreground (dumpsys window) before capturing. |
   | `matrix-synapse-login` | **App-specific:** add server + login for Matrix Synapse Manager (mock Synapse); use only for that app |

4. **Build the app** (from the app repo root):

   ```bash
   ./gradlew :app:assembleDebug
   ```

5. **Install the app** on all connected emulators (or use MCP tool `install-app-on-emulators`):

   ```bash
   podman exec android-mcp adb devices
   podman exec android-mcp adb install -r /apks/app-debug.apk
   ```

   (Install runs on all devices; for a single device use `adb -s emulator-5554 install -r /apks/app-debug.apk`.)

6. **Mock server and workflow (Matrix Synapse Manager)**

   - **Start mock before the app.** The mock must be reachable at `http://10.0.2.2:8008` from the emulator (host port 8008).
   - **URL to enter in the app:** `http://10.0.2.2:8008` (no trailing slash). The mock returns `/.well-known/matrix/client` with `base_url` derived from the request host so all API calls go to the same origin.
   - **Required mock endpoints** for the app to avoid errors/crashes after login: `/.well-known/matrix/client`, `/_matrix/client/v3/login`, `/_matrix/client/versions`, `/_synapse/admin/v1/server_version`, `/_synapse/admin/v2/users`, `/_matrix/client/v3/account/whoami`.
   - **Credentials:** **admin** / **1234** (mock also has alice/alicepass, bob/bobpass).

7. **Capture screenshots via MCP tool** (fully automated):

   Ensure **mock-synapse** is running (`podman compose up`). The tool will:
   - Launch the app on each emulator (fresh start),
   - Add server `http://10.0.2.2:8008` and log in as **admin** / **1234**,
   - Tap the first 4 bottom-nav tabs and capture a screenshot after each.

   No manual login or tab switching. Output: `play-screenshots/<avd>_users.png`, `_rooms.png`, `_stats.png`, `_settings.png`.

   ```bash
   mkdir -p ../../matrix-synapse-manager-android/play-screenshots
   # From your MCP client, call capture-emulator-screenshots
   ```

   For **Matrix Synapse Manager** use `loginFlow: "matrix-synapse"` and ensure mock-synapse is running. For **any other app** use `launchPackage: "com.yourapp.debug"`, `loginFlow: "none"`, and set `navItemCount` to match the app’s bottom nav (e.g. 3 or 5).

## Using with another app

- **APK:** Override the `/apks` volume when running compose (e.g. mount your app’s `app/build/outputs/apk/debug`), or pass `apkPath` to `install-app-on-emulators` (e.g. `/apks/other-app-debug.apk` if you mount it).
- **Screenshots:** Override the `/screenshots` volume so PNGs go to a folder you choose.
- **Flow:** Install your APK → `launch-app` with your app’s package name → `capture-emulator-screenshots` with `launchPackage` set (or leave unset if already in app), `loginFlow: "none"`, and `navItemCount` matching your app’s bottom nav (e.g. 3 for 3 tabs, 5 for 5). Use `autoNavigate: false` and `delayMs` if you prefer to switch screens manually.

## Volumes

- **android-sdk** — persistent SDK/AVD data for the MCP container  
- **../../matrix-synapse-manager-android/app/build/outputs/apk/debug** → `/apks` (read-only)  
- **../../matrix-synapse-manager-android/play-screenshots** → `/screenshots` (capture script writes here)

If your app repo is elsewhere, adjust the volume paths in `compose.yaml` (paths are relative to `mcp/android`).

## Mock Synapse

- **Admin**: `@admin:example.com` / **1234**  
- **Users**: `@alice:example.com` / alicepass, `@bob:example.com` / bobpass  
- Endpoints: `/_matrix/client/versions`, `/_matrix/client/v3/login`, `/_synapse/admin/v2/users`, `/_matrix/client/v3/account/whoami`

## Running services separately

- **Only MCP** (other apps, generic screenshots):  
  `podman compose up -d android-mcp`
- **Only mock Synapse** (e.g. already have MCP elsewhere):  
  `podman compose up -d mock-synapse`
- **Both** (Matrix Synapse Manager):  
  `podman compose up -d`

## Best practices alignment (emulator + mock testing)

This setup is aimed at **screenshot capture and scripted UI flows** against a **fake backend**, not at replacing in-app instrumented tests (Espresso + MockWebServer). Relative to common Android/emulator testing advice:

| Practice | Our setup | Notes |
|----------|-----------|--------|
| **Hermetic / stable network** | ✅ Mock server under control; no real backend. | Matches “mock network for stability” (Android UI Testing Cookbook). We use an external mock, not in-process MockWebServer. |
| **Same origin for discovery + API** | ✅ Mock returns `base_url` from request host. | Avoids mixed-content and wrong-host issues. |
| **Start mock before app** | ✅ Documented and required. | App discovery and post-login calls hit the mock immediately. |
| **Implement all endpoints used after login** | ✅ well-known, login, versions, server_version, users, whoami. | Missing endpoints cause 404 → errors/crashes; we cover the flow we use. |
| **Emulator in container** | ✅ Podman/Docker, KVM. | Aligns with “emulator in Docker” for reproducibility. |
| **Wait for boot** | ✅ Parallel start; wait for device state then sys.boot_completed. | Avoids acting on not-ready emulators.|
| **Cleartext only where needed** | ✅ App allows cleartext only for 10.0.2.2/localhost. | Safe for local/mock testing. |
| **UI automation** | ⚠️ `adb` input + screencap. | We do **black-box** automation (no Espresso, no test code in app). Good for store screenshots and manual-like flows; more flaky than Espresso + semantic selectors. Best practice for *instrumented* tests is Espresso + wait for content. |
| **Timing** | ⚠️ Condition-based where possible. | Best practice is “wait for condition” (idle or element). We wait for sys.boot_completed and app in foreground; short fixed delays (1–3 s) only for UI transitions we can't detect via adb. |
| **Emulator config** | ✅ Optional optimization. | `create-android-tablet-avds` with `optimizeConfig: true` (default) patches each AVD’s config.ini to disable sensors, audio, and Play Store (see [emulator setup](https://android-ui-testing.github.io/Cookbook/practices/emulator_setup/)). Set `optimizeConfig: false` to keep defaults. |
| **In-app test build** | ❌ Not used. | We run the **real** app against a real URL pointing at the mock. Hermetic *instrumented* tests often use a test build + Hilt test module + MockWebServer; that’s a different use case (unit/integration tests). |

**Summary:** For **screenshot and scripted E2E flows** with a **mock backend**, this is in line with best practices (hermetic network, same origin, mock before app, full endpoint coverage, emulator in container, wait for boot). It is **not** a substitute for **hermetic instrumented UI tests** (Espresso + MockWebServer + test doubles in the app).

### Why were screenshots black?
With **-no-window** (headless), the Android emulator does not attach to any display, so nothing is rendered and `adb screencap` returns a black or empty image. The fix is to run the emulator **without** -no-window but with a **virtual display** (Xvfb). The container entrypoint starts Xvfb on `:99`; `start-android-tablet-emulators` uses **useVirtualDisplay: true** by default so the emulator renders to that display and screenshots capture the real UI. Use `useVirtualDisplay: false` only if you don't need screenshots (faster, but screencap will be black).

### Why are emulators slow?

- **Cold boot:** The first time an AVD starts (or after a wipe), there is no Quick Boot snapshot, so the emulator does a full cold boot (~1–2 min). Later runs can be faster if the emulator saves a snapshot on exit (Quick Boot is on by default; we do not pass `-no-snapshot-load`).
- **No long fixed sleeps:** We no longer use a 30s “boot settle”; we wait for `sys.boot_completed` and for the app to be in foreground, so automation proceeds as soon as the system is ready.
- **Config optimizations (sensors/audio off)** do not slow the emulator; they reduce background work. If you see slowness after enabling them, try `optimizeConfig: false` when creating AVDs to rule out a bad interaction.
- **Resource contention:** Running multiple emulators (e.g. 3) on the same host competes for CPU and RAM; each will be slower than a single instance.

## Stop

```bash
podman compose down
```

Stops all services that were started. Emulators started by the MCP tool keep running until you kill them (e.g. `adb -s emulator-5554 emu kill` or close the container).
