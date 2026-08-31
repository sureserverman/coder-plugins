# Phase Close-out — after the last stage

Reached once, at the end of a plan, and only when every stage is green. The trunk
(`../SKILL.md` § Phase Close-out — After the last stage) points here; this file is the
procedure. Work the steps in order.

1. Run the plan's **sole plan-scope pass** — the only `clean` and the only full
   expensive-suite run in the whole execution (intermediate gates ran stage-scope), including
   any quarantined slow tests. Use the plan's declared `plan-scope:` command when present. If
   the final stage gate already ran this exact plan-scope pass and no commits landed after it,
   that pass counts — don't run it twice.
2. Run any integration / e2e tests the plan flagged.

2a. **The tier's Tier-2 pass, if it lands here rather than at a gate.** At `light` the deep
   review is **one `git-github:code-reviewer` (read-only) pass over the whole plan diff**
   (`<plan-base>..HEAD`), and this is where it runs — the stage gates deliberately ran none.
   At `standard` and `high` the Tier-2 passes already ran per stage gate, so nothing is owed
   here except `high`'s second independent pass. At `none`, nothing. Handle the verdict by the
   same rules a gate uses: a **Critical blocks the merge** (fix, re-run at fix-scope,
   re-dispatch — and that re-dispatch counts a remediation round), and every **Important**
   leaves close-out **fixed** per the exit criterion. Report it in the close-out list with the
   agent and the diff range, exactly as a gate report would. This step exists because
   `light`'s single review is the whole plan's only white-box pass; a close-out that forgot it
   would ship a tier that reads as reviewed and was not.

3. **Independent evaluator pass.** **Whether it runs comes from `../references/review-scope.md`**
   — never at `none`; at `light` and `standard` when the final gate carries a `(judgment)`
   check; always at `high`. When it runs, dispatch a fresh evaluator briefed ONLY with the
   plan's stated goals, the per-stage Goal lines and the gate criteria — never the
   implementation transcript. It verifies the goal against the artifact itself and grades every
   finding Blocking / Material / Minor, as at the stage gate, and **each finding is repaired as
   a class** per `../SKILL.md` § A bug found during execution is a class — sweep it, fix every
   instance — a close-out evaluator reads the whole plan diff, which is the widest view any
   reader gets and therefore the one most likely to name one instance of something true of
   several. **A Blocking finding is the stop condition** — surface it before merge. A FAIL
   carrying only **Material** findings is *not* a merge blocker — but it is not a filing
   exercise either: **fix each Material finding**, sweeping its class, and report what was
   fixed. Only a Material finding you genuinely cannot fix here escalates with its blocker
   named, per the exit criterion's fourth row
   (`../references/stage-gate.md` § Exit criterion — the dispositions behind it). The
   distinction matters because "the evaluator returned no adverse findings" is not a reachable
   state for a fresh reader of a real artifact; treating any FAIL as blocking is what makes the
   final gate oscillate. Where the tier mandates it, skip only on an **evidenced** user
   opt-out; where the tier does not, report it as scope rather than as an opt-out.
4. **Bump versions for what changed**, as part of close-out rather than a follow-up.
   Breaking/removed → major; new capability → minor; fix/docs/internal → patch. Bump it
   wherever the project records it **and every place that mirrors it** — grep the old version
   string to find them. In this repo that is a plugin's `.claude-plugin/plugin.json` **and**
   its root `.claude-plugin/marketplace.json` entry, plus `metadata.version` when the
   marketplace set itself changed. Add a `CHANGELOG.md` entry if the project keeps one, and
   commit the bumps (`"chore: bump <component> to <version>"`). When the right bump is
   genuinely ambiguous, state your call and let the user override — don't silently skip.
5. Update the plan document with a closing note: append `**Completed:** YYYY-MM-DD — commits:
   <list>` at the end. Also confirm every task's `- **Status:**` is `[x]` (any remaining `[ ]`
   task was not executed — either finish it or note it as deferred). The close-out line +
   all-`[x]` statuses make the plan's done-state unambiguous for any downstream reader.
6. **Reconcile the backlog.** Scan the plan for `Closes BL-NNN` references and any tasks that
   implemented an open backlog item. Call the `backlog` skill (`remove`) with that ID list.
   Reference each removed ID in the close-out commit message.

6a. **Run the decisions-conformance check over the plan's whole diff.** This is the second
   of its two runs (the other is the final stage gate) and it is a **close-out criterion, not
   a formality**: a contradiction found here without a `Supersedes` citation blocks the merge
   exactly as it fails a gate (DEC-003), with the same two legal resolutions — re-scope the
   change, or record a deliberate supersede and cite it. It runs here rather than only at the
   gate because close-out itself lands commits the final gate never saw: version bumps, the
   `**Completed:**` line, backlog and register reconciliation. State which IDs were checked
   against which parts of the diff rather than asserting blanket conformance. Skip only when
   the diff is genuinely non-code and no decision in force bears on documentation.

7. **Reconcile the decisions register**, in both directions — this is the *recording* half
   and does not substitute for the sweep in step 6a:
   - **Supersedes citations → record them.** For each `Supersedes DEC-NNN` on a task, call
     `decisions supersede`. Until this runs the register still asserts a constraint the code
     no longer honors, and the *next* plan will be written against it.
   - **New constraints created → record them.** Execution discovers what planning couldn't:
     an approach that turned out blocked, a platform limit, a cost knowingly accepted to get
     a stage green. Call `decisions add` with the reason — constraint, evidence, rejected
     alternative, accepted cost. If you cannot name a rejected alternative or a cost, it
     probably wasn't a decision; don't pad the register.
   - Reference the recorded IDs in the close-out report and commit message.

