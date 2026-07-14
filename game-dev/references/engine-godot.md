# engine-godot

Opinionated rules for Godot 4 projects. Distilled from the official best practices section of docs.godotengine.org (`/en/stable/tutorials/best_practices/`).

## The Godot philosophy

Godot's design is **scene-as-composition**. A scene is a tree of nodes, each node has a single responsibility, and scenes compose via instancing. Lean into this — don't fight it with monolithic scripts or god-autoloads.

## Scenes vs Scripts vs Custom Resources

Three first-class units in Godot. Pick the right one.

| Unit | Use for | Skip for |
|---|---|---|
| **Scene** (.tscn) | Game-specific concepts, reusable composed entities, level geometry, UI screens | Pure logic with no visual / hierarchy |
| **Script** (.gd / class) | Reusable behavior, custom node types, editor tools | Game-specific entities (use scenes) |
| **Custom Resource** (.tres) | Configuration data, item / enemy stats, save data | Things that need a node lifecycle |

### Rules

1. **Game-specific = scene.** A "Goblin" with sprite, collision, health bar is a scene, not a script that constructs all that in `_ready()`.
2. **Reusable tool = script class.** A `HealthBar` that can drop into any UI is a script with `class_name`.
3. **Configuration = custom resource.** A `WeaponStats` resource with damage / range / fire-rate is `extends Resource` with `@export`s.
4. **Scenes are *much* faster than scripted construction.** PackedScene serializes for batch creation; script-constructed trees fire engine-API calls one node at a time.

## Autoload (singletons) — restrain

Autoloads are global singletons available from every script. They are the single most-abused feature in Godot.

### Rules

1. **Cap autoloads at ~5.** Common legit autoloads: `GameState`, `SaveSystem`, `AudioBus`, `EventBus`, `Settings`. More than that and the project is becoming spaghetti.
2. **No game-specific logic in autoloads.** "PlayerAutoload" holding the player node is wrong — the player is a scene, not a singleton.
3. **No autoload for "convenience".** If a script *could* get a reference via `get_tree().get_first_node_in_group("foo")` and you're making an autoload to avoid that, you're adding global state to save 2 lines.
4. **Document the autoload's lifecycle.** When does it spawn? When does it persist? What does it own?
5. **Use composition over autoload.** A `LevelManager` node *inside the level scene* is almost always better than `LevelManagerAutoload`.

## Signals over polling

Godot's signals are the engine-blessed observer pattern. Use them.

### Rules

1. **`_process()` that checks a value every frame = signal candidate.** If the value changes irregularly, emit a signal instead.
2. **Custom signals for game events.** `health_changed(new_value)`, `died`, `picked_up_item(item)` — define them explicitly with `signal`.
3. **Connect in `_ready()`, disconnect in `_exit_tree()`** if the target may outlive the source.
4. **Don't chain signals into recursion.** A signal that triggers another that triggers another is a stack-trace nightmare.
5. **One signal, one purpose.** A `state_changed(state)` signal that's read 12 different ways = split into multiple typed signals.

## Node tree composition

### Rules

1. **One node, one responsibility.** A node that handles both input *and* physics *and* rendering wants to be a scene of three nodes.
2. **Composition depth ≤ 5 by default.** Deeper trees are valid but harder to maintain. Re-evaluate if you're at depth 7.
3. **Children own children, not the other way around.** A child node should not call `get_parent().do_something()` — emit a signal up instead.
4. **Group membership instead of direct refs.** `add_to_group("enemies")` then `get_tree().get_nodes_in_group("enemies")` is cleaner than hard refs.
5. **No `get_node("../../../X")`.** Long up-tree paths are brittle. Refactor for composition or signals.

## Resource (`.tres`) usage

Custom resources are the Godot way to share data.

### Rules

1. **Item / enemy / weapon stats = `.tres`.** Not `.gd` constants, not autoload dictionaries.
2. **`@export` for designer-friendly fields.** Inspector editing is the whole point.
3. **Resources can have signals.** Useful for "live" config that updates UI when changed.
4. **Watch for shared references.** Multiple nodes referencing the same `.tres` will all see mutations. Use `.duplicate()` for instance state.

## `_process` / `_physics_process` discipline

Godot's two main update callbacks differ by purpose.

| Callback | Use for | Rate |
|---|---|---|
| `_process(delta)` | Visuals, UI updates, non-physics state | Variable (frame rate) |
| `_physics_process(delta)` | Physics, movement, collisions, gameplay | Fixed (default 60 Hz) |
| `_unhandled_input(event)` | Input that didn't bubble through UI | Event-driven |
| `_input(event)` | Input that needs to intercept UI | Event-driven |

