#!/usr/bin/env python3
"""`check-master-register.py` fires on each desync kind, and stays silent on the legal ones.

Every case is built from the RULE (master-plans.md steps 3 and 5), never from what the
checker currently does — a fixture shaped by observed behavior cannot falsify that
behavior. And every assertion is paired with its INVERSION: the same tree with the one
thing that makes it a finding removed. A test that only ever asserts "fires" passes
just as happily on a checker that fires on everything, which is the shape
`honest-gates` § *A test does not exist until its mutant dies* exists to forbid.
"""

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "scripts" / "check-master-register.py"

RAN, FAILURES = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    if not ok:
        FAILURES.append(f"{name}: {detail}")


MASTER = """# Master Plan: {title}
Date: 2026-01-01

## Sub-plans

### Sub-plan 1: The only one
- **Status:** {state}
- **Plan:** ./sub-01-thing-plan.md
- **Goal:** a thing
- **Depends on:** none
- **Blocks:** none

**Gate:**
- [{mgate}] the thing integrates
{closeout}"""

MASTER_PLAN_FIRST = """# Master Plan: T
Date: 2026-01-01

## Sub-plans

### Sub-plan 1: The only one
- **Plan:** ./sub-01-thing-plan.md
- **Status:** [x]

**Gate:**
- [ ] the thing integrates
"""

SUB = """# Project Plan: The only one
Date: 2026-01-01
Master: ./master-plan.md

### Task 1.1: do it
- **Status:** [x]
- **Test:** `true`

### Stage 1 Gate
- [{gate}] it works
{closeout}"""


def build(tmp, *, state, sub_closeout="", master_closeout="", gate="x", mgate=" ",
          extra_sub=None):
    """One master + one sub-plan on disk, in the vault layout the checker globs.

    `state` is the literal Status payload, so a case can pass an out-of-contract one.
    `extra_sub` writes a second sub-plan file that backlinks the master.
    """
    d = Path(tmp) / "Portfolio" / "area" / "proj" / "plans"
    d.mkdir(parents=True, exist_ok=True)
    (d / "master-plan.md").write_text(
        MASTER.format(title="T", state=state, closeout=master_closeout, mgate=mgate),
        encoding="utf-8")
    (d / "sub-01-thing-plan.md").write_text(
        SUB.format(gate=gate, closeout=sub_closeout), encoding="utf-8")
    if extra_sub is not None:
        (d / "sub-02-other-plan.md").write_text(extra_sub, encoding="utf-8")
    return d


def kinds(tmp):
    r = subprocess.run([sys.executable, str(CHECK), "--vault", tmp, "--json"],
                       capture_output=True, text=True)
    import json
    return {f["kind"] for f in json.loads(r.stdout)["findings"]}, r.returncode


def case(name, kind, fires, silent):
    """Assert `kind` appears for the `fires` tree and is absent from the `silent` one."""
    with tempfile.TemporaryDirectory() as t:
        build(t, **fires)
        got, rc = kinds(t)
        check(f"{name}: fires", kind in got, f"expected {kind}, got {got or 'none'}")
        check(f"{name}: exits non-zero when it fires", rc == 1 or kind not in got,
              f"found {kind} but exit was {rc}")
    with tempfile.TemporaryDirectory() as t:
        build(t, **silent)
        got, _ = kinds(t)
        check(f"{name}: mutant dies (inverted fixture is silent)", kind not in got,
              f"{kind} still reported after removing the thing that causes it: {got}")


def kinds_with_allow(tmp, allow_text):
    """Run the checker against a written acceptance file."""
    p = Path(tmp) / "allow.txt"
    p.write_text(allow_text, encoding="utf-8")
    r = subprocess.run([sys.executable, str(CHECK), "--vault", tmp, "--json",
                        "--allowlist", str(p)], capture_output=True, text=True)
    import json
    return {f["kind"] for f in json.loads(r.stdout)["findings"]}, r.returncode


