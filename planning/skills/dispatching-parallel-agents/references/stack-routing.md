# Stack routing — which subagent (and stack skill) gets a task

Shared by `dispatching-parallel-agents` (Phase 3 brief / Phase 4 dispatch) and
`executing-plans` (Step 3.2). It answers two questions for a ready task: **should
this go to a subagent at all**, and if so **which subagent type, and which stack
skill should that subagent load first**.

The point is *context hygiene*, not speed or token thrift. A subagent runs in its
own context window and returns only a condensed result, so the orchestrator's
window stays focused on plan state and stage gates instead of filling with file
dumps, build logs, and search noise. (Anthropic, "Create custom subagents" and
"Effective context engineering for AI agents".)

---

## Decision rule — delegate by signal, not by default

Hand a task to a subagent when **all three** hold:

1. **Independent** — it doesn't need the running session's accumulated context, and
   later steps won't need *its* working trace (only its result).
2. **Output-heavy** — it will generate verbose intermediate output the orchestrator
   would otherwise absorb and never reference again (builds, greps over many files,
   long test logs, large reads).
3. **Not latency-critical** — a fresh subagent pays startup + re-gather cost; that's
   worth it here because the task is substantial.

Keep it **inline in the main session** when any of these hold:

- **Coupled** — it depends on intent/state built up across earlier steps.
- **Iterative** — it needs frequent back-and-forth or refinement.
- **Quick / targeted** — a small edit where re-gathering context costs more than the
  work itself.

