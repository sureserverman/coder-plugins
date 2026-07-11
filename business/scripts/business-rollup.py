#!/usr/bin/env python3
"""business-rollup — render the portfolio business roll-up.

Reads business-scan.py's JSON on stdin and writes global-business.md (per
references/global-business-format.md) on stdout. Pure rendering: it never parses
the vault itself — the scanner is the sole parser; this only shapes its JSON into
markdown. Usage:

    python3 business-scan.py | python3 business-rollup.py > global-business.md

Degrade-loudly: unassessed projects, projects that couldn't be assessed, and
projects whose BUSINESS.md had errors are each surfaced in their own section,
never dropped.
"""
import json
import sys


def _cell(x):
    """Neutralize markdown-table-breaking chars in a free-text cell: `|` splits
    cells, a newline splits the row. Registry names are only informally
    kebab-case, so this isn't a safe assumption to skip."""
    return str(x).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _wl(p):
    """Area-qualified wikilink, matching portfolio-rebuild.py — two projects in
    different areas may share a name slug (registry-format.md documents this)."""
    return f"{_cell(p.get('area'))}/[[{_cell(p['name'])}]]"


def stage_of(p):
    """Highest pipeline stage the scanner evidence supports."""
    if p.get("metrics"):
        return "tracked"
    if p.get("gtm"):
        return "launched"
    if (p.get("monetization") or {}).get("model"):
        return "modeled"
    return "assessed"


def actuals_of(p):
    m = p.get("metrics")
    if not m:
        return "—"
    vals = m.get("values", {}) or {}
    # Count only real actuals: exclude the `note` string and any key whose value
    # is null (failed numeric parse or left blank) — a null must not inflate (N).
    n = sum(1 for k, v in vals.items() if k != "note" and v is not None)
    return f"{_cell(m.get('date') or '—')} ({n})"


def reviewed_of(p):
    age = p.get("last_reviewed_age_days")
    return f"{age}d" if isinstance(age, int) else "—"


def render(doc):
    projects = doc.get("projects", [])
    assessed = [p for p in projects if p.get("assessed")]
    unassessed = [p for p in projects if not p.get("assessed")]
    # errors surface for ANY project carrying them, assessed or not — the
    # degrade-loudly guarantee isn't conditional on assessment.
    errored = [p for p in projects if p.get("errors")]

    out = ["# Global Business Roll-up", f"Generated: {_cell(doc.get('generated'))}", ""]

    out.append(f"## Assessed ({len(assessed)})")
    out.append("")
    if assessed:
        out.append("| Project | Verdict | Model | Stage | Reviewed | Actuals |")
        out.append("|---------|---------|-------|-------|----------|---------|")
        for p in sorted(assessed, key=lambda x: (x.get("area", ""), x["name"])):
            model = _cell((p.get("monetization") or {}).get("model") or "—")
            out.append(f"| {_wl(p)} | {_cell(p.get('verdict') or '—')} | {model} "
                       f"| {stage_of(p)} | {reviewed_of(p)} | {actuals_of(p)} |")
    else:
        out.append("_None assessed yet._")
    out.append("")

    out.append(f"## Not yet assessed ({len(unassessed)}) — triage gap")
    out.append("")
    if unassessed:
        links = ", ".join(_wl(p) for p in sorted(unassessed, key=lambda x: (x.get("area", ""), x["name"])))
        out.append(f"- {links}")
    else:
        out.append("_All registry projects have a verdict._")
    out.append("")

    couldnt = doc.get("couldnt_assess", [])
    if couldnt:
        out.append(f"## Couldn't assess ({len(couldnt)})")
        out.append("")
        for c in couldnt:
            out.append(f"- {_cell(c.get('name'))}: {_cell(c.get('reason'))}")
        out.append("")

    if errored:
        out.append(f"## Errors ({len(errored)})")
        out.append("")
        for p in sorted(errored, key=lambda x: (x.get("area", ""), x["name"])):
            tag = "" if p.get("assessed") else " (unassessed)"
            for e in p["errors"]:
                out.append(f"- {_wl(p)}{tag}: {_cell(e)}")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def main():
    try:
        doc = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.exit(f"business-rollup: input is not valid JSON ({e})")
    sys.stdout.write(render(doc))


if __name__ == "__main__":
    main()
