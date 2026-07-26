#!/usr/bin/env python3
"""Structure suite for the gate-remediation contract — run directly (CI convention):
    python3 planning/skills/executing-plans/tests/test-gate-remediation-contract.py

These are PROSE contracts, not behavior. The suite asserts that the skill text
states the rules an executor must follow at a failed gate; it cannot and does not
verify that an executor obeys them. Stated plainly because a structure suite that
implies behavioral coverage is the exact falsehood class this stage exists to fix
(`honest-gates`, and P7 of the gate-oscillation plan).

What it pins:
  1. The `If the gate fails` procedure defines a NUMERIC remediation-round budget
     that the plan may override.
  2. It names all three review severity levels (Critical / Important / Suggestion),
     reusing the taxonomy already in the file rather than inventing a second one.
  3. An exit criterion scoped to Critical findings — not "the detector returned
     silent", which is not a reachable state for a judgment agent — stated OUTSIDE
     the failure branch, so it governs every gate pass. (A Tier-1 review caught the
     first draft defining it only inside `If the gate fails`, which Step 3.5 never
     enters on an Important-only result: the common case passed with nothing
     recorded. Two checks guard against that returning, and they do different jobs:
     "exit criterion DEFINED outside the failure branch" is a *placement* check — it
     asserts the definition heading exists before the failure branch and nothing more.
     The *content* checks — "Important findings fixed-or-recorded" and the per-site
     "Importants bound to the exit criterion at: …" loop — are the ones that reject a
     negated restatement, since the defect's natural reintroduction is prose that names
     the criterion only to opt out of it.)
  4. It describes budget-exhaustion escalation carrying a residual list.
  5. It requires the class sweep to be re-run alongside the narrow re-verification.
  6. Every other site in the file that restates what happens to an Important finding
     is bound to the same criterion — the Light-plan pre-gate review and the
     Integration summary. These are siblings of the same defect class, which is why
     they are checked as a set rather than one at a time.
  7. A sweep over every file under planning/skills/: no file still frames gate repair
     as a single instance via the banned singular phrase (see BANNED_PHRASE below).
     Written as a sweep because that is the rule Stage 1 introduced — an
     instance-shaped check cannot fail on the siblings that make the class.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / "SKILL.md"
SKILLS_ROOT = HERE.parent.parent  # planning/skills/

# Assembled at runtime rather than written literally: this file lives inside the
# tree it sweeps, so a literal occurrence would make both this check and the
# Stage 2 gate's `! grep -rn ... planning/skills/` permanently red against the
# very test that enforces the rule.
#
# It must be `join`, not `"the culprit " + "task"`: CPython's peephole optimizer
# constant-folds adjacent string literals, so the concatenated form reappears whole
# in __pycache__/*.pyc — which the sweep below and the gate's `grep -r` both read.
# Found by this very sweep going red on its own bytecode. A `join` of separate
# constants is a runtime method call and is not folded.
BANNED_PHRASE = " ".join(("the", "culprit", "task"))

FAILURES = []
RAN = []


def check(name, ok, detail=""):
    RAN.append(name)
    if not ok:
        FAILURES.append(f"{name}: {detail or 'assertion failed'}")


# Word-boundary anchored: plain substring matching read "cannot" as "not " and
# "whenever" as "never " (a Tier-1 finding), which would have rejected true prose.
NEGATION_RE = re.compile(
    r"\b(?:not|never|without|no longer|isn't|aren't|doesn't|don't|"
    r"rather than|instead of|unless|except|excluding|optional)\b",
    re.I,
)


def flat(s):
    """Collapse whitespace runs so a wrapped phrase still matches a literal-space regex.

    Skill prose is hard-wrapped, so `**exit\\n   criterion**` is one phrase to a reader
    and two tokens to `re`. Stage 1's classifier hit the same class (wrapped checks
    truncated in both directions); every prose assertion below therefore runs against
    the flattened block, never the raw one.
    """
    return re.sub(r"\s+", " ", s)


def affirms(hay, pattern, flags=re.I | re.S):
    """True when `pattern` matches somewhere with no negation token inside the match.

    A guard a negated restatement can satisfy is not a guard: the natural way this
    defect returns is prose that names the rule only to opt out of it ("... are
    surfaced for triage, NOT bound to the exit criterion"). Any single clean match
    is enough — the same block may legitimately also contain negated prose.
    """
    for m in re.finditer(pattern, hay, flags):
        if not NEGATION_RE.search(m.group(0)):
            return True
    return False


def section(text, start_pat, end_pat):
    """Slice the text between two anchors; returns '' when the start is missing."""
    m = re.search(start_pat, text, re.I)
    if not m:
        return ""
    rest = text[m.start():]
    e = re.search(end_pat, rest[1:], re.I)
    raw = rest[: e.start() + 1] if e else rest
    return flat(raw)


def main():
    if not SKILL.is_file():
        print(f"FAIL: {SKILL} not found", file=sys.stderr)
        return 1
    text = SKILL.read_text(encoding="utf-8")

    gate_fail = section(text, r"\*\*If the gate fails", r"\*\*If the gate passes")
    check("gate-failure section present", bool(gate_fail),
          "no '**If the gate fails' … '**If the gate passes' block in SKILL.md")

    # Anchored on the DEFINITION heading, not the bare phrase. A Tier-1 review caught
    # the bare anchor matching the Tier-2 paragraph's inline forward-reference ("per the
    # **exit criterion** below") first, which inflated the slice to 2693 chars starting
    # mid-sentence and made the placement check nearly vacuous — it would still have
    # passed with the real definition deleted.
    exit_block = section(text, r"\*\*Exit criterion\s+—\s+what", r"\*\*If the gate fails")
    check("exit criterion DEFINED outside the failure branch", bool(exit_block),
          "no '**Exit criterion — what …' definition heading before '**If the gate "
          "fails' — a criterion defined only inside the failure branch never fires on "
          "an Important-only gate")

    # 1 — numeric round budget, overridable by the plan
    budget_nums = re.findall(r"\*\*(\d+)\s+rounds?\*\*|\b(\d+)\s+rounds?\b", gate_fail)
    round_nums = [n for pair in budget_nums for n in pair if n]
    check("numeric remediation-round budget", bool(round_nums),
          "no numeric round count in the gate-failure procedure")
    # Tightened after a Tier-1 finding: `...|budget` subsumed its own alternatives, so
    # the assertion passed on the word "budget" appearing anywhere in the section,
    # however far from the round count. Require the two to sit in one phrase.
    check("the round count is named as a budget",
          re.search(r"budget[^.]{0,80}\b\d+\s+rounds?|\b\d+\s+rounds?[^.]{0,80}budget",
                    gate_fail, re.I) is not None,
          "the numeric round count and the word 'budget' are not in the same sentence")
    check("plan may override the budget",
          re.search(r"(plan|Plan).{0,80}overrid", gate_fail, re.S) is not None,
          "the budget is not stated as overridable by the plan")
    check("budget is counted and reported",
          re.search(r"count(ed)?\b.{0,60}report|report.{0,60}count", gate_fail, re.I | re.S)
          is not None,
          "the budget is not required to be counted and reported")

    # 2 — the existing three-level severity taxonomy
    for level in ("Critical", "Important", "Suggestion"):
        check(f"severity level named: {level}", level in gate_fail,
              f"'{level}' absent from the gate-failure procedure")
    check("severity classification is a step",
          re.search(r"classif", gate_fail, re.I) is not None,
          "no severity-classification step before repair")

    # 3 — an exit criterion a non-deterministic detector can satisfy
    # Tightened after a Tier-1 finding: the old 400-char window let "Critical" satisfy
    # the check from an unrelated aside. Pin the actual pass condition instead.
    check("exit criterion turns on no Critical remaining",
          re.search(r"passes when\s+\*{0,2}no Critical", exit_block, re.I) is not None,
          "the exit criterion does not state that passing requires no Critical remaining")
    check("Important findings fixed-or-recorded",
          affirms(exit_block, r"Important[\s\S]{0,160}(fixed|recorded)[\s\S]{0,160}backlog"),
          "Important findings may be silently dropped — no affirmative fix-or-record rule")
    check("'no findings' rejected as the bar",
          re.search(r"not a reachable state|returned silent", exit_block, re.I) is not None,
          "the rationale for not using 'detector returned silent' is missing")

    # 6 — the sibling sites. Every other place in the file that restates what happens to
    # an Important finding is a member of the same defect class, so they are checked as a
    # SET (Stage 1's class-predicate rule): the first Tier-1 review of this task fixed the
    # Tier-2 site alone and the Light-plan sibling survived to the next round, which is the
    # exact oscillation this stage exists to end.
    sibling_sites = [
        ("Tier-2 stage review",
         section(text, r"\*\*Deep code review \(Tier 2\)", r"\*\*Decisions-conformance")),
        ("Light-plan pre-gate review",
         section(text, r"\*\*One review, not per-task", r"\*\*Both evaluator passes")),
        ("Integration summary (code-reviewer agent)",
         section(text, r"- \*\*git-github:code-reviewer agent\*\*", r"\n- \*\*")),
    ]
    for label, block in sibling_sites:
        check(f"site present: {label}", bool(block), f"could not locate the {label} block")
        check(f"Importants bound to the exit criterion at: {label}",
              affirms(block, r"exit criterion[\s\S]{0,220}backlog|"
                             r"backlog[\s\S]{0,220}exit criterion"),
              f"{label} describes Important findings without binding them to the exit "
              f"criterion and the backlog — findings can pass this path unrecorded")

    # 4 — escalation on exhaustion, carrying the residual list
    check("budget-exhaustion escalation",
          re.search(r"exhaust", gate_fail, re.I) is not None,
          "no budget-exhaustion path")
    check("escalation carries a residual list",
          re.search(r"residual", gate_fail, re.I) is not None,
          "escalation does not carry a residual list")
    check("exhaustion is a Stop condition",
          re.search(r"[Ss]top condition", gate_fail) is not None,
          "exhaustion is not tied to a Stop condition")

    # 5 — narrow re-verification plus the class sweep
    check("class sweep re-run alongside narrow re-verification",
          re.search(r"sweep", gate_fail, re.I) is not None,
          "the class sweep is not required at re-verification")

    # 6 — sweep: no instance-shaped framing survives anywhere under planning/skills/
    offenders = []
    scanned = 0
    # Every file, not just *.md — the Stage 2 gate runs `grep -r` over the whole
    # tree, and a sweep narrower than the gate it stands in for is a false green.
    # __pycache__ is excluded as generated, not as inconvenient: it is not a source
    # of prose, and its .pyc are rebuilt from the .py files already swept.
    for path in sorted(p for p in SKILLS_ROOT.rglob("*")
                       if p.is_file() and "__pycache__" not in p.parts):
        scanned += 1
        body = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(body.splitlines(), 1):
            if BANNED_PHRASE in line:
                rel = path.relative_to(SKILLS_ROOT.parent.parent)
                offenders.append(f"{rel}:{i}")
    check("sweep examined a non-empty set", scanned > 0,
          "no markdown files scanned — an empty sweep is not a pass")
    check(f"no {BANNED_PHRASE!r} under planning/skills/", not offenders,
          f"instance-shaped framing survives at: {', '.join(offenders)}")

    print(f"assertions run ({len(RAN)}), files swept: {scanned}")
    for name in RAN:
        print(f"  - {name}")
    if FAILURES:
        print("\nFAILURES:", file=sys.stderr)
        for f in FAILURES:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print("\nOK — gate-remediation contract present in skill text (prose contract only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
