# Using coder-plugins end to end

Each plugin's own README documents its components (per
[`plugin-readme-contract.md`](./plugin-readme-contract.md)). This guide covers what no
single README can: how the pieces **compose** into an end-to-end flow.

Most flows here cross plugin boundaries — that is the interesting case, and the one a
README structurally cannot describe. Two do not, and deliberately: **flow 6** (knowing what
to work on) and **flow 7** (the decisions register) are *layers* rather than pipelines, and
both live entirely in `planning`. They are here because they are cross-cutting in scope —
they operate over every project in the portfolio — not because they are cross-plugin. A
flow being single-plugin is not a gap to be padded out with components it does not use.

Nothing here is required reading to use one plugin. It matters when you want the
plugins to compose — which is what they were built for.

---

## 1. Idea → shipped feature

The core loop. Five skills in the `planning` plugin carry an idea to a green branch, then
`git-github` takes it the rest of the way — review, commit, PR.

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
gates, and independent tasks fanned out via `dispatching-parallel-agents` to stack-matched
subagents. Its two review tiers are not its own — both dispatch `code-reviewer` from the
`git-github` plugin, and how much of either runs comes from the plan's declared
**review scope**: at the default *standard* tier that is one deep review per stage gate
and no per-task pass, with per-task review reserved for the *high* tier or a task the plan
annotated Review: required. At close-out it bumps versions
across every mirror, reconciles the backlog, and records any decision the work created.

While it runs, execution state is mirrored to `<repo>/.claude/plan-progress.json` and can be
rendered as a live status-line bar
(`⚙ plan ▐██████░░░░▌ 3/6 (50%) · S2/3 ▶ T2.2 …`), which disappears at close-out.

```text
/planning:statusline install     # one-time and global; also takes status, remove
```

That one entry has to live in your own `~/.claude/settings.json` because `statusLine` is
not a plugin contribution point — so the plugin ships the scripts and this command
generates the pointer, rather than asking you to hand-author a wrapper. An existing
status line invoked as a plain `bash <script>` is preserved and runs first; anything else
is left alone unless you pass `--force`.

```text
"review this, then open a PR"
```

The plan is green; shipping it is `git-github`'s half of the loop. `code-review` audits the
branch diff as one piece — the per-task reviews only ever saw a task at a time — and
`gate-audit` sweeps it for faked verification: stubbed gates, tests that never ran,
hidden exclusions. `create-commit` and `create-pr`
each dispatch a Haiku subagent to draft and create the thing; both require that you asked
for it explicitly, and neither ever fires on its own. When the branch lands, `release-tag`
cuts the tag and drafts notes from the changelog — it is the one of the three that gates on
an explicit "yes", once before tagging and again before pushing.

**Cross-cutting the whole flow:** `honest-gates` defines what a gate may claim, and
`no-fafo-debugging` takes over the moment something breaks — evidence before theories.

---

## 2. Build an Android feature

Flow 1 with a platform under it. The `planning` loop stays in charge; `android-dev` and
`testing` attach at the points where the platform actually matters.

```text
/loadout set android

"add a settings screen with a dark-mode toggle"
```

`android-gradle-build` handles module and dependency wiring. The screen itself is authored
against `android-ui-layout-patterns`, which supplies the Compose spacing and Material 3
decision rules. For a full redesign rather than one screen, `android-ui-design-figma` runs
the longer app-analysis → spec → apply workflow.

The seam worth knowing: **`executing-plans` invokes `android-stage-verify` at every Android
stage gate automatically** — you don't ask for it. It builds the debug APK and, when a
device is attached, installs, smoke-launches, and runs `connectedDebugAndroidTest`.

```text
"verify this stage on device"
```

> **With no device attached it degrades to a build-only gate and reports the skip.** It does
> not claim a pass it didn't earn — which is `honest-gates` applied to hardware. Check
> `adb devices` before you trust a green Android gate.

Test work hands off twice: `kotlin-compose-testing-patterns` for the patterns (Compose UI
tests, Espresso, MockWebServer), and the **`testing-expert`** agent when a test is flaky,
the failure is unexplained, or coverage needs auditing rather than writing.

Screenshots for the store listing run the emulator stack — three emulators plus an
in-container MCP server, brought up and torn down per task:

```text
/android-dev:android-screenshots
```

