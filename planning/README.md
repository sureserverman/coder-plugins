# planning

A fifteen-skill pipeline (v0.48.0) that turns a vague idea into executed work — including redesigning an app to a Claude Design handoff — keeps each project's contracts honest, and gives a cross-project portfolio view across `~/dev/`. Each skill hands off to the next; they were designed as a unit.

## Installation

Add the marketplace:
```bash
/plugin marketplace add sureserverman/coder-plugins
```

Install the plugin:
```bash
/plugin install planning@coder-plugins
```

## The pipeline

```
compass                 ── (optional entry point) what's in flight, what to
    │                      work on next, what's going stale — across every
    │                      project. Report-only; picks the work, never runs it.
    ▼
vague idea
    │
    ▼
brainstorming           ── validate the design via Q&A: purpose, constraints,
    │                      alternatives, risks. One question at a time.
    ▼
architecting-projects   ── (designs with a structural surface) research 2–4
    │                      architecture candidates via parallel researcher
    │                      agents, user approves one, write the ARCH-ID doc.
    ▼
planning-projects       ── triage a format first (Direct / Light / Standard /
    │                      Master), then stage the work: tasks with Depends on /
    │                      Blocks / Parallel fields, Red-Green cycles, gates.
    ▼
executing-plans         ── drive the plan: Red-Green loops, tiered test-scope
    │                      gates, fan independent tasks out for parallel run.
    ▼
dispatching-parallel-agents  ── one agent per task marked Parallel YES whose
                               dependencies are all green; integrate results
                               respecting the dependency graph.

  ┌─ cross-cutting, no fixed position in the flow ────────────────────────┐
  │ honest-gates       ── the integrity contract every gate above obeys.  │
  │ capability-router  ── reach a marketplace skill/agent whose plugin    │
  │                       isn't enabled this session.                     │
  └───────────────────────────────────────────────────────────────────────┘
```

## Skills

### `brainstorming`

Use **before** any non-trivial creative or implementation work — new features, refactors, migrations, behavior changes. Turns a vague idea into a validated design by exploring purpose, constraints, alternatives, and risks one question at a time. Terminal handoff is to `architecting-projects` (designs with a structural surface) or straight to `planning-projects`.

**Triggers:** "I'm thinking about adding X", "what's the best way to", "should I refactor", "design a new", "let's brainstorm".

### `architecting-projects` (since v0.17.0)

Use after a design is validated (or on a direct architecture request) to produce a researched, user-approved architecture document that `planning-projects` consumes. Derives 2–4 stack-concrete candidates, fans out one sonnet-pinned `architecture-researcher` agent per candidate in parallel (uncited claims are discarded), presents a comparison matrix for explicit approval, then writes a parser-safe `*-architecture.md` with stable `ARCH-NN` section IDs beside the plan. Plans cite the ARCH-IDs on structure-creating tasks and carry an architecture-conformance check in their final stage gate. On existing codebases, **re-architecture mode** (v0.18.0) inventories the current module map, requires each candidate's research to address the migration explicitly, and adds an `ARCH-NN Migration map` section whose ordered, build-green steps seed the plan's stage order.

**Triggers:** "design the architecture", "architecture options", "how should the codebase be structured", "compare architecture candidates", "pick an architecture".

### `planning-projects`

Produces a staged plan for a non-trivial project with phase gates before execution. Plans use a strict format with Stages, Tasks, `Depends on` / `Blocks` / `Parallel` fields, Red-Green max cycles, and Stage gates that `executing-plans` can drive mechanically.

**Format ladder (since v0.22.1).** Every request is triaged to a format *first*, so the apparatus scales to the size of the job — and a trivial request may be declined a plan file entirely:

| Format | Shape | Use when |
|---|---|---|
| **Direct** | no plan file — just do it | the job is trivial and self-evident |
| **Light** | one stage, 2–5 tasks, one gate (`*-light-plan.md`) | small but worth a test-and-gate backbone |
| **Standard** | multiple stages, full task fields, per-stage gates | the default for non-trivial work |
| **Master** | 2–7 sub-plans linked by a register (`*-master-plan.md`) | >~6 stages / >~25 tasks, or several independently shippable workstreams |

The Light and Master formats are specified in `skills/planning-projects/references/light-plan-format.md` and `master-plan-format.md`; both are parser-safe by construction (zero `portfolio unify` backlog candidates, locked by the `validate-plan-parser` CI fixture suite).

