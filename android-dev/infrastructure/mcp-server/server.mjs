import express from "express";
import * as z from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { createMcpExpressApp } from "@modelcontextprotocol/sdk/server/express.js";
import { mkdirSync, writeFileSync, existsSync } from "fs";
import { join, resolve as resolvePath } from "path";
import { execFile as _execFile } from "child_process";
import { promisify } from "util";
import { timingSafeEqual } from "crypto";

const execFile = promisify(_execFile);
const SCREENSHOTS_DIR = process.env.SCREENSHOTS_DIR || "/screenshots";
const APK_BASE_DIR = process.env.APK_BASE_DIR || "/apks";

const APP_PACKAGE = "com.matrix.synapse.manager.debug";
const APP_MAIN_ACTIVITY = "com.matrix.synapse.manager.MainActivity";

// Mock-server credentials are NEVER hard-coded — supplied at the tool-call boundary
// or via env vars. Kept undefined so the matrix-synapse-login tool errors if neither
// the caller nor the env supply them.
const MOCK_SERVER_URL = process.env.MOCK_SERVER_URL;
const MOCK_USERNAME = process.env.MOCK_USERNAME;
const MOCK_PASSWORD = process.env.MOCK_PASSWORD;

/**
 * Emulator container hostnames from compose environment.
 * Format: "host:port,host:port,..." where port is the adb server port (5037).
 */
const EMULATOR_HOSTS = (process.env.EMULATOR_HOSTS || "")
  .split(",")
  .map(h => h.trim())
  .filter(Boolean)
  .map(h => {
    const [host, port] = h.split(":");
    return { host, port: port || "5037" };
  });

// ── Input validation ─────────────────────────────────────────────────

// Java/Android package-name grammar plus a permissive activity grammar
// that allows the leading-dot relative form ('.MainActivity') and the
// fully-qualified form ('com.x.MainActivity').
const PACKAGE_NAME_RE = /^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+$/;
const ACTIVITY_RE = /^\.?[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*$/;

function validatePackageName(name) {
  if (typeof name !== "string" || !PACKAGE_NAME_RE.test(name)) {
    throw new Error(`invalid packageName: ${JSON.stringify(name)}`);
  }
  return name;
}

function validateActivity(activity) {
  if (typeof activity !== "string" || !ACTIVITY_RE.test(activity)) {
    throw new Error(`invalid activity: ${JSON.stringify(activity)}`);
  }
  return activity;
}

/**
 * Resolve apkPath inside APK_BASE_DIR. Reject anything that escapes the base
 * (path traversal) or contains shell metacharacters. Returns the resolved
 * absolute path, suitable for passing as an argv arg to execFile.
 */
function validateApkPath(apkPath) {
  if (typeof apkPath !== "string" || apkPath.length === 0) {
    throw new Error(`invalid apkPath: ${JSON.stringify(apkPath)}`);
  }
  const abs = resolvePath(APK_BASE_DIR, apkPath);
  if (abs !== APK_BASE_DIR && !abs.startsWith(APK_BASE_DIR + "/")) {
    throw new Error(`apkPath escapes APK_BASE_DIR: ${apkPath}`);
  }
  if (!/^[A-Za-z0-9._/-]+$/.test(abs)) {
    throw new Error(`apkPath contains disallowed characters: ${apkPath}`);
  }
  return abs;
}

// ── Helpers ──────────────────────────────────────────────────────────

/**
 * Spawn a binary with an argv array — never invokes a shell, so metacharacters
 * in args are inert. Returns { stdout, stderr } as strings unless opts.encoding
 * is overridden to "buffer".
 */
async function runArgs(file, args, opts = {}) {
  const { stdout, stderr } = await execFile(file, args, {
    ...opts,
    env: { ...process.env, ...opts.env },
  });
  return { stdout, stderr };
}

async function log(ctx, level, data) {
  return ctx?.mcpReq?.log?.(level, data) ?? Promise.resolve();
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/** Build adb argv prefix for a remote emulator's adb server. */
function adbArgs(emulator) {
  return ["-H", emulator.host, "-P", emulator.port];
}

async function adb(emulator, ...args) {
  return runArgs("adb", [...adbArgs(emulator), ...args]);
}

/** Check if a remote adb server has a device ready. */
async function adbCheckDevice(emulator) {
  try {
    const { stdout } = await adb(emulator, "devices");
    return (stdout || "").includes("emulator");
  } catch {
    return false;
  }
}

async function getAvdName(emulator) {
  try {
    const { stdout } = await adb(
      emulator, "shell", "getprop", "ro.boot.qemu.avd_name"
    );
    const name = (stdout || "").trim();
    if (name) return name;
  } catch { /* ignore */ }
  return emulator.host;
}

async function captureScreenshot(emulator, filePath) {
  try {
    const { stdout } = await execFile(
      "adb",
      [...adbArgs(emulator), "exec-out", "screencap", "-p"],
      { encoding: "buffer", maxBuffer: 20 * 1024 * 1024 }
    );
    if (Buffer.isBuffer(stdout) && stdout.length > 0) {
      writeFileSync(filePath, stdout);
      return true;
    }
  } catch { /* ignore */ }
  return false;
}

async function getDisplaySize(emulator) {
  try {
    const { stdout } = await adb(emulator, "shell", "wm", "size");
    const match = (stdout || "").match(/(\d+)\s*x\s*(\d+)/);
    if (match) {
      return { width: parseInt(match[1], 10), height: parseInt(match[2], 10) };
    }
  } catch { /* ignore */ }
  return null;
}

async function waitForBootComplete(emulator, timeoutMs = 120000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const { stdout } = await adb(
        emulator, "shell", "getprop", "sys.boot_completed"
      );
      if ((stdout || "").trim() === "1") return true;
    } catch { /* ignore */ }
    await sleep(3000);
  }
  return false;
}