> Set `APK_DIR` and `SCREENSHOT_DIR` to absolute paths first. The stack's defaults are
> placeholders relative to the bundled plugin directory, so `up.sh` exits 4 with a guiding
> message rather than mounting an empty directory (see the `android-dev` README).

---

## 3. Ship a browser extension

Two plugins and a register, because an extension is judged by a reviewer who is not you.

```text
/loadout set web-ext

"build a Firefox extension that rewrites tracking URLs"
```

The `browser-extensions` skill covers manifest v3, the Firefox/Chrome split, and
`browser_specific_settings`. Popup and options pages are ordinary web UI: there is no
dedicated agent for them, so hold the accessibility baseline yourself — keyboard
reachability and contrast are what AMO reviewers actually cite.

Then the preflight, before you upload rather than after rejection:

```text
/browser-extensions:amo-compliance-check
```

```text
/planning:project-maturity
```

`project-maturity` gives the ship verdict across six axes. Two of them auto-detect an
extension without you claiming anything: **Packaging** reads `chrome/manifest.json` /
`mozilla/manifest.json` directly, and **UI/UX** finds an `icons/` directory beside the
manifest. The accessibility half of UI/UX is a **manual claim** — for web and extensions, a
WCAG 2.1 AA audit — as is most of what the axes ask for. **i18n** wants the locale catalogs,
which is the next flow.

---

## 4. Take a project multilingual

```text
/i18n:i18n-audit
```

Detects the framework in use, finds hardcoded strings, and diffs catalogs across locales for
missing or stale keys. It reports; it doesn't rewrite.

```text
/i18n:i18n-translate
```

Fills the gaps, dispatching the **`translator`** agent per batch — placeholders, ICU
MessageFormat, CLDR plurals and HTML tags preserved. `i18n-formats` is the reference for
whichever catalog format you're in.

The seam back to `planning`: `project-maturity` carries an **i18n axis**, so translation
coverage becomes part of the ship-readiness verdict instead of a thing someone remembers to
check. Extension locales feed flow 3's AMO preflight the same way.

---

## 5. Fanning out to stack-matched experts

This is the mechanism the other flows lean on. When `executing-plans` reaches independent
tasks, `dispatching-parallel-agents` runs one agent per task — and picks each agent from
[`stack-routing.md`](../planning/skills/dispatching-parallel-agents/references/stack-routing.md)
rather than defaulting everything to a generalist:

| Task looks like | Routes to | Shipped by |
|---|---|---|
| Rust | `rust-expert` | `rust-dev` |
| Reproduce a Claude Design handoff pack | `design-handoff-reproducer` | `planning` |
| Game mechanics, feel, camera | `game-design-expert` | `game-dev` |
| Test triage, flakiness, coverage | `testing-expert` | `testing` |
| Catalog translation batches | `translator` | `i18n` |

The same table routes *downward* too, for cost rather than capability. **`stingy-agents`**
ships three delegation targets, each pinned to the smallest model that can do its job —
`readonly-scanner` (Haiku) for bulk grep and enumeration, `code-generator` and
`skill-rewriter` (Sonnet) for scaffolding from a spec and for mechanical markdown edits.
`stack-routing.md` carries a dedicated row for each, so an I/O-bound or boilerplate phase is
dispatched away from a frontier model automatically. Audit and review skills in `git-github`,
`android-dev` and `infra-build` also name them directly.

Game work has its own front door, since mechanics are a design problem before a coding one:

```text
/game-dev:game-mechanic     # guided design session → implementable brief
/game-dev:game-review       # scoped diff review: feel, camera, UX, accessibility
```

> Routing does **not** require the target plugin to be enabled. Plan execution resolves the
> component from `capability-index.json` on disk — the same mechanism as flow 10 — so a Rust
> task gets `rust-expert` even when only `planning` is on. Components needing hooks or
> MCP are flagged `requires_enablement` and stop for explicit enablement.

---

## 6. Knowing what to work on

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

## 7. Why the architecture is the way it is

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

## 8. Shipping it

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

`/promote-release` is `release-promo`'s front door: it decides which channels a release is
even eligible for, then dispatches the `post-drafter` agent per channel against that
channel's house style — `hackernews-show-hn`, `lobsters-post`, `reddit-promo`,
`fediverse-post`, `twim-submission`. It **drafts and never posts**, which is the same
report-only posture `compass` takes toward work.

---

## 9. Running a business case on a project

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

## 10. You don't have to enable everything

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
