# android-dev

Claude Code plugin for Android development. Part of the [`coder-plugins`](..) marketplace.

## Installation

Add the marketplace:
```bash
/plugin marketplace add sureserverman/coder-plugins
```

Install the plugin:
```bash
/plugin install android-dev@coder-plugins
```

## Requirements

- Android SDK (platform + build-tools)
- JDK 21
- Podman (for emulator containers and mock servers)
- Gradle wrapper in the project (`./gradlew`)

The emulator infrastructure (compose stack, Containerfiles, MCP server, mock backend) is bundled in `infrastructure/` — no external repo needs to be *cloned*.

### Pointing the stack at your project

Both host mounts are configurable — you never edit `compose.yaml` to run the stack against a
different project:

| Variable | Default | Mounted at |
|---|---|---|
| `APK_DIR` | `./app/build/outputs/apk/debug` | `/apks` (read-only) |
| `SCREENSHOT_DIR` | `./play-screenshots` | `/screenshots` |

> **Don't confuse these with the container-side pair.** The MCP server reads `APK_BASE_DIR`
> and `SCREENSHOTS_DIR` (plural) — see [`infrastructure/mcp-server/server.mjs`](./infrastructure/mcp-server/server.mjs),
> which defaults them to `/apks` and `/screenshots`. Those name paths *inside* the container,
> which is the far end of the mounts above; `SCREENSHOT_DIR` and `SCREENSHOTS_DIR` differ by
> one letter and mean different things. Setting the container-side pair is not a supported way
> to aim the stack at a project — the host-side overrides in this table are.

Set either in `infrastructure/.env` (where `up.sh` seeds both as commented lines on first run) or in
the environment:

```bash
APK_DIR=/path/to/your-project/app/build/outputs/apk/debug \
SCREENSHOT_DIR=/path/to/your-project/play-screenshots \
  skills/android-mcp-orchestrator/scripts/up.sh
```

> **Use absolute paths — treat the relative defaults as placeholders.** Compose resolves relative
> mount paths from the compose directory, which is this plugin's bundled `infrastructure/` directory,
> *not* the project you are testing. There is no supported way to make the defaults resolve against
> your project (`up.sh` and `down.sh` take the compose directory as a positional argument only, and
> `run.sh` does not forward one), so set both variables to absolute paths for any real run.
>
> **In `.env`, write the path out in full — no `~`.** Compose reads `.env` as literal `KEY=VALUE`
> with no shell expansion, so `APK_DIR=~/dev/…` there tries to mount a directory named `~`. Tilde
> works only in the shell-invocation form shown above.
>
> **`up.sh` validates both paths before starting anything.** A missing `APK_DIR` is a hard error
> (exit 4) naming the path it tried and how to set it — because podman would otherwise create an
> empty directory for the missing bind source and the mistake would surface as "no APK found" from
> inside the container minutes later. `SCREENSHOT_DIR` is an output, so `up.sh` creates it instead
> (exit 5 if it cannot). The check reads the environment first and then `.env`, the same precedence
> compose itself uses. It parses plain and quoted `KEY=value` lines, which is a deliberate subset of
> compose's `.env` syntax — exotic forms (`export KEY=…`, spaces around `=`, `${OTHER}` interpolation,
> trailing inline comments) are not recognised, so `up.sh` may refuse a path compose would have
> accepted. It errs toward a loud false refusal, never toward the silent empty mount. Bypassing `up.sh`
> with a direct `podman compose up` skips these checks entirely and gets that silent behavior.

**Migration — `matrix-synapse-manager-android`.** Before these variables existed, `compose.yaml`
hardcoded `../../matrix-synapse-manager-android/{app/build/outputs/apk/debug, play-screenshots}`.
That path was relative to `infrastructure/`, so it resolved *inside this repo* — a directory that
does not exist — and therefore mounted empty for everyone. Use the checkout's real location:

```bash
APK_DIR=~/dev/android/matrix-synapse-manager-android/app/build/outputs/apk/debug \
SCREENSHOT_DIR=~/dev/android/matrix-synapse-manager-android/play-screenshots \
  skills/android-mcp-orchestrator/scripts/up.sh
```

## Skills

### `android-gradle-build`

Four-phase build management with decision trees and security hard gates. Covers module wiring, Hilt/Room/Retrofit/Compose setup, test execution, and commit validation.

**Triggers:** Add a module, fix build error, set up Hilt/Compose, add a dependency, run tests, edit version catalog, wire Retrofit/Room.

### `android-stage-verify`

The per-stage on-device gate. Builds the debug APK, checks `adb devices`, and when a device is attached installs it (`-r`), smoke-launches it (verifies the launcher Activity survives start-up), and runs `connectedDebugAndroidTest` if an `androidTest/` suite exists. Device-conditional: with no device attached it degrades to a build-only gate and reports the skip rather than claiming a pass. Invoked automatically by the `planning` plugin's `executing-plans` at each Android stage gate.

