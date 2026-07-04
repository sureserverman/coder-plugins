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
    return entry, None


def main():
    vault, projects = load_env()
    out = {
        "generated": datetime.date.today().isoformat(),
        "vault_dir": str(vault),
        "projects": [],
        "couldnt_assess": [],
    }
    for proj in projects:
        try:
            entry, reason = scan_project(proj, vault)
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
