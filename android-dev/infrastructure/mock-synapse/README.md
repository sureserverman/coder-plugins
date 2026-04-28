# Mock Synapse for Matrix Synapse Manager

Minimal mock of the Matrix Synapse admin API for testing and screenshot capture. Listens on port 8008.

**Use case:** E2E-style flows and store screenshots against a controllable backend (hermetic network). For in-app instrumented tests (Espresso, Hilt), the app’s own tests typically use MockWebServer or test doubles instead of this external mock.

## Best practices (network apps + mock servers)

1. **Start mock before the app.** The app discovers the server and calls APIs immediately after login; if the mock is down or returns wrong shapes, the app shows errors or crashes.

2. **Use the same origin for discovery and API.** The mock serves `GET /.well-known/matrix/client` with `base_url` derived from the request host (`requestBaseUrl(req)`). So when the emulator opens `http://10.0.2.2:8008`, the app gets `base_url: "http://10.0.2.2:8008"` and all subsequent calls (login, server_version, users) go to the same mock. No mixed-content or wrong-host issues.

3. **Implement every endpoint the app calls after login.** Missing endpoints cause 404 → app error or crash. This mock implements:
   - `/.well-known/matrix/client` — discovery
   - `/_matrix/client/versions` — client support
   - `/_matrix/client/v3/login` — password login
   - `/_synapse/admin/v1/server_version` — **required** by CapabilityService; without it the app fails after login
   - `/_synapse/admin/v2/users` — user list (first tab)
   - `/_matrix/client/v3/account/whoami` — session

4. **Match the app’s request/response shapes.** Login expects `identifier.user` and `password`; response must include `access_token`, `user_id`, `device_id`. Server version must include `server_version` (e.g. `"1.97.0"`) for capability parsing.

5. **Allow cleartext on the app side** for the emulator host (`10.0.2.2`) so HTTP works. The Matrix Synapse Manager app uses `network_security_config.xml` for this in debug builds.

## Credentials

- **admin** / **1234**
- alice / alicepass, bob / bobpass

## Run

From `mcp/android`: `podman compose up -d mock-synapse`. From the emulator, use server URL: `http://10.0.2.2:8008`.
