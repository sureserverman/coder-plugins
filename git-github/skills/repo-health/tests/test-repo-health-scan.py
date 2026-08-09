#!/usr/bin/env python3
"""Fixture suite for repo-health-scan.py — run directly (CI convention):
    python3 git-github/skills/repo-health/tests/test-repo-health-scan.py

Builds a throwaway HOME with a portfolio-config + registry pointing at
temp git repos, puts a fake `gh` shim on PATH serving canned JSON, runs
the scanner as a subprocess, and asserts the JSON contract: envelope keys,
unconfigured error, remote partitioning (github / no_remote /
couldnt_assess), CI default-branch filtering, issue/PR/security lanes,
backlog cross-check (triaged_as + zombies), --project filter, and the
read-only guarantee.
"""
import datetime
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "repo-health-scan.py"

# All fixture timestamps below are expressed as offsets from NOW rather than
# baked-in calendar dates, so the suite stays green no matter when it runs.
# REPO_HEALTH_NOW (the scan script's NOW-injection seam) lets this same
# mechanism prove the fixture also holds with the clock advanced a year —
# see the year-ahead check in main(). Absent that override, NOW is real time,
# captured once so the fixture builder, the fake `gh` shim subprocess, and
# the scanner subprocess all agree on exactly the same instant.
_NOW_OVERRIDE = os.environ.get("REPO_HEALTH_NOW")
NOW = (datetime.datetime.fromisoformat(_NOW_OVERRIDE.replace("Z", "+00:00"))
       if _NOW_OVERRIDE else datetime.datetime.now(datetime.timezone.utc))
NOW_ISO = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")


def ago_date(days):
    """YYYY-MM-DD `days` before NOW, for backlog.md's date-only fields."""
    return (NOW - datetime.timedelta(days=days)).strftime("%Y-%m-%d")


FAILURES = []


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


def tree_digest(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            h.update(p.as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


GH_SHIM = r'''#!/usr/bin/env python3
import datetime, json, os, sys
args = sys.argv[1:]

# Mirrors the outer test's NOW-relative fixture construction: reads the same
# REPO_HEALTH_NOW seam the scanner reads, so shim output and the scanner's
# own "now" always agree, whether that's real time or a test-injected one.
_now_override = os.environ.get("REPO_HEALTH_NOW")
NOW = (datetime.datetime.fromisoformat(_now_override.replace("Z", "+00:00"))
       if _now_override else datetime.datetime.now(datetime.timezone.utc))


def ago(days):
    return (NOW - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def out(x):
    print(json.dumps(x))
    sys.exit(0)


if args[:2] == ["auth", "status"]:
    sys.exit(0)
if args[:2] == ["run", "list"]:
    out([
        {"workflowName": "ci", "conclusion": "failure", "status": "completed",
         "url": "https://github.com/tester/alpha/actions/runs/3",
         "createdAt": ago(10), "headBranch": "main"},
        {"workflowName": "ci", "conclusion": "success", "status": "completed",
         "url": "https://github.com/tester/alpha/actions/runs/2",
         "createdAt": ago(19), "headBranch": "main"},
        {"workflowName": "release", "conclusion": "success", "status": "completed",
         "url": "https://github.com/tester/alpha/actions/runs/1",
         "createdAt": ago(30), "headBranch": "main"},
        {"workflowName": "feature-only", "conclusion": "failure", "status": "completed",
         "url": "https://github.com/tester/alpha/actions/runs/4",
         "createdAt": ago(9), "headBranch": "feat/x"},
    ])
if args[:2] == ["issue", "list"]:
    out([
        {"number": 1, "title": "Old bug", "createdAt": ago(80),
         "updatedAt": ago(79),
         "url": "https://github.com/tester/alpha/issues/1",
         "labels": [{"name": "bug"}]},
        {"number": 2, "title": "Fresh ask", "createdAt": ago(10),
         "updatedAt": ago(10),
         "url": "https://github.com/tester/alpha/issues/2", "labels": []},
    ])
if args[:2] == ["pr", "list"]:
    out([
        {"number": 5, "title": "Stale WIP", "createdAt": ago(49),
         "updatedAt": ago(40),
         "url": "https://github.com/tester/alpha/pull/5", "isDraft": True},
        {"number": 6, "title": "Fresh PR", "createdAt": ago(6),
         "updatedAt": ago(5),
         "url": "https://github.com/tester/alpha/pull/6", "isDraft": False},
    ])
if args[0] == "api":
    path = args[1]
    if "dependabot" in path:
        sys.stderr.write("HTTP 403: Dependabot alerts are disabled (dummy)")
        sys.exit(1)
    # gh --jq prints raw unquoted scalars, not JSON
    if path == "repos/tester/alpha" and "--jq" in args:
        print("main")
        sys.exit(0)
    if path == "repos/tester/alpha/issues/99" and "--jq" in args:
        print("closed")
        sys.exit(0)
sys.stderr.write("gh shim: unhandled args: %r" % (args,))
sys.exit(1)
'''

BACKLOG = f"""# Backlog

Deferred items.

---

## BL-001 — Fix the old bug

- **Opened:** {ago_date(49)}
- **Source:** github — https://github.com/tester/alpha/issues/1
- **Reason:** deferred
- **Next step:** plan
- **Tags:** gh-issue

---

## BL-002 — Chase closed thing

- **Opened:** {ago_date(80)}
- **Source:** github — https://github.com/tester/alpha/issues/99
- **Reason:** deferred
- **Next step:** plan
- **Tags:** gh-issue

---

## BL-003 — Fix red CI on main

- **Opened:** {ago_date(4)}
- **Source:** github — https://github.com/tester/alpha/actions/runs/3
- **Reason:** deferred
- **Next step:** triage
- **Tags:** gh-ci
"""


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd)] + list(args), check=True,
                   capture_output=True)


