---
name: engine-unreal
description: Use when authoring or reviewing Unreal Engine 5 projects — C++ gameplay code, Blueprints, GameMode, GameState, PlayerController, Pawn/Character, PlayerState, Subsystems, replication, .uproject configuration. Triggers on edits to `*.cpp`/`*.h` inheriting from `AActor`/`APawn`/`AGameModeBase`/`APlayerController`/`UGameInstance`, `*.uasset`, `*.umap`, `*.uproject`. Also on natural-language prompts like "Unreal gameplay framework", "GameMode vs GameState", "PlayerController vs PlayerState", "Blueprint vs C++", "Unreal Subsystem", "Unreal replication", "UE5 architecture review", "Pawn possession". Grounded in Epic's official Unreal Engine 5 documentation (dev.epicgames.com).
---

# engine-unreal

Opinionated rules for Unreal Engine 5 projects. Distilled from Epic's official gameplay framework documentation (dev.epicgames.com/documentation/en-us/unreal-engine/gameplay-framework-in-unreal-engine), Tom Looman's published guides, and a decade of Unreal community consensus.

## The gameplay framework — the boundaries that matter most

Unreal's gameplay framework is *opinionated*. It works *only* if you respect the class boundaries. Misuse here causes the worst Unreal bugs — multiplayer desyncs, replication leaks, and "works in editor, breaks in build" failures.

| Class | Lives on | Owns | Don't put here |
|---|---|---|---|
| **`AGameModeBase`** | Server only (multiplayer); always (singleplayer) | Rules, win conditions, spawn logic | Player data; UI state; anything clients need to see |
| **`AGameStateBase`** | Replicated to all clients | Match state, score, time remaining | Per-player data; server-secret state |
| **`APlayerController`** | Client (with server stub) | Input handling, possession of pawn | Player data that persists past pawn death |
| **`APawn` / `ACharacter`** | World, possessed by controller | Movement, physics, animation, abilities | Per-player score, persistent stats |
| **`APlayerState`** | Replicated to all clients | Per-player score, ping, persistent data | Logic; this is a data class |
| **`UGameInstance`** | Client process | Cross-level state, save/load coordination | Anything per-level |
| **`UGameInstanceSubsystem`** | Client process | Cross-cutting infra (audio, save, telemetry) | Per-level state |
| **`UWorldSubsystem`** | Per world | Per-level shared services | Anything that needs to survive level transition |

### Rules (the boundary errors that wreck Unreal projects)

1. **Never access `AGameMode*` from a client.** It doesn't exist there. Multiplayer-by-default thinking: ask "where does this code run?" before you write it.
2. **Communication flows GameMode → GameState → clients.** GameMode tells GameState; GameState replicates; clients read GameState. Never the reverse.
3. **Per-player data goes in `APlayerState`**, not `APlayerController`, not `APawn`. Because pawns die, controllers don't always exist on every client, but `APlayerState` is replicated and survives death.
4. **Spawning lives in `AGameMode*`.** `APlayerController` *possesses* an already-spawned pawn; it does not spawn pawns itself (in server-authoritative play).
5. **Default to `AGameModeBase`, not `AGameMode`.** `AGameMode` is the full-fat class with match state machine; `AGameModeBase` is leaner. Most games don't need match states.
6. **Subsystems > custom GameInstance overrides.** `UGameInstanceSubsystem` is the modern equivalent of "where do I put global services" — auto-instantiated, no boilerplate.

## Blueprint vs C++ — the rule

Unreal supports both. The shipping balance:

- **C++** owns: gameplay framework classes, performance-critical loops, asset management, networking, anything that needs to be hard to override.
- **Blueprint** owns: designer-friendly variation, UI behavior, level scripting, rapid prototyping of mechanics, anything visual artists / designers will touch.

### Rules

1. **C++ base, Blueprint subclass.** Define `AMyEnemy` in C++, derive `BP_Goblin`, `BP_Orc` in Blueprint with assets and stats.
2. **`UPROPERTY` everything Blueprint touches.** No exposed property = no designer access.
3. **`UFUNCTION(BlueprintCallable)` for C++→BP API.** Without it, Blueprints can't call your C++.
4. **`UFUNCTION(BlueprintImplementableEvent)`** when C++ defines the *call site* but Blueprint provides the implementation. (Designer fills in animation cues, etc.)
5. **`UFUNCTION(BlueprintNativeEvent)`** when C++ has a default implementation but Blueprint can override. The C++ side is named `_Implementation`.
6. **No tick logic in Blueprint** for entities that exist in large numbers. Blueprint tick is 5–10× slower than C++. Use C++ tick + BP events for state changes.
7. **Don't put network logic in Blueprint.** Replication metadata yes; the actual replicated functions, no — easier to reason about in C++.

## Replication — the rules

Multiplayer is where Unreal's class boundaries actually pay rent. Get them right.

### Rules

1. **`UPROPERTY(Replicated)` + `GetLifetimeReplicatedProps`** to replicate a property. Forgetting the lifetime function = silently nothing replicates.
2. **`Server`, `Client`, `NetMulticast`** RPC specifiers. Pick deliberately:
   - `Server` — client → server (the *only* path for client-initiated authority).
   - `Client` — server → owning client (private to that player).
   - `NetMulticast` — server → all clients (cosmetic FX broadcast).
