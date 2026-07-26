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
     the criterion only to opt out of it. **Measured limit**, stated because a guard
     overstating itself is the failure this file exists to catch: a close-out evaluator
     showed the first version rejected a negation only *between* the two anchors, so
     "explicitly **not** bound by the **exit criterion** … recorded to the `backlog`"
     passed clean. It now also scans NEGATION_LOOKBEHIND characters before the match,
     which catches that and two other opt-out phrasings — but the guard remains
     strongest against *removal*, and an inversion worded far from the anchor could
     still slip past.)
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
  8. (Task 2.2) Both evaluator briefs — the Step 3.5 gate evaluator and the close-out
     evaluator — grade findings by severity (Blocking / Material / Minor) rather than
     bare pass/fail, the close-out stop condition is scoped to Blocking, and the
     reason a silent detector is not the bar is stated at both sites.
  9. (Task 2.2) The renderer's fallback remediation budget equals the default the
     skill prose documents — they are two copies of one number with nothing else
     coupling them.
 10. (Task 2.3 / P7) The behavioral-claim rule exists in honest-gates with both
     sub-rules, and is referenced at each of the three executing-plans sites that
     must consult it (Tier-1 brief, Tier-2 brief, docs-only skip), with the
     docs-only skip naming its executable-behavior exception. Checked as a set,
     printing each site — the rule this stage adds is not enforceable by a script
     (no validator can decide whether a sentence asserts behavior), so what IS
     mechanically checkable is that it is stated and wired everywhere it is
     consumed. That distinction is stated here rather than left to be inferred.
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
    r"\b(?:not|never|no|without|isn't|aren't|doesn't|don't|exempt|"
    r"rather than|instead of|unless|except|excluding|optional)\b",
    re.I,
)

# How far *before* a match to look for a negation. A Tier-2 review measured the guard
# and found it only rejected negations falling lexically BETWEEN the two anchors, so
# "explicitly **not** bound by the **exit criterion** … recorded to the `backlog`"
# passed clean — an inversion, which is the defect's most natural reintroduction.
# Deliberately tight: at 80+ chars it also swallows the legitimate contrastive
# "surfaced … *rather than* auto-fixed — but they are still bound by the …" that the
# real Light-plan text uses, and rejects true prose.
NEGATION_LOOKBEHIND = 30


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
        pre = hay[max(0, m.start() - NEGATION_LOOKBEHIND):m.start()]
        # Never read across a clause boundary. A negation belonging to the PREVIOUS
        # sentence does not negate this claim — without this, "…is *not* a merge
        # blocker: record each Material finding to the `backlog`" was rejected on the
        # strength of a "not" that was part of the sentence before it.
        pre = re.split(r"[.;:]\s|\s[-–—]\s", pre)[-1]
        if not NEGATION_RE.search(pre + m.group(0)):
            return True
    return False


def affirms_predicate(hay, anchor_pat, target_pat, window=200):
    """True when `target` follows `anchor` with no negation BETWEEN the two.

    For requirements whose subject is itself an absence — "when no `Scope:` exists,
    enumerate one" — `affirms()` rejects the subject's own "no", while a plain search
    leaves the predicate wide open. A Tier-2 review demonstrated the cost concretely:
    "When no `Scope:` field exists, the task must NOT attempt to enumerate one"
    satisfied the plain form, i.e. prose stating the exact opposite of the requirement
    passed the check meant to pin it.
    """
    for m in re.finditer(anchor_pat, hay, re.I | re.S):
        span = hay[m.end(): m.end() + window]
        tgt = re.search(target_pat, span, re.I | re.S)
        if not tgt:
            continue
        if not NEGATION_RE.search(span[:tgt.start()] + tgt.group(0)):
            return True
    return False


