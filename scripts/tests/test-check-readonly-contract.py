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
# A minimal but REAL definition — it states each obligation the checker requires. The
# earlier version was a stub ("Create nothing in the target tree.") that satisfied the
# weak check this round replaced; keeping it would have meant the control fixture was
# built from what the old code accepted rather than from what the contract demands.
GOOD_AGENT = (f"# code-reviewer\n\n{ro.OPEN}\n## Read-only means no writes\n\n"
              "Create nothing in the target tree — not a report, not a scratch file, "
              "tracked or untracked. Modify and delete nothing, including files you "
              "created yourself in the same run. Reproductions and scratch work go to "
              "the session scratchpad, never beside the code. Reading and history "
              f"inspection are unrestricted.\n{ro.CLOSE}\n")


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
        # Built from the real control block so the case fails on the axis it tests —
        # the orphan exclusion — rather than on the definition being too thin.
        quoting = GOOD_AGENT.replace(
            "## Read-only means no writes\n",
            '## Read-only means no writes\n\nSix sites call this agent "(read-only)".\n')
        orph, defined, n = run(fake_root(tmp, GOOD_SITE, quoting))
        check(orph == [] and defined and n == 1,
              "the block quoting '(read-only)' while defining it is not counted as an "
              "orphan dispatch site")

    print("check-readonly-contract — a definition must say something:")
    with tempfile.TemporaryDirectory() as tmp:
        # Markers present, ordered, and empty. This passed the first cut — a
        # pointer-check whose own pointer resolved to nothing, which is the failure the
        # docstring says it exists to catch. The mutants missed it because they were
        # derived from the implementation (delete the block) rather than the requirement
        # (a definition exists AND states the obligations).
        _, defined, _ = run(fake_root(tmp, GOOD_SITE, f"# c\n\n{ro.OPEN}\n{ro.CLOSE}\n"))
        check(not defined, "an EMPTY contract block is not a definition")

    with tempfile.TemporaryDirectory() as tmp:
        long_but_silent = (f"# c\n\n{ro.OPEN}\n## Read-only\n\n" + ("Prose. " * 60)
                           + f"\n{ro.CLOSE}\n")
        _, defined, _ = run(fake_root(tmp, GOOD_SITE, long_but_silent))
        check(not defined,
              "a block long enough but naming none of the obligations is not a "
              "definition either — length alone would be a proxy for content")

    print("check-readonly-contract — the live tree:")
    live = ro.sites()
    check(len(live) >= 6,
          f"the population is enumerated from disk ({len(live)} dispatch sites)")
    check(ro.orphans() == [], f"no orphan site in the tree ({ro.orphans()})")
    check(ro.definition_present(), "the agent every site names carries the definition")
    # Scope guard, rewritten: the previous version filtered sites() for "android", but
    # sites() only ever walks SITE_DIRS, which cannot contain android-dev — so it passed
    # by construction whatever the exclusion did. A guarantee that cannot fail is not a
    # guard. This builds a root that DOES hold an android-dev-shaped hit and asserts the
    # sweep still ignores it.
    with tempfile.TemporaryDirectory() as tmp:
        root = fake_root(tmp, GOOD_SITE, GOOD_AGENT)
        (root / "android-dev").mkdir()
        (root / "android-dev" / "README.md").write_text(
            "| `APK_DIR` | `./build` | `/apks` (read-only) |\n")
        orph, defined, n = run(root)
        check(n == 1 and orph == [],
              "a Docker-mount '(read-only)' in android-dev is not swept in even when "
              "present — the exclusion is real, not an artifact of the glob")

    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
