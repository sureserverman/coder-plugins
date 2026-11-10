---
name: android-gradle-build
description: Use when creating or modifying Android build scripts, wiring Gradle modules, or running Android unit/instrumented tests — before writing any build config or test command. Trigger on "gradle build failing", "add a module", "wire up instrumented tests", "update my AGP version".
---

# Android Gradle Build

## House rules

- Versions live in `gradle/libs.versions.toml`; modules reference `libs.*` aliases only.
- Annotation processing uses KSP, never kapt.
- Run tests per module (`./gradlew :module:testDebugUnitTest`, `:module:connectedDebugAndroidTest`); never `--quiet`. With an `androidTest/` suite, start an emulator rather than skipping it.
- At a stage gate, the on-device counterpart is the **android-stage-verify** skill.

## Screenshot-test gate

When a gate names `validateDebugScreenshotTest` (or another Compose screenshot task):

- Wire the REAL harness: the `com.android.compose.screenshot` plugin, `android.experimental.enableScreenshotTest=true`, and a `screenshotTest` source set with `@Preview`/`@PreviewTest` composables.
- NEVER register a no-op task named like the gate. A `validateDebugScreenshotTest` that only logs "skipped" is a faked gate (see honest-gates).
- Generate baselines with `./gradlew :module:updateDebugScreenshotTest`, inspect the PNGs (never approve a diff just to go green), then run `:module:validateDebugScreenshotTest`.
- If the plugin cannot be added for the target AGP, report the gate BLOCKED and escalate. Do not stub it.

## Security Hard Gates

**Block all progress unconditionally. No exceptions.**

| Gate | Violation | Fix |
|------|-----------|-----|
| No password persistence | `password`/`pass`/`pwd` in SharedPreferences, Room, or DataStore | Store access tokens only; discard passwords after login. "Only for testing" and "useful for future features" are not exemptions — use fakes/mocks in tests instead. |
| Keystore-backed tokens | Tokens in plain SharedPreferences or file | `EncryptedSharedPreferences` + `MasterKey` / Android Keystore |
| No cleartext traffic | `usesCleartextTraffic="true"` or `http://` in production | `false` + `https://` only; MockWebServer exempt. |
| No secrets in source | Keys/tokens in `.kt`, `.xml`, `.gradle.kts`, `.toml` | BuildConfig from gitignored `local.properties`, or Keystore at runtime |
| Destructive confirmation | Destructive use-case without user confirmation | `confirmed: Boolean` param or sealed UI state required. |

Before any commit also refuse: `.gradle/`, `build/` or `*.keystore` staged; `http://` base URLs in production Retrofit config.