For big projects (roughly >6 stages / >25 tasks, or multiple independently shippable workstreams) it **decomposes** the work into 2–7 independently executable **sub-plans** linked by one **master plan**: the master holds the shared research, a sub-plan register (Status / plan link / Goal / cross-plan `Depends on`+`Blocks` / `Parallel`), and a `**Gate:**` block of integration checks per entry. The canonical format lives in `skills/planning-projects/references/master-plan-format.md` and is parser-safe by construction — a master plan yields zero backlog candidates in `portfolio unify` (locked by the `validate-plan-parser` CI fixture suite); the sub-plans carry the real tasks.

**Triggers:** "plan", "roadmap", "how should I build", "break this down", "what are the steps", "create a plan", "what order should I do this".

### `executing-plans`

Takes a plan file produced by `planning-projects` and executes it. The skill is a **trunk plus references**: what fires on every run stays in `SKILL.md`, while the master-plan and light-plan execution models, the review-scope and opt-out rules, the dispatch-fidelity rationale, the gate-failure procedure, the progress-state schema and the sources load from `skills/executing-plans/references/` only when their condition is met. `planning-projects` is split the same way (plan template, task-field specs, set-valued-check rules). Drives Red-Green loops, respects the stage-gate model, and dispatches independent tasks through `dispatching-parallel-agents` — **without a confirmation turn, because approving the plan was the request** (a standing caution against calling the Agent tool is conditional, not absolute; with no plan in play it still applies and you still ask). **A bug found anywhere during a run is treated as a defect class**: diagnose, name the set, enumerate it with a command, and fix every member — the whole project is the search space, not the plan's blast radius, and the sweep costs a command rather than a dispatch, so no review tier gates it. It executes every rung of the format ladder — a **light plan** runs with proportionate machinery (Preflight-lite, inline no-parallel execution, one whole-diff review instead of per-task Tier-1, a single stated version bump; whether an evaluator runs beside that review comes from the review tier, not the format — see the composition rule below). Also executes **master plans** (`*-master-plan.md`): sub-plans run in register dependency order, each via the normal single-plan flow (ideally one per fresh session — the master file is the cross-session handoff artifact); each sub-plan completion flips its register `Status`, runs that entry's cross-plan `**Gate:**` checks, and commits `"Sub-plan N green"`; version bumps are deferred from sub-plan close-outs to the single master close-out.

