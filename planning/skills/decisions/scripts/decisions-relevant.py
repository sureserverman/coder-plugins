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


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="decisions-relevant",
        description="Digest the decisions that bind a project on given stacks.")
    ap.add_argument("--vault-dir", type=Path, default=None,
                    help="Override the configured vault root (fixtures/tests).")
    ap.add_argument("--list-domains", action="store_true",
                    help="List every domain register with its entry count, then exit.")
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

    ap.error("nothing to do: pass --list-domains")


if __name__ == "__main__":
    sys.exit(main())
