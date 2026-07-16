#!/usr/bin/env python3
"""repo-health-scan — deterministic evidence lane for the repo-health skill.

Walks ~/.claude/projects-registry.yaml and, per enabled project with a GitHub
remote, gathers the upstream health evidence the repo-health SKILL.md
triages: latest workflow-run conclusion per workflow on the default branch,
open issues, stale open PRs, and open Dependabot alerts — all via the `gh`
CLI. When the portfolio vault is configured it also cross-checks each
project's backlog.md for already-filed GitHub URLs, marking findings as
triaged and flagging zombie BL entries whose upstream item has closed.
Emits ONE JSON document on stdout.

Read-only by construction: never writes under the vault or any repo.
Projects that cannot be assessed land in `couldnt_assess` with a reason;
projects without a GitHub remote land in `no_remote` — never silently
dropped. No LLM in this lane; judgment lives in SKILL.md.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

STALE_PR_DAYS_DEFAULT = 14
ISSUE_LIMIT = 100
PR_LIMIT = 100
RUN_LIMIT = 50
RED_CONCLUSIONS = {"failure", "timed_out", "startup_failure", "action_required"}

GITHUB_REMOTE_RE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$"
)
# Issue/PR URLs inside a backlog.md; GitHub's issues API serves both kinds.
BACKLOG_URL_RE = re.compile(
    r"https://github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)/(?:issues|pull)/(?P<num>\d+)"
)
BL_HEADER_RE = re.compile(r"^##\s+(BL-\d{3})\s+—", re.M)


def config_paths():
    home = Path.home()
    return home / ".claude" / "portfolio-config.yaml", home / ".claude" / "projects-registry.yaml"


def load_env():
    """Registry is required; vault_dir is optional (backlog cross-check only)."""
    config, registry = config_paths()
    if not registry.exists():
        sys.exit(f"portfolio not configured: {registry} missing")
    reg = yaml.safe_load(registry.read_text()) or {}
    if not isinstance(reg, dict) or "projects" not in reg:
        sys.exit(f"portfolio not configured: {registry} has no 'projects' key")
    vault = None
    if config.exists():
        cfg = yaml.safe_load(config.read_text()) or {}
        vd = cfg.get("vault_dir")
        if vd:
            vault = Path(vd)
    return vault, [p for p in reg["projects"] if p.get("enabled", True)]


def run(cmd, timeout=60):
    """Run a command; return (rc, stdout, stderr). Never raises on rc != 0."""
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return cp.returncode, cp.stdout.strip(), cp.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return -1, "", str(e)


def gh_json(args, timeout=60):
    """gh call expected to print JSON. Returns (data, error)."""
    rc, out, err = run(["gh"] + args, timeout=timeout)
    if rc != 0:
        return None, (err or out or f"gh exited {rc}").splitlines()[0]
    try:
        return json.loads(out) if out else None, None
    except json.JSONDecodeError:
        return None, "gh returned unparseable JSON"


def gh_text(args, timeout=60):
    """gh call with --jq, which prints a raw (unquoted) scalar. Returns (text, error)."""
    rc, out, err = run(["gh"] + args, timeout=timeout)
    if rc != 0:
        return None, (err or out or f"gh exited {rc}").splitlines()[0]
    return out or None, None


def parse_remote(path):
    """(owner, repo) of the project's GitHub remote, or (None, reason)."""
    rc, out, _ = run(["git", "-C", path, "remote", "get-url", "origin"])
    if rc != 0:
        rc2, remotes, _ = run(["git", "-C", path, "remote"])
        first = remotes.splitlines()[0] if rc2 == 0 and remotes else None
        if not first:
            return None, "no git remote"
        rc, out, _ = run(["git", "-C", path, "remote", "get-url", first])
        if rc != 0:
            return None, "no readable remote URL"
    m = GITHUB_REMOTE_RE.match(out)
    if not m:
        return None, f"non-GitHub remote: {out}"
    return (m.group("owner"), m.group("repo")), None