Preflight includes a **git bootstrap** — if the project isn't a repo it runs `git init` (and offers a GitHub remote) so the per-task commits have somewhere to land. Execution **runs to completion**: stage gates are checkpoints, not approval gates, so it doesn't pause between green stages to ask permission — only the documented stop conditions halt it. At each stage gate it invokes a matching **platform stage-verify skill** (Android → `android-stage-verify`: build the debug APK, and if an adb device is attached, install + smoke-launch + run instrumented tests). At close-out it **bumps versions** for whatever the plan changed, across every mirror of the version string (e.g. a plugin's `plugin.json` and the root `marketplace.json`).

**Test-first Red-Green (v0.42.0).** The task's test is written and run **before** the implementation, and must go RED for the reason the task names. A RED that means something else is a defective test, diagnosed as such on the spot rather than debugged against code the executor already believes correct — and repairing it doesn't spend the `Red-Green max cycles` budget, which bounds failed hypotheses about the product. Where the task's `Test:` names a `-k` selector, that selector is a naming constraint applied as the test is written, not a rename discovered after it passes.

**Tiered test-scope gates (v0.24.0).** Gates run the tests their tier warrants rather than the whole suite every time — cheap host-side checks always run in full, expensive suites (device / instrumented / e2e) are scoped:

- **task-scope** — inside a task: the task's own `Test:` and nothing wider (v0.42.0). The `stage-scope:` command never runs "for Task 2.3" — a break in a sibling module surfaces at the stage gate, which is the one place that sweep is scheduled.
- **fix-scope** — after a review fix inside a Red-Green cycle: the task's own `Test:` plus the test classes the fix touched.
- **stage-scope** — at an intermediate stage gate, **once per gate entry** (v0.41.0): restricted to the modules the stage's commits touched, never `clean`.
- **plan-scope** — exactly one clean full pass, at close-out (the final stage's gate runs at this tier).

A scoped gate report always discloses what actually ran. Policy lives in `skills/planning-projects/references/test-scope-tiers.md`, shared with `planning-projects`.

**Tiered verification scope (v0.37.0).** The same idea applied to the *verification* machinery, which through v0.36.0 ran at close to one weight regardless of what it reviewed. The plan declares a tier at Preflight from its cumulative diff and repeats it in every gate report, so a downgrade is on the record rather than silent:

| Tier | When | What runs |
|---|---|---|
| **none** | docs / config / version-bump / comment-only | the plan's own tests and gate checks, nothing else |
| **light** | no new executable behavior, **or** under ~200 changed lines across ≤ ~5 files, and nothing risk-listed | + **one** whole-plan-diff review, at close-out |
| **standard** | multi-file code with new behavior — the default, and what an undeclared run gets | + one Tier-2 review per stage gate; an evaluator only at gates carrying a `(judgment)` check, plus a close-out evaluator when the final gate carries one |
| **high** | security / auth, data-destructive, public API, schema / migration | the full apparatus: per-task Tier-1, per-gate Tier-2 + evaluator, a second independent close-out pass |

**What the tier gates** is every mandate that costs an agent dispatch: both review tiers, the gate and close-out evaluators, the Preflight dispatch probe, and the design-fidelity verify loop's evaluator. What it never gates is the cheap-but-load-bearing half — the dispatch roster, the executor trailer, the dispatched-vs-inline reconciliation, honest-gates disclosure, the class sweep run on any bug found during execution, and the plan's own tests. Concretely, counting **verification** dispatches only — the plan's own `Parallel: YES` task dispatches are execution, not verification, and are never tiered — a Standard 3-stage / 9-task plan whose gates each carry a `(judgment)` check costs **7** at `standard` (3 Tier-2, 3 gate evaluators, 1 probe; 8 if its close-out evaluator is a separate dispatch, 4 if its gates are all executable sweeps). The same plan under v0.36.0 mandated **17** (9 Tier-1, 3 Tier-2, 3 gate evaluators, 1 close-out, 1 probe), before any re-dispatch after a fix — and re-dispatches were unbounded, which is the larger part of the saving.

The prior version of this table was reachable only in theory — `light` required prose or config edits, **a single file**, or the absence of new executable behavior. In practice almost nothing landed there: the first two disjuncts exclude any real multi-file plan, and the third turns on a judgment ("new executable behavior") that an executor under the old "never take the lighter option" rule resolved upward every time. A criterion nothing can satisfy is a dead branch, not a conservative default. The bar is now a size the diff can be measured against, with escalation carried by the risk list instead.

**Escalation is by risk, not by size (v0.37.0).** The format ladder and the review tier answer different questions and a plan carries both, so: **the format decides the review's shape** (Direct/Light → one whole-diff pass; Standard/Master → per stage gate), **the tier decides its depth** (how many passes, and whether an independent evaluator runs). Ambiguity resolves by the **risk floor**: touching a risk-listed area sets `high` whatever the size, and size alone never escalates — a large prose or mechanical-rename diff is a big `light` change, not a `standard` one. This replaces "never take the lighter option", which was right for the dangerous case (a Light plan touching auth still gets whole-diff shape *and* `high`'s depth) and wrong for every other, making small prose plans pay `standard` for no protection. Master plans declare a tier per sub-plan, and the master's own close-out takes the highest any sub-plan declared.

**Two-tier code review.** Execution wires in `git-github`'s read-only `code-reviewer` agent on a distinct axis from the goal-evaluator (*code quality* vs *goal attainment*). **Tier 1** reads one green task's diff before its commit, where a Critical blocks the task and is fixed within the same Red-Green cycle budget — it runs **only at `high`**, or on a task the plan annotated `Review: required`. **Tier 2** is the deep pass: one review over the whole plan diff at `light`, one per stage gate at `standard` and `high`, where a Critical is a gate failure and every Important leaves the gate **fixed** — the backlog is not a disposition for a defect. Trivial/non-code diffs are auto-skipped at either tier. Per-task review was unconditional through v0.36.0, which made a nine-task plan pay nine review dispatches plus a re-dispatch after every fix; Tier 2 still reads every line of the same diff, so what a `standard` plan gives up is latency, not coverage.

**Live progress.** Execution state is mirrored to `.claude/plan-progress.json` at every transition, and `skills/executing-plans/scripts/plan-progress.py` renders it as a statusline progress bar (`⚙ plan ▐██████░░░░▌ 3/6 (50%) · S2/3 ▶ T2.2 …`). It chains after an existing statusline invoked as a plain `bash <script>` and prints nothing when no plan is executing; done/total are derived from the plan's authoritative `Status:` fields, so a missed update shows a wrong CURRENT-TASK label rather than wrong counts — and, since BL-096, a `⚠ status lag N` marker when the markers themselves stop moving.

**Wiring it — `/planning:statusline`.** The bar needs one entry in your global `~/.claude/settings.json`, and that entry is the one piece a plugin cannot ship: `statusLine` is not a plugin contribution point (a plugin's `settings.json` supports only `agent` and `subagentStatusLine`). So the plugin ships the parts — `scripts/statusline-chain.sh`, which runs your existing statusline first and appends the bar on the next line, resolving the renderer as its own sibling so it carries no absolute path — and `/planning:statusline install` generates the pointer. `status` reports what is wired, and the installer refuses to clobber a third-party `statusLine` without `--force`. What it can preserve as that base is a plain `bash <script>` entry; anything else (a `node` command, a pipeline, arguments of its own) is replaced under `--force`, reported on stderr, and kept in the timestamped backup. `remove` takes the bar back out — restoring a preserved base if there was one, otherwise clearing the key. Wiring is **global and one-time**, not per project. Hand-authoring a wrapper instead is what this replaces: a hand-written one hard-codes a checkout path and keeps running that copy after the plugin moves, so the shipped renderer and the running one drift apart with nothing to catch it.

**Triggers:** "execute this plan", "run the plan", "drive this plan to green", "work the plan in plan.md".

### `applying-design-handoff`

Redesigns an app to **precisely reproduce a Claude Design handoff pack** (the spec bundle from claude.ai/design — tokens, components, layout, assets), reshaping functionality to fit the design where they conflict. Auto-detects the input (a local exported bundle or a live claude.ai design-system project via the `DesignSync` tool), inventories the app and its `workflow-spec` contracts, builds a design→app fidelity map, and writes a **reconciliation report** — the design wins, but every behavior change is declared via `workflow-spec` (`Changes`/`Removes WF-*`) and destructive changes require user sign-off. Implementation is cross-platform: it delegates to the **`design-handoff-reproducer`** subagent for precise per-slice reproduction, briefed with whatever stack skill the routing table names for the surface, then runs a fidelity verify loop (separate evaluator, rubric-graded, max 3 iterations). `executing-plans` drives it for a design-handoff/redesign task and fires the fidelity loop as a stage-gate hook.

**Triggers:** "reproduce this design", "apply the handoff pack", "redesign to match the design", "implement the Claude Design spec".

### `dispatching-parallel-agents`

Used by `executing-plans` (or directly) when a task is marked `Parallel YES` and its dependencies are green — one such task or many. Dispatches one agent per task, runs them concurrently, integrates results respecting the plan's dependency graph.

**Triggers:** "dispatch these tasks in parallel", "run these in parallel", "fan out the parallel-marked tasks".

Routing is table-driven: `references/stack-routing.md` maps each task's stack to a matched subagent (`rust-expert`, `testing-expert`, `design-handoff-reproducer`, …). `executing-plans` consults the same table to hand independent, output-heavy *sequential* tasks to a subagent for context hygiene. A CI-enforced `validate-stack-routing.py` check fails the build when the table names an agent or skill the marketplace no longer ships.

### `honest-gates`

The integrity contract behind every gate in this plugin — and any acceptance check, test command, or "done" claim elsewhere. A gate is **GREEN** only when its real command ran *here* and passed; otherwise it is **RED** or **BLOCKED**. Never a stubbed task, fabricated evidence, a hidden exclusion, or a self-graded miss. Includes escalation rules for a genuinely blocked gate, so "I couldn't run it" stays distinguishable from "it passed". Applies eagerly — it does not wait to be asked.

**Triggers:** any point where something must pass, build, run, or be measured — before reporting a gate green, registering a build/test task, or recording test/benchmark evidence.

### `capability-router`

Reaches a marketplace capability — a skill or a subagent — **even when its plugin isn't enabled in this session**. Enablement only controls what Claude Code injects at session start; every component's files are on disk regardless. Looks the capability up in `capability-index.json` and loads it from disk (reading a SKILL.md, or injecting an agent body with its `model` pin). This is the ad-hoc entry point to the same disk-resolution flow `executing-plans` and `dispatching-parallel-agents` use mid-plan. Components that need runtime registration (hooks, MCP) can't be lazy-loaded — those stop and ask you to enable the plugin.

**Triggers:** "load the Rust expert", "which plugin covers X", "write idiomatic Rust", "review my game design".

### `no-fafo-debugging`

The diagnostic counterpart to the pipeline. Blocks "Fix And Forget" — speculative patches that make the symptom go away without explaining root cause. Fires at the **start of any debugging or diagnostic work**, not just when a plan task fails red: the moment a symptom, error, failing test, crash, or "it's not working" shows up, before the first hypothesis. Also drives evidence-first **autonomy** — Claude reads logs, runs read-only diagnostics, reproduces failures, and builds interceptors/probes *itself*, escalating to the user only when genuinely blocked (access it lacks, a world-action only the user can take, or a decision only they can make) — and when it must ask, it asks once, batched and specific.

**Triggers:** "debug this", "why is X broken", "fix this bug", "diagnose", "investigate", "it's not working", "tests are failing", a stack trace / error / crash / hang / regression — any diagnostic request where evidence-first root-cause analysis is expected over speculative patches.

### `backlog` (v0.4.0+; v0.5.0 adds `unify` + `complete`)

Owns the per-project deferred-work register at `<portfolio_home>/backlog.md` (vault-canonical — there is no repo mode; a missing `vault_dir` fails loudly). Append on defer, remove on implement, list on plan research. **It admits three kinds and refuses a fourth:** a significant improvement, a non-urgent decision the user must make, and work the user explicitly chose to defer — never a defect found during plan execution, which is fixed and its class swept instead. `add` refuses those rather than filing them, so the rule does not depend on the executor's self-discipline under gate pressure. v0.5.0 adds:

- `unify <project-path>` — derive backlog candidates from this project's plans via the parser rules in `portfolio/references/plan-parser.md`. Dedups by exact `Source` string equality. Dry-run by default.
- `complete <BL-NNN> --summary "<text>"` — archive a backlog item as a short `<portfolio_home>/plans/YYYY-MM-DD-<slug>-done.md` plan-summary and remove the entry. Commit convention `Closes BL-NNN` remains the audit trail.

**Triggers:** "add to backlog", "defer this", "what's in the backlog", "BL-007 is done", "unify plans and backlog for this project".

### `decisions` (since v0.27.0)

Owns the architectural-decision register in two linked halves: per-project
`<portfolio_home>/decisions.md` (`DEC-NNN`) and per-architecture-domain
`Portfolio/decisions/<domain>.md` (`GDEC-<DOM>-NNN` — `android`, `ios`, `rust`,
`ubuntu`, …). Every entry carries the **reason** behind the choice: the constraint,
the evidence, the rejected alternative, the accepted cost.

- `add` / `list` / `read` — record and consult decisions for one project.
- `relevant` *(since v0.29.0)* — **the question planning and execution actually ask:**
  which recorded decisions constrain the work in front of me? Infers the domain
  registers from the project's stack (`decisions/references/domain-slugs.md`, paired
  with the stack-routing table) and returns a digest of both halves, rather than raw
  files. Superseded entries come back **marked, not filtered** — "we believed X and
  stopped" is what stops the rejected approach being re-proposed; malformed blocks come
  back **flagged, not dropped**.
- `promote <DEC-NNN> --domain <slug>` — lift a project decision into its domain
  register, writing **both** link directions in one step. That symmetry is what
  makes the two halves one register instead of two.
- `supersede` — replace a decision that no longer holds. The old entry stays, marked
  `superseded by DEC-NNN`; its reason is the record of what was believed and why.

Underneath `relevant` is a deterministic script you can also run directly:

```bash
python3 <plugin>/skills/decisions/scripts/decisions-relevant.py --list-domains
python3 <plugin>/skills/decisions/scripts/decisions-relevant.py \
    --domains android,tor --project myapp --area android --format json
```

It imports the same fixture-locked parser `portfolio rebuild` uses, so the digest can't
disagree with the roll-up. Missing `vault_dir` fails loudly rather than falling back
inside the repo.

**Brand-new projects are a first-class case.** The two halves resolve independently:
`decisions.md` needs a registry entry, but `Portfolio/decisions/<domain>.md` is keyed by
domain and resolves from `vault_dir` alone. So a project with no registry entry gets
`project_register: absent` **and still receives the global half** — which is the half
that matters most to a greenfield codebase, since it inherits every constraint its
platform has already accumulated. An absent project half never means "no decisions
apply"; treating it that way would leave the newest codebase, the one still cheap to
change, consulting the fewest constraints.

`portfolio rebuild` reads both halves, renders `Portfolio/global-decisions.md`
(by-domain index, per-project counts, malformed entries, link asymmetries,
unresolved targets), and adds a `Decisions:` pointer to the repo sidecar. Symmetry
gaps are **reported, never auto-fixed** — repairing one side would assert an edge
about a project the run has not read. `compass-scan.py` surfaces a per-project
`{count, malformed, domains, last_decided}` summary.

**sec-audit recommendations** are recorded here under a hard rule: cite the report by
filename and date, restate its substance in the entry's own words, and
never embed the report body — those reports are local-only and gitignored
across the portfolio.

Format: `portfolio/references/decisions-format.md`.

**Triggers:** "record this decision", "why did we choose X", "log this sec-audit recommendation", "promote this to the android decisions", "what binds all Rust projects".

#### How a decision reaches the code (since v0.29.0)

A register nothing consults at implementation time is a filing cabinet. Decisions
therefore travel the whole pipeline, using the **same mechanism as `ARCH-NN`** citations
so nothing downstream needed new machinery:

| Stage | What happens |
|---|---|
| **Planning** | `planning-projects` runs `relevant` at research time and writes the result into the plan as a `## Decisions in force` section — non-checkbox bullets, so the portfolio parser never mistakes them for deferred work. Records *what was consulted*, so a reader can tell "nothing binds this" from "nobody looked". |
| **Task authoring** | A constrained task cites `Honors DEC-003`. A task that deliberately overrides one cites `Supersedes GDEC-AND-002 — <why>`, which is what makes the override auditable instead of silent. |
| **Preflight** | `executing-plans` **re-runs the scan and diffs it** against the plan's section. The register accretes between planning and execution, so a plan can honor a constraint that has since been superseded. A plan with no section is handled as *"not recorded"*, never *"none apply"*. |
| **Dispatch** | Every sub-agent's prompt carries the entries bearing on its task. A dispatched agent sees a task, a file list, and a slice of research — never the register — so a constraint absent from its prompt is one it cannot honor. |
| **Stage gate** | A change contradicting a decision in force **without** a `Supersedes` citation is a **gate failure**, not an advisory. Two legal resolutions: re-scope, or record the supersede and cite it. The check discloses what it examined, because unlike a test command it is a judgment call over a diff. |
| **Close-out** | Declared supersedes get recorded via `supersede`; constraints *execution itself* discovered (a blocked approach, a platform limit, a cost accepted to get a stage green) get recorded via `add`. |

The Light and Master rungs carry this proportionately: a Light plan states its decisions in
one `Context:` line rather than growing a section, and a Master plan holds the section once
at master level with sub-plans citing IDs rather than restating them — a duplicated
constraint drifts, and the copy nobody updated is the one someone implements from.

### `workflow-spec` (v0.4.0+)

Owns behavior contracts at `docs/workflows/`. Provides `capture` (draft a spec for a scope), `audit` (regression checklist against a diff), `refresh` (re-verify and re-stamp), and `list` subcommands, so behavior changes can be detected against a versioned spec. There is no `extend` subcommand — extending a spec happens through `capture`.

**Triggers:** "capture this workflow", "audit workflows against the diff", "this PR changes documented behavior".

### `project-maturity` (since v0.5.0)

Scaffolds and audits a per-project `<portfolio_home>/MATURITY.md` checklist across six publishing-readiness axes: Documentation, Security, Packaging, UI/UX, i18n, Testing & CI. Three subcommands:

- `init <project-path>` — scaffold MATURITY.md from a template.
- `audit <project-path> [--write]` — run deterministic auto-detectors (file globs, sec-audit-report findings parse, packaging-recipe presence, locale dirs, CI workflow detection). Dry-run by default. Never overwrites manual `[x] claim:` lines.
- `get <project-path>` — return parsed state as JSON for the portfolio orchestrator.

**Triggers:** "scaffold maturity", "is this ready to publish", "ship-readiness", "init MATURITY.md".

**v0.5.1:** the UI/UX icon auto-detector now recognizes the WebExtension layout — an `icons/` dir holding `icon*.{png,svg}` beside a `manifest.json` (e.g. `mozilla/icons/`, `chrome/icons/`, or root `icons/`) — in addition to root-level `icon.*`/`app-icon.*` and Android `res/mipmap-*`.

### `compass`

The portfolio **work orchestrator** — decides *what to work on*, where `portfolio` maintains the artifacts. Answers three questions across every registry project, grounded in evidence reconstructed fresh each run (no maintained state, nothing to drift):

- `compass now` — what is in flight? (in-progress plan stages, current task)
- `compass next` — what should I pick up? Ranked by momentum > almost-shippable > unblocking > staleness, with cited evidence on every recommendation.
- `compass review` — a periodic sweep: what's going stale, what's parked, where the gaps are.

The deterministic `compass-scan.py` (CI-guarded, reusing `portfolio-unify`'s plan-parser regexes) rebuilds the cross-project picture from plan stages, backlog open/parked counts, maturity gaps, integration edges, and git recency; the judgment layer only ranks. Respects `Parked:` annotations in backlogs. **Report-only** — it recommends, and never launches work or writes portfolio artifacts.

**Triggers:** "what should I work on next", "what's in flight", "portfolio review", "what's going stale".

### `portfolio` (since v0.5.0)

Cross-project orchestrator. Single user-facing entry point that ties registry + per-project unification + per-project maturity into one command. Subcommands:

- `scan` — load `~/.claude/projects-registry.yaml`, walk `~/dev/` for project markers, surface drift; first-run flow auto-seeds the registry.
- `unify` — dispatches a sub-agent per registered project (8 in flight) that invokes `backlog unify`. Aggregates candidate reports; user accepts per-project.
- `maturity` — dispatches a sub-agent per project that invokes `project-maturity audit`; surfaces stale claims.
- `migrate` — moves a project's plans/backlog/maturity from in-repo `docs/` into its vault `portfolio_home`, making the vault canonical. Dry-run first.
- `integrate` — reads each project's `integration.md` and merges the declared edges into `Portfolio/integration-graph.md` + `integration-backlog.md`. Symmetry gaps are **reported, never auto-repaired**.
- `rebuild` — regenerates the global roll-ups in the vault: `global-backlog.md`, `global-maturity.md`, `global-decisions.md`, `global-business.md`, `global-security.md`, plus each repo's `PORTFOLIO-STATUS` sidecar block. Preserves a `<!-- BEGIN PRESERVE — content below this line is preserved across rebuilds -->` ... `<!-- END PRESERVE -->` block (the exact sentinels the parser matches — a hand-authored approximation is silently discarded on the next `rebuild --write`) in `global-backlog.md` for hand-curated cross-project items. Writes only with `--write`; **a second consecutive run must produce zero writes**, and that idempotency is a gate every plan touching this lane has to preserve.

- `plan-status` — reconciles every vault plan's *recorded* status against its *actual* task completion, and surfaces the plans whose status is wrong. A finished plan that was never close-out-marked keeps feeding phantom work to `unify` (which mines its open tasks as backlog candidates) and to `compass next` (which ranks projects by what is in flight); nothing else compares the two. **Report-first — the default run writes nothing**; `--fix` asks per plan and backs the file up first, `--restore <run-id>` reverts a run wholesale. The corpus is the vault, not the registry. Evidence is **graded**, strongest first: a master's sub-plan register marking this exact plan done (and naming a commit that resolves) identifies *the plan* and lives in the vault rather than git; a commit naming the plan file is next; stage-completion commits dated after it are merely correlative and identify a repo and a period, never a plan. The grade is written into the recorded line. Each candidate also shows its **stage-gate state**, since *all tasks `[x]`* is not the same as *finished*. It **never infers `**Abandoned:**`**: a marker nobody adopts degrades to the status quo, while a heuristic false-positive hides live work.

Default flow composes the four in order: `scan → unify (dry-run) → maturity (opt-in during staged rollout) → rebuild`. Idempotent: re-running with no upstream changes produces zero writes. `plan-status` is **not** in the default flow — it is opt-in and on no execution path.

**Triggers:** "portfolio scan", "global backlog", "what's parked across projects", "ship readiness across projects", "scan all my projects".

## Agents

Two subagents ship with the plugin. Both are dispatched by their owning skill — you don't normally invoke them directly, though you can.

### `architecture-researcher`

Researches **one** candidate architecture (a pattern plus a concrete module layout) and returns cited findings: evidence, a directory tree, boundary definitions, and risks. `architecting-projects` fans out one per candidate, in parallel, then discards any uncited claim before building the comparison matrix.

**Model:** `sonnet`. **Tools:** read-only plus `WebFetch`/`WebSearch` — it researches, it does not write code.

### `design-handoff-reproducer`

Reproduces **one** slice of a Claude Design handoff pack (a component or screen, plus its tokens and assets) precisely in the target stack, self-checking against the fidelity rubric. Dispatched per slice by `applying-design-handoff`. It reproduces; it does not design — and it **FLAGs** a behavior change back to the caller rather than applying one.

**Model:** `sonnet`. **Tools:** `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`.

## Hooks

### `plan-continue` (since v0.45.0) — **off by default**

A `Stop` hook (`hooks/hooks.json` → `hooks/plan-continue.sh`) that refuses a turn ending on a
promise or an approval question while a plan is in flight, so an authorized run doesn't sit
waiting for you to say "carry on". It returns `{"decision":"block"}` only when the plan's
`.claude/plan-progress.json` reads `preflight`/`task`/`gate` **and** the last assistant message
matches a promise (*"Next: Task 2.4"*, *"I'll start…"*) or an approval question (*"say the
word"*, *"ready to start Stage 2"*) while matching neither a wait marker (*"waiting on"*,
*"once it reports"*) nor an `ACTION NEEDED` block.

That distinction is the point: a turn that ends **waiting** on a dispatched reviewer is
correct on this host — Claude Code re-invokes when the agent reports — so blocking it would
spin. Measured across two real sessions of one master plan (39 turn ends): 7/7 promise-shaped
stops caught, 0 of the 30 legitimate waits blocked.

Enable per project in `.claude/settings.json`:

```json
{ "env": { "PLAN_CONTINUE": "1" } }
```

`PLAN_CONTINUE_MAX` (default 3) bounds continuations while the plan does not move. It fails
open on every unexpected condition and always exits 0. Full contract:
`skills/executing-plans/references/plan-continue-hook.md`.

## Where artifacts live

Everything this plugin persists is **vault-canonical**, not in your repo. `portfolio_home` resolves as `<vault_dir>/Portfolio/<area>/<name>/`, where `vault_dir` comes from `~/.claude/portfolio-config.yaml` and `area`/`name` from `~/.claude/projects-registry.yaml`.

| Artifact | Path | Written by |
|---|---|---|
| Plans (all rungs) | `<portfolio_home>/plans/YYYY-MM-DD-<topic>-plan.md` | `planning-projects` |
| Architecture docs | `<portfolio_home>/plans/YYYY-MM-DD-<topic>-architecture.md` | `architecting-projects` |
| Backlog | `<portfolio_home>/backlog.md` | `backlog` |
| Decisions (project) | `<portfolio_home>/decisions.md` | `decisions` |
| Decisions (domain) | `<vault_dir>/Portfolio/decisions/<domain>.md` | `decisions promote` |
| Maturity | `<portfolio_home>/MATURITY.md` | `project-maturity` |
| Global roll-ups | `<vault_dir>/Portfolio/global-*.md` | `portfolio rebuild` |
| Behavior contracts | `<repo>/docs/workflows/` | `workflow-spec` |
| Live execution state | `<repo>/.claude/plan-progress.json` | `executing-plans` (ephemeral, gitignored, deleted at close-out) |

**Prerequisite:** `vault_dir` must be set. If it is unset, the portfolio scripts **fail loudly rather than falling back to a path inside your repo** — that fallback is exactly what the vault-canonical storage law exists to prevent. Only `planning-projects` has a documented in-repo fallback (`docs/plans/`), and it warns when it uses one.

## Worked example

```text
/plugin install planning@coder-plugins

"I want to add offline sync"
```

`brainstorming` fires and works through purpose, constraints, and alternatives one question at a time. Because the design has a structural surface, it hands off to `architecting-projects`, which fans out `architecture-researcher` agents over 2–4 candidates and presents a comparison matrix for your explicit approval, then writes the `ARCH-NN` doc.

```text
"plan it"
```

`planning-projects` triages a format first, runs its research phase (online sources, backlog scan, workflow specs, the architecture doc, and the **decisions scan**), and writes a staged plan whose structure-creating tasks cite `ARCH-NN` and whose constrained tasks cite `Honors DEC-NNN`.

```text
"execute the plan"
```

`executing-plans` re-checks the decisions for staleness at Preflight, drives Red-Green loops with a commit per green task, fans independent tasks out through `dispatching-parallel-agents`, runs tiered gates with two-tier review, and at close-out bumps versions across every mirror, reconciles the backlog, and records any supersede the plan declared.

## Why a separate plugin

All fifteen skills reference each other by name (handoffs from brainstorming → architecting-projects → planning-projects → executing-plans → dispatching-parallel-agents; executing-plans → applying-design-handoff for redesign tasks; planning-projects/executing-plans ↔ backlog and workflow-spec; compass → the plans, backlogs and maturity files portfolio maintains; portfolio → backlog + project-maturity + dispatching-parallel-agents; executing-plans/dispatching-parallel-agents → capability-router's disk-resolution flow; and honest-gates binding every gate the pipeline reports). Splitting them across plugins would break the handoffs. They have no transitive runtime dependencies and can be installed alongside any other plugin without conflict.

## License

MIT
