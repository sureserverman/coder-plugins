import express from "express";

const app = express();
app.use(express.json());

const port = 8008;
const baseDomain = "example.com";

/** Base URL for Matrix IDs (e.g. @user:example.com). Can be overridden via env. */
const publicBaseUrl = process.env.SYNAPSE_BASE_URL || `https://${baseDomain}`;

/**
 * Best practice: derive API base_url from the request so the app uses the same
 * origin it connected to (e.g. http://10.0.2.2:8008 from emulator). This avoids
 * mixed-content and ensures all subsequent API calls hit this mock.
 */
function requestBaseUrl(req) {
  const host = req.get("host") || `localhost:${port}`;
  const proto = req.get("x-forwarded-proto") || req.protocol || "http";
  return `${proto}://${host}`;
}

// In-memory mock users
const users = [
  {
    name: `@admin:${baseDomain}`,
    localpart: "admin",
    password: "1234",
    admin: true,
    deactivated: false
  },
  {
    name: `@alice:${baseDomain}`,
    localpart: "alice",
    password: "alicepass",
    admin: false,
    deactivated: false
  },
  {
    name: `@bob:${baseDomain}`,
    localpart: "bob",
    password: "bobpass",
    admin: false,
    deactivated: false
  }
];

// Well-known: return base_url from request origin so app uses this mock for all API calls
app.get("/.well-known/matrix/client", (req, res) => {
  res.json({
    "m.homeserver": {
      base_url: requestBaseUrl(req)
    }
  });
});

// Basic versions endpoint
app.get("/_matrix/client/versions", (_req, res) => {
  res.json({
    versions: ["v1.11"],
    unstable_features: {}
  });
});

// Required after login: CapabilityService and dashboard call this; 404 causes errors/crashes
app.get("/_synapse/admin/v1/server_version", (_req, res) => {
  res.json({
    server_version: "1.97.0",
    python_version: "3.11.0"
  });
});

// Simple login endpoint for password auth
app.post("/_matrix/client/v3/login", (req, res) => {
  const body = req.body || {};
  const identifier = body.identifier || {};
  const username = identifier.user || body.user || "";
  const password = body.password || "";

  const user = users.find(
    u => (u.localpart === username || u.name === username) && u.password === password
  );

  if (!user) {
    return res.status(403).json({
      errcode: "M_FORBIDDEN",
      error: "Invalid username or password"
    });
  }

  const token = `mock_access_token_${user.localpart}`;

  res.json({
    user_id: user.name,
    access_token: token,
    device_id: "MOCKDEVICE"
  });
});

// Minimal admin users listing endpoint
app.get("/_synapse/admin/v2/users", (req, res) => {
  const responseUsers = users.map(u => ({
    name: u.name,
    is_guest: false,
    admin: u.admin,
    deactivated: u.deactivated
  }));

  res.json({
    users: responseUsers,
    total: responseUsers.length,
    next_token: null
  });
});

// Basic whoami endpoint
app.get("/_matrix/client/v3/account/whoami", (_req, res) => {
  res.json({
    user_id: `@admin:${baseDomain}`
  });
});

app.listen(port, "0.0.0.0", () => {
  // eslint-disable-next-line no-console
  console.log(
    `Mock Synapse listening on http://0.0.0.0:${port}. Well-known base_url is derived from request host (e.g. http://10.0.2.2:${port} from emulator).`
  );
});

