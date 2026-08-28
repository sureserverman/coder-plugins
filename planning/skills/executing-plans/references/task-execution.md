# Task execution — parallelism, test-first, Tier 1, and the executor trailer

The trunk (`../SKILL.md` § Step 3.2 — Split by parallelism and § Step 3.3 — Red-Green loop
(per task)) carries the rules. This file carries what makes each of them hold up: the
incidents they come from, the machinery that only fires on a branch, and the failure modes
that keep re-appearing when the reasoning is forgotten.

## Why a file conflict serializes rather than inlines

A file conflict is a fact about *scheduling*: it says two tasks cannot run at the same
moment, which is a different claim from "this task need not go to a subagent".
`Parallel: YES` is a delegation directive (`../../planning-projects/SKILL.md` § Stage
structure), and nothing about a sibling touching the same file withdraws it. So the
conflicting task is dispatched on its own once the first returns, and its commit carries
`Executor: dispatched — <type>` like any other.

## An inlined `Parallel: YES` task is a deviation

It is a deviation the user authorised. An unavailable dispatch *raises* the Stop condition
rather than resolving it: the run halts, the user chooses, and only then is there an inline
run to record. *"It seemed easier inline"* and *"I judged it unnecessary"* are not on that
list — `../SKILL.md` § The plan is the authorization
— dispatch without a confirmation turn is explicit that the substitution is not the
executor's call to make. When it does happen, run it, say so in the gate report's dispatch
line with the reason, and let the trailer record `Executor: inline (dispatch failed)` or
`Executor: inline (user authorised)` — the bare `Executor: inline` on a task the plan marked
`YES` is the shape that hides a silent downgrade.

## Why there is no third execution mode

The `Parallel: NO` rule retires a "delegate output-heavy sequential tasks for context
hygiene" nudge that stood in the trunk through 0.36.0. It was optional, discretionary, and
conceded in its own text that it saved no tokens — the subagent's burn simply moved. What it
actually produced was a third execution mode nobody could predict from the plan, since a
reader of `Parallel: NO` could not tell whether a task would run inline or dispatched, and
the choice turned on the executor's judgment about its own context window. A plan that wants
a task dispatched says `Parallel: YES` and gets the roster, the reconciliation and the
file-conflict rules with it. **If an inline task really would flood the orchestrator's
context, that is a planning bug** — mark it `Parallel: YES` in `planning-projects` and it
becomes a visible, reconciled dispatch instead of an invisible one.

**If the matched capability's plugin isn't enabled**, don't fall through to `general-purpose`
with no domain knowledge — resolve it from disk per
`../../dispatching-parallel-agents/references/stack-routing.md` § *Resolving a capability
whose plugin isn't enabled*. A component flagged `requires_enablement` (hooks / MCP) can't be
lazy-loaded: stop and ask the user to enable that plugin.

## Why test-first is a rule and not a preference

Written after the implementation, a test's first run cannot distinguish "the behavior is
missing" from "my test is wrong" — both print RED — so the executor debugs its own test
against code it already believes correct, and the task's early cycles are spent repairing
assertions rather than building. Measured (remote-agents `bot-live-view` sub-02, 2026-08-10):
both of Stage 1's first tasks edited the source file first, and every RED that followed was
the test's own defect — an assertion comparing callback tokens that are minted fresh per
render, and one comparing unescaped text against a presenter that HTML-escapes. Neither RED
said anything about the feature. Running the test **before** the implementation exists costs
one command and converts that ambiguity into information: a test that passes before the work
is done is testing nothing, and a test that fails for the wrong reason is defective *now*,
when it is cheap and unmistakable.

**Repairing a wrong RED is not an implementation cycle.** Fixing a test that failed for the
wrong reason does not consume the `Red-Green max cycles` budget — that budget bounds failed
*fix hypotheses about the product*, and spending it on test mechanics would make a careful
test-first task look like a failing one. Repairs are still bounded by honesty: never weaken an
assertion to reach green (`honest-gates`), and if the test cannot be made to fail for the named
reason at all, the task's `Test:` is wrong and that is a plan defect, not a debugging problem.

