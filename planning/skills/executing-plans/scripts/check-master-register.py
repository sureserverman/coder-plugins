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
vault when this was written: 7 sub-plans carried a register `[x]` with no terminal
marker of their own — two of them over sub-plans with ZERO tasks executed, standing since
2026-07-06. A point-in-time measurement, not a live invariant; the run's output is current.

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
  - A sub-plan carrying `**Blocked-accepted:**` with no `[~]` gate anywhere has both
    blocked kinds permanently suppressed, because `plan_blocked()` checks acceptance
    first and short-circuits. That is the contract predicate's behaviour, not this
    checker's, and changing it here would be a second definition of "blocked".
  - It reads the vault, never the registry (DEC-011). A plans/ directory outside
    `Portfolio/*/*/plans` is not seen.
"""

import argparse
import importlib.util
import json
import re
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
# The one pattern with no owner upstream: the contract anchors the marker at column 0
# (BL-107), so "the same marker, indented" has no representation there to import.
INDENTED_ACCEPT = re.compile(r"^[ \t]+\*\*Blocked-accepted:\*\*", re.M)


def terminal_marker(text):
    """Which terminal marker a plan carries, or None. Contract predicates only."""
    if pu.ABANDONED_RE.search(text):
        return "abandoned"
    if pu.COMPLETED_RE.search(text):
        return "completed"
    return None


def register_entries(master_text, master_path):
    """([(subplan_path, status_char, entry_line)], [unparsable Status lines]) for one master.

    Mirrors register_evidence()'s walk in plan-status-audit.py: a `### Sub-plan N`
    heading opens an entry, a `- **Status:**` line records its state, and a
    `- **Plan:**` line names the file. Same order, same regexes, same owner.
    """
    out, unparsed, status_line = [], [], None
    for line in master_text.splitlines():
        if pu.SUBPLAN_RE.match(line):
            status_line = None
            continue
        sm = pu.STATUS_RE.match(line)
        if sm:
            status_line = line
            continue
        anym = pu.ANY_STATUS_RE.match(line)
        if anym and not sm:
            # M4: in the Status POSITION but outside the contract's `[ xX~]` class. The
            # entry is dropped by the walk below, so both directions go unchecked for it
            # silently — the failure this reports rather than skips.
            unparsed.append(line.strip()[:90])
            status_line = None
            continue
        if pu.SUBPLAN_LINK_RE.match(line) and status_line is None:
            # F4: a `- **Plan:**` with no Status before it — the entry is dropped by the
            # walk, so BOTH directions go unchecked for it. Same defect as an
            # out-of-contract Status, different axis.
            unparsed.append(f"Plan line with no preceding Status: {line.strip()[:70]}")
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
    return out, unparsed


def master_gate_blocked(master_text):
    """M3: a `[~]` in the master's own `**Gate:**` blocks.

    `plan_has_blocked_gate()` keys on `### Stage N Gate` headings, which a master does
    not have — its cross-plan checks live under `**Gate:**` markers on each register
    entry. Those are the checks that prove integration BETWEEN sub-plans, so a blocked
    one is a class member, not a predicate limit.
    """
    out, in_gate = [], False
    for line in master_text.splitlines():
        if line.strip().startswith("**Gate:**"):
            in_gate = True
            continue
        if in_gate:
            gi = pu.GATE_ITEM_RE.match(line)
            if gi and gi.group(1) == "~":
                out.append(line.strip()[:90])
            elif line.strip() and not gi:
                in_gate = False
    return out


def audit(vault):
    findings, seen = [], set()

    def add(kind, sub, master, detail):
        key = (kind, str(sub), str(master), detail)
        if key in seen:                       # m2: one defect, one finding
            return
        seen.add(key)
        findings.append(dict(kind=kind, path=str(sub), master=str(master), detail=detail))

    for d in sorted(Path(vault).glob("Portfolio/*/*/plans")):
        masters = []
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
            masters.append((master, mtext))

        for master, mtext in masters:
            if pu.ABANDONED_RE.search(mtext):
                # An abandoned master's register is a historical record, not a live
                # contract: the decomposition is over, so demanding its entries flip
                # reports a red nobody can legitimately clear — the same failure as a
                # master gate `[~]` with no acceptance. Found triaging BL-110, where 5
                # of 16 findings were sub-plans of two claude-pacer masters their author
                # had abandoned (one superseded, one a reverted dead end).
                continue
            master_closed = bool(pu.COMPLETED_RE.search(mtext))
            entries, unparsed = register_entries(mtext, master)
            # F2: gating this on `master_closed` reproduced B1 — step 5 runs the check
            # BEFORE the Completed line exists. A master whose every listed entry is [x]
            # IS at close-out, which is decidable now, so the kind is live there too.
            at_closeout = bool(entries) and all(
                pu.status_state(st) == "done" for _, st, _ in entries)
            # A master's own `[~]` is acceptable on exactly the terms a sub-plan's is:
            # `plan_blocked()` checks `**Blocked-accepted:**` first and short-circuits, and
            # nothing here did the same, so a master that performed the prescribed act still
            # fired — a red clearable only by falsifying the `[~]`, which is the failure this
            # whole plan exists to forbid. Found at the close-out evaluator pass, on a master
            # accepted earlier the same day.
            master_accepted = pu.blocked_acceptance(mtext)
            for blocked_line in master_gate_blocked(mtext):
                if master_accepted:
                    continue
                if master_closed or at_closeout:
                    add("MASTER-GATE-BLOCKED", master, master,
                        f"master's own `[~]` register gate check is unrun while the "
                        f"decomposition is at close-out: {blocked_line}")
            for raw in unparsed:              # M4
                add("ENTRY-UNPARSED", master, master,
                    f"register entry's Status is outside the contract's `[ xX~]`, so the "
                    f"entry is unreadable and BOTH directions go unchecked for it: {raw!r}")

            listed = set()
            for sub, state, entry in entries:
                if not sub.exists():
                    continue                  # disclosed: a dead link is a different defect
                listed.add(sub.resolve())
                stext = sub.read_text(encoding="utf-8", errors="replace")
                marker = terminal_marker(stext)
                done = pu.status_state(state) == "done"
                blocked, why = pu.plan_blocked(stext, sub)

                if done and marker is None:
                    add("REGISTER-AHEAD", sub, master,
                        "register marks this sub-plan [x] but the sub-plan carries no "
                        "terminal marker — the flip outran its close-out")

                # B1 (Blocking): step 5 runs BEFORE the master's Completed line, so this
                # may not depend on master_closed or it is inert at the one gate that
                # could prevent the defect.
                if done and blocked and marker != "abandoned":
                    add("REGISTER-AHEAD-UNACCEPTED", sub, master,
                        f"register marks this sub-plan [x] but its completion was never "
                        f"proven and no acceptance stands: {why}")

                # M1: both directions, for EITHER terminal marker. An abandoned sub-plan
                # whose entry never flipped deadlocks the master silently.
                if marker is not None and not done:
                    add("REGISTER-BEHIND", sub, master,
                        f"sub-plan carries a terminal marker ({marker}) but its register "
                        f"entry reads {entry!r} — BL-104's direction, invisible to status_lag")

                if master_closed and blocked and marker != "abandoned":
                    add("MASTER-OVER-BLOCKED", sub, master,
                        f"master carries **Completed:** over this sub-plan: {why}")

                # M2: step 5's FIRST clause — every entry [x] — had no check at all.
                if master_closed and not done:
                    add("MASTER-OVER-UNFINISHED", sub, master,
                        f"master carries **Completed:** while this entry still reads "
                        f"{entry!r} — the decomposition was declared done over it")

                if master_closed and marker == "abandoned":
                    add("MASTER-CLOSED-OVER-ABANDONED", sub, master,
                        "master's **Completed:** enumerates this sub-plan, which is "
                        "**Abandoned:** — the register cannot tell the two apart, so the "
                        "close-out list must not read as though the work was done")

                if INDENTED_ACCEPT.search(stext):
                    add("ACCEPTANCE-UNPARSED", sub, master,
                        "**Blocked-accepted:** is indented, so it parses as absent "
                        "(BL-107) — move it to column 0")

            # M5: the membership axis. A sub-plan backlinking this master with no entry
            # in its register is the dangerous half — the master closes with every
            # LISTED entry [x] while a real sub-plan is unfinished.
            for cand in sorted(d.rglob("*.md")):
                if ".audit-backups" in cand.parts or cand.resolve() in listed:
                    continue
                if pu.is_not_a_plan(cand):
                    # Same predicate the classifier uses, from the same owner. Two
                    # scripts reading one corpus while disagreeing about what counts as
                    # a plan is the drift the one-owner rule exists to prevent.
                    continue
                try:
                    ctext = cand.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                bl = pu.MASTER_BACKLINK_RE.search(ctext)
                if not bl:
                    continue
                target = pu.link_target(bl.group(1))
                try:
                    same = target and (cand.parent / target).resolve() == master.resolve()
                except (OSError, ValueError):
                    same = False
                if same:
                    add("SUBPLAN-UNREGISTERED", cand, master,
                        "sub-plan backlinks this master but has no register entry in it — "
                        "the master can close with every listed entry [x] while this one "
                        "is unfinished")
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
