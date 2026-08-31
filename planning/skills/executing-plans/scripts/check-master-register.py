#!/usr/bin/env python3
"""A master's register and its sub-plans agree — in both directions.

RUN AT THE MASTER CLOSE-OUT, which is its position (DEC-017) and not a repo validator.
It lives here rather than in `scripts/` deliberately: its corpus is the VAULT, so as a
`check-*.py` in the repo's validator set it made this repo's build red or green according
to whether four other projects had tidied their registers. A repo's CI may not depend on
another project's plan hygiene. `master-plans.md` step 5 is what invokes it.

WHY THIS EXISTS. `master-plans.md` step 3 flips a register entry to `[x]` once the
sub-plan carries a terminal marker, and step 5 forbids the master's own
`**Completed:**` line while any `[x]` entry's sub-plan is unclosed or carries an
unaccepted `[~]` gate. Both are rules a reader follows; neither was checkable, and
the register is the half that gets edited under pressure. Measured on the live
vault when this was written: 4 sub-plans carried a register `[x]` with no terminal
marker of their own, and they had stood since 2026-08-09 and 2026-08-21.

BL-104 is the mirror direction and says in as many words why nothing caught it:
the flip happens at a sub-plan close-out, outside any task transition, so
`status_lag`'s state-file comparison structurally cannot see it. A master can sit
with a finished sub-plan and an unflipped register indefinitely.

THE CONTRACT LIVES IN ONE PLACE. Every regex and predicate here comes from
`portfolio-unify.py` via importlib — STATUS_RE, SUBPLAN_RE, SUBPLAN_LINK_RE,
COMPLETED_RE, ABANDONED_RE, link_target, status_state, is_master_plan and
plan_blocked. This file defines none of them. If you find yourself about to write
one here, add it there and import it: two definitions of "closed" is what DEC-011's
sibling reasoning forbids, and it is how three consumers came to disagree about the
same plan.

WHAT THIS GUARD CANNOT SCREEN, disclosed per DEC-008:

  - A register entry whose `- **Plan:**` link does not resolve is skipped, not
    reported. A broken link is a different defect with a different owner, and a
    checker that fails on one would fail on every master mid-authoring.
  - The master's own inline `**Gate:**` blocks are not scanned for `[~]`.
    `plan_has_blocked_gate()` keys on `### Stage N Gate` headings, which a master
    does not have; propagation through `plan_blocked()` covers the sub-plans' gates,
    which is where the blocked checks actually live.
  - It reads the vault, never the registry (DEC-011). A plans/ directory outside
    `Portfolio/*/*/plans` is not seen.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_UNIFY = _HERE.parent.parent / "portfolio" / "scripts" / "portfolio-unify.py"
_spec = importlib.util.spec_from_file_location("portfolio_unify", _UNIFY)
pu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pu)

# The staleness probe lives beside portfolio-unify.py, not beside this file, so a bare
# `import _staleness` resolves against sys.path[0] — this script's own directory — and
# raises. Guarded, that failure is silent, and the probe would pass a grep while warning
# nobody. Loaded by explicit path for the same reason `pu` is.
_STALE = _UNIFY.parent / "_staleness.py"


def _warn_if_stale():
    try:
        spec = importlib.util.spec_from_file_location("_staleness", _STALE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.warn_if_stale(__file__)
    except Exception:
        pass          # a probe that cannot load must never stop the command it advises on

# BL-107: the marker is recognised only at column 0. An indented one is the shape an
# author writes when tying it to the gate box it accepts, and it parses as absent.
INDENTED_ACCEPT = __import__("re").compile(r"^[ \t]+\*\*Blocked-accepted:\*\*", __import__("re").M)


def terminal_marker(text):
    """Which terminal marker a plan carries, or None. Contract predicates only."""
    if pu.ABANDONED_RE.search(text):
        return "abandoned"
    if pu.COMPLETED_RE.search(text):
        return "completed"
    return None


def register_entries(master_text, master_path):
    """[(subplan_path, status_char, entry_line)] for one master.

    Mirrors register_evidence()'s walk in plan-status-audit.py: a `### Sub-plan N`
    heading opens an entry, a `- **Status:**` line records its state, and a
    `- **Plan:**` line names the file. Same order, same regexes, same owner.
    """
    out, status_line = [], None
    for line in master_text.splitlines():
        if pu.SUBPLAN_RE.match(line):
            status_line = None
            continue
        sm = pu.STATUS_RE.match(line)
        if sm:
            status_line = line
            continue
        lm = pu.SUBPLAN_LINK_RE.match(line)
        if lm and status_line is not None:
            target = pu.link_target(lm.group(1))
            if target:
                try:
                    out.append(((master_path.parent / target).resolve(),
                                pu.STATUS_RE.match(status_line).group(1),
                                status_line.strip()))
                except (OSError, ValueError):
                    pass
            status_line = None
    return out


def audit(vault):
    findings = []
    for d in sorted(Path(vault).glob("Portfolio/*/*/plans")):
        for master in sorted(d.rglob("*.md")):
            if ".audit-backups" in master.parts:
                continue
            try:
                mtext = master.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            try:
                if not pu.is_master_plan(mtext, master):
                    continue
            except Exception:
                continue
            master_closed = bool(pu.COMPLETED_RE.search(mtext))
            for sub, state, entry in register_entries(mtext, master):
                if not sub.exists():
                    continue                      # disclosed: a dead link is not this check's defect
                stext = sub.read_text(encoding="utf-8", errors="replace")
                marker = terminal_marker(stext)
                done = pu.status_state(state) == "done"
                blocked, why = pu.plan_blocked(stext, sub)

                if done and marker is None:
                    findings.append(dict(
                        kind="REGISTER-AHEAD", path=str(sub), master=str(master),
                        detail="register marks this sub-plan [x] but the sub-plan carries "
                               "no terminal marker — the flip outran its close-out"))
                if marker == "completed" and not done:
                    findings.append(dict(
                        kind="REGISTER-BEHIND", path=str(sub), master=str(master),
                        detail=f"sub-plan carries **Completed:** but its register entry reads "
                               f"{entry!r} — BL-104's direction, invisible to status_lag"))
                if master_closed and blocked:
                    findings.append(dict(
                        kind="MASTER-OVER-BLOCKED", path=str(sub), master=str(master),
                        detail=f"master carries **Completed:** over this sub-plan: {why}"))
                if INDENTED_ACCEPT.search(stext):
                    findings.append(dict(
                        kind="ACCEPTANCE-UNPARSED", path=str(sub), master=str(master),
                        detail="**Blocked-accepted:** is indented, so it parses as absent "
                               "(BL-107) — move it to column 0"))
    return findings


def main():
    _warn_if_stale()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    ap.add_argument("--vault", help="override the vault directory")
    args = ap.parse_args()
    vault = args.vault or pu.vault_dir()
    findings = audit(vault)
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, sort_keys=True))
    else:
        for f in findings:
            print(f"  {f['kind']}  {f['path']}\n      {f['detail']}")
        print(f"Scanned {vault}; {len(findings)} finding(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
