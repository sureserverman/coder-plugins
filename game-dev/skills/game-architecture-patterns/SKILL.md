---
name: game-architecture-patterns
description: Use when designing or reviewing the architecture of a game's code — entity systems, game loop, state machines, event systems, object pools, observer/messaging. Triggers on "design my entity system", "ECS vs OOP", "game loop architecture", "fixed timestep", "variable timestep", "state machine for enemies", "FSM for player", "object pool for bullets", "observer pattern in my game", "event queue", "service locator", "singleton in games", "game architecture review", "decoupling game systems". Grounded in Robert Nystrom's Game Programming Patterns (gameprogrammingpatterns.com).
---

# game-architecture-patterns

Decision rules and named pitfalls for game-code architecture. Distilled from Robert Nystrom's *Game Programming Patterns* (free at gameprogrammingpatterns.com), the canonical text on this topic.

The patterns aren't a religion. Use them where they earn their complexity. Most small games don't need ECS, don't need an event queue, and don't need a service locator. Reach for the pattern *when the problem it solves shows up* — not before.

## The patterns at a glance

| Pattern | Solves | First reach for it when |
|---|---|---|
| Game Loop | Frame timing, simulation vs render rate | Always — every game has one |
| Update Method | Per-frame behavior on many entities | Always — natural shape |
| Component | "5000-line entity class" smell | Entities touch ≥ 3 domains (physics/render/AI/input) |
| State (FSM) | Tangled `if`/flag soup for behavior | Entity has ≥ 4 distinct behaviors with transitions |
| Observer | Decoupling broadcaster from listeners | Achievements, sound triggers, UI reactions |
| Event Queue | Async / decoupled-in-time messaging | Frame-rate-independent triggers, replay, networking |
| Object Pool | GC churn / fragmentation from short-lived objects | Bullets, particles, enemies, audio sources |
| Service Locator | "Where's the renderer?" globals problem | Cross-cutting infra (audio, log, save) |
| Flyweight | Many instances sharing identical data | Tile maps, particle types, item templates |
| Spatial Partition | O(n²) collision/proximity checks | > 50 dynamic entities querying each other |

---

## Game Loop (always)

The single most important architectural decision: **fixed-timestep simulation, variable-rate render with interpolation.**

```text
accumulator += deltaTime
while accumulator >= FIXED_DT:
    update(FIXED_DT)
    accumulator -= FIXED_DT
alpha = accumulator / FIXED_DT
render(alpha)  // interpolate between previous and current state by alpha
```

### Rules

1. **Physics runs at a fixed timestep** (typically 50–60 Hz). Variable-timestep physics is non-deterministic and breaks networking and replay.
2. **Rendering interpolates.** The renderer receives `alpha ∈ [0, 1]` to interpolate between the prior and current physics state. This gives smooth motion at any frame rate.
3. **Cap accumulator catch-up.** If rendering takes too long, the accumulator can spiral. Cap max iterations per frame (e.g., 5) and accept gameplay slowdown rather than freeze.
4. **Don't mix update modes per system.** All gameplay simulation in fixed update; all visual-only effects in variable update; all post-physics camera/UI in late update.

### Pitfalls

- **Variable-timestep simulation.** Floating-point drift, non-deterministic multiplayer, broken replay.
- **Spiral of death.** No cap on catch-up iterations → render falls behind further every frame.
- **Frame-rate-locked simulation.** "Game runs at double speed on a 144 Hz monitor" — classic bug.
- **Physics inside render.** Move character in `Update()` (variable) instead of `FixedUpdate()` — see [[engine-unity]].

## Update Method

Each entity exposes an `update(dt)` method, the game loop calls them all once per tick. The natural shape for any per-frame behavior.

### Rules

1. **One update method per entity, one purpose.** If `update()` does input, physics, AI, and rendering, you're not using Update Method — you're using a god method. Split into systems or components.
2. **No `update()` that calls `update()` of others directly.** Calls must go through the game loop or a system. Cross-entity ordering bugs are the #1 cause of "this worked yesterday."
3. **Cache references, don't lookup per-tick.** `GetComponent` / `find_node` per frame is a GC death spiral. See [[engine-unity]] / [[engine-godot]].

### Pitfalls

