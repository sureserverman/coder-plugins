---
name: engine-unity
description: Use when authoring or reviewing Unity projects (Unity 6 / 2022+) — C# MonoBehaviour, ScriptableObject, Update / FixedUpdate / LateUpdate lifecycle, GC pressure, prefabs, addressables, scenes, DOTS/ECS, package manifest. Triggers on edits to `*.cs` files under `Assets/`, `*.unity` scenes, `*.asset`, `ProjectSettings/`, `Packages/manifest.json`, `*.prefab`. Also on natural-language prompts like "Unity best practices", "Update vs FixedUpdate", "ScriptableObject for shared data", "Unity GC allocations", "Addressables", "Unity DOTS overview", "MonoBehaviour lifecycle", "Unity performance review". Grounded in Unity 6 official programming best practices.
---

# engine-unity

Opinionated rules for Unity 6 (and 2022+ LTS) projects. Distilled from the official Unity programming best practices (docs.unity3d.com/6000.3/Documentation/Manual/programming-best-practices.html) and a generation of GDC postmortems.

## The Unity execution model

Three update phases, not one. Pick the right one — using the wrong phase is the most common Unity bug.

| Phase | Rate | Use for | Avoid |
|---|---|---|---|
| **`Update()`** | Frame rate (variable) | Input polling, animation state, non-physics visuals | Physics, force application |
| **`FixedUpdate()`** | Fixed (default 50 Hz) | Physics, `Rigidbody` forces, deterministic gameplay | Per-frame visuals (will stutter) |
| **`LateUpdate()`** | After all `Update()` and `Animator` | Camera follow, IK adjustments, anything reading another transform's *final* position this frame | Anything that needs to drive other Update behavior |

### Rules

1. **Movement of `Rigidbody` = `FixedUpdate`**, not `Update`. Otherwise force application is frame-rate-dependent.
2. **Reading transforms moved this frame = `LateUpdate`.** Camera follow especially — read the avatar's final position after physics.
3. **Input polling = `Update`.** `FixedUpdate` may miss single-frame presses.
4. **Animator parameters = `Update`.** `LateUpdate` is too late if other code reads the animator state this frame.

See also [[game-architecture-patterns]] for the underlying fixed-vs-variable timestep theory.

## Garbage Collection — the #1 cost

Unity's mono GC is non-generational and pauses execution. *Any* allocation in the hot path can stutter.

### Rules

1. **No `new` keyword in `Update`/`FixedUpdate`/`LateUpdate`** for non-trivial types. Allocate once in `Awake`/`Start`, reuse.
2. **Cache `GetComponent` in `Awake`**, never call in `Update`. Each call is a managed array allocation.
3. **No LINQ in per-frame methods.** `Where`, `Select`, `ToList`, `OrderBy` all allocate. Use raw `for` loops in hot paths.
4. **No `string` concatenation in `Update`.** Even `transform.position.ToString()` allocates. Use `StringBuilder` (clear and reuse), or only emit on event.
5. **No `Find()` / `FindObjectOfType()` in `Update`.** These are linear scans of the scene. Cache in `Awake`.
6. **`foreach` over `List<T>` is allocation-free in modern C#**, but `foreach` over `Dictionary<K,V>` allocates an enumerator. Use indexed `for` if hot.
7. **Pre-size `List<T>` capacities** in `Awake` if peak size is known.
8. **Reuse arrays.** `Physics.OverlapBoxNonAlloc` and friends exist for this — use the `NonAlloc` variants.

### Detect via profiler

Open Profiler → CPU → GC Alloc column → sort by descending. Anything > 0 in `Update` is a bug.

## ScriptableObject — for shared data and decoupling

`ScriptableObject` is a Unity-native asset that lives in the project, not in a scene. It's the right tool for:

- **Shared static data** — item stats, enemy types, dialogue lines.
- **Event channels** — a SO that subsystems Raise() on and others Listen() to (Ryan Hipple, Unite 2017 "Game Architecture with Scriptable Objects").
- **Runtime sets** — a SO that maintains "all active enemies" as a list, populated/depopulated by `OnEnable`/`OnDisable` in the items.
- **Settings / preferences.**

### Rules

1. **Item stats / weapon stats / enemy stats = SO**, not hard-coded scripts and not JSON loaded at runtime.
2. **No gameplay state in SO** — SOs survive Play-mode exits in editor and *can* retain state by accident. Reset `OnEnable` if instance state is needed.
3. **Decouple via SO event channels.** Subsystems don't need to know about each other; they share a SO.
4. **Domain Reload pitfalls.** Disabling domain reload to speed iteration breaks `static` fields. SOs sidestep this.

## MonoBehaviour lifecycle — the order

Memorize this. Bugs come from misordering.

```
Awake()         // Once. References to *this* object only.
OnEnable()      // Every enable. Wire up event handlers here.
Start()         // Once, after all Awakes. Cross-object refs safe.
FixedUpdate()   // Fixed rate.
Update()        // Frame rate.
LateUpdate()    // After all Updates.
OnDisable()     // Every disable. Unwire event handlers here.
OnDestroy()     // Once. Release native resources.
```

### Rules

1. **`Awake` for self-init**, `Start` for cross-object init. Don't reference another object's state in `Awake`.
2. **Event subs in `OnEnable`, unsubs in `OnDisable`.** Symmetry prevents zombies and double-subs.
3. **No `null` checks against `Destroy`'d Unity objects with `ReferenceEquals`** — Unity overloads `==` to return true for destroyed-but-not-GC'd objects. Use `obj == null`.

## Coroutines vs `async/await` vs `Awaitable`

Unity 6 introduces `Awaitable` for async work on the main thread. Use it.

### Rules

