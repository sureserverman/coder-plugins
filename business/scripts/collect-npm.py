#!/usr/bin/env python3
"""collect-npm — best-effort free npm metrics for the business `track` skill.

Given an npm package name OR a repo path containing a package.json, collects
what the public npm APIs give away for free — weekly and monthly download
counts (api.npmjs.org) and the published-version count (registry.npmjs.org),
neither of which needs authentication. Emits ONE JSON document on stdout:

    {"package": "<name>|null", "collected": "<YYYY-MM-DD>",
     "values":  {"npm.downloads_last_week": N|null,
                 "npm.downloads_last_month": N|null,
                 "npm.versions": N|null},
     "reasons": {"<metric or _>": "<why it's null>"}}

Best-effort by contract (references/collector-contract.md): every source
degrades to a null value + a reason sentinel; the script exits 0 even when
nothing could be collected (no package.json, unknown package, network down,
rate-limited). Only a usage error (wrong argument count) exits non-zero. The
`track` skill folds `values` into metrics.md as the `npm.*` entries and
surfaces `reasons` to the operator.
"""
import importlib.util
import json
import re
import sys
import urllib.parse
from pathlib import Path

_HELPER = Path(__file__).resolve().parent / "_collector.py"
_spec = importlib.util.spec_from_file_location("_collector", _HELPER)
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)

METRICS = ["npm.downloads_last_week", "npm.downloads_last_month", "npm.versions"]

# npm's published name grammar: an optional @scope/ prefix, then a name of
# URL-safe characters. Deliberately not permissive — see resolve_package.
# `\Z`, not `$`: Python's `$` also matches immediately before ONE trailing
# newline, so `left-pad\n` would validate and carry a raw newline into the
# `package` subject field — and metrics.md is a line-oriented format, where an
# embedded newline can split or fabricate a line.
NPM_NAME_RE = re.compile(r"^(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*\Z",
                         re.IGNORECASE)
NPM_NAME_MAX = 214          # npm's published limit

# Test seam: the suite points these at a localhost stub so CI never makes a live
# call. Unset in normal use — the real public endpoints are the defaults, and a
# non-loopback override is refused (see _collector.test_base).
_DL_DEFAULT = "https://api.npmjs.org"
_REG_DEFAULT = "https://registry.npmjs.org"
DOWNLOADS_API = (c.test_base("NPM_TEST_BASE", _DL_DEFAULT)
                 + "/downloads/point/{period}/{pkg}")
REGISTRY_API = c.test_base("NPM_TEST_BASE", _REG_DEFAULT) + "/{pkg}"


def _probe(path, method):
    """Call Path.is_dir()/exists(), treating ANY OSError as "not a path".

    `Path.is_dir()` only swallows a fixed set of errnos (ENOENT, ENOTDIR,
    EBADF, ELOOP); an over-long name raises ENAMETOOLONG straight through,
    which crashed the collector on a 500-char argument. A target the OS cannot
    even stat is, for our purposes, simply not a directory.
    """
    try:
        return getattr(path, method)()
    except OSError:
        return False


