#!/usr/bin/env python3
"""business-scan — deterministic evidence lane for the business plugin.

Walks ~/.claude/projects-registry.yaml and, per enabled project, reads the
business artifacts under <vault_dir>/Portfolio/<area>/<name>/business/ and emits
ONE JSON document on stdout describing each project's business state:

    assessed, schema, verdict, audience, evidence, last_reviewed(+age),
    monetization, targets, latest metrics, gtm-plan progress, errors.

This is the SOLE parser of the business artifacts — every skill and every
planning-plugin integration consumes this JSON, never the markdown. gtm-plan
progress reuses portfolio-unify's CHECKED/UNCHECKED regexes (one contract, one
implementation). Read-only by construction: never writes under the vault or any
repo. Projects that raise land in `couldnt_assess` with a reason; per-project
parse problems land in that project's `errors` — never silently dropped, never
fatal to the sweep. No LLM in this lane; judgment lives in the skills.
"""
import datetime
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

# Reuse the authoritative checkbox regexes from the portfolio skill (stable
# sibling layout: business/ and planning/ are siblings under the marketplace
# root). Hyphenated filename → importlib.
_UNIFY = (Path(__file__).resolve().parents[2]
          / "planning" / "skills" / "portfolio" / "scripts" / "portfolio-unify.py")
_spec = importlib.util.spec_from_file_location("portfolio_unify", _UNIFY)
pu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pu)

import yaml  # noqa: E402  (after pu import, which also needs it)

