---
description: Capture Play Store screenshots across all emulators (phone + tablets)
argument-hint: [login|capture|full] [--tabs "Accounts,Rooms,Info,Config"]
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
  "mcp__plugin_android-dev_android-emulator-mcp__start-android-tablet-emulators",
  "mcp__plugin_android-dev_android-emulator-mcp__launch-app",
  "mcp__plugin_android-dev_android-emulator-mcp__matrix-synapse-login",
  "mcp__plugin_android-dev_android-emulator-mcp__install-app-on-emulators",
  "mcp__plugin_android-dev_android-emulator-mcp__capture-emulator-screenshots"
]
---

# Android Screenshots

Capture screenshots of an Android app across all emulator form factors (phone 6", tablet 7", tablet 10" landscape) using the Android MCP emulator stack.

## Arguments

The user invoked this command with: $ARGUMENTS

## Modes

- **full** (default): Clear app data, run login flow, then capture all tabs
- **login**: Only run the login flow (add server + sign in) on all emulators
- **capture**: Only capture screenshots of current screen state (no login)

## Instructions

### 1. Ensure MCP stack is running

Check if the MCP server is up:
```bash
curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/mcp
```
- If result is `405`, the stack is running.
- If not, start it from the bundled infrastructure directory (resolve plugin path first):
```bash
# INFRA_DIR: ~/.claude/plugins/local/android-dev/infrastructure
# or:        ~/.claude/plugins/android-dev/infrastructure
cd "$INFRA_DIR"
APP_APK_DIR=/path/to/app/build/outputs/apk/debug APP_SCREENSHOTS_DIR=/path/to/play-screenshots podman compose build
APP_APK_DIR=/path/to/app/build/outputs/apk/debug APP_SCREENSHOTS_DIR=/path/to/play-screenshots podman compose --profile mock up -d
```
Wait for emulators to boot (~1-2 minutes). Retry the curl until you get `405`.

### 2. Login flow (modes: full, login)

Prefer the native MCP tool — the `android-dev` plugin's `.mcp.json` registers the server, so call it directly:

- `mcp__plugin_android-dev_android-emulator-mcp__matrix-synapse-login` (no arguments needed if `MOCK_SERVER_URL` / `MOCK_USERNAME` / `MOCK_PASSWORD` are set in the compose env)

Fallback (diagnostic only — use when the plugin's MCP wiring is unavailable):
```bash
curl -s http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"matrix-synapse-login","arguments":{}}}'
```

If the user passes `--clear` or mode is `full`, first clear app data:
```bash
podman exec android-emu-mcp_android-mcp_1 sh -c '
for H in 10.89.0.10 10.89.0.11 10.89.0.12; do
  adb -H $H -P 5037 shell pm clear com.matrix.synapse.manager.debug
done'
```

### 3. Capture tab screenshots (modes: full, capture)

Default tabs: Accounts, Rooms, Info, Config (override with `--tabs`).

Prefer the native MCP tool — `mcp__plugin_android-dev_android-emulator-mcp__capture-emulator-screenshots` with `loginFlow: "matrix-synapse"`, `navItemCount: 5`, and `tabLabels` matching `--tabs`. Use the manual adb sequence below only when the MCP wiring is unavailable or you need a custom tap sequence the tool doesn't expose.

For each emulator, for each tab:
1. Dump UI via `uiautomator dump`
2. Find the tab element by its text label in the XML
3. Tap the center of the element's bounds
4. Wait 2 seconds for content to load
5. Capture screenshot via `adb exec-out screencap -p`

Use this pattern inside the MCP container:
```bash
podman exec android-emu-mcp_android-mcp_1 sh -c '
TABS="Accounts Rooms Info Config"
for H in 10.89.0.10 10.89.0.11 10.89.0.12; do
  NAME=$(adb -H $H -P 5037 shell getprop ro.boot.qemu.avd_name | tr -d "\r\n")
  adb -H $H -P 5037 shell am start -n "com.matrix.synapse.manager.debug/com.matrix.synapse.manager.MainActivity"
  sleep 2
  for TAB in $TABS; do
    adb -H $H -P 5037 shell uiautomator dump /sdcard/ui.xml
    XML=$(adb -H $H -P 5037 shell cat /sdcard/ui.xml)
    COORDS=$(echo "$XML" | grep -oP "<node[^>]*text=\"${TAB}\"[^>]*bounds=\"\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]\"" | head -1 | sed -E "s/.*bounds=\"\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]\".*/\1 \2 \3 \4/")
    read X1 Y1 X2 Y2 <<< "$COORDS"
    CX=$(( (X1 + X2) / 2 ))
    CY=$(( (Y1 + Y2) / 2 ))
    adb -H $H -P 5037 shell input tap "$CX" "$CY"
    sleep 2
    LABEL=$(echo "$TAB" | tr "[:upper:]" "[:lower:]")
    adb -H $H -P 5037 exec-out screencap -p > /screenshots/${NAME}_${LABEL}.png
  done
done'
```

### 4. Report results

Show the user:
- How many screenshots were captured
- The file paths in `play-screenshots/` on the host (the container's `/screenshots/` directory is volume-mounted to `play-screenshots/`)
- Read and display one screenshot from each device as a sample

### Emulator details

| Device | IP | Resolution | Orientation |
|--------|----|-----------|-------------|
| phone6in | 10.89.0.10 | 1440x2560 | Portrait |
| tablet7in | 10.89.0.11 | 800x1280 | Portrait |
| tablet10in | 10.89.0.12 | 2560x1800 | Landscape |
