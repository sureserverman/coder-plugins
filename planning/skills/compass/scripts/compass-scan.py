#!/usr/bin/env python3
"""compass-scan — deterministic evidence lane for the compass skill.

Walks ~/.claude/projects-registry.yaml and, per enabled project, gathers the
work-state evidence the compass SKILL.md ranks: in-flight plan state (reusing
the authoritative plan-parser regexes from portfolio-unify.py — one contract,
one implementation), backlog open/parked counts, maturity axis summary,
integration-graph edges, and git recency. Emits ONE JSON document on stdout.

Read-only by construction: never writes under the vault or any repo.
Projects that cannot be assessed land in `couldnt_assess` with a reason —
never silently dropped. No LLM in this lane; judgment lives in SKILL.md.
"""
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Reuse the authoritative plan-parser pieces from the portfolio skill (stable
# sibling layout inside the planning plugin). Hyphenated filename → importlib.
_UNIFY = Path(__file__).resolve().parents[2] / "portfolio" / "scripts" / "portfolio-unify.py"
_spec = importlib.util.spec_from_file_location("portfolio_unify", _UNIFY)
pu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pu)

import yaml  # noqa: E402  (after pu import, which also needs it)


def config_paths():
    home = Path.home()
    return home / ".claude" / "portfolio-config.yaml", home / ".claude" / "projects-registry.yaml"


def load_env():
    config, registry = config_paths()
    cfg = yaml.safe_load(config.read_text()) if config.exists() else {}
    vd = (cfg or {}).get("vault_dir")
    if not vd:
        sys.exit("portfolio not configured: set vault_dir in ~/.claude/portfolio-config.yaml")
    if not registry.exists():
        sys.exit(f"portfolio not configured: {registry} missing")
    reg = yaml.safe_load(registry.read_text()) or {}
    if not isinstance(reg, dict) or "projects" not in reg:
        sys.exit(f"portfolio not configured: {registry} has no 'projects' key")
    return Path(vd), [p for p in reg["projects"] if p.get("enabled", True)]


COMPLETED_RE = re.compile(r"^\*\*Completed:\*\*\s*(\S+)", re.M)
MASTER_HEAD_RE = re.compile(r"^#\s+Master Plan:", re.M)


def plan_state(text, fname):
    """State of one executing-plans plan file, via the authoritative Status
    path (portfolio-unify regexes). Returns None for master plans (register
    format — no Task context, tracked through their sub-plans instead)."""
    # Master detection is deliberately explicit (filename AND heading), unlike
    # portfolio-unify's implicit skip (Sub-plan headers never match TASK_RE):
    # without this filter a master would fall into the "legacy/malformed"
    # degrade branch below and emit a spurious active/stage-unknown entry.
    if fname.endswith("-master-plan.md") or MASTER_HEAD_RE.search(text):
        return None
    cm = COMPLETED_RE.search(text)
    tasks = []          # (stage, num, desc, done)
    cur_stage = None
    cur_task = None
    for line in text.splitlines():
        sh = pu.STAGEHDR_RE.match(line)
        if sh:
            cur_stage = int(sh.group(1))
        tm = pu.TASK_RE.match(line)
        if tm:
            cur_task = (cur_stage, tm.group(1), tm.group(2).strip())
        sm = pu.STATUS_RE.match(line)
        if sm and cur_task:
            tasks.append(cur_task + (sm.group(1) != " ",))
            cur_task = None
    state = {"file": fname, "active": True, "stage": None, "next_task": None,
             "done": sum(1 for t in tasks if t[3]), "total": len(tasks),
             "completed": cm.group(1) if cm else None, "note": None}
    if not tasks:
        # legacy/malformed plan: degrade, never drop
        state["active"] = not cm
        state["note"] = "stage unknown (no parseable Status fields)"
        return state
    open_tasks = [t for t in tasks if not t[3]]
    if open_tasks:
        stage, num, desc, _ = open_tasks[0]
        state["stage"] = stage
        state["next_task"] = f"Task {num}: {desc}"
        if cm:
            state["note"] = f"completed marker present but {len(open_tasks)} task(s) still open"
    else:
        state["active"] = False
        if not cm:
            state["note"] = "all tasks done but no close-out line"
    return state


