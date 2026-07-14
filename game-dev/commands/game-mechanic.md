---
description: Run a guided design session for a new game mechanic. Walks through verb, core loop, depth, feel target, FTUE plan, accessibility, and engineering scope, producing an implementable brief.
argument-hint: "<mechanic name or one-line description>"
---

# /game-mechanic

Guided design session for a new game mechanic. Delegates to the **game-design-expert** subagent running **Protocol 2 (Mechanic Design)**.

## Input handling

`$ARGUMENTS` is the mechanic name or a one-line description.

- Empty → ask the user what mechanic they're designing.
- Single word ("dash", "parry", "build") → ask for one sentence of context before dispatching.
- One-line description → dispatch directly.

## Dispatch

Call the game-design-expert subagent with:

- **Skip Protocol 1 (Stack Detection)** unless the user is also asking for engine-specific implementation guidance.
- **Run Protocol 2 (Mechanic Design).**
- **Cross-handoffs to other protocols as needed:**
  - "How should it feel?" → Protocol 3 (Feel Tune) starting values.
  - "How does the player learn it?" → Protocol 5 (UX Review) FTUE rules.
  - "Can everyone play it?" → Protocol 6 (Accessibility Audit) on the specific mechanic.
  - "How do I build it?" → Protocol 7 (Architecture) + the engine-specific reference.

## Output

A **Mechanic Brief** in the agent's standard schema:

- Verb (one sentence).
- Core loop (30s–5m diagram).
- Decision opened (Schell's depth test).
- Emergent behaviors (Sylvester's elegance test).
- Feel target (one paragraph; concrete numbers if known).
- FTUE plan (how the level teaches this without text).
- Accessibility (motor / cognitive / vision / hearing notes).
- Engineering scope (rough size, primary patterns, engine-specific notes).
- Open questions for the team.

## Don'ts

- Don't generate code unless the user asks. The brief is design, not implementation.
- Don't fill in numbers as if they're authoritative. Game feel only exists in playtest.
- Don't propose multiple mechanics in one session. One per `/game-mechanic` invocation.
