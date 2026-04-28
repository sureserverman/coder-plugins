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

Includes reference files for M3 best practices, adaptive layouts, and a component lookup table.

**Triggers:** Redesign a screen, change color scheme, update theme, add bottom nav, implement Figma design, fix spacing, add dark theme, Material 3 components.

### `android-mcp-orchestrator`

Manages the multi-container emulator stack lifecycle: build, start, run operations, shut down. 3 emulators (phone + tablets) + MCP server + optional mock backend.

**Triggers:** Test on emulators, take screenshots, start emulator stack, spin up containers, test on phone and tablet, bring up the MCP.

### `mock-server-from-app-sources`

Analyzes app source code (Retrofit interfaces, DTOs, auth flow) to scaffold a minimal mock server container for testing.

**Triggers:** Fake backend, stub the API, test server, Docker/Podman mock, offline testing, mock the REST API.

## Commands

### `/android-screenshots`

Captures Play Store screenshots across all emulator form factors (phone 6", tablet 7", tablet 10" landscape).

```
/android-screenshots [login|capture|full] [--tabs "Tab1,Tab2,..."]
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

Connects to the android-emulator-mcp HTTP server at `http://localhost:8000/mcp` when the compose stack is running.

## License

MIT