SUPPORTED_SCHEMA = 1
VERDICTS = {"monetize", "free-for-reputation", "internal-only", "park"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")      # rejects inf/nan/text → JSON-safe


def config_paths():
    home = Path.home()
    return (home / ".claude" / "portfolio-config.yaml",
            home / ".claude" / "projects-registry.yaml")


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


def _isodate(v):
    """YAML auto-parses ISO dates to date/datetime; normalize to ISO string so
    the value is JSON-serializable and stable regardless of yaml's coercion."""
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()[:10] if isinstance(v, datetime.datetime) else v.isoformat()
    return v


def _normalize(obj):
    """Recursively stringify date/datetime so json.dump never chokes."""
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return _isodate(obj)
    if isinstance(obj, float) and not math.isfinite(obj):
        return None      # .nan/.inf anywhere (pricing, a target) → null, so the
                         # single JSON envelope stays RFC-8259 valid for every
                         # consumer (bare NaN/Infinity tokens break strict parsers)
    return obj


def parse_business_md(text):
    """Parse BUSINESS.md frontmatter. Returns (fields_dict, error_or_None).
    fields_dict is None when unparseable."""
    body = text.lstrip()
    if not body.startswith("---"):
        return None, "BUSINESS.md: no YAML frontmatter"
    # Anchor on delimiter LINES, not a raw "---" substring: a triple-dash inside
    # a free-text scalar (e.g. `audience: power users --- anyone`) must NOT
    # truncate the frontmatter and silently drop later fields.
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", body, re.S)
    if not m:
        return None, "BUSINESS.md: unterminated frontmatter"
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        msg = str(e).splitlines()[0] if str(e) else "invalid YAML"
        return None, f"BUSINESS.md: invalid frontmatter YAML ({msg})"
    if not isinstance(fm, dict):
        return None, "BUSINESS.md: frontmatter is not a mapping"
    schema = fm.get("schema")
    if schema is None:
        return None, "BUSINESS.md: missing 'schema'"
    if not isinstance(schema, int):
        return None, f"BUSINESS.md: 'schema' must be an integer, got {schema!r}"
    if schema > SUPPORTED_SCHEMA:
        return ({"schema": schema},
                f"BUSINESS.md: schema {schema} is newer than supported "
                f"({SUPPORTED_SCHEMA}) — upgrade the business plugin")
    verdict = fm.get("verdict")
    err = None
    if verdict not in VERDICTS:
        err = (f"BUSINESS.md: verdict {verdict!r} not one of "
               f"{sorted(VERDICTS)}")
    mon = fm.get("monetization") or {}
    if not isinstance(mon, dict):
        mon = {}
    fields = {
        "schema": schema,
        "verdict": verdict if verdict in VERDICTS else None,
        "audience": fm.get("audience"),
        "evidence": fm.get("evidence"),
        "last_reviewed": _isodate(fm.get("last_reviewed")),
        "monetization": {
            "model": mon.get("model"),
            "pricing": mon.get("pricing"),
            "channels": mon.get("channels") or [],
        },
        "targets": _normalize(fm.get("targets") or []),
    }
    return fields, err


def parse_metrics(text):
    """Latest dated block of metrics.md → {date, values} or None."""
    blocks = []          # (date_str, {key: value})
    cur_date = None
    cur = {}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            # flush any open block, then only open a new one for a real date
            # heading — a stray non-date "## " section (prose, copy-paste
            # artifact) must NOT become the reported "latest" block.
            if cur_date is not None:
                blocks.append((cur_date, cur))
                cur_date, cur = None, {}
            hdr = s[3:].strip()
            if DATE_RE.match(hdr):
                cur_date, cur = hdr, {}
            continue
        if cur_date is not None and s.startswith("- ") and ":" in s:
            key, _, val = s[2:].partition(":")
            key = key.strip()
            val = val.strip()
            if key == "note":
                cur[key] = val
            elif val == "":
                cur[key] = None
            elif NUM_RE.match(val):      # rejects inf/nan → JSON-safe, never Infinity/NaN tokens
                cur[key] = float(val) if "." in val else int(val)
            else:
                cur[key] = None          # non-numeric metric → null, block still parses
    if cur_date is not None:
        blocks.append((cur_date, cur))
    if not blocks:
        return None
    date_str, values = blocks[-1]
    return {"date": date_str, "values": values}


def parse_gtm(text):
    """gtm-plan.md checkbox progress via the shared CHECKED/UNCHECKED regexes."""
    done = total = 0
    for line in text.splitlines():
        if pu.CHECKED.match(line):
            done += 1
            total += 1
        elif pu.UNCHECKED.match(line):
            total += 1
    if total == 0:
        return None
    return {"done": done, "total": total, "pct": round(100 * done / total)}


def _age_days(last_reviewed):
    if not last_reviewed:
        return None
    try:
        d = datetime.date.fromisoformat(str(last_reviewed)[:10])
    except ValueError:
        return None
    return (datetime.date.today() - d).days


def scan_project(proj, vault):
    """Assess one registry project's business state. Returns (entry, None) or
    (None, reason). A missing repo path is not fatal — business state lives in
    the vault, keyed by area/name — so we assess regardless."""
    home = vault / "Portfolio" / proj["area"] / proj["name"]
    entry = {
        "name": proj["name"],
        "area": proj["area"],
        "path": proj.get("path"),
        "assessed": False,
        "errors": [],
    }
    bdir = home / "business"
    if not bdir.is_dir():
        return entry, None      # triage gap, not an error
    entry["assessed"] = True
    entry.update({
        "schema": None, "verdict": None, "audience": None, "evidence": None,
        "last_reviewed": None, "last_reviewed_age_days": None,
        "monetization": None, "targets": None, "metrics": None, "gtm": None,
    })

    bmd = bdir / "BUSINESS.md"
    if not bmd.exists():
        entry["errors"].append("business/ exists but BUSINESS.md is missing")
    else:
        try:
            fields, err = parse_business_md(bmd.read_text(errors="ignore"))
        except Exception as e:
            fields, err = None, f"BUSINESS.md: {e}"
        if err:
            entry["errors"].append(err)
        if fields:
            entry.update(fields)
            entry["last_reviewed_age_days"] = _age_days(fields.get("last_reviewed"))

    metrics_f = bdir / "metrics.md"
    if metrics_f.exists():
        try:
            entry["metrics"] = parse_metrics(metrics_f.read_text(errors="ignore"))
        except Exception as e:
            entry["errors"].append(f"metrics.md: {e}")

    gtm_f = bdir / "gtm-plan.md"
    if gtm_f.exists():
        try:
            entry["gtm"] = parse_gtm(gtm_f.read_text(errors="ignore"))
        except Exception as e:
            entry["errors"].append(f"gtm-plan.md: {e}")

    return entry, None


def main():
    vault, projects = load_env()
    out = {
        "generated": datetime.date.today().isoformat(),
        "vault_dir": str(vault),
        "supported_schema": SUPPORTED_SCHEMA,
        "projects": [],
        "couldnt_assess": [],
    }
    for proj in projects:
        try:
            entry, reason = scan_project(proj, vault)
        except Exception as e:      # a broken project must not abort the sweep
            entry, reason = None, f"scan error: {e}"
        if entry is None:
            out["couldnt_assess"].append(
                {"name": proj.get("name"), "area": proj.get("area"),
                 "path": proj.get("path"), "reason": reason})
        else:
            out["projects"].append(entry)
    # _normalize converts any date/datetime (YAML auto-coerces unquoted
    # date-shaped scalars anywhere — pricing, a target `by`, etc.) to ISO
    # strings so serialization never crashes mid-stream and takes the whole
    # sweep down. default=str is a final backstop for any other stray type.
    sys.stdout.write(json.dumps(_normalize(out), indent=1, default=str))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
