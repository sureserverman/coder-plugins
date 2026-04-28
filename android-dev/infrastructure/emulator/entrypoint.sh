#!/usr/bin/env bash
set -euo pipefail

: "${AVD_NAME:?AVD_NAME not set}"
: "${AVD_DEVICE:?AVD_DEVICE not set}"

SDK_ROOT="${ANDROID_SDK_ROOT:-/opt/android-sdk}"
AVD_HOME="${ANDROID_AVD_HOME:-/avd}"
SYSTEM_IMAGE="system-images;android-35;google_apis;x86_64"

export ANDROID_SDK_ROOT="$SDK_ROOT"
export ANDROID_HOME="$SDK_ROOT"
export ANDROID_AVD_HOME="$AVD_HOME"
export PATH="${SDK_ROOT}/cmdline-tools/latest/bin:${SDK_ROOT}/platform-tools:${SDK_ROOT}/emulator:${PATH}"

if [ ! -d "${AVD_HOME}/${AVD_NAME}.avd" ]; then
  echo "[entrypoint] Creating AVD: ${AVD_NAME} (device: ${AVD_DEVICE})"
  echo "no" | avdmanager create avd \
    --name "$AVD_NAME" \
    --package "$SYSTEM_IMAGE" \
    --device "$AVD_DEVICE"

  CONFIG="${AVD_HOME}/${AVD_NAME}.avd/config.ini"
  if [ -f "$CONFIG" ]; then
    cat >> "$CONFIG" <<'OPTS'
PlayStore.enabled=false
hw.audioInput=no
hw.audioOutput=no
hw.accelerometer=no
hw.gyroscope=no
hw.dPad=no
hw.keyboard=no
hw.sensors.proximity=no
hw.sensors.orientation=no
hw.sensors.magnetic_field=no
hw.sensors.temperature=no
hw.sensors.light=no
hw.sensors.pressure=no
hw.sensors.humidity=no
OPTS
    echo "[entrypoint] Patched ${CONFIG} for testing."
  fi
else
  echo "[entrypoint] AVD ${AVD_NAME} already exists — skipping creation."
fi

# Start adb server on all interfaces so MCP can connect via network
echo "[entrypoint] Starting adb server on 0.0.0.0:5037"
adb -a -P 5037 nodaemon server &

echo "[entrypoint] Starting emulator: ${AVD_NAME}"
exec emulator -avd "$AVD_NAME" \
  -no-window \
  -no-audio \
  -gpu swiftshader_indirect \
  -netdelay none \
  -netspeed full \
  -no-snapshot
