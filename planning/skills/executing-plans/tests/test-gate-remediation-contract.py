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
 11. (dispatch-fidelity Stage 1) The `Parallel` field is DEFINED as a directive, not a
     capability: YES obligates dispatch, a lone ready task with no concurrent sibling is
     still dispatched, and no permissive gloss survives in the authoring skill. 11b keeps
     the SUB-PLAN-level `Parallel` (session/worktree concurrency) permissive, since it is
     a different mechanism sharing a name. 11c pins the same rule in the CONSUMING skill,
     which kept its own "|S| < 2 → execute sequentially" escape after Stage 1 fixed the
     definition — the sibling site a scope-limited sweep missed.
 12. (Stage 2, Task 2.1) Preflight probes dispatch with a throwaway subagent and
     enumerates a roster of every `Parallel: YES` task with its routed agent type; an
     unavailable dispatch fails Preflight rather than being resolved by inlining. 12b
     checks the two authoring sites as a set, since a template that never asks for a
     roster produces plans whose Preflight cannot be executed.
 13. (Stage 2, Task 2.2) Every per-task commit carries an executor trailer naming who ran
     the task, constrained to one physical line (git drops a trailer block at the first
     unparseable line), and the Status-flip rule is disclaimed as not being that record.
 14. (Stage 2, Task 2.3) The stage gate reports dispatched-vs-inline counts with a reason
     per inlined YES task, read off the trailers and reconciled against the roster — with
     an unparseable trailer counted as `unknown` rather than silently folded into either
     count, and a stated reason framed as disclosure rather than authorisation.
 15. (Stage 2, Task 2.4) An unperformable mandated dispatch or review is a Stop
     condition, inline substitution is refused as a resolution, and the decision is
     routed to the user with the three legitimate options named.
 16. (Stage 3, Task 3.1) A review is skipped for two reasons and no third — an explicit
     user opt-out or a trivial/non-code diff — and a code-reviewer that cannot be
     dispatched is routed to the Stop condition instead of excusing itself. The class
     check is a deny-sweep scoped to the review/evaluator SUBJECT, deliberately not to
     the "is not a gate failure" shape: the platform stage-verify line uses that shape
     correctly, because a platform verifier is conditionally applicable (not every
     project is Android) where a code reviewer always applies.
 17. (Stage 3, Task 3.2) The one surviving discretionary reason — the user opt-out — has
     to be EVIDENCED: the report quotes the user's own words, only the user can author
     one, and executor judgment is named as not constituting one. The trivial-diff reason
     is explicitly exempted from the quote, because it is checkable from the diff and a
     quote requirement over it would be unsatisfiable. Checked at all three skip sites as
     a set (DEC-005): a definition only its defining site honors is the Stage 1 defect.
 18. (Stage 3, Task 3.3) The review analogue of 14's dispatch ledger: both places a run
     claims it was reviewed — the stage gate report and the close-out report list — name
     the agent that ran each review, the diff it saw, and what excused any tier that did
     not run. Checked as a set over the two sites, each mutated at a different one of
     them so the set property is proved from both directions. The rationale is pinned
     alongside the rule, because a rule whose reason is dropped reads as formatting.

 Items 11-18 were added by the dispatch-fidelity plan, which also found this list had
 stopped being maintained: groups 11 through 13 shipped without entries, three separate
 reviews flagged it, and the first fix still omitted group 15 — a fourth instance, caught
 by the gate review. Coverage of this list is now asserted mechanically by
 test-contract-negation-mutations.py rather than remembered.
