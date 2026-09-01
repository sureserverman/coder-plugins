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
  9. (Task 2.2, extended by 2.3) DEFAULT_REMEDIATION_BUDGET equals the default the
     skill prose documents. One copy in the renderer now serves two consumers —
     the bar's `↻N/M` and `--budget-check`'s ceiling — and nothing but this
     assertion couples it to the prose that states the same number.
 10. (Task 2.3 / P7) The behavioral-claim rule exists in honest-gates with both
     sub-rules, and is referenced at each of the three executing-plans sites that
     must consult it (Tier-1 brief, Tier-2 brief, docs-only skip), with the
     docs-only skip naming its executable-behavior exception. Checked as a set,
     printing each site — the rule this stage adds is not enforceable by a script
     (no validator can decide whether a sentence asserts behavior), so what IS
     mechanically checkable is that it is stated and wired everywhere it is
     consumed. That distinction is stated here rather than left to be inferred.
 11. (dispatch-fidelity) The dispatch and review contract, pinned at one assertion per
     rule: `Parallel: YES` obligates dispatch (including a lone ready task), Preflight
     probes and rosters it, each per-task commit carries a one-line executor trailer,
     the gate reports dispatched-vs-inline, an unperformable dispatch or review is a
     Stop condition, review skips are closed at two reasons, an opt-out is evidenced,
     and both report sites name the reviewer and the diff.
 11b/c/d. (dispatch precedence, Task 3.4) A plan's mandated dispatch needs no
     confirmation turn — the standing caution against calling the Agent tool is
     conditional and the plan's approval IS the request. Pinned with its BOUND at
     equal weight (no plan in play → the caution stands and you ask) and with the
     over-correction recorded as its own failure, because the incident behind the
     rule failed in BOTH directions and a guard pinning only the permissive half
     would readmit the second. Plus: the rule reaches the two files that actually
     make the decision (a set), and a marketplace-wide sweep that no skill
     reintroduces a confirmation turn.
 12. (class repair) The class-repair rule has its own trunk section, states that it
     fires outside a gate, is priced as a command rather than a dispatch (DEC-010),
     carries its outer bound and its un-nameable-class disclosure, and is reached
     from every site where a defect can surface — that last one checked as a SET,
     printing the specific unwired site, because an instance-shaped check cannot
     fail on the siblings that make the class.

     **Deliberately small.** The first version of this group ran 62 assertions plus a
     574-line mutation harness that re-ran this suite against mutated copies, plus a
     coverage meta-check over that harness. It generated more defects than the rules it
     guarded — five backlog entries were about the guards themselves, none about the
     product — because pinning English with regexes regresses: each guard is prose-
     dependent, so it needs a meta-guard, which needs a meta-meta-guard. Cut back to one
     assertion per rule. These catch DELETION of a rule, which is the failure that
     actually happens; they do not pretend to catch every rewording, and no meta-layer
     is added to make them pretend harder.