def case_acceptance_allowlist():
    """A sub-plan closed DELIBERATELY partial must not be punished for saying so.

    MASTER-OVER-UNFINISHED cannot otherwise be cleared except by flipping an
    entry that is correctly `[ ]` — the checker demanding the disclosure be
    withdrawn (BL-111 case 2). Decided 2026-09-01: an allowlist with a mandatory
    reason, not a new register state, because the contract had just decided to
    stop adding marker dialects and because keying off the master's close-out
    prose would make free text load-bearing.

    Both halves matter. An acceptance that suppresses is only half a guard: one
    that suppresses the WRONG finding, or suppresses on a malformed line, is how
    an allowlist quietly becomes a blanket.
    """
    fires = dict(state="[ ]", master_closeout="\n**Completed:** 2026-02-01 — commits: a")
    with tempfile.TemporaryDirectory() as t:
        build(t, **fires)
        got, rc = kinds(t)
        check("allowlist: the finding fires with no acceptance on file",
              "MASTER-OVER-UNFINISHED" in got, str(got))
        check("allowlist: and exits non-zero", rc == 1)

    with tempfile.TemporaryDirectory() as t:
        build(t, **fires)
        got, rc = kinds_with_allow(
            t, "MASTER-OVER-UNFINISHED sub-01-thing-plan.md — closed partial, "
               "BL-002 still open, disclosed in the master's close-out\n")
        check("allowlist: an accepted finding is cleared",
              "MASTER-OVER-UNFINISHED" not in got, str(got))
        check("allowlist: and the run exits 0", rc == 0, f"rc={rc}")

    with tempfile.TemporaryDirectory() as t:
        build(t, **fires)
        got, _ = kinds_with_allow(
            t, "MASTER-OVER-UNFINISHED some-other-plan.md — a different plan\n")
        check("allowlist: an entry for a DIFFERENT plan does not suppress",
              "MASTER-OVER-UNFINISHED" in got, str(got))

    with tempfile.TemporaryDirectory() as t:
        build(t, **fires)
        got, _ = kinds_with_allow(
            t, "MASTER-OVER-BLOCKED sub-01-thing-plan.md — right plan, wrong kind\n")
        check("allowlist: an entry for a DIFFERENT kind does not suppress",
              "MASTER-OVER-UNFINISHED" in got, str(got))

    with tempfile.TemporaryDirectory() as t:
        build(t, **fires)
        got, _ = kinds_with_allow(t, "MASTER-OVER-UNFINISHED sub-01-thing-plan.md\n")
        check("allowlist: an entry with NO reason does not suppress",
              "MASTER-OVER-UNFINISHED" in got,
              "a reasonless line suppressed a finding — the reason is the "
              "whole point of the file")

    with tempfile.TemporaryDirectory() as t:
        build(t, **fires)
        got, _ = kinds_with_allow(
            t, "# a comment — not an entry\n\n   \n")
        check("allowlist: comments and blank lines suppress nothing",
              "MASTER-OVER-UNFINISHED" in got, str(got))

    # A missing acceptance file is the normal case, not an error.
    with tempfile.TemporaryDirectory() as t:
        build(t, **fires)
        r = subprocess.run([sys.executable, str(CHECK), "--vault", t, "--json",
                            "--allowlist", str(Path(t) / "nope.txt")],
                           capture_output=True, text=True)
        check("allowlist: a missing acceptance file degrades to suppressing nothing",
              r.returncode == 1 and "MASTER-OVER-UNFINISHED" in r.stdout)