async function tap(emulator, x, y) {
  try {
    await adb(emulator, "shell", "input", "tap",
      String(Math.round(x)), String(Math.round(y)));
    return true;
  } catch { return false; }
}

async function tapBottomNavTab(emulator, tabIndex, displaySize, navItemCount = 5) {
  const { width, height } = displaySize;
  const x = (width * (tabIndex + 0.5)) / navItemCount;
  const y = height - 80;
  return tap(emulator, x, y);
}

async function launchApp(emulator, packageName, activity = ".MainActivity") {
  const pkg = validatePackageName(packageName);
  const act = validateActivity(activity);
  const component = `${pkg}/${act}`;
  try {
    await adb(emulator, "shell", "am", "start", "-S", "-n", component);
    return true;
  } catch { return false; }
}

async function inputText(emulator, text) {
  if (typeof text !== "string") return false;
  // adb shell input text uses a single arg — execFile passes it without
  // shell interpretation, so spaces and metacharacters are inert.
  try {
    await adb(emulator, "shell", "input", "text", text);
    return true;
  } catch { return false; }
}

async function keyevent(emulator, code) {
  if (!Number.isInteger(code)) return false;
  try {
    await adb(emulator, "shell", "input", "keyevent", String(code));
    return true;
  } catch { return false; }
}

async function swipe(emulator, x1, y1, x2, y2, durationMs = 300) {
  try {
    await adb(emulator, "shell", "input", "swipe",
      String(Math.round(x1)), String(Math.round(y1)),
      String(Math.round(x2)), String(Math.round(y2)),
      String(Math.round(durationMs)));
    return true;
  } catch { return false; }
}