def collect_plans(home):
    plans_dir = home / "plans"
    if not plans_dir.is_dir():
        return []
    out = []
    for pf in sorted(plans_dir.glob("*-plan.md")):
        st = plan_state(pf.read_text(errors="ignore"), pf.name)
        if st is not None:
            out.append(st)
    return out


PARKED_RE = re.compile(r"^\s*-\s*\*\*Parked:\*\*\s*(.+)$", re.I | re.M)
AXIS_RE = re.compile(r"^##\s+(.+)$")
MBOX_RE = re.compile(r"^\s*-\s*\[(x|X| |N/A)\]", re.I)
EDGE_RE = re.compile(r"^-\s*`([^`]+)`\s*→\s*`([^`]+)`\s*—\s*(.*)$")


def collect_git(path):
    r = subprocess.run(["git", "-C", str(path), "log", "-1", "--format=%ct"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, "git: " + (r.stderr.strip().splitlines() or ["not a git repository"])[0]
    ts = int(r.stdout.strip())
    # %ct is a UTC epoch; convert in UTC so age_days is host-TZ-independent
    utc = datetime.timezone.utc
    last = datetime.datetime.fromtimestamp(ts, tz=utc).date()
    today = datetime.datetime.now(tz=utc).date()
    return {"last_commit": last.isoformat(),
            "age_days": (today - last).days}, None


def collect_backlog(home):
    f = home / "backlog.md"
    if not f.exists():
        return {"open": 0, "parked": 0, "parked_items": []}
    parked_items = []
    open_n = parked_n = 0
    for block in f.read_text(errors="ignore").split("\n## ")[1:]:
        m = re.match(r"BL-\d+\s*—\s*(.+)", block)
        if not m:
            continue
        open_n += 1
        pm = PARKED_RE.search(block)
        if pm:
            parked_n += 1
            parked_items.append({"title": m.group(1).strip(),
                                 "note": pm.group(1).strip()})
    return {"open": open_n, "parked": parked_n, "parked_items": parked_items}


def collect_maturity(home):
    f = home / "MATURITY.md"
    if not f.exists():
        return None
    axes = {}
    cur = None
    for line in f.read_text(errors="ignore").splitlines():
        am = AXIS_RE.match(line)
        if am:
            cur = am.group(1).strip()
            axes[cur] = {"done": 0, "open": 0, "na": 0}
            continue
        bm = MBOX_RE.match(line)
        if bm and cur:
            mark = bm.group(1).lower()
            key = "done" if mark == "x" else ("na" if mark == "n/a" else "open")
            axes[cur][key] += 1
    axes = {k: v for k, v in axes.items() if sum(v.values())}
    return {"axes": axes,
            "done": sum(a["done"] for a in axes.values()),
            "open": sum(a["open"] for a in axes.values())}


def load_edges(vault):
    """Parse integration-graph.md once: list of (dependent, upstream, why)."""
    f = vault / "Portfolio" / "integration-graph.md"
    if not f.exists():
        return []
    edges = []
    for line in f.read_text(errors="ignore").splitlines():
        em = EDGE_RE.match(line.strip())
        if em:
            edges.append((em.group(1), em.group(2), em.group(3).strip()))
    return edges


def scan_project(proj, vault):
    """Assess one registry project. Returns (entry, None) or (None, reason)."""
    path = Path(proj["path"])
    if not path.exists():
        return None, "path does not exist"
    entry = {
        "name": proj["name"],
        "area": proj["area"],
        "path": str(path),
        "errors": [],
    }
    home = vault / "Portfolio" / proj["area"] / proj["name"]
    collectors = {
        "plans": (lambda: collect_plans(home), []),
        "backlog": (lambda: collect_backlog(home),
                    {"open": 0, "parked": 0, "parked_items": []}),
        "maturity": (lambda: collect_maturity(home), None),
    }
    for key, (fn, fallback) in collectors.items():
        try:
            entry[key] = fn()
        except Exception as e:  # degrade per collector, never drop the project
            entry[key] = fallback
            entry["errors"].append(f"{key}: {e}")
    try:
        git_info, git_err = collect_git(path)
    except Exception as e:  # git binary/exec failure degrades like any collector
        git_info, git_err = None, f"git: {e}"
    entry["git"] = git_info
    if git_err:
        entry["errors"].append(git_err)
    return entry, None


def business_map():
    """Optional business-plugin state keyed by project name — {} when the plugin
    isn't installed alongside (additive: compass works identically without it).
    BUSINESS_SCAN_PATH overrides the probe (used to force the layer off in tests).

    NEVER raises: the business layer is optional and independently versioned, so
    ANY failure (missing plugin, nonzero exit, timeout, malformed/unexpected-shape
    JSON) degrades to {} — a broken business scanner must not take down compass's
    plan/backlog/maturity evidence."""
    root = Path(__file__).resolve().parents[4]          # marketplace root
    scan = Path(os.environ.get("BUSINESS_SCAN_PATH")
                or root / "business" / "scripts" / "business-scan.py")
    if not scan.exists():
        return {}
    try:
        r = subprocess.run([sys.executable, str(scan)], capture_output=True,
                           text=True, timeout=120)
        if r.returncode != 0:
            return {}
        doc = json.loads(r.stdout)
        if not isinstance(doc, dict):
            return {}
        out = {}
        for p in doc.get("projects", []):
            if not isinstance(p, dict) or not p.get("name") or not p.get("assessed"):
                continue
            gtm = p.get("gtm") if isinstance(p.get("gtm"), dict) else None
            model = (p.get("monetization") or {}).get("model") \
                if isinstance(p.get("monetization"), dict) else None
            research = p.get("research") if isinstance(p.get("research"), dict) else None
            plan = p.get("plan") if isinstance(p.get("plan"), dict) else None
            out[p["name"]] = {
                "verdict": p.get("verdict"),
                "model": model,
                "gtm_pct": gtm.get("pct") if gtm else None,
                "last_reviewed_age_days": p.get("last_reviewed_age_days"),
                # research/plan age (days) when the artifact exists, else None — so compass
                # can flag stale market-research/plan alongside stale review. Additive.
                "research_age_days": research.get("age_days")
                    if research and research.get("exists") else None,
                "plan_age_days": plan.get("age_days")
                    if plan and plan.get("exists") else None,
                "stage": ("tracked" if p.get("metrics") else "launched" if gtm
                          else "modeled" if model else "assessed"),
            }
        return out
    except Exception:      # timeout, JSON error, unexpected shape — degrade to no layer
        return {}


def main():
    vault, projects = load_env()
    out = {
        "generated": datetime.date.today().isoformat(),
        "vault_dir": str(vault),
        "projects": [],
        "couldnt_assess": [],
    }
    edges = load_edges(vault)
    biz = business_map()            # {} when business plugin absent → no per-project key
    for proj in projects:
        try:
            entry, reason = scan_project(proj, vault)
            if entry is not None:
                name = entry["name"]
                entry["dependents"] = [
                    {"project": a, "why": w} for a, b, w in edges if b == name]
                entry["depends_on"] = [
                    {"project": b, "why": w} for a, b, w in edges if a == name]
                if name in biz:
                    entry["business"] = biz[name]
        except Exception as e:  # a broken project must not abort the sweep
            entry, reason = None, f"scan error: {e}"
        if entry is None:
            out["couldnt_assess"].append(
                {"name": proj["name"], "area": proj["area"],
                 "path": proj["path"], "reason": reason})
        else:
            out["projects"].append(entry)
    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
