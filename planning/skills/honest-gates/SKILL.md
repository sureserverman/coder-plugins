---
name: honest-gates
description: >-
  Integrity rules for any verification gate, acceptance check, test command, or
  "done" claim. Use whenever something must pass, build, run, or be measured —
  before reporting a gate green, registering a build/test task, or recording
  test/benchmark evidence. Apply eagerly; do not wait to be asked.
---
# Honest Gates

A gate is a claim that something was verified. This skill exists because the
cheapest way to make a gate "pass" is to lie about it — stub the task, skip the
run, or hand-write the evidence. Never do that. A faked gate is worse than a
failing one: it hides the failure and poisons every decision downstream.

## The one rule

**A gate is green only when its real command ran in the current environment and
actually passed. Nothing else counts as green.**

If you cannot make the real check run here, the gate is **BLOCKED**, not green.
Stop and escalate (see below). Do not invent a substitute that passes.

**Violating the letter of a gate is violating its spirit.** A gate named
`validateDebugScreenshotTest` that does no screenshot validation satisfies the
letter ("a task by that name exits 0") while betraying the purpose. The purpose is
the gate. When you catch yourself optimizing for the green checkmark instead of the
thing it certifies, stop — that impulse is the failure mode this skill exists to
name. Diagnose blockers with evidence (`no-fafo-debugging`), never by guessing a
fix that happens to make the check pass.

## Prohibited (these are gate-faking)

- **No-op tasks that impersonate a gate.** Never register a build task whose name
  matches a required gate (e.g. `validateDebugScreenshotTest`,
  `connectedDebugAndroidTest`) but whose body only logs "skipped"/"placeholder"
  and exits 0. If the real tooling isn't wired, the gate is BLOCKED.
- **Fabricated evidence.** Never hand-author benchmark output (gfxinfo, frame
  stats), device logs, screenshots, or playtest/session results. Evidence must be
  the captured output of a command that actually ran. If you didn't run it, you
  don't have the evidence.
- **Silently excluding the failing case.** Do not add runner exclusions
  (`notClass`, `-PexcludeTests`, `@Ignore`, skip flags) to make a suite green, then
  report the suite green. Disabling a check is a BLOCKED gate, not a pass.
- **"Written" ≠ "passing."** A test that exists but never executed proves nothing.
  Authoring `FooTest.kt` does not satisfy a gate that requires `FooTest` to pass.
- **Heuristic self-grading.** Do not stamp `Pass: true` on a measurement that
  misses its own threshold (e.g. "Skipped 35 frames" / 6% jank against a
  "≥95% within refresh" bar). Report the number and the verdict it actually earns.
- **Proxy data that doesn't measure what the gate measures.** Facilitator runs on
  the optimal path do not validate a "first-time casual player, 8–15 min" gate.
  Label proxy evidence as proxy and leave the real gate BLOCKED.
- **Unannotated amendment of a gate's own checks.** Rewriting what a check verifies,
  or how wide it sweeps, and then reporting the result as though the authored check
  passed. A legitimate amendment exists — the rules a plan was authored under do move
  — but it is annotated with the rule that authorized it and the value it replaced
  (`../executing-plans/SKILL.md` § *Amending authored ceremony*). Without that, a recalibrated
  gate and a quietly cheapened one leave identical artifacts, which is the same
  reason a scope change must be disclosed rather than merely made. **Amending a
  check to make a failing gate pass is never an amendment** — that is the gate-failure
  procedure wearing its clothes.
- **Verifying against a dirty working tree.** A gate whose commands ran over
  uncommitted edits proves nothing about what the branch records: the next reader,
  the next stage, and CI all see the committed state, not yours. Commit first, then
  run the gate — and if a gate was run early to save time, re-run it after the commit
  rather than reporting the earlier result
  (`/mnt/vault/Gotchas/Gate Verified Against Uncommitted Working Tree.md`).

## When a gate is BLOCKED

Blocked = the real check cannot run here (no device/emulator, missing SDK, needs
human testers, missing secret, network-restricted). Then:

1. **Stop on that gate.** Do not advance to the next task or stage.
2. **Name the exact blocker** and the exact command that cannot run.
3. **Try to unblock it for real** if it's in scope (stand up an emulator, install
   the SDK package, wire the missing plugin). Resolving the blocker is always
   preferred over escalating.
4. **If it can't be unblocked here, escalate to the user** with the blocker and
   what you'd need. Mark the gate BLOCKED in your status, never green.