def run_scan(env, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT)] + list(extra),
        capture_output=True, text=True, env=env)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="repo-health-test-"))
    home = tmp / "home"
    vault = tmp / "vault"
    bindir = tmp / "bin"
    (home / ".claude").mkdir(parents=True)
    bindir.mkdir()

    shim = bindir / "gh"
    shim.write_text(GH_SHIM)
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)

    # alpha: github remote, full lanes; beta: non-github remote; gamma: not a repo
    alpha = tmp / "projects" / "alpha"
    beta = tmp / "projects" / "beta"
    gamma = tmp / "projects" / "gamma"
    for d in (alpha, beta, gamma):
        d.mkdir(parents=True)
    git(alpha, "init", "-q")
    git(alpha, "remote", "add", "origin", "git@github.com:tester/alpha.git")
    git(beta, "init", "-q")
    git(beta, "remote", "add", "origin", "https://gitlab.com/tester/beta.git")

    blog = vault / "Portfolio" / "ai-tools" / "alpha"
    blog.mkdir(parents=True)
    (blog / "backlog.md").write_text(BACKLOG)

    registry = home / ".claude" / "projects-registry.yaml"
    env = {**os.environ, "HOME": str(home),
           "PATH": f"{bindir}:{os.environ['PATH']}",
           "REPO_HEALTH_NOW": NOW_ISO}

    print("unconfigured:")
    cp = run_scan(env)
    check(cp.returncode != 0 and "portfolio not configured" in (cp.stderr + cp.stdout),
          "missing registry exits with 'portfolio not configured'")

    registry.write_text(f"""version: 1
projects:
  - {{path: {alpha}, name: alpha, area: ai-tools, enabled: true}}
  - {{path: {beta}, name: beta, area: ai-tools, enabled: true}}
  - {{path: {gamma}, name: gamma, area: ai-tools, enabled: true}}
  - {{path: {tmp}/nope, name: disabled-proj, area: ai-tools, enabled: false}}
""")
    (home / ".claude" / "portfolio-config.yaml").write_text(f"vault_dir: {vault}\n")

    before = tree_digest(tmp)
    print("full sweep:")
    cp = run_scan(env)
    check(cp.returncode == 0, f"scanner exits 0 (stderr: {cp.stderr[:200]})")
    doc = json.loads(cp.stdout)
    check(set(doc) >= {"generated", "stale_pr_days", "backlog_cross_check",
                       "projects", "no_remote", "couldnt_assess"},
          "envelope keys present")
    check(doc["backlog_cross_check"] is True, "vault configured -> cross-check on")
    check([p["name"] for p in doc["projects"]] == ["alpha"], "alpha assessed")
    check([p["name"] for p in doc["no_remote"]] == ["beta"], "beta -> no_remote")
    check("gitlab" in doc["no_remote"][0]["reason"], "no_remote cites the URL")
    check([p["name"] for p in doc["couldnt_assess"]] == ["gamma"],
          "gamma -> couldnt_assess")
    check("disabled-proj" not in cp.stdout, "disabled project skipped")

    a = doc["projects"][0]
    check(a["repo"] == "tester/alpha", "ssh remote parsed to owner/repo")
    ci = a["ci"]
    check(ci["default_branch"] == "main", "default branch resolved")
    names = [w["workflow"] for w in ci["workflows"]]
    check(names == ["ci", "release"], "latest run per workflow, default branch only")
    check(ci["red_count"] == 1, "one red workflow (latest ci run = failure)")
    red_wf = next(w for w in ci["workflows"] if w["conclusion"] == "failure")
    check(red_wf.get("triaged_as") == "BL-003",
          "red CI workflow deduped repo-level against a gh-ci backlog entry")

    iss = a["issues"]
    check(iss["open_count"] == 2, "two open issues")
    check(iss["items"][0]["number"] == 1, "issues sorted oldest-first")
    check(iss["items"][0].get("triaged_as") == "BL-001",
          "backlogged issue carries triaged_as")
    check("triaged_as" not in iss["items"][1], "untriaged issue unmarked")

    prs = a["prs"]
    check(prs["open_count"] == 2 and len(prs["stale"]) == 1
          and prs["stale"][0]["number"] == 5,
          "only the idle PR is stale")
    check("error" in a["security"], "dependabot 403 degrades to lane error")

    zombies = a["backlog_zombies"]
    check([z["bl_id"] for z in zombies] == ["BL-002"],
          "closed-upstream BL entry flagged as zombie")

    check(tree_digest(tmp) == before, "read-only: no file under HOME/vault/repos changed")

    print("--project filter:")
    cp = run_scan(env, "--project", "alpha")
    doc = json.loads(cp.stdout)
    check(cp.returncode == 0 and [p["name"] for p in doc["projects"]] == ["alpha"]
          and doc["no_remote"] == [], "--project scopes the sweep")
    cp = run_scan(env, "--project", "nope")
    check(cp.returncode != 0 and "not in registry" in cp.stderr,
          "unknown --project fails loudly")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
