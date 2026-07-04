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

`Parallel: YES` tasks are *already* delegated (that's what this skill does). The
decision rule matters most for `Parallel: NO` tasks in `executing-plans` Step 3.2:
a sequential task that is independent + output-heavy should still be delegated to a
stack-matched subagent rather than run inline — it just runs as a single dispatch,
not a fan-out.

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
| Rust — `*.rs`, `Cargo.toml`, clippy/audit/idiom work | `rust-dev:rust-expert` | `rust-coding` (authoring) or `rust-project` (audit) |
| Android build / Kotlin / Gradle | `general-purpose` | `android-gradle-build` |
| Android UI — Compose / Material 3 screens | `android-dev:ui-android` | `android-ui-layout-patterns`, `android-ui-design-figma` |
| Android tests — Compose/Espresso/MockWebServer | `testing:testing-expert` | `kotlin-compose-testing-patterns` |
| GNOME / GTK4 / libadwaita UI | `ui-design:ui-gnome` | — |
| Web UI / a11y / WCAG | `ui-design:ui-web` | — |
| macOS (SwiftUI/AppKit) UI | `ui-design:ui-macos` | — |
| Windows (WinUI/WPF) UI | `ui-design:ui-windows` | — |
| Garmin Connect IQ / Monkey C watch UI — `*.mc`, `monkey.jungle`, `manifest.xml`, watch face / data field / widget / glance | `ui-design:ui-garmin` | — |
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

The **design-handoff redesign** row composes with the platform rows: the
`applying-design-handoff` skill orchestrates the redesign and dispatches
`planning:design-handoff-reproducer` for precise per-slice reproduction, while the
matching `ui-*` row supplies platform best-practice judgment for the same stack. Use
both — the reproducer enforces spec fidelity, the `ui-*` agent enforces platform idiom.

**Exception — `ui-design:ui-garmin`.** A Claude Design handoff pack is a visual HTML/component
spec; it does **not** map onto Monkey C's resource-layout / `Dc` model. Route Garmin
Connect IQ work to `ui-design:ui-garmin` for general design/review/facelift, but do **not** drive
it through `applying-design-handoff` for precise reproduction — treat a handoff pack there
as loose visual inspiration, not a fidelity target.

---

## Keeping this table honest

Every agent and skill named above must resolve to a built-in, a marketplace-shipped
agent/skill, or an agent tagged `*(if installed)*`. `scripts/validate-stack-routing.py`
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
