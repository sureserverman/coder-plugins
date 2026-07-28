# Set-valued gate checks — write the sweep that proves the property

The class-predicate rule (DEC-005) and the `validate-gate-checks.py` contract.

### Write a set-valued check as the sweep that proves it

A check asserting a property of a **set** — "no file still claims X", "every example sets
Y", "all callers handle Z" — is written as the **command that sweeps the set**, never as
prose about one member of it:

- **BAD** — `- [ ] the README no longer claims the stack is not project-agnostic`
- **ALSO BAD** — `` - [ ] `grep -q 'not yet project-agnostic' <plugin>/README.md` exits 1 ``
- **ALSO BAD** — `` - [ ] `grep -c 'x' <plugin>/README.md` = 1 and no stale claims remain`` — bolting plural-sounding prose onto a narrow command does not widen its scope; the sweep still never runs
- **GOOD** — `` - [ ] `! grep -rl 'not yet project-agnostic' <plugin>/` `` — no file in the plugin still carries the claim

The first form is not merely vaguer. **An instance-shaped check cannot fail on the siblings
that make the class**, so it passes while the other members of the defect class survive — and
each survivor costs another remediation round at the gate. Naming one file where the goal is a
property of many is how a single defect gets discovered three times.

The second form is the trap worth naming explicitly: **being a shell command is not the
point — scope is.** A command that inspects exactly one path is every bit as instance-shaped
as the prose, and it will pass a mechanical classifier that can only read syntax. Scope the
command to the set (a directory, a glob, a file list you generate), not merely to something
that looks executable.

So when writing a gate check, ask what set the claim is really over. If the answer is more
than one artifact, the check is a command **over that set**. If the claim genuinely needs a
reader — "reads coherently", "the flow works end-to-end", a conformance judgment over a diff
— mark it **`(judgment)`** and name why a sweep cannot prove it, so the executor routes it to
the evaluator instead of trying to make prose executable. Those two shapes cover every
legitimate check; anything else is an instance-shaped claim waiting to be rewritten.

This is enforced mechanically rather than left to discipline. `../scripts/validate-gate-checks.py`
classifies every check in a plan as EXECUTABLE / JUDGMENT / INSTANCE-SHAPED / PROSE, and
`executing-plans` runs it at critique time (its Phase 1 step 4a). Run it on the plan before
you present it:

```bash
python3 ../scripts/validate-gate-checks.py <plan>
```

**A newly authored plan must come back clean** — zero INSTANCE-SHAPED. Existing plans predate
the rule and are only *reported* by `executing-plans`, never retro-failed; that asymmetry is
deliberate, because a check executors learn to route around protects nothing.

Be honest about where the "mandatory" half lives: it is **this checklist**, and nothing else.
No plan-file marker records that a plan was validated, so `executing-plans` cannot tell a
post-rule plan that skipped the check from a legacy one — it reports either identically. A plan
authored outside this skill, or hand-edited after authoring, reaches execution unenforced. If
that becomes a real leak, the fix is a marker the authoring check writes and the executor looks
for; today it is discipline with a mechanical *reporter*, not a mechanical *gate*. Calibrated
against 374 real gate checks across 41 plans; its known limits, including the one escape hatch
left open, are stated in the script's own docstring.