def affirmed_index(hay, pattern):
    """Index of the first match of `pattern` that is NOT negated, else -1.

    Only the preceding clause is scanned, never the match itself: the token this is
    used for — `no-fafo-debugging` — literally begins with "no", so including the
    match would make NEGATION_RE reject every genuine reference.
    """
    for m in re.finditer(pattern, hay, re.I | re.S):
        pre = hay[max(0, m.start() - NEGATION_LOOKBEHIND):m.start()]
        pre = re.split(r"[.;:]\s|\s[-–—]\s", pre)[-1]
        if not NEGATION_RE.search(pre):
            return m.start()
    return -1


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
        # Added after the Tier-2 stage review: Task 2.1's own review notes claimed the
        # master-plan clause had been swept into this set, and it had not. A sibling the
        # notes name but the sweep omits is the exact instance-vs-class gap this stage
        # exists to close — reproduced by the stage's own remediation test.
        ("master-plan sub-plan gate clause",
         section(text, r"\*\*On a sub-plan's close-out\*\*", r"\n4\. \*\*Version bumps")),
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

    # 5b — the set has a DERIVATION SOURCE, not just an instruction to name it (P1).
    # "name the set" was already present and was not enough: naming is not deriving,
    # and a set produced from recollection is how a class arrives one member short.
    check("the set is derived from the task's Scope: field",
          affirms(gate_fail, r"`?Scope:`?[^.]{0,80}field|field'?s? `?Scope:`?"),
          "step 2 does not name the task's Scope: field as the derivation source")
    check("a missing Scope: has a stated fallback",
          affirms_predicate(gate_fail, r"(no `?Scope:`?|when no scope)", r"enumerate"),
          "there is no procedure for deriving the set when the task declares no Scope:")
    check("the derived sweep command is recorded in the gate report",
          affirms(gate_fail, r"write the command down|command down in the gate report"),
          "the derivation is not required to be written down, so the next round re-guesses")
    check("every member found is fixed in the SAME round",
          affirms(gate_fail, r"every member[^.]{0,80}this round|fix every member"),
          "repair may still proceed one instance per round, which is oscillation")

    # 6b — no-fafo-debugging is routed AT the diagnosis step, not merely mentioned (P4).
    # A bare reference anywhere in the file would satisfy a naive grep and change
    # nothing, so position is the assertion: it must sit inside the gate-failure
    # block, and before the set is named.
    check("no-fafo-debugging is referenced in the gate-failure procedure",
          affirmed_index(gate_fail, r"no-fafo") != -1,
          "the gate-failure procedure never routes to no-fafo-debugging "
          "(or names it only to opt out)")
    # Anchor on the DERIVATION instruction, not on step 2's heading: the heading
    # ("Diagnose evidence-first, then name the set…") already contains "name the set"
    # and states the order itself, so anchoring there compares against the wrong point.
    fafo_at = affirmed_index(gate_fail, r"no-fafo")
    derive_at = gate_fail.lower().find("derive it")
    check("step 2's heading orders diagnosis before naming",
          affirms(gate_fail, r"diagnose evidence-first, then name the set"),
          "step 2 does not state diagnosis-before-generalization in its own heading")
    check("no-fafo is routed BEFORE the set is derived",
          fafo_at != -1 and derive_at != -1 and fafo_at < derive_at,
          "diagnosis is not ordered before generalization, so a wrong root cause "
          "yields a confidently-swept wrong set")
    check("the ordering rationale is stated, not just the order",
          affirms(gate_fail, r"wrong root cause[^.]{0,60}wrong set|set derived from a wrong"),
          "nothing explains why diagnosis must precede generalization")

    # 6c — BL-027's SECOND site. An independent evaluator deleted the Red-Green
    # diagnose-rule reference and this suite stayed green, so the site was unpinned.
    rg = section(text, r"\*\*Diagnose before fixing", r"\*\*Respect the cycle budget")
    check("no-fafo is routed at the Red-Green diagnose step too",
          affirmed_index(rg, r"no-fafo") != -1,
          "the Red-Green loop's diagnose rule does not route to no-fafo-debugging")

    # 7 — sweep: no instance-shaped framing survives anywhere under planning/skills/
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
    # 8 — (Task 2.2) the evaluator briefs. Two sites, checked as a set for the same
    # reason as #6: the gate evaluator and the close-out evaluator are siblings, and
    # giving only one of them a severity vocabulary leaves the other unsatisfiable.
    evaluator_sites = [
        ("gate evaluator (Step 3.5)",
         section(text, r"\*\*Independent evaluator for non-command checks",
                 r"\*\*Deep code review")),
        ("close-out evaluator",
         section(text, r"\*\*Independent evaluator pass \(default\)", r"\n4\. \*\*Bump")),
    ]
    for label, block in evaluator_sites:
        check(f"site present: {label}", bool(block), f"could not locate the {label} block")
        for level in ("Blocking", "Material", "Minor"):
            check(f"severity '{level}' in brief: {label}", level in block,
                  f"{label} does not brief the evaluator to return '{level}'")
        check(f"silent-detector rationale at: {label}",
              re.search(r"not a reachable state|essentially (always|never)|"
                        r"almost never", block, re.I) is not None,
              f"{label} does not say why 'no adverse findings' cannot be the bar")

    close_out = evaluator_sites[1][1]
    # One alternative only. A Tier-1 review flagged the second (`stop condition …
    # Blocking` within 80 chars) as dead weight that would also match "…is the stop
    # condition. Blocking findings especially matter" — prose that does NOT narrow the
    # condition. The precise form is the one that fires against the real text.
    check("close-out stop condition scoped to Blocking",
          affirms(close_out, r"Blocking finding is the stop condition"),
          "the close-out stop condition is not narrowed to Blocking findings — any FAIL "
          "still blocks merge, which is the unsatisfiable exit this task removes")
    # Plain search, NOT affirms(): this claim is affirmative in meaning but negative in
    # wording ("is *not* a merge blocker"), so the negation guard rejects it correctly
    # and uselessly. affirms() belongs only where a negated restatement would invert the
    # rule — using it reflexively is how a guard becomes a maintenance tax.
    #
    # The emphasis markers must be tolerated: the source reads `is *not* a merge
    # blocker`, so a literal `not a merge blocker` never matches. A Tier-1 review caught
    # this passing only via a loose `|residual` fallback that ordinary boilerplate
    # satisfies — i.e. the assertion was green while pinning nothing.
    check("close-out Material FAIL does not block merge",
          re.search(r"Material[\s\S]{0,120}is \*?not\*? a merge blocker",
                    close_out, re.I) is not None,
          "a Material-only FAIL is not distinguished from a Blocking one")
    check("close-out Material findings are recorded, not just mentioned",
          affirms(close_out, r"record each Material finding[\s\S]{0,40}backlog"),
          "Material findings are reported without an imperative to record them")

    # 9 — drift guard. The renderer hardcodes the default budget as its denominator when
    # `remediation_budget` is absent, which duplicates the number stated in the skill
    # prose. Nothing coupled them, so a prose edit to "default 3 rounds" would have left
    # the statusline silently rendering /2. Assert the two agree.
    doc_default = re.search(r"[Rr]emediation budget\s*—\s*default\s+(\d+)\s+rounds?",
                            flat(text))
    check("skill text states a default remediation budget", doc_default is not None,
          "could not find 'Remediation budget — default N rounds' in SKILL.md")
    renderer = SKILL.parent / "scripts" / "plan-progress.py"
    check("renderer present", renderer.is_file(), f"{renderer} not found")
    if doc_default and renderer.is_file():
        code = renderer.read_text(encoding="utf-8")
        # Anchored on the assignment line, not a character window: the first attempt used
        # `remediation_budget[\s\S]{0,300}?else (\d+)` and the explanatory comment added
        # between the two pushed the distance to 327, silently reporting "<not found>".
        m_fallback = re.search(r"^\s*total\s*=\s*budget\b.*?else\s+(\d+)",
                               code, re.M)
        check("renderer default budget matches the documented default",
              m_fallback is not None and m_fallback.group(1) == doc_default.group(1),
              f"SKILL.md documents a default of {doc_default.group(1)} rounds but the "
              f"renderer falls back to "
              f"{m_fallback.group(1) if m_fallback else '<not found>'}")

    # 10 — (Task 2.3 / P7) the behavioral-claim rule and its wiring, as a SET of sites.
    hg = SKILLS_ROOT / "honest-gates" / "SKILL.md"
    check("honest-gates present", hg.is_file(), f"{hg} not found")
    if hg.is_file():
        hg_text = flat(hg.read_text(encoding="utf-8"))
        check("honest-gates: behavioral claim is a verification claim",
              affirms(hg_text, r"sentence asserting behavior[\s\S]{0,120}"
                               r"claim that something was verified"),
              "honest-gates does not extend 'a gate is a claim that something was "
              "verified' to sentences asserting behavior")
        check("honest-gates: the citation requirement",
              re.search(r"cite the [`*]*file:line", hg_text, re.I) is not None,
              "no file:line citation requirement for a behavioral assertion")
        check("honest-gates sub-rule: a correction is a new claim",
              re.search(r"correction is a new claim", hg_text, re.I) is not None,
              "the 'a correction is a new claim' sub-rule is missing")
        check("honest-gates sub-rule: unrequested specificity",
              re.search(r"[Uu]nrequested specificity", hg_text) is not None,
              "the 'unrequested specificity' sub-rule is missing")
        # The rule's own honesty clause: it must say it is not a script, because
        # implying a validator exists would be the falsehood the rule forbids.
        check("honest-gates: discloses that no script can enforce this",
              re.search(r"cannot be a script", hg_text, re.I) is not None,
              "the section does not disclose that it is a discipline, not a validator")
        # The hard cases. A citation rule that only covers positive single-locus claims
        # leaves the most error-prone class — proving a negative — unguided.
        #
        # Plain search, NOT affirms(): this rule is *about* negative claims, so its prose
        # necessarily quotes them ("not a line", "no caller reaches X"). Third time this
        # distinction has come up — affirms() belongs only where a negated restatement
        # would invert the rule, never where the rule's subject matter is itself negative.
        check("honest-gates: absence claims cite the search, not a line",
              re.search(r"absence claim[\s\S]{0,240}(scope|grep)", hg_text, re.I)
              is not None,
              "no guidance for an absence claim ('nothing wires this'), where there is "
              "no single file:line and the claim is only as strong as the search scope")
        check("honest-gates: aggregate claims routed to the sweep rule",
              affirms(hg_text, r"(emergent|aggregate) [\s\S]{0,200}sweep"),
              "no guidance for a claim over a set, which the class-predicate rule "
              "already covers — leaving the two rules unconnected")

    p7_sites = [
        ("Tier-1 review brief",
         section(text, r"\*\*Quick review gate \(Tier 1\)", r"\n   - \*\*Critical")),
        ("Tier-2 review brief",
         section(text, r"\*\*Deep code review \(Tier 2\)", r"\*\*Decisions-conformance")),
        ("docs-only Tier-1 skip",
         section(text, r"\*\*Skip for trivial/non-code diffs",
                 r"7\. \*\*Commit after each green task")),
    ]
    for label, block in p7_sites:
        check(f"P7 site present: {label}", bool(block),
              f"could not locate the {label} block")
        check(f"P7 rule referenced at: {label}",
              affirms(block, r"behavioral claim|claims? about what the code does|"
                             r"behavioral claims"),
              f"{label} does not ask the reviewer to check behavioral claims")
    docs_skip = p7_sites[2][1]
    check("docs-only skip names the executable-behavior exception",
          re.search(r"[Ee]xception[\s\S]{0,120}executable behavior", docs_skip) is not None,
          "the docs-only skip does not carve out docs that assert executable behavior")
    # Every token in the message is actually checked — a Tier-1 review caught the first
    # version naming "commands" in the failure text while omitting it from the tuple.
    claim_kinds = ("commands", "flags", "env vars", "exit codes")
    missing_kinds = [tok for tok in claim_kinds if tok not in docs_skip]
    check("docs-only exception lists the claim kinds it covers",
          not missing_kinds,
          f"the exception does not name these claim kinds, so a docs diff asserting "
          f"them would still auto-skip Tier 1: {', '.join(missing_kinds)}")
    check("docs-only exception turns on asserting, not merely mentioning",
          re.search(r"asserting[\s\S]{0,40}not[\s\S]{0,20}mentioning|"
                    r"asserting a fact about", docs_skip, re.I) is not None,
          "the exception's trigger is not scoped to *asserting* a fact — 'naming' a "
          "flag would make nearly every docs diff in this file non-trivial")

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