**The task's `Test:` selector is a naming constraint, applied when the test is written.**
When the plan names `pytest <file> -k <expr>` — or a gate check names a selector this task's
tests are meant to satisfy — **name the tests to match that expression as you write them**.
Both of the sub-02 tasks above wrote sensible names, ran them, then re-ran and renamed on
discovering the plan's selector collected only half of them; the constraint was in the task
the whole time. This is the same defect class the Preflight gate-selector probe catches one
phase earlier, and reading the selector before naming the test closes it at zero cost.

## Why the task's own `Test:` is the whole of its testing

Between the loop starting and the task's commit, the only other tests that may run are a
Tier-1 Critical's fix-scope. **Do not run the plan's `stage-scope:` command inside a task** —
not "for Task 2.3", not as a regression check across the suites the task touched. The stage
gate runs it once, at the gate, and that is where a break in a sibling module surfaces
(`../../planning-projects/references/test-scope-tiers.md` § *A stage-scope pass never runs
inside a task*, which measured a 297-second full regression run for a single task whose own
`Test:` was a one-file `-k` filter). Widening within the task's own subject — the whole test
file instead of one filter, or the class a fix touched — is task-scope and needs no
permission; a genuine class sweep (`../SKILL.md` § A bug found during execution is a class —
sweep it, fix every instance) is likewise untouched.

## Tier 1 — the quick per-task review

Whether it runs comes from `../references/review-scope.md`; do not re-derive it. **At `none`,
`light` and `standard` there is no per-task review**: a green task goes straight to its
commit, and the stage's Tier-2 pass is where its diff is read. Tier 1 runs when the declared
tier is `high` **and this task is one the declaration names** — a **risk-listed task**, whose
`Scope:`/diff touches the risk-listed area — or when *this* task carries `Review: required`,
the per-task opt-in that buys one risky task a review without raising the whole plan's tier.
A `high` declaration naming no tasks binds all of them; an ordinary task in a `high` plan
whose own diff touches nothing risk-listed does **not** run Tier 1, and the gate report
records that as scope (`Tier-1: not run — tier high, task not risk-listed`), never as an
opt-out.

**Why the default moved.** Per-task review was unconditional through 0.36.0, so a nine-task
plan paid nine review dispatches plus their re-dispatches after fixes, and the findings were
overwhelmingly about the verification apparatus rather than the product. What Tier 1 uniquely
buys is catching a Critical *before* it is built on — worth an agent when the change is risky,
not worth nine when it is prose. Tier 2 still reads every line of the same diff at the gate;
what a `standard` plan gives up is latency, not coverage. That is the trade, and it is why
`high` keeps Tier 1 and why a single dangerous task can buy it back by annotation.

When it does run: after the test is green and Status is flipped but **before** the commit,
dispatch `git-github:code-reviewer` (read-only) as a **fresh dispatch seeing only the task
diff** — never the executor self-reviewing — briefed with the task description and its
`Test:`. **Brief it to check behavioral claims too**: every sentence in the diff asserting
what the code does (a default, an exit code, a count, an "every") is verified against the
source or flagged, per `honest-gates`. Handle by severity:

- **Critical → blocking.** A Critical finding means the task is not actually done. Fix it
  inline (one fix per cycle, diagnose first — same discipline as the Red-Green loop),
  sweeping its class per `../SKILL.md` § A bug found during execution is a class — sweep it,
  fix every instance, then **re-run at fix-scope** — the task's own `Test:` plus the test
  classes the fix touched, never the full suite
  (`../../planning-projects/references/test-scope-tiers.md`) — **and re-dispatch the review**.
  Critical-review cycles count against the *same* `Red-Green max cycles` budget as test
  failures; on exhaustion, escalate like any other budget exhaustion (`../SKILL.md` § Stop
  conditions). The executor applies the fix; the reviewer only ever reports.
- **Important / Suggestion → advisory.** Do not act on them now. Append them to the plan file
  as a note under the task (`**Review notes (Task N.M):** …`) so the stage gate's deep review
  can triage the batch. They never block the task.