**Triggers:** Verify this stage on device, build and install on my phone, run the on-device gate, did this stage break the app.

### `android-ui-design-figma`

End-to-end UI workflow: app analysis, design spec (with optional Figma), feedback loop, then apply to code. Standard-first approach using Material 3 / Compose Material / AndroidX.

Includes reference files for M3 best practices, adaptive layouts, a component lookup table, and the adaptive launcher icon spec (foreground/background/monochrome layers, themed icons, Image Asset Studio scaffold + verification recipe — required for every release).

**Triggers:** Redesign a screen, change color scheme, update theme, add bottom nav, implement Figma design, fix spacing, add dark theme, Material 3 components, adaptive launcher icon, themed icon, monochrome layer.

### `android-ui-layout-patterns`

Jetpack Compose layout and Material 3 styling rules — spacing, cards, grids, alignment. The decision-rule companion to `android-ui-design-figma`'s full design workflow; routed to for Compose-screen tasks during plan execution.

**Triggers:** Build or fix a Compose layout, spacing/padding, cards, grids, alignment, Material 3 styling.

### `kotlin-compose-testing-patterns`

Testing patterns for Kotlin Android apps with Compose, Espresso, and MockWebServer. Covers UI tests, instrumented tests, and test-infrastructure setup.

**Triggers:** Write Android tests, UI/instrumented tests, set up test infrastructure, MockWebServer, Espresso, Compose test.

### `android-mcp-orchestrator`

Manages the multi-container emulator stack lifecycle: build, start, run operations, shut down. 3 emulators (phone + tablets) + MCP server + optional mock backend.

**Triggers:** Test on emulators, take screenshots, start emulator stack, spin up containers, test on phone and tablet, bring up the MCP.

### `mock-server-from-app-sources`

Analyzes app source code (Retrofit interfaces, DTOs, auth flow) to scaffold a minimal mock server container for testing.

**Triggers:** Fake backend, stub the API, test server, Docker/Podman mock, offline testing, mock the REST API.

### `android-release-signing`

Shared signing foundation for any distribution channel: upload-keystore creation, `keystore.properties` wiring, `signingConfigs.release` in Gradle, and a `release.yml` GitHub Actions workflow that decodes a base64 keystore from secrets and uploads APK + AAB to GitHub Releases.

**Triggers:** Sign my APK, create upload keystore, set up release signing, build a signed AAB, release workflow won't sign, keystore.properties missing, Gradle uses debug key for release.

### `android-fdroid-publish`

End-to-end F-Droid submission flow: scaffolding `fastlane/metadata/android/en-US/`, drafting the `fdroiddata` build recipe YAML, computing `AllowedAPKSigningKeys`, and choosing between RFP issue vs direct merge request. Reference files include a drop-in YAML template and the full fastlane directory layout with per-file constraints.

**Triggers:** Publish to F-Droid, submit to fdroid, create fdroid metadata, fastlane folder, RFP issue, fdroiddata YAML, AllowedAPKSigningKeys, F-Droid build recipe.

### `android-play-publish`

End-to-end Google Play submission flow: AAB build, Play Console setup, store listing copy and assets, App content forms (Privacy policy, Data safety, App access, Content rating), release tracks, the 12-tester / 14-day closed-test rule for new personal accounts, and `fastlane supply` automation. Reference files include a per-release preflight checklist and a Data safety decision table.

**Triggers:** Publish to Google Play, submit to play store, Play Console setup, build AAB for play, Data safety form, app access demo credentials, Play App Signing, closed test 12 testers, fastlane supply.

## Commands

### `/android-screenshots`

