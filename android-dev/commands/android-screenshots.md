---
description: Capture Play Store screenshots across all emulators (phone + tablets)
argument-hint: '[login|capture|full] [--tabs "Accounts,Rooms,Info,Config"]'
allowed-tools: [
  "Read",
  "Write",
  "Glob",
  "Grep",
  "Bash(podman:*)",
  "Bash(podman compose:*)",
  "Bash(curl:*)",
  "Bash(date:*)",
  "Bash(ls:*)",
  "Bash(cd:*)",
  "Bash(./skills/android-mcp-orchestrator/scripts/run.sh:*)",
  "Bash(./skills/android-mcp-orchestrator/scripts/up.sh:*)",
  "Bash(./skills/android-mcp-orchestrator/scripts/down.sh:*)",
  "Bash(./skills/android-mcp-orchestrator/scripts/mcp-call.sh:*)"
]
---

# Android Screenshots

Arguments: $ARGUMENTS

Hand the work to the **android-mcp-orchestrator** skill and follow its lifecycle rules: run everything through `${CLAUDE_PLUGIN_ROOT}/skills/android-mcp-orchestrator/scripts/run.sh`, set absolute `APK_DIR` and `SCREENSHOT_DIR` from the project under test, and confirm no `infrastructure_*` containers remain afterwards.

Modes:

- **full** (default): install, log in, capture every tab.
- **login**: install and log in only.
- **capture**: capture the current screen state, no login.

`--tabs "A,B,C"` replaces the `tabLabels` array.

Example values from one app (Matrix Synapse Manager, which logs in against the `--mock` mock-synapse backend). Take the paths, login flow and tab labels from the app you are capturing:

```bash
APK_DIR=/abs/path/to/project/app/build/outputs/apk/debug \
SCREENSHOT_DIR=/abs/path/to/project/play-screenshots \
${CLAUDE_PLUGIN_ROOT}/skills/android-mcp-orchestrator/scripts/run.sh --mock <<'EOF'
tools/call start-android-tablet-emulators {}
tools/call install-app-on-emulators {"apkPath":"/apks/app-debug.apk"}
tools/call matrix-synapse-login {}
tools/call capture-emulator-screenshots {"loginFlow":"matrix-synapse","navItemCount":5,"tabLabels":["Accounts","Rooms","Info","Config"]}
EOF
```

Report the screenshot count, the resolved `$SCREENSHOT_DIR` paths, and show one screenshot per device (phone6in, tablet7in, tablet10in).