- **Ordering dependencies.** Entity A reads B's state, but B updated last frame. Solve with [[engine-unity]]-style execution order or two-pass update (compute → commit).
- **Per-tick allocations.** Anything `new`'d per update is GC pressure.

## Component pattern (when entities sprawl)

When a single entity class crosses ≥ 3 domains (input, physics, render, AI, audio), break it into components.

### Communication strategies

Nystrom names three; in increasing decoupling order:

1. **Shared parent state** — components read/write the parent's data. Simple, but creates implicit ordering deps.
2. **Direct refs** — components hold typed refs to siblings. Fast, but tightly coupled.
3. **Messaging via the parent** — components emit messages, parent dispatches. Decoupled, but a layer of indirection.

### Rules

1. **Default to shared state for small games.** It's enough. Components-as-namespaces, not as message buses.
2. **Move to messaging only when ordering bugs appear.** Premature messaging is a worse fate than implicit ordering.
3. **Components don't own other components' lifecycles.** Parent owns. Components borrow.
4. **No cyclical component dependencies.** `Physics` → `Render` → `AI` → `Physics` = nightmare. Linearize the chain.

### When *not* to use components

- The entity is genuinely a single concern (UI widget, particle, tile).
- The game is < 10k LOC and you can hold the entity in your head.
- You haven't measured the "5000-line god class" problem yet.

## State pattern (FSMs)

When an entity's behavior depends on internal state with discrete transitions, use a state machine.

### Levels of complexity

1. **Enum + switch** — 2–4 states. Don't overthink it.
2. **State classes (GoF State)** — 5+ states, or state-specific data exists.
3. **Hierarchical FSM** — common behavior shared across related states (Crouch, Walk, Run all "OnGround").
4. **Pushdown automaton** — temporary states (firing animation interrupts movement, then pops back).
5. **Concurrent FSMs** — orthogonal concerns (movement FSM + weapon FSM + animation FSM, run independently).

### Rules

1. **State enter/exit hooks.** Always have `on_enter(prev)` / `on_exit(next)` — resource initialization lives there, not in transition code.
2. **No multi-frame transitions in code.** A "Transitioning" state is a real state if it has duration. Model it.
3. **Mutually-exclusive booleans = enum.** `isWalking`, `isJumping`, `isFalling`, `isCrouching` → MovementState enum.
4. **More than ~8 states in a single FSM = consider hierarchical or concurrent.**

### Pitfalls

- **Implicit states encoded as booleans.** Three booleans = 8 implicit states, 5 of which are invalid. Make them explicit.
- **State leak.** Forgetting to clear state-specific data on exit → bug shows up two transitions later.
- **Untested transition.** Every state pair (A → B) is a transition. Test the common ones; document the impossible ones.

## Observer (decoupled notification)

When one event needs to fire effects in many unrelated systems — achievements, sound, UI flash, telemetry — emit it and let subscribers handle.

### Rules

1. **Observers are *fire and forget*.** No return value, no blocking. If you need a response, use a different pattern (command pattern, RPC).
2. **Synchronous by default for game events.** Async observers cause "the achievement popped two frames late" bugs.
3. **Always have an unsubscribe path.** Destroyed entities still in the subscriber list = use-after-free or worse, silent failure.
4. **Type the event.** A `string` event name is fast to write and slow to debug. A typed event class catches typos at compile time.

### Pitfalls

- **Forgotten subscriptions** keeping objects alive (memory leak).
- **Observer-during-observer.** Subscriber A triggers event X which has subscriber B... which triggers Y... order = chaos.

## Event Queue

When events need to be *delayed*, *batched*, or *replayable*, use a queue instead of direct observer calls.

### When to use

- Input replay / demo recording.
- Decoupling producer frame rate from consumer.
- Multiplayer / lockstep simulation.
- Audio engine (queue sounds, mix later).

### Rules

1. **Fixed-size ring buffer** to bound memory. Drop or block on overflow.
2. **Single consumer per event type** (multi-consumer = observer).
3. **No object references in events.** Events outlive frames; references can be stale. Use IDs.
4. **Timestamp every event** if order matters.

## Object Pool (the "bullet pool")

When entities spawn and despawn frequently, pre-allocate and reuse.

### Rules