async function ensureLoggedIn(emulator, displaySize, opts = {}) {
  const serverUrl = opts.serverUrl ?? MOCK_SERVER_URL;
  const username = opts.username ?? MOCK_USERNAME;
  const password = opts.password ?? MOCK_PASSWORD;
  if (!serverUrl || !username || !password) {
    throw new Error(
      "ensureLoggedIn requires serverUrl/username/password — pass via tool args " +
      "or set MOCK_SERVER_URL / MOCK_USERNAME / MOCK_PASSWORD env vars."
    );
  }
  const { width, height } = displaySize;
  const KEYCODE_ESCAPE = 111;

  await launchApp(emulator, opts.packageName ?? APP_PACKAGE, APP_MAIN_ACTIVITY);
  await sleep(2000);
  await tap(emulator, width - 70, height - 120);
  await sleep(1200);
  await tap(emulator, width / 2, height * 0.28);
  await sleep(500);
  await inputText(emulator, serverUrl);
  await sleep(400);
  await keyevent(emulator, KEYCODE_ESCAPE);
  await sleep(400);
  await tap(emulator, width / 2, height * 0.38);
  await sleep(400);
  await swipe(emulator, width / 2, height * 0.75, width / 2, height * 0.35, 400);
  await sleep(400);
  await tap(emulator, width / 2, height * 0.82);
  await sleep(5000);
  await tap(emulator, width / 2, height * 0.36);
  await sleep(600);
  await inputText(emulator, username);
  await sleep(300);
  await keyevent(emulator, KEYCODE_ESCAPE);
  await sleep(400);
  await tap(emulator, width / 2, height * 0.48);
  await sleep(600);
  await inputText(emulator, password);
  await sleep(300);
  await keyevent(emulator, KEYCODE_ESCAPE);
  await sleep(400);
  await tap(emulator, width / 2, height * 0.62);
  await sleep(3000);
}

// ── MCP Server ───────────────────────────────────────────────────────

// Top-level guards. The express layer can swallow per-request errors, but a
// stray rejection in a fire-and-forget Promise (e.g., the parallel-emulator
// loops) would otherwise terminate the process with no diagnostic.
process.on("unhandledRejection", err => {
  console.error("Unhandled rejection:", err);
});
process.on("uncaughtException", err => {
  console.error("Uncaught exception:", err);
  process.exit(1);
});