- **Skip for trivial/non-code diffs.** Docs-only, config-only, pure version-bump, or
  comment-only diffs don't need Tier 1 even at `high` — note the skip and proceed. Honor a
  `Review: skip` task annotation and the global opt-out the same way — but an opt-out is
  **evidenced, not asserted** (`../references/integration.md` § Review opt-out): note the skip
  *with* the quote or the cited annotation, never as a bare "skipped". A task where the *tier*
  never called for Tier 1 needs none of this: that is scope, recorded once by the declared
  tier, not a per-task skip to evidence.

  **Exception — docs that assert executable behavior are not a trivial diff.** A docs change
  **asserting a fact about** commands, flags, env vars, exit codes, defaults, paths or
  invocation examples makes exactly the **behavioral claims** `honest-gates` governs under its
  rule that a behavioral claim is a gate too, and prose is where they go unchecked longest: no compiler, no
  test. Such a diff does **not** auto-skip Tier 1. The test is *asserting*, not *mentioning* —
  naming a flag in a heading or an unchanged sample claims nothing and still skips. The Tier-1
  dispatch is scoped to the task *diff*, which bounds what it reviews, not what it may read,
  so the reviewer opens the cited source to check the claim.

Tier 1 does **not** pause to ask the user — only to fix autonomously within budget,
preserving run-to-completion.

## The executor trailer — why it exists, and how it breaks

**Keep the trailer to one physical line.** Git folds a continuation into the preceding
trailer only when it is **indented**; an unindented wrap ends the block instead, so the
trailer vanishes from every `%(trailers:…)` query with no error at all. The rule in the trunk
is deliberately stricter than git — one physical line, never a folded continuation — because
"indent it and it still parses" is a detail nobody checks at commit time and the failure
is silent. Put the reason in the body; keep the trailer bare.

**A routed agent that cannot commit does not become an inline task.** Four of the agents
the routing table names have no `git commit` in their tool grant, so the agent does the
work and reports, this session runs the `Test:` and writes the commit, and **the trailer
still names the agent** — it records who did the work, not who typed `git commit`
(`../../dispatching-parallel-agents/references/stack-routing.md` § *Not every routed agent can
commit*, DEC-015).

Name the actual `subagent_type` that ran the work, not the routing table's suggestion, and
say so when a dispatch failed and finished inline: a substitution nobody can see is the
defect this trailer exists to end. **A trailer that misstates who ran the task is worse
than none** — it converts a visible gap into a false record. Why a trailer at all: every
other artifact is byte-identical whether a task ran inline or dispatched, so
`git log --format='%(trailers:key=Executor,valueonly)' <base>..HEAD` is the only check
that can read "5 marked YES, 0 dispatched" straight off the log.

## Committing a task whose plan lives outside the repo

Rule 7 mandates committing the work, the Tier-1 fixes and the flipped `Status: [x]` together,
which reads as one action and is two whenever the plan sits **outside the repo it plans**.
The portfolio convention puts plans in the vault (`<vault>/Portfolio/<area>/<name>/plans/`),
which is an NFS Obsidian store and not a git repository at all.

The two halves, and where each runs:

| The edit | The commit |
|---|---|
| The plan file, at its **absolute path**, from wherever you are | The **repo root**, with `git add`/`git commit` |

**Never change directory into the plan's directory to make the edit.** The observed failure —
roughly 20-25 refused commits across four sessions — was a single chained command that moved
into the plan's directory, edited the file there, and then ran `git add -A && git commit`. The
edit lands, the git command dies on `fatal: not a git repository`, and the task's work is left
uncommitted while the plan already reads `[x]`. That ordering is what makes it worth a rule:
the failure is not "the commit did not happen", it is "the marker and the commit disagree",
which is the one state the `Status:` flip exists to make impossible.

**What becomes of the flip.** For an in-repo plan the `Status: [x]` flip is part of the task's
commit, exactly as rule 7 says. For a **vault-resident** plan it rides no commit at all: the
flip is written to the vault file and is authoritative there, and the task's commit carries
only the work. Nothing is lost — `plan-progress.py` and `portfolio unify` both read the plan
file, not the log — but a gate report that claims the flip was committed is claiming something
that did not happen, so say which case the run is in.