1. **Pool size = peak concurrent demand + 20% headroom.** Measured, not guessed.
2. **Initialize on reuse, not on construction.** A pooled bullet retains last shot's state — re-init every field.
3. **Free list, not linear search.** Thread the free list through the pool elements themselves (the unused slot's storage holds the next-free index).
4. **Explicit "in use" flag.** Pool can answer "is this slot live?" without inference.
5. **Overflow policy.** Choose explicitly: refuse new (silent fail bad), forcibly recycle oldest (good for particles, bad for entities), grow pool (good for editor, bad for production).
6. **Reset all state on release.** Velocity, target, timer, flags, references. Stale state = nondeterministic bug.

### When *not* to pool

- Game has < 50 entity creates/sec.
- Engine has its own pool (Unity addressables, Godot scene instancing).
- Object size varies wildly (pool would waste memory).

## Service Locator

When cross-cutting infra (audio, save, log, telemetry) is needed everywhere, a service locator beats a singleton.

### Rules

1. **Service locator > singleton.** Locator can swap implementations (live, null, mock) at runtime.
2. **Provide a null service.** Tests should run against a null audio service, not against `nullptr` checks.
3. **Bind once, at startup.** No re-binding in gameplay code.
4. **Lookup at startup, cache the result.** Don't lookup per-frame.

### Pitfalls

- **Service-locator-as-global-bag.** Don't put gameplay state in the locator. Infra only.
- **Initialization order.** If service A needs service B at construction, define the order explicitly.

## Flyweight (shared immutable data)

When you have N entities sharing identical data, share the data not the copies.

### Examples

- Tile map: 100k tiles, 30 tile *types*. Tile *type* holds texture, collision, walkable; tile *instance* holds coordinate and type ref.
- Particle: type holds sprite, lifetime, behavior; instance holds position and age.
- Item: type holds icon, name, stats; instance holds quantity and modifiers.

### Rules

1. **Type / instance split.** Type is immutable, instance is mutable.
2. **Type is cheap to compare by reference.** Pointer equality, no string compare.
3. **Avoid mutating types at runtime.** A "level up" modifying the item type breaks every other instance of the item.

## Spatial Partition

When > 50 dynamic entities query each other for proximity, naive O(n²) hurts. Use a spatial index.

### Choices

- **Uniform grid** — best for predictable density. Cheap insert/query.
- **Quadtree (2D) / Octree (3D)** — best for varying density.
- **BVH** — best for static geometry + dynamic queries.
- **Sweep-and-prune** — best for axis-aligned, mostly-still-moving.

### Rules

1. **Update on motion, not per-frame.** Rebuild only what moved.
2. **Bound the query.** "All entities within radius R" — pick R conservatively to limit results.
3. **Profile the partition cost.** A grid that's too fine costs more in rebuild than the lookup saves.

## When *none* of these patterns

A small game (≤ 5k LOC) can ship with no patterns at all. A single update method, plain entities, no FSM, no event queue, no pool. Don't apply Game Programming Patterns as boilerplate; apply them when the problem they solve actually shows up in profiling or readability.

## Procedure (when reviewing architecture)

1. **Identify the game shape.** Genre, scale, multiplayer, target platform — these dominate which patterns are worth their complexity.
2. **Run the smell checklist:**
   - Single-class entity > 1500 lines? → Component candidate.
   - Boolean soup for state? → State candidate.
   - Per-frame `new`? → Object Pool candidate.
   - 200+ entity-to-entity proximity checks per tick? → Spatial Partition.
   - Cross-cutting singletons? → Service Locator.
   - Multi-system event broadcasts? → Observer / Event Queue.
3. **For each candidate, ask "what does this complexity buy me?"** If the answer is vague, skip it.
4. **Verify the game loop choice.** Fixed-timestep with variable render? If not, why not?
5. **Output review** with each finding referencing the Nystrom chapter and the rule it touches.

## Sources

- Robert Nystrom, *Game Programming Patterns*, https://gameprogrammingpatterns.com/ (free online, also in print).
- *Game Engine Architecture* — Jason Gregory, 3rd ed., CRC Press.
- *Game Programming Gems* series — pattern essays.
- *Effective C++ / More Effective C++* — Meyers' rules apply unchanged to game code.

When this gets stale: the patterns themselves don't age — they're 20-year-old wisdom about timing, decoupling, and resource management. Replace example games with current titles.
