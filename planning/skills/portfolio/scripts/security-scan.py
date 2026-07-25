#!/usr/bin/env python3
"""Sweep every registry project's security state into one JSON document.

Reads `<vault>/Portfolio/<area>/<name>/security/history.jsonl` — written by
sec-audit v1.29+ — for each enabled project and emits a normalised summary on
stdout for `security-rollup.py` to render.

The input contract is published by sec-audit's SKILL.md §1.5.1. Two rules from it
drive almost every decision here:

  * **Optional fields normalise to `null`, never `0`.** "We did not record this"
    and "this was zero" are different facts. A dashboard that renders a missing
    CRITICAL count as `0` reports a clean project that was never measured — the
    single most dangerous thing a security roll-up can do.
  * **`mode: "feeds"` means no code lane ran.** Its unchanged counts are NOT
    evidence the code was re-verified, so a feed-only check must never be
    presented as an audit.

Unknown keys and unknown enum values are passed through, never rejected: this
file lives in a different repo from its producer and must not break when
sec-audit adds a field.

A broken project never aborts the sweep — it lands in `couldnt_assess` with a
reason, because a roll-up that dies on one bad file tells you nothing about the
other thirty.

Pure stdlib + pyyaml (already required by portfolio-rebuild.py). No network.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

SUPPORTED_SCHEMA = 1
TREND_WINDOW = 5          # runs considered when computing a direction
CONFIG = Path.home() / ".claude" / "portfolio-config.yaml"
REGISTRY = Path.home() / ".claude" / "projects-registry.yaml"


def load_env():
    cfg_p = Path(os.environ.get("PORTFOLIO_CONFIG") or CONFIG)
    reg_p = Path(os.environ.get("SECURITY_REGISTRY") or REGISTRY)
    if not cfg_p.exists():
        sys.exit(f"portfolio not configured: {cfg_p} not found")
    cfg = yaml.safe_load(cfg_p.read_text()) or {}
    vd = cfg.get("vault_dir")
    if not vd:
        sys.exit("portfolio not configured: set vault_dir in ~/.claude/portfolio-config.yaml")
    if not reg_p.exists():
        sys.exit(f"portfolio not configured: {reg_p} not found")
    reg = yaml.safe_load(reg_p.read_text()) or {}
    if "projects" not in reg:
        sys.exit(f"portfolio not configured: {reg_p} has no `projects` key")
    return Path(vd), [p for p in reg["projects"] if p.get("enabled", True)]


def _read_runs(path):
    """Every parseable run record, oldest first. A malformed LINE is skipped and
    counted; a malformed FILE raises (the caller records couldnt_assess). Losing
    one line must not discard a project's whole history."""
    runs, bad = [], 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            if isinstance(rec, dict) and rec.get("run_id"):
                runs.append(rec)
            else:
                bad += 1
    runs.sort(key=lambda r: str(r.get("run_id")))
    return runs, bad


def _sev(counts, *names):
    """A severity count, or None when it was not recorded. Never coerces a
    missing value to 0 — see the module docstring."""
    if not isinstance(counts, dict):
        return None
    for n in names:
        for key in (n, n.upper(), n.lower(), n.capitalize()):
            if key in counts and isinstance(counts[key], (int, float)):
                return int(counts[key])
    return None


def _age_days(run, now):
    """Days since the run, from finished_at/started_at, else the run_id stamp."""
    for field in ("finished_at", "started_at"):
        v = run.get(field)
        if isinstance(v, str):
            try:
                d = datetime.fromisoformat(v.replace("Z", "+00:00"))
                if d.tzinfo is None:
                    d = d.replace(tzinfo=timezone.utc)
                return max(0, (now - d).days)
            except ValueError:
                pass
    rid = str(run.get("run_id") or "")
    try:
        d = datetime.strptime(rid[:13], "%Y%m%d-%H%M").replace(tzinfo=timezone.utc)
        return max(0, (now - d).days)
    except ValueError:
        return None


def _trend(runs):
    """Direction of open CRITICAL+HIGH over the last TREND_WINDOW runs.

    Only runs that actually recorded the counts are compared — an unrecorded run
    is skipped rather than read as zero. Fewer than two comparable points means
    no trend, not a flat one.
    """
    pts = []
    for r in runs[-TREND_WINDOW:]:
        c = _sev(r.get("counts"), "critical")
        h = _sev(r.get("counts"), "high")
        if c is None and h is None:
            continue
        pts.append((c or 0) + (h or 0))
    if len(pts) < 2:
        return None
    if pts[-1] > pts[0]:
        return "up"
    if pts[-1] < pts[0]:
        return "down"
    return "flat"


def scan_project(proj, vault, now):
    home = vault / "Portfolio" / proj["area"] / proj["name"]
    hist = home / "security" / "history.jsonl"
    base = {"name": proj["name"], "area": proj["area"], "path": proj.get("path")}
    if not hist.exists():
        reports = home / "security" / "reports"
        return {**base, "never_audited": True,
                # A reports dir with no history means a pre-v1.29 layout or a
                # partially-written state — worth saying, not worth guessing at.
                "note": "has security/reports but no history.jsonl"
                        if reports.is_dir() else None}
    runs, bad_lines = _read_runs(hist)
    if not runs:
        return {**base, "never_audited": True,
                "note": f"history.jsonl present but no usable records "
                        f"({bad_lines} malformed line(s))"}
    last = runs[-1]
    deltas = last.get("deltas") if isinstance(last.get("deltas"), dict) else {}
    counts = last.get("counts") if isinstance(last.get("counts"), dict) else {}
    accepted = deltas.get("accepted")
    total_open = deltas.get("total_open")
    if not isinstance(accepted, int):
        accepted = None
    if not isinstance(total_open, int):
        total_open = None
    return {
        **base,
        "never_audited": False,
        "runs": len(runs),
        "malformed_lines": bad_lines,
        "last_run_id": last.get("run_id"),
        # `mode` is passed through verbatim, including values this script does
        # not know — the vocabulary belongs to sec-audit, not here.
        "mode": last.get("mode"),
        "code_verified": last.get("mode") != "feeds",
        "age_days": _age_days(last, now),
        "plugin_version": last.get("plugin_version"),
        "critical": _sev(counts, "critical"),
        "high": _sev(counts, "high"),
        "medium": _sev(counts, "medium"),
        "low": _sev(counts, "low"),
        "total_open": total_open,
        "accepted": accepted,
        # "open and not currently suppressed" per §1.5.1; None unless BOTH known
        "unsuppressed_open": (total_open - accepted)
        if isinstance(total_open, int) and isinstance(accepted, int) else None,
        "trend": _trend(runs),
    }


def main():
    vault, projects = load_env()
    now = datetime.now(timezone.utc)
    out = {"generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "vault_dir": str(vault), "supported_schema": SUPPORTED_SCHEMA,
           "projects": [], "couldnt_assess": []}
    for p in sorted(projects, key=lambda x: (x.get("area", ""), x.get("name", ""))):
        try:
            out["projects"].append(scan_project(p, vault, now))
        except Exception as e:                     # never abort the sweep
            out["couldnt_assess"].append(
                {"name": p.get("name"), "area": p.get("area"),
                 "reason": f"{type(e).__name__}: {e}"})
    json.dump(out, sys.stdout, indent=1, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
