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

SUPPORTED_SCHEMA = 1                 # baseline: BUSINESS.md, metrics.md, gtm-plan.md
SUPPORTED_GROUP_SCHEMA = 1           # business-groups/<slug>/group.md
# Per-artifact schema ceilings. market-research.md and plan.md moved to schema 2
# (tiered depth); BUSINESS.md stays at the baseline. The gate is parameterized by
# the artifact's ceiling so each file degrades loudly only past its OWN max.
MARKET_RESEARCH_MAX_SCHEMA = 2
PLAN_MAX_SCHEMA = 2
VERDICTS = {"monetize", "free-for-reputation", "internal-only", "park"}
EVIDENCE = {"local-only", "researched"}
# Research depth is schema-dependent: schema 1 was the binary triage|full; schema 2
# is the operator-selected brief|standard|deep tier. Validate a file's depth against
# the set for that file's OWN schema, so legacy artifacts keep parsing clean.
RESEARCH_DEPTHS_BY_SCHEMA = {1: {"triage", "full"}, 2: {"brief", "standard", "deep"}}
PLAN_DEPTHS = {"brief", "standard", "deep"}      # schema-2 plan depth tier
CONFIDENCE = {"high", "medium", "low"}
PLAN_STATUS = {"draft", "active"}
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
    # Set-but-missing `vault_dir` is REFUSED, never created — a missing vault is
    # not an empty vault (portfolio/SKILL.md § Resolver). Full rationale in
    # portfolio-rebuild.py's vault_dir(). expanduser() comes first because an
    # unexpanded `~/vault` is cwd-RELATIVE, the same defect by another route.
    # Not merely the scan's own read path: resolve-dest.py calls this function to
    # resolve <vault>/Portfolio/global-business.md, the destination biz-portfolio
    # then writes. Unchecked, that pipeline would print a path under a vault that
    # is not mounted and write the roll-up into a directory it had to create.
    vault = Path(vd).expanduser()
    if not vault.is_dir():
        sys.exit(f"vault unreachable: vault_dir {vault} (from {config}) is not an "
                 f"existing directory — refusing, because a missing vault is not "
                 f"an empty vault. Mount the vault or correct vault_dir.")
    return vault, [p for p in reg["projects"] if p.get("enabled", True)]


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


def _schema_gate(fm, fname, max_schema=SUPPORTED_SCHEMA):
    """Shared schema validation for the light-frontmatter artifacts (market-research.md,
    plan.md). Same *policy* as parse_business_md — missing or non-integer (bool is an
    int subclass — rejected) is fatal, a schema above the artifact's `max_schema` is a
    loud upgrade error, a too-low one is below-minimum — but these blocks don't surface
    `schema` in their output (their contract is exists/date/age_days/… only; the error
    carries the schema value), so every fatal case nulls the whole block. `max_schema`
    is the artifact's OWN ceiling (market-research/plan → 2), so each degrades loudly
    only past its own max. Returns (schema, fatal_return): fatal_return, when not None,
    is the (fields, errors) tuple the caller returns as-is (fields always None here);
    when None, schema is a valid supported int and parsing continues."""
    schema = fm.get("schema")
    if schema is None:
        return None, (None, [f"{fname}: missing 'schema'"])
    if not isinstance(schema, int) or isinstance(schema, bool):
        return None, (None, [f"{fname}: 'schema' must be an integer, got {schema!r}"])
    if schema > max_schema:
        return schema, (None,
                        [f"{fname}: schema {schema} is newer than supported "
                         f"({max_schema}) — upgrade the business plugin"])
    if schema < 1:
        return schema, (None,
                        [f"{fname}: schema {schema} is below 1 (schema 1 is the minimum)"])
    return schema, None


def _project_mismatch(fm, expected_project, fname):
    """One project-mismatch error if the declared project disagrees with the registry
    name, else empty — the check both light-frontmatter parsers share (BL-005)."""
    declared = fm.get("project")
    if expected_project and declared and declared != expected_project:
        return [f"{fname}: project {declared!r} does not match registry "
                f"name {expected_project!r} (stale copy-paste?)"]
    return []


def _date_or_null(fm, key, fname):
    """Validate a required YYYY-MM-DD frontmatter date. Returns (value_or_None, errors);
    missing or malformed → None so age math downstream is always safe. The null-on-invalid
    discipline both light-frontmatter parsers share (BL-005)."""
    val = _isodate(fm.get(key))
    if not val:
        return None, [f"{fname}: missing required {key!r}"]
    if not DATE_RE.match(str(val)):
        return None, [f"{fname}: {key} {val!r} is not YYYY-MM-DD"]
    return val, []


