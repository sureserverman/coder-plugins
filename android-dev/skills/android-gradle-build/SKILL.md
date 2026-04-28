---
name: android-gradle-build
description: Use when creating or modifying Android build scripts, wiring Gradle modules, running Android unit or instrumented tests, or touching security-sensitive storage — before writing any build configuration, implementation file, or test command. Trigger on "gradle build failing", "add a module", "wire up instrumented tests", "my androidTest won't run", "keystore for encrypted prefs", "update my AGP version".
---

# Android Gradle Build

## Overview

Four build phases, each with a decision tree. Complete each exit gate before the next. Security hard gates block unconditionally. **Violating the letter of these rules is violating the spirit.**

## Phase 1: Bootstrap

Enter when modifying any Gradle build file or `libs.versions.toml`.

```
Does settings.gradle.kts exist and declare ALL modules?
├── NO → Create it first. Do not write any module build file.
└── YES ↓
Does gradle/libs.versions.toml exist?
├── NO → Create it first. Never hardcode versions inline.
│        "We can move it to a catalog later" is not acceptable. Catalog first, always.
└── YES ↓
Does each module apply exactly ONE correct plugin?
  (app → com.android.application | lib → com.android.library | jvm → org.jetbrains.kotlin.jvm)
├── NO → Fix plugin declaration before adding any dependencies.
└── YES ↓
Are ALL dependency versions referenced via libs.* catalog aliases?
├── NO → Move hardcoded versions to libs.versions.toml first.
└── YES ↓
Run: ./gradlew help --dry-run
├── FAILS → Read the error. Fix config. Do not proceed to writing Kotlin code.
│           "The config looks correct visually" is not a substitute for running this.
└── PASSES → Bootstrap complete.
```

## Phase 2: Feature Module

Enter when adding a module with Hilt, Room, Retrofit, or Compose:

```
Hilt?
├── hilt-android + ksp(hilt-compiler) declared? (NEVER kapt)
│   └── NO → Fix first. Do not write @HiltViewModel or @Module.
└── app module applies com.google.dagger.hilt.android plugin?
    └── NO → Add it. Hilt silently fails without it.

Room?
├── room-runtime + ksp(room-compiler) declared?
│   └── NO → Fix first. Do not write @Entity, @Dao, or @Database.
└── ksp { room.schemaLocation } set?
    └── NO → Add it. Required for migrations.

Retrofit?
├── kotlinx-serialization-json + retrofit-kotlinx-serialization converter declared?
│   └── NO → Fix first. Do not write @GET/@POST interfaces.
├── INTERNET permission in AndroidManifest.xml?
│   └── NO → Add it.
└── No cleartext traffic (usesCleartextTraffic=false)?
    └── NO → SECURITY HARD GATE. Fix before anything else.

Compose?
├── buildFeatures { compose = true } + compose-bom declared?
│   └── NO → Fix first. Do not write @Composable.
└── org.jetbrains.kotlin.plugin.compose plugin applied?
    └── NO → Add it. Do NOT set composeOptions.kotlinCompilerExtensionVersion (K2 builds fail with it).

All checks pass?
└── ./gradlew :module:compileDebugKotlin
    ├── FAILS → Fix compiler errors first.
    └── PASSES → Feature Module phase complete.
```

**Never:**
- `kapt` — KSP is the supported replacement; KAPT is ~2× slower and slated for deprecation by JetBrains.
- Compose deps without BOM — versions drift across artifacts and produce incompatible runtime combinations.
- `implementation(project(":app"))` in library modules — inverts the dependency graph and causes circular build failures.

## Phase 3: Test Verification

Enter after writing implementation, before committing or advancing.

```
Unit tests exist (src/test/)?
└── Run: ./gradlew :module:testDebugUnitTest
    ├── FAILS → Fix implementation. Do NOT advance task. Do NOT commit.
    │           "I'll fix it after the review" is not acceptable. Fix it now.
    └── PASSES ↓
MockWebServer API tests exist?
└── Run: ./gradlew :module:testDebugUnitTest --tests *ApiTest*
    ├── FAILS → Fix response parsing. Do not proceed.
    └── PASSES ↓
Instrumented tests exist (src/androidTest/)?
├── Emulator/device connected? NO → Start one. Never skip instrumented tests.
└── Run: ./gradlew :module:connectedDebugAndroidTest
    ├── FAILS → Read logcat. Fix. Do NOT advance task.
    └── PASSES → Test Verification complete.
```

**Never:**
- Mark task complete with failing tests — downstream work assumes the gate held and debugging compounds.
- Use `--quiet` — Gradle output is how you find the first failing test; suppressing it hides the root cause.
- Substitute test types — unit tests and instrumented tests catch different classes of bug; one doesn't cover the other.

## Phase 4: Commit

```
Working tree clean except for intentional changes?
├── NO → Review untracked/modified files. Do not commit unrelated changes.
└── YES ↓
Any of these staged? (HARD STOP)
  · passwords/tokens/secrets in any source file
  · .gradle/ build/ *.keystore directories staged
  · http:// base URLs in production Retrofit config
├── YES → Remove. Even "just for testing" secrets reach git history and are effectively leaked — rewriting history is disruptive and often incomplete.
└── NO ↓
All unit tests pass for changed modules?
├── NO → Fix before committing.
└── YES → Commit: <type>: <what and why>
           Types: feat / fix / chore / docs / test / refactor
```

## Security Hard Gates

**Block all progress unconditionally. No exceptions.**

| Gate | Violation | Fix |
|------|-----------|-----|
| No password persistence | `password`/`pass`/`pwd` in SharedPreferences, Room, or DataStore | Store access tokens only; discard passwords after login. "Only for testing" and "useful for future features" are not exemptions — use fakes/mocks in tests instead. |
| Keystore-backed tokens | Tokens in plain SharedPreferences or file | `EncryptedSharedPreferences` + `MasterKey` / Android Keystore |
| No cleartext traffic | `usesCleartextTraffic="true"` or `http://` in production | `false` + `https://` only; MockWebServer exempt. |
| No secrets in source | Keys/tokens in `.kt`, `.xml`, `.gradle.kts`, `.toml` | BuildConfig from gitignored `local.properties`, or Keystore at runtime |
| Destructive confirmation | Destructive use-case without user confirmation | `confirmed: Boolean` param or sealed UI state required. |

## Common Mistakes

| Mistake | Correct |
|---------|---------|
| `apply plugin: "kotlin-android"` | `alias(libs.plugins.kotlin.android)` |
| `kapt(libs.hilt.compiler)` | `ksp(libs.hilt.compiler)` |
| `implementation("com.google.dagger:hilt:2.51")` | `implementation(libs.hilt.android)` |
| `./gradlew test` | `./gradlew :module:testDebugUnitTest` |
| App module depends on feature | Feature → core; app → feature. Never reverse. |
