---
name: android-stage-verify
description: Use after each stage of plan execution (or any milestone) to prove an Android app still builds, installs, and runs on real hardware. Trigger on "verify this stage on device", "build and install on my phone", "run the on-device gate", "did this stage break the app".
---

# Android Stage Verify

The per-stage on-device gate: after a unit of work lands, prove the app **still
assembles, installs, launches without crashing, and passes its instrumented
tests** on whatever device is attached. This is the physical-reality check that
unit tests alone can't give — a green `testDebugUnitTest` says nothing about
whether the APK installs or the first Activity crashes on a real Android runtime.

**Announce at start:** "Using the android-stage-verify skill to gate this stage on device."

## When this runs

- At every **stage gate** during `executing-plans` for an Android project, after
  the stage's own gate checks pass (this skill is the platform verify hook).
- On demand, after any milestone the user wants proven on hardware.

It is **device-conditional**: with no adb device attached it degrades to a build
gate and reports the skip — it never silently passes and never blocks the stage
purely for lack of a device.

## The gate (run in order — stop at the first failure)

```
Step 1 — Build the debug APK
  ./gradlew :app:assembleDebug
  ├── FAILS → STAGE GATE FAILS. Read the error, fix, rebuild. Do not proceed.
  └── PASSES ↓

Step 2 — Detect an attached device
  adb devices | grep -w device   (excludes "offline" / "unauthorized" lines)
  ├── NONE → Build-only gate. Report: "APK built; no adb device attached —
  │          install/smoke/instrumented steps SKIPPED." Stage may proceed.
  │          Do NOT report the stage as fully device-verified.
  └── ≥1 device ↓   (if >1, install/test on each, or the one named by $ANDROID_SERIAL)

Step 3 — Install
  adb install -r <path-to-app-debug.apk>      (-r = reinstall, keep data)
  ├── FAILS → STAGE GATE FAILS. Common causes below. Fix, reinstall.
  └── PASSES ↓

Step 4 — Smoke launch (does the launcher Activity survive start-up?)
  adb shell am start -W -n <applicationId>/<launcherActivity>
  then confirm the process is alive and no crash was logged:
  adb shell pidof <applicationId>             (empty → crashed on launch)
  adb logcat -d -t 200 | grep -E "FATAL EXCEPTION|ANR in <applicationId>"
  ├── No live pid, OR a FATAL EXCEPTION for this package → STAGE GATE FAILS.
  │   Capture the stack trace from logcat into the failure report.
  └── Process alive, no fatal → smoke passed ↓

Step 5 — Instrumented tests (only if src/androidTest/ exists)
  androidTest sources present?
  ├── NO → No instrumented suite; smoke launch is the on-device signal. Gate passes.
  └── YES → ./gradlew :app:connectedDebugAndroidTest
            ├── FAILS → STAGE GATE FAILS. Read logcat + the test report under
            │           app/build/reports/androidTests/. Fix. Do not advance.
            └── PASSES → On-device gate complete.
```

## Resolving the APK path and launch target

Don't hardcode. Derive them:

- **APK:** default `app/build/outputs/apk/debug/app-debug.apk`. If the module
  isn't `:app` or the variant differs, find it:
  `find . -path '*/outputs/apk/debug/*-debug.apk' -newer /tmp 2>/dev/null` — or
  read the variant output. Multiple flavors → install the one the plan targets.
- **applicationId / launcher Activity:** read `applicationId` from
  `app/build.gradle.kts` (account for `applicationIdSuffix`, e.g. `.debug`) and
  the `<activity android:name>` carrying `<category android:name=
  "android.intent.category.LAUNCHER">` in the merged manifest. When unsure of
  the launcher, `adb shell cmd package resolve-activity --brief <applicationId>`
  prints it after install.

## Multiple devices / emulators

- `adb devices` lists several → loop the install + smoke (+ instrumented) over
  each, or honor `$ANDROID_SERIAL` / `adb -s <serial>` if the user pinned one.
- Need the bundled multi-emulator stack (phone6in/tablet7in/tablet10in) with
  screenshot capture instead of a locally-attached device? That is a different
  job — use **android-mcp-orchestrator**. This skill targets `adb`-reachable
  devices (physical or already-running emulators) and does not manage container
  lifecycle.

## Common install/launch failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | Signed with a different key than the installed build | `adb uninstall <applicationId>` then install fresh (warn: wipes app data) |
| `INSTALL_FAILED_VERSION_DOWNGRADE` | versionCode lower than installed | Bump versionCode, or uninstall first |
| `INSTALL_FAILED_INSUFFICIENT_STORAGE` | Device full | Free space / pick another device |
| `device unauthorized` | USB debugging prompt not accepted | Accept the RSA prompt on the device; re-run `adb devices` |
| `device offline` | adb/device handshake stale | `adb kill-server && adb start-server`, replug |
| Smoke launch: empty `pidof` | Crash in `onCreate` / DI graph / first frame | Read the `FATAL EXCEPTION` trace in `adb logcat -d` |

## Never

- **Never report a stage as device-verified when no device was attached.** A
  build-only run is a real, useful result — but say so explicitly. Silent
  "passed" hides that the install/launch path was never exercised.
- **Never `adb uninstall` to clear a failure without flagging the data wipe** —
  it deletes app data and can mask a real migration bug.
- **Never substitute the smoke launch for instrumented tests** when an
  `androidTest/` suite exists — a clean launch and a passing suite catch
  different failures.
- **Never use `--quiet`** — the Gradle/logcat output is how you find the first
  failure.

## Integration

- **executing-plans** (planning plugin) — invokes this skill at each stage gate
  as the platform verify hook for Android projects, after the stage's own gate
  checks pass.
- **android-gradle-build** — owns the build-config and unit/instrumented test
  *authoring* gates; this skill runs the resulting build on a device. Fix build
  or test failures through that skill's decision trees.
- **android-mcp-orchestrator** — the container-emulator alternative when you
  need the managed multi-device + screenshot stack rather than an attached device.
