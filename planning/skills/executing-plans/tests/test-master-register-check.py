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

CHECK = Path(__file__).resolve().parents[4] / "scripts" / "check-master-register.py"

RAN, FAILURES = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    if not ok:
        FAILURES.append(f"{name}: {detail}")


MASTER = """# Master Plan: {title}
Date: 2026-01-01

## Sub-plans

### Sub-plan 1: The only one
- **Status:** [{state}]
- **Plan:** ./sub-01-thing-plan.md
- **Goal:** a thing
- **Depends on:** none
- **Blocks:** none

**Gate:**
- [ ] the thing integrates
{closeout}"""

SUB = """# Project Plan: The only one
Date: 2026-01-01
Master: ./master-plan.md

### Task 1.1: do it
- **Status:** [x]
- **Test:** `true`

### Stage 1 Gate
- [{gate}] it works
{closeout}"""


def build(tmp, *, state, sub_closeout="", master_closeout="", gate="x"):
    """One master + one sub-plan on disk, in the vault layout the checker globs."""
    d = Path(tmp) / "Portfolio" / "area" / "proj" / "plans"
    d.mkdir(parents=True, exist_ok=True)
    (d / "master-plan.md").write_text(
        MASTER.format(title="T", state=state, closeout=master_closeout), encoding="utf-8")
    (d / "sub-01-thing-plan.md").write_text(
        SUB.format(gate=gate, closeout=sub_closeout), encoding="utf-8")
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


def main():
    if not CHECK.exists():
        print(f"checker not found at {CHECK}", file=sys.stderr)
        return 1

    # Step 3: the entry flips only once the sub-plan carries a terminal marker.
    case("REGISTER-AHEAD", "REGISTER-AHEAD",
         fires={"state": "x", "sub_closeout": ""},
         silent={"state": "x", "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"})

    # BL-104: the mirror. A closed sub-plan whose entry never got flipped.
    case("REGISTER-BEHIND", "REGISTER-BEHIND",
         fires={"state": " ", "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"},
         silent={"state": "x", "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"})

    # Step 5 / BL-081: a master closed over a sub-plan whose gate never ran.
    case("MASTER-OVER-BLOCKED", "MASTER-OVER-BLOCKED",
         fires={"state": "x", "gate": "~",
                "sub_closeout": "\n**Completed:** 2026-01-02 — done\n",
                "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"},
         # the inversion is the acceptance, at column 0 — the whole point of the marker
         silent={"state": "x", "gate": "~",
                 "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"
                                 "**Blocked-accepted:** 2026-01-02 — no hardware here\n",
                 "master_closeout": "\n**Completed:** 2026-01-03 — sub-plans: 1\n"})

    # BL-107: the same acceptance, indented, parses as absent.
    case("ACCEPTANCE-UNPARSED", "ACCEPTANCE-UNPARSED",
         fires={"state": "x", "gate": "~",
                "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"
                                "  **Blocked-accepted:** 2026-01-02 — indented, so invisible\n"},
         silent={"state": "x", "gate": "~",
                 "sub_closeout": "\n**Completed:** 2026-01-02 — done\n"
                                 "**Blocked-accepted:** 2026-01-02 — column 0\n"})

    # An abandoned sub-plan is terminal too — closed, not unfinished.
    with tempfile.TemporaryDirectory() as t:
        build(t, state="x", sub_closeout="\n**Abandoned:** 2026-01-02 — retired by the owner\n")
        got, rc = kinds(t)
        check("**Abandoned:** is a terminal marker, not a desync",
              "REGISTER-AHEAD" not in got, f"got {got}")
        check("a wholly legal tree exits 0", rc == 0 or got, f"exit {rc} with findings {got}")

    print(f"assertions run ({len(RAN)})")
    for n in RAN:
        print(f"  - {n}")
    if FAILURES:
        print("\nFAILURES:", file=sys.stderr)
        for f in FAILURES:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print("\nOK — every desync kind fires, and every inverted fixture is silent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