def main():
    if not CHECK.exists():
        print(f"checker not found at {CHECK}", file=sys.stderr)
        return 1

    # Step 3: the entry flips only once the sub-plan carries a terminal marker.
    case("REGISTER-AHEAD", "REGISTER-AHEAD",
         fires={"state": "[x]", "sub_closeout": ""},
         silent={"state": "[x]", "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"})

    # BL-104: the mirror. A closed sub-plan whose entry never got flipped.
    case("REGISTER-BEHIND", "REGISTER-BEHIND",
         fires={"state": "[ ]", "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"},
         silent={"state": "[x]", "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"})

    # Step 5 / BL-081: a master closed over a sub-plan whose gate never ran.
    case("MASTER-OVER-BLOCKED", "MASTER-OVER-BLOCKED",
         fires={"state": "[x]", "gate": "~",
                "sub_closeout": "\n**Completed:** 2026-01-02 — done\n",
                "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"},
         # the inversion is the acceptance, at column 0 — the whole point of the marker
         silent={"state": "[x]", "gate": "~",
                 "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"
                                 "**Blocked-accepted:** 2026-01-02 — no hardware here\n",
                 "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"})

    # BL-107: the same acceptance, indented, parses as absent.
    case("ACCEPTANCE-UNPARSED", "ACCEPTANCE-UNPARSED",
         fires={"state": "[x]", "gate": "~",
                "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"
                                "  **Blocked-accepted:** 2026-01-02 — indented, so invisible\n"},
         silent={"state": "[x]", "gate": "~",
                 "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"
                                 "**Blocked-accepted:** 2026-01-02 — column 0\n"})


    # B1 (Blocking, found by the gate evaluator): step 5 runs BEFORE the master's
    # Completed line, so a check gated on master_closed is inert at the one moment the
    # rule invokes it. The fires-fixture has NO master close-out on purpose.
    case("REGISTER-AHEAD-UNACCEPTED", "REGISTER-AHEAD-UNACCEPTED",
         fires={"state": "[x]", "gate": "~",
                "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"},
         silent={"state": "[x]", "gate": "~",
                 "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"
                                 "**Blocked-accepted:** 2026-01-02 — no hardware\n"})

    # M2: step 5's FIRST clause — every entry [x] — had no check at all.
    case("MASTER-OVER-UNFINISHED", "MASTER-OVER-UNFINISHED",
         fires={"state": "[ ]", "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"},
         silent={"state": "[x]", "sub_closeout": "\n**Completed:** 2026-01-02 — done\n",
                 "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"})

    # M3: the master's own cross-plan **Gate:** checks are class members too.
    case("MASTER-GATE-BLOCKED", "MASTER-GATE-BLOCKED",
         fires={"state": "[x]", "mgate": "~",
                "sub_closeout": "\n**Completed:** 2026-01-02 — done\n",
                "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"},
         silent={"state": "[x]", "mgate": "x",
                 "sub_closeout": "\n**Completed:** 2026-01-02 — done\n",
                 "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"})

    # M4: an entry whose Status is outside `[ xX~]` was dropped by the walk in silence,
    # so BOTH directions went unchecked for it.
    case("ENTRY-UNPARSED", "ENTRY-UNPARSED",
         fires={"state": "[done]"},
         silent={"state": "[x]", "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"})

    # M5: the membership axis — a sub-plan backlinking the master with no register entry.
    ORPHAN = "# Project Plan: Other\nDate: 2026-01-01\nMaster: ./master-plan.md\n\n### Task 1.1: x\n- **Status:** [ ]\n"
    case("SUBPLAN-UNREGISTERED", "SUBPLAN-UNREGISTERED",
         fires={"state": "[x]", "sub_closeout": "\n**Completed:** 2026-01-02 — done\n",
                "extra_sub": ORPHAN},
         silent={"state": "[x]", "sub_closeout": "\n**Completed:** 2026-01-02 — done\n",
                 "extra_sub": ORPHAN.replace("Master: ./master-plan.md", "Master: ./other-master.md")})

    # M1 / the reviewer split: abandonment IS terminal for the register (master-plans.md
    # step 3 now names three members), so an unflipped abandoned entry is REGISTER-BEHIND
    # rather than legal — otherwise it deadlocks the master forever.
    case("REGISTER-BEHIND on abandonment", "REGISTER-BEHIND",
         fires={"state": "[ ]", "sub_closeout": "\n**Abandoned:** 2026-01-02 — retired\n"},
         silent={"state": "[x]", "sub_closeout": "\n**Abandoned:** 2026-01-02 — retired\n"})

    # An abandoned sub-plan is terminal too — closed, not unfinished.
    with tempfile.TemporaryDirectory() as t:
        build(t, state="[x]", sub_closeout="\n**Abandoned:** 2026-01-02 — retired by the owner\n")
        got, rc = kinds(t)
        check("**Abandoned:** is a terminal marker, not a desync",
              "REGISTER-AHEAD" not in got, f"got {got}")
        check("a wholly legal tree is CLEAN — no findings, exit 0",
              rc == 0 and not got,
              f"exit {rc} with findings {got}")

    # F5's own regression: the assertion above used to read `rc == 0 or got`, which any
    # finding satisfies, so nothing in the suite asserted a clean tree is clean — and a
    # false positive on a legal tree was invisible. Pin it with a second legal shape.
    with tempfile.TemporaryDirectory() as t:
        build(t, state="[x]", gate="~",
              sub_closeout="\n**Completed:** 2026-01-02 — done\n"
                           "**Blocked-accepted:** 2026-01-02 — no hardware\n")
        got, rc = kinds(t)
        check("an accepted blocked gate is clean, not a finding",
              rc == 0 and not got, f"exit {rc} with findings {got}")
    with tempfile.TemporaryDirectory() as t:
        build(t, state="[x]", gate="~", sub_closeout="\n**Abandoned:** 2026-01-02 — retired\n")
        got, rc = kinds(t)
        check("an abandoned sub-plan's unrun gate is clean (step 3's third marker)",
              rc == 0 and not got, f"exit {rc} with findings {got}")

    # The two scripts read one corpus and must agree about what a plan is. A design doc
    # backlinking a master is not an unregistered sub-plan — it is not a sub-plan at all.
    DESIGN = "# Design: something\nDate: 2026-01-01\nMaster: ./master-plan.md\n"
    with tempfile.TemporaryDirectory() as tmp:
        d = build(tmp, state="[x]", sub_closeout="\n**Completed:** 2026-01-02 — done\n")
        (d / "2026-01-01-thing-design.md").write_text(DESIGN, encoding="utf-8")
        got, rc = kinds(tmp)
        check("a design doc backlinking a master is not SUBPLAN-UNREGISTERED",
              "SUBPLAN-UNREGISTERED" not in got, f"got {got}")
    with tempfile.TemporaryDirectory() as tmp:
        d = build(tmp, state="[x]", sub_closeout="\n**Completed:** 2026-01-02 — done\n")
        # inversion: the same file under a plan name IS an unregistered sub-plan
        (d / "2026-01-01-thing-plan.md").write_text(DESIGN, encoding="utf-8")
        got, rc = kinds(tmp)
        check("mutant dies: the same content under a -plan.md name IS reported",
              "SUBPLAN-UNREGISTERED" in got, f"got {got}")


    # M3: MASTER-CLOSED-OVER-ABANDONED had no pair — it could fire and nothing proved it.
    case("MASTER-CLOSED-OVER-ABANDONED", "MASTER-CLOSED-OVER-ABANDONED",
         fires={"state": "[x]", "sub_closeout": "\n**Abandoned:** 2026-01-02 — retired\n",
                "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"},
         silent={"state": "[x]", "sub_closeout": "\n**Completed:** 2026-01-02 — done\n",
                 "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"})

    # M2: a master's own `[~]` is acceptable on the same terms a sub-plan's is. Without
    # this, the kind was unclearable except by falsifying the `[~]`.
    case("master acceptance clears MASTER-GATE-BLOCKED", "MASTER-GATE-BLOCKED",
         fires={"state": "[x]", "mgate": "~",
                "sub_closeout": "\n**Completed:** 2026-01-02 — done\n",
                "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"},
         silent={"state": "[x]", "mgate": "~",
                 "sub_closeout": "\n**Completed:** 2026-01-02 — done\n",
                 "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"
                                    "**Blocked-accepted:** 2026-01-03 — no hardware here\n"})

    # M3: ENTRY-UNPARSED's second branch — a `- **Plan:**` with no Status before it — was
    # unreachable in every fixture, because the template always emitted Status first.
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "Portfolio" / "area" / "proj" / "plans"
        d.mkdir(parents=True, exist_ok=True)
        (d / "master-plan.md").write_text(MASTER_PLAN_FIRST, encoding="utf-8")
        (d / "sub-01-thing-plan.md").write_text(
            SUB.format(gate="x", closeout="\n**Completed:** 2026-01-02 — done\n"), encoding="utf-8")
        got, _ = kinds(tmp)
        check("ENTRY-UNPARSED fires on a Plan line preceding its Status",
              "ENTRY-UNPARSED" in got, f"got {got}")


    # An abandoned master's register is history. Demanding entry flips on it is a red
    # nobody can clear — the same shape as an unaccepted master gate.
    case("an abandoned master's register is not enforced", "REGISTER-BEHIND",
         fires={"state": "[ ]", "sub_closeout": "\n**Abandoned:** 2026-01-02 — retired\n"},
         silent={"state": "[ ]", "sub_closeout": "\n**Abandoned:** 2026-01-02 — retired\n",
                 "master_closeout": "\n**Abandoned:** 2026-01-03 — superseded\n"})

    case_acceptance_allowlist()
    print(f"assertions run ({len(RAN)})")
    for n in RAN:
        print(f"  - {n}")
    if FAILURES:
        print("\nFAILURES:", file=sys.stderr)
        for f in FAILURES:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print(f"\nOK — {len(RAN)} assertions; every kind exercised here fires, and every\n     inverted fixture is silent. This proves the kinds the suite NAMES, not that the\n     checker's kind set is complete — completeness is the gate evaluator's judgment.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
