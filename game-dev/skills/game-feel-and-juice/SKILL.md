---
name: game-feel-and-juice
description: Use when tuning the moment-to-moment responsiveness, "game feel", or "juice" of a game — input handling, controller feel, jump feel, hit feedback, screen shake, hitstop, easing curves, particle feedback, animation snappiness. Triggers on "improve game feel", "the jump feels off", "controller feels mushy", "tune the controller", "add juice", "the combat feels weak", "hits don't feel impactful", "input lag", "input feels delayed", "add coyote time", "add jump buffer", "add screen shake", "tune dead zones". Also triggers on `*controller*` / `*input*` / `*camera*` file edits in a game project. Grounded in Steve Swink (Game Feel) and platformer-feel best practices.
---

# game-feel-and-juice

Tuning rules for *moment-to-moment* responsiveness. Distilled from Steve Swink's *Game Feel: The Secret Ingredient* and the cross-genre consensus on input forgiveness (coyote time, jump buffer, input buffer, dead zones).

## Swink's six principles

Every game-feel decision touches one of these:

1. **Input** — the controller-to-character mapping. Higher sensitivity = more expressive but harder to master. Match input axis count to verb count: a single-button game can't have analog feel.
2. **Response** — how the simulation processes input. *Mario doesn't snap to max speed* — he accelerates over ~8 frames, decelerates over ~15. That ramp is the *feel*.
3. **Context** — spatial constraints. A jump that clears a 4-tile gap in a 5-tile corridor feels precise; in a 50-tile corridor it feels trivial. Layout sells the mechanic.
4. **Polish** — non-essential effects that sell physicality: screen shake, particles, squash-and-stretch, hitstop, camera punch. Cheap in code; *transforms* in feel.
5. **Metaphor** — what the player *thinks* they're controlling. Same physics, different sprite: a car vs a fat guy vs a ghost vs a robot — each feels completely different because expectations differ.
6. **Rules** — what makes the feel *matter*. Without higher-level goals (don't fall, kill the boss), great feel is just a toy.

## Concrete starting numbers (always tune via playtest)

Frames are at **60 FPS** unless noted. These are *starting points*, not commandments — every game's feel target is different. Tune via playtest.

### Input forgiveness

| Mechanic | Starting value | Source |
|---|---|---|
| **Coyote time** (jump after leaving ledge) | 6–8 frames (100–133ms) | Celeste / Hollow Knight consensus |
| **Jump buffer** (jump pressed before landing) | 6 frames (100ms) | Celeste source |
| **Input buffer** (action queued before window) | 3–6 frames (50–100ms) | Fighting-game / action-game norm |
| **Edge-cling forgiveness** (auto-grab near ledge) | 2–4 px | *Mario Odyssey*-style assist |

### Response curves

| Movement event | Ramp | Notes |
|---|---|---|
| Accel from rest to max walk | 6–10 frames | Tweak: shorter = snappier, longer = "weight" |
| Decel from max to rest | 4–8 frames | Always shorter than accel for "responsive" feel |
| Air control (% of ground accel) | 50–80% | 100% = floaty, 0% = frustrating |
| Jump rise gravity | g | — |
| Jump fall gravity | 2g–2.5g | Asymmetric gravity is *the* platformer trick |
| Variable jump cutoff | release-to-cutoff = 4 frames | Hold = full jump, tap = half |

### Hit feedback

| Effect | Starting value |
|---|---|
| **Hitstop** (freeze on impact) | 3–6 frames for normal hit, 8–12 for crit |
| **Screen shake amplitude** | 1–3 px normal, 4–8 px big hit; decay over 8–15 frames |
| **Knockback** | distance proportional to damage; never zero |
| **Hit flash** (white-out sprite) | 2–4 frames |
| **Hit particle count** | 4–8 normal, 12–20 crit |
| **Camera punch** (1-frame zoom-in) | scale 1.02–1.05x, decay 4–6 frames |

### Animation easing

- **Snappy actions** (attacks, dodges, jumps): use cubic-in or expo-in — fast at start, no anticipation. Anticipation frames before an attack are for *responsive* combat killers (Souls). Drop them for *snappy* combat (DMC, Bayonetta).
- **Settling motions** (idle return, camera recenter): use cubic-out or expo-out — fast at start, smooth end.
- **UI tweens**: 0.15–0.25s with ease-out. Anything longer feels sluggish.

## Dead zones (analog sticks)

| Zone | Range | Use |
|---|---|---|
| **Inner dead zone** | 0.10–0.20 of stick magnitude | Ignore drift |
| **Outer dead zone** | 0.95–1.0 | Clamp to full-tilt |
| **Curve** | linear, then squared past ~0.3 | More precision at low tilt, full speed at full tilt |

Always **rescale** input magnitude after dead-zone subtraction. The classic bug is "stick is mushy near zero, then suddenly full speed" — that's a dead zone that *clips* instead of remapping.

## The Polish toolkit, ranked by ROI

These are nearly free in code. Use them.

1. **Screen shake on impact.** Hour-of-work payoff in feel.
2. **Hitstop on kill / heavy hit.** Half-hour payoff. *The* trick to making combat feel "weighty."
3. **Particle bursts on action.** Dust on landing, sparks on parry, debris on hit.
4. **Squash-and-stretch on jump/land.** Disney's 12 principles still work in 2026.
5. **Camera punch / zoom on big moments.** Sells scale.
6. **Audio layering.** Same hit sound + variant pitch (±10%) + low-frequency thud on crit.
7. **Time dilation (bullet time) on near-misses or final blows.** Use sparingly — overuse kills the effect.
8. **Trail effects on fast motion.** Sword swings, dashes, projectiles.

## Anti-patterns

- **Input lag from physics interpolation.** If physics runs at 50 Hz but rendering at 144 Hz, input feels delayed unless you interpolate. See [[game-architecture-patterns]] Game Loop section.
- **Mushy controls "for realism."** Realistic vehicle/character feel is *not* fun feel. Tune for *responsive*, not real.
- **Hitstop on every action.** Hitstop loses meaning if it fires constantly. Reserve for impact moments.
- **Screen shake on every effect.** Same — reserve for emphasis. Constant shake = headache.
- **Anticipation frames on a "fast" character.** If the character can read a frame before the player, the player will hate it.
- **Punishing the player for sloppy input.** Coyote time, jump buffer, and input buffer exist *for a reason*. The player's brain is faster than their thumb.

## Procedure (when reviewing or tuning game feel)

1. **Identify the verb being tuned.** Jump? Attack? Dodge? Aim?
2. **Test the *bad* case.** Is there input lag? Find it before tuning anything else.
3. **Measure response.** Accel/decel ramps in frames. Are they symmetric? (Should be asymmetric for snap.)
4. **Add forgiveness if it's a precision verb.** Coyote / jump buffer / input buffer if the verb has a timing window.
5. **Layer Polish from the ROI list above.** Pick 2–3, not all 8.
6. **Playtest.** Game feel is the one area where intuition lies — only the controller in someone's hands tells the truth.
7. **Profile.** Polish effects (particle systems, post-processing) are common frame-rate killers. See [[engine-unity]] / [[engine-godot]] / [[engine-unreal]] for hot-path rules.

## Sources

- Swink, *Game Feel: The Secret Ingredient*, gamedeveloper.com / *Game Feel* book.
- Celeste source — `Player.cs` (open source, MIT) — canonical coyote-time/jump-buffer reference.
- Maddy Thorson — "Celeste & TowerFall Physics" devlog.
- Ketra Games — "Improve Annoying Jump Controls With Coyote Time and Jump Buffering."
- Mark Brown / *Game Maker's Toolkit* — multiple videos on game feel (informal but well-researched).
- *Doom (2016)* GDC postmortem — combat hitstop / glory kill cadence.

When this gets stale: numbers age, principles don't. Re-derive numbers from a modern game in the target genre.
