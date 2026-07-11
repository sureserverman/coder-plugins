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
    n = sum(1 for k in vals if k != "note")
    return f"{m.get('date')} ({n})"


def reviewed_of(p):
    age = p.get("last_reviewed_age_days")
    return f"{age}d" if isinstance(age, int) else "—"


def render(doc):
    projects = doc.get("projects", [])
    assessed = [p for p in projects if p.get("assessed")]
    unassessed = [p for p in projects if not p.get("assessed")]
    errored = [p for p in assessed if p.get("errors")]

    out = ["# Global Business Roll-up", f"Generated: {doc.get('generated')}", ""]

    out.append(f"## Assessed ({len(assessed)})")
    out.append("")
    if assessed:
        out.append("| Project | Verdict | Model | Stage | Reviewed | Actuals |")
        out.append("|---------|---------|-------|-------|----------|---------|")
        for p in sorted(assessed, key=lambda x: x["name"]):
            model = (p.get("monetization") or {}).get("model") or "—"
            out.append(f"| [[{p['name']}]] | {p.get('verdict') or '—'} | {model} "
                       f"| {stage_of(p)} | {reviewed_of(p)} | {actuals_of(p)} |")
    else:
        out.append("_None assessed yet._")
    out.append("")

    out.append(f"## Not yet assessed ({len(unassessed)}) — triage gap")
    out.append("")
    if unassessed:
        out.append(", ".join(f"[[{p['name']}]]" for p in sorted(unassessed, key=lambda x: x["name"])))
    else:
        out.append("_All registry projects have a verdict._")
    out.append("")

    couldnt = doc.get("couldnt_assess", [])
    if couldnt:
        out.append(f"## Couldn't assess ({len(couldnt)})")
        out.append("")
        for c in couldnt:
            out.append(f"- {c.get('name')}: {c.get('reason')}")
        out.append("")

    if errored:
        out.append(f"## Errors ({len(errored)})")
        out.append("")
        for p in sorted(errored, key=lambda x: x["name"]):
            for e in p["errors"]:
                out.append(f"- [[{p['name']}]]: {e}")
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