### Rules

1. **Movement / physics = `_physics_process`**, not `_process`. Predictable simulation.
2. **Don't override `_process` if you don't need it.** Empty overrides still cost engine call overhead.
3. **`set_process(false)` when idle.** A node that's paused-and-waiting shouldn't be in the process queue.
4. **`set_physics_process(false)` for static nodes.** Same logic, physics flavor.
5. **No `await` inside `_process`** unless you understand the implications — the function will hold up the engine until the awaitable completes.

## Version control hygiene

A `.gitignore` for Godot 4:

```gitignore
# Godot 4 generated cache and project state
.godot/
.import/

# Build artifacts
export.cfg
exports/
*.import

# OS / IDE
.DS_Store
*.swp
.vscode/
.idea/
```

### Rules

1. **Track `*.tscn`, `*.gd`, `*.tres`, `*.cfg`, `project.godot`.** These are the source of truth.
2. **Don't track `.godot/`** — engine cache, regenerates on open.
3. **Binary assets stay in repo** (PNG, OGG, GLB). LFS if > 50 MB each or > 100 in count.
4. **One change per commit.** Godot's scene format is reasonably mergeable but conflicts are brutal; small commits ease pain.

## Common Godot 4 gotchas

1. **`onready` is now `@onready`.** Migration from Godot 3 catches this. Same for `tool` → `@tool`, `export` → `@export`.
2. **`get_node()` paths are case-sensitive and brittle.** Use `@onready var x = $Path/To/Node` once, reference `x` thereafter.
3. **`_ready()` order is depth-first, child-first.** Parents `_ready()` *after* children. Don't depend on the opposite.
4. **CharacterBody2D vs RigidBody2D.** Use `CharacterBody2D` for player-controlled characters; `RigidBody2D` for physics-driven objects (boxes, balls). Mixing them causes "the player feels weightless" or "my box doesn't collide."
5. **`Tween` is now `Tween` node *and* `create_tween()` method.** Old API is `SceneTreeTween`-style.
6. **Signal Variant args.** Connect a signal with extra args via `bind()`, not positional ordering.
7. **`@export var x: Resource` shows in inspector as type-restricted dropdown.** Use this; don't take `Variant`.
8. **`process_mode` for pause behavior.** Set `PROCESS_MODE_ALWAYS` for pause menu, `PROCESS_MODE_PAUSABLE` for gameplay, `PROCESS_MODE_DISABLED` if it shouldn't run paused or unpaused.

## Performance signals

Watch for these in profiler:

1. **`Object::call` heavy** — script call overhead. C# or GDExtension for hot paths.
2. **`get_node` per frame** — cache with `@onready`.
3. **`String` allocations per frame** — concatenation in `_process`.
4. **`Tween` thrash** — don't create-and-destroy a tween every frame; `kill()` and `create_tween()` for one-shots.
5. **Physics layer mask too broad** — narrow masks cut collision work.
6. **Particles without lifetime cap** — set `lifetime` and `amount` deliberately; default 1000 amount × 10 sec = 10k particle slots.

## Procedure (when reviewing a Godot project)

1. **Run stack detection.** Godot version (3 vs 4 has huge differences), GDScript / C# / GDExtension mix, target export platforms.
2. **Read `project.godot`.** Display settings, physics tick rate, autoloads — autoloads especially.
3. **Map the scene structure.** Top-level scenes, instancing relationships, shared resources.
4. **Audit autoloads.** Are they justified? Are any candidates for "should be a scene"?
5. **Grep for `_process` polling smells.** Per-frame value checks → signal candidates.
6. **Check `_physics_process` vs `_process` usage.** Is movement in the right callback?
7. **Check version control.** Is `.godot/` ignored? Are `.tscn`/`.gd` tracked?
8. **Output severity-ranked review.**

## Sources

- Godot 4 official docs — https://docs.godotengine.org/en/stable/tutorials/best_practices/
- "Scenes versus scripts" — https://docs.godotengine.org/en/stable/tutorials/best_practices/scenes_versus_scripts.html
- "Autoloads versus internal nodes" — https://docs.godotengine.org/en/stable/tutorials/best_practices/autoloads_versus_internal_nodes.html
- Godot 4 migration notes (3 → 4).
- GDQuest tutorials — community standard for idiomatic Godot 4.

When this gets stale: re-fetch the best practices index. Godot moves fast — every minor version adds annotations and idioms.
