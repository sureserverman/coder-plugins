---
name: gate-audit
description: >-
  Audit a repo or diff for faked verification — stubbed gates, tests that never
  ran, fabricated evidence, and hidden exclusions. Use at stage boundaries, before
  declaring work done, when reviewing someone else's "all gates green" claim, or
  when a build looks suspiciously passing. Complements code review (which checks
  whether code is correct) by checking whether the *verification* is real.
---
# Gate Audit

Ordinary review asks "is this code correct?". This asks "is the proof that it
works real, or was the gate gamed?". Run it whenever results look too clean given
a constrained environment (no device, no SDK, no human testers). Report findings
as a table sorted by severity: Severity, Location (`file:line`), Finding.

## Checklist

1. **Stubbed gate tasks.** Search build scripts for tasks whose name matches a
   required gate but whose body is a no-op:
   `grep -rn "tasks.register\|doLast" build.gradle* | …` then read any task named
   like a real check (`validate*ScreenshotTest`, `connected*Test`, `*lint*`). A
   body that only logs "skipped"/"placeholder" and exits 0 is a **faked gate**.
2. **Declared-but-unwired tooling.** A dependency in the catalog (e.g. a screenshot
   library) with no matching plugin applied and no source set is a tell that the
   gate was named but never built.
3. **Tests that never ran.** Do output dirs exist? For Android, absence of
   `app/build/outputs/.../connected/` / `connected_android_test_additional_output/`
   means `connectedDebugAndroidTest` never executed, regardless of how many
   `androidTest/` files exist. "Written" ≠ "passing".
4. **Hidden exclusions.** Grep for `notClass`, `-PexcludeTests`, `@Ignore`,
   `@Disabled`, `xfail`, skip flags. A suite reported green while a case is excluded
   is not green.
5. **Fabricated evidence.** Committed benchmark/device/playtest files (gfxinfo,
   frame stats, session logs, screenshots) with no script that reproduces them, or
   that contradict the stated environment (e.g. cites a physical device while
   preflight marked device access FAILED) — flag as unverifiable/fabricated.
6. **Self-graded misses.** Measurements stamped "Pass" that miss their own stated
   threshold (frame jank above the bar, median outside the required band).
7. **Proxy passed off as real.** Evidence that doesn't measure the gate's actual
   condition (optimal-path facilitator runs standing in for first-time casual
   playtests).
8. **Preflight bulldozed.** Preflight items marked FAILED while later stages claim
   their gates green anyway.

## Dispatch an independent reviewer for the judgment calls

The deterministic checks above (grep for stubs, missing output dirs, exclusions)
run inline. But "is this evidence fabricated?" and "does this proxy actually
measure the gate?" are judgment calls — and the session that did the work grades
itself too generously. For those, dispatch the `git-github:code-reviewer` subagent
(Agent tool, `subagent_type: "git-github:code-reviewer"`) with a
**self-contained brief** (it sees none of this conversation): state the
gate's pass criteria, list the suspect artifacts with `file:line`, and ask it to
confirm each gate's real status against the criteria — not against the author's
summary. Redact any secrets from the diff before handing it over. Surface its
triage **verbatim**; do not re-rank severity.

## Output

For each finding: severity (high if it makes a RED/BLOCKED gate look GREEN),
`file:line`, and one-line description of how the gate was gamed and what the real
status is. End with the honest gate ledger: which gates are actually GREEN, which
are RED, which are BLOCKED. Do not fix anything unless asked — report.

## Integration

- `honest-gates` — the rules this skill audits against.
- `executing-plans` — calls this at stage boundaries and close-out.
- `code-reviewer` subagent — the independent evaluator for judgment-based findings.
