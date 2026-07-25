"""Shared primitives for the per-channel metric collectors (BL-002).

Implements the mechanical parts of `references/collector-contract.md` §2–§4 —
best-effort HTTP, reason accumulation, secret redaction, document emission — so
each `collect-<channel>.py` carries only its channel's endpoints and parsing.

THE REFERENCE DOC IS THE CONTRACT, not this module. `collect-github.py` predates
this helper and implements the same contract directly against the `gh` CLI; it
is deliberately not retrofitted (it has a passing suite, and rewriting a working
collector buys no behavior).
"""
import datetime
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "coder-plugins-business-collector/1.0 (+metrics collection)"
TIMEOUT = 20


def quote_id(ident, safe="@"):
    """Percent-encode a caller-supplied identifier for use in a URL path.

    MUST be used on every target before it is interpolated into an endpoint. A
    raw unicode or space-bearing target reaches http.client and raises
    (UnicodeEncodeError / InvalidURL) *outside* any degrade path, crashing a
    collector that the contract says must always exit 0. `@` stays literal so
    npm scoped names (@scope/pkg) and addon GUIDs survive unmangled.
    """
    return urllib.parse.quote(str(ident), safe=safe)


def test_base(env_var, default):
    """Resolve a collector's API base, honoring a LOOPBACK-ONLY test override.

    The suites point collectors at a localhost stub so CI never makes a live
    call. The override is restricted to loopback because collector output is
    written straight into a committed metrics.md: a stray `export
    NPM_TEST_BASE=…` left in a shell profile, or one set by anything hostile,
    would otherwise silently commit attacker-chosen numbers with nothing in the
    output to show the data did not come from the real API. A non-loopback
    value is ignored, loudly, on stderr — never silently honored.
    """
    base = os.environ.get(env_var)
    if not base:
        return default
    host = urllib.parse.urlsplit(base).hostname or ""
    if host in ("127.0.0.1", "::1", "localhost"):
        return base
    print(f"{env_var} ignored: {redact(base)[:60]} is not loopback; "
          f"using {default}", file=sys.stderr)
    return default


def redact(text):
    """Strip any `<userinfo>@` run before a URL or remote is echoed into a
    reason. Reasons land in a committed metrics.md, and targets/remotes commonly
    embed tokens. Scheme-INDEPENDENT so scp-style (git@host:path) and no-scheme
    (oauth2:TOKEN@host:path) forms are covered, not just https://user@host."""
    return re.sub(r"[^/@\s]+@", "", text)


def safe_label(text, limit=60):
    """Make an untrusted string safe to write into a reason.

    Redact, then COLLAPSE ALL WHITESPACE, then truncate. The whitespace step
    matters as much as redaction: `metrics.md` is line-oriented, so a newline
    inside a reason can split one bullet into two or fabricate a whole line —
    the same hazard the id grammars anchor with `\\Z` to avoid. Use this
    anywhere a caller-supplied or upstream-supplied value is echoed.
    """
    return re.sub(r"\s+", " ", redact(str(text))).strip()[:limit]


def get_json(url, not_found_reason=None):
    """Fetch and parse JSON. Returns (parsed, None) or (None, short_reason).

    Never raises: every failure mode of a public HTTP API — unreachable, 404,
    rate limit, HTML error page, truncated body — becomes a reason string, per
    the best-effort contract.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 404 and not_found_reason:
            return None, not_found_reason
        if e.code == 429:
            return None, "rate-limited by the API (HTTP 429)"
        return None, f"HTTP {e.code} from {redact(url)[:80]}"
    except urllib.error.URLError as e:
        return None, f"network unreachable ({str(e.reason)[:60]})"
    except (TimeoutError, OSError) as e:
        return None, f"network error ({str(e)[:60]})"
    except (UnicodeError, http.client.InvalidURL) as e:
        # Defense in depth behind quote_id(): a malformed URL raises these
        # *outside* the OSError/URLError families, so without this clause an
        # un-encoded target escapes every degrade path and exits non-zero —
        # the one thing the best-effort contract forbids. Belongs here, in the
        # shared helper, so future collectors inherit the guarantee.
        return None, f"malformed request URL ({type(e).__name__})"
    except http.client.HTTPException as e:
        # A response-side protocol failure (truncated body, bad chunking).
        # Kept SEPARATE from the URL case above — InvalidURL subclasses
        # HTTPException, so a single clause blamed the URL for what is really a
        # broken response, and the operator read a wrong explanation.
        return None, f"incomplete or invalid HTTP response ({type(e).__name__})"
    try:
        return json.loads(body), None
    except ValueError:
        # A valid-HTTP but non-JSON body (captive portal, HTML error page).
        return None, f"non-JSON response from {redact(url)[:80]}"


def dig(obj, *path, cast=int):
    """Pull a nested value, returning (value, None) or (None, reason).

    Upstream shape drift is expected, not exceptional: a missing key, a null, or
    a string where a number belongs all degrade to a reason instead of raising.
    """
    cur = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None, f"unexpected response shape (no {'.'.join(path)})"
        cur = cur[key]
    if cur is None:
        return None, f"{'.'.join(path)} was null"
    try:
        return cast(cur), None
    except (ValueError, TypeError):
        return None, f"{'.'.join(path)} was not a number ({str(cur)[:30]})"


def document(subject_key, subject, metrics, values=None, reasons=None):
    """Build the contract document: every known metric key present, null when
    uncollected, so a caller never distinguishes 'absent' from 'failed'."""
    out_values = {m: None for m in metrics}
    out_values.update(values or {})
    return {subject_key: subject,
            "collected": datetime.date.today().isoformat(),
            "values": out_values,
            "reasons": dict(reasons or {})}


def emit(doc):
    """Write the one JSON document to stdout. Nothing else goes to stdout."""
    json.dump(doc, sys.stdout, indent=1)
    print()


def usage(msg):
    """The ONLY non-zero exit path a collector has."""
    sys.exit(msg)