def resolve_package(target):
    """(package_name, None) or (None, reason).

    Accepts a bare package name or a repo path holding a package.json, so the
    caller can pass the same project path it passes collect-github.py rather
    than having to know the published name.
    """
    # Every reason in this function echoes the target, so redact ONCE up front
    # rather than at each branch: classifying by shape and redacting only the
    # branches that "look like" a URL is what let a bare `user:TOKEN@host`
    # target reach a committed metrics.md unredacted.
    safe = c.redact(target)[:60]
    if not target:
        # `Path("").is_dir()` is True (it is `.`), so without this guard an
        # unset caller variable silently resolves against the CWD and reports
        # some unrelated project's downloads as this project's.
        return None, "no package name or repo path given (empty target)"
    if len(target) > NPM_NAME_MAX and not _probe(Path(target), "is_dir"):
        # npm caps a published name at 214 chars. Checked before any filesystem
        # probe so an absurd argument is refused by rule, not by an OS error.
        return None, f"target is {len(target)} chars; npm names are ≤{NPM_NAME_MAX}"
    p = Path(target)
    if _probe(p, "is_dir"):
        manifest = p / "package.json"
        if not manifest.is_file():
            return None, f"no package.json in {safe}"
        try:
            data = json.loads(manifest.read_text(errors="replace"))
        except (ValueError, OSError) as e:
            return None, f"package.json unreadable ({str(e)[:60]})"
        if not isinstance(data, dict) or not data.get("name"):
            return None, "package.json has no name field"
        if data.get("private") is True:
            # A private package is never on the registry; say so plainly rather
            # than reporting it as an unknown package.
            return None, f"{c.redact(str(data['name']))[:60]} is marked private in package.json"
        name = str(data["name"])
        # File contents are as untrusted as a CLI argument here: the caller is
        # invited to point this at any repo path, and this name becomes both the
        # `package` subject field and part of the outbound URL. Same grammar
        # check as the bare-name path — validation must not be asymmetric across
        # the two ways a name can arrive.
        if len(name) > NPM_NAME_MAX or not NPM_NAME_RE.match(name):
            return None, (f"package.json name {c.redact(name)[:60]} is not a "
                          f"valid npm package name")
        return name, None
    if _probe(p, "exists"):
        return None, f"{safe} is a file, not a package name or repo directory"
    # Not a path — treat as a package name. Match a real URL by SCHEME, not by
    # a bare "http" prefix: `http-server` and `httpolyglot` are real published
    # packages that a prefix test would permanently refuse to collect.
    scheme = urllib.parse.urlsplit(target).scheme
    if scheme in ("http", "https") or ("/" in target and not target.startswith("@")):
        return None, f"{safe} is not a package name or repo directory"
    # Validate against npm's actual name grammar rather than accepting whatever
    # is left. This is also the last redaction gap: an unvalidated target became
    # the document's `package` subject verbatim, so a `user:TOKEN@host` string
    # reached a committed metrics.md through the one field redaction can't
    # rewrite (it must stay the real name to be useful). A legal name has no
    # colon and no `@` except a leading scope, so such a target is rejected
    # here, not carried.
    if not NPM_NAME_RE.match(target):
        return None, f"{safe} is not a valid npm package name"
    return target, None


def _quote(pkg):
    """URL-encode a package name. Scoped names (@scope/pkg) keep their `@` but
    must have the slash encoded for the downloads API; unicode and spaces must
    be encoded too, or http.client raises outside every degrade path."""
    return c.quote_id(pkg, safe="@")


def get_downloads(pkg, period, key):
    url = DOWNLOADS_API.format(period=period, pkg=_quote(pkg))
    data, err = c.get_json(
        url, not_found_reason=f"package {c.redact(pkg)[:60]} not found on npm")
    if err:
        return None, f"{key}: {err}"
    if isinstance(data, dict) and data.get("error"):
        # The downloads API sometimes answers 200 with an error envelope.
        return None, f"{key}: {str(data['error'])[:80]}"
    if not isinstance(data, dict):
        return None, f"{key}: unexpected response shape"
    val, reason = c.dig(data, "downloads")
    # Prefix every reason with its metric key so it stays self-describing if
    # ever read apart from its dict key. collect-github.py does the same with
    # the BARE suffix ("stars: ..."); the full dotted key is used here because
    # a channel prefix is what disambiguates once several collectors' reasons
    # sit side by side in one metrics.md.
    return val, (f"{key}: {reason}" if reason else None)


def get_versions(pkg):
    url = REGISTRY_API.format(pkg=_quote(pkg))
    data, err = c.get_json(
        url, not_found_reason=f"package {c.redact(pkg)[:60]} not found on npm")
    if err:
        return None, f"npm.versions: {err}"
    if not isinstance(data, dict) or not isinstance(data.get("versions"), dict):
        return None, "npm.versions: unexpected response shape"
    return len(data["versions"]), None


def collect(target):
    pkg, err = resolve_package(target)
    if err:
        # Whole-collection failure: one reason explains every null at once.
        return c.document("package", None, METRICS, reasons={"_": err})
    values, reasons = {}, {}
    for key, period in (("npm.downloads_last_week", "last-week"),
                        ("npm.downloads_last_month", "last-month")):
        val, reason = get_downloads(pkg, period, key)
        values[key] = val
        if reason:
            reasons[key] = reason
    val, reason = get_versions(pkg)
    values["npm.versions"] = val
    if reason:
        reasons["npm.versions"] = reason
    return c.document("package", pkg, METRICS, values, reasons)


def main(argv):
    if len(argv) != 2:
        c.usage("usage: collect-npm.py <package-name-or-repo-path>")
    c.emit(collect(argv[1]))


if __name__ == "__main__":
    main(sys.argv)
