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

### The opposite error: widening past the set the claim is over

Those pressures push one way, so the failure they produce is over-correction — and that one
is worse than the mistake it avoids, because the check does not merely fail to catch things,
it **cannot pass at all**. A real example, from a gate check that shipped:

- **BAD (too wide)** — `` ! grep -rln 'BL-008' /mnt/vault/Portfolio/ --include='*backlog*.md' | grep . `` — "the entry is removed from every register that carries it"
- **GOOD** — `` ! grep -l '^## BL-008 ' /mnt/vault/Portfolio/<area>/<project>/backlog.md ``

Backlog IDs are unique **within one project's register**, not across a portfolio. Twenty other
projects number their own entries from BL-001, so the wide sweep matches two dozen unrelated
entries and reports failure whatever the plan did. It also matched any *mention* of the string
— a `Closes BL-008` in a neighbouring entry, a note explaining the removal — rather than the
entry itself, which is why the `^## ` anchor belongs in it too.

**One artifact is instance-shaped only when the claim is over many.** "Every file in this
plugin has stopped saying X" is a set of files and needs `-r`. "This project's register no
longer holds this entry" is a set of exactly one register, and naming it is correct rather
than lazy. The question is never how many paths the command touches; it is whether the paths
it touches are the ones the claim is about.

**A check nobody can pass is not a strict check, it is an absent one** — and it is worse than
absent when an executor takes it literally. That one was: the removal written against its
premise deleted three unrelated entries from a register with no version control behind it. So
before writing a sweep wider than one file, **run it once against the current tree and read
what comes back.** If it returns matches the plan will never remove, the scope is wrong.

**Mark it `(scoped)` and say why.** The validator cannot tell a correct narrow check from the
harmful one — nothing in `grep -l X one/file.md` reveals whether that file is the whole set —
so it failed both, and an author obeying it widened a claim that should not have been widened.
The marker is the third sanctioned shape beside `(judgment)`, and it carries the same bargain:
the author asserts the thing syntax cannot see, in the check, where a reviewer can read the
sentence and disagree with it.

```
- [ ] **(scoped)** `! grep -l '^## BL-008 ' <vault>/Portfolio/<area>/<project>/backlog.md`
      — backlog ids are unique within one project's register, so this file is the whole set
```

Use it only when one artifact really is the set. It is not a waiver for a narrow check over a
wide claim — that is still INSTANCE-SHAPED, and the identical check without the marker still
fails, which `tests/test-validate-gate-checks.py` group 2b pins in both directions.

### The third error, orthogonal to both: the right set, swept in the wrong direction

Scope is not the only way a set-valued check can be structurally unable to do its job. A check
can sweep exactly the right set and still be blind for its whole life, because **it can only
fail in one direction and the hazard runs the other way.**

The common shape is an allow-list: *"X appears only at A, B and C."*

```
! grep -rn 'SessionService(' src/ | grep -v 'compose_backend\|application/services.py'
```

That fails when a **new** member appears — a second constructor call, an unauthorised caller, a
leaked import. Where the hazard is an unwanted presence, it is exactly right, and most
allow-list checks are.

It is structurally blind when the hazard is an **absence** — a path that *should* do X and
doesn't. No missing call ever adds a line for a grep to find, so the check is green on the day
the defect ships and green every day after. Worse, it reads as rigorous: it names a set, it
sweeps a tree, it passes the validator.

**So name the hazard's direction before choosing the check's shape.** Ask what the defect
would look like in the tree:

| The hazard | Its shape in the tree | The check that can fail on it |
|---|---|---|
| an unwanted writer, caller, import, claim | a **new line** somewhere | an allow-list sweep (`! grep … \| grep -v …`) |
| a required call, guard, publish, invalidate that is **missing** | **nothing at all** | an invariant asserted over every operation — a test, not a grep |

Where they disagree, the check will be green for the entire life of the defect. This is the
authoring-time face of the same fact `executing-plans` records for repair time
(`../../executing-plans/references/bug-is-a-class.md` § *Two shapes*): an absence-shaped class
has no searchable fingerprint, so it is asserted as a property and never enumerated.