"""
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Overridable so the suite can be pointed at a COPY of the tree. That is what lets
# test-contract-negation-mutations.py verify these checks actually bind: it mutates a
# throwaway copy and re-runs this file against it. Without the override a mutation test
# has to edit the real tree and revert, where a crash mid-run leaves the repo corrupted.
SKILLS_ROOT = Path(os.environ.get("CONTRACT_SKILLS_ROOT", HERE.parent.parent))
SKILL = SKILLS_ROOT / "executing-plans" / "SKILL.md"

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
# The second half of the list is not padding: a requirement is most often softened
# rather than contradicted, and "is waived" / "though this is optional" negate a rule
# without using a single word from the first half. A review demonstrated three such
# inversions passing a check that had every token in the first half.
NEGATION_RE = re.compile(
    r"\b(?:not|never|no|without|isn't|aren't|doesn't|don't|exempt|"
    r"rather than|instead of|unless|except|excluding|optional|optionally|"
    r"waived?|waives|unnecessary|dropped|skipped|advisory|discretionary|"
    # `recommended` only. `may` was tried and reverted with evidence: it is the CORRECT
    # word at the sub-plan-level `Parallel` site, which is legitimately permissive
    # (group 11b), so banning it turned a true statement red. A negation list is
    # corpus-specific, not universal — recorded rather than asserted.
    r"recommended|"
    r"need not|nor)\b",
    re.I,
)

# The availability-based excuses for skipping a review (group 16). Scoped to the
# review/evaluator SUBJECT rather than to the sentence shape: "Absence of a match is not
# a gate failure" is the same grammar and is CORRECT about a platform stage-verify skill,
# which is conditionally applicable. `[^.\n]` spans never cross a sentence boundary, which
# is what keeps that line and the "If no matching skill is installed" hook out of the
# sweep. `fall(?:s|ing)?` rather than a plain `fall`: this file lives inside the tree the
# task's gate greps, so the literal phrase must not appear in it.
REVIEW_ESCAPE_RE = re.compile(
    r"(?:missing|absent|unavailable|uninstalled)\s+(?:code-)?(?:reviewer|evaluator)"
    r"|(?:reviewer|evaluator)[^.\n]{0,40}\b(?:isn't|is not|not)\s+installed"
    r"|fall(?:s|ing)? back to the goal-evaluator"
    r"|(?:review|reviewer|evaluator)[^.\n]{0,60}(?:is|are)\s+not\s+a\s+gate\s+failure",
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


# ASYMMETRIC on purpose — the two directions are not the same grammatical question, and a
# single boundary set gets one of them wrong:
#
#   backward  "The gate report never skips a stage, AND a reason for every inlined task
#             is stated" — the preceding comma-joined clause is a SEPARATE assertion, and
#             its `never` must not reject the claim beside it. So a comma ends the span.
#   forward   "…a reason for every inlined task, THOUGH this is not mandatory" — a
#             trailing clause MODIFIES the claim, so it belongs inside the screened span.
#             A comma must therefore NOT end it; only a sentence does.
#
# `:` is a backward boundary but never a forward one: "`Parallel: YES`" puts a colon
# inside the requirement's own text, and treating it as a boundary truncated the forward
# span right before the trailing qualifier — which is precisely how three constructed
# inversions escaped a version of this helper that used one symmetric set.
CLAUSE_START = re.compile(r"[.;:,]\s|\s[-–—]\s|\*\*\s|\bso\b|\brather\b|\bthough\b")
SENTENCE_END = re.compile(r"[.;]\s|\.\*\*|\s[-–—]\s")


def affirms_claim(hay, target_pat):
    """True when `target` appears in a clause that carries no negation.

    THE default for a prose requirement. Prefer it over `affirms` / `affirms_predicate`.

    Those two both let the CHECK AUTHOR pick how far to screen — `affirms` looks
    NEGATION_LOOKBEHIND characters back, `affirms_predicate` screens only the span
    between two author-chosen anchors — and three separate Criticals on the
    dispatch-fidelity branch were all the same bug wearing different window sizes:
      * an inversion placed BEFORE `affirms_predicate`'s anchor is never examined
        (Task 2.2: "never who did it" → "including who did it" passed clean);
      * a fixed character window anchored on a repeated phrase bleeds across bullets,
        so a sibling bullet's unnegated opening satisfies an `any()` over windows
        (Task 2.3: "and a reason for…" → "and NO reason for…" passed clean);
      * every window size in this file (120 … 500) was tuned to the prose as it stood
        that day, so the next legitimate clarification breaks the guard, not the rule.

    A claim lives in a clause, so the clause is the unit to screen. The span runs from
    the last clause boundary before the match to the END of the match, which is what
    catches both a negated verb ("does not require") and a negated object ("no reason").

    Use `affirms_predicate` ONLY when the requirement's own subject is an absence
    ("when no concurrent sibling exists, dispatch anyway") — there the clause
    legitimately contains a negation and screening it would reject true prose.
    """
    for m in re.finditer(target_pat, hay, re.I | re.S):
        starts = [b.end() for b in CLAUSE_START.finditer(hay[:m.start()])]
        # BOTH ends derived from the text. The first cut of this helper sliced back to the
        # previous boundary but stopped dead at m.end(), so a negation TRAILING the match
        # inside the same clause escaped — "…a reason for every inlined task, though this
        # is not mandatory" passed clean. That is the identical defect the helper was
        # written to kill (an author-chosen span edge), surviving on the side nobody
        # looked at. A review found it by constructing inversions rather than reading the
        # code. If one edge is derived and the other is picked, the guard is only as good
        # as the picked one.
        after = SENTENCE_END.search(hay, m.end())
        span = hay[(starts[-1] if starts else 0): (after.start() if after else len(hay))]
        # Blank out `code spans` first: they hold literals, not prose. The rule "the user
        # can re-mark the tasks `Parallel: NO`" names a FIELD VALUE, and reading its `NO`
        # as a negation rejected the sentence — the same mistake as treating the colon in
        # `Parallel: YES` as a clause boundary. A guard over prose must screen prose only.
        if not NEGATION_RE.search(re.sub(r"`[^`]*`", " ", span)):
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

    # 11 — (Task 1.2) The `Parallel:` field is defined as a DIRECTIVE, not a capability.
    # The defect: planning-projects glossed it "can a sub-agent run this concurrently?"
    # while executing-plans says "Dispatch". An executor reading the definition inferred
    # no obligation and ran 18 tasks inline despite 5 marked YES. Anchored on the
    # structural claim rather than one sentence (BL-031).
    pp = SKILLS_ROOT / "planning-projects" / "SKILL.md"
    pp_text = flat(pp.read_text(encoding="utf-8")) if pp.is_file() else ""
    check("planning-projects/SKILL.md is readable", bool(pp_text),
          "cannot verify the Parallel-field contract without the authoring skill")
    check("the Parallel field is stated as an instruction to the executor",
          affirms(pp_text, r"Parallel\*\*? field[^.]{0,120}(directive|instruction)"
                           r"|(directive|instruction) to the executor"),
          "the authoring skill does not say the field is a directive")
    check("YES obligates dispatch",
          affirms(pp_text, r"YES obligates dispatch|it is dispatched"),
          "the authoring skill does not say YES obligates dispatch")
    # The half that matters in the common case: most stages have ONE ready task, so if
    # "nothing to run alongside" excuses inlining, the field stays optional in practice.
    # affirms_predicate, NOT affirms: the subject is itself an absence ("NO concurrent
    # sibling"), so the negation guard would reject the very wording that satisfies the
    # requirement. Screen the predicate instead.
    check("a lone ready task with no concurrent sibling is still dispatched",
          affirms_predicate(pp_text, r"no concurrent sibling", r"still dispatched"),
          "the no-sibling case is unaddressed, so the field reads optional whenever a "
          "stage has one ready task — which is the common case")
    # Presence checks alone are not enough: a mutation test showed that deleting one
    # affirming sentence while leaving another elsewhere leaves the file CONTRADICTING
    # itself and the suite still green. So also deny the permissive phrasings outright —
    # this catches a restatement reappearing in a different sentence, which is how the
    # rule would most naturally erode. Scoped to *dispatch* permissiveness, so the
    # legitimate "executing-plans may still delegate a NO task on its own
    # context-hygiene criteria" is untouched.
    check("no permissive gloss survives in the authoring skill",
          not re.search(r"can a sub-agent run this concurrently|it can be dispatched",
                        pp_text, re.I),
          "a permissive gloss of the Parallel field is still present")
    # Scoped to the YES bullet, NOT the whole file. A file-wide keyword ban false-positives
    # on the legitimate NO-task rule — "executing-plans may still delegate it ... at the
    # executor's discretion" is correct English for sanctioned behavior, and a Tier-2 review
    # reproduced the failure against a reasonable paraphrase of it. Protect the specific
    # claim, not every occurrence of ordinary phrasing.
    #
    # Honest limit: this narrows the false-positive surface, it does not make the check
    # evasion-proof. Arbitrary paraphrase inside the YES bullet ("left to the executor's
    # judgment") can still slip a regex; the affirming checks above are what carry the
    # requirement, and this is a backstop against the most likely regression, not a proof.
    yes_bullet = section(pp_text, r"- \*\*YES\*\* if the task has no unfinished",
                         r"- \*\*NO\*\* if it")
    check("the YES bullet was locatable for scoped scanning", bool(yes_bullet),
          "could not isolate the YES bullet — the scoped deny-check is not running")
    permissive = re.search(
        r"may be dispatched|need not be dispatched|dispatch is optional"
        r"|at the executor.s discretion|left to the executor.s judgment"
        r"|optional|inlined instead", yes_bullet, re.I)
    check("no phrasing makes YES-task dispatch discretionary",
          permissive is None,
          f"discretionary phrasing inside the YES bullet: {permissive.group(0) if permissive else ''}")

    # The third format doc. light-plan-format.md legitimately has NO Parallel field, and
    # that exclusion was named in the plan's gate but pinned nowhere — the exact
    # "sibling site the notes name but the sweep omits" class this file warns about a few
    # checks above, recurring inside the task meant to close it.
    lpf = SKILLS_ROOT / "planning-projects" / "references" / "light-plan-format.md"
    if lpf.is_file():
        lpf_text = flat(lpf.read_text(encoding="utf-8"))
        check("light-plan-format.md documents the field's ABSENCE, not a permissive gloss",
              re.search(r"no fan-out|no Risk/Rollback/Blocks/Parallel", lpf_text, re.I)
              is not None,
              "light-plan-format.md no longer documents that Light plans have no Parallel field")
        check("light-plan-format.md never introduces a YES/NO Parallel gloss",
              not re.search(r"Parallel:\s*(YES|NO)\b", lpf_text),
              "a task-level Parallel value appeared in the Light format, which has no such field")

    # 11b — TASK-level `Parallel` (subagent dispatch, obligatory) and SUB-PLAN-level
    # `Parallel` (session/worktree concurrency, permissive) are different mechanisms that
    # share a field name. executing-plans' own master-plan section says sub-plans "may run
    # concurrently (separate sessions or worktrees)", so the permissive wording in
    # master-plan-format.md is CORRECT and must survive. Without this, the next sweep for
    # permissive dispatch language "fixes" it and silently contradicts the master model.
    mpf = SKILLS_ROOT / "planning-projects" / "references" / "master-plan-format.md"
    if mpf.is_file():
        check("sub-plan-level Parallel stays session-scoped, not subagent dispatch",
              affirms(flat(mpf.read_text(encoding="utf-8")),
                      r"separate session/worktree|separate session"),
              "master-plan-format.md no longer scopes sub-plan Parallel to sessions — a "
              "sweep may have collapsed it into the task-level dispatch obligation")

    # 11c — the CONSUMING skill's own copy of the defect. Stage 1 rewrote the field's
    # definition in planning-projects, but `dispatching-parallel-agents` Phase 1 still
    # said "|S| < 2 → execute sequentially" and listed "|S| = 1 — no parallelism; just
    # execute" under *When NOT to use this skill*. So an executor that read the fixed
    # definition, obeyed `executing-plans`' "dispatch via dispatching-parallel-agents",
    # and opened that skill was told to inline after all — the field's authoring site and
    # its dispatch site disagreeing is the same contradiction Stage 1 exists to remove,
    # one file downstream. Found while dispatching Stage 2's own lone YES task, which
    # this line would have blocked.
    dpa = SKILLS_ROOT / "dispatching-parallel-agents" / "SKILL.md"
    dpa_text = flat(dpa.read_text(encoding="utf-8")) if dpa.is_file() else ""
    check("dispatching-parallel-agents/SKILL.md is readable", bool(dpa_text),
          "cannot verify the lone-task dispatch rule without the dispatch skill")
    # affirms_predicate for the same reason as the planning-projects sibling above: the
    # subject is an absence ("no concurrent sibling" / "|S| = 1"), so a negation screen
    # over the whole phrase would reject the wording that satisfies it.
    check("a lone dispatchable task is still dispatched, not returned to the caller",
          affirms_predicate(dpa_text, r"\|S\| = 1", r"single dispatch"),
          "the dispatch skill does not state that |S| = 1 still dispatches")
    check("only an EMPTY set returns control to the caller",
          affirms(dpa_text, r"\|S\| = 0 returns control to the caller"),
          "the dispatch skill does not scope the early return to |S| = 0")
    banned_dpa = re.search(r"\|S\| < 2|no parallelism; just execute", dpa_text)
    check("no threshold makes a lone YES task skip dispatch",
          banned_dpa is None,
          f"the |S|<2 escape is back in the dispatch skill: "
          f"{banned_dpa.group(0) if banned_dpa else ''}")

    # 12 — (Task 2.1) Preflight declares the dispatch roster and probes the capability.
    # The defect: an executor ran all 18 tasks of a plan inline although 5 carried
    # `Parallel: YES`, and the violation left no trace — an inlined task and a dispatched
    # task produce byte-identical artifacts, so the diff, the commits and every gate look
    # the same either way. Nothing downstream can detect the substitution, so the fix has
    # to run *upstream*: Preflight writes the roster down before any work, which turns a
    # silent omission into a contradiction of a written list, and probes dispatch there,
    # which moves "dispatch isn't available here" from close-out (where the executor
    # decided for the user) to the one place that is already a hard stop.
    #
    # Anchored on the structural claims — a sweep over the task set, a probe returning a
    # fixed string, an unavailable dispatch failing the gate — rather than on verbatim
    # sentences (BL-031).
    preflight = section(text, r"## Phase 2 — Preflight", r"## Phase 3 — Stage execution")
    check("Preflight section present", bool(preflight),
          "no '## Phase 2 — Preflight' … '## Phase 3 — Stage execution' block in SKILL.md")
    check("Preflight probes dispatch with a throwaway subagent",
          affirms(preflight, r"throwaway subagent[\s\S]{0,240}(fixed string|DISPATCH-OK)"),
          "Preflight does not dispatch a throwaway subagent returning a fixed string — "
          "dispatch availability is assumed rather than proven")
    # Anchored on the probe STEP, not on the phrase anywhere in Preflight: the bullet list
    # above the step already says "Dispatch works in this session", so a bare search was
    # satisfied by the summary line and survived a mutation that gutted the step itself.
    check("the probe proves dispatch in THIS session",
          affirms_predicate(preflight, r"\*\*Probe the capability",
                            r"works in \*?this\*? session", window=500),
          "the probe step does not scope the proof to the running session, so a past "
          "success — or an assumption — would count")
    # The half that decides who owns the outcome. Without it a failed probe is just a
    # note, and the executor silently substitutes inline execution — the original defect.
    check("an unavailable dispatch is a Preflight failure",
          affirms(preflight, r"dispatch is unavailable[\s\S]{0,120}Preflight fails"),
          "an unavailable dispatch does not fail Preflight, so the run continues inline "
          "and the user never gets the decision")
    # Plain search, NOT affirms(): the claim is affirmative in meaning but negative in
    # wording ("is not a resolution"), so the negation guard would reject it correctly and
    # uselessly — the same distinction drawn at the close-out checks above.
    check("inline substitution is refused as a resolution",
          re.search(r"[Ss]ubstituting inline execution[\s\S]{0,80}not a resolution",
                    preflight) is not None,
          "nothing forbids the executor from resolving a failed probe by inlining on its "
          "own authority")
    # The roster must quantify over the plan's whole task set. A check that names one
    # task cannot fail on its siblings — the instance-vs-class rule this suite enforces
    # elsewhere, applied to the declaration itself.
    check("the roster sweeps every task in the plan",
          affirms(preflight,
                  r"[Ss]weep \*{0,2}every task in the plan\*{0,2}[\s\S]{0,200}"
                  r"[`*]*Parallel:[`*]*\s*field reads [`*]*YES"),
          "Preflight does not enumerate every Parallel: YES task across the whole plan")
    check("each rostered task carries its routed agent type and the routing source",
          affirms(preflight,
                  r"subagent_type[`*]* it routes to per[\s\S]{0,120}stack-routing\.md"),
          "the roster does not pair each task with the subagent type from the "
          "stack-routing table, so it records an intent no one can check")
    # affirms_predicate, not affirms: the subject is itself an absence ("an empty
    # roster"), and the surrounding prose necessarily says "rather than … never", which
    # the negation screen would reject.
    check("an empty roster is written down, not omitted",
          affirms_predicate(preflight, r"empty roster is a legitimate result",
                            r"write [`*]*0 tasks"),
          "a plan with no Parallel: YES task produces no line at all, so 'nobody looked' "
          "and 'nothing to dispatch' are indistinguishable")

    # 12b — the authoring side. A plan template that never asks for a roster produces
    # plans whose Preflight the reader above cannot execute, so the two sites are checked
    # as a SET: the Phase 1 checklist (what the planner verifies) and the plan template
    # (what the planner writes into the file). Fixing one and leaving the other is the
    # sibling-survival pattern this file exists to catch.
    pp_preflight_sites = [
        ("planning-projects Phase 1 checklist",
         section(pp_text, r"### Preflight checklist", r"## Phase 2 — Stage Breakdown")),
        # Lookbehind, not a bare anchor: "### Preflight checklist" contains "## Preflight"
        # as a substring and matches ~250 lines earlier, which would silently slice the
        # wrong block and check the same site twice.
        ("planning-projects plan template",
         section(pp_text, r"(?<!#)## Preflight\b", r"\*\*Test-scope commands\*\*")),
    ]
    for label, block in pp_preflight_sites:
        check(f"site present: {label}", bool(block),
              f"could not locate the {label} Preflight block")
        check(f"dispatch probe required at: {label}",
              affirms(block, r"throwaway subagent[\s\S]{0,120}fixed string"),
              f"{label} does not require a throwaway-subagent probe, so a plan authored "
              f"from it carries no capability check")
        check(f"dispatch roster required at: {label}",
              affirms(block, r"[Ee]very [`*]*Parallel:\s*YES[`*]*\s*task[\s\S]{0,160}"
                             r"subagent[ _]type"),
              f"{label} does not require every Parallel: YES task to be listed with its "
              f"routed subagent type")

    # 13 — (Task 2.2) The per-task commit records WHO executed the task.
    # This is the finding that makes group 12 enforceable. The roster declares an intent
    # before the work; without a matching record after it, nothing can be compared against
    # that declaration — the diff, the `Status: [x]` flip and the commit subject are
    # byte-identical whether a task ran inline or in a subagent. So the trailer is the
    # only artifact that distinguishes them, which is why both the commit rule AND the
    # Status-flip rule are checked: the flip is where a reader would *expect* the record
    # to live, and saying plainly that it is not there is what sends them to the trailer.
    commit_rule = section(text, r"7\. \*\*Commit after each green task",
                          r"### Step 3\.4")
    check("Step 3.3 commit rule located", bool(commit_rule),
          "could not slice rule 7 — the executor-trailer checks are not running")
    check("every per-task commit carries an executor trailer",
          # Either order — the paraphrase control caught the fixed one: "an executor
          # trailer is required on every per-task commit" says the same thing backwards.
          affirms_claim(commit_rule,
                        r"every per-task commit[^.]{0,60}executor trailer"
                        r"|executor trailer[^.]{0,60}every per-task commit"),
          "the commit convention does not require an executor trailer, so who ran a task "
          "is recorded nowhere")
    # Both values, checked as a set. A trailer that only ever names dispatched agents is
    # satisfied by omitting it on the inlined tasks — which is exactly the run this plan
    # exists to make visible. These two are literal-token *presence* checks (a trailer
    # value has no negated restatement), so they fail on removal only — the same honest
    # limit the `site present:` locators above carry. The five substantive claims around
    # them are the ones verified against negation.
    for form, pat in (("inline", r"Executor: inline"),
                      ("dispatched — <subagent_type>",
                       r"Executor: dispatched [—-] .{0,20}subagent_type")):
        check(f"trailer form documented: {form}",
              re.search(pat, commit_rule) is not None,
              f"the '{form}' trailer form is not documented, so the convention cannot "
              f"distinguish an inlined task from a dispatched one")
    # Plain search, not affirms(): the claim is affirmative in meaning and negative in
    # wording ("not the routing table's suggestion"), same as the group-12 sibling.
    check("the trailer names the agent that actually ran, not the routed one",
          re.search(r"actual [`*]*subagent_type[`*]* that ran[\s\S]{0,80}"
                    r"not the routing table", commit_rule) is not None,
          "nothing distinguishes what was planned from what happened, so a trailer copied "
          "from the roster would read green on a run that dispatched nothing")
    # The constraint that makes the trailer machine-readable at all. A Tier-1 review ran
    # `git log --format='%(trailers:key=Executor,valueonly)'` against the two commits that
    # had already been written under this convention and got EMPTY for both: their
    # `Executor:` line wrapped, and git stops parsing a trailer block at the first
    # non-trailer line. A documented check that silently returns nothing is worse than no
    # check, so the single-line rule is pinned, not left as authoring folklore.
    check("the trailer is constrained to one physical line",
          affirms(commit_rule, r"one physical line"),
          "nothing forbids a wrapped trailer, so the reason-carrying form — the one case "
          "this whole rule exists for — drops out of %(trailers:...) unnoticed")
    # Measured limit: the requirement is stated at TWO sites (the form list and the prose
    # sentence), and this check is satisfied by either. Negating only the prose therefore
    # leaves it green — correctly, since the form list still documents the case. The
    # mutation that rejects it has to negate both, which is what was actually run.
    check("a failed dispatch finished inline is recorded as such",
          affirms(commit_rule, r"dispatch failed"),
          "a dispatch that failed and was finished inline has no recorded form, so the "
          "substitution is invisible again")
    # The honest-gates coupling: the trailer's value is that it can be compared, and a
    # false trailer is worse than a missing one because it forecloses the comparison.
    check("a misstated trailer is called worse than none",
          affirms(commit_rule, r"trailer that misstates[\s\S]{0,80}worse than none"),
          "the commit rule does not say a false trailer is worse than an absent one, so "
          "'write what the plan expected' reads as acceptable")
    status_rule = section(text, r"5\. \*\*Flip the task's Status", r"\n6\. \*\*Quick review")
    check("Step 3.3 Status-flip rule located", bool(status_rule),
          "could not slice rule 5 — the flip/trailer division of labour is unchecked")
    # affirms_predicate anchored PAST the rule's own negative ("never who did it"): that
    # phrase is the requirement, so anchoring before it puts a negation the screen must
    # reject between anchor and target. Anchor on the consequence instead — the identical
    # `[x]` — which is affirmative and sits immediately before the pointer to the trailer.
    check("the Status flip is stated NOT to record the executor",
          affirms_predicate(status_rule, r"write the identical", r"executor trailer"),
          "the Status-flip rule does not point at the trailer, so a reader looking for "
          "who ran the task finds an identical [x] and stops there")
    # The pointer check above proves the two phrases CO-OCCUR, not that the disclaimer is
    # still a disclaimer: a Tier-1 review inverted "never who did it" to "including who
    # did it" and the suite stayed green, because affirms_predicate screens only BETWEEN
    # its anchor and target and the mutation sat before the anchor. So assert the clause
    # itself — whatever follows "records that the task is done" must be negative. This is
    # structural (a negation must be present), not a verbatim sentence match (BL-031).
    done_claim = re.search(r"records that the task is done(.{0,40})", status_rule)
    check("the flip's scope is stated as EXCLUDING who did it",
          bool(done_claim) and NEGATION_RE.search(done_claim.group(1)) is not None,
          "the flip is no longer disclaimed as not recording the executor, so the rule "
          "now reads as if [x] were the record of who ran the task")

    # 14 — (Task 2.3) The stage gate reports dispatched-vs-inline.
    # Groups 12 and 13 give a run a declaration (the roster) and a record (the trailer).
    # This is what compares them. Without it both artifacts exist and nobody reads either:
    # the prior incident's five inlined `Parallel: YES` tasks passed every gate, because no
    # gate was asked for the count. Same shape as the remediation-round count the report
    # already carries — an uncounted thing is how a run reaches close-out unnoticed.
    gate_step = section(text, r"### Step 3\.5 — Stage gate", r"\*\*Platform stage-verify hook")
    check("Step 3.5 gate-report block located", bool(gate_step),
          "could not slice Step 3.5 — the dispatch-ledger checks are not running")
    # Both use affirms_claim: structural (BL-031 — a faithful paraphrase must pass) AND
    # clause-scoped, so the negation screen lands on the claim rather than on a window
    # the author sized. The two earlier drafts of these very checks are the case study in
    # affirms_claim's docstring: one anchored a 400-char window on "gate report", which
    # bled into the previous bullet, and a negated restatement passed clean.
    check("the gate report states dispatched-vs-inline counts",
          affirms_claim(gate_step,
                        r"dispatched[- ]vs[- ]inline|dispatched .{0,20}inline"),
          "the gate report carries no dispatch counts, so a stage that inlined every YES "
          "task reports exactly what a stage that dispatched them all reports")
    check("a reason is required per inlined Parallel: YES task",
          # No trailing `Parallel: YES` requirement: the paraphrase control showed a
          # faithful rewording ("and why every inlined one was") puts the quantifier and
          # the object in the other order and never repeats the field name. The
          # structural claim is reason + universal + inlined, inside one unnegated clause.
          affirms_claim(gate_step,
                        r"(reason|why)[^.]{0,60}(every|each|per)[^.]{0,40}inlin"),
          "an inlined YES task needs no stated reason, so the count degrades to a number "
          "with nothing behind it")
    # The Critical a Tier-1 review reproduced against this branch: git drops a whole
    # trailer block at a line it cannot parse, so a wrapped `Executor:` line returns
    # blank with exit 0. `065bd8b` and `6b09499` do exactly that. Without a rule for the
    # blank, the prescribed query silently undercounts at the very gate that runs it —
    # and "no trailer" would be read as "inline", inventing a deviation, or as
    # "dispatched", hiding one.
    check("an unparseable trailer is counted as unknown, not as inline",
          affirms(gate_step, r"empty trailer value is [`*]*unknown"),
          "a blank trailer has no defined reading, so the prescribed query undercounts "
          "silently and the gate report states a number nobody can trust")
    check("the unknowns are reported, not absorbed into the counts",
          affirms(gate_step, r"report the unknowns"),
          "unknown-executor commits vanish into one of the two counts, which is the "
          "false-record failure the trailer rule calls worse than none")
    # The counts must come from the artifact, not from the executor's recollection — the
    # executor is the party the count is about, and Task 2.2 exists precisely so this is
    # readable rather than remembered.
    check("the counts are read off the executor trailers, not from memory",
          # Anchored on the SOURCING VERB, not on the git command. Both a gate reviewer
          # and the goal evaluator independently inverted this claim to "Recall them from
          # memory rather than reading the executor trailers" and the check stayed green:
          # the command string and the reconciliation phrase both survive that inversion,
          # so the clause the check is NAMED for was never examined. affirms_predicate
          # rather than affirms_claim because the true prose says "…rather than from
          # memory", and `rather than` is itself a negation token — the documented case
          # where clause screening would reject the wording that satisfies the rule.
          # Bare verb anchor: `[^.]{0,40}` after it was greedy and consumed the target
          # itself, so the predicate search began past what it was looking for.
          affirms_predicate(gate_step, r"\b(?:Read|Take|Derive)\b", r"executor trailers"),
          "nothing ties the gate count to the trailers, so the report can restate the "
          "plan's intent instead of the run's history")
    # Split out of the check above rather than bundled with it. One check asserting two
    # claims is satisfiable by either, which is how the sourcing half went unguarded while
    # the reconciliation half carried it — the same "either site satisfies it" weakness
    # the failed-dispatch check discloses. Two claims, two checks, two mutations.
    check("the counts are reconciled against Preflight's roster",
          affirms_claim(gate_step, r"reconcile against the roster"),
          "the gate count is never compared with what Preflight declared, so the roster "
          "and the ledger are two records nobody puts side by side")
    # affirms_predicate on the AFFIRMATIVE half. The requirement's natural wording ends
    # "…rather than saying nothing", and both "rather than" and "nothing" are negation
    # tokens — screening that phrase rejects the sentence that satisfies the rule. The
    # positive claim (it states a count) is the checkable part.
    check("a fully-dispatched stage still states its count",
          affirms_predicate(gate_step, r"dispatched everything it marked",
                            r"[`*]*dispatch: 4 of 4"),
          "only deviations get reported, so 'no dispatch line' means both 'all dispatched' "
          "and 'nobody counted' — the distinction the whole ledger exists to draw")
    # The half that keeps the report from becoming a rubber stamp. A stated reason makes a
    # deviation auditable; it does not make it authorised, or `Parallel: YES` would be
    # discretionary again by way of the gate — the exact reading Stage 1 removed.
    check("a stated reason is disclosure, not authorisation",
          affirms(gate_step, r"deviation being disclosed"),
          "an inlined YES task with a reason attached reads as sanctioned, which restores "
          "the discretionary reading of the field that Stage 1 removed")

    # 15 — (Task 2.4) An unperformable mandated dispatch or review STOPS the run.
    # The list already blocked on "a test cannot be run" while an unavailable dispatch or
    # reviewer silently downgraded to inline/unreviewed. Both are verification; only one
    # blocked. The asymmetry survived because the substitute is indistinguishable from
    # the work in every artifact — which is also why it needs a rule and not judgment.
    stops = section(text, r"## Stop conditions", r"## When to revisit earlier steps")
    check("Stop-conditions list located", bool(stops),
          "could not slice the Stop conditions list — group 15 is not running")
    check("an unperformable mandated dispatch or review is a Stop condition",
          affirms_claim(stops,
                        r"mandated verification or dispatch cannot be performed"
                        r"|mandated (dispatch|review) cannot be (run|performed)"),
          "an unavailable dispatch or reviewer does not stop the run, so the executor "
          "substitutes inline execution and the user never learns of the choice")
    # The half that makes it a Stop rather than a note. Without it "stop" is satisfiable
    # by stopping to think and then inlining anyway.
    check("inline substitution is named as not a resolution",
          re.search(r"[Ss]ubstituting inline execution[^.]{0,80}not a documented "
                    r"resolution", stops) is not None,
          "the entry does not refuse the substitution, so the rule reads as advice")
    check("the decision is routed to the user, with the options named",
          affirms_claim(stops, r"choice belongs to the user"),
          "nothing says whose call this is, which is how the executor took it silently")

    # 16 — (Task 3.1) The review escape ramp. One sentence used to bundle three
    # situations — the user opted out, the diff is trivial, `git-github:code-reviewer` was
    # not installed — and only the first two are legitimate. The third made an unavailable
    # *review* excuse itself in a file that already blocked on an unrunnable *test*; group
    # 15 gave it the Stop condition it belongs in, and this group keeps it deleted.
    # Neither block gets a `site present:` locator: an empty slice fails every assertion
    # below it, so these are fail-closed already and a locator would only add a check with
    # no negatable form.
    review_optout = section(text, r"\*\*Review opt-out\.\*\*", r"\Z")
    # The claim is worded "the list is closed at two" rather than "the only reasons a
    # review is skipped" because `skipped` is itself on NEGATION_RE — the clause screen
    # rejected the sentence that satisfied the rule, which is the documented cost of a
    # corpus-specific negation list, hit here for the second time (see `may`, above).
    # Honest limit (BL-031): an exhaustiveness claim has no structural anchor the way a
    # count or a citation does, so this one is close to verbatim and a faithful rewording
    # ("the two reasons are the whole list") would fail it. The deny-sweep below is the
    # check that binds the CLASS; this one binds the sentence.
    check("review skips are closed to user opt-out and trivial diffs",
          affirms_claim(review_optout, r"the list is closed at two"),
          "the review opt-out no longer states its reasons as an exhaustive pair, so a "
          "third situation can be read into it the way an uninstalled reviewer once was")
    # Plain search, NOT affirms(): the claim is affirmative in meaning and negative in
    # wording ("is not a third one"), the same distinction drawn at the group-12 and
    # group-13 siblings above.
    check("an undispatchable reviewer routes to the Stop condition",
          re.search(r"Stop condition for a mandated review", review_optout) is not None,
          "an unavailable code-reviewer has no stated resolution, so the run proceeds on "
          "whatever checks remain and the user never gets the decision")
    gate_eval = section(text, r"\*\*Independent evaluator for non-command checks",
                        r"\*\*Deep code review")
    check("the gate evaluator's skip clause is closed the same way",
          affirms_claim(gate_eval,
                        r"[Ss]kip the evaluator only on[^.]{0,60}user opt-out"),
          "the Step 3.5 evaluator's skip clause no longer scopes skipping to an explicit "
          "opt-out — the loose wording the reviewer ramp grew out of")
    # The class check: not "is this one sentence gone" but "does any review or evaluator
    # anywhere in the file excuse itself on its own availability". See REVIEW_ESCAPE_RE
    # for why it is scoped to the subject and not to the sentence shape.
    escape = REVIEW_ESCAPE_RE.search(text)
    check("no review or evaluator excuses itself on availability",
          escape is None,
          f"an availability-based excuse for skipping a review is back in the file: "
          f"{escape.group(0) if escape else ''}")

    # 17 — (Stage 3, Task 3.2) group 16 closed the LIST of skip reasons at two; this group
    # is about what the surviving user opt-out has to show for itself. Deleting the ramp
    # without this is a dead end: the legitimate path stays open only if it is auditable,
    # and "the user asked me to skip this" and "I decided to skip this" currently produce
    # the identical record — the same invisibility the executor trailer (group 13) exists
    # to end, one axis over.
    check("an opt-out is evidenced by quoting the user",
          affirms_claim(review_optout,
                        r"recording it means \*\*quoting the user's own\s+words\*\*"),
          "the user opt-out no longer has to quote the user, so an asserted opt-out and "
          "an evidenced one leave the same artifact")
    check("only the user can author an opt-out",
          affirms_claim(review_optout,
                        r"the only person who can author it is the user"),
          "the opt-out's authorship is unstated, which is what lets an executor record "
          "its own decision as the user's")
    # Plain search WITH the negation inside the pattern — deliberately, and NOT the same
    # mistake as the sibling check two blocks up (`Stop condition for a mandated review`),
    # which a Tier-1 review demonstrated stays green when `not` is inserted BEFORE its
    # match. The distinction is where the negation sits relative to the pattern: here the
    # requirement IS the negation, so the minimal inversion — dropping `not` — deletes the
    # matched text and turns this red. affirms_claim cannot be used at all, because it
    # would screen the requirement's own `not` and reject the true sentence (the
    # absence-subject case its docstring carves out).
    check("executor judgment is named as not constituting an opt-out",
          re.search(r"\*\*Executor judgment is not an opt-out\.\*\*",
                    review_optout) is not None,
          "the file no longer says that an executor's own judgment fails to be an "
          "opt-out, which is the only reading that makes the quote requirement bite")
    # The asymmetry is load-bearing, not decoration: without it "evidenced" over-reaches
    # onto the trivial-diff reason, which has no user to quote and would become
    # unsatisfiable — closing the legitimate path this task exists to keep open.
    check("a trivial diff is exempted from the quote requirement",
          affirms_claim(review_optout,
                        r"trivial/non-code diff\*\* carries its own evidence"),
          "the quote requirement is not scoped away from the trivial-diff reason, which "
          "has no user to quote and would be unsatisfiable")
    # Set check (DEC-005): the sibling skip clauses are checked together, not one at a
    # time. A definition that only the defining site honors is how the Stage 1 defect
    # worked — the authoring site said one thing and the consuming sites another.
    evidenced_sites = [
        ("gate evaluator (Step 3.5)", gate_eval),
        ("close-out evaluator",
         section(text, r"3\. \*\*Independent evaluator pass \(default\)",
                 r"\n4\. \*\*Bump versions")),
        ("Integration summary (goal-evaluator entry)",
         section(text, r"- \*\*goal-evaluator agent\*\*", r"\n- \*\*git-github:code-reviewer")),
    ]
    unevidenced = [n for n, s in evidenced_sites
                   if not affirms_claim(s, r"evidenced\b[^.]{0,40}user opt-out")]
    check("every skip clause requires the opt-out to be evidenced, at: "
          + "; ".join(n for n, _ in evidenced_sites),
          not unevidenced,
          f"these skip clauses still accept a bare asserted opt-out: "
          f"{', '.join(unevidenced)}")

    # 18 — (Stage 3, Task 3.3) the review analogue of group 14's dispatch ledger. Groups 16
    # and 17 decide WHEN a review may be skipped; this makes the answer readable off the
    # report either way. Written as a set over both reporting sites for the same reason
    # group 14 reconciles counts rather than trusting memory: the stage gate and the
    # close-out are the two places a run claims it was reviewed, and a requirement landing
    # on only one of them leaves the other free to assert it.
    report_sites = [
        ("stage gate (Step 3.5)", gate_step),
        ("close-out report list",
         section(text, r"9\. Report to the user with:", r"\n10\. Offer merge")),
    ]
    for label, slab in report_sites:
        check(f"report site located: {label}", bool(slab),
              f"could not slice {label} — the group-18 set checks would pass vacuously "
              f"over an empty string")
    no_agent = [n for n, s in report_sites if not affirms_claim(s, r"the agent that ran it")]
    check("every review report names the agent that ran it, at: "
          + "; ".join(n for n, _ in report_sites),
          not no_agent,
          f"these report sites let a run claim it was reviewed without naming the "
          f"reviewer: {', '.join(no_agent)}")
    # `(?: range)?` so the two sites may word it naturally — the gate reports one stage's
    # diff, the close-out a range across the plan — without either being pinned verbatim
    # (BL-031). What is pinned is that the diff is identified at all.
    no_diff = [n for n, s in report_sites
               if not affirms_claim(s, r"the diff(?: range)? it saw")]
    check("every review report names the diff the review saw, at: "
          + "; ".join(n for n, _ in report_sites),
          not no_diff,
          f"these report sites name a reviewer but not what it reviewed, so a review "
          f"briefed on the wrong range is indistinguishable: {', '.join(no_diff)}")
    no_skip = [n for n, s in report_sites
               if not affirms_claim(s, r"evidenced opt-out[^.]{0,60}excused it")]
    check("every review report records what excused a tier that did not run, at: "
          + "; ".join(n for n, _ in report_sites),
          not no_skip,
          f"these report sites are silent about a review that did not happen, which is "
          f"the state that reads as 'reviewed': {', '.join(no_skip)}")
    # The rationale, not just the rule. This is the claim that says WHY naming the agent is
    # load-bearing rather than ceremony, and it is the first thing a future tightening
    # would drop as redundant — at which point the rule reads as a formatting preference.
    check("naming the agent is tied to the executor-self-review it rules out",
          affirms_claim(gate_step,
                        r"distinguishes a dispatched review from the executor reading "
                        r"its own diff"),
          "the gate report's reviewer name is no longer connected to the self-review "
          "Step 3.5 forbids, leaving it as a formatting rule with no stated purpose")

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