8. **Audit workflow specs.** If `docs/workflows/` exists, call the `workflow-spec` skill
   (`audit`) against the plan's cumulative diff. For every WF-ID the plan declared (`Changes
   WF-NNN`, `Removes WF-NNN`), verify the corresponding block was updated or deleted in this
   branch. **Any `Removed` finding the audit reports that the plan did not declare is a
   regression — stop and escalate before merge.** Surface every `Moved`/`Modified` finding for
   explicit user review.
9. Report to the user with:
   - Stages completed
   - Total commits
   - Version bumps applied (component → old → new)
   - Plan location for future reference
   - Reviews that ran: each tier, the agent that ran it, and the diff range it saw — or, for
     one that did not, the same three reasons the gate report uses: the declared tier did not
     mandate it (named as scope, not as an excuse), or an evidenced opt-out or trivial diff
     where it did. Same requirement as the stage gate's, at plan scope: a close-out that says
     the work was reviewed without saying by what, over what, is the claim this list exists to
     stop being unfalsifiable.
   - **Dispatch reconciled against Preflight's roster, plan-wide.** Read the trailers across
     the whole plan (`git log --format='%h %(trailers:key=Executor,valueonly)'
     <plan-base>..HEAD`) and state `dispatch: <n> of <total> rostered tasks dispatched`, naming
     every inlined `Parallel: YES` task with its reason. Per-stage gates each reconcile their
     own slice, so aggregate coverage holds **only if every stage gate ran and reported**. The
     roster is declared once for the whole plan; this is where it is answered.
   - Backlog items closed (by ID) and any new ones opened during execution
   - Decisions recorded or superseded during close-out (by ID)
   - Workflow audit triage: blocks updated, blocks removed, undeclared changes (if any
     survived escalation)
10. Offer merge / finalize options (worktree cleanup, PR creation, branch merge). Do not merge
    without explicit confirmation.

## ACTION NEEDED — the one place the close-out report asks for something

Same form as the gate report's (`stage-gate.md` § ACTION NEEDED), and it binds here for the
same reason: a close-out ends with a merge offer, which is itself a decision, so a close-out
that also carries an unresolved question is the report most likely to bury one.

```
ACTION NEEDED: <one line naming the decision>
  1. <option>
  2. <option>
```

One block, last, options numbered. **A close-out report carrying an `ACTION NEEDED:` block
does not also announce that it is proceeding** — to a merge, a tag, or anything else.

**Step 10's merge offer is always the block, and it is why close-out has no "or none" case.**
A close-out always ends in a decision the user owns, so the block is always present: with no
other decision it carries the merge options alone, and with one it carries both, numbered
together. What may never happen is a separate `ACTION NEEDED:` block for some other decision
*plus* a freestanding merge offer elsewhere in the report — that reconstructs the pairing this
form exists to forbid, out of two individually well-formed halves. Anything the user does not
have to decide is not an `ACTION NEEDED:` item at all.

**Tier: untiered.** This mandate costs a line of text, not an agent dispatch, so per
DEC-010 it runs at every review scope including `none` — named here because DEC-017
requires a new mandate to state the rule that gates it rather than leave it inferred.

## Closing a plan whose gate could not be run

A `[~]` gate check outranks the close-out line: the plan classifies `blocked`, stays on
compass's in-flight board and keeps its `⊘ GATE BLOCKED` bar, because a check that could not
run means completion was never proven. That is correct and it is not the end of the story —
a plan can be genuinely finished with a check that will never run here.

**Write `**Blocked-accepted:** <date> — <why>` beside the `**Completed:**` line.** It records
that someone looked, understood, and closed the plan anyway; it does not claim the gate ran.
It is the only thing that retires such a plan.

**Do not edit the `[~]` to `[x]`.** That is the falsification the marker exists to prevent,
and it is what BL-077 was filed from. The block is the record; the acceptance is the decision.

**Write it at column 0.** `**Blocked-accepted:**` is recognised only at the start of a line
(BL-107): indented two spaces under the gate item it accepts — the natural place, since it
explains that specific `[~]` box — it does not parse, `plan_blocked()` stays true, and the plan
stays on the in-flight board having done everything right. Put it beside the close-out line and
name the gate check in its text instead.

### On a sub-plan, this line is load-bearing for the master

**A sub-plan's close-out line is what flips its master register entry** to `- **Status:** [x]`
(`master-plans.md` step 3), so on a sub-plan it is not only this plan's record — it is the
master's precondition. That makes deferring it a different act here than on a standalone plan:
a sub-plan whose close-out is postponed leaves the master with no legal way to advance.

**So when the gate is blocked, write both markers now rather than deferring the close-out.**
The pairing — `**Completed:**` plus `**Blocked-accepted:**` — is the whole point: it lets the
register flip on an honest record instead of forcing the choice between an unearned `[x]` and a
sub-plan that cannot unblock its dependents. Deferring "until the gate can be run" is the shape
that has actually failed: the register got flipped anyway to let the next sub-plan start, the
close-out was never written, and the master then declared the decomposition done over a
sub-plan that never closed.

Delete `.claude/plan-progress.json` as the last step, once the report is out.
