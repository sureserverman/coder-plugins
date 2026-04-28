---
name: mock-server-from-app-sources
description: Use when the user asks for a mock server, fake API, or stub backend based on an app's sources. Trigger on "make a mock server for this app", "I need a fake API for testing", "this app needs a backend for UI tests", or when an app requires login/REST/GraphQL and no mock exists yet.
---

# Mock Server from App Sources

Analyze the app's sources to infer what backend/API it needs, then scaffold a **mock server container** that implements the minimal endpoints so the app can be tested (e.g. login, list data) without a real backend.

## When to use

- User wants to test an app that clearly depends on a backend (login, REST/GraphQL API).
- User asks for a "mock server" or "fake API" for the app.
- You need a backend for integration tests, screenshots, or manual testing and no mock exists yet.

## Workflow

### 1. Analyze app sources

- **API clients:** Find Retrofit interfaces, Ktor clients, OkHttp calls, fetch/axios, or similar. Look for `@GET`, `@POST`, `@PUT`, `@DELETE`, base URL config, and path strings.
- **Auth flow:** Identify login endpoint (path + body/query), token handling (header, response field), and any "whoami" or session endpoint.
- **Key endpoints:** List the endpoints the app calls to reach a useful state (e.g. after login: list users, list rooms, config). Prefer the **minimum set** needed for a smoke test or for the flow the user cares about.
- **Request/response shapes:** From DTOs, Kotlin data classes, TypeScript interfaces, or API docs: note method, path, request body, and response body (or status) for each endpoint.

Produce a short **API contract** (list of endpoints and their behavior) that the mock must satisfy.

### 2. Decide if a mock is needed

- If the app is **login-gated** or **fetches data from an API**, a mock is usually needed for deterministic testing.
- If the app only talks to optional or third-party services, a mock may still be useful for offline or controlled tests.

### 3. Create the mock server

- **Location:** Prefer a dedicated directory, e.g. `mock-<name>/` next to your app's compose stack. This plugin bundles `infrastructure/mock-synapse/` as a reference implementation alongside the emulator stack.
- **Stack:** Node (Express) or Python (FastAPI/Flask). Use the same as the rest of the repo if there is one; otherwise Node/Express is a good default.
- **Contents:**
  - **Containerfile** (or Dockerfile): base image (e.g. `node:22-bookworm` or `python:3.12-slim`), install deps, copy server, expose port, CMD to run server.
  - **Server implementation:** One file or a small module that:
    - Listens on a fixed port (e.g. 8008 or from env).
    - Implements each endpoint from the API contract with **minimal in-memory state** (e.g. hardcoded users, list that can be extended).
    - Returns the expected status and JSON shape the app expects (infer from DTOs or error handling).
  - **Dependencies file:** `package.json` (Express) or `requirements.txt` (FastAPI).
- **Auth:** If the app uses login: mock accepts a fixed credential (e.g. admin/1234), returns a token and any user/session fields the app stores. Protect other routes with the same header the app sends (e.g. `Authorization: Bearer <token>`).
- **Config:** Use env vars for port, base URL, or credentials so the same image can be reused (e.g. `MOCK_PORT`, `BASE_URL`).

### 4. Document how to run and use

- **Run:** `podman compose up -d mock-<name>` or `podman run -p <port>:<port> mock-<name>`.
- **App config:** Document the URL the app must use (e.g. emulator: `http://10.0.2.2:8008`; host: `http://localhost:8008`). If the app has cleartext or network config, note it.
- **Optional:** Add the mock service to an existing `compose.yaml` (e.g. next to android-mcp) so the orchestrator skill can start it when testing that app.

## Reference: mock-synapse (bundled in this plugin)

This plugin bundles a mock Matrix Synapse server you can copy as a template:

- **Path:** `infrastructure/mock-synapse/` inside this plugin. Resolves to `~/.claude/plugins/android-dev/infrastructure/mock-synapse` (marketplace) or `~/.claude/plugins/local/android-dev/infrastructure/mock-synapse` (local).
- **Layout:** `Containerfile`, `package.json`, `server.mjs`. Node + Express, in-memory users, env `SYNAPSE_BASE_URL`.
- **Endpoints:** `/_matrix/client/versions`, `/_matrix/client/v3/login`, `/_synapse/admin/v2/users`, `/_matrix/client/v3/account/whoami`.
- Reuse the same layout and substitute your app's endpoints and request/response shapes.

## Checklist

- [ ] List API endpoints and auth from app sources (Retrofit/Ktor/OkHttp/fetch, DTOs).
- [ ] Write a minimal API contract (method, path, request/response).
- [ ] Create `mock-<name>/` with Containerfile, server implementation, and deps.
- [ ] Mock returns the shapes the app expects; auth matches (e.g. Bearer token).
- [ ] Document run command and URL for the app (and optionally add to compose).

## Delegation (Claude Code only)

> **Skip this section unless you are Claude Code.** The Agent tool with
> `subagent_type:` parameters is a Claude Code feature. Codex, Cursor, Gemini,
> OpenCode, and other hosts do not have it — run the full workflow yourself
> instead.

Once the endpoint list and API contract are extracted from the app sources,
producing the mock server (Containerfile, implementation, deps, run docs) is
a Sonnet-tier code-generation job. If you are on Opus, delegate the write
phase to the `code-generator` subagent (model: sonnet) via the Agent tool
with `subagent_type: code-generator`. Give it:

- the finalized endpoint list with method, path, request/response shapes,
- the auth scheme the app expects (Bearer token, cookie, header),
- the target language/framework and the `mock-<name>/` target directory,
- the instruction to verify the mock starts (e.g. build the container,
  `curl` a known route) before returning.

Keep the source-code reconnaissance (finding Retrofit/Ktor/OkHttp/fetch call
sites, DTOs, auth handling) and the contract synthesis in this session —
those require reading and reasoning about the app's actual wiring.
