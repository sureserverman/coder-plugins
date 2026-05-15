# game-dev

Game development plugin for Claude Code. Part of the [`coder-plugins`](..) marketplace.

## What it does

Opinionated, source-cited skills covering the three areas that actually decide whether a game *feels good*: **mechanics**, **user experience**, and **navigation/camera**. Plus engine-agnostic architecture patterns, an accessibility ship-gate, and three engine-specific skills (Godot 4, Unity 6, Unreal 5).

Every rule cites where it came from. The skills do not pretend; they reference Nystrom (*Game Programming Patterns*), Swink (*Game Feel*), Schell (*Art of Game Design*), Sylvester (*Designing Games*), Hodent (*The Gamer's Brain*), Nesky (*50 Camera Mistakes*, GDC 2014), the official Godot / Unity / Unreal docs, and the Game Accessibility Guidelines.

## Installation

```bash
/plugin marketplace add sureserverman/coder-plugins
/plugin install game-dev@coder-plugins
```

## Components

### Skills (engine-agnostic)

- **`game-mechanics-design`** — core loop, compulsion loop, depth vs shallow complexity, progression pacing, FTUE / onboarding loop. Triggers on "design a core loop", "balance this mechanic", "what's the loop", or any greenfield mechanic-design request.
- **`game-feel-and-juice`** — Swink's six principles (Input, Response, Context, Polish, Metaphor, Rules). Concrete numbers: coyote time 6–8 frames @ 60fps, jump buffer 6 frames, input buffer 3–6 frames, screen shake amplitude curves, hitstop windows. Triggers on "improve game feel", "jump feels off", "tune the controller".
- **`game-navigation-camera`** — John Nesky distilled (50 Camera Mistakes). Third-person follow rules, predictive lookahead, collision pull-in, yaw/pitch limits, cinematic rig separation. 2D camera framing, level signposting, fast travel design. Triggers on "review my camera", "camera feels bad", "design navigation".
- **`game-ux-onboarding`** — Celia Hodent's seven usability heuristics + game-specific patterns: no modal tutorials, teach by doing, exaggerated FTUE rewards, consistent affordance language, HUD restraint. Triggers on "review my game UX", "design FTUE", "fix this menu".
- **`game-accessibility-audit`** — Game Accessibility Guidelines Basic-tier checklist as ship-gate. Motor / Cognitive / Vision / Hearing / General. Tiering guidance for Intermediate/Advanced.
- **`game-architecture-patterns`** — Nystrom patterns (Component, State, Game Loop, Object Pool, Observer, Event Queue, Service Locator). Decision rules + named pitfalls.

### Skills (engine-specific)

- **`engine-godot`** — Godot 4 best practices: scenes vs scripts, autoload restraint, signals over polling, version-control hygiene. Triggers on `*.gd`/`*.tscn`/`*.tres` edits.
- **`engine-unity`** — Unity 6 best practices: Update/FixedUpdate/LateUpdate split, GC discipline, ScriptableObject for shared data, Addressables. Triggers on `*.cs` under `Assets/`, `*.unity`, `ProjectSettings/`.
- **`engine-unreal`** — Unreal 5 gameplay framework: GameMode/GameState/PlayerController/Pawn/PlayerState boundaries, Blueprint vs C++ split, Subsystems. Triggers on `*.uasset`, `*.umap`, `*.uproject`, UE class headers.

### Agent

- **`game-design-expert`** — sonnet-pinned, authoring-capable. Six protocols: Stack Detection, Mechanic Design, Feel Tune, Camera Audit, UX Review, Accessibility Audit. Cites sources by name.

### Commands

- **`/game-review [scope]`** — scoped diff (uncommitted / file / commit / PR / branch) review covering mechanics, UX, navigation, accessibility, architecture.
- **`/game-mechanic <name>`** — guided design session for a new mechanic; outputs an implementable brief.

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
