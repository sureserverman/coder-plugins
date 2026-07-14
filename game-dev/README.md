# game-dev

Game development plugin for Claude Code. Part of the [`coder-plugins`](..) marketplace.

## What it does

Opinionated, source-cited game-development expertise covering the areas that decide whether a game *feels good*: **mechanics**, **game feel**, **camera/navigation**, **UX/FTUE**, **architecture**, and **accessibility**, across Godot 4 / Unity 6 / Unreal 5. A thin `game-dev` router skill fires on game work and routes to shared `references/`; the `game-design-expert` agent does full design/review/audit passes over the same references — one source of truth.

Every rule cites where it came from. The references don't pretend; they cite Nystrom (*Game Programming Patterns*), Swink (*Game Feel*), Schell (*Art of Game Design*), Sylvester (*Designing Games*), Hodent (*The Gamer's Brain*), Nesky (*50 Camera Mistakes*, GDC 2014), the official Godot / Unity / Unreal docs, and the Game Accessibility Guidelines.

## Installation

```bash
/plugin marketplace add sureserverman/coder-plugins
/plugin install game-dev@coder-plugins
```

## Components

Four components — one thin router skill, one full agent, two commands — over one shared
`references/` set.

### Skill

- **`game-dev`** — a lean **knowledge router**. Fires on game work (`*.gd`/`*.tscn`/`*.uproject`
  edits, "the jump feels off", "camera fights me", engine best-practices, "is my game accessible")
  and routes each situation to the matching `references/` file (Godot/Unity/Unreal, game feel,
  mechanics, camera/navigation, UX/FTUE, architecture, accessibility — nine files, one level deep
  at `references/`). Hands verb-shaped or output-heavy work to `game-design-expert`.

### Agent

- **`game-design-expert`** — sonnet-pinned, authoring-capable. Six protocols: Stack Detection, Mechanic Design, Feel Tune, Camera Audit, UX Review, Accessibility Audit. Cites sources by name.

### Commands

- **`/game-review [scope]`** — scoped diff (uncommitted / file / commit / PR / branch) review covering mechanics, UX, navigation, accessibility, architecture.
- **`/game-mechanic <name>`** — guided design session for a new mechanic; outputs an implementable brief.

### Migration note

The eight knowledge skills (`game-mechanics-design`, `game-feel-and-juice`,
`game-navigation-camera`, `game-ux-onboarding`, `game-architecture-patterns`, `engine-godot`,
`engine-unity`, `engine-unreal`) and the `game-accessibility-audit` skill were **folded into
shared `references/` + the `game-design-expert` agent**: each skill's body moved to
`game-dev/references/<slug>.md` (one source of truth for the router and the agent), the `game-dev`
router skill carries their passive triggers, and accessibility became the agent's Protocol 6
(accessibility-audit) mode. When `game-dev` isn't enabled, the agent is still reachable from disk
via `capability-index.json` (the marketplace's capability-router) — its `.md` body is injected
into a generic subagent with its `model` pin.

## Opinionated defaults

- Camera frames the avatar, never itself (Nesky).
- No locks/loads at the wrong cadence: Unity Update for input/visuals, FixedUpdate for physics, LateUpdate for camera; no `new` in per-frame methods.
- Godot autoload reserved for true global singletons; signals over polling.
- Unreal: GameMode is server-only — never read from clients; PlayerState for replicated per-player data.
- Game Accessibility Guidelines **Basic tier is a ship gate** for any project intended for release.
- Coyote time 6–8 frames, jump buffer 6 frames, input buffer 3–6 frames as *starting* points (always tune via playtest).
- ScriptableObjects for shared data in Unity; no LINQ / string concat in `Update`.
- Object pool for any high-churn entity (bullets, particles, FX); initialize on reuse, not on construction.

## License

MIT — see [LICENSE](./LICENSE).
