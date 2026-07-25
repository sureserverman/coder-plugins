#!/usr/bin/env python3
"""decisions-relevant — which recorded decisions bind a project on these stacks?

The decisions register has two halves (references/decisions-format.md): the
per-project `<portfolio_home>/decisions.md` (DEC-NNN) and the per-domain
`<vault>/Portfolio/decisions/<domain>.md` registers (GDEC-<DOM>-NNN) that bind
every project on a platform or stack. Planning and execution need a digest of
both, scoped to the stacks in play, without hand-reading files.

Two properties this script exists to guarantee:

  * **The global half is always reachable.** A brand-new project has no registry
    entry and no decisions.md, so `portfolio_home` does not resolve — but the
    domain registers bind it anyway, and are exactly what it needs. A missing
    project half degrades to `project_register: absent`; it is never an error.
  * **Degrade, never drop.** A malformed block comes back flagged, not skipped —
    the parser contract inherited from portfolio-rebuild.py, whose functions this
    script imports rather than re-deriving (the compass-scan.py precedent).

`vault_dir()` is called only in main(); every other function takes an explicit
vault Path, so fixtures drive the logic without touching the user's config.

Run: python3 planning/skills/decisions/scripts/decisions-relevant.py --list-domains
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_REBUILD = Path(__file__).resolve().parents[2] / "portfolio" / "scripts" / "portfolio-rebuild.py"


def _load_rebuild():
    """Import portfolio-rebuild.py as a module (it is a script path, not a package).

    Reusing its parser is the point: the decisions block grammar, the
    degrade-never-drop contract, and the required-field sets are fixture-locked
    by test-portfolio-decisions.py. A second implementation here would be a
    second thing to keep correct.
    """
    spec = importlib.util.spec_from_file_location("portfolio_rebuild", _REBUILD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pr = _load_rebuild()


def list_domains(vault: Path):
    """[(slug, entry_count, error_count)] for every Portfolio/decisions/*.md register.

    This is the answer to "which domains even exist?" — the question a project
    with no decision history of its own cannot answer from local state.
    """
    domains = pr.read_domain_decisions(vault)
    return [(slug, len(d["entries"]), len(d["errors"])) for slug, d in sorted(domains.items())]


def first_sentence(text, limit=240):
    """The Reason's opening sentence — the constraint, without the full argument.

    A digest row has to be scannable, but a truncation mid-word is worse than a
    long line: the Reason IS the deliverable of an entry, and a mangled one reads
    as though the register itself is unreliable. So: cut at a sentence boundary
    when there is one in range, otherwise at a word boundary, and mark it.
    """
    t = " ".join((text or "").split())
    if not t:
        return ""
    for end in (". ", "; "):
        i = t.find(end)
        if 0 < i <= limit:
            return t[:i + 1].strip()
    if len(t) <= limit:
        return t
    return t[:t.rfind(" ", 0, limit)].rstrip(",;: ") + " …"


def digest_entry(entry, domain):
    """One register block → one digest row.

    Malformed blocks come through with `id: None` and a populated `missing`
    list; they are carried into the digest flagged rather than filtered, because
    a decision that fails to parse is exactly the one a planner must see.
    """
    f = entry["fields"]
    status = (f.get("Status") or "").strip()
    return {
        "id": entry["id"],
        "title": entry["title"],
        "status": status or "unknown",
        "superseded": status.lower().startswith("superseded"),
        "domain": domain,
        "domains": pr.decision_domains(entry),
        # `Applies to` is a nested bullet list that the shared parser flattens to
        # one string, leaving the "- " markers inline. Strip them for display;
        # the wikilinks the roll-up cares about are unaffected.
        "applies_to": " ".join((f.get("Applies to", "") or "").split()).lstrip("- ").replace(" - ", "; "),
        "source": f.get("Source", ""),
        "decided": f.get("Decided", ""),
        "reason": first_sentence(f.get("Reason", "")),
        "malformed": entry["malformed_heading"] or bool(entry["missing"]),
        "missing": entry["missing"],
        "heading": entry["heading"],
    }


def global_digest(vault: Path, slugs):
    """Digest of the domain registers named by `slugs`.

    Superseded entries are INCLUDED and marked. "We used to believe X and
    stopped" is context a planner needs — dropping it invites re-proposing the
    approach that was already rejected.
    """
    domains = pr.read_domain_decisions(vault)
    rows, unknown, errors = [], [], []
    for slug in slugs:
        d = domains.get(slug)
        if d is None:
            unknown.append(slug)
            continue
        for e in d["entries"]:
            rows.append(digest_entry(e, slug))
        errors.extend(f"{slug}: {msg}" for msg in d["errors"])
    return {
        "global": rows,
        "unknown_domains": unknown,
        "available_domains": sorted(domains),
        "errors": errors,
    }


def render_text(result):
    """Human-readable digest. Flags and supersessions are visible, not implied."""
    rows = result["global"]
    if not rows:
        print("no decisions bind the requested domains")
    for r in rows:
        marks = []
        if r["superseded"]:
            marks.append("SUPERSEDED")
        if r["malformed"]:
            marks.append("MALFORMED: missing " + ", ".join(r["missing"]) if r["missing"]
                         else "MALFORMED: unparseable heading")
        mark = ("  [" + "; ".join(marks) + "]") if marks else ""
        ident = r["id"] or f"<unparseable heading: {r['heading']}>"
        print(f"{ident} — {r['title']}  ({r['status']}; {r['domain']}){mark}")
        if r["reason"]:
            print(f"    {r['reason']}")
        if r["applies_to"]:
            print(f"    applies to: {r['applies_to']}")
    for e in result["errors"]:
        print(f"register error: {e}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="decisions-relevant",
        description="Digest the decisions that bind a project on given stacks.")
    ap.add_argument("--vault-dir", type=Path, default=None,
                    help="Override the configured vault root (fixtures/tests).")
    ap.add_argument("--list-domains", action="store_true",
                    help="List every domain register with its entry count, then exit.")
    ap.add_argument("--domains", default="",
                    help="Comma-separated domain slugs to digest (e.g. android,tor).")
    ap.add_argument("--format", choices=("text", "json"), default="text",
                    help="Output shape. json is for programmatic callers.")
    args = ap.parse_args(argv)

    # The one place the user's config is read. Missing vault_dir exits loudly
    # here rather than falling back to a path inside the repo — the
    # vault-canonical storage law (see SKILL.md § Where the files live).
    vault = args.vault_dir if args.vault_dir is not None else pr.vault_dir()

    if args.list_domains:
        rows = list_domains(vault)
        if not rows:
            print("no domain registers found under "
                  f"{vault / 'Portfolio' / 'decisions'}")
            return 0
        for slug, n, errs in rows:
            suffix = f"  ({errs} malformed)" if errs else ""
            print(f"{slug}\t{n} entries{suffix}")
        return 0

    slugs = [s.strip().lower() for s in args.domains.split(",") if s.strip()]
    if not slugs:
        ap.error("nothing to do: pass --list-domains or --domains <slug,...>")

    result = global_digest(vault, slugs)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        render_text(result)

    # An unknown slug is reported, never silently empty: "no decisions bind this"
    # and "you asked about a register that does not exist" are different answers,
    # and conflating them is how a planner concludes nothing constrains them.
    for slug in result["unknown_domains"]:
        print(f"unknown domain: {slug} — available: "
              f"{', '.join(result['available_domains']) or '(none)'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