def parse_market_research(text, expected_project=None):
    """Parse market-research.md frontmatter (schema 1 or 2) per
    references/market-research-format.md. Returns (fields_dict, errors_list).
    fields_dict is None only on an extraction failure or a fatal schema problem
    with no schema value; otherwise a dict (emitted as the entry's `research`
    block) plus a possibly-empty list of per-field validation errors. The `depth`
    enum is validated against the file's OWN schema (schema 1 → triage|full, schema
    2 → brief|standard|deep). Read-only, additive: absent fields null, never fatal
    to the sweep."""
    fm, errs = _extract_frontmatter(text, "market-research.md")
    if fm is None:
        return None, errs
    schema, fatal = _schema_gate(fm, "market-research.md", MARKET_RESEARCH_MAX_SCHEMA)
    if fatal is not None:
        return fatal

    errors = _project_mismatch(fm, expected_project, "market-research.md")
    researched, derrs = _date_or_null(fm, "researched", "market-research.md")
    errors += derrs
    valid_depths = RESEARCH_DEPTHS_BY_SCHEMA.get(schema, set())
    depth = fm.get("depth")
    if depth not in valid_depths:
        errors.append(f"market-research.md: depth {depth!r} not one of "
                      f"{sorted(valid_depths)} (schema {schema})")
        depth = None
    confidence = fm.get("confidence")
    if confidence not in CONFIDENCE:
        errors.append(f"market-research.md: confidence {confidence!r} not one of {sorted(CONFIDENCE)}")
        confidence = None
    # Emit exactly the design-contract keys (date/depth/confidence); scan_project
    # adds age_days. No `schema` key — the block's shape is uniform across every branch.
    fields = {"date": researched, "depth": depth, "confidence": confidence}
    return fields, errors


def parse_plan(text, expected_project=None):
    """Parse plan.md frontmatter (schema 1 or 2) per references/plan-format.md. Returns
    (fields_dict, errors_list) with the same discipline and uniform-block policy as
    parse_market_research: fields_dict is None only on an extraction/fatal-schema
    failure; otherwise the `plan` block's data keys (date/status/depth) plus per-field
    errors. `depth` is required on a schema-2 plan (brief|standard|deep) and absent on a
    schema-1 plan (reported null — legacy plans are not retro-tiered). `market_research`
    is validated (a YYYY-MM-DD date or the literal 'none') but not emitted — the block's
    contract is presence/age/status/depth for the roll-up."""
    fm, errs = _extract_frontmatter(text, "plan.md")
    if fm is None:
        return None, errs
    schema, fatal = _schema_gate(fm, "plan.md", PLAN_MAX_SCHEMA)
    if fatal is not None:
        return fatal

    errors = _project_mismatch(fm, expected_project, "plan.md")
    date, derrs = _date_or_null(fm, "date", "plan.md")
    errors += derrs
    status = fm.get("status")
    if status not in PLAN_STATUS:
        errors.append(f"plan.md: status {status!r} not one of {sorted(PLAN_STATUS)}")
        status = None
    # depth: schema 2 requires the brief|standard|deep tier; schema 1 plans have no
    # depth field (reported null — legacy plans are not retro-tiered).
    depth = fm.get("depth")
    if schema >= 2:
        if depth not in PLAN_DEPTHS:
            errors.append(f"plan.md: depth {depth!r} not one of {sorted(PLAN_DEPTHS)} "
                          f"(required at schema {schema})")
            depth = None
    else:
        depth = None
    # market_research: a YYYY-MM-DD (the folded-in research date) or the literal
    # 'none'. Validated for malformation, not emitted (block contract is
    # exists/date/age_days/status/depth).
    mr = _isodate(fm.get("market_research"))
    if mr is None:
        errors.append("plan.md: missing required 'market_research' (a date or 'none')")
    elif mr != "none" and not DATE_RE.match(str(mr)):
        errors.append(f"plan.md: market_research {mr!r} must be YYYY-MM-DD or 'none'")
    fields = {"date": date, "status": status, "depth": depth}
    return fields, errors


