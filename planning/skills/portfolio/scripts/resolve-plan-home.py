#!/usr/bin/env python3
"""Resolve where a project's plans belong — for the LLM lane, so it stops resolving in prose.

Ten *scripted* consumers agree on one definition of a reachable vault: `vault_problem()` in
`portfolio-rebuild.py`, five conditions with five messages. Three SKILLS resolved it in prose
instead — `planning-projects` § Output location, and `architecting-projects` and
`brainstorming` by delegation to it — and branched on **unset** alone. Against a configured
but unmounted vault they therefore did what the scripted lane now refuses to do: `mkdir -p`
the phantom tree and write the plan into it. Same failure, through the model instead of a
script (BL-101).

The fix could not be "teach three skills the five conditions", because that is a second
definition of reachable in prose, free to drift from the one the tests pin — which is DEC-011,
the decision this plan violated twice while trying to honour it. So the conditions stay in one
place and the skills call this instead.

EXIT CODES, which are the interface:

  0  stdout is the absolute plans directory. Use it.
  2  the vault is CONFIGURED BUT UNREACHABLE. stderr carries the canonical message.
     **Stop.** Do not fall back to the repo, and do not create anything: a missing vault is
     not an empty vault, and this is the exact case that produced phantom trees.
  3  no `vault_dir` is configured at all. stderr says so. The policy is to warn and write to
     `<repo>/docs/plans/` — defined once in `../references/registry-format.md`
     § Auto-registration and settled by DEC-020. It is the CALLER's to apply: this script
     answers the reachability question, not the fallback question, and keeping the two apart
     is what stops a dropped mount being handled like an unconfigured machine.

The split between 2 and 3 is the whole point. "Unset" and "set but not there" were one branch
in the prose, and collapsing them is what let a dropped mount look like an unconfigured
machine.
"""
import argparse
import importlib.util
import sys
from pathlib import Path

CONFIG = Path.home() / ".claude" / "portfolio-config.yaml"
REGISTRY = Path.home() / ".claude" / "projects-registry.yaml"


def rebuild():
    """portfolio-rebuild.py by path — the canonical guard lives there and is not restated."""
    spec = importlib.util.spec_from_file_location(
        "portfolio_rebuild", Path(__file__).resolve().parent / "portfolio-rebuild.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    # Staleness probe, diagnostic only — one stderr line if this copy is an older cached
    # plugin than the checkout. Guarded, and inside main() rather than at module scope, for
    # the same reason every sibling does it: a probe that cannot import must never be able
    # to stop the command it is advising on.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import _staleness
        _staleness.warn_if_stale(__file__)
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", default=".",
                    help="repo path (default: cwd). Its area/name locate the portfolio home.")
    args = ap.parse_args()

    import yaml
    cfg = yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}
    vd = (cfg or {}).get("vault_dir")
    if not vd:
        print(f"no vault_dir configured in {CONFIG} — apply the documented fallback "
              f"(registry-format.md § Auto-registration, DEC-020); this script decides "
              f"reachability only.", file=sys.stderr)
        return 3

    pr = rebuild()
    # The ONE definition. Not re-implemented, not paraphrased, not partially applied.
    vault, problem = pr.vault_problem(Path(vd), str(CONFIG))
    if problem:
        print(problem, file=sys.stderr)
        return 2

    repo = Path(args.project).resolve()
    area = name = None
    if REGISTRY.exists():
        reg = yaml.safe_load(REGISTRY.read_text()) or {}
        for p in reg.get("projects", []):
            if Path(p.get("path", "")).resolve() == repo:
                area, name = p.get("area"), p.get("name")
                break
    if area is None:
        # Not registered yet — a first-class state, not an error: `planning-projects`
        # auto-registers as part of writing a project's first plan. Derive the same
        # `~/dev/<area>/<name>` shape it derives, and let the caller do the registering.
        parts = repo.parts
        if len(parts) >= 2:
            area, name = parts[-2], parts[-1]
        else:
            print(f"cannot derive area/name from {repo} — pass a repo path shaped like "
                  f"~/dev/<area>/<name>.", file=sys.stderr)
            return 2

    print(vault / "Portfolio" / area / name / "plans")
    return 0


if __name__ == "__main__":
    sys.exit(main())