5. **Write the checklist item as `- [~]`, never `- [x]` with a note explaining
   it away.** `[~]` is the gate checklist's BLOCKED state and it parses
   everywhere the plan tooling reads — a ticked box carrying
   *(amended — exit 2; no hardware)* is a GREEN check to every reader, and the
   prose that says otherwise is invisible to all of them. This is the exact
   shape BL-077 was filed from: a plan rendered **Completed:** with every
   hardware-in-the-loop box ticked and annotated. The annotation is still worth
   writing; it goes beside the `[~]`, not instead of it.

Preflight blockers (repo/SDK/device marked FAILED) are BLOCKED gates by
definition. Building "around" them and declaring later gates green is the exact
failure this skill prevents.

## A behavioral claim is a gate too

Those rules govern claims about *verification runs*. The same rule governs
claims about *what the code does* — because **a sentence asserting behavior is
itself a claim that something was verified**, and it is read by people who will
act on it without re-checking.

So when you write, into a doc, README, skill, comment, commit message or report,
an assertion about behavior — what a flag defaults to, what a command exits with,
what invokes what, what is auto-detected, what a script covers — **cite the
`file:line` you checked it against.** In a commit message or an adjacent comment
is fine; the citation does not have to survive into user-facing prose, it has to
have existed when the sentence was written. If you did not open the file, you do
not have the claim. "It's obviously true" and "it was true last time" are the two
ways this goes wrong.

**When there is no single line to cite**, the requirement does not lapse — it
changes shape:

- **An absence claim** ("nothing wires this", "no caller reaches X", "no validator
  checks Y") is proved by a *search*, not a line. Cite the query and the scope it
  ran over (`grep -rn 'foo' planning/skills/` → no matches), because the claim is
  only as strong as the scope, and a scope narrower than the reader assumes is how
  an absence claim turns out false. An empty result over the wrong tree is not
  evidence.
- **An emergent or aggregate claim** ("the suite is hermetic", "every plugin
  ships a README") is a claim about a set — write it as the sweep that proves it,
  per the class-predicate rule (`planning-projects`), and cite the sweep. If you
  cannot express it as a sweep, weaken the sentence until it matches what you
  actually checked.

Two rules with teeth, both drawn from observed failures rather than principle:

- **A correction is a new claim.** Discovering that a sentence was wrong tells you
  the old text was wrong; it does not tell you the replacement is right. Verify the
  replacement against the source, exactly as if no sentence had been there. This has
  happened here: commit `178f988` ("correct two factual overreaches in the new
  prose") introduced three *new* false claims, caught by `edaeba2` — the very next
  commit — whose own message names the cause: corrections written from a reviewer's
  negative finding without verifying the positive claim replacing it.
- **Unrequested specificity is where errors hide.** A model pin nobody asked for, a
  count ("all 14 plugins"), an "every"/"never", a version number, a precise path —
  these read as authority and are rarely checked. Verify it or omit it. Vaguer and
  true beats specific and wrong; if the specific number matters, go get it.

**This one cannot be a script.** No validator can decide whether an English
sentence asserts behavior, so there is no `check-behavioral-claims.py` and this
section is deliberately a write-time discipline plus a thing reviewers look for
(`executing-plans`, both review tiers). Saying so is itself the rule: claiming a
guard exists here would be the very falsehood the section forbids.

## A test does not exist until its mutant dies

The rules above govern claims about runs and about code. This one governs the
**check itself**, because a green suite is the claim everything else is built on,
and a test derived from the fix it is meant to guard cannot fail on it.

**First, before any of it: can this mechanism decide this property?** Name what the
check actually decides. If that is a fact about the *meaning* of prose — does this
sentence instruct, assert, disclose, promise — **no pattern can decide it**; this file's
§ *A behavioral claim is a gate too* says so already. Hardening buys one evasion class per
round: each pass rejects the counterexample you were shown and admits the next one, while
the suite stays green and reads like progress.

Two ways out, and they are the only two. **Make the property structural** — a delimited
block, a required literal, a machine-readable marker — so the question becomes decidable
and text outside the structure cannot satisfy it. Or **leave it to review and say so in
the checker**, which is what `check-behavioral-claims.py` not existing means.

Written from a checker that cost two review rounds and five Criticals before its author
noticed he had built the thing this file says cannot be built. A rule not consulted at the
moment of choosing is not in force — hence its position here, first.

**The rule this backs up already exists and already failed.** `executing-plans`
Step 3.3 opens "the test is written first and must go RED for the right reason" —
correct, and unenforceable after the fact: a test written first and a test
transcribed from the fix are byte-identical in a passing suite. Every failure
below happened with that rule in force. What follows is the part that leaves
evidence.

Three rules, in the order they have to happen. They cost a command each and no
agent dispatch, so they are **untiered — they run at every review scope including
`none`** (DEC-010's cost line as DEC-017 corrected it for commands: a mandate costing a line of text or a local
re-run is not tiered; a mandate costing an agent is).

1. **Write the set down before the fix.** Before patching, enumerate the
   population the defect belongs to — as a *command*, in the commit: `grep -rl`,
   a list of siblings, every caller of the changed symbol. Fix every member, then
   derive one test from the set. A fix scoped from the counterexample that
   revealed it will regenerate the finding on the next sibling, and each round
   reads as progress.

2. **Revert the fix; the suite must go red.** If it stays green you do not have a
   weak test, you have **no test** — and you cannot know which, because both look
   identical from a passing run. Name the mutation and the count in the commit
   ("reverting the `active` expression turns 3 checks red"). This is the whole
   rule: a check that cannot fail is not evidence, and it is indistinguishable
   from one that can until you try.

3. **Build fixtures from the requirement, never from observed behavior.** The
   moment a fixture is shaped by what the code currently does, it can no longer
   falsify what the code currently does. This is not theoretical: a vault fixture
   built without `Portfolio/` — because that was what the code then accepted —
   asserted the accepting behavior as correct, so a suite of 41 stayed green over
   the defect it was written to catch.

**Assert the discriminating cause, not the outcome.** `refused` is satisfied by
an argparse error, an ImportError, and the guard under test; `refused with the
guard's own wording` is satisfied by one of them. Whenever an assertion can be
made true by something other than the mechanism you are testing, it will
eventually be made true that way, and the suite will report it as a pass. Every
instance of this found so far was an outcome assertion standing in for a cause.

**Why this is not covered by § *Prohibited* or § *A behavioral claim is a gate too*.** Those catch a false sentence
about behavior. This catches a *true* sentence — "the suite passes" — that means
less than the reader takes it to mean. Nothing in a passing run distinguishes a
test that would catch the regression from one that would not, which is why the
distinguishing step has to be performed rather than assumed.

## Changing a contract reclassifies everything already written

Every other rule here reads the artifact in front of you. This one governs a change
whose effect lands elsewhere: a parsing rule, marker vocabulary or classification
predicate re-reads every document already written, under rules their authors could not
have followed.

**A change to a parsing contract, marker vocabulary or classification rule does not ship
until the corpus it reclassifies has been inventoried, and each member either backfilled
or filed as a named migration entry.** Shipping the rule and leaving the corpus is not a
partial fix — it is a new classification asserted over documents nobody opened.

**The inventory is a command and its output, never an estimate.** An uncounted set cannot
be backfilled, checked off, or declared done; "~20+" is what a migration entry says when
the sweep was never run.

Worked example, both halves of one commit. `4bb486e` (2026-08-27) made `[~]` outrank a
plan's close-out line and propagate to masters — retroactive over every plan already
written — while adding `**Blocked-accepted:**`, the only marker that retires such a plan,
which nothing closed earlier could carry. **19 closed plans across 9 projects flipped to
`blocked`**, every one closed before that commit, and stood as phantom in-flight work
until they were backfilled by hand. BL-103 is the same commit's other half, still
unmigrated — which is why its entry says "~20+" rather than a count.

**Tier: untiered.** One enumeration command and at most one backlog entry, never a
dispatch, so per DEC-010's cost line as DEC-017 extends it to commands, it runs at every
review scope including `none`. Named because DEC-017 requires a mandate to state the rule
that gates it.

**Adds, net.** It removes nothing — no other rule here looks at documents the change did
not touch — and costs one sweep per contract change, paid only by the change that earns
it. What it catches that nothing else does: a change that is right in the diff and wrong
in the corpus, where the diff, the suite and the rule are all green and the whole of the
damage sits in files no one opened.

## Reporting

When you report status, every gate is one of: **GREEN** (real command + passed,
quote it), **RED** (ran, failed), or **BLOCKED** (couldn't run, with the reason).
Never collapse BLOCKED into GREEN. If asked "is this done?", a stage with any
BLOCKED gate is not done.

## Integration

- `executing-plans` — enforces these rules at every stage gate.
- `gate-audit` — detects after the fact where these rules were broken.
- `android-gradle-build` / `android-stage-verify` — supply the *real* build/test/
  device commands so a gate never has to be faked for lack of technique.
- `no-fafo-debugging` — evidence-first diagnosis instead of guessing a passing fix.