def parse_metrics(text):
    """Latest dated block of metrics.md → {date, values, notes, breakdown} or None.

    `values` holds aggregate metrics only. A key containing `@` is a per-member
    breakdown line (`github.stars@<area>/<name>`, groups only) and goes to
    `breakdown` instead: it must never reach target matching, because the
    suffix-after-last-`.` rule would make every member's key claim the same
    target and silently discard all but one (references/group-format.md).

    `notes` is a LIST. One `track` cycle can degrade several metrics at once —
    a private npm package nulls three keys while a missing push token separately
    kills github.clones_14d — and a single-string note silently kept only the
    last reason, exactly in the runs where provenance matters most (BL-012).
    `values["note"]` is retained as the last note for backward compatibility
    with consumers written against the single-string contract.
    """
    blocks = []          # (date_str, values, notes, breakdown)
    cur_date = None
    cur, notes, brk = {}, [], {}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            # flush any open block, then only open a new one for a real date
            # heading — a stray non-date "## " section (prose, copy-paste
            # artifact) must NOT become the reported "latest" block.
            if cur_date is not None:
                blocks.append((cur_date, cur, notes, brk))
                cur_date, cur, notes, brk = None, {}, [], {}
            hdr = s[3:].strip()
            if DATE_RE.match(hdr):
                cur_date, cur, notes, brk = hdr, {}, [], {}
            continue
        if cur_date is not None and s.startswith("- ") and ":" in s:
            key, _, val = s[2:].partition(":")
            key = key.strip()
            val = val.strip()
            if key == "note":
                notes.append(val)
                cur[key] = val           # last note wins, for pre-BL-012 consumers
                continue
            if val == "":
                parsed = None
            elif NUM_RE.match(val):      # rejects inf/nan → JSON-safe, never Infinity/NaN tokens
                parsed = float(val) if "." in val else int(val)
            else:
                parsed = None            # non-numeric metric → null, block still parses
            if "@" in key:
                brk[key] = parsed        # per-member attribution, never target-matched
            else:
                cur[key] = parsed
    if cur_date is not None:
        blocks.append((cur_date, cur, notes, brk))
    if not blocks:
        return None
    date_str, values, notes, brk = blocks[-1]
    return {"date": date_str, "values": values, "notes": notes, "breakdown": brk}


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


def _scan_light_artifact(bdir, fname, parser, expected_project, empty_shape):
    """Shared scan for the additive light-frontmatter artifacts (market-research.md,
    plan.md) — BL-005. An absent file yields empty_shape with exists:false and no error;
    a present file is parsed, its errors collected, and on a successful parse the fields
    merged in with a computed age_days from the block's `date`. A present-but-unparseable
    file keeps exists:true with null data (matching the pre-dedup behavior). Returns
    (block_dict, errors_list)."""
    f = bdir / fname
    if not f.exists():
        return {**empty_shape, "exists": False}, []
    block = {**empty_shape, "exists": True}
    try:
        fields, errs = parser(f.read_text(errors="ignore"),
                              expected_project=expected_project)
    except Exception as e:
        fields, errs = None, [f"{fname}: {e}"]
    if fields:
        block.update(fields)
        block["age_days"] = _age_days(fields.get("date"))
    return block, (errs or [])


def _age_days(last_reviewed):
    if not last_reviewed:
        return None
    try:
        d = datetime.date.fromisoformat(str(last_reviewed)[:10])
    except ValueError:
        return None
    return (datetime.date.today() - d).days


def _read_business_dir(bdir, expected_project, entry):
    """Fill `entry` from the business artifacts in `bdir`.

    Shared by a single registry project (`<home>/business/`) and a business group
    (`Portfolio/business-groups/<slug>/`) — the artifacts are identical in both
    cases; only the directory and the name `project:` must match differ. Keeping
    one reader is what stops a group's artifacts from drifting into a second,
    subtly different contract.
    """
    entry["assessed"] = True
    entry.update({
        "schema": None, "verdict": None, "audience": None, "evidence": None,
        "last_reviewed": None, "last_reviewed_age_days": None,
        "monetization": None, "targets": None, "metrics": None, "gtm": None,
        "research": None, "plan": None,
    })
    proj = {"name": expected_project}

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
    # without the scanner ever inventing state. Both share _scan_light_artifact
    # (BL-005) — the only difference is the parser and the block's uniform shape.
    entry["research"], rerrs = _scan_light_artifact(
        bdir, "market-research.md", parse_market_research, proj["name"],
        {"exists": False, "date": None, "age_days": None,
         "depth": None, "confidence": None})
    entry["errors"].extend(rerrs)

    entry["plan"], perrs = _scan_light_artifact(
        bdir, "plan.md", parse_plan, proj["name"],
        {"exists": False, "date": None, "age_days": None,
         "status": None, "depth": None})
    entry["errors"].extend(perrs)


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
    _read_business_dir(bdir, proj["name"], entry)
    return entry, None


