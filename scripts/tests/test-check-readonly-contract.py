#!/usr/bin/env python3
"""Fixture tests for scripts/check-readonly-contract.py.

The load-bearing cases are the ones proving the sweep REJECTS. The failure this guards
is quiet: "(read-only)" reads as meaningful whether or not anything defines it, so a
dispatch site pointing at nothing looks exactly like one pointing at a contract.

This validator's shape was chosen under `honest-gates` § "A test does not exist until its
mutant dies" — its opening rule is to ask whether the mechanism can decide the property
before writing the checker. "Does this paragraph define read-only?" cannot be decided by a
pattern; "is this occurrence next to the agent name, and does that agent carry a delimited
block?" can. So the cases below are structural, and the fixtures manipulate structure —
there is deliberately no fixture asserting that some prose 'reads like' a definition,
because no assertion of that kind would mean anything.

The sibling validator reached this shape only after two review rounds defeated a
prose-matching cut of it. This one started here.

Stdlib only.
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "check-readonly-contract.py"

spec = importlib.util.spec_from_file_location("ro", SCRIPT)
ro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ro)

FAILURES = []


def check(ok, msg):
    print(f"  {'ok' if ok else 'FAIL'}: {msg}")
    if not ok:
        FAILURES.append(msg)


def fake_root(tmp, site_line, agent_body):
    """A miniature repo: one dispatch site, one agent."""
    root = Path(tmp)
    (root / "planning" / "skills" / "executing-plans" / "references").mkdir(parents=True)
    (root / "git-github" / "agents").mkdir(parents=True)
    (root / "planning" / "skills" / "executing-plans" / "references" / "s.md").write_text(
        f"# Stage gate\n\n{site_line}\n")
    (root / "git-github" / "agents" / "code-reviewer.md").write_text(agent_body)
    return root


def run(root):
    """Point the module at a fixture root and collect its findings."""
    old_root, old_agent = ro.ROOT, ro.AGENT
    ro.ROOT = root
    ro.AGENT = root / "git-github" / "agents" / "code-reviewer.md"
    try:
        return sorted(ro.orphans()), ro.definition_present(), len(ro.sites())
    finally:
        ro.ROOT, ro.AGENT = old_root, old_agent


GOOD_SITE = "Dispatch `git-github:code-reviewer` (read-only) over the full stage diff."
GOOD_AGENT = (f"# code-reviewer\n\n{ro.OPEN}\n## Read-only means no writes\n\n"
              f"Create nothing in the target tree.\n{ro.CLOSE}\n")


def main():
    print("check-readonly-contract — the control:")
    with tempfile.TemporaryDirectory() as tmp:
        orph, defined, n = run(fake_root(tmp, GOOD_SITE, GOOD_AGENT))
        check(orph == [] and defined and n == 1,
              f"a site naming the agent + an agent carrying the block passes "
              f"(orphans={orph}, defined={defined}, sites={n})")

    print("check-readonly-contract — each half, removed alone:")
    with tempfile.TemporaryDirectory() as tmp:
        # The pointer is the agent name. Strip it and the adjective is unanchored.
        orph, defined, _ = run(fake_root(
            tmp, "Dispatch the reviewer (read-only) over the full stage diff.", GOOD_AGENT))
        check(len(orph) == 1 and defined,
              "a site that does NOT name the agent is an orphan — the adjective alone "
              "points nowhere")

    with tempfile.TemporaryDirectory() as tmp:
        # The pointer resolving to nothing is the same defect as no pointer.
        orph, defined, _ = run(fake_root(
            tmp, GOOD_SITE, "# code-reviewer\n\nRead-only, obviously. No block here.\n"))
        check(orph == [] and not defined,
              "an agent with no contract block fails — prose saying 'read-only' is not "
              "a definition, which is the whole reason this check exists")

    with tempfile.TemporaryDirectory() as tmp:
        orph, defined, _ = run(fake_root(
            tmp, GOOD_SITE, f"# c\n\n{ro.CLOSE}\nbody\n{ro.OPEN}\n"))
        check(not defined,
              "reversed markers are not a block — CLOSE before OPEN is rejected")

    print("check-readonly-contract — the definition does not fail its own check:")
    with tempfile.TemporaryDirectory() as tmp:
        # The block quotes the term it defines. Its interior must be excluded, or the
        # only finding this validator ever produces is itself.
        quoting = (f"# c\n\n{ro.OPEN}\n## Read-only\n\nSix sites call this agent "
                   f'"(read-only)" with no definition anywhere.\n{ro.CLOSE}\n')
        orph, defined, n = run(fake_root(tmp, GOOD_SITE, quoting))
        check(orph == [] and defined and n == 1,
              "the block quoting '(read-only)' while defining it is not counted as an "
              "orphan dispatch site")

    print("check-readonly-contract — the live tree:")
    live = ro.sites()
    check(len(live) >= 6,
          f"the population is enumerated from disk ({len(live)} dispatch sites)")
    check(ro.orphans() == [], f"no orphan site in the tree ({ro.orphans()})")
    check(ro.definition_present(), "the agent every site names carries the definition")
    # Scope guard: the Docker-mount sense must stay out, or the check produces findings
    # nobody can act on and readers learn to skip it.
    android = [p for p, _, _ in live if "android" in p.as_posix()]
    check(not android, f"android-dev's Docker-mount '(read-only)' stays out of scope "
                       f"({android})")

    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