Captures Play Store screenshots across all emulator form factors (phone 6", tablet 7", tablet 10" landscape).

```
/android-screenshots [login|capture|full] [--tabs "Tab1,Tab2,..."]
```

The F-Droid and Google Play prep flows are now skills (invoke `/android-dev:android-fdroid-publish` or `/android-dev:android-play-publish`, or let them model-trigger). Each carries a **Quick audit (punchlist)** section — the former `check`-mode checklist — plus the full signing → metadata/AAB → recipe/listing walkthrough.

## Agents

### `ui-android`

The Android surface of the per-platform UI expert family (its five siblings — `ui-web`, `ui-gnome`, `ui-macos`, `ui-windows`, `ui-garmin` — live in the `ui-design` plugin). It lives here rather than there because Android UI work is inseparable from the Gradle and Compose tooling this plugin owns.

**What it does.** Designs, reviews, and facelifts Android UI against Material 3 and Jetpack Compose — dynamic color, adaptive layouts and `WindowSizeClass`, predictive back, edge-to-edge, and TalkBack accessibility.

**How it fires.** Automatic delegation on "design Android UI", "Material 3 facelift", "Compose screen", "TalkBack audit"; direct request; or from plan execution, where `planning`'s `stack-routing.md` maps *Android UI — Compose / Material 3* to this agent with `android-ui-layout-patterns` and `android-ui-design-figma` loaded first.

**Six protocols**, announced before it acts and composable — the same shape as its `ui-design` siblings: Surface detection → Design review → Facelift → Greenfield → Accessibility audit → Coach. Protocol 1 runs first on unfamiliar code, because a review that assumes the wrong Compose version or theming setup produces confident, wrong advice.

**Model:** `sonnet`. **Tools:** `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`, `WebFetch`, `TaskCreate`, `TaskUpdate` — it edits source, so scope your request.

## Infrastructure

The `infrastructure/` directory contains the full emulator stack:

- `compose.yaml` — Podman/Docker compose with 3 emulators + MCP server + optional mock backend
- `emulator/` — Containerfile and entrypoint for Android emulator containers (phone 6", tablet 7", tablet 10")
- `mcp-server/` — MCP server that connects to emulators via adb
- `mock-synapse/` — Optional mock Matrix Synapse backend for testing login-gated apps

## MCP stack (ephemeral)

The stack is **off by default**. There is no `.mcp.json` — the in-container HTTP server is a private loopback JSON-RPC backend, not a Claude-Code-registered MCP. The `android-mcp-orchestrator` skill owns the lifecycle: it brings the stack up for one task and tears it down on exit.

Canonical entrypoint:

```bash
APK_DIR=/abs/path/to/project/app/build/outputs/apk/debug \
SCREENSHOT_DIR=/abs/path/to/project/play-screenshots \
skills/android-mcp-orchestrator/scripts/run.sh [--mock] <<'EOF'
tools/call start-android-tablet-emulators {}
tools/call install-app-on-emulators {"apkPath":"/apks/app-debug.apk"}
tools/call launch-app {"packageName":"com.example.app"}
tools/call capture-emulator-screenshots {"loginFlow":"none","navItemCount":5}
EOF
```

`run.sh` generates `infrastructure/.env` with a random `MCP_AUTH_TOKEN` on first run, builds + starts the compose stack, dispatches each line through `mcp-call.sh` (curl + bearer), and runs `down.sh` in an EXIT trap so the host returns to its idle state.

For interactive iteration use the paired form (`up.sh` / `mcp-call.sh` / `down.sh`) and wrap it in your own `trap`. See the orchestrator skill for the full flow.

## Where artifacts land

| Artifact | Path | Written by |
|---|---|---|
| Debug/release APKs | your project's `app/build/outputs/apk/…` | `android-gradle-build`, `android-stage-verify` |
| Play Store screenshots | `${SCREENSHOT_DIR:-./play-screenshots}` on the host (see [Pointing the stack at your project](#pointing-the-stack-at-your-project)) | `/android-screenshots` |
| Emulator stack env (random `MCP_AUTH_TOKEN`) | `infrastructure/.env` — generated on first run, **not** committed | `android-mcp-orchestrator` `run.sh` |
| Signing config | per the `android-release-signing` skill; **keystores and passwords never enter the repo** | you, guided by the skill |
| Mock server sources | generated into your project per the skill's declared output path | `mock-server-from-app-sources` |

## Worked example

```text
/plugin install android-dev@coder-plugins

"add a settings screen with a dark-mode toggle"
```

`android-gradle-build` fires for the module/dependency wiring; `ui-android` handles the Compose screen against Material 3, then `android-ui-layout-patterns` informs the adaptive layout.

```text
"verify this stage on device"
```

`android-stage-verify` builds the debug APK, checks `adb devices`, installs and smoke-launches, then runs `connectedDebugAndroidTest`. **With no device attached it degrades to build-only and reports the skip** — it does not claim a pass it didn't earn. This is the single most common surprise mid-execution, so check `adb devices` before you rely on a green stage gate.

```text
"capture Play Store screenshots"
```

`/android-screenshots` brings the ephemeral emulator stack up across form factors, captures, and tears it down on exit.

## Related plugins

- **`planning`** — `executing-plans` invokes `android-stage-verify` automatically at every Android stage gate, scoped by gate tier (touched-module instrumented tests at intermediate gates, the full device suite once at close-out). `dispatching-parallel-agents` routes Android work here via `stack-routing.md`.
- **`ui-design`** — the five non-Android surfaces of the same UI-expert family.
- **`testing`** — `testing-expert` handles Compose/Espresso test authoring and triage, loading `kotlin-compose-testing-patterns` first.
- **`infra-build`** / **`release-promo`** — packaging registration and release announcements once you're shipping.

## License

MIT
