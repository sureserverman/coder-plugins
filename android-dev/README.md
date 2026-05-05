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

The emulator infrastructure (compose stack, Containerfiles, MCP server, mock backend) is bundled in `infrastructure/` — no external repo needed.

## Skills

### `android-gradle-build`

Four-phase build management with decision trees and security hard gates. Covers module wiring, Hilt/Room/Retrofit/Compose setup, test execution, and commit validation.

**Triggers:** Add a module, fix build error, set up Hilt/Compose, add a dependency, run tests, edit version catalog, wire Retrofit/Room.

### `android-ui-design-figma`

End-to-end UI workflow: app analysis, design spec (with optional Figma), feedback loop, then apply to code. Standard-first approach using Material 3 / Compose Material / AndroidX.

Includes reference files for M3 best practices, adaptive layouts, a component lookup table, and the adaptive launcher icon spec (foreground/background/monochrome layers, themed icons, Image Asset Studio scaffold + verification recipe — required for every release).

**Triggers:** Redesign a screen, change color scheme, update theme, add bottom nav, implement Figma design, fix spacing, add dark theme, Material 3 components, adaptive launcher icon, themed icon, monochrome layer.

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

### `/android-prepare-fdroid`

Walks through the F-Droid prep checklist: signing, fastlane scaffold, and `docs/f-droid/<applicationId>.yml` build recipe. The user submits to `gitlab.com/fdroid/fdroiddata` themselves — the command produces and validates the artefacts.

```
/android-prepare-fdroid [check|init|metadata|yaml] [applicationId]
```

### `/android-prepare-play`

Walks through the Google Play prep checklist: signing, AAB build + verification, Play-specific store listing assets, and a draft `docs/play-app-content.md` for the App content forms. The user uploads to Play Console themselves.

```
/android-prepare-play [check|init|aab|listing] [applicationId]
```

## Infrastructure

The `infrastructure/` directory contains the full emulator stack:

- `compose.yaml` — Podman/Docker compose with 3 emulators + MCP server + optional mock backend
- `emulator/` — Containerfile and entrypoint for Android emulator containers (phone 6", tablet 7", tablet 10")
- `mcp-server/` — MCP server that connects to emulators via adb
- `mock-synapse/` — Optional mock Matrix Synapse backend for testing login-gated apps

Start the stack:
```bash
cd infrastructure/
APP_APK_DIR=/path/to/app/build/outputs/apk/debug podman compose build
APP_APK_DIR=/path/to/app/build/outputs/apk/debug podman compose up -d
```

## MCP Server

The plugin ships `.mcp.json` at its root, which auto-registers the `android-emulator-mcp` HTTP server (`http://localhost:8000/mcp`) with Claude Code on plugin install. Run `/mcp` to confirm it appears once the compose stack is up.

The five tools become available as:

- `mcp__plugin_android-dev_android-emulator-mcp__start-android-tablet-emulators`
- `mcp__plugin_android-dev_android-emulator-mcp__launch-app`
- `mcp__plugin_android-dev_android-emulator-mcp__install-app-on-emulators`
- `mcp__plugin_android-dev_android-emulator-mcp__capture-emulator-screenshots`
- `mcp__plugin_android-dev_android-emulator-mcp__matrix-synapse-login`

### Environment variables

- `ANDROID_MCP_AUTH_TOKEN` *(optional)* — bearer token expanded into `.mcp.json`'s `Authorization` header. Required only when the compose service sets `MCP_AUTH_TOKEN` (i.e. you've moved the listener off loopback). Leave unset for the default loopback-only setup.

## License

MIT