**Caveats (don't oversell delegation):**

- It is **not** a token saving. The subagent's intermediate tokens still burn against
  the budget; you trade a higher total count for a cleaner main window. Parallel
  subagents compound the burn.
- Subagents start fresh: no conversation history, no previously-read files, no
  already-invoked skills. Brief them completely (see the Phase 3 prompt template).
- Subagents can't talk to each other — only the orchestrator integrates their results.

`Parallel: YES` tasks are *already* delegated (that's what this skill does), and they
are the only tasks this table routes. **A `Parallel: NO` task runs inline** —
`executing-plans` Step 3.2 retired the rule that sent independent, output-heavy
sequential tasks here, because it was a discretionary third execution mode that no
reader of the plan could predict and that saved nothing (the subagent's tokens burn
either way). A task that should be dispatched is marked `Parallel: YES` in the plan,
where the roster and the gate's reconciliation can see it.

---

## Routing table

Match by what the task touches. Pick the most specific row that fits; fall through to
`general-purpose` when nothing does. `(if installed)` agents are not part of this
marketplace — if the agent type isn't available, note it and fall back to the generic
worker named in the row.

Agent names are written as Claude Code dispatches them: plugin-provided agents use
their `plugin:agent` form, built-ins (`general-purpose`, `Explore`) are bare, and
agents this marketplace does **not** ship are tagged `*(if installed)*` with a
built-in fallback.

| Task / stack signal | Subagent type | Stack skill the subagent loads first |
|---|---|---|
| Rust — `*.rs`, `Cargo.toml`, clippy/audit/idiom work | `rust-dev:rust-expert` | `rust-coding` (authoring; the agent's own review/idiomize/project-audit modes handle the rest) |
| Android build / Kotlin / Gradle | `general-purpose` | `android-gradle-build` |
| Android UI — Compose / Material 3 screens | `general-purpose` | `android-ui-layout-patterns`, `android-ui-design-figma` |
| Android tests — Compose/Espresso/MockWebServer | `testing:testing-expert` | `kotlin-compose-testing-patterns` |
| Reproduce a Claude Design handoff pack (redesign to spec, any stack) | `planning:design-handoff-reproducer` | `applying-design-handoff` |
| Research ONE architecture candidate — evidence, layout, libraries (any stack) | `planning:architecture-researcher` | `architecting-projects` (dispatching context only — the skill orchestrates, the agent researches) |
| Game mechanics / feel / camera / FTUE design | `game-dev:game-design-expert` | — |
| i18n catalog translation | `i18n:translator` | — |
| Test authoring / triage / coverage (any stack) | `testing:testing-expert` | — |
| Scaffolding / boilerplate from a concrete spec | `stingy-agents:code-generator` | — |
| Rewrite existing skill / agent / README markdown to a spec | `stingy-agents:skill-rewriter` | — |
| Bulk read-only scan / enumerate / grep many files | `stingy-agents:readonly-scanner` | — |
| Find-and-fix investigation, unknown location | `Explore` then `general-purpose` | — |
| Independent review of an integrated diff | `git-github:code-reviewer` | — |
| Nothing above fits | `general-purpose` | — |

When the table names a stack skill, put it in the dispatched agent's prompt
(`## Stack skill — invoke <skill> first`) so the delegate authors to the stack's
conventions instead of generic defaults.

**A row earns its place by adding something the fallback doesn't.** Android UI keeps a row
because it names stack skills; the other UI surfaces lost theirs when their agents were
retired, because a row reading `general-purpose` / `—` says exactly what the final
*Nothing above fits* row already says. Don't re-add informational rows that carry no
routing signal.

The **design-handoff redesign** row carries the redesign path on its own: the
`applying-design-handoff` skill orchestrates and dispatches
`planning:design-handoff-reproducer` for precise per-slice reproduction. Platform idiom
is the dispatched agent's job, informed by whatever stack skill its row names — there is
no separate per-surface UI agent to pair it with.

**Exception — Garmin Connect IQ / Monkey C** (`*.mc`, `monkey.jungle`, `manifest.xml`, watch
face / data field / widget / glance). A Claude Design handoff pack is a visual
HTML/component spec; it does **not** map onto Monkey C's resource-layout / `Dc` model. Do
not drive Connect IQ work through `applying-design-handoff` for precise reproduction —
treat a handoff pack there as loose visual inspiration, not a fidelity target.

---

## Not every routed agent can commit — the orchestrator finishes the task

`executing-plans` Step 3.3 requires every dispatched task to run its `Test:`, flip its
`Status:` to `[x]`, and land a commit ending in an executor trailer. **Four of the agents
this table routes to cannot do that**, because their `tools:` grant withholds what it takes.
Swept 2026-08-09 against every agent frontmatter in the marketplace
(grep -m1 '^tools:' over every `*/agents/*.md`):

| Routed agent | Can run a test? | Can commit? |
|---|---|---|
| `testing:testing-expert` | yes | **yes** — unrestricted shell |
| `stingy-agents:code-generator` | yes | **yes** — unrestricted shell |
| `planning:design-handoff-reproducer` | yes | **yes** — unrestricted shell |
| `rust-dev:rust-expert` | yes (cargo) | **no** — its git grant is read-only (status, diff, log, show, blame) |
| `game-dev:game-design-expert` | no | **no** — same read-only git grant |
| `i18n:translator` | partly (python3) | **no** — status and diff only |
| `stingy-agents:skill-rewriter` | **no** — no shell at all | **no** |
| `stingy-agents:readonly-scanner` | n/a | n/a — read-only by design; never route a *task* here |

Rows this table routes for *research or review* rather than for a task — `planning:architecture-researcher`, `git-github:code-reviewer`, `stingy-agents:readonly-scanner` — are deliberately out of scope for this table: they never carry a `Status:` or a commit obligation, so commit capability is not a property they need. Their absence is a scoping decision, not a gap in the sweep.

This is a capability boundary, not a bug in those agents: a markdown rewriter with no shell
is a deliberately cheap, deliberately safe tool. What was missing is the handoff.

**So when the routed agent cannot commit, the task is still dispatched** — the delegation
directive is unchanged, and inlining it instead would be the exact substitution
`../../executing-plans/references/dispatch-fidelity.md` exists to prevent. Split the work:

1. **The agent does the work** and returns its report, including what it could not verify.
   Brief it that way up front rather than letting it discover the gap: tell it to make the
   edits and report, and that the caller will run the test and commit.
2. **The orchestrator runs the task's `Test:` itself**, from the main session. This is the
   same trust-but-verify re-run Phase 6 already requires for a GREEN return, so it costs
   nothing new — it just becomes the only run rather than the second one.
3. **The orchestrator writes the commit**, and **the trailer still names the agent**:
   `Executor: dispatched — stingy-agents:skill-rewriter`. The trailer records **who did the
   work**, not who typed `git commit` — that is what makes it answer "5 marked YES, 0
   dispatched". Say in the commit body that the agent lacked commit capability and the
   orchestrator completed it, so the split is on the record.

**What you may not do** is call the task inline because the agent could not finish it, or
mark the trailer `inline` when an agent wrote the diff. Both convert a capability boundary
into a false record of who did the work.

## Resolving a capability whose plugin isn't enabled

The routing table names agents and skills by the identity Claude Code uses **when
their plugin is enabled** — a registered `plugin:agent` type, an invocable skill.
But a task can need a capability whose plugin isn't in the current session's
loadout (a fresh project, a narrow task profile). Enablement only controls what
Claude Code *injects and registers* at session start; the component files are on
disk regardless. So resolve the capability from disk instead of assuming it's
registered.

**Find the index.** `capability-index.json` lives at the marketplace repo root and
lists every component: `plugin`, `kind` (skill/agent/command), `name`, repo-relative
`path`, `description`, `model`, `disable_model_invocation`, `requires_enablement`.
There is no absolute `root` field — resolve each component's `path` **against the
directory that contains the index file** (that directory *is* the marketplace root
by construction, so the index is machine-independent). Match the task against
`description`/`name` to pick the component the routing table points at.

Then, by `kind`:

- **Skill** — put an explicit instruction in the delegate's prompt to **Read the SKILL.md**
  at that `path` and follow it (load its `references/` the same way the skill's own
  body directs). Caveat: a skill reached this way runs **without its
  frontmatter `allowed-tools` scoping** — that scoping only applies when Claude Code
  invokes the skill as a registered skill. If the skill relies on a restricted tool
  set, say so in the brief or prefer enabling the plugin.
- **Agent** — the agent isn't a registered subagent type, so you can't set
  `subagent_type` to it. Instead dispatch a `general-purpose` subagent and **inject
  the agent's `.md` body** (below its frontmatter) into the prompt as its operating
  instructions, and pass the agent's frontmatter **`model`** as the subagent's model
  so the pin is preserved (e.g. a `model: sonnet` agent still runs on Sonnet). This
  is the same content the agent type would carry; only the delivery differs.
- **`requires_enablement: true`** — the component depends on machinery that only
  activates on enablement (native hooks, a native or bundled MCP server), so it
  **cannot** be faithfully lazy-loaded. Do **not** Read-and-follow it. Stop and tell
  the user which plugin to enable and why (e.g. "this task needs android-dev's
  emulator MCP — enable the android-dev plugin for this session").

This disk-resolution path is a fallback layered **under** the delegate-by-signal
rule above, not a replacement for it: first decide *whether* the task should be
delegated at all, then — if the chosen capability's plugin happens to be disabled —
resolve it from the index. When the plugin **is** enabled, use the normal registered
`subagent_type` / skill invocation; the index path is only for the disabled case.

For ad-hoc (non-plan) work where you just need a domain capability that isn't
loaded, the `planning:capability-router` skill wraps this same lookup-and-resolve
flow.

---

## Keeping this table honest

Every agent and skill this table names must resolve to a built-in, a marketplace-shipped
agent/skill, or an agent tagged `*(if installed)*`. `../scripts/validate-stack-routing.py`
checks this and fails on drift (renamed/removed agent, typo, undeclared external dep).
It runs in CI (`.github/workflows/validate-stack-routing.yml`) on any edit to this
file, the script, or any plugin agent/skill; run it locally with:

```
python3 planning/skills/dispatching-parallel-agents/scripts/validate-stack-routing.py
```

---

## Sources

- Anthropic — "Create custom subagents" (code.claude.com/docs/en/sub-agents): isolated
  context windows; subagents for context preservation; choose main conversation for
  coupled/iterative/quick/latency-sensitive work.
- Anthropic — "Effective context engineering for AI agents"
  (anthropic.com/engineering/effective-context-engineering-for-ai-agents): subagents
  return condensed summaries; specialized agents with clean context windows.
