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

import yaml

# Reuse the authoritative checkbox regexes from the portfolio skill (stable
# sibling layout: business/ and planning/ are siblings under the marketplace
# root). Hyphenated filename → importlib. If the planning plugin isn't installed
# alongside (business is a separately-versioned plugin), degrade to pu=None: the
# sweep still runs and emits JSON for every project — only gtm-plan progress
# becomes a per-project error, honoring "never fatal to the sweep".
_UNIFY = (Path(__file__).resolve().parents[2]
          / "planning" / "skills" / "portfolio" / "scripts" / "portfolio-unify.py")
try:
    _spec = importlib.util.spec_from_file_location("portfolio_unify", _UNIFY)
    pu = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(pu)
except Exception:      # missing sibling, import-time error → degrade, don't crash
    pu = None

SUPPORTED_SCHEMA = 1
VERDICTS = {"monetize", "free-for-reputation", "internal-only", "park"}
EVIDENCE = {"local-only", "researched"}
RESEARCH_DEPTHS = {"triage", "full"}
CONFIDENCE = {"high", "medium", "low"}
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


def parse_business_md(text, expected_project=None):
    """Parse BUSINESS.md frontmatter. Returns (fields_dict, errors_list).
    fields_dict is None only when the file can't be parsed at all; otherwise a
    fields_dict plus a (possibly empty) list of per-field validation errors —
    the required/enum fields (verdict, evidence, last_reviewed, project) are all
    validated symmetrically, matching business-md-format.md."""
    body = text.lstrip("﻿").lstrip()      # tolerate a UTF-8 BOM
    if not body.startswith("---"):
        return None, ["BUSINESS.md: no YAML frontmatter"]
    # Anchor on delimiter LINES, not a raw "---" substring: a triple-dash inside
    # a free-text scalar (e.g. `audience: power users --- anyone`) must NOT
    # truncate the frontmatter and silently drop later fields.
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", body, re.S)
    if not m:
        return None, ["BUSINESS.md: unterminated frontmatter"]
    try:
        fm = yaml.safe_load(m.group(1))
    except (yaml.YAMLError, ValueError) as e:   # ValueError: e.g. 2026-13-45 date
        msg = str(e).splitlines()[0] if str(e) else "invalid YAML"
        return None, [f"BUSINESS.md: invalid frontmatter YAML ({msg})"]
    if not isinstance(fm, dict):
        return None, ["BUSINESS.md: frontmatter is not a mapping"]
    schema = fm.get("schema")
    if schema is None:
        return None, ["BUSINESS.md: missing 'schema'"]
    # bool is an int subclass — reject `schema: true` explicitly, don't treat as 1
    if not isinstance(schema, int) or isinstance(schema, bool):
        return None, [f"BUSINESS.md: 'schema' must be an integer, got {schema!r}"]
    if schema > SUPPORTED_SCHEMA:
        return ({"schema": schema},
                [f"BUSINESS.md: schema {schema} is newer than supported "
                 f"({SUPPORTED_SCHEMA}) — upgrade the business plugin"])
    if schema < 1:
        return ({"schema": schema},
                [f"BUSINESS.md: schema {schema} is below 1 (schema 1 is the minimum)"])

    errors = []
    verdict = fm.get("verdict")
    if verdict not in VERDICTS:
        errors.append(f"BUSINESS.md: verdict {verdict!r} not one of {sorted(VERDICTS)}")
    evidence = fm.get("evidence")
    if evidence not in EVIDENCE:
        errors.append(f"BUSINESS.md: evidence {evidence!r} not one of {sorted(EVIDENCE)}")
    last_reviewed = _isodate(fm.get("last_reviewed"))
    if not last_reviewed:
        errors.append("BUSINESS.md: missing required 'last_reviewed'")
    elif not DATE_RE.match(str(last_reviewed)):
        errors.append(f"BUSINESS.md: last_reviewed {last_reviewed!r} is not YYYY-MM-DD")
    declared = fm.get("project")
    if expected_project and declared and declared != expected_project:
        errors.append(f"BUSINESS.md: project {declared!r} does not match registry "
                      f"name {expected_project!r} (stale copy-paste?)")
    mon = fm.get("monetization") or {}
    if not isinstance(mon, dict):
        mon = {}
    channels = mon.get("channels")
    if channels is not None and not isinstance(channels, list):
        errors.append(f"BUSINESS.md: monetization.channels must be a list, got {channels!r}")
        channels = []
    # Validate targets[] item shape symmetrically with the scalar fields above:
    # a target missing `by`, or with a non-numeric `target`, must surface an error
    # rather than pass through silently. Non-finite `target` floats stay valid here
    # (numeric) and are nulled downstream by _normalize.
    targets = fm.get("targets")
    if targets is None:
        targets = []
    elif not isinstance(targets, list):
        errors.append(f"BUSINESS.md: targets must be a list, got {targets!r}")
        targets = []
    for i, t in enumerate(targets):
        if not isinstance(t, dict):
            errors.append(f"BUSINESS.md: targets[{i}] must be a mapping, got {t!r}")
            continue
        metric = t.get("metric")
        if not isinstance(metric, str) or not metric.strip():
            errors.append(f"BUSINESS.md: targets[{i}].metric must be a non-empty string")
        tval = t.get("target")
        if isinstance(tval, bool) or not isinstance(tval, (int, float)):
            errors.append(f"BUSINESS.md: targets[{i}].target must be numeric, got {tval!r}")
        by = _isodate(t.get("by"))
        if not by or not DATE_RE.match(str(by)):
            errors.append(f"BUSINESS.md: targets[{i}].by must be YYYY-MM-DD, got {t.get('by')!r}")
    fields = {
        "schema": schema,
        "verdict": verdict if verdict in VERDICTS else None,
        "audience": fm.get("audience"),
        "evidence": evidence if evidence in EVIDENCE else None,
        "last_reviewed": last_reviewed,
        "monetization": {
            "model": mon.get("model"),
            "pricing": mon.get("pricing"),
            "channels": channels or [],
        },
        "targets": _normalize(targets),
    }
    return fields, errors


