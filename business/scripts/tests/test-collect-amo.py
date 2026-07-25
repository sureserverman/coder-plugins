#!/usr/bin/env python3
"""Fixture suite for collect-amo.py — run directly (CI convention):
    python3 business/scripts/tests/test-collect-amo.py

Drives collect-amo.py against a stub HTTP server bound to localhost (no live
network in CI), asserting the best-effort contract from
references/collector-contract.md: happy path, missing addon, network failure,
malformed upstream shape, a partial response, and the usage error.

The exit code is asserted EXPLICITLY on every failure path — "a total failure
still exits 0" is the contract's whole point and the easiest thing to regress.
"""
import http.server
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "collect-amo.py"

FAILURES = []


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


# Recorded from the real AMO API on 2026-07-24 (shape kept, extra keys trimmed).
ADDON = {
    "slug": "ublock-origin",
    "average_daily_users": 10558859,
    "weekly_downloads": 211702,
    "ratings": {"average": 4.8006, "bayesian_average": 4.8002830281191,
                "count": 21933, "text_count": 5782},
}
# A freshly-listed addon: present, but with no ratings block yet.
NEW_ADDON = {"slug": "brand-new", "average_daily_users": 3, "weekly_downloads": 1}

METRICS = ["amo.daily_users", "amo.downloads_last_week",
           "amo.rating_count", "amo.rating_average"]


class Handler(http.server.BaseHTTPRequestHandler):
    mode = "ok"

    def log_message(self, *a):
        pass

    def do_GET(self):
        if Handler.mode == "malformed":
            return self._send(200, json.dumps(["not", "an", "object"]))
        if Handler.mode == "noslug":
            # A dict WITHOUT a slug key — the branch where the collector falls
            # back to the caller's argument as the subject. Neither the list
            # `malformed` fixture nor `partial` (which has a slug) reaches it.
            return self._send(200, json.dumps(
                {"average_daily_users": 5, "weekly_downloads": 2}))
        if Handler.mode == "partial":
            return self._send(200, json.dumps(NEW_ADDON))
        if Handler.mode == "notjson":
            return self._send(200, "<html>captive portal</html>")
        if "not-a-real" in self.path:
            return self._send(404, json.dumps({"detail": "Not found."}))
        return self._send(200, json.dumps(ADDON))

    def _send(self, code, body):
        raw = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def run(target, base, mode="ok"):
    Handler.mode = mode
    env = dict(os.environ, AMO_TEST_BASE=base)
    r = subprocess.run([sys.executable, str(SCRIPT), target],
                       capture_output=True, text=True, env=env)
    doc = None
    if r.stdout.strip():
        try:
            doc = json.loads(r.stdout)
        except ValueError:
            doc = None
    return r, doc


def contract_shape(doc):
    """Every known metric key present (null when uncollected) — a caller must
    never have to distinguish 'absent' from 'failed'."""
    return (isinstance(doc, dict)
            and set(doc.get("values", {})) == set(METRICS)
            and "collected" in doc and "addon" in doc
            and isinstance(doc.get("reasons"), dict))


