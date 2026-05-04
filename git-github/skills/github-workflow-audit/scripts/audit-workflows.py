#!/usr/bin/env python3
# github-workflow-audit audit-workflows.py — automated workflow checks
# Usage: ./audit-workflows.py [repo-root]
# Scans <root>/.github/workflows/*.yml and *.yaml.
# Exits 0 if no ERROR found, 1 otherwise, 2 on usage error.

import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: PyYAML not installed. Try: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

INJECTION_CONTEXTS = [
    "github.event.inputs",
    "github.event.pull_request.title",
    "github.event.pull_request.body",
    "github.event.pull_request.head.ref",
    "github.event.issue.title",
    "github.event.issue.body",
    "github.event.comment.body",
    "github.head_ref",
    "inputs.",
]

findings = []  # (severity, file, line, message)

def add(sev, file, line, msg):
    findings.append((sev, file, line, msg))

def get_latest_major(owner, repo):
    try:
        r = subprocess.run(
            ["curl", "-sI", "-o", "/dev/null", "-w", "%{url_effective}", "-L",
             "--max-time", "15",
             f"https://github.com/{owner}/{repo}/releases/latest"],
            capture_output=True, text=True, timeout=20,
        )
        eff = r.stdout.strip()
    except Exception:
        return None
    m = re.search(r"/tag/v?(\d+)(?:\.\d+)*", eff)
    if m:
        return int(m.group(1))
    return None