"""
import os
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
# The second half is not padding: a requirement is more often softened than contradicted,
# and "is waived" / "though this is optional" negate a rule without using a word from the
# first half. `may` was tried and reverted with evidence — it is the CORRECT word at the
# sub-plan-level `Parallel` site, which is legitimately permissive, so banning it turned a
# true statement red. A negation list is corpus-specific, not universal.
NEGATION_RE = re.compile(
    r"\b(?:not|never|no|without|isn't|aren't|doesn't|don't|exempt|"
    r"rather than|instead of|unless|except|excluding|optional|optionally|"
    r"waived?|waives|unnecessary|advisory|discretionary|recommended|"
    r"need not|nor)\b",
    re.I,
)

# Availability-based excuses for skipping a review. Scoped to the review/evaluator SUBJECT
# rather than the sentence shape: "Absence of a match is not a gate failure" is the same
# grammar and is CORRECT about a platform stage-verify skill, which is conditionally
# applicable where a code reviewer always applies. `[^.\n]` spans never cross a sentence
# boundary, which is what keeps that line out of the sweep. `fall(?:s|ing)?` rather than a
# bare `fall`: this file lives inside the tree the gate greps.
#
# MEASURED LIMIT: four alternations, not a decision procedure. "cannot be found",
# "unreachable", "if the reviewer is currently unavailable, proceed" all express the same
# idea and evade it. It is defence in depth behind the sentence-anchored check below,
# which is what actually binds the rule.
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


# Clause boundaries for affirms_claim. Asymmetric on purpose: a PRECEDING comma-joined
# clause is a separate assertion whose negation must not bleed in, while a TRAILING one
# modifies the claim and must be screened. `:` is a backward boundary and never a forward
# one — `Parallel: YES` puts a colon inside a requirement's own text.
CLAUSE_START = re.compile(r"[.;:,]\s|\s[-–—]\s|\*\*\s|\bso\b|\brather\b|\bthough\b")
SENTENCE_END = re.compile(r"[.;]\s|\.\*\*|\s[-–—]\s")


def affirms_claim(hay, target_pat):
    """True when `target` appears in a clause that carries no negation.

    THE default for a prose requirement. Prefer it over `affirms` / `affirms_predicate`,
    which both let the check AUTHOR pick how far to screen — a fixed character lookbehind,
    or the span between two chosen anchors — so an inversion placed outside the chosen
    window is never examined, and every window size drifts as the prose is clarified.

    A claim lives in a clause, so the clause is the unit to screen: back to the previous
    boundary, forward to the end of the sentence. Both ends derived from the text, which
    is what catches a negated verb ("does not require") and a negated object ("no reason")
    and a trailing withdrawal ("…, though this is optional") alike.

    Use `affirms_predicate` ONLY when the requirement's own subject is an absence
    ("when no concurrent sibling exists, dispatch anyway") — there the clause legitimately
    contains a negation and screening it would reject true prose.
    """
    for m in re.finditer(target_pat, hay, re.I | re.S):
        starts = [b.end() for b in CLAUSE_START.finditer(hay[:m.start()])]
        after = SENTENCE_END.search(hay, m.end())
        span = hay[(starts[-1] if starts else 0): (after.start() if after else len(hay))]
        # Blank out `code spans` first: they hold literals, not prose. The rule "the user
        # can re-mark the tasks `Parallel: NO`" names a FIELD VALUE, and reading its `NO`
        # as a negation rejected the sentence.
        if not NEGATION_RE.search(re.sub(r"`[^`]*`", " ", span)):
            return True
    return False


# Slices whose END anchor matched nothing, so the slice ran to the end of whatever
# it was reading. Recorded centrally rather than guarded call-by-call: this file
# already carried two hand-written `len(block) < N` bounds added after the same bug
# bit twice (a Light-plan slice reading 33,190 chars; a Step 3.5 slice reading 56,637
# across six files), and a per-call guard is instance-shaped by construction — it
# protects the slices someone remembered to bound and no others. A fall-through fails
# OPEN: the assertions still name their site while reading unrelated text, so they can
# pass on prose that has nothing to do with the rule. Detecting it here covers every
# existing caller and every future one.
FELL_THROUGH = []
OVERSIZED = []

# No rule-level slice in this suite is legitimately this long. The largest real one is
# Step 3.5's full trunk section at ~8.4k. The bound exists because a fall-through does
# not always leave the end anchor UNMATCHED: Step 3.5's stale `**Platform stage-verify`
# anchor matched a case-insensitive bullet in a different reference file, producing a
# 56,637-char slice spanning six files that FELL_THROUGH could not see. Unmatched-anchor
# and matched-far-away are two shapes of one defect, so both are detected.
MAX_SLICE = 12000


def section(text, start_pat, end_pat):
    """Slice the text between two anchors; returns '' when the start is missing."""
    m = re.search(start_pat, text, re.I)
    if not m:
        return ""
    rest = text[m.start():]
    e = re.search(end_pat, rest[1:], re.I)
    if e is None and end_pat != r"\Z":
        # `\Z` is the one legitimate unbounded end anchor, and only where the slice
        # is scoped to a file that genuinely ends there (see the review_optout note).
        FELL_THROUGH.append(f"{start_pat!r} → {end_pat!r} (read {len(rest)} chars)")
    raw = rest[: e.start() + 1] if e else rest
    out = flat(raw)
    if len(out) > MAX_SLICE:
        OVERSIZED.append(f"{start_pat!r} → {end_pat!r} ({len(out)} chars)")
    return out


def main():
    if not SKILL.is_file():
        print(f"FAIL: {SKILL} not found", file=sys.stderr)
        return 1
    # The skill is the trunk PLUS any reference files it loads on demand. If
    # progressive disclosure moves a rule out of SKILL.md into references/, the rule
    # has not gone away — it has moved, and these assertions exist to catch DELETION
    # (see the module docstring), not relocation. Reading only SKILL.md would fail on
    # a change that removed nothing, and would push authors to keep content in the
    # trunk to satisfy the guard rather than because it belongs there. Slices that must
    # stay scoped to the trunk read SKILL.md directly rather than this concatenation —
    # see review_optout below for why an unbounded end anchor is unsafe here.
    refs = sorted((SKILL.parent / "references").glob("*.md"))
    text = "\n\n".join(
        [SKILL.read_text(encoding="utf-8")]
        + [r.read_text(encoding="utf-8") for r in refs]
    )

    gate_fail = section(text, r"\*\*If the gate fails", r"\*\*If the gate passes")
    check("gate-failure section present", bool(gate_fail),
          "no '**If the gate fails' … '**If the gate passes' block in SKILL.md")

    # 0 — the class-repair rule's own section. It used to live INSIDE the gate-failure
    # branch, which scoped it to gates: a bug found in a Red-Green loop, in a review, or
    # noticed while editing got no sweep at all. It is now stated once in the trunk and
    # called from every site where a defect can surface, so the properties that belong to
    # the RULE are asserted here and the properties the GATE adds stay on gate_fail.
    # Splitting them this way is what lets either move again without unpinning the other.
    class_rule = section(text, r"## A bug found during execution is a class",
                         r"## Phase 1 — Load and critique")
    check("class-repair rule stated as its own trunk section", bool(class_rule),
          "no '## A bug found during execution is a class' section — the rule is either "
          "deleted or has collapsed back inside a single caller")
    check("the rule fires beyond gates, naming the non-gate discovery sites",
          affirms(class_rule, r"RED test|while editing"),
          "the rule does not say it fires outside a gate, which is the entire change: "
          "scoped to gates it is the rule that already existed")
    check("the gate-failure branch routes to the shared rule",
          affirms(gate_fail, r"A bug found during execution is a class"),
          "the gate-failure branch does not call the shared rule, so the two can drift "
          "back into separate procedures")

    # 0b — the rule is wired at EVERY site a defect can surface, checked as a SET rather
    # than one worked example: an instance-shaped check cannot fail on the siblings that
    # make the class, which is the very defect this rule exists to repair.
    #
    # Each site names the FILE its procedure lives in (Stage 2, Task 2.2). This suite used
    # to read SKILL.md alone, on the reasoning that these were all trunk call sites — true
    # until the extraction, after which Tier-1's machinery and the gate's evaluator and
    # Tier-2 briefs moved to references/ by a classification that marked them branch-taken.
    # Reading only the trunk would then report three deletions where nothing was deleted.
    #
    # Naming the file rather than searching the concatenation is deliberate, and is the
    # difference between loosening and unpinning: `section()` over trunk+references returns
    # the FIRST match, so a site present in both would be checked only in the trunk and a
    # reference copy could silently stop routing. One (file, start, end) triple per site
    # keeps every one pinned to a definite place that a reader can open.
    skill_only = SKILL.read_text(encoding="utf-8")
    REFS = SKILL.parent / "references"
    DISCOVERY_SITES = [
        ("Red-Green loop", SKILL,
         r"\*\*Diagnose before fixing", r"\*\*Respect the cycle budget"),
        ("Tier-1 Critical", REFS / "task-execution.md",
         r"\*\*Critical → blocking", r"\*\*Important / Suggestion"),
        ("Tier-2 review", REFS / "stage-gate.md",
         r"## Deep code review \(Tier 2\)", r"## Decisions-conformance"),
        ("gate evaluator", REFS / "stage-gate.md",
         r"## Independent evaluator for non-command checks",
         r"## Deep code review \(Tier 2\)"),
        ("gate failure", SKILL,
         r"\*\*If the gate fails", r"\*\*If the gate passes"),
    ]
    unwired = []
    for name, path, start, end in DISCOVERY_SITES:
        if not path.is_file():
            unwired.append(f"{name} (no {path.name})")
            continue
        blk = section(path.read_text(encoding="utf-8"), start, end)
        if not blk or not affirms(blk, r"A bug found during execution is a class"):
            unwired.append(name)
    check("every discovery site routes to the class rule: "
          + ", ".join(n for n, _, _, _ in DISCOVERY_SITES),
          not unwired,
          f"these sites do not reach the rule: {', '.join(unwired)} — a bug found there "
          f"is repaired one instance at a time")

    # 0c — the rule's two bounds. Both were added deliberately and both are the kind of
    # qualifier a later compression deletes as hedging: without the cost line the rule
    # reads as fundable-by-tier (contradicting DEC-010), and without the stop line it
    # reads as a licence to refactor whatever lives near the bug.
    check("the sweep is priced as a command, never a dispatch",
          affirms(class_rule, r"costs a command")
          and affirms(class_rule, r"untiered mandates"),
          "the rule does not state that it costs no agent dispatch, so a reader cannot "
          "tell whether the review tier gates it (DEC-010 says a command-cost mandate "
          "is never tiered)")
    check("the sweep's outer bound is stated",
          affirms(class_rule, r"nothing wider"),
          "nothing bounds the sweep to the defect's own predicate, so it reads as "
          "authorisation for unrelated refactoring")
    check("an un-nameable class is disclosed rather than swept by feel",
          affirms(class_rule, r"disclose the limit"),
          "no instruction for the case where the class cannot be expressed as a "
          "command — which is where a sweep silently becomes a guess")

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

    # (Task 2.3) The budget stops being prose the executor tracks about itself.
    # A 4th round was dispatched after a declared budget of 3 — ~604K subagent
    # tokens across four rounds for one Critical — while `plan-progress.json`
    # already carried `remediation_round` and nothing read it as a stop. A rule
    # whose only enforcement is the executor's own memory of how many rounds it
    # has spent is the shape that failed; a command is what replaces it.
    check("the budget is enforced by a command, not by self-tracking",
          re.search(r"--budget-check", gate_fail) is not None,
          "the gate-failure procedure names no mechanical check, so counting the "
          "rounds is still the executor's own bookkeeping about itself")
    check("the check runs BEFORE a further remediation dispatch",
          re.search(r"--budget-check[\s\S]{0,200}?\bbefore\b"
                    r"|\bbefore\b[\s\S]{0,200}?--budget-check",
                    gate_fail, re.I) is not None,
          "nothing says WHEN to run it; a check run after the round it should have "
          "stopped is a receipt, not a gate")
    check("the mandate states what the check rests on",
          re.search(r"binds only on a recorded round", gate_fail, re.I) is not None,
          "nothing says the check is only as good as the counter it reads; an "
          "executor that never writes `remediation_round` gets a silent zero "
          "forever, which is the same self-tracking failure one layer down")
    check("exhaustion routes to escalation, not to another round",
          re.search(r"escalat", gate_fail, re.I) is not None,
          "the on-exhaustion path is not named, so the natural next move is the "
          "round the budget exists to prevent")
    # DEC-017: a new mandate names the tier or scope rule that gates it. This one
    # costs a command, not a dispatch, so per DEC-010 it is untiered.
    check("the new mandate states what gates it (DEC-010/DEC-017)",
          re.search(r"--budget-check[\s\S]{0,300}?(untiered|every tier|DEC-010)"
                    r"|(untiered|every tier|DEC-010)[\s\S]{0,300}?--budget-check",
                    gate_fail, re.I) is not None,
          "the mandate does not name its tier or scope rule, which DEC-017 requires "
          "of a new mandate and which this plan requires of Task 2.3 by name")

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
    check("Important findings are FIXED, not filed",
          affirms(exit_block, r"Important[\s\S]{0,120}fixed"),
          "Important findings may be silently dropped — no affirmative fix rule")
    # The inverse pin, and the load-bearing half after this stage: the criterion must not
    # offer the backlog as a way to pass a gate on an unfixed defect. The old contract
    # REQUIRED "backlog" next to "Important"; letting that requirement simply lapse would
    # leave the drift free to return in the next rewording.
    check("the criterion does not offer the backlog as a disposition for a defect",
          not re.search(r"Important[\s\S]{0,120}recorded to the `?backlog", exit_block, re.I),
          "the exit criterion still lets an Important finding leave the gate as a backlog "
          "ID, which is the deferral asymmetry this criterion was rewritten to close")
    check("the backlog's two admissible kinds are named at the criterion",
          affirms(exit_block, r"significant improvement")
          and affirms(exit_block, r"decision"),
          "the criterion removes the backlog as a disposition without saying what the "
          "backlog IS for, which is how the rule reads as 'never file anything'")
    check("a defect that cannot be fixed here escalates with its blocker named",
          affirms_predicate(exit_block, r"cannot fix", r"[Ee]scalat")
          or affirms(exit_block, r"naming the blocker"),
          "no escape valve: a defect needing a device, a credential or an upstream "
          "release would be unreportable, which is worse than the drift being fixed")
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
         section(text, r"\*\*One review, not per-task",
                 r"\*\*The evaluator follows the tier")),
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
        # A dead END anchor makes section() run to the end of the concatenation, and the
        # checks below then pass on unrelated text while still naming this site — found
        # live: the Light-plan slice was reading 33,190 chars because its end anchor
        # ("**Both evaluator passes") existed nowhere outside this file. Every real
        # sibling block is 300-1500 chars, so a bound catches the whole failure mode.
        check(f"slice is bounded, not fallen through: {label}", len(block) < 4000,
              f"the {label} slice is {len(block)} chars — its end anchor no longer "
              f"matches, so these checks are reading the rest of the document")
        # Two conditions rather than one 220-char window. The window had to be greedy to
        # span either order, and a greedy span pulls in any negation further down the
        # paragraph — including, at the master site, the criterion's own "no Critical
        # remains". Cite-the-criterion and say-they-are-fixed are separate claims anyway.
        check(f"Importants bound to the exit criterion at: {label}",
              "exit criterion" in block and affirms(block, r"leaves[\s\S]{0,40}?fixed")
              and not re.search(r"either fixed or recorded|or recorded to the `?backlog",
                                block, re.I),
              f"{label} describes Important findings without binding them to the exit "
              f"criterion and to being fixed — findings can pass this path unrepaired")
        check(f"no backlog escape hatch at: {label}",
              not re.search(r"Important[\s\S]{0,260}recorded to the `?backlog", block, re.I),
              f"{label} still offers the backlog as a disposition for an Important "
              f"finding, so the deferral path survives at this sibling")

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
    # Asserted on the RULE, not the gate: the enumeration procedure moved to the trunk
    # section when the rule stopped being gate-only, and a defect found outside a gate is
    # precisely the case where no `Scope:` was ever declared — so this property matters
    # MORE at the rule than it did here.
    check("a missing Scope: has a stated fallback",
          affirms_predicate(class_rule, r"(no `?Scope:`?|when no scope)", r"enumerate"),
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
    # The ORDER is now asserted on the rule (step 1 before step 2) and its ROUTING on
    # the gate, because the rule is where the ordering is defined and the gate is where
    # it is most fix-prone. Both must hold; neither alone is the contract.
    check("step 2's heading orders diagnosis before naming",
          affirms(gate_fail, r"diagnose evidence-first, then name the set"),
          "step 2 does not state diagnosis-before-generalization in its own heading")
    fafo_at = affirmed_index(class_rule, r"no-fafo")
    derive_at = class_rule.lower().find("name the set")
    check("no-fafo is routed BEFORE the set is derived",
          fafo_at != -1 and derive_at != -1 and fafo_at < derive_at,
          "diagnosis is not ordered before generalization, so a wrong root cause "
          "yields a confidently-swept wrong set")
    check("the ordering rationale is stated, not just the order",
          affirms(class_rule + gate_fail,
                  r"wrong root cause[^.]{0,60}wrong set|set derived from a wrong"),
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
        # The BRIEF moved to references/stage-gate.md at Stage 2 (the classification marked
        # the evaluator's briefing branch-taken); the trunk keeps the rule that it runs and
        # what gates it. Anchored on the reference so the severity vocabulary is pinned
        # where it is actually written, rather than reported missing from a trunk that was
        # never meant to carry it after the extraction.
        ("gate evaluator (Step 3.5)",
         section((SKILL.parent / "references" / "stage-gate.md")
                 .read_text(encoding="utf-8"),
                 r"## Independent evaluator for non-command checks",
                 r"## Deep code review")),
        # Anchored on the step's NAME, not on the parenthetical that used to follow it.
        # The heading read "Independent evaluator pass (default)" until the pass stopped
        # being an unconditional default and became tier-gated; pinning "(default)" meant
        # the anchor asserted a policy word inside a *locator*, so a legitimate policy
        # change silently unanchored eight downstream assertions at once (they reported
        # as eight independent failures, which is how an over-fit anchor disguises itself
        # as a real regression). BL-031's class: pin the rule, locate by the stable name.
        ("close-out evaluator",
         section(text, r"\*\*Independent evaluator pass", r"\n4\. \*\*Bump")),
    ]
    for label, block in evaluator_sites:
        check(f"site present: {label}", bool(block), f"could not locate the {label} block")
        # The level must be BRIEFED, not merely mentioned. A bare `level in block` was
        # satisfiable by the prose around the brief — "an evaluator FAIL carrying no
        # Blocking finding…", "Blocking maps to Critical…" — so a mutation probe that
        # replaced the severity table's own `**Blocking**` row left this green (measured
        # at Stage 2, Task 2.2). Both legitimate briefing forms are accepted: the gate
        # evaluator states them as an emphasised table, the close-out evaluator as the
        # slash-listed triple, and neither survives deleting the row or the list.
        for level in ("Blocking", "Material", "Minor"):
            briefed = (re.search(rf"\*\*{level}\*\*", block) is not None
                       or re.search(r"Blocking\s*/\s*Material\s*/\s*Minor", block)
                       is not None)
            check(f"severity '{level}' in brief: {label}", briefed,
                  f"{label} does not brief the evaluator to return '{level}' — the word "
                  f"may appear in nearby prose, but the brief itself does not require it")
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
    check("close-out Material findings are FIXED, not just mentioned",
          affirms(close_out, r"fix each Material finding"),
          "Material findings are reported without an imperative to fix them")
    check("close-out does not route a Material finding to the backlog instead",
          not re.search(r"record each Material finding[\s\S]{0,60}backlog", close_out, re.I),
          "close-out still files Material findings rather than fixing them, so the "
          "deferral path survives at the one gate with the widest view of the diff")

    # 8b — (backlog admission) A SWEEP over every skill, not a check on the two files
    # this stage happened to edit. The retired contract — "fixed OR recorded to the
    # backlog" — was restated at seven sites, which is why it survived three earlier
    # attempts to tighten it: each fixed the site that was noticed. Any file under
    # planning/skills/ that still offers the backlog as a disposition for an Important
    # or Material finding fails here, by name.
    #
    # tests/fixtures/ is excluded deliberately, not incidentally: gate-check-corpus/
    # holds FROZEN COPIES OF REAL, UNMODIFIED past plans (see its PROVENANCE.md), one of
    # which narrates a July gate as "eleven were fixed or recorded". Editing a historical
    # record to satisfy a sweep would falsify it AND decalibrate
    # test-validate-gate-checks.py group 9, whose figures are pinned against that corpus.
    # Two patterns, because one of them needs no distance parameter at all. The window on
    # the second was originally 80 chars, chosen by eye; a mutation probe reverting ONE
    # sibling site proved it vacuous — the real distance at that site is 186 characters,
    # measured, so it is now 260 and the disjunction pattern backstops it regardless.
    DEFERRAL_RE = re.compile(
        r"either fixed or recorded|fixed or recorded to the `?backlog|"
        r"or recorded to the `?backlog|"
        r"(Important|Material)[\s\S]{0,260}?recorded to the `?backlog", re.I)
    # Marketplace-wide, not planning/skills/: the disposition claim also lives in
    # planning/README.md and docs/USAGE.md, and README WAS an offending site — it still
    # said "fixed or recorded" until a stage gate caught it by hand. A guard narrower than
    # the claim it protects is the instance-vs-class shape this whole plan exists to close,
    # recurring inside the guard. Matches check 11d's scope for the same reason.
    ADMISSION_ROOT = SKILLS_ROOT.parent.parent
    offenders = []
    swept = 0
    for md in sorted(ADMISSION_ROOT.rglob("*.md")):
        if "fixtures" in md.parts or ".git" in md.parts:
            continue
        swept += 1
        if DEFERRAL_RE.search(flat(md.read_text(encoding="utf-8"))):
            offenders.append(str(md.relative_to(ADMISSION_ROOT)))
    check(f"no skill files a defect instead of fixing it (swept {swept} files)",
          not offenders,
          "these still offer the backlog as a disposition for a finding: "
          + ", ".join(offenders))
    check("the admission sweep examined a non-empty set", swept > 20,
          f"only {swept} files swept — the sweep is not reaching the skills tree")

    # 8c — the backlog skill states what it DOES admit. A rule that only forbids leaves
    # an executor with nowhere to put a genuine improvement, and the predictable failure
    # is that it stops recording those too.
    backlog_skill = SKILLS_ROOT / "backlog" / "SKILL.md"
    if backlog_skill.is_file():
        bt = flat(backlog_skill.read_text(encoding="utf-8"))
        for kind in ("significant improvement", "non-urgent decision"):
            check(f"backlog admits: {kind}", affirms(bt, re.escape(kind)),
                  f"the backlog skill does not name '{kind}' as admissible")
        check("backlog refuses a defect found during execution",
              affirms_predicate(bt, r"Refuse", r"defect"),
              "the backlog skill has no refusal path, so `add` still accepts a defect")

    # 11b — (dispatch precedence) The rule that a plan's mandated dispatch needs no
    # confirmation turn. One assertion per clause, and the BOUND is pinned as hard as the
    # rule: the recorded incident produced BOTH failures — an executor reading the standing
    # caution as absolute (37 commits, zero dispatches, every mandated review skipped), and
    # then the over-correction that inverted the rule instead of scoping it. A guard that
    # pinned only the permissive half would let the second one back in.
    precedence = section(text, r"## The plan is the authorization",
                         r"## A bug found during execution is a class")
    check("dispatch-precedence rule stated as its own trunk section", bool(precedence),
          "no '## The plan is the authorization' section — a session must then re-derive "
          "the precedence between the standing caution and the plan's execution model")
    check("slice is bounded, not fallen through: precedence", len(precedence) < 4000,
          f"the precedence slice is {len(precedence)} chars — its end anchor no longer "
          f"matches, so the checks below are reading the rest of the document")
    # These four requirements have a NEGATION as their subject — "conditional, not
    # absolute", "no plan in play", "over-corrected", "without asking" — so affirms(),
    # which screens negation tokens inside the match, rejects every one of them on true
    # prose. Closest precedent is check 9b, which drops the screen because there is no single
    # claim clause to anchor; here the reason differs again — the target text itself embeds
    # a negation token, so the screen rejects the requirement's own correct wording. The phrases are specific enough
    # that an inversion cannot match them accidentally, which is what affirms() would
    # otherwise be buying.
    check("the standing caution is named as CONDITIONAL, not absolute",
          re.search(r"conditional, not absolute", precedence, re.I) is not None,
          "the rule does not say the standing caution is conditional, which is the whole "
          "resolution — without it the two rules still contradict and the general one wins")
    check("approving the plan is named as the request",
          affirms(precedence, r"was the request|is the request"),
          "nothing states that the plan's approval IS the request the caution refers to")
    check("the BOUND is stated: no plan in play means you still ask",
          re.search(r"no plan in play[\s\S]{0,160}?ask", precedence, re.I) is not None,
          "the rule is stated without its bound, which is how it gets over-corrected into "
          "its inverse — the documented second failure of the same incident")
    check("the over-correction is recorded as a failure in its own right",
          re.search(r"over-correct(?:ed|ion)? into its own inverse", precedence, re.I)
          is not None,
          "only the permissive failure is recorded, so a reader has no warning against "
          "inverting the rule rather than scoping it")
    check("what still halts a dispatch is enumerated",
          affirms(precedence, r"requires_enablement") and affirms(precedence, r"probe"),
          "the rule removes the confirmation turn without saying what legitimately still "
          "stops a dispatch, which reads as 'dispatch unconditionally'")

    # 11c — the rule must reach the two files that actually make the decision, checked as a
    # SET. dispatching-parallel-agents is where a fan-out is launched; dispatch-fidelity is
    # where the reasoning is kept. A rule stated only in the trunk is a rule the dispatch
    # path never reads.
    DISPATCH_SITES = [
        # Sentence-shaped, not a bare substring: "without asking" alone is satisfied by
        # "never dispatch without asking permission first" — i.e. by the over-correction
        # this stage exists to prevent. Reproduced before widening.
        ("dispatching-parallel-agents", SKILLS_ROOT / "dispatching-parallel-agents"
         / "SKILL.md", r"[Dd]ispatch on invocation[\s\S]{0,80}?without asking"),
        ("dispatch-fidelity rationale", SKILLS_ROOT / "executing-plans" / "references"
         / "dispatch-fidelity.md", r"conditional"),
    ]
    missing = [name for name, path, pat in DISPATCH_SITES
               if not (path.is_file()
                       and re.search(pat, flat(path.read_text(encoding="utf-8")), re.I))]
    check("dispatch precedence reaches: " + ", ".join(n for n, _, _ in DISPATCH_SITES),
          not missing,
          f"these dispatch-path files do not carry the rule: {', '.join(missing)}")

    # 11d — tree-wide sweep: no skill may reintroduce a confirmation turn before a
    # mandated dispatch. Fixtures excluded for the reason given at the admission sweep.
    # Synonyms matter: the rule is about a confirmation turn, not about one phrasing of
    # it, and "check with the user before fanning out" is the same regression. Scope is
    # the whole marketplace, matching the stage gate's own class predicate rather than
    # being quietly narrower than the check it mirrors.
    ASK_RE = re.compile(r"ask (?:the user )?(?:whether|if) to (?:dispatch|fan out)|"
                        r"(?:confirm|check) with the user before (?:dispatch|fan)|"
                        r"confirm before dispatching|permission to dispatch", re.I)
    MARKET_ROOT = SKILLS_ROOT.parent.parent
    askers = [str(md.relative_to(MARKET_ROOT))
              for md in sorted(MARKET_ROOT.rglob("*.md"))
              if "fixtures" not in md.parts and ".git" not in md.parts
              and ASK_RE.search(flat(md.read_text(encoding="utf-8")))]
    check("no skill asks before a mandated dispatch", not askers,
          "these still ask before dispatching: " + ", ".join(askers))

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
        # Follows the CONSTANT now, not a literal after `else`. Task 2.3 gave the
        # renderer's fallback a second consumer (--budget-check's ceiling), and
        # two literals would let the bar and the stop disagree about when a
        # budget is spent — so the file keeps one definition and this assertion
        # reads it. The older `else (\d+)` form is deliberately gone: it would
        # now match nothing and report "<not found>" instead of a mismatch.
        m_fallback = re.search(r"^DEFAULT_REMEDIATION_BUDGET\s*=\s*(\d+)",
                               code, re.M)
        check("renderer default budget matches the documented default",
              m_fallback is not None and m_fallback.group(1) == doc_default.group(1),
              f"SKILL.md documents a default of {doc_default.group(1)} rounds but the "
              f"renderer falls back to "
              f"{m_fallback.group(1) if m_fallback else '<not found>'}")

    # 9b — (0.37.0) every agent-dispatching mandate defers to the declared review tier at
    # the site that DISPATCHES it, not only in the summary table.
    #
    # Written as a set for the reason the rest of this file writes sets: this defect has
    # now recurred twice in one stage. Round 1 fixed the five sites a `grep` for the old
    # unconditional phrasings returned; the fix itself introduced two NEW mandates (the
    # Preflight probe, the design-fidelity evaluator) stated in review-scope.md and wired
    # nowhere — the same defect, one mandate over, invisible to the same grep because the
    # new sites never carried the old phrasing. An instance sweep cannot catch that; a
    # roster of sites can, because a mandate added later either joins the roster or is
    # absent from it.
    #
    # MEASURED LIMIT, stated rather than implied (honest-gates; DEC-008's disclosure
    # half): this asserts the site MENTIONS the tier, not that it defers correctly. A site
    # saying "the tier is irrelevant here" would pass. It catches the failure that has
    # actually happened twice — a dispatch mandate written with no tier term at all — and
    # does not pretend to grade the wording. No negation screen is used for the same
    # reason: there is no single claim clause to screen, only a topic that must be present.
    tier_gated_dispatch_sites = [
        ("Tier-1 per-task review",
         section(text, r"6\. \*\*Quick review gate \(Tier 1\)", r"7\. \*\*Commit after each")),
        ("Tier-2 deep review",
         section(text, r"\*\*Deep code review \(Tier 2\)", r"\*\*Decisions-conformance check")),
        ("gate evaluator",
         section(text, r"\*\*Independent evaluator for non-command checks",
                 r"\*\*Deep code review")),
        ("close-out evaluator",
         section(text, r"\*\*Independent evaluator pass", r"\n4\. \*\*Bump")),
        ("Preflight dispatch probe",
         section(text, r"2\. \*\*Probe the capability", r"3\. \*\*Snapshot the")),
        # Moved whole to references/stage-gate.md at Stage 2 — it fires only on a redesign
        # stage, which is the definition of branch-taken. Matched in either form so the
        # anchor survives the heading style rather than the file it lives in.
        ("design-fidelity verify hook",
         section(text, r"(?:\*\*|## )Design-fidelity verify hook",
                 r"(?:\*\*|## )Independent evaluator for non-command checks")),
    ]
    for label, block in tier_gated_dispatch_sites:
        check(f"dispatch site present: {label}", bool(block),
              f"could not locate the {label} block — if it moved, re-anchor it here; a "
              f"site this suite cannot find is a site it is not guarding")
        if block:
            check(f"tier-gated at the dispatch site: {label}",
                  re.search(r"§ Review scope|review scope|\btier\b", block, re.I)
                  is not None,
                  f"{label} dispatches an agent without referring to the declared review "
                  f"tier — the summary table can say the tier gates it while this site "
                  f"runs it unconditionally, which is the 0.37.0 defect class")

    # 9c — (0.37.0) the three rules that made the defaults lean. Check 9b asserts each
    # dispatch site MENTIONS a tier, which is deliberately weak — it catches a mandate
    # nobody tiered. It does NOT catch a rule reverting to the unconditional default while
    # still naming the tier, which is how these three would actually erode. A gate
    # evaluator mutation-tested all three against 9b alone and found every one reverts
    # green, so each gets its own claim-level anchor here.
    check("Tier-1 is scoped to high's risk-listed tasks and Review: required",
          affirms_claim(text,
                        r"there is no per-task review|"
                        r"Tier 1\)[^.]{0,80}`high` tier's risk-listed tasks and "
                        r"`Review: required` tasks only"),
          "Step 3.3 rule 6 no longer scopes the per-task review to `high`'s risk-listed "
          "tasks and `Review: required` — per-task review has reverted to a default")
    # DEC-016: the floor escalates the plan for mandates reading an integrated diff, but
    # Tier-1 follows the risk to the individual task. Anchored separately from the check
    # above because that one would stay green if `high` silently went back to binding every
    # task — the wording it pins is about which *tiers* run Tier-1, not which *tasks*.
    check("Tier-1 at high binds the risk-listed task, not every task in the plan",
          affirms_claim(text, r"this task is one the declaration names"),
          "Step 3.3 rule 6 no longer requires a `high` declaration to name the tasks "
          "Tier-1 binds — one risk-listed task has gone back to buying a per-task review "
          "dispatch for every task in the plan (DEC-016)")
    check("a re-dispatched review counts against the remediation budget",
          affirms_claim(text, r"re-dispatched review or evaluator is a round"),
          "the fix -> re-review loop is unbounded again: the budget counts repairs but "
          "not re-dispatches, so a gate can loop until the reviewer goes quiet — which "
          "is not a reachable state")
    # Negative assertion, so affirms_claim is wrong here (its negation screen would
    # reject the very absence being asserted). A literal-absence sweep is the honest
    # shape: the retired nudge is gone from every .md under planning/, or it is not.
    # Assembled, not written literally — same reason as BANNED_PHRASE above. This file
    # lives under planning/, which the final stage gate greps for the retired phrase, so
    # a literal here turns that gate permanently red against its own guard.
    retired_nudge = " ".join(
        ("Delegate", "sequential", "tasks", "for", "context", "hygiene"))
    revived = []
    for path in sorted(SKILLS_ROOT.parent.rglob("*.md")):
        if retired_nudge in path.read_text(encoding="utf-8", errors="replace"):
            revived.append(str(path.relative_to(SKILLS_ROOT.parent.parent)))
    check("the discretionary sequential-delegation nudge stays retired",
          not revived,
          "a `Parallel: NO` task may again be delegated at the executor's discretion, "
          f"reintroducing a third execution mode no plan reader can predict: {revived}")

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

    # Tier-1's brief and its docs-only skip moved to references/task-execution.md at
    # Stage 2. Both are anchored on that file rather than the concatenation, and BOTH
    # end anchors were re-pointed: each one's old end marker now sits in the trunk,
    # which precedes the reference in the concatenation, so `section()` found no end
    # after the start and ran to the end of the whole corpus. That fails open — the
    # slice was ~30k chars of unrelated text and the assertions below passed on it
    # while naming a site they were no longer reading. A vacuous pass is worse here
    # than a red, so the anchors are pinned inside the file that owns the text.
    task_exec = (SKILL.parent / "references" / "task-execution.md").read_text(
        encoding="utf-8")
    p7_sites = [
        ("Tier-1 review brief",
         section(task_exec, r"## Tier 1 — the quick per-task review",
                 r"- \*\*Critical → blocking")),
        ("Tier-2 review brief",
         section(text, r"\*\*Deep code review \(Tier 2\)", r"\*\*Decisions-conformance")),
        ("docs-only Tier-1 skip",
         section(task_exec, r"- \*\*Skip for trivial/non-code diffs",
                 r"## The executor trailer")),
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

    # ---- 11 — dispatch fidelity. One assertion per rule; see the docstring for why
    # this group is deliberately small. Each names the rule it would lose.
    pp = (SKILLS_ROOT / "planning-projects" / "SKILL.md").read_text(encoding="utf-8")
    dpa = (SKILLS_ROOT / "dispatching-parallel-agents" / "SKILL.md").read_text(
        encoding="utf-8")

    # Anchored past the `YES | NO` field gloss: that `NO` is a FIELD VALUE in a fenced
    # block (not a code span, so it survives the backtick blanking) and reads as a
    # negation. Screening prose means screening prose only.
    check("Parallel: YES is defined as a dispatch obligation",
          affirms_claim(flat(pp), r"YES obligates dispatch"),
          "the authoring skill no longer defines YES as an obligation, so an author and "
          "an executor can read the same field two ways — the original defect")
    check("no permissive gloss survives in the authoring skill",
          not re.search(r"can a sub-agent run this concurrently|it can be dispatched",
                        pp, re.I),
          "a permissive gloss is back: YES reads as 'a subagent could do this'")
    # `affirms`, not `affirms_claim`: the sentence continues "...and is NEVER a reason to
    # hand the task back to the caller", which reinforces the rule but is a negation token
    # inside the claim's own sentence. This is the absence-subject case, one clause over.
    split = section(text, r"### Step 3\.2 — Split by parallelism",
                    r"### Step 3\.3 — Red-Green loop")
    review_scope = section(text, r"### Review scope — the machinery scales to the change",
                           r"## Phase 3 — Stage execution")
    check("review effort is tiered to the diff, and the tier is declared",
          affirms_claim(review_scope,
                        r"the declaration is what makes the choice reviewable"),
          "the review machinery runs at one weight regardless of what it reviews, and a "
          "downgrade leaves no record — the cost nobody compares to what it protects")
    check("format and tier compose as shape-vs-depth, not lighter-wins",
          affirms_claim(review_scope,
                        r"format decides the review's SHAPE\. The tier decides its DEPTH"),
          "the two axes are unspecified where they meet again, so a Light plan declaring "
          "a heavy tier can be run at either weight and be equally compliant")
    check("a process plan must name what it removes",
          affirms_claim(flat(pp), r"adds an obligation names what it removes"),
          "plans can add mandatory steps without ever retiring one, so the process grows "
          "monotonically and each addition looks individually defensible")

    check("a file conflict serializes the dispatch instead of inlining it",
          affirms_claim(split, r"serialize the dispatches"),
          "a file-conflicting YES task routes to the main session again — the one "
          "documented authorization to inline a task the plan marked for dispatch")

    check("a lone ready task is still dispatched",
          affirms(flat(dpa), r"lone ready task is \*\*still dispatched\*\*"),
          "|S| = 1 can return control to the caller again, which is how a stage with one "
          "ready task inlines it while looking compliant")

    roster = section(text, r"### Dispatch roster and capability probe",
                     r"## Phase 3 — Stage execution")
    closeout_report = section(text, r"9\. Report to the user with:", r"\n10\. Offer merge")
    resets = section(text, r"## Context resets at stage boundaries",
                     r"## Progress state file")
    check("the Preflight roster/probe block is present", bool(roster),
          "could not slice the dispatch roster section — the two checks below would "
          "pass vacuously over an empty string")
    # Both patterns were bare literals and false-alarmed on a meaning-preserving
    # rewrite (BL-031): naming the probe's agent type ("Dispatch one throwaway
    # `general-purpose` subagent") and widening the sweep's scope ("sweep **every task
    # in the plan, across all stages**") each broke a pin while strengthening the prose.
    # Loosened to tolerate an inserted qualifier and the leading case, and no further.
    # The sweep pattern KEEPS a right boundary ([,*]): without it "sweep **every task in
    # the plan's first stage**" would match, which is the very defect the rule forbids
    # ("A roster covering only the first stage is not a roster") and which no other
    # assertion pins. Deleting either sentence still fails, which is what these assert.
    check("Preflight probes dispatch and declares a roster",
          affirms_claim(roster, r"[Dd]ispatch one throwaway[^.]{0,40}subagent")
          and affirms_claim(roster, r"[Ss]weep \*\*every task in the plan[,*]"),
          "Preflight no longer probes dispatch or sweeps the plan for YES tasks, so an "
          "unavailable dispatch is discovered at close-out instead of before Stage 1")
    check("the probe is conditioned on a non-empty roster",
          affirms_claim(roster, r"only if the roster is non-empty"),
          "the probe runs unconditionally again, so a plan that will never dispatch "
          "still burns a throwaway one to prove a capability nothing uses")
    check("Review: skip annotations are snapshotted at Preflight",
          affirms_claim(roster, r"Snapshot the `Review: skip` annotations"),
          "nothing pins the annotations to the run's base commit, so an executor can "
          "add one mid-run and cite it as a user opt-out")
    check("close-out reconciles dispatch plan-wide against the roster",
          affirms_claim(closeout_report, r"reconciled against Preflight's roster"),
          "the roster is declared plan-wide but answered only per stage, so a skipped "
          "or silent stage gate leaves a hole no per-stage check can see")
    check("the handoff carries the ledgers a reset would discard",
          affirms_claim(resets, r"dispatch and review lines are carried here"),
          "the gate's ledgers stay transcript-only while the skill recommends discarding "
          "that context — and the review ledger cannot be rebuilt from git")

    check("an unavailable dispatch fails Preflight",
          affirms_predicate(roster, r"dispatch is unavailable or disallowed",
                            r"Preflight fails and you stop"),
          "an unavailable dispatch no longer stops the run, so the executor substitutes "
          "inline execution and the user never gets the decision")

    commit_rule = section(text, r"7\. \*\*Commit after each green task", r"### Step 3\.4")
    check("every per-task commit carries an executor trailer",
          affirms_claim(commit_rule, r"ends with an executor trailer"),
          "nothing records WHO ran a task, so an inlined YES task and a dispatched one "
          "are byte-identical again — the finding that made the rest enforceable")
    check("the trailer is constrained to one physical line",
          affirms_claim(commit_rule, r"trailer to one physical line"),
          "a wrapped trailer silently vanishes from every %(trailers:...) query, so the "
          "convention documents a check that returns nothing")

    # Scoped to the TRUNK and ended on the next top-level heading. The old end anchor
    # was `**Platform stage-verify`, a bold inline run that Stage 2's extraction turned
    # into a `## ` heading in references/stage-gate.md — so the pattern no longer matched
    # where it was expected and instead hit a case-insensitive bullet in
    # references/integration.md, 56,637 chars and six files later. The two assertions
    # below still bit, by the accident of which files sort inside that span. Both
    # properties this needs — the right file, and an end anchor that exists in it — are
    # restored here rather than left to luck.
    gate_step = section(skill_only, r"### Step 3\.5 — Stage gate",
                        r"## Context resets at stage boundaries")
    check("the gate reports dispatched-vs-inline with a reason",
          affirms_claim(gate_step, r"dispatched-vs-inline counts")
          and affirms_claim(gate_step, r"a reason for every inlined"),
          "the gate stops counting dispatch, which is how the prior run reached close-out "
          "with five inlined YES tasks and nobody noticing")
    check("the report names the reviewer and the diff it saw",
          affirms_claim(gate_step, r"the agent that ran it")
          and affirms_claim(gate_step, r"the diff it saw"),
          "a gate can report green without saying who reviewed what, so an unrun review "
          "and a passed one leave the same record")

    stops = section(text, r"## Stop conditions", r"## When to revisit")
    check("an unperformable mandated dispatch or review is a Stop condition",
          affirms(stops, r"mandated verification or dispatch cannot be performed"
                         r"|mandated (dispatch|review) cannot be (run|performed)"),
          "an unavailable dispatch or reviewer no longer stops the run")
    check("inline substitution is refused as a resolution",
          re.search(r"[Ss]ubstituting inline execution[^.]{0,80}not a documented "
                    r"resolution", stops) is not None,
          "the Stop entry does not refuse the substitution, so it reads as advice")

    # Bound this to ONE file's opt-out block. The reason has not changed, only the file:
    # reading trunk+references means a \Z end anchor runs past the end of SKILL.md and
    # swallows every reference file — review-scope.md carries its own "**Review opt-out.**"
    # heading and the pre-compression wording, so an unbounded slice over the concatenation
    # would let these assertions pass on the archived copy even if the live block were
    # deleted outright.
    #
    # At Stage 2 the block moved from the trunk to references/integration.md, where
    # `## Review opt-out` is the final section — so \Z is bounded by the file itself, which
    # is what made the trunk anchor safe before. If a later edit appends a section there,
    # re-point the end anchor rather than widening the slice. The trunk keeps the pointer
    # to it (Integration), which the DEAD-PATH half of check-extraction-integrity.py
    # verifies actually resolves.
    integration_md = SKILL.parent / "references" / "integration.md"
    review_optout = section(integration_md.read_text(encoding="utf-8"),
                            r"## Review opt-out", r"\Z") if integration_md.is_file() else ""
    check("the review opt-out block is locatable", bool(review_optout),
          "no '## Review opt-out' section in references/integration.md — the block the "
          "four assertions below pin has been deleted or moved again")
    check("review skips are closed to two reasons",
          affirms_claim(review_optout, r"the list is closed at two"),
          "the review opt-out no longer states its reasons as an exhaustive pair, so a "
          "third situation can be read in the way an uninstalled reviewer once was")
    check("an undispatchable reviewer routes to the Stop condition",
          affirms_claim(review_optout, r"Stop condition for a mandated review"),
          "an unavailable code-reviewer has no stated resolution, so the run proceeds on "
          "whatever checks remain and the user never gets the decision")
    check("only a snapshotted annotation counts as an opt-out",
          affirms_claim(review_optout,
                        r"counts as an opt-out when Preflight's snapshot lists it"),
          "an annotation read at skip time is accepted again, which cannot distinguish "
          "a user's decision from the executor's own")
    check("an opt-out is evidenced by quoting the user",
          affirms_claim(review_optout, r"quoting the user's own\s+words"),
          "an asserted opt-out and an evidenced one leave the same artifact again")
    # The negation is INSIDE the pattern deliberately: the requirement itself is negative,
    # so affirms_claim would screen its own `not` and reject true prose. Dropping the `not`
    # deletes the match and turns this red. It does NOT catch a trailing clause that keeps
    # the literal and withdraws its force — stated, not implied closed.
    check("executor judgment is named as not constituting an opt-out",
          re.search(r"\*\*Executor judgment is not an opt-out\.\*\*", review_optout)
          is not None,
          "the file no longer says an executor's own judgment fails to be an opt-out, "
          "which is the only reading that makes the quote requirement bite")
    escape = REVIEW_ESCAPE_RE.search(text)
    check("no review or evaluator excuses itself on availability",
          escape is None,
          f"an availability-based excuse for skipping a review is back: "
          f"{escape.group(0) if escape else ''}")

    # Every slice this suite took must have found its end anchor. Checked last, so it
    # reports on all of them at once. A fall-through does not fail the assertion that
    # used the slice — it makes that assertion read unrelated text while still naming
    # its site, which is how a guard goes quiet without going red.
    check("no slice fell through its end anchor",
          not FELL_THROUGH,
          "these slices ran past their end anchor and are reading unrelated text: "
          + "; ".join(FELL_THROUGH))
    check(f"no slice exceeds {MAX_SLICE} chars",
          not OVERSIZED,
          "these slices are too long to be the section they name — their end anchor "
          "most likely matched in a different file: " + "; ".join(OVERSIZED))

    check("sweep examined a non-empty set", scanned > 0,
          "no markdown files scanned — an empty sweep is not a pass")
    check(f"no {BANNED_PHRASE!r} under planning/skills/", not offenders,
          f"instance-shaped framing survives at: {', '.join(offenders)}")

    # 11. (honest-gates-rule-gaps plan, Task 3.2 / BL-079) Preflight proves hardware and
    #     remote access by an executed probe, never by an environment variable. Two sites:
    #     the trunk's Preflight bullet, and the procedure in preflight-checks.md.
    _here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_here, "..", "SKILL.md"), encoding="utf-8") as fh:
        _trunk = fh.read()
    with open(os.path.join(_here, "..", "references", "preflight-checks.md"), encoding="utf-8") as fh:
        _pre = fh.read()
    _ws = lambda pat: re.sub(r" ", r"\\s+", pat)
    _access = re.search(r"^- Access / permissions verified.*$", _trunk, re.M)
    check("Preflight's access line is no longer bare",
          _access is not None and re.search(r"^- Access / permissions verified$", _trunk, re.M) is None,
          "the trunk still lists 'Access / permissions verified' with no probe")
    check("Preflight's access line names a probe",
          _access is not None and "probe" in _access.group(0),
          "the access bullet does not say access is proven by a probe")
    _probe = section(_pre, r"\n## Access probe", r"\n## ")
    check("preflight-checks.md has an access-probe section", bool(_probe),
          "no '## Access probe' heading in preflight-checks.md")
    check("access probe: the host is resolved from the repo's own deploy/HIL scripts",
          affirms_claim(_probe, _ws(r"from the repo's own deploy, HIL or provisioning scripts")),
          "nothing says to resolve the target from the repo's own scripts")
    check("access probe: the probe is run and what answered is recorded",
          affirms_claim(_probe, _ws(r"record what answered")),
          "nothing says to run the probe and record what answered")
    check("access probe: nothing answered -> BLOCKED",
          re.search(_ws(r"nothing answered.{0,200}BLOCKED"), _probe, re.S | re.I) is not None,
          "the 'nothing answered' outcome is not mapped to BLOCKED")
    check("access probe: something answered but not what was expected -> investigate, not excuse",
          re.search(_ws(r"not what was expected.{0,120}investigat"), _probe, re.S) is not None,
          "the wrong-identity outcome is not mapped to investigation")
    check("access probe: an unset variable is missing configuration, not missing hardware",
          re.search(_ws(r"missing configuration"), _probe) is not None
          and re.search(_ws(r"missing hardware"), _probe) is not None,
          "the configuration/hardware distinction is not stated")

    # 12. (rule-gaps plan, Task 3.3 / BL-080) The amendment protocol names what never
    #     authorizes an amendment, and the two definition sites cite each other.
    _amend = section(_pre, r"\n## Amending authored ceremony", r"\n## ")
    with open(os.path.join(_here, "..", "..", "honest-gates", "SKILL.md"), encoding="utf-8") as fh:
        _hg = fh.read()
    check("amendment protocol: cost, wall-clock and disk argue for re-scoping the plan, never the evidence",
          re.search(_ws(r"cost, wall-clock and disk"), _amend, re.I) is not None
          and re.search(_ws(r"re-scoping the plan"), _amend) is not None
          and re.search(_ws(r"never (?:for )?(?:re-scoping )?the evidence"), _amend) is not None,
          "the protocol does not say cost/time/disk are arguments for re-scoping the plan, not the evidence")
    check("amendment protocol: a suite dropped from a gate command is recorded [~] BLOCKED on that suite",
          re.search(_ws(r"dropped from a gate command.{0,120}`\[~\]`.{0,40}BLOCKED on that suite"), _amend, re.S) is not None,
          "the dropped-suite consequence is not stated as [~] on that suite")
    check("amendment protocol: cites test-scope-tiers.md for the declared-scope distinction",
          "test-scope-tiers.md" in _amend and re.search(_ws(r"neither touched nor depend on"), _amend) is not None,
          "the protocol does not name the tiering discriminator (trees the stage neither touched nor depends on)")
    check("cross-citation: preflight-checks § Amending cites honest-gates, and honest-gates' amendment bullet cites § Amending authored ceremony",
          "honest-gates" in _amend and "Amending authored ceremony" in _hg,
          "one of the two definition sites does not point at the other")

    # 13. (rule-gaps plan, Task 3.4 / BL-082 + BL-084) The host's own footing is a safety
    #     rail; a mid-execution feature request goes back through triage.
    _rails = section(_trunk, r"\n## Safety rails", r"\n## ")
    _revisit = section(_trunk, r"\n## When to revisit earlier steps", r"\n## ")
    check("safety rail: never reconfigure the agent host's own network interfaces, routes or DNS to reach a device under test",
          re.search(_ws(r"own network interfaces, routes or DNS"), _rails) is not None
          and re.search(_ws(r"device under test"), _rails) is not None,
          "no rail names the host's own interfaces/routes/DNS")
    check("safety rail: names the alternatives (second interface, spare client, subagent on another machine)",
          all(re.search(_ws(w), _rails) for w in (r"second interface", r"spare client", r"subagent on another machine")),
          "the rail does not name the three alternatives")
    check("safety rail: with none available the gate is BLOCKED",
          re.search(_ws(r"none is available.{0,60}BLOCKED"), _rails, re.S) is not None,
          "the rail does not map 'no alternative' to BLOCKED")
    check("safety rail: generalized to anything the session depends on to keep running",
          re.search(_ws(r"anything the session depends on to keep running"), _rails) is not None,
          "the rail is not generalized past networking")
    check("revisit: a mid-execution request for new work goes through planning-projects triage before implementation",
          affirms_claim(_revisit, _ws(r"mid-execution request for new work")) and re.search(_ws(r"triage"), _revisit) is not None
          and "planning-projects" in _revisit,
          "no sentence routes a mid-execution feature request through triage")
    check("revisit: such work does not share the plan's branch or its gate (negation-subject, literal)",
          re.search(_ws(r"does not share the plan's branch or its gate"), _revisit) is not None,
          "the branch/gate separation is not stated")

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
