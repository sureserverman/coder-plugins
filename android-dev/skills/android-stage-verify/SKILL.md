---
name: android-stage-verify
description: Use after each stage of plan execution (or any milestone) to prove an Android app still builds, installs, and runs on real hardware. Trigger on "verify this stage on device", "build and install on my phone", "run the on-device gate", "did this stage break the app".
---

# Android Stage Verify

The per-stage on-device gate. `executing-plans` (planning plugin) invokes this skill at every Android stage gate, after the stage's own gate checks pass, as the platform verify hook. It also runs on demand after any milestone.

## The gate (stop at the first failure)

```
Step 1 — ./gradlew :app:assembleDebug
  FAILS → STAGE GATE FAILS.

Step 2 — Device check
  adb devices | grep -w device   (excludes "offline" / "unauthorized")
  ├── NONE → Build-only gate. Report: "APK built; no adb device attached —
  │          install/smoke/instrumented steps SKIPPED." Stage may proceed.
  │          Never report the stage as device-verified.
  └── ≥1 device → run Steps 3–5 on each, or only on $ANDROID_SERIAL if set.

Step 3 — adb install -r <app-debug.apk>
  FAILS → STAGE GATE FAILS.

Step 4 — Smoke launch
  adb shell am start -W -n <applicationId>/<launcherActivity>
  adb shell pidof <applicationId>             (empty → crashed on launch)
  adb logcat -d -t 200 | grep -E "FATAL EXCEPTION|ANR in <applicationId>"
  No live pid, or a FATAL EXCEPTION for this package → STAGE GATE FAILS;
  put the logcat stack trace in the failure report.

Step 5 — Instrumented tests, only if src/androidTest/ exists
  ./gradlew :app:connectedDebugAndroidTest
  FAILS → STAGE GATE FAILS (report under app/build/reports/androidTests/).
```

Derive the APK path, `applicationId` (with any `applicationIdSuffix`) and launcher Activity from the build files; `adb shell cmd package resolve-activity --brief <applicationId>` prints the launcher after install.

If `adb uninstall` is needed to clear an install failure, say that it wipes app data.

The managed multi-emulator stack with screenshot capture is a different job: use **android-mcp-orchestrator**.
