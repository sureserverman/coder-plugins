---
name: brainstorming
description: Use before any non-trivial creative or implementation work — new features, components, services, migrations, or behavior changes. Turns a vague idea into a validated design by exploring purpose, constraints, alternatives, and risks one question at a time. Terminal handoff is to the planning-projects skill, which produces the staged plan. Triggers on "I want to build", "let's design", "new feature", "how should I approach", "brainstorm", "help me think through", "what should this look like".
---

# Brainstorming Ideas Into Designs

Turn an idea into a design the user has explicitly validated, section by section, before any planner or implementer touches the code. The output of this skill is a **design document** that the next skill (`planning-projects`) uses as input.

**Announce at start:** "Using the brainstorming skill to turn this idea into a validated design."

<HARD-GATE>
Do NOT invoke `planning-projects`, write production code, scaffold a project, or run an implementation skill until you have presented a design and the user has said yes. This applies to every project regardless of perceived simplicity. The design may be three sentences for a trivial task — but it must be presented and approved before handoff.
</HARD-GATE>

## Core principle

Design work is about surfacing the assumptions that separate "what the user said" from "what the user meant" — and the constraints that separate "what works in the head" from "what works in the codebase." Skipping this produces plans that solve the wrong problem, and a wrong plan executed perfectly is worse than no plan (see also `planning-projects`, Phase -1).

## Anti-pattern: "this is too simple"

"Simple" is where unexamined assumptions hide. A todo list has an authentication model. A config change has a rollback strategy. A single-function utility has a failure domain. Every project goes through brainstorming — the design can be compact, but it must be validated.

---

## Checklist

Create a task for each of these and work them in order. Do not skip ahead.

1. **Ground the idea in project context** — read relevant files, docs, recent commits, existing ADRs
2. **Clarify purpose and constraints** — one question at a time, using the question heuristics below
3. **Surface alternatives** — propose 2-3 approaches with tradeoffs; name your recommendation
4. **Pre-mortem the recommended approach** — what would cause this to fail or be regretted in 6 months?
5. **Present the design in sections** — architecture, components, data flow, error handling, testing, rollout; each section scaled to its complexity; confirm after each
6. **Write the design document** — save to `docs/plans/YYYY-MM-DD-<topic>-design.md`
7. **Hand off to planning-projects** — that skill produces the staged implementation plan from this design

---

## Phase 1 — Ground the idea

Before asking anything of the user, gather what the repo already tells you. The fewer questions you ask, the better — questions you can answer from evidence should not be asked.

