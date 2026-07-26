# Using coder-plugins end to end

Each plugin's own README documents its components (per
[`plugin-readme-contract.md`](./plugin-readme-contract.md)). This guide covers what no
single README can: the flows that **span** plugins.

Nothing here is required reading to use one plugin. It matters when you want the
plugins to compose — which is what they were built for.

---

## 1. Idea → shipped feature

The core loop. Five skills in the `planning` plugin, each handing to the next.

```text
/plugin install planning@coder-plugins

"I want to add offline sync"
```

`brainstorming` fires and works one question at a time — purpose, constraints,
alternatives, risks. It reads the **decisions register** while doing so, so a design that
would violate a recorded constraint gets caught before it becomes a plan.

Because this design has a structural surface, brainstorming hands to
`architecting-projects`, which researches 2–4 candidates in parallel (one
`architecture-researcher` agent each, uncited claims discarded), shows you a comparison
matrix, and writes the approved one as a doc with stable `ARCH-NN` IDs.

```text
"plan it"
```

`planning-projects` **triages a format first** — Direct (no plan file at all), Light,
Standard, or Master — so a two-task chore doesn't pay for a twelve-task project's
ceremony. Then it researches, and writes a staged plan where structure-creating tasks cite
`ARCH-NN` and constrained tasks cite `Honors DEC-NNN`.

```text
"execute the plan"
```

`executing-plans` drives it: Red-Green loop per task, a commit per green task, tiered test
gates, two-tier code review, and independent tasks fanned out via
`dispatching-parallel-agents` to stack-matched subagents. At close-out it bumps versions
across every mirror, reconciles the backlog, and records any decision the work created.

**Cross-cutting the whole flow:** `honest-gates` defines what a gate may claim, and
`no-fafo-debugging` takes over the moment something breaks — evidence before theories.

---

## 2. Knowing what to work on

`planning` also runs the layer above individual projects, across everything in
`~/.claude/projects-registry.yaml`.

```text
/planning:compass now       # what's in flight — plan stages, current task
/planning:compass next      # what to pick up, ranked, with cited evidence
/planning:compass review    # what's going stale, what's parked, where the gaps are
```

`compass` is **report-only** — it recommends and never launches work or writes artifacts.
`portfolio` is what maintains the artifacts it reads:

```text
/planning:portfolio scan       # registry vs reality, surface drift
/planning:portfolio unify      # mine plans for backlog candidates, per project
/planning:portfolio maturity   # ship-readiness audit, per project
/planning:portfolio migrate    # move docs/ artifacts into the vault
/planning:portfolio integrate  # merge per-project integration edges into the graph
/planning:portfolio rebuild    # regenerate every global-*.md roll-up
```

Per project, three registers hold the durable state: `backlog` (deferred work),
`project-maturity` (ship-readiness across six axes), and `decisions` (why the architecture
is the way it is).

> **Everything portfolio is vault-canonical.** Artifacts live under
> `<vault_dir>/Portfolio/<area>/<name>/`, not in your repo. Set `vault_dir` in
> `~/.claude/portfolio-config.yaml`; if it's unset the scripts **fail loudly** rather than
> writing inside your repo.

---

## 3. Why the architecture is the way it is

The `decisions` register is the one piece that spans *time* rather than plugins — it
answers questions long after the plan that decided them was archived.

```text
"why did we choose Orbot over iptables owner-match?"
"what binds all the Rust projects?"
```

Two linked halves: per-project `DEC-NNN` entries, and per-domain `GDEC-<DOM>-NNN` entries
that bind **every** project on a platform. `promote` lifts one into the other, writing both
link directions at once.

**This is what a new project gets for free.** The domain registers are keyed by domain, not
project, so a brand-new repo with no registry entry still inherits every constraint its
platform has accumulated — before it has written a line of code. Ask directly:

```bash
python3 <planning-plugin>/skills/decisions/scripts/decisions-relevant.py --list-domains
```

From there the constraint travels: into the plan's `## Decisions in force` section, onto
task lines as `Honors` / `Supersedes`, into every dispatched sub-agent's prompt, and into a
stage gate that **fails** on an uncited contradiction.

---

## 4. Shipping it

```text
/git-github:code-review          # authoritative local review of your diff
/git-github:gate-audit           # did those gates actually run, or just claim to?
/git-github:create-commit        # drafts in your repo's style; never amends, never add -A
/git-github:create-pr            # drafts from recent merged PRs; defaults to draft
/git-github:release-tag v1.4.0   # confirms before tagging, and again before pushing
```

Then registration and announcement:

```text
/infra-build:build-readiness-check   # ready for .deb / .pkg / OCI image?
/infra-build:utils-register          # register with the pipeline (edits ~/dev/infra/, not your repo)
/promote-release                     # drafts posts per eligible channel — never posts
```

---

## 5. Running a business case on a project

`business` is the sibling pipeline to `planning`, storing its artifacts beside
`MATURITY.md` so `compass` and `portfolio` can read business state.

```text
/business:assess           # monetize / free-for-reputation / internal-only / park
/business:market-research  # tiered, cited — writes nothing if WebSearch is unavailable
/business:revenue-model    # model, pricing, channels, dated numeric targets
/business:business-plan    # compose everything into a twelve-section plan
/business:launch           # GTM checklist, guarded by ship-readiness
/business:track            # actuals vs targets
/business:biz-portfolio    # sweep and rebuild the global roll-up
```

Several repos that are really one product (a server plus its admin client) group into a
single business case via a manifest under `Portfolio/business-groups/<slug>/`.

---

## 6. You don't have to enable everything

Enabled plugins cost context: every skill/agent/command description is injected at session
start whether or not you use it. Two mechanisms keep that bounded.

**`loadout`** — a per-project sticky baseline plus task overlays:

```text
/loadout set rust
/loadout add security-audit
```

Applies to your **next** session; Claude Code reads `enabledPlugins` once at startup.

**`capability-index.json`** — lets one skill or agent be resolved **from disk without
enabling its plugin**. `planning:capability-router` wraps this for ad-hoc use, and plan
execution uses the same lookup on its dispatch path, so a Rust task gets `rust-expert` even
when `rust-dev` isn't enabled:

```text
"load the Rust expert"
```

Components needing hooks or MCP are flagged `requires_enablement` and stop for explicit
enablement rather than degrading silently.

Rule of thumb: **`loadout`** for a durable per-project set, **`capability-router`** for a
one-off need.

---

## Where things are written

| Artifact | Location |
|---|---|
| Plans, architecture docs, backlog, decisions, maturity | `<vault_dir>/Portfolio/<area>/<name>/` |
| Domain decision registers | `<vault_dir>/Portfolio/decisions/<domain>.md` |
| Global roll-ups | `<vault_dir>/Portfolio/global-*.md` |
| Behavior contracts | `<repo>/docs/workflows/` |
| Live plan progress | `<repo>/.claude/plan-progress.json` (ephemeral, gitignored) |
| Per-project loadout | `<repo>/.claude/loadout.json` (committed) |
| Review and security reports | **local only — gitignored, never committed** |