1. **`Awaitable` over `Task` for main-thread work.** `Task.Result` blocks; `Awaitable` cooperates with Unity's main thread.
2. **Coroutines for time-based gameplay** (wait 2 seconds then spawn). Familiar pattern, fine for game logic.
3. **No async I/O on main thread without `Awaitable.BackgroundThreadAsync()`.** Blocking the main thread freezes the game.
4. **No Unity API from background threads.** Period. Anything that touches `transform`, `GameObject`, components — main thread only.

## Addressables vs Resources vs Direct Refs

| System | Use for | Why |
|---|---|---|
| **Direct ref** (`[SerializeField]`) | Small, scene-local assets | Simplest, no async |
| **Addressables** | Big assets, DLC, conditional loads | Async load/unload, memory control |
| **Resources/** folder | **Avoid** in modern Unity | Forces everything to ship in build, no async |

### Rules

1. **No `Resources/` folder in new projects.** Use Addressables.
2. **Direct serialized refs for prefabs in the same scene.** Easy and efficient.
3. **Addressables for boss assets, level packs, optional content.** Loads on demand, releases when done.
4. **Always release Addressables.** `Addressables.Release(handle)`. Memory leak if you don't.

## Scenes and prefabs

### Rules

1. **One scene = one *level/screen*** is the simplest model. Multi-scene additive loading is powerful but easy to misuse.
2. **Prefabs are the unit of reuse.** Entities (enemies, items, UI panels) → prefabs.
3. **Prefab variants** for type families (sword → fire-sword variant, ice-sword variant).
4. **No scene-baked references between prefabs.** A prefab can't reference a scene object — use scene-level wiring or SO event channels.

## DOTS / ECS — when it's worth the cost

DOTS (Data-Oriented Tech Stack) gives massive perf for many entities, but it's a *separate programming model*.

### Use DOTS when

- > 10,000 simultaneously simulated entities.
- Tight perf budget (mobile / VR / minimum-spec).
- Team has time to learn ECS thinking.

### Don't use DOTS when

- Game has fewer than ~1,000 entities.
- Team is new to Unity.
- Project ships in < 6 months.

GameObject + MonoBehaviour will carry most games to ship.

## Performance check rules

1. **Use the Profiler, not intuition.** "I think this is slow" → measure. Always.
2. **Memory profiler for leaks.** Especially Addressables references.
3. **Frame Debugger for draw-call bloat.** Batch-able sprites that don't batch are common.
4. **Cache `Camera.main`.** It's a `FindObjectsOfType` internally. Cache once.
5. **Static batching** for non-moving level geometry.
6. **GPU instancing** for many identical moving objects (bullets, particles).

## Common Unity pitfalls

1. **Reading `transform.position` repeatedly in a frame** — caches a getter call per access. Local-variable it once per method.
2. **`SetActive(true)` on a deactivated GameObject re-runs `OnEnable`** — make sure handlers are idempotent.
3. **Coroutine on a disabled GameObject does *not* run.** Reactivating doesn't resume.
4. **`Time.deltaTime` in `FixedUpdate`** is wrong — use `Time.fixedDeltaTime` (or just the delta arg).
5. **`Instantiate(prefab)` in `Update`** allocates and runs `Awake`. Pool it. See [[game-architecture-patterns]] Object Pool.
6. **UI Toolkit vs UGUI vs IMGUI.** New projects: UI Toolkit. Existing projects: stay on UGUI. IMGUI: editor tooling only.
7. **Singleton MonoBehaviours with `DontDestroyOnLoad`** that re-register on every scene load — guard with a static instance check.

## Cross-engine concerns

- **Game loop discipline.** See [[game-architecture-patterns]] for the fixed-timestep theory; Unity gives you `FixedUpdate` to express it.
- **Object pooling.** Unity 2021+ ships `UnityEngine.Pool.ObjectPool<T>`. Use it.
- **State machines.** Use the Animator FSM for animation state; use plain C# state machines for gameplay logic — don't conflate them.
- **Camera.** Use Cinemachine. Hand off to [[game-navigation-camera]] for the rules Cinemachine implements.

## Procedure (when reviewing a Unity project)

1. **Stack detection.** Unity version, render pipeline (Built-in / URP / HDRP), input system (Input Manager / Input System package), assembly definitions.
2. **Open the Profiler.** Note `GC Alloc` in `Update`. Any non-zero is a finding.
3. **Grep for smells:**
   - `GetComponent` in `Update`/`FixedUpdate`.
   - LINQ in `Update` / `FixedUpdate` / `LateUpdate`.
   - `new` in per-frame methods (excluding trivial value types).
   - `Find` / `FindObjectsOfType` in `Update`.
   - String concatenation in `Update`.
4. **Check `FixedUpdate` for physics use.** If `Rigidbody.AddForce` is in `Update`, that's a bug.
5. **Audit Addressables vs Resources.** Resources/ in a new project = finding.
6. **Audit Singletons / DontDestroyOnLoad** — must guard against re-init.
7. **Audit SO usage.** Item stats in SO? Or scattered across scripts? Event channels for cross-system events?
8. **Output severity-ranked review** with profiler evidence cited.

## Sources

- Unity 6 Programming Best Practices — https://docs.unity3d.com/6000.3/Documentation/Manual/programming-best-practices.html
- Ryan Hipple, Unite Austin 2017 — "Game Architecture with Scriptable Objects" (canonical SO-as-event reference).
- Microsoft Learn — Performance recommendations for Unity (Mixed Reality docs apply broadly).
- Cinemachine documentation — Unity's camera system.

When this gets stale: Unity 7 will reorganize the manual. Re-fetch the programming-best-practices and the Profiler sections.