def _extract_frontmatter(text, fname):
    """Shared frontmatter extraction, mirroring parse_business_md's discipline:
    BOM-tolerant, anchored on delimiter LINES (a triple-dash inside a scalar must
    not truncate), YAML-loaded, must be a mapping. Returns (fm_dict, errors);
    fm_dict is None only when extraction fails outright."""
    body = text.lstrip("﻿").lstrip()      # tolerate a UTF-8 BOM
    if not body.startswith("---"):
        return None, [f"{fname}: no YAML frontmatter"]
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", body, re.S)
    if not m:
        return None, [f"{fname}: unterminated frontmatter"]
    try:
        fm = yaml.safe_load(m.group(1))
    except (yaml.YAMLError, ValueError) as e:   # ValueError: e.g. 2026-13-45 date
        msg = str(e).splitlines()[0] if str(e) else "invalid YAML"
        return None, [f"{fname}: invalid frontmatter YAML ({msg})"]
    if not isinstance(fm, dict):
        return None, [f"{fname}: frontmatter is not a mapping"]
    return fm, []


def _schema_gate(fm, fname):
    """Shared schema validation for the light-frontmatter artifacts (market-research.md,
    plan.md). Same *policy* as parse_business_md — missing or non-integer (bool is an
    int subclass — rejected) is fatal, a too-high schema is a loud upgrade error, a
    too-low one is below-minimum — but these blocks don't surface `schema` in their
    output (their contract is exists/date/age_days/… only; the error carries the
    schema value), so every fatal case nulls the whole block. Returns
    (schema, fatal_return): fatal_return, when not None, is the (fields, errors) tuple
    the caller returns as-is (fields always None here); when None, schema is a valid
    supported int and parsing continues."""
    schema = fm.get("schema")
    if schema is None:
        return None, (None, [f"{fname}: missing 'schema'"])
    if not isinstance(schema, int) or isinstance(schema, bool):
        return None, (None, [f"{fname}: 'schema' must be an integer, got {schema!r}"])
    if schema > SUPPORTED_SCHEMA:
        return schema, (None,
                        [f"{fname}: schema {schema} is newer than supported "
                         f"({SUPPORTED_SCHEMA}) — upgrade the business plugin"])
    if schema < 1:
        return schema, (None,
                        [f"{fname}: schema {schema} is below 1 (schema 1 is the minimum)"])
    return schema, None