def load_groups(vault, projects):
    """Read Portfolio/business-groups/*/group.md — see references/group-format.md.

    Returns (groups, member_index). `groups` entries are dicts with dir/group/
    members/errors/fatal; `member_index` maps "<area>/<name>" -> group slug for
    every member of a NON-fatal group, so the caller can suppress those projects'
    own rows. A fatal group claims no members: a suite assessed over an unknown
    subset is worse than no answer, so it degrades whole rather than in part.
    """
    gdir = vault / "Portfolio" / "business-groups"
    groups, member_index, claimed = [], {}, {}
    if not gdir.is_dir():
        return groups, member_index
    enabled = {f"{p['area']}/{p['name']}" for p in projects}

    for d in sorted(x for x in gdir.iterdir() if x.is_dir()):
        man = d / "group.md"
        g = {"dir": d, "slug": d.name, "group": d.name, "members": [],
             "created": None, "errors": [], "fatal": None}
        if not man.exists():
            g["fatal"] = "group.md is missing"
            groups.append(g)
            continue
        try:
            fm, ferrs = _extract_frontmatter(man.read_text(errors="ignore"), "group.md")
        except Exception as e:
            g["fatal"] = f"group.md: {e}"
            groups.append(g)
            continue
        if fm is None:
            g["fatal"] = "; ".join(ferrs) or "group.md: no YAML frontmatter"
            groups.append(g)
            continue

        schema, fatal = _schema_gate(fm, "group.md", max_schema=SUPPORTED_GROUP_SCHEMA)
        if fatal is not None:
            g["fatal"] = "; ".join(fatal[1])
            groups.append(g)
            continue

        declared = fm.get("group")
        if declared and declared != d.name:
            # The directory is what the resolver finds, so a mismatch would make
            # the group addressable under two different names.
            g["fatal"] = (f"group.md declares group {declared!r} but lives in "
                          f"directory {d.name!r}")
            groups.append(g)
            continue

        members = fm.get("members") or []
        if not isinstance(members, list) or not all(isinstance(m, str) for m in members):
            g["fatal"] = "group.md: 'members' must be a list of '<area>/<name>' strings"
            groups.append(g)
            continue
        if len(members) < 2:
            g["fatal"] = (f"group.md lists {len(members)} member(s); a business group "
                          f"needs at least 2 (one member is just a project)")
            groups.append(g)
            continue

        unknown = [m for m in members if m not in enabled]
        if unknown:
            g["fatal"] = ("group.md names member(s) that are not enabled registry "
                          f"projects: {', '.join(sorted(unknown))}")
            groups.append(g)
            continue

        g["members"], g["created"], g["schema"] = members, fm.get("created"), schema

        # A member's own business/ dir is reported, never silently overridden:
        # someone assessed that repo standalone AND as part of a suite, and the
        # two verdicts may disagree. Choosing one would hide the contradiction.
        for m in members:
            area, _, name = m.partition("/")
            if (vault / "Portfolio" / area / name / "business").is_dir():
                g["errors"].append(
                    f"member {m} has its own business/ directory, which this group "
                    f"supersedes — migrate it into the group dir or drop the member")
            if m in claimed:
                g["errors"].append(f"member {m} is also claimed by group {claimed[m]!r}")
            else:
                claimed[m] = d.name
                member_index[m] = d.name
        groups.append(g)

    return groups, member_index


def scan_group(g, vault):
    """Assess one business group. Returns an entry shaped like a project entry
    plus `group: True` and `members`, or (None, reason) when the manifest is
    fatally malformed."""
    entry = {
        "name": g["slug"],
        "area": None,
        "path": str(g["dir"]),
        "group": True,
        "members": g["members"],
        "assessed": False,
        "errors": list(g["errors"]),
    }
    if g["fatal"]:
        return None, g["fatal"]
    _read_business_dir(g["dir"], g["slug"], entry)
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
    # Groups first: a grouped member must not also emit its own row, or the
    # roll-up would double-count one product. See references/group-format.md.
    try:
        groups, member_index = load_groups(vault, projects)
    except Exception as e:          # the group layer must never abort the sweep
        groups, member_index = [], {}
        out["group_errors"] = [f"group discovery failed: {e}"]
    out["groups"] = sorted(set(member_index.values()))

    for g in groups:
        try:
            entry, reason = scan_group(g, vault)
        except Exception as e:
            entry, reason = None, f"scan error: {e}"
        if entry is None:
            out["couldnt_assess"].append(
                {"name": g["slug"], "area": None, "path": str(g["dir"]),
                 "group": True, "reason": reason})
        else:
            out["projects"].append(entry)

    for proj in projects:
        if f"{proj['area']}/{proj['name']}" in member_index:
            continue                # covered by its group's entry
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
