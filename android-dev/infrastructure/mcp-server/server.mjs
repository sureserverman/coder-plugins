import express from "express";
import { randomUUID } from "crypto";
import * as z from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { createMcpExpressApp } from "@modelcontextprotocol/sdk/server/express.js";
import { mkdirSync, writeFileSync, existsSync } from "fs";
import { join } from "path";
import { promisify } from "util";
import { exec as _exec } from "child_process";

const exec = promisify(_exec);
const SCREENSHOTS_DIR = process.env.SCREENSHOTS_DIR || "/screenshots";

const APP_PACKAGE = "com.matrix.synapse.manager.debug";
const APP_MAIN_ACTIVITY = "com.matrix.synapse.manager.MainActivity";
const MOCK_SERVER_URL = "http://10.0.2.2:8008";
const MOCK_USERNAME = "admin";
const MOCK_PASSWORD = "1234";

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

// ── Helpers ──────────────────────────────────────────────────────────

async function run(cmd, opts = {}) {
  const { stdout, stderr } = await exec(cmd, {
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

/** Build adb prefix to talk to a remote emulator's adb server. */
function adbCmd(emulator) {
  return `adb -H ${emulator.host} -P ${emulator.port}`;
}

/** Check if a remote adb server has a device ready. */
async function adbCheckDevice(emulator) {
  try {
    const { stdout } = await run(`${adbCmd(emulator)} devices`);
    return (stdout || "").includes("emulator");
  } catch {
    return false;
  }
}

async function getAvdName(emulator) {
  try {
    const { stdout } = await run(
      `${adbCmd(emulator)} shell getprop ro.boot.qemu.avd_name 2>/dev/null`
    );
    const name = (stdout || "").trim();
    if (name) return name;
  } catch { /* ignore */ }
  return emulator.host;
}

async function captureScreenshot(emulator, filePath) {
  try {
    const { stdout } = await exec(
      `${adbCmd(emulator)} exec-out screencap -p`,
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
    const { stdout } = await run(`${adbCmd(emulator)} shell wm size`);
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
      const { stdout } = await run(
        `${adbCmd(emulator)} shell getprop sys.boot_completed 2>/dev/null`
      );
      if ((stdout || "").trim() === "1") return true;
    } catch { /* ignore */ }
    await sleep(3000);
  }
  return false;
}

async function tap(emulator, x, y) {
  try {
    await run(`${adbCmd(emulator)} shell input tap ${Math.round(x)} ${Math.round(y)}`);
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
  const component = `${packageName}/${activity.startsWith(".") ? activity : activity}`;
  const safe = component.replace(/"/g, '\\"');
  try {
    await run(`${adbCmd(emulator)} shell am start -S -n "${safe}"`);
    return true;
  } catch { return false; }
}

async function inputText(emulator, text) {
  const escaped = text.replace(/'/g, "'\\''");
  try {
    await run(`${adbCmd(emulator)} shell input text '${escaped}'`);
    return true;
  } catch { return false; }
}

async function keyevent(emulator, code) {
  try {
    await run(`${adbCmd(emulator)} shell input keyevent ${code}`);
    return true;
  } catch { return false; }
}

async function swipe(emulator, x1, y1, x2, y2, durationMs = 300) {
  try {
    await run(
      `${adbCmd(emulator)} shell input swipe ${Math.round(x1)} ${Math.round(y1)} ${Math.round(x2)} ${Math.round(y2)} ${durationMs}`
    );
    return true;
  } catch { return false; }
}

async function ensureLoggedIn(emulator, displaySize, opts = {}) {
  const serverUrl = opts.serverUrl ?? MOCK_SERVER_URL;
  const username = opts.username ?? MOCK_USERNAME;
  const password = opts.password ?? MOCK_PASSWORD;
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
    { name: "android-emulator-mcp", version: "0.2.0" },
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
        packageName: z.string().describe("Application ID / package name"),
        activity: z.string().default(".MainActivity").describe("Launchable activity"),
      }),
    },
    async ({ packageName, activity }, ctx) => {
      if (EMULATOR_HOSTS.length === 0) {
        return { content: [{ type: "text", text: "No emulators configured." }] };
      }
      for (const emulator of EMULATOR_HOSTS) {
        await log(ctx, "info", { host: emulator.host, packageName, activity });
        await launchApp(emulator, packageName, activity);
      }
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
        "App-specific: launches Matrix Synapse Manager, adds server URL, and logs in via mock Synapse.",
      inputSchema: z.object({
        serverUrl: z.string().default(MOCK_SERVER_URL),
        username: z.string().default(MOCK_USERNAME),
        password: z.string().default(MOCK_PASSWORD),
      }),
    },
    async ({ serverUrl, username, password }, ctx) => {
      if (EMULATOR_HOSTS.length === 0) {
        return { content: [{ type: "text", text: "No emulators configured." }] };
      }
      let count = 0;
      for (const emulator of EMULATOR_HOSTS) {
        const displaySize = await getDisplaySize(emulator);
        if (!displaySize) continue;
        await log(ctx, "info", { host: emulator.host, step: "ensure-logged-in" });
        await ensureLoggedIn(emulator, displaySize, { serverUrl, username, password });
        count++;
      }
      return {
        content: [{
          type: "text",
          text: `Logged in on ${count} emulator(s). Server: ${serverUrl}, user: ${username}.`,
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
        apkPath: z.string().default("/apks/app-debug.apk").describe("Path to APK inside the container"),
      }),
    },
    async ({ apkPath }, ctx) => {
      await log(ctx, "info", { step: "install-app", apkPath });

      if (!existsSync(apkPath)) {
        return {
          content: [{
            type: "text",
            text: `APK not found at ${apkPath}. Build the app first and ensure the debug output is mounted at /apks.`,
          }],
          isError: true,
        };
      }

      if (EMULATOR_HOSTS.length === 0) {
        return {
          content: [{ type: "text", text: "No emulators configured." }],
        };
      }

      const results = [];
      for (const emulator of EMULATOR_HOSTS) {
        const avdName = await getAvdName(emulator);
        try {
          await run(`${adbCmd(emulator)} install -r ${apkPath}`);
          results.push({ host: emulator.host, avdName, ok: true });
        } catch (err) {
          results.push({ host: emulator.host, avdName, ok: false, error: err.message || String(err) });
        }
      }

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
        launchPackage: z.string().optional(),
        loginFlow: z.enum(["none", "matrix-synapse"]).default("none"),
        serverUrl: z.string().optional(),
        username: z.string().optional(),
        password: z.string().optional(),
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

      const results = [];

      for (const emulator of EMULATOR_HOSTS) {
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
          await ensureLoggedIn(emulator, displaySize, { packageName: launchPackage || APP_PACKAGE, ...loginOpts });
          await launchApp(emulator, launchPackage || APP_PACKAGE, APP_MAIN_ACTIVITY);
          await sleep(4000);
        } else if (launchPackage && displaySize) {
          await log(ctx, "info", { host: emulator.host, packageName: launchPackage });
          await launchApp(emulator, launchPackage, ".MainActivity");
          await sleep(settleMs);
        }

        const defaultMatrixLabels = ["users", "rooms", "stats", "settings"];
        const labels =
          tabLabels && tabLabels.length >= captureCount
            ? tabLabels
            : loginFlow === "matrix-synapse" && captureCount === defaultMatrixLabels.length
              ? defaultMatrixLabels
              : Array.from({ length: captureCount }, (_, i) => `tab${i + 1}`);
        const postLoginSettle = loginFlow === "matrix-synapse" ? 3000 : settleMs;

        for (let i = 1; i <= captureCount; i++) {
          const tabIndex = i - 1;
          if (autoNavigate && displaySize && tabIndex < navItemCount) {
            await tapBottomNavTab(emulator, tabIndex, displaySize, navItemCount);
            await sleep(i === 1 && loginFlow === "matrix-synapse" ? postLoginSettle : settleMs);
          } else if (!autoNavigate && i > 1 && delayMs > 0) {
            await sleep(delayMs);
          }

          const filePath = join(SCREENSHOTS_DIR, `${avdName}_${labels[tabIndex]}.png`);
          const ok = await captureScreenshot(emulator, filePath);
          if (ok) filesForDevice.push(filePath);
        }

        results.push({ host: emulator.host, avdName, files: filesForDevice });
      }

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

const app = createMcpExpressApp({
  host: "0.0.0.0",
  allowedHosts: ["localhost", "127.0.0.1"],
});

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

app.post("/mcp", async (req, res) => {
  try {
    await handleMcpRequest(req, res, req.body);
  } catch (error) {
    console.error("Error handling MCP request:", error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: "2.0",
        error: { code: -32603, message: "Internal server error" },
        id: null,
      });
    }
  }
});

app.get("/mcp", async (req, res) => {
  try {
    await handleMcpRequest(req, res, undefined);
  } catch (error) {
    console.error("Error handling MCP GET request:", error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: "2.0",
        error: { code: -32603, message: "Internal server error" },
        id: null,
      });
    }
  }
});

const PORT = process.env.PORT || 8000;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`MCP Android emulator server listening on port ${PORT}`);
});