- Read the root manifests and README to identify language, framework, conventions
- Scan `docs/`, `docs/plans/`, `docs/adrs/` for prior decisions on this topic
- Recent commit history (`git log -30 --oneline`) for active work threads
- Existing patterns in the codebase that a new feature should match (don't introduce a second HTTP client, a second test framework, a second auth flow)

If an Obsidian vault is linked via `vault-context`, `.claude/vault-context.md` already points to the relevant architecture and gotcha pages — consult it before asking the user.

## Phase 2 — Clarify, one question at a time

Ask only what you cannot infer. For each question:

- **Prefer multiple choice** when the answer space is finite
- **State an assumption and ask for confirmation** when you can infer an answer
- **One question per message.** A wall of questions gets a wall of shallow answers
- **Stop asking when you have enough to design** — not when you have everything you'd ever want

### What to clarify (5W1H framing)

- **Why** — what is the underlying problem? What happens if we do nothing?
- **Who** — who uses the end result (user, their team, end users, CI, an operator)?
- **What** — what is explicitly in scope and what is explicitly out?
- **When** — deadlines, release constraints, ordering with other work
- **Where** — what platform, environment, language, framework?
- **How (success)** — how will the user know it's done? What does "working" look like, concretely?

### Red flags in user answers

- "Just like X but …" — compatibility requirements hiding as scope
- "Eventually we'll also want …" — future work trying to smuggle into current scope
- "It should be flexible" — unknown requirements masquerading as an abstraction
- "Obviously" or "of course" — the user has an unstated assumption the design should make explicit

When you hear these, ask the follow-up that pulls the hidden requirement to the surface.

## Phase 3 — Surface alternatives

Never present a single "the design." Always propose 2-3 approaches with named tradeoffs. This protects against anchoring on the first idea and gives the user material to push back against.

Format:

```
Option A — <one-phrase name>
  How it works: <2-3 sentences>
  Tradeoff: <what you give up>
  Fits when: <condition>

Option B — ...
Option C — ...

Recommendation: <A/B/C> because <specific reason>.
```

Ruthless **YAGNI** — cut features that aren't in the "why" from Phase 2. Ruthless **KISS** — the simpler option wins unless a concrete need justifies the complexity.

Consider the classic forces (Christopher Alexander's pattern vocabulary applied to code):
- Clarity vs performance
- Flexibility vs simplicity
- Coupling vs reuse
- Explicit vs convention

Name which forces are in tension in this design — it makes the tradeoff visible.

## Phase 4 — Pre-mortem

Before presenting the design, imagine it's six months later and the design is regretted. What went wrong? Three sources to check (from Gary Klein's pre-mortem technique and Kahneman's planning-fallacy work):

- **Integration** — did this break something else in the system?
- **Operability** — is this on-call-hostile? Hard to observe? Hard to roll back?
- **Scope creep** — did we carry forward a feature that should have been cut?

Write down the top 2-3 failure modes and what the design does to prevent them. If a failure mode has no mitigation, that's a real risk — either add a mitigation, accept it explicitly, or revisit the choice of approach.

## Phase 5 — Present the design in sections

Walk the user through these sections. Scale each to the project's complexity — a few sentences for a trivial task, up to 200-300 words for nuanced areas. After each section, ask "does this match what you had in mind?" and be ready to revise.

1. **Problem statement** — the "why" from Phase 2, one paragraph
2. **Architecture** — the shape of the solution at the highest level (components, boundaries, data stores)
3. **Components** — each named component, its responsibility, its inputs/outputs
4. **Data flow** — how information moves through the system (sequence of calls for the main use case)
5. **Error handling** — what failures look like, how they propagate, what the user sees
6. **Testing** — which behaviors are tested at which pyramid layer (defer depth to `testing-expert`)
7. **Rollout** — feature flag? staged deploy? migration script? how to roll back?

Do not present sections 2-7 until section 1 is approved. Do not skip sections because "they don't apply" — if they don't apply, say so explicitly ("no rollout concerns: this is a pure dev-tool change"). Explicit-negative is better than silent-missing because it shows the reader you considered it.

## Phase 6 — Write the design document

Save to `docs/plans/YYYY-MM-DD-<topic>-design.md`. Structure:

```markdown
# Design: <Topic>
Date: <YYYY-MM-DD>

## Problem
<why, constraints, success criteria>

## Alternatives considered
- Option A: <name> — <why not>
- Option B: <name> — <why not>
- Option C (chosen): <name> — <why>

## Architecture
<diagram or prose>

## Components
<per-component responsibilities and boundaries>

## Data flow
<sequence>

## Error handling
<failure modes and propagation>

## Testing strategy
<layers>

## Rollout / rollback
<how to ship, how to undo>

## Risks (from pre-mortem)
- <failure mode> — mitigation: <what we do>
- <failure mode> — mitigation: <what we do>
```

Commit the design document before handoff so future sessions can find it.

## Phase 7 — Hand off to planning-projects

The **only** skill you invoke after brainstorming is `planning-projects`. Do not invoke `executing-plans`, `frontend-design`, or any implementation skill directly — those are downstream of the plan.

Say to the user:

> Design approved and saved to `docs/plans/<filename>-design.md`. Handing off to the `planning-projects` skill to produce the staged implementation plan with research, preflight, tasks, and stage gates.

Then invoke `planning-projects` with the design document as input.

---

## Key principles

- **One question at a time** — break complex topics into multiple messages
- **Multiple choice preferred** — easier to answer than open-ended
- **YAGNI and KISS** — cut unnecessary features, pick the simpler approach, let the need justify complexity
- **Explicit alternatives** — never a single design; always 2-3 with tradeoffs
- **Pre-mortem before approval** — name the failure modes before they happen
- **Validated by section, not in bulk** — present a section, get approval, move on
- **Explicit-negative** — "no rollout concerns" beats silent omission
- **Terminal state is `planning-projects`** — never jump straight to implementation

---

## Sources and rationale

Cited so the methodology is defensible:

- **One question at a time / multiple choice** — Socratic dialogue tradition; easier to reason about a constrained choice than generate an open-ended answer
- **YAGNI / KISS / DRY** — *The Pragmatic Programmer* (Hunt & Thomas); Kent Beck's *Extreme Programming Explained*
- **Explicit alternatives with tradeoffs** — ADR (Architecture Decision Record) practice; Michael Nygard, "Documenting Architecture Decisions"
- **Pre-mortem technique** — Gary Klein, *Performing a Project Premortem* (Harvard Business Review, 2007)
- **Planning fallacy** — Daniel Kahneman, *Thinking, Fast and Slow*, Ch. 23
- **Christopher Alexander pattern forces** — *A Pattern Language* (1977) via *Design Patterns* (GoF)
- **5W1H clarification** — journalism/business-analysis standard; see Kipling's "six honest serving men"
- **Section-by-section validation** — stage-gate process (Robert Cooper, *Winning at New Products*)

These are why the skill looks the way it does — the shape is not arbitrary.
