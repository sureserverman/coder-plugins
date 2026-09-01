# Incidents behind the honest-gates rules

Extracted from `../SKILL.md` by `2026-09-01-honest-gates-rule-gaps-plan.md` Task 1.2. Each
heading names the rule it belongs to; the trunk keeps the rule and a one-clause pointer here.
This file is read when a reader wants the story, never as the definition of a rule — the
rule text lives only in the trunk, where `extraction-classification.md` pins it.

## Prohibited — why an unannotated amendment is indistinguishable from a cheapened gate

  (`../../executing-plans/SKILL.md` § *Amending authored ceremony*). Without that, a recalibrated
  gate and a quietly cheapened one leave identical artifacts, which is the same
  reason a scope change must be disclosed rather than merely made. **Amending a
  check to make a failing gate pass is never an amendment** — that is the gate-failure
  procedure wearing its clothes.

## A behavioral claim — the 178f988 / edaeba2 correction

- **A correction is a new claim.** Discovering that a sentence was wrong tells you
  the old text was wrong; it does not tell you the replacement is right. Verify the
  replacement against the source, exactly as if no sentence had been there. This has
  happened here: commit `178f988` ("correct two factual overreaches in the new
  prose") introduced three *new* false claims, caught by `edaeba2` — the very next
  commit — whose own message names the cause: corrections written from a reviewer's
  negative finding without verifying the positive claim replacing it.

## A test does not exist until its mutant dies — the checker that could not be built, and why the test-first rule needed backing

Written from a checker that cost two review rounds and five Criticals before its author
noticed he had built the thing this file says cannot be built. A rule not consulted at the
moment of choosing is not in force — hence its position here, first.

**The rule this backs up already exists and already failed.** `executing-plans`
Step 3.3 opens "the test is written first and must go RED for the right reason" —
correct, and unenforceable after the fact: a test written first and a test
transcribed from the fix are byte-identical in a passing suite. Every failure
below happened with that rule in force. What follows is the part that leaves
evidence.

## A test does not exist until its mutant dies — the Portfolio/ fixture

3. **Build fixtures from the requirement, never from observed behavior.** The
   moment a fixture is shaped by what the code currently does, it can no longer
   falsify what the code currently does. This is not theoretical: a vault fixture
   built without `Portfolio/` — because that was what the code then accepted —
   asserted the accepting behavior as correct, so a suite of 41 stayed green over
   the defect it was written to catch.

## A test does not exist until its mutant dies — why the section is not covered by the two before it

**Why this is not covered by the trunk's *Prohibited* or *A behavioral claim is a gate too* sections.** Those catch a false sentence
about behavior. This catches a *true* sentence — "the suite passes" — that means
less than the reader takes it to mean. Nothing in a passing run distinguishes a
test that would catch the regression from one that would not, which is why the
distinguishing step has to be performed rather than assumed.

## Changing a contract — the 4bb486e worked example

Worked example, both halves of one commit. `4bb486e` (2026-08-27) made `[~]` outrank a
plan's close-out line and propagate to masters — retroactive over every plan already
written — while adding `**Blocked-accepted:**`, the only marker that retires such a plan,
which nothing closed earlier could carry. **19 closed plans across 9 projects flipped to
`blocked`**, every one closed before that commit, and stood as phantom in-flight work
until they were backfilled by hand. BL-103 is the same commit's other half, still
unmigrated — which is why its entry says "~20+" rather than a count.

## Changing a contract — the adds-net argument

**Adds, net.** It removes nothing — no other rule here looks at documents the change did
not touch — and costs one sweep per contract change, paid only by the change that earns
it. What it catches that nothing else does: a change that is right in the diff and wrong
in the corpus, where the diff, the suite and the rule are all green and the whole of the
damage sits in files no one opened.

## A behavioral claim — why an absence claim names its scope

  ran over (`grep -rn 'foo' planning/skills/` → no matches), because the claim is
  only as strong as the scope, and a scope narrower than the reader assumes is how
  an absence claim turns out false. An empty result over the wrong tree is not
  evidence.

## Mutant dies — hardening buys one evasion class per round

the trunk's *A behavioral claim is a gate too* section says so already. Hardening buys one evasion class per
round: each pass rejects the counterexample you were shown and admits the next one, while
the suite stays green and reads like progress.

## Mutant dies — rule 1's rationale

   derive one test from the set. A fix scoped from the counterexample that
   revealed it will regenerate the finding on the next sibling, and each round
   reads as progress.

## Mutant dies — every instance so far

eventually be made true that way, and the suite will report it as a pass. Every
instance of this found so far was an outcome assertion standing in for a cause.

## Prohibited — proxy data example

- **Proxy data that doesn't measure what the gate measures.** Facilitator runs on
  the optimal path do not validate a "first-time casual player, 8–15 min" gate.
  Label proxy evidence as proxy and leave the real gate BLOCKED.

## Prohibited — self-grading example

- **Heuristic self-grading.** Do not stamp `Pass: true` on a measurement that
  misses its own threshold (e.g. "Skipped 35 frames" / 6% jank against a
  "≥95% within refresh" bar). Report the number and the verdict it actually earns.

## Changing a contract — framing

Every other rule here reads the artifact in front of you. This one governs a change
whose effect lands elsewhere: a parsing rule, marker vocabulary or classification
predicate re-reads every document already written, under rules their authors could not
have followed.

## Changing a contract — what an estimate is

**The inventory is a command and its output, never an estimate.** An uncounted set cannot
be backfilled, checked off, or declared done; "~20+" is what a migration entry says when
the sweep was never run.