**The validator cannot help here, and the reason is worth stating.** Measured across one
project's plan corpus: five gate checks share the allow-list shape to the character, and all
five are correct, because each one's hazard is a new presence. A sixth with identical syntax
was blind for its whole life because its hazard was a missing call. The syntax is the same; only
the hazard differs, and the hazard is not in the text. A classifier would have to reject all
six or accept all six. **This one is an authoring judgement, and the checklist item below is
the only thing enforcing it.**

A gate check whose claim is an absence — "every path that changes the cursor publishes it",
"every writer takes the lock", "no request leaves without the header" — belongs in a task's
`Test:` as an invariant test, with the gate check *running* that test. Writing it as a sweep of
the sites the plan chose produces a check that verifies the design against itself.

This is enforced mechanically rather than left to discipline. `../scripts/validate-gate-checks.py`
classifies every check in a plan as EXECUTABLE / JUDGMENT / SCOPED / INSTANCE-SHAPED / PROSE, and
`executing-plans` runs it at critique time (its Phase 1 step 4a). Run it on the plan before
you present it:

```bash
python3 <planning-plugin>/skills/planning-projects/scripts/validate-gate-checks.py <plan>
```

**A newly authored plan must come back clean** — zero INSTANCE-SHAPED. Existing plans predate
the rule and are only *reported* by `executing-plans`, never retro-failed; that asymmetry is
deliberate, because a check executors learn to route around protects nothing.

## Worked example — a sweep is not licence to sweep twice

The rules pull in opposite directions and both are right. This one says *widen the check to
the set*; the trunk's § *Every fact has one owner* says *don't verify what a task test
already decided*. What resolves them is that the gate owns the **class** and the task owns
its **instance** — so a gate sweep is legitimate exactly when the set it covers is strictly
wider than what any task proved, and the widening can be named.

Observed live (remote-agents `bot-live-view` sub-plan 01, 2026-08-10) — one fact, *view
expiry is gone*, verified four times:

| # | The check | Verdict |
|---|---|---|
| 1 | Task 1.1 `Test:` — the migration produces no `expires_at` column | **Keep.** The task owns its instance; nothing else proves this migration is right. |
| 2 | Stage-1 gate — `! grep -rn 'expires_at\|timedelta(minutes=15)\|view_revision' src/` | **Keep.** Strictly wider and nameable: the task proved one file, this sweeps the tree for the whole vocabulary. |
| 3 | Close-out gate — the same grep again | **Keep.** Same command and same *set*, but a **larger population**: two stages of commits landed since check 2 ran. A negative-existence sweep is a regression guard, and its whole value is re-running over a tree that has grown. |
| 4 | `(judgment)` — "no surviving claim that a view can expire" | **Cut, or narrow.** As written it restates check 2 and spends an evaluator dispatch on it. It earns its place only against what a grep genuinely cannot decide — that the two surviving mentions of "expired" are *denials* rather than assertions — and then it says so. |

The plan shipped all four; three of them were coverage and one was cost.

**The boundary that decides rows 1 and 3 is the same one, read in two directions.** A task's
`Test:` is not re-proved *at that stage's gate*, because the task's commit is inside the
stage the gate is about to check — the population is genuinely identical. Across a **stage
boundary** it is not: later commits can reintroduce what an earlier sweep proved absent, and
nothing else is looking. So "one owner per fact" retires *repetition within a stage*, and
leaves *regression sweeps across stages* alone. A negative-existence check (`! grep -r …`) is
almost always the second kind.

An earlier draft of this table cut row 3 for being "the same command, the same set, the same
population". The first two were true and the third was not, and the cut would have removed the
only guard against a late stage reintroducing the vocabulary — a rule against redundancy
deleting a real check, which is the failure mode this whole reference exists to prevent in the
opposite direction.

Be honest about where the "mandatory" half lives: it is **this checklist**, and nothing else.
No plan-file marker records that a plan was validated, so `executing-plans` cannot tell a
post-rule plan that skipped the check from a legacy one — it reports either identically. A plan
authored outside this skill, or hand-edited after authoring, reaches execution unenforced. If
that becomes a real leak, the fix is a marker the authoring check writes and the executor looks
for; today it is discipline with a mechanical *reporter*, not a mechanical *gate*. Calibrated
against 374 real gate checks across 41 plans; its known limits, and both author-asserted
markers, are stated in the script's own docstring.