3. **`Reliable` vs `Unreliable`** — reliable has cost, use sparingly. Unreliable for cosmetic effects.
4. **Authority check before mutating state.** `if (HasAuthority()) { ... }` — server-only state changes happen *only* on the server.
5. **Replication is async.** Don't expect `SetReplicatedVar(true); CheckVar()` to see the new value on clients immediately. Use `RepNotify` for value-change reactions.
6. **`OnRep_Foo` notify functions** trigger on clients when Foo changes. Always implement them — never trust raw replicated state without a reaction.

## Subsystems — the modern way to globals

UE5 introduced subsystems as the answer to "where do I put global services."

| Subsystem | Lifetime | Use for |
|---|---|---|
| `UEngineSubsystem` | Engine | Editor-time tooling |
| `UGameInstanceSubsystem` | Game process | Save system, telemetry, audio manager |
| `UWorldSubsystem` | Per world | Per-level shared services |
| `ULocalPlayerSubsystem` | Per local player | Input mapping, UI state |

### Rules

1. **Subsystem > Singleton.** Auto-instantiated, no static state, no header pollution.
2. **One subsystem, one concern.** Don't write `UMyGameSubsystem` that does saves *and* audio *and* leaderboards.
3. **Access via `GetSubsystem<>()`.** Cheap, type-safe.
4. **No tick in subsystems unless required.** They're services, not actors.

## Performance — the Unreal-specific rules

1. **`Tick` is opt-out by default for some classes, opt-in for others.** Check `PrimaryActorTick.bCanEverTick`. Most static actors don't need it.
2. **`SetActorTickEnabled(false)`** for actors that don't need it right now.
3. **`Component` ticks separately from `Actor`.** Same opt-in / opt-out story.
4. **Garbage collector pause** — UE has a GC. Frequency tuned in project settings. Many UObjects allocated per frame = stutter.
5. **Soft references over hard references** for assets that aren't always needed. `TSoftObjectPtr<UTexture2D>` doesn't force-load the texture.
6. **Async asset loading** via `FStreamableManager` for content not needed immediately.
7. **Stat commands.** `stat fps`, `stat unit`, `stat scenerendering`, `stat game` — the in-editor profiler is excellent.
8. **No `Cast<T>` in hot loops.** Cache the cast.

## Common Unreal pitfalls

1. **`UPROPERTY` on a raw pointer is required for GC**, otherwise the pointer is garbage-collected out from under you. `UPROPERTY() AActor* MyActor;` not `AActor* MyActor;`.
2. **`GetWorld()` returning null in constructors** — actors don't have a world during construction. Use `BeginPlay()`.
3. **Tick order is undefined between unrelated actors.** Use `AddTickPrerequisiteActor` if you need ordering.
4. **Hot-reload corrupts C++ class state.** Use Live Coding (UE5+) instead of legacy hot-reload.
5. **Blueprint nativization** is deprecated in UE5. Don't rely on it.
6. **Animation Blueprint thread-safety.** Property accessors run on worker threads; only thread-safe data sources are valid.
7. **Replication graph bandwidth blows up** with naïve `Multicast`. Use replication conditions and relevancy.

## Cross-engine concerns

- **Game loop discipline.** Unreal's tick uses variable-timestep by default; physics is sub-stepped. See [[game-architecture-patterns]] for theory.
- **Camera.** Unreal's `APlayerCameraManager` and Camera Modifier system implement many of the rules in [[game-navigation-camera]].
- **Animation state machines** — use them for animation; use plain C++ state machines for gameplay logic. Don't conflate.
- **Object pooling** — Unreal has no first-class pool; roll your own or use `FObjectPool` patterns from community plugins.

## Procedure (when reviewing an Unreal project)

1. **Stack detection.** UE version (5.x), C++ / Blueprint mix, multiplayer or singleplayer, target platforms, Lumen / Nanite use.
2. **Map the gameplay framework hierarchy.** Which GameMode? Which GameState? Which PlayerController/Pawn? Are class boundaries respected?
3. **Audit replication.** Are `UPROPERTY(Replicated)` properties paired with `GetLifetimeReplicatedProps`? Are RPC specifiers correct?
4. **Check authority.** `HasAuthority()` guards before state mutation?
5. **Audit subsystems.** Are globals via subsystems, or via static state / Singletons?
6. **Profile.** `stat fps`, `stat unit`. Tick overhead? GC pauses? Asset load hitches?
7. **Audit `Tick` enablement.** Are tickless actors actually tickless?
8. **Blueprint hot-paths.** Is anything Blueprint-ticking that should be C++?
9. **Output severity-ranked review.**

## Sources

- Unreal Engine 5 Gameplay Framework — https://dev.epicgames.com/documentation/en-us/unreal-engine/gameplay-framework-in-unreal-engine
- Tom Looman — *Unreal Engine Gameplay Framework Guide for C++* (tomlooman.com/unreal-engine-gameplay-framework/).
- Epic Game Developers Library — replication and networking talks.
- Outscal — "Unreal Engine GameMode" architecture explainer.
- Unreal Engine Forums — official replication FAQ.

When this gets stale: re-check the gameplay framework page on dev.epicgames.com. Epic reorganizes their docs; class names stay stable.