def load_workflows(root):
    wf_dir = root / ".github" / "workflows"
    if not wf_dir.is_dir():
        print(f"error: no .github/workflows/ under {root}", file=sys.stderr)
        sys.exit(2)
    files = sorted(list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml")))
    return files

def parse_workflow(path):
    raw = path.read_text()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        add("ERROR", path.name, getattr(e, "problem_mark", None) and e.problem_mark.line + 1 or 0,
            f"YAML parse error: {e}")
        return None, raw
    return data, raw

def line_of(raw, needle, default=0):
    for i, line in enumerate(raw.splitlines(), 1):
        if needle in line:
            return i
    return default

def iter_steps(data):
    jobs = data.get("jobs", {}) or {}
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", []) or []
        for idx, step in enumerate(steps):
            if isinstance(step, dict):
                yield job_name, idx, step, job

def check_syntax(path, data, raw):
    if not data:
        return
    if "name" not in data:
        add("INFO", path.name, 1, "workflow has no name:")
    if "on" not in data and True not in data:
        add("ERROR", path.name, 1, "workflow has no on: trigger")
    jobs = data.get("jobs", {}) or {}
    if not jobs:
        add("WARN", path.name, 1, "workflow has no jobs")
    for jn, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if "runs-on" not in job and "uses" not in job:
            add("ERROR", path.name, line_of(raw, jn + ":"),
                f"job {jn!r} has neither runs-on: nor uses:")
    for _, _, step, _ in iter_steps(data):
        uses = step.get("uses")
        if uses and "@" not in uses and not uses.startswith("./"):
            add("ERROR", path.name, 0, f"uses: {uses!r} has no ref (@version)")

def check_action_versions(path, data, raw):
    seen = set()
    for _, _, step, _ in iter_steps(data):
        uses = step.get("uses", "")
        if not uses or uses.startswith("./") or "@" not in uses:
            continue
        spec, ref = uses.rsplit("@", 1)
        if "/" not in spec:
            continue
        if spec.count("/") > 1:
            owner_repo = "/".join(spec.split("/")[:2])
        else:
            owner_repo = spec
        if (owner_repo, ref) in seen:
            continue
        seen.add((owner_repo, ref))
        # Mutable refs
        if ref in ("main", "master", "develop", "HEAD"):
            add("WARN", path.name, line_of(raw, uses),
                f"{uses}: pinned to mutable branch — use a tag or SHA")
            continue
        m = re.match(r"^v?(\d+)(?:\.\d+){0,2}$", ref)
        if not m:
            continue
        current_major = int(m.group(1))
        owner, repo = owner_repo.split("/", 1)
        latest_major = get_latest_major(owner, repo)
        if latest_major and current_major < latest_major:
            add("WARN", path.name, line_of(raw, uses),
                f"{uses}: outdated (latest major v{latest_major})")

def check_security(path, data, raw):
    if not data:
        return
    # Expression injection in run: blocks
    for i, line in enumerate(raw.splitlines(), 1):
        for ctx in INJECTION_CONTEXTS:
            if "${{" in line and ctx in line:
                stripped = line.lstrip()
                if stripped.startswith("- run:") or stripped.startswith("run:"):
                    add("ERROR", path.name, i,
                        f"expression injection: {ctx} used in run: (line uses shell)")
                elif ":" in stripped and not stripped.startswith("#"):
                    # env or with — medium risk if passed to shell downstream
                    add("WARN", path.name, i,
                        f"context {ctx} interpolated — ensure downstream consumer treats as untrusted")
                    break
    # Broad permissions
    perms = data.get("permissions")
    if perms == "write-all":
        add("WARN", path.name, line_of(raw, "permissions:"), "permissions: write-all (use least-privilege)")
    if perms is None:
        jobs = data.get("jobs", {}) or {}
        if jobs and not any(isinstance(j, dict) and "permissions" in j for j in jobs.values()):
            add("INFO", path.name, 1, "no permissions: block — defaults to broad token scope")
    # Secret echo
    for i, line in enumerate(raw.splitlines(), 1):
        if re.search(r"\becho\s+.*\$\{\{\s*secrets\.", line):
            add("ERROR", path.name, i, "secret echoed to log")
    # Hardcoded-looking credentials (very loose)
    for i, line in enumerate(raw.splitlines(), 1):
        if re.search(r"(api[_-]?key|token|password|secret)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}", line, re.I):
            if "secrets." not in line and "inputs." not in line:
                add("WARN", path.name, i, "possible hardcoded credential (review)")

def check_logic(path, data, raw):
    if not data:
        return
    # Malformed if: `${{ x }} == 'y'` instead of `${{ x == 'y' }}`
    for i, line in enumerate(raw.splitlines(), 1):
        m = re.search(r"if:\s*\$\{\{\s*[^}]+\}\}\s*==", line)
        if m:
            add("WARN", path.name, i, "if: expression appears malformed (comparison outside ${{ }})")
    # Same-step GITHUB_ENV use
    jobs = data.get("jobs", {}) or {}
    for jn, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", []) or []
        for idx, step in enumerate(steps):
            run = step.get("run") or ""
            if ">> $GITHUB_ENV" in run or ">> \"$GITHUB_ENV\"" in run:
                # Look for same-step use of a var set via GITHUB_ENV
                set_vars = re.findall(r'([A-Z_][A-Z0-9_]*)=.*>>\s*"?\$GITHUB_ENV"?', run)
                for v in set_vars:
                    body_after = run.split(">> $GITHUB_ENV", 1)
                    tail = body_after[1] if len(body_after) > 1 else ""
                    if re.search(rf"\${v}\b|\$\{{\s*env\.{v}\s*\}}", tail):
                        add("WARN", path.name, 0,
                            f"job {jn} step {idx}: {v} set via GITHUB_ENV and used in same step")
    # needs: referencing non-existent jobs
    job_names = set(jobs.keys())
    for jn, job in jobs.items():
        if not isinstance(job, dict):
            continue
        needs = job.get("needs")
        if isinstance(needs, str):
            needs = [needs]
        for dep in (needs or []):
            if dep not in job_names:
                add("ERROR", path.name, line_of(raw, f"needs:"), f"job {jn} needs: {dep!r} (not defined)")

def check_improvements(path, data, raw):
    if not data:
        return
    jobs = data.get("jobs", {}) or {}
    for jn, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if "uses" in job:
            continue  # reusable caller
        if "timeout-minutes" not in job:
            add("INFO", path.name, line_of(raw, jn + ":"), f"job {jn}: no timeout-minutes (default 360)")
    if "concurrency" not in data:
        add("INFO", path.name, 1, "no top-level concurrency: — duplicate runs possible")

def check_cross(files, parsed):
    # Reusable workflow coverage
    callers_ref = set()
    for path, (data, raw) in parsed.items():
        if not data:
            continue
        for _, _, step, _ in iter_steps(data):
            uses = step.get("uses", "")
            if uses.startswith("./.github/workflows/"):
                callers_ref.add(uses.split("/")[-1])
        for jn, job in (data.get("jobs") or {}).items():
            if isinstance(job, dict):
                u = job.get("uses", "")
                if isinstance(u, str) and u.startswith("./.github/workflows/"):
                    callers_ref.add(u.split("/")[-1])
    for path, (data, raw) in parsed.items():
        if not data:
            continue
        on = data.get("on") if isinstance(data.get("on"), dict) else (data.get(True) if isinstance(data.get(True), dict) else None)
        if on and "workflow_call" in on and path.name not in callers_ref:
            add("INFO", path.name, 1, "reusable workflow not referenced by any caller")

def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        sys.exit(2)
    files = load_workflows(root)
    if not files:
        print("no workflow files found")
        sys.exit(0)
    print(f"=== scanning {len(files)} workflow file(s) under {root} ===\n")
    parsed = {}
    for f in files:
        data, raw = parse_workflow(f)
        parsed[f] = (data, raw)
        check_syntax(f, data, raw)
        check_security(f, data, raw)
        check_logic(f, data, raw)
        check_improvements(f, data, raw)
    # Version check last (slowest — network calls)
    for f, (data, raw) in parsed.items():
        if data:
            check_action_versions(f, data, raw)
    check_cross(files, parsed)

    # Output
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    findings.sort(key=lambda x: (order.get(x[0], 9), x[1], x[2]))
    print("| #  | Severity | File | Line | Issue |")
    print("|----|----------|------|------|-------|")
    for i, (sev, file, line, msg) in enumerate(findings, 1):
        print(f"| {i} | {sev} | {file} | {line} | {msg} |")
    errs = sum(1 for s, *_ in findings if s == "ERROR")
    warns = sum(1 for s, *_ in findings if s == "WARN")
    infos = sum(1 for s, *_ in findings if s == "INFO")
    print(f"\nERRORS: {errs}   WARNINGS: {warns}   INFO: {infos}")
    print("\nNote: sections covered automatically — YAML parse, job/step structure, action-version currency,")
    print("expression injection, mutable refs, secret echoes, malformed if:, needs DAG, timeouts/concurrency.")
    print("Re-read SKILL.md for manual checks needing judgment (reusable workflow input/secret matching,")
    print("artifact name uniqueness across jobs, continue-on-error intent, parallelization opportunities).")
    sys.exit(1 if errs else 0)

if __name__ == "__main__":
    main()
