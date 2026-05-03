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

function createServer() {
  const server = new McpServer(
    { name: "android-emulator-mcp", version: "0.3.0" },
    { capabilities: { logging: {} } }
  );

  server.registerTool(
    "start-android-tablet-emulators",
    {
      title: "Connect to emulator containers",
      description:
        "Connects to the 3 emulator containers (phone6in, tablet7in, tablet10in) over the compose network via adb TCP. Waits for boot completion in parallel. Emulators must already be running (started by compose).",
      inputSchema: z.object({
        bootTimeoutMs: z
          .number()
          .int()
          .min(30000)
          .max(300000)
          .default(120000)
          .describe("Max wait for each emulator to finish booting (ms)"),
      }),
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
        "Launches an app by package name on all connected emulators (am start -S). Use for any app; activity defaults to .MainActivity.",
      inputSchema: z.object({
        packageName: z.string().regex(PACKAGE_NAME_RE).describe("Application ID / package name"),
        activity: z.string().regex(ACTIVITY_RE).default(".MainActivity").describe("Launchable activity"),
      }),
    },
    async ({ packageName, activity }, ctx) => {
      if (EMULATOR_HOSTS.length === 0) {
        return { content: [{ type: "text", text: "No emulators configured." }] };
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
        "App-specific: launches Matrix Synapse Manager, adds server URL, and logs in. " +
        "Credentials must be supplied as tool args or via MOCK_SERVER_URL/MOCK_USERNAME/MOCK_PASSWORD env vars.",
      inputSchema: z.object({
        serverUrl: z.string().url().optional(),
        username: z.string().min(1).optional(),
        password: z.string().min(1).optional(),
      }),
    },
    async ({ serverUrl, username, password }, ctx) => {
      if (EMULATOR_HOSTS.length === 0) {
        return { content: [{ type: "text", text: "No emulators configured." }] };
      }
      const effectiveUrl = serverUrl ?? MOCK_SERVER_URL;
      const effectiveUser = username ?? MOCK_USERNAME;
      const effectivePass = password ?? MOCK_PASSWORD;
      if (!effectiveUrl || !effectiveUser || !effectivePass) {
        return {
          content: [{
            type: "text",
            text: "matrix-synapse-login requires serverUrl, username, and password — supply as tool args or set MOCK_SERVER_URL / MOCK_USERNAME / MOCK_PASSWORD env vars.",
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
        "Installs the debug APK on all connected emulators. Build the app first and ensure the APK volume is mounted.",
      inputSchema: z.object({
        apkPath: z.string().default("/apks/app-debug.apk").describe("Path to APK inside the container — must resolve under APK_BASE_DIR (default /apks)"),
      }),
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
        "Captures screenshots from all connected emulators. Supports bottom-nav tab auto-navigation, Matrix Synapse login flow, or manual delay-based capture.",
      inputSchema: z.object({
        captureCount: z.number().int().min(1).max(10).default(4),
        autoNavigate: z.boolean().default(true),
        navItemCount: z.number().int().min(2).max(10).default(5),
        launchPackage: z.string().regex(PACKAGE_NAME_RE).optional(),
        loginFlow: z.enum(["none", "matrix-synapse"]).default("none"),
        serverUrl: z.string().url().optional(),
        username: z.string().min(1).optional(),
        password: z.string().min(1).optional(),
        delayMs: z.number().int().min(0).max(30000).default(2000),
        settleMs: z.number().int().min(100).max(5000).default(800),
        tabLabels: z.array(z.string()).optional(),
      }),
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
        return { content: [{ type: "text", text: "No emulators configured." }] };
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