def main():
    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    base = f"http://127.0.0.1:{srv.server_port}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    print("happy path (recorded fixture shape):")
    r, doc = run("ublock-origin", base)
    check(r.returncode == 0, "happy path: exit 0")
    check(contract_shape(doc), f"happy path: contract shape ({doc})")
    check(doc and doc["addon"] == "ublock-origin", "happy path: addon identified")
    check(doc and doc["values"]["amo.daily_users"] == 10558859,
          "happy path: daily users")
    check(doc and doc["values"]["amo.downloads_last_week"] == 211702,
          "happy path: weekly downloads")
    check(doc and doc["values"]["amo.rating_count"] == 21933,
          "happy path: rating count from the nested block")
    check(doc and abs(doc["values"]["amo.rating_average"] - 4.8006) < 1e-9,
          "happy path: rating average kept as a float, not truncated to 4")
    check(doc and doc["reasons"] == {}, f"happy path: no reasons ({doc})")

    print("missing addon (404):")
    r, doc = run("not-a-real-addon-9987", base)
    check(r.returncode == 0, "missing addon: EXIT 0 (contract)")
    check(contract_shape(doc), "missing addon: contract shape held")
    check(doc and all(v is None for v in doc["values"].values()),
          "missing addon: all values null")
    check(doc and list(doc["reasons"]) == ["_"],
          f"missing addon: ONE whole-collection reason ({doc and doc['reasons']})")
    check(doc and "not found" in doc["reasons"]["_"],
          "missing addon: reason says not-found")

    print("network failure (nothing listening):")
    r, doc = run("ublock-origin", "http://127.0.0.1:1")
    check(r.returncode == 0, "network failure: EXIT 0 (contract)")
    check(contract_shape(doc), "network failure: contract shape held")
    check(doc and all(v is None for v in doc["values"].values()),
          "network failure: all values null")
    check(doc and "_" in doc["reasons"]
          and ("unreachable" in doc["reasons"]["_"]
               or "network" in doc["reasons"]["_"]),
          f"network failure: reason names the cause ({doc and doc['reasons']})")

    print("malformed upstream response (valid JSON, wrong shape):")
    r, doc = run("ublock-origin", base, mode="malformed")
    check(r.returncode == 0, "malformed: EXIT 0 (contract)")
    check(r.stderr == "", f"malformed: no traceback ({r.stderr[:120]})")
    check(doc and all(v is None for v in doc["values"].values()),
          "malformed: all values null, never a partial number")
    check(doc and "shape" in doc["reasons"].get("_", ""),
          f"malformed: reason names the shape problem ({doc and doc['reasons']})")

    print("non-JSON response (captive portal / HTML error page):")
    r, doc = run("ublock-origin", base, mode="notjson")
    check(r.returncode == 0, "non-JSON: EXIT 0 (contract)")
    check(r.stderr == "", "non-JSON: no traceback")
    check(doc and all(v is None for v in doc["values"].values()),
          "non-JSON: all values null")

    print("partial response (new addon, no ratings block yet):")
    r, doc = run("brand-new", base, mode="partial")
    check(r.returncode == 0, "partial: EXIT 0")
    check(doc and doc["values"]["amo.daily_users"] == 3
          and doc["values"]["amo.downloads_last_week"] == 1,
          "partial: the metrics that ARE present still collect")
    check(doc and doc["values"]["amo.rating_count"] is None
          and doc["values"]["amo.rating_average"] is None,
          "partial: absent ratings are NULL, never 0 — a zero would silently "
          "satisfy a rating target")
    check(doc and set(doc["reasons"]) == {"amo.rating_count", "amo.rating_average"},
          f"partial: per-metric reasons only for what failed ({doc and doc['reasons']})")

    # --- hostile / malformed TARGET strings ---------------------------------
    # These vary the ARGUMENT, not the response. The response-shape cases above
    # all passed while unicode and space targets still crashed with a traceback
    # (exit 1) — the contract's one forbidden outcome.
    print("hostile target strings (must degrade, never raise):")
    for label, target in (("unicode", "café-addon"),
                          ("space", "addon with space"),
                          ("control char", "addon\tname"),
                          ("emoji", "addon-🔥"),
                          ("very long", "a" * 500)):
        r, doc = run(target, base)
        check(r.returncode == 0, f"{label} target: EXIT 0, no crash")
        check("Traceback" not in r.stderr, f"{label} target: no traceback")
        check(doc is not None, f"{label} target: still emits a document")

    print("trailing newline must not slip past the id grammar:")
    r, doc = run("ublock-origin\n", base)
    check(r.returncode == 0, "trailing-newline target: EXIT 0")
    check(doc and "\n" not in json.dumps(doc["reasons"])[1:-1].replace("\\n", ""),
          f"a raw newline never reaches a reason — metrics.md is line-oriented "
          f"({doc and doc['reasons']})")
    check(doc and doc["addon"] is None,
          "trailing-newline id is refused, not carried")

    print("secret redaction — a token must never reach a committed reason:")
    for label, target in (("bare userinfo", "oauth2:SECRETTOKEN123@internal.example.com"),
                          ("url userinfo", "https://user:SECRETTOKEN123@example.com/p")):
        r, doc = run(target, base)
        raw = json.dumps(doc)
        check(r.returncode == 0, f"{label}: EXIT 0")
        check("SECRETTOKEN123" not in raw,
              f"{label}: token absent from the WHOLE document ({raw[:150]})")

    print("response without a slug — the subject-fallback branch:")
    r, doc = run("oauth2:SECRETTOKEN123@internal.example.com", base, mode="noslug")
    check(r.returncode == 0, "no-slug + hostile target: EXIT 0")
    check("SECRETTOKEN123" not in json.dumps(doc),
          f"no-slug fallback never carries an unvalidated target into the "
          f"`addon` subject field ({json.dumps(doc)[:150]})")
    r, doc = run("ublock-origin", base, mode="noslug")
    check(doc and doc["addon"] == "ublock-origin",
          "no-slug fallback still reports a VALID id, so the document stays useful")

    print("AMO id grammar (all three legal forms survive; junk is refused):")
    for label, ident in (("slug", "ublock-origin"),
                         ("numeric id", "12345"),
                         ("name@domain GUID", "uBlock0@raymondhill.net"),
                         ("{uuid} GUID", "{d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}")):
        r, doc = run(ident, base, mode="noslug")
        check(r.returncode == 0 and doc and doc["addon"] == ident,
              f"{label} accepted and echoed intact ({doc and doc['addon']})")
    r, doc = run("uBlock0@raymondhill.net", base)
    check(r.returncode == 0, "name@domain GUID: EXIT 0 on the normal path")

    print("test seam is loopback-only:")
    env = dict(os.environ, AMO_TEST_BASE="http://evil.example.com")
    r = subprocess.run([sys.executable, str(SCRIPT), "ublock-origin"],
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
    print("\nOK — all collect-amo fixture checks passed")


if __name__ == "__main__":
    main()
