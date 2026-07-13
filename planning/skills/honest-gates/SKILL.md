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

Preflight blockers (repo/SDK/device marked FAILED) are BLOCKED gates by
definition. Building "around" them and declaring later gates green is the exact
failure this skill prevents.

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
