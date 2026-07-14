---
name: capability-router
description: Use when a task needs domain expertise whose plugin may not be enabled (Rust, Android UI, game design, i18n, testing, packaging). Finds it in capability-index.json and loads it from disk. Triggers on "load the Rust expert", "which plugin covers X", "write idiomatic Rust", "review my game design".
---

# capability-router

Reach a marketplace capability — a skill or a subagent — **even when its plugin
isn't enabled in this session**. Enablement only controls what Claude Code injects
and registers at session start; every component's files are on disk regardless. This
skill is the ad-hoc entry point to the disk-resolution flow that `executing-plans` and
`dispatching-parallel-agents` use during plan execution — use it outside a plan, when
you just need a domain capability that isn't loaded.

## When this fires vs. normal triggering

If the relevant plugin **is** enabled, you don't need this skill — the target skill
triggers on its own description, or the agent is a registered `subagent_type`. Use
`capability-router` only when the capability you want isn't loaded (a fresh project, a
narrow task profile, a disabled plugin) and you'd otherwise get generic behavior.

## How to route

1. **Load the index.** Read `capability-index.json` at the marketplace repo root. It
   lists every component: `plugin`, `kind` (skill/agent/command), `name`, repo-relative
   `path`, `description`, `model`, `disable_model_invocation`, `requires_enablement`.
   Resolve each `path` against the directory that contains the index file — that
   directory is the marketplace root, so the index is machine-independent (there is no
   absolute `root` field).

2. **Match the need** against component `description`/`name`. Prefer the most specific
   match; the `../dispatching-parallel-agents/references/stack-routing.md` routing table
   is the canonical stack→capability map if you want a curated pick over a raw search.

3. **Resolve it from disk**, following
   `../dispatching-parallel-agents/references/stack-routing.md`
   § *Resolving a capability whose plugin isn't enabled* exactly:
   - **skill** → Read its SKILL.md at `path` and follow it (its `allowed-tools` scoping
     won't apply on this path — note that if the skill relies on a restricted tool set);
   - **agent** → dispatch `general-purpose` with the agent's `.md` body injected as
     instructions and its frontmatter `model` passed as the subagent model;
   - **`requires_enablement: true`** → do not lazy-load; tell the user which plugin to
     enable and why (it depends on hooks/MCP that only activate on enablement).

## Keep it honest

This is context *hygiene and reach*, not a token saving — reading a SKILL.md or
injecting an agent body still costs tokens. And it's a fallback: when the plugin is
enabled, prefer normal registered invocation. Don't Read-and-follow a component the
index flags `requires_enablement`.