def age_days(iso, now):
    try:
        then = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (now - then).days
    except (ValueError, AttributeError):
        return None


def latest_run_per_workflow(runs):
    """gh run list is newest-first; keep the first (latest) run per workflow."""
    seen = {}
    for r in runs:
        name = r.get("workflowName") or "(unnamed workflow)"
        if name not in seen:
            seen[name] = {
                "workflow": name,
                "conclusion": r.get("conclusion") or None,
                "status": r.get("status"),
                "url": r.get("url"),
                "created": r.get("createdAt"),
            }
    return sorted(seen.values(), key=lambda w: w["workflow"])


def scan_ci(slug):
    data, err = gh_json([
        "run", "list", "-R", slug, "--limit", str(RUN_LIMIT),
        "--json", "workflowName,conclusion,status,url,createdAt,headBranch",
    ])
    if err:
        return {"error": err}
    default_branch, dberr = gh_text(["api", f"repos/{slug}", "--jq", ".default_branch"])
    branch_runs = [r for r in data or []
                   if not default_branch or r.get("headBranch") == default_branch]
    workflows = latest_run_per_workflow(branch_runs)
    red = [w for w in workflows if w["conclusion"] in RED_CONCLUSIONS]
    return {
        "default_branch": default_branch if not dberr else None,
        "workflows": workflows,
        "red_count": len(red),
    }


def scan_issues(slug, now):
    data, err = gh_json([
        "issue", "list", "-R", slug, "--state", "open", "--limit", str(ISSUE_LIMIT),
        "--json", "number,title,createdAt,updatedAt,url,labels",
    ])
    if err:
        return {"error": err}
    items = [{
        "number": i["number"], "title": i["title"], "url": i["url"],
        "age_days": age_days(i.get("createdAt"), now),
        "labels": [lb.get("name") for lb in i.get("labels") or []],
    } for i in data or []]
    items.sort(key=lambda i: (-(i["age_days"] or 0), i["number"]))
    return {"open_count": len(items), "items": items}


def scan_prs(slug, now, stale_days):
    data, err = gh_json([
        "pr", "list", "-R", slug, "--state", "open", "--limit", str(PR_LIMIT),
        "--json", "number,title,createdAt,updatedAt,url,isDraft",
    ])
    if err:
        return {"error": err}
    stale = []
    for p in data or []:
        idle = age_days(p.get("updatedAt"), now)
        if idle is not None and idle >= stale_days:
            stale.append({
                "number": p["number"], "title": p["title"], "url": p["url"],
                "draft": p.get("isDraft", False), "idle_days": idle,
                "age_days": age_days(p.get("createdAt"), now),
            })
    stale.sort(key=lambda p: -p["idle_days"])
    return {"open_count": len(data or []), "stale": stale, "stale_days": stale_days}


def scan_security(slug):
    data, err = gh_json(
        ["api", f"repos/{slug}/dependabot/alerts?state=open&per_page=100"])
    if err:
        # 403/404 when alerts are disabled or the token lacks scope — degrade, don't drop
        return {"error": err}
    by_severity = {}
    for a in data or []:
        sev = ((a.get("security_advisory") or {}).get("severity") or "unknown").lower()
        by_severity[sev] = by_severity.get(sev, 0) + 1
    return {"open_count": len(data or []), "by_severity": by_severity}


def backlog_refs(vault, proj, slug):
    """GitHub issue/PR URLs already filed in this project's backlog.md,
    grouped under their BL id. Returns [] when the vault or file is absent."""
    if vault is None:
        return []
    bpath = vault / "Portfolio" / proj.get("area", "") / proj["name"] / "backlog.md"
    if not bpath.is_file():
        return []
    text = bpath.read_text(errors="ignore")
    refs = []
    sections = list(BL_HEADER_RE.finditer(text))
    for i, m in enumerate(sections):
        body = text[m.end(): sections[i + 1].start() if i + 1 < len(sections) else len(text)]
        for um in BACKLOG_URL_RE.finditer(body):
            if f"{um.group('owner')}/{um.group('repo')}" == slug:
                refs.append({"bl_id": m.group(1), "url": um.group(0),
                             "number": int(um.group("num"))})
    return refs


