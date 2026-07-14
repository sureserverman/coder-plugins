---
name: game-dev
description: 'Use when authoring or reviewing game code or design — Godot/Unity/Unreal, game feel, mechanics, camera, UX, architecture, accessibility. Triggers: "*.gd"/"*.tscn"/"*.uproject" edits, "the jump feels off", "camera fights me", "review my game design", "is my game accessible", engine best-practices.'
---

# game-dev

Lean **knowledge router** for game development. Maps the situation to the matching
`../../references/` file (the deep rules, examples, and citations live there — one source
of truth, shared with the `game-design-expert` agent) and hands verb-shaped or output-heavy
work off to that agent.

## Reference map (progressive disclosure)

Read the matching file when the decision gets deep:

| When you're… | Read first |
|---|---|
| Authoring/reviewing Godot 4 (GDScript, `.tscn`, `.tres`, autoloads, signals) | `../../references/engine-godot.md` |
| Authoring/reviewing Unity (C# MonoBehaviour, ScriptableObject, prefabs) | `../../references/engine-unity.md` |
| Authoring/reviewing Unreal 5 (C++ gameplay, Blueprints, GameMode) | `../../references/engine-unreal.md` |
| Designing/balancing mechanics, the core/compulsion loop, FTUE pacing | `../../references/game-mechanics-design.md` |
| Tuning game feel / juice — input lag, jump feel, hit feedback, "feels off" | `../../references/game-feel-and-juice.md` |
| Camera or navigation — "camera fights me", lookahead, 2D/3D rigs, fast travel | `../../references/game-navigation-camera.md` |
| UX — menus, HUD, FTUE, tutorialization, button prompts, settings | `../../references/game-ux-onboarding.md` |
| Game code architecture — entity systems, game loop, state machines, ECS | `../../references/game-architecture-patterns.md` |
| Accessibility — GAG audit, colorblind/remap/subtitles, ship-gate | `../../references/game-accessibility-audit.md` |

## When to hand off to game-design-expert

Apply the reference rules inline for focused, single-file changes. **Hand off to the
`game-design-expert` subagent** — delegate-by-signal: independent + output-heavy + not
latency-critical — for a full design/review pass (its Mechanic Design, Feel Tune, Camera
Audit, UX Review, Accessibility Audit, or Architecture Review protocols), a multi-file
review, a from-scratch mechanic brief, or a ship-gate accessibility audit. The agent reads
the same `references/` in its own context window. The `/game-mechanic` and `/game-review`
commands are the guided entry points to it.
