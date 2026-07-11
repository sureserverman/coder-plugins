#!/usr/bin/env python3
"""collect-github — best-effort free metrics for the business `track` skill.

Given a repo path, derive its GitHub slug from the origin remote and collect the
metrics GitHub gives away for free — stars, total release-asset downloads, and
14-day clones — via the `gh` CLI. Emits ONE JSON document on stdout:

    {"repo": "<owner/name>|null", "collected": "<YYYY-MM-DD>",
     "values":  {"github.stars": N|null, "github.release_downloads": N|null,
                 "github.clones_14d": N|null},
     "reasons": {"<metric or _>": "<why it's null>"}}

Best-effort by contract: every source degrades to a null value + a reason
sentinel; the script exits 0 even when nothing could be collected (no remote, no
`gh`, not authenticated, rate-limited, no push access for traffic). Only a
usage error (missing path arg) exits non-zero. The `track` skill folds `values`
into metrics.md as the `github.*` entries and surfaces `reasons` to the operator.
"""
import datetime
import json
import re
import subprocess
import sys
import urllib.parse

METRICS = ["github.stars", "github.release_downloads", "github.clones_14d"]


def _redact(url):
    """Strip any userinfo before a URL is echoed in a reason — git remotes for CI
    mirrors commonly embed tokens, and reasons can land in the committed
    metrics.md. Scheme-INDEPENDENT: removes any `<userinfo>@` run whether or not
    a `//` precedes it, so scp-style (git@host:path) and no-scheme
    (oauth2:TOKEN@host:path) forms are redacted too, not just https://user@host."""
    return re.sub(r"[^/@\s]+@", "", url)


def run(cmd):
    """Run a command, return (stdout, None) or (None, short_reason)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return None, f"{cmd[0]} not found"
    except subprocess.TimeoutExpired:
        return None, f"{cmd[0]} timed out"
    if r.returncode != 0:
        reason = (r.stderr or r.stdout or "").strip().splitlines()
        return None, (reason[0] if reason else f"{cmd[0]} exit {r.returncode}")[:200]
    return r.stdout, None


def repo_slug(path):
    """owner/name from the origin remote, or (None, reason). Host-anchored: the
    remote's host must be exactly github.com (not a substring), so a
    notgithub.com or a mirror path can't be mis-attributed as real GitHub."""
    out, err = run(["git", "-C", path, "remote", "get-url", "origin"])
    if err:
        return None, "no git remote (origin)"
    url = out.strip()
    scp = re.match(r"^[\w.+-]+@([^:/]+):(.+)$", url)   # git@github.com:owner/repo.git
    if scp and "//" not in url:
        host, pathpart = scp.group(1), scp.group(2)
    else:
        parts = urllib.parse.urlsplit(url)
        host = parts.netloc.rsplit("@", 1)[-1]         # drop userinfo
        host = host.rsplit(":", 1)[0] if ":" in host else host   # drop :port
        pathpart = parts.path
    if host.lower() != "github.com":
        return None, f"origin is not a GitHub remote ({_redact(url)[:80]})"
    segs = [s for s in pathpart.strip("/").split("/") if s]
    if len(segs) < 2:
        return None, f"origin path is not owner/repo ({_redact(url)[:80]})"
    owner, repo = segs[0], segs[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"{owner}/{repo}", None


def gh_ready():
    _, err = run(["gh", "auth", "status"])
    if err:
        return "gh unavailable or not authenticated"
    return None


def get_stars(slug):
    out, err = run(["gh", "repo", "view", slug, "--json", "stargazerCount"])
    if err:
        return None, f"stars: {err}"
    try:
        parsed = json.loads(out)
        if not isinstance(parsed, dict) or "stargazerCount" not in parsed:
            return None, "stars: unexpected response shape"
        return int(parsed["stargazerCount"]), None
    except (ValueError, TypeError) as e:
        return None, f"stars: unexpected response ({e})"


def get_release_downloads(slug):
    out, err = run(["gh", "api", "--paginate", f"repos/{slug}/releases"])
    if err:
        return None, f"release_downloads: {err}"
    try:
        releases = json.loads(out)
        if not isinstance(releases, list):   # e.g. a {"message": "Not Found"} envelope
            return None, "release_downloads: unexpected response shape"
        total = sum(int(a.get("download_count", 0))
                    for rel in releases if isinstance(rel, dict)
                    for a in rel.get("assets", []) if isinstance(a, dict))
        return total, None
    except (ValueError, TypeError) as e:
        return None, f"release_downloads: unexpected response ({e})"


def get_clones(slug):
    # traffic/clones requires push access — 403 for repos you don't own.
    out, err = run(["gh", "api", f"repos/{slug}/traffic/clones"])
    if err:
        low = err.lower()
        if "403" in err or "must have push" in low or "forbidden" in low:
            return None, "clones_14d: needs push access to the repo"
        return None, f"clones_14d: {err}"
    try:
        parsed = json.loads(out)
        if not isinstance(parsed, dict):     # `null`, an array, or a scalar
            return None, "clones_14d: unexpected response shape"
        return int(parsed.get("count", 0)), None
    except (ValueError, TypeError) as e:
        return None, f"clones_14d: unexpected response ({e})"


def collect(path):
    values = {m: None for m in METRICS}
    reasons = {}
    slug, err = repo_slug(path)
    if err:
        reasons["_"] = err
        return {"repo": None, "collected": datetime.date.today().isoformat(),
                "values": values, "reasons": reasons}
    gh_err = gh_ready()
    if gh_err:
        reasons["_"] = gh_err
        return {"repo": slug, "collected": datetime.date.today().isoformat(),
                "values": values, "reasons": reasons}
    for key, fn in (("github.stars", get_stars),
                    ("github.release_downloads", get_release_downloads),
                    ("github.clones_14d", get_clones)):
        val, reason = fn(slug)
        values[key] = val
        if reason:
            reasons[key] = reason
    return {"repo": slug, "collected": datetime.date.today().isoformat(),
            "values": values, "reasons": reasons}


def main(argv):
    if len(argv) != 2:
        sys.exit("usage: collect-github.py <repo_path>")
    json.dump(collect(argv[1]), sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main(sys.argv)
