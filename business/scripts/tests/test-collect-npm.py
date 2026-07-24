#!/usr/bin/env python3
"""Fixture suite for collect-npm.py — run directly (CI convention):
    python3 business/scripts/tests/test-collect-npm.py

Drives collect-npm.py against a stub HTTP server bound to localhost (no live
network in CI), asserting the best-effort contract from
references/collector-contract.md: happy path, unknown package, network failure,
malformed upstream shape, private/absent package.json, and the usage error.

The exit code is asserted EXPLICITLY on every failure path — "a total failure
still exits 0" is the contract's whole point and the easiest thing to regress.
"""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "collect-npm.py"

FAILURES = []


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


# Recorded from the real APIs on 2026-07-24 (shapes, with counts trimmed).
WEEK = {"downloads": 1383101, "start": "2026-07-17", "end": "2026-07-23",
        "package": "left-pad"}
MONTH = {"downloads": 5222218, "start": "2026-06-24", "end": "2026-07-23",
         "package": "left-pad"}
REGISTRY = {"name": "left-pad", "dist-tags": {"latest": "1.3.0"},
            "versions": {f"1.0.{i}": {} for i in range(15)}}


class Handler(http.server.BaseHTTPRequestHandler):
    mode = "ok"

    def log_message(self, *a):
        pass

    def do_GET(self):
        if Handler.mode == "malformed":
            # Valid JSON, wrong SHAPE for every endpoint — must degrade, not crash.
            return self._send(200, json.dumps({"unexpected": True}))
        if Handler.mode == "notjson":
            return self._send(200, "<html>captive portal</html>")
        if "not-a-real" in self.path:
            return self._send(404, json.dumps({"error": "package not found"}))
        if "/downloads/point/last-week/" in self.path:
            return self._send(200, json.dumps(WEEK))
        if "/downloads/point/last-month/" in self.path:
            return self._send(200, json.dumps(MONTH))
        return self._send(200, json.dumps(REGISTRY))

    def _send(self, code, body):
        raw = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def run(target, base, mode="ok"):
    """Run the collector with its API endpoints pointed at the stub server."""
    Handler.mode = mode
    env = dict(os.environ, NPM_TEST_BASE=base)
    r = subprocess.run([sys.executable, str(SCRIPT), target],
                       capture_output=True, text=True, env=env)
    doc = None
    if r.stdout.strip():
        try:
            doc = json.loads(r.stdout)
        except ValueError:
            doc = None
    return r, doc


METRICS = ["npm.downloads_last_week", "npm.downloads_last_month", "npm.versions"]


def contract_shape(doc):
    """Every known metric key present (null when uncollected) — a caller must
    never have to distinguish 'absent' from 'failed'."""
    return (isinstance(doc, dict)
            and set(doc.get("values", {})) == set(METRICS)
            and "collected" in doc and "package" in doc
            and isinstance(doc.get("reasons"), dict))


