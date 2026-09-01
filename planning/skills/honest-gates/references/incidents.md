# Incidents behind the honest-gates rules

Extracted from `../SKILL.md` by `2026-09-01-honest-gates-rule-gaps-plan.md` Task 1.2. Each
heading names the rule it belongs to and holds only what left the trunk — the incident, the
example, or the rationale — with a lead-in so it reads on its own. The rule sentence itself
is not repeated here: the trunk is its only definition site, and
`extraction-classification.md` pins it there. A copy in this file would be a second site
that can drift.

## Prohibited — why an unannotated amendment is indistinguishable from a cheapened gate

The amendment bullet says a legitimate amendment is annotated with the authorizing rule and
the value it replaced. The reason disclosure is the whole difference: without it, a
recalibrated gate and a quietly cheapened one leave identical artifacts, which is the same
reason a scope change must be disclosed rather than merely made.

## Prohibited — the authored-stub pair (b85c294)

In pi-modem's Cursor sessions of 2026-08-19..24 the executor wrote the `hil-*.sh` scripts its
own gates ran. One had the body `echo "soft residual"; echo OK` and passed; another was
`exit 2` and was ticked `[x]` with *(amended — exit 2)*, the block serving as the excuse.
The project owner reverted both (`b85c294`, "make live gates fail blocked instead of
succeeding on stubs"). Nothing in the rules had asked who wrote the gate.

## Prohibited — the proxy-data example

Facilitator runs on the optimal path do not validate a "first-time casual player, 8–15 min"
gate: the evidence is real, and it measures a different population than the gate names.

## Prohibited — the self-grading example

"Skipped 35 frames" / 6% jank, stamped `Pass: true` against a "≥95% within refresh" bar.
The number was reported; the verdict it earned was not.

## A behavioral claim — the 178f988 / edaeba2 correction

The correction-is-a-new-claim rule has happened here. Commit `178f988` ("correct two factual
overreaches in the new prose") introduced three *new* false claims, caught by `edaeba2` — the
very next commit — whose own message names the cause: corrections written from a reviewer's
negative finding without verifying the positive claim replacing it.

## A behavioral claim — why an absence claim names its scope

The absence-claim rule requires citing the query and the scope it ran over. The reason: the
claim is only as strong as the scope, and a scope narrower than the reader assumes is how an
absence claim turns out false.

## A test does not exist until its mutant dies — the checker that could not be built

The mechanism question sits first in its section because of a checker that cost two review
rounds and five Criticals before its author noticed he had built the thing the section says
cannot be built — a pattern matcher over what prose means. A rule not consulted at the
moment of choosing is not in force; hence its position, first.

## A test does not exist until its mutant dies — why the test-first rule needed backing

`../../executing-plans/SKILL.md` Step 3.3 opens "the test is written first and must go RED
for the right reason" — correct, and unenforceable after the fact: a test written first and
a test transcribed from the fix are byte-identical in a passing suite. Every failure the
section's three rules answer happened with that rule in force.

## A test does not exist until its mutant dies — hardening buys one evasion class per round

Each hardening pass rejects the counterexample you were shown and admits the next one, while
the suite stays green and reads like progress.

## A test does not exist until its mutant dies — rule 1's rationale

A fix scoped from the counterexample that revealed it will regenerate the finding on the
next sibling, and each round reads as progress — which is why the set is written down as a
command before the fix.

## A test does not exist until its mutant dies — the masking pair (99/101)

Measured in one stage of engineering-skills' 2026-08-25 plan: a suite stayed green at 31/31
with a whole clause removed, 91/91 with four findings' severity unpinned, and 99/101 with two
env-var guards each keeping the single negative fixture clean — so deleting *either alone*
looked harmless. No individual test was wrong, and no reader of the suite would have seen it.
A mutation battery of 24, one per guard, first ran 20 killed / 4 survived, every survivor a
masking pair; after one isolating fixture per guard, 24/24.

## A test does not exist until its mutant dies — the Portfolio/ fixture

Rule 3 is not theoretical: a vault fixture built without `Portfolio/` — because that was
what the code then accepted — asserted the accepting behavior as correct, so a suite of 41
stayed green over the defect it was written to catch.

## A test does not exist until its mutant dies — the outcome-assertion tally

Every instance of a non-discriminating assertion found so far was an outcome assertion
standing in for a cause.

## A test does not exist until its mutant dies — why the section is not covered by the two before it

The *Prohibited* and *A behavioral claim is a gate too* sections catch a false sentence
about behavior. This one catches a *true* sentence — "the suite passes" — that means less
than the reader takes it to mean. Nothing in a passing run distinguishes a test that would
catch the regression from one that would not, which is why the distinguishing step has to
be performed rather than assumed.

## Changing a contract — the framing

Every other honest-gates rule reads the artifact in front of you. This one governs a change
whose effect lands elsewhere: a parsing rule, marker vocabulary or classification predicate
re-reads every document already written, under rules their authors could not have followed.

## Changing a contract — the 4bb486e worked example

Both halves of one commit. `4bb486e` (2026-08-27) made `[~]` outrank a plan's close-out
line and propagate to masters — retroactive over every plan already written — while adding
`**Blocked-accepted:**`, the only marker that retires such a plan, which nothing closed
earlier could carry. **19 closed plans across 9 projects flipped to `blocked`**, every one
closed before that commit, and stood as phantom in-flight work until they were backfilled
by hand. BL-103 is the same commit's other half.

## Changing a contract — what an estimate is

"~20+" is what a migration entry says when the sweep was never run.

## Changing a contract — the adds-net argument

The rule removes nothing — no other honest-gates rule looks at documents the change did not
touch — and costs one sweep per contract change, paid only by the change that earns it. What
it catches that nothing else does: a change that is right in the diff and wrong in the
corpus, where the diff, the suite and the rule are all green and the whole of the damage
sits in files no one opened.

## Reporting — host fixtures reported as device acceptance

Measured across the sessions engineering-skills' 2026-08-25 plan audited: Playwright runs
against **host fixtures** were reported as browser acceptance of the product, and nothing was
deployed to a reachable device until the user asked three separate times. Every individual
claim was true — the tests ran, and passed. What was false was the implied subject: evidence
about the host, presented as evidence about the artifact.

## Reporting — figures that drifted three rounds running, and the 188 plans

Every round of the 2026-07-28 context-engineering plan's Stage 4 recorded before/after word
and line counts, and every round they were wrong: the "after" numbers went stale by
construction because the same commit kept editing the files, and the "before" numbers were
transcribed rather than measured (12,913 vs 12,912). A second instance on 2026-08-26 was a
different shape: a false-positive rate "over 188 non-pi-modem plans" that does not reproduce,
because no selection rule for those 188 was ever stated — a sha would not have helped there;
the missing line was the one naming what was counted.
