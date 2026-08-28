# `plan-status` — classification order and evidence grades

The procedure behind `../SKILL.md` § `plan-status` — reconcile every vault plan's recorded
status against its real progress. The trunk states what binds every invocation (report-first,
the per-plan confirm, and that abandonment is never inferred); this file is the classification
and evidence detail.

Inputs: optional `--check`, `--json`, `--verbose`, `--fix`, `--restore <run-id>`. Runs
`../scripts/plan-status-audit.py`. **Report-first: the default invocation writes nothing.**

Why it exists: a plan's recorded status and its actual task completion are read by two
different code paths and never reconciled. `unify` emits an in-flight plan's open tasks as
backlog candidates and `compass next` ranks projects by what is in flight, so a plan that is
finished but never close-out-marked is a standing source of phantom work in both. Measured
when this shipped: **15 plans at 100% of tasks done carrying no `**Completed:**` line.**

1. Enumerate every `plans/*.md` under `<vault>/Portfolio/*/*/`. **The vault is the corpus, not
   the registry** — 39 files across 7 projects have no registry entry, and skipping them while
   reporting a portfolio-wide audit would claim coverage the run does not have. The registry
   resolves each project's **repo path** for evidence, nothing more.
2. Classify each plan: `abandoned` → `blocked` → `completed` → `unclassifiable` →
   `no-status` → `never-started` → `started-unfinished`, in that order. Human-authored
   terminal markers win first, with **one** exception, and it is the only one: a `[~]`
   stage-gate check classifies the plan `blocked` even when it carries `**Completed:**`
   (BL-077). The close-out line is the author's claim about the work; the gate box is the
   record of what could not be proven, and proof outranks claim. Nothing after `completed`
   overrules an author.
3. **`unclassifiable`** is the load-bearing class: a plan carrying any bracketed `Status:`
   marker outside the contract's `[ xX~]` (`[!]`, `[~ BLOCKED]`, `[~ N/A]` — see
   `pu.ANY_STATUS_RE`) has a task invisible to the parser, so it reads **more finished than it
   is**. Those plans are **never offered as completion candidates, under any flag.**
4. Gather **graded** evidence, strongest first. Grades, in the order they are tried:
   - **`register+commit`** — a master's `## Sub-plans` register marks this exact plan `[x]`
     *and* names a commit that resolves in the repo. A human, in another document, naming the
     plan and the work. The strongest thing available, and it lives in the **vault**, not git.
   - **`register`** — the register marks it done but names no commit, or the one it names does
     not resolve. Still identifies *the plan*.
   - **`names-the-plan`** — a commit message contains the plan's filename, matched **anchored**
     so `<plan>.md.orig` does not count. Currently unattested anywhere in the corpus.
   - **`correlative`** — stage-completion commits dated on or after the plan. Identifies a repo
     and a period, **never a plan**: the same commits get offered to every plan that repo ran.
   - **`none`** — searched, found nothing. Distinct from "no repo to search".

   Git is never run against the vault, which is not under version control; a repo path pointing
   inside it is refused outright rather than allowed to fail and read as "no evidence".
   Each candidate also shows its **stage-gate state**, because *all tasks `[x]`* is not the
   same as *finished* — a plan can carry every task done and still have an unticked final gate.
5. `--fix` presents one candidate at a time with its evidence and requires a per-plan `y`. It
   takes a timestamped backup under `<portfolio_home>/plans/.audit-backups/<run-id>/` before
   writing, and the write is atomic. `--restore <run-id>` reverts a run wholesale — the vault
   has no version control behind it, so the backup is the only undo that exists.
6. The recorded line states the evidence's **grade**: a correlative match is written as
   `user-confirmed; no commit names this plan — correlated with stage commits <hashes>`, never
   as a bare `evidence: <hashes>`. The line outlives the run by years and a future reader has
   only its words to tell the two apart.

**It never infers `**Abandoned:**`.** A marker nobody adopts degrades to the status quo; a
heuristic false-positive is a *new* failure mode, because a plan wrongly marked abandoned
disappears from the one view still listing its open work. `portfolio-unify.py` owns an advisory
banner-prose detector and it is deliberately not consulted here.

`--check` runs two separately-labelled sets: **invariants** (true of any corpus — the classes
partition the enumeration, no plan lands in two, candidates and unclassifiable are disjoint),
which gate the exit status; and **corpus observations** (true of the live vault when measured —
`abandoned` is 0, `unclassifiable` is non-empty), which are reported and **never fatal**, so a
human legitimately adopting a marker cannot turn a green audit red.