def main():
    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    base = f"http://127.0.0.1:{srv.server_port}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    print("happy path (recorded fixture shapes):")
    r, doc = run("left-pad", base)
    check(r.returncode == 0, "happy path: exit 0")
    check(contract_shape(doc), f"happy path: contract shape ({doc})")
    check(doc and doc["package"] == "left-pad", "happy path: package identified")
    check(doc and doc["values"]["npm.downloads_last_week"] == 1383101,
          "happy path: weekly downloads")
    check(doc and doc["values"]["npm.downloads_last_month"] == 5222218,
          "happy path: monthly downloads")
    check(doc and doc["values"]["npm.versions"] == 15,
          "happy path: published-version count")
    check(doc and doc["reasons"] == {}, f"happy path: no reasons ({doc})")

    print("unknown package (404):")
    r, doc = run("not-a-real-package-9987", base)
    check(r.returncode == 0, "unknown package: EXIT 0 (contract)")
    check(contract_shape(doc), "unknown package: contract shape held")
    check(doc and all(v is None for v in doc["values"].values()),
          f"unknown package: all values null ({doc and doc['values']})")
    check(doc and len(doc["reasons"]) == len(METRICS),
          "unknown package: a reason per metric, none silently dropped")
    check(doc and all("not found" in v for v in doc["reasons"].values()),
          f"unknown package: reasons say not-found ({doc and doc['reasons']})")

    print("network failure (nothing listening):")
    dead = "http://127.0.0.1:1"
    r, doc = run("left-pad", dead)
    check(r.returncode == 0, "network failure: EXIT 0 (contract)")
    check(contract_shape(doc), "network failure: contract shape held")
    check(doc and all(v is None for v in doc["values"].values()),
          "network failure: all values null")
    check(doc and all("unreachable" in v or "network" in v
                      for v in doc["reasons"].values()),
          f"network failure: reasons name the cause ({doc and doc['reasons']})")

    print("malformed upstream response (valid JSON, wrong shape):")
    r, doc = run("left-pad", base, mode="malformed")
    check(r.returncode == 0, "malformed: EXIT 0 (contract)")
    check(r.stderr == "", f"malformed: no traceback on stderr ({r.stderr[:120]})")
    check(doc and all(v is None for v in doc["values"].values()),
          "malformed: all values null, never a partial number")
    check(doc and all("shape" in v or "null" in v for v in doc["reasons"].values()),
          f"malformed: reasons name the shape problem ({doc and doc['reasons']})")

    print("non-JSON response (captive portal / HTML error page):")
    r, doc = run("left-pad", base, mode="notjson")
    check(r.returncode == 0, "non-JSON: EXIT 0 (contract)")
    check(r.stderr == "", "non-JSON: no traceback")
    check(doc and all(v is None for v in doc["values"].values()),
          "non-JSON: all values null")

    with tempfile.TemporaryDirectory() as td:
        print("repo path without package.json:")
        r, doc = run(td, base)
        check(r.returncode == 0, "no package.json: EXIT 0 (contract)")
        check(doc and doc["package"] is None, "no package.json: package null")
        check(doc and list(doc["reasons"]) == ["_"],
              f"no package.json: ONE whole-collection reason ({doc and doc['reasons']})")
        check(doc and "no package.json" in doc["reasons"]["_"],
              "no package.json: reason explains it")

        print("repo path WITH package.json (name resolved from disk):")
        Path(td, "package.json").write_text(json.dumps({"name": "left-pad"}))
        r, doc = run(td, base)
        check(r.returncode == 0 and doc and doc["package"] == "left-pad",
              "package.json name resolved without the caller knowing it")
        check(doc and doc["values"]["npm.downloads_last_week"] == 1383101,
              "repo-path target collects the same metrics as a bare name")

        print("package.json name is as untrusted as a CLI argument:")
        Path(td, "package.json").write_text(
            json.dumps({"name": "oauth2:SECRETTOKEN123@internal.example.com"}))
        r, doc = run(td, base)
        check(r.returncode == 0, "hostile package.json name: EXIT 0")
        check("SECRETTOKEN123" not in json.dumps(doc),
              f"a name read from disk gets the SAME grammar check as a bare "
              f"argument — validation must not be asymmetric "
              f"({json.dumps(doc)[:150]})")

        print("private package:")
        Path(td, "package.json").write_text(
            json.dumps({"name": "@corp/secret", "private": True}))
        r, doc = run(td, base)
        check(r.returncode == 0, "private: EXIT 0")
        check(doc and list(doc["reasons"]) == ["_"]
              and "private" in doc["reasons"]["_"],
              "private package explained as private, not as 'not found'")

    # --- hostile / malformed TARGET strings ---------------------------------
    # These vary the ARGUMENT, not the response. The response-shape cases above
    # all passed while unicode and space targets still crashed with a traceback
    # (exit 1) — the contract's one forbidden outcome.
    print("hostile target strings (must degrade, never raise):")
    for label, target in (("unicode", "café-pkg"),
                          ("space", "pkg with space"),
                          ("control char", "pkg\tname"),
                          ("emoji", "pkg-🔥"),
                          ("very long", "a" * 500)):
        r, doc = run(target, base)
        check(r.returncode == 0, f"{label} target: EXIT 0, no crash")
        check("Traceback" not in r.stderr, f"{label} target: no traceback")
        check(doc is not None, f"{label} target: still emits a document")

    print("trailing newline must not slip past the name grammar:")
    r, doc = run("left-pad\n", base)
    check(r.returncode == 0, "trailing-newline target: EXIT 0")
    check(doc and doc["package"] != "left-pad\n",
          f"a raw newline never reaches the `package` subject — metrics.md is "
          f"line-oriented, so an embedded newline can fabricate a line "
          f"(`$` matches before one trailing \\n; the grammar needs `\\Z`) "
          f"({doc and doc['package']!r})")

    print("secret redaction — a token must never reach a committed reason:")
    for label, target in (("bare userinfo", "oauth2:SECRETTOKEN123@internal.example.com"),
                          ("url userinfo", "https://user:SECRETTOKEN123@example.com/p")):
        r, doc = run(target, base)
        raw = json.dumps(doc)
        check(r.returncode == 0, f"{label}: EXIT 0")
        check("SECRETTOKEN123" not in raw,
              f"{label}: token absent from the WHOLE document, "
              f"including the `package` subject field ({raw[:150]})")

    print("real packages that merely look URL-ish:")
    for name in ("http-server", "httpolyglot", "https-proxy-agent"):
        r, doc = run(name, base)
        check(doc and doc["package"] == name,
              f"{name} resolves as a package name (a bare 'http' prefix test "
              f"would refuse it forever)")
    r, doc = run("@babel/core", base)
    check(doc and doc["package"] == "@babel/core", "scoped name still resolves")

    print("empty target must not silently resolve against CWD:")
    r, doc = run("", base)
    check(r.returncode == 0, "empty target: EXIT 0")
    check(doc and doc["package"] is None
          and "empty target" in doc["reasons"].get("_", ""),
          f"empty target refused, not resolved to '.' ({doc and doc['reasons']})")

    print("test seam is loopback-only:")
    env = dict(os.environ, NPM_TEST_BASE="http://evil.example.com")
    r = subprocess.run([sys.executable, str(SCRIPT), "left-pad"],
                       capture_output=True, text=True, env=env)
    check("ignored" in r.stderr and "not loopback" in r.stderr,
          f"non-loopback override refused loudly on stderr ({r.stderr[:100]})")

    print("usage error (the ONLY non-zero exit):")
    r = subprocess.run([sys.executable, str(SCRIPT)],
                       capture_output=True, text=True)
    check(r.returncode != 0, "no args: non-zero exit")
    check("usage" in (r.stderr + r.stdout).lower(), "no args: usage message")

    srv.shutdown()
    if FAILURES:
        print(f"\nFAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("\nOK — all collect-npm fixture checks passed")


if __name__ == "__main__":
    main()