function createServer() {
  const server = new McpServer(
    { name: "android-emulator-mcp", version: "0.3.0" },
    { capabilities: { tools: {}, logging: {} } }
  );

  server.registerTool(
    "start-android-tablet-emulators",
    {
      title: "Connect to emulator containers",
      description:
        "Connect to the 3 bundled emulator containers (phone6in, tablet7in, tablet10in) over the compose network via adb TCP and wait for boot completion in parallel. " +
        "Use this once after `podman compose up` to confirm all emulators are reachable before installing apps or capturing screenshots. " +
        "Returns a per-emulator readiness summary (avdName + host) plus a count of failures. Side-effect-free: never starts emulators (compose does that), only checks adb device state and `sys.boot_completed`.",
      inputSchema: z.object({
        bootTimeoutMs: z
          .number()
          .int()
          .min(30000)
          .max(300000)
          .default(120000)
          .describe("Max wait for each emulator to finish booting (ms)"),
      }).strict(),
      annotations: {
        readOnlyHint: true,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ bootTimeoutMs }, ctx) => {
      if (EMULATOR_HOSTS.length === 0) {
        return {
          content: [{
            type: "text",
            text: "No EMULATOR_HOSTS configured. Set the environment variable in compose.yaml.",
          }],
          isError: true,
        };
      }

      await log(ctx, "info", { step: "connecting", hosts: EMULATOR_HOSTS.map(e => `${e.host}:${e.port}`) });

      // Check each emulator's adb server and wait for boot in parallel
      const results = await Promise.all(
        EMULATOR_HOSTS.map(async emulator => {
          const hasDevice = await adbCheckDevice(emulator);
          if (!hasDevice) return { emulator, avdName: emulator.host, booted: false, error: "no device" };
          const booted = await waitForBootComplete(emulator, bootTimeoutMs);
          const avdName = booted ? await getAvdName(emulator) : emulator.host;
          return { emulator, avdName, booted };
        })
      );

      const ready = results.filter(r => r.booted);
      const failed = results.filter(r => !r.booted);

      if (failed.length > 0) {
        await log(ctx, "warn", {
          step: "failures",
          hosts: failed.map(f => `${f.emulator.host}: ${f.error || "boot timeout"}`),
        });
      }

      const total = EMULATOR_HOSTS.length;
      const readyList = ready.map(r => `${r.avdName} (${r.emulator.host})`).join(", ");
      const failList = failed.map(f => `${f.emulator.host}: ${f.error || "boot timeout"}`);

      return {
        content: [{
          type: "text",
          text: ready.length === total
            ? `All ${total} emulators ready: ${readyList}.`
            : `${ready.length}/${total} emulators ready: ${readyList || "none"}.\nFailed:\n${failList.join("\n")}`,
        }],
      };
    }
  );

  server.registerTool(
    "launch-app",
    {
      title: "Launch app on emulators",
      description:
        "Launch an Android app by package name on every connected emulator using `am start -S` (force-stop then start). " +
        "Use after `install-app-on-emulators` or any time you need to bring an app to the foreground (for example, before capturing screenshots). " +
        "Returns a one-line confirmation with the package name and emulator count. " +
        "Activity defaults to `.MainActivity` (relative to packageName); pass a fully-qualified activity for non-standard launchers.",
      inputSchema: z.object({
        packageName: z.string().regex(PACKAGE_NAME_RE).describe("Application ID / package name (e.g., com.example.app)"),
        activity: z.string().regex(ACTIVITY_RE).default(".MainActivity").describe("Launchable activity — leading-dot relative form or fully-qualified"),
      }).strict(),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ packageName, activity }, ctx) => {
      if (EMULATOR_HOSTS.length === 0) {
        return { content: [{ type: "text", text: "No emulators configured." }], isError: true };
      }
      await Promise.all(EMULATOR_HOSTS.map(async emulator => {
        await log(ctx, "info", { host: emulator.host, packageName, activity });
        await launchApp(emulator, packageName, activity);
      }));
      return {
        content: [{ type: "text", text: `Launched ${packageName} on ${EMULATOR_HOSTS.length} emulator(s).` }],
      };
    }
  );

  server.registerTool(
    "matrix-synapse-login",
    {
      title: "Matrix Synapse Manager: add server and login",
      description:
        "App-specific helper: launch Matrix Synapse Manager, drive the add-server form, and log in on every connected emulator. " +
        "Use only when testing the Matrix Synapse Manager app against the bundled mock-synapse container. " +
        "Returns a one-line confirmation with server URL, username, and emulator count (never the password). " +
        "The password is read exclusively from the MOCK_PASSWORD env var on the compose service — it is intentionally NOT a tool argument so the secret never traverses the MCP channel or appears in model context.",
      inputSchema: z.object({
        serverUrl: z.string().url().optional().describe("Matrix homeserver URL (e.g. http://10.0.2.2:8008). Falls back to MOCK_SERVER_URL env var."),
        username: z.string().min(1).optional().describe("Account username. Falls back to MOCK_USERNAME env var."),
      }).strict(),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ serverUrl, username }, ctx) => {
      if (EMULATOR_HOSTS.length === 0) {
        return { content: [{ type: "text", text: "No emulators configured." }], isError: true };
      }
      const effectiveUrl = serverUrl ?? MOCK_SERVER_URL;
      const effectiveUser = username ?? MOCK_USERNAME;
      const effectivePass = MOCK_PASSWORD;
      if (!effectiveUrl || !effectiveUser || !effectivePass) {
        return {
          content: [{
            type: "text",
            text: "matrix-synapse-login requires serverUrl + username (tool args or MOCK_SERVER_URL/MOCK_USERNAME env vars) and MOCK_PASSWORD env var on the compose service.",
          }],
          isError: true,
        };
      }
      let count = 0;
      for (const emulator of EMULATOR_HOSTS) {
        const displaySize = await getDisplaySize(emulator);
        if (!displaySize) continue;
        await log(ctx, "info", { host: emulator.host, step: "ensure-logged-in" });
        await ensureLoggedIn(emulator, displaySize, {
          serverUrl: effectiveUrl, username: effectiveUser, password: effectivePass
        });
        count++;
      }
      return {
        content: [{
          type: "text",
          text: `Logged in on ${count} emulator(s). Server: ${effectiveUrl}, user: ${effectiveUser}.`,
        }],
      };
    }
  );

  server.registerTool(
    "install-app-on-emulators",
    {
      title: "Install app on emulators",
      description:
        "Install (or reinstall via `adb install -r`) a debug APK on every connected emulator in parallel. " +
        "Use after building the app's debug APK and confirming the `/apks` volume is mounted. " +
        "Returns a per-emulator install report (avdName + host + ok/fail status); marks the call as `isError: true` if any single install fails. " +
        "The apkPath is resolved under APK_BASE_DIR (default `/apks`) and rejected if it escapes the base or contains shell metacharacters.",
      inputSchema: z.object({
        apkPath: z.string().default("/apks/app-debug.apk").describe("Path to APK inside the container — must resolve under APK_BASE_DIR (default /apks)"),
      }).strict(),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ apkPath }, ctx) => {
      let safePath;
      try {
        safePath = validateApkPath(apkPath);
      } catch (err) {
        return { content: [{ type: "text", text: err.message }], isError: true };
      }
      await log(ctx, "info", { step: "install-app", apkPath: safePath });

      if (!existsSync(safePath)) {
        return {
          content: [{
            type: "text",
            text: `APK not found at ${safePath}. Build the app first and ensure the debug output is mounted at ${APK_BASE_DIR}.`,
          }],
          isError: true,
        };
      }

      if (EMULATOR_HOSTS.length === 0) {
        return {
          content: [{ type: "text", text: "No emulators configured." }],
          isError: true,
        };
      }

      const results = await Promise.all(EMULATOR_HOSTS.map(async emulator => {
        const avdName = await getAvdName(emulator);
        try {
          await adb(emulator, "install", "-r", safePath);
          return { host: emulator.host, avdName, ok: true };
        } catch (err) {
          return { host: emulator.host, avdName, ok: false, error: err.message || String(err) };
        }
      }));

      const lines = results.map(
        r => `${r.avdName} (${r.host}): ${r.ok ? "installed" : "failed"}` + (r.error ? ` — ${r.error}` : "")
      );
      const allOk = results.every(r => r.ok);

      return {
        content: [{
          type: "text",
          text: (allOk ? "App installed on all emulators.\n\n" : "Install finished with failures.\n\n") + lines.join("\n"),
        }],
        ...(allOk ? {} : { isError: true }),
      };
    }
  );

  server.registerTool(
    "capture-emulator-screenshots",
    {
      title: "Capture emulator screenshots",
      description:
        "Capture N PNG screenshots per connected emulator into SCREENSHOTS_DIR (default `/screenshots`), in parallel across all devices. " +
        "Use for Play-Store listings or release-notes assets — set `loginFlow: \"matrix-synapse\"` to drive the bundled mock login first, or `loginFlow: \"none\"` (default) for any other app. " +
        "Returns the per-emulator file paths plus a `structuredContent` block enumerating screenshotsDir and devices. " +
        "Defaults walk the bottom-nav tabs; pass `autoNavigate: false` with `delayMs` for manual screen switching, or `tabLabels` to override file naming.",
      inputSchema: z.object({
        captureCount: z.number().int().min(1).max(10).default(4).describe("Screenshots per device"),
        autoNavigate: z.boolean().default(true).describe("Tap bottom-nav tabs in sequence between captures"),
        navItemCount: z.number().int().min(2).max(10).default(5).describe("Total bottom-nav items in the target app — used to compute tap x-coordinate"),
        launchPackage: z.string().regex(PACKAGE_NAME_RE).optional().describe("Package to launch before capturing. Defaults to the Matrix Synapse Manager debug package when loginFlow=matrix-synapse."),
        loginFlow: z.enum(["none", "matrix-synapse"]).default("none").describe("`matrix-synapse` runs the add-server + login UI choreography first; `none` skips it."),
        serverUrl: z.string().url().optional().describe("matrix-synapse only — Matrix homeserver URL. Falls back to MOCK_SERVER_URL env var."),
        username: z.string().min(1).optional().describe("matrix-synapse only — Falls back to MOCK_USERNAME env var."),
        password: z.string().min(1).optional().describe("matrix-synapse only — Falls back to MOCK_PASSWORD env var. Prefer env over tool arg."),
        delayMs: z.number().int().min(0).max(30000).default(2000).describe("Sleep between captures when autoNavigate=false"),
        settleMs: z.number().int().min(100).max(5000).default(800).describe("Sleep after each tab tap before screencap"),
        tabLabels: z.array(z.string()).optional().describe("File-name suffixes per capture — defaults to tab1..tabN, or matrix labels when applicable"),
      }).strict(),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: false,
      },
    },
    async (
      { captureCount, autoNavigate, navItemCount, launchPackage, loginFlow, serverUrl, username, password, delayMs, settleMs, tabLabels },
      ctx
    ) => {
      await log(ctx, "info", { step: "capture-screenshots", captureCount, autoNavigate, navItemCount, launchPackage, loginFlow });

      if (!existsSync(SCREENSHOTS_DIR)) {
        mkdirSync(SCREENSHOTS_DIR, { recursive: true });
      }

      if (EMULATOR_HOSTS.length === 0) {
        return { content: [{ type: "text", text: "No emulators configured." }], isError: true };
      }

      const defaultMatrixLabels = ["users", "rooms", "stats", "settings"];
      const labels =
        tabLabels && tabLabels.length >= captureCount
          ? tabLabels
          : loginFlow === "matrix-synapse" && captureCount === defaultMatrixLabels.length
            ? defaultMatrixLabels
            : Array.from({ length: captureCount }, (_, i) => `tab${i + 1}`);
      const postLoginSettle = loginFlow === "matrix-synapse" ? 3000 : settleMs;

      const settled = await Promise.all(EMULATOR_HOSTS.map(async emulator => {
        const avdName = await getAvdName(emulator);
        const filesForDevice = [];
        const displaySize =
          autoNavigate || launchPackage || loginFlow === "matrix-synapse"
            ? await getDisplaySize(emulator)
            : null;

        if ((autoNavigate || loginFlow === "matrix-synapse") && !displaySize) {
          await log(ctx, "warning", { host: emulator.host, message: "Could not get display size; skipping tap/login" });
        }

        if (loginFlow === "matrix-synapse" && displaySize) {
          await log(ctx, "info", { host: emulator.host, message: "Running Matrix Synapse add-server + login" });
          const loginOpts = {};
          if (serverUrl != null) loginOpts.serverUrl = serverUrl;
          if (username != null) loginOpts.username = username;
          if (password != null) loginOpts.password = password;
          try {
            await ensureLoggedIn(emulator, displaySize, { packageName: launchPackage || APP_PACKAGE, ...loginOpts });
          } catch (err) {
            return { host: emulator.host, avdName, files: filesForDevice, error: err.message };
          }
          await launchApp(emulator, launchPackage || APP_PACKAGE, APP_MAIN_ACTIVITY);
          await sleep(4000);
        } else if (launchPackage && displaySize) {
          await log(ctx, "info", { host: emulator.host, packageName: launchPackage });
          await launchApp(emulator, launchPackage, ".MainActivity");
          await sleep(settleMs);
        }

        for (let i = 1; i <= captureCount; i++) {
          const tabIndex = i - 1;
          if (autoNavigate && displaySize && tabIndex < navItemCount) {
            await tapBottomNavTab(emulator, tabIndex, displaySize, navItemCount);
            await sleep(i === 1 && loginFlow === "matrix-synapse" ? postLoginSettle : settleMs);
          } else if (!autoNavigate && i > 1 && delayMs > 0) {
            await sleep(delayMs);
          }

          const safeLabel = String(labels[tabIndex] ?? `tab${i}`).replace(/[^A-Za-z0-9._-]/g, "_");
          const filePath = join(SCREENSHOTS_DIR, `${avdName}_${safeLabel}.png`);
          const ok = await captureScreenshot(emulator, filePath);
          if (ok) filesForDevice.push(filePath);
        }

        return { host: emulator.host, avdName, files: filesForDevice };
      }));

      const loginErr = settled.find(r => r.error);
      if (loginErr) {
        return { content: [{ type: "text", text: loginErr.error }], isError: true };
      }
      const results = settled;

      const summaryLines = results.map(
        r => `${r.avdName} (${r.host}):\n  ${r.files.join("\n  ")}`
      );

      return {
        content: [{
          type: "text",
          text:
            (autoNavigate
              ? `Tapped ${captureCount} bottom nav tab(s) (navItemCount=${navItemCount}) on each device, then captured.\n\n`
              : "Screenshots written under ") +
            SCREENSHOTS_DIR + ":\n\n" + summaryLines.join("\n\n"),
        }],
        structuredContent: {
          screenshotsDir: SCREENSHOTS_DIR,
          autoNavigate,
          navItemCount,
          launchPackage: launchPackage ?? null,
          loginFlow,
          devices: results,
        },
      };
    }
  );

  return server;
}

