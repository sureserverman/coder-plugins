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