def parse_market_research(text, expected_project=None):
    """Parse market-research.md frontmatter (schema 1) per
    references/market-research-format.md. Returns (fields_dict, errors_list).
    fields_dict is None only on an extraction failure or a fatal schema problem
    with no schema value; otherwise a dict (emitted as the entry's `research`
    block) plus a possibly-empty list of per-field validation errors. Read-only,
    additive: absent fields null, never fatal to the sweep."""
    fm, errs = _extract_frontmatter(text, "market-research.md")
    if fm is None:
        return None, errs
    schema, fatal = _schema_gate(fm, "market-research.md")
    if fatal is not None:
        return fatal

    errors = []
    declared = fm.get("project")
    if expected_project and declared and declared != expected_project:
        errors.append(f"market-research.md: project {declared!r} does not match registry "
                      f"name {expected_project!r} (stale copy-paste?)")
    researched = _isodate(fm.get("researched"))
    if not researched:
        errors.append("market-research.md: missing required 'researched'")
        researched = None
    elif not DATE_RE.match(str(researched)):
        errors.append(f"market-research.md: researched {researched!r} is not YYYY-MM-DD")
        # Null an invalid date so it never reaches _age_days downstream. (This is a
        # deliberate divergence from parse_business_md, which keeps the raw invalid
        # last_reviewed value — that function stays untouched; the new light-frontmatter
        # parsers null-on-invalid so age math is always safe.)
        researched = None
    depth = fm.get("depth")
    if depth not in RESEARCH_DEPTHS:
        errors.append(f"market-research.md: depth {depth!r} not one of {sorted(RESEARCH_DEPTHS)}")
        depth = None
    confidence = fm.get("confidence")
    if confidence not in CONFIDENCE:
        errors.append(f"market-research.md: confidence {confidence!r} not one of {sorted(CONFIDENCE)}")
        confidence = None
    # Emit exactly the design-contract keys (date/depth/confidence); scan_project
    # adds age_days. No `schema` key — the block's shape is uniform across every branch.
    fields = {"date": researched, "depth": depth, "confidence": confidence}
    return fields, errors


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
    if pu is None:      # portfolio-unify not importable → degrade per-project
        raise RuntimeError("portfolio-unify.py not found — cannot compute gtm progress")
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
        "research": None,
    })

    bmd = bdir / "BUSINESS.md"
    if not bmd.exists():
        entry["errors"].append("business/ exists but BUSINESS.md is missing")
    else:
        try:
            fields, errs = parse_business_md(bmd.read_text(errors="ignore"),
                                             expected_project=proj["name"])
        except Exception as e:
            fields, errs = None, [f"BUSINESS.md: {e}"]
        entry["errors"].extend(errs or [])
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

    # market-research.md and plan.md are additive: an absent file is `exists:
    # false` with no error (a triage/research gap, not a malformation), so
    # existing projects degrade cleanly and downstream consumers read presence
    # without the scanner ever inventing state.
    research_f = bdir / "market-research.md"
    if research_f.exists():
        entry["research"] = {"exists": True, "date": None, "age_days": None,
                             "depth": None, "confidence": None}
        try:
            rfields, rerrs = parse_market_research(research_f.read_text(errors="ignore"),
                                                   expected_project=proj["name"])
        except Exception as e:
            rfields, rerrs = None, [f"market-research.md: {e}"]
        entry["errors"].extend(rerrs or [])
        if rfields:
            entry["research"].update(rfields)
            entry["research"]["age_days"] = _age_days(rfields.get("date"))
    else:
        entry["research"] = {"exists": False, "date": None, "age_days": None,
                             "depth": None, "confidence": None}

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