def upstream_state(slug, number):
    return gh_text(["api", f"repos/{slug}/issues/{number}", "--jq", ".state"])


def cross_check(project, refs, slug):
    """Mark findings already triaged into the backlog; flag zombie BL entries
    whose upstream item is closed."""
    open_urls = {i["url"] for i in project.get("issues", {}).get("items", [])}
    open_urls |= {p["url"] for p in project.get("prs", {}).get("stale", [])}
    open_numbers = {i["number"] for i in project.get("issues", {}).get("items", [])}
    zombies = []
    triaged = []
    for ref in refs:
        if ref["url"] in open_urls or ref["number"] in open_numbers:
            triaged.append(ref)
        else:
            state, err = upstream_state(slug, ref["number"])
            if state == "closed":
                zombies.append(ref)
            elif state == "open":
                triaged.append(ref)  # open upstream, just not in our windows
            else:
                zombies.append({**ref, "note": f"state unknown: {err}"})
    for issue in project.get("issues", {}).get("items", []):
        bl = next((r["bl_id"] for r in triaged if r["number"] == issue["number"]), None)
        if bl:
            issue["triaged_as"] = bl
    for pr in project.get("prs", {}).get("stale", []):
        bl = next((r["bl_id"] for r in triaged if r["url"] == pr["url"]), None)
        if bl:
            pr["triaged_as"] = bl
    return zombies


def scan_project(proj, vault, now, stale_days):
    """One project's health dict, or a (bucket, entry) tuple for the footers."""
    path = proj["path"]
    if not Path(path, ".git").exists():
        return ("couldnt_assess", {"name": proj["name"], "reason": "not a git repo"})
    remote, reason = parse_remote(path)
    if remote is None:
        return ("no_remote", {"name": proj["name"], "reason": reason})
    owner, repo = remote
    slug = f"{owner}/{repo}"
    out = {
        "name": proj["name"], "area": proj.get("area"), "path": path, "repo": slug,
        "ci": scan_ci(slug),
        "issues": scan_issues(slug, now),
        "prs": scan_prs(slug, now, stale_days),
        "security": scan_security(slug),
    }
    lane_errors = [k for k in ("ci", "issues", "prs") if "error" in out[k]]
    if len(lane_errors) == 3:
        first = out["ci"]["error"]
        return ("couldnt_assess",
                {"name": proj["name"], "reason": f"all gh lanes failed: {first}"})
    refs = backlog_refs(vault, proj, slug)
    out["backlog_zombies"] = cross_check(out, refs, slug) if refs else []
    return ("projects", out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", action="append", default=None,
                    help="limit the sweep to this registry project name (repeatable)")
    ap.add_argument("--stale-days", type=int, default=STALE_PR_DAYS_DEFAULT,
                    help=f"idle days before an open PR counts as stale (default {STALE_PR_DAYS_DEFAULT})")
    args = ap.parse_args()

    rc, _, err = run(["gh", "auth", "status"])
    if rc != 0:
        sys.exit(f"gh not authenticated: {err or 'run `gh auth login`'}")

    vault, projects = load_env()
    if args.project:
        wanted = set(args.project)
        missing = wanted - {p["name"] for p in projects}
        if missing:
            sys.exit(f"not in registry (or disabled): {', '.join(sorted(missing))}")
        projects = [p for p in projects if p["name"] in wanted]

    now = datetime.datetime.now(datetime.timezone.utc)
    result = {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stale_pr_days": args.stale_days,
        "backlog_cross_check": vault is not None,
        "projects": [], "no_remote": [], "couldnt_assess": [],
    }
    with ThreadPoolExecutor(max_workers=8) as pool:
        for bucket, entry in pool.map(
                lambda p: scan_project(p, vault, now, args.stale_days), projects):
            result[bucket].append(entry)
    for key in ("projects", "no_remote", "couldnt_assess"):
        result[key].sort(key=lambda e: e["name"])
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