// ── Express app ──────────────────────────────────────────────────────

// Default to loopback. To expose on the compose network, the operator must
// ALSO supply MCP_AUTH_TOKEN — we refuse to start otherwise (fail-closed).
const BIND_HOST = process.env.MCP_BIND_HOST || "127.0.0.1";
const PORT = process.env.PORT || 8000;
const AUTH_TOKEN = process.env.MCP_AUTH_TOKEN;

const isLoopback = BIND_HOST === "127.0.0.1" || BIND_HOST === "::1" || BIND_HOST === "localhost";
if (!isLoopback && !AUTH_TOKEN) {
  console.error(
    `Refusing to bind to non-loopback address ${BIND_HOST} without MCP_AUTH_TOKEN. ` +
    `Set MCP_AUTH_TOKEN to a long random secret, or set MCP_BIND_HOST=127.0.0.1.`
  );
  process.exit(1);
}

const app = createMcpExpressApp({
  host: BIND_HOST,
  // Restrict the Host header to defend against DNS-rebinding even when the
  // listener is on a non-loopback address.
  allowedHosts: ["localhost", "127.0.0.1", BIND_HOST],
});

// Bearer-token middleware. Constant-time compare via Buffer length+content.
function requireAuth(req, res, next) {
  if (!AUTH_TOKEN) return next(); // loopback-only mode: skip
  const header = req.get("authorization") || "";
  const expected = `Bearer ${AUTH_TOKEN}`;
  const got = Buffer.from(header);
  const want = Buffer.from(expected);
  const ok = got.length === want.length && timingSafeEqual(got, want);
  if (!ok) {
    res.status(401).json({
      jsonrpc: "2.0",
      error: { code: -32001, message: "Unauthorized" },
      id: null,
    });
    return;
  }
  next();
}

async function handleMcpRequest(req, res, parsedBody) {
  const server = createServer();
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  });
  await server.connect(transport);
  res.on("close", () => {
    transport.close();
    server.close();
  });
  await transport.handleRequest(req, res, parsedBody);
}

async function mcpRoute(req, res) {
  try {
    await handleMcpRequest(req, res, req.method === "POST" ? req.body : undefined);
  } catch (error) {
    console.error(`Error handling MCP ${req.method} request:`, error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: "2.0",
        error: { code: -32603, message: "Internal server error" },
        id: null,
      });
    }
  }
}

app.post("/mcp", requireAuth, mcpRoute);
app.get("/mcp", requireAuth, mcpRoute);

app.listen(PORT, BIND_HOST, () => {
  const authNote = AUTH_TOKEN ? "auth: bearer-token required" : "auth: loopback-only (no token set)";
  console.log(`MCP Android emulator server listening on ${BIND_HOST}:${PORT} (${authNote})`);
});
