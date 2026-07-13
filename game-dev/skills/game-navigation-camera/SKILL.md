---
name: game-navigation-camera
description: 'Use when designing, reviewing, or fixing a game camera (2D or 3D), level navigation, fast travel, signposting, or wayfinding. Triggers: "review my camera", "camera feels bad", "the camera fights the player", "design navigation". Grounded in John Nesky''s "50 Camera Mistakes" (GDC 2014).'
---

# game-navigation-camera

Rules for cameras and navigation. The camera is the *one* system the player can't turn off and can't escape. Get it wrong and the rest of the game can't save it. Distilled from John Nesky's GDC 2014 talk *50 Camera Mistakes* (he was the dynamic camera designer for *Journey*) and current Cinemachine / Unreal Camera Rig best practice.

## Nesky's prime directive

**The camera frames the avatar. It is never the subject.** Players are not looking at the camera; they're looking *through* it at their character. A camera that draws attention to itself has already failed.

Corollary: third-person dynamic cameras are *the hardest camera type to design*. If you can ship the game with a fixed angle, a side-scroll, an isometric, or a first-person view — **do it**. Don't pick dynamic third-person unless the game *requires* it.

## The non-negotiable rules

These come straight from Nesky. Apply them to every dynamic camera.

1. **Don't undermine sense of direction.** The camera must not rotate without player input *or* a clear cinematic reason. Disoriented players quit.
2. **Don't impair distance judgment.** Sudden FOV changes, dolly zooms, lens distortion — these confuse depth perception. Use only as intentional storytelling beats.
3. **Don't break line of sight.** When the world occludes the camera between the player and the action, *the camera must move first*. Either pull in, fade the occluder, or change angle. Never let the player attack what they can't see.
4. **Don't induce simulation sickness.** Avoid rapid yaw, high-frequency bobbing, or coupled roll. If the camera *must* shake, use horizontal-only or vertical-only — never combined sinusoidal motion at frequencies near vestibular resonance (~2–5 Hz).
5. **Don't be useless.** A camera that just floats at the same offset frame after frame is dead weight. The camera *participates*: it leads ahead in motion, frames threats, holds rest beats.

## Third-person follow camera — design rules

A dynamic third-person rig is composed of:

- **Target** — the avatar, or a point near it.
- **Pivot** — the rotation center, usually slightly above the avatar's head.
- **Boom** — the distance from pivot to camera.
- **Lens** — FOV.

Configure them by these rules:

1. **Lookahead in motion.** When the avatar moves, shift the camera 1–3 meters in the direction of motion so the player sees *where they're going*, not where they were. Latency: ramp over 8–16 frames so it doesn't snap.
2. **Vertical bias up.** Pivot above the head, never below. Cameras below the head feel claustrophobic and clip terrain.
3. **Boom collision pull-in.** When the boom intersects geometry, *retract* the camera to the collision point + small offset. Never let the camera clip through walls.
4. **Boom restoration.** When the obstruction clears, extend the boom *slowly* (1–2 seconds). Snapping back to default distance is jarring.
5. **Yaw deadzone.** A 5–15° window around the avatar where small movements don't trigger camera rotation. Prevents jitter when the player nudges.
6. **Yaw catch-up.** Outside the deadzone, the camera follows yaw at 60–80% the speed of the avatar. The lag *is* the feel.
7. **Pitch limits.** Clamp pitch between roughly -45° (looking down) and +30° (looking up) for combat games. Wider for exploration.
8. **No auto-recenter during gameplay.** Auto-recenter on yaw is one of the most-hated camera behaviors in modern games. The player chose that angle for a reason. Recenter on input only.
9. **Different rigs for different contexts.** Combat rig (close, snappy, threat-framing) vs exploration rig (wide, slow, scenic) vs cinematic rig (any) are *separate cameras* that blend on context switch. Don't bend one rig to do all three.

## 2D camera — design rules

2D is simpler but has its own rules:

1. **Camera leads, doesn't trail.** Like 3D, lead 1–3 tiles in the direction of motion.
2. **Tile-aligned snapping for pixel art.** Sub-pixel camera motion in pixel art destroys the aesthetic. Snap to whole pixels (or use rendering tricks like nearest-neighbor with internal smoothing).
3. **Vertical look-down (Metroidvania).** Hold-down-to-pan is a classic. Don't pan more than 2 screen heights.
4. **Camera windows / boxes.** A "deadzone" rectangle around the avatar — camera only moves when the avatar pushes its edge. Used in *Sonic*, *Symphony of the Night*, *Hollow Knight*.
5. **Vertical priority on jump arcs.** During a jump, slightly raise the camera so the apex is in frame.
6. **Screen shake — single axis.** 2D shake should be horizontal or vertical, not radial. Radial shake in 2D nauseates.

## Camera shake — concrete rules

- **Amplitude curve:** linear ramp-up *or* immediate spike, then **exponential decay**. Never sinusoidal — that's nausea.
- **Duration:** 4–15 frames at 60 FPS. Anything longer is intrusive.
- **Frequency:** above 10 Hz. Below 10 Hz hits the vestibular system.
- **Trauma model** (Squirrel Eiserloh, GDC 2016): shake amount = `trauma^2`, decay over time. Avoids linear-shake-feels-mechanical.
- **Disable option** in settings. Required for accessibility. See [[game-accessibility-audit]].

## Hitstop interacts with the camera

Hitstop (4–8 frames freeze on impact) makes hits feel weighty *because* it freezes the camera too. If hitstop freezes the world but the camera keeps moving, the effect is broken. See [[game-feel-and-juice]] for hitstop numbers; cameras must respect the freeze.

## Navigation design — beyond the camera

A game's navigation is composed of:

1. **Local navigation** — how do I move *here*? Solved by [[game-feel-and-juice]] (controller feel).
2. **Macro navigation** — how do I find *where to go next*?
3. **Wayfinding / signposting** — how do I know what I'm looking at?
4. **Fast travel** — how do I skip what I've already done?

### Signposting rules

Players orient on hierarchy. Frame the world so it tells you what matters:

1. **Hierarchy of light.** The brightest thing in frame is the most important thing. If the chest is glowing and the goal door isn't, the player will get lost.
2. **Hierarchy of contrast.** In a world of grey rocks, the red rope marks the path. The red rope must be the *only* red thing in the scene.
3. **Hierarchy of motion.** Moving things draw the eye. A wind-blown banner over the next objective is worth a hundred map markers.
4. **Hierarchy of scale.** The tower visible from anywhere on the map is the long-term goal. Use vertical landmarks aggressively.
5. **Negative space.** A wide path with empty walls invites travel. A narrow path with cluttered walls feels like a dead end.

### Wayfinding tools (ranked least-to-most intrusive)

1. **Environmental storytelling** — bodies, fires, footprints. Always best.
2. **Lighting / contrast / motion** — see Hierarchy rules.
3. **NPC dialogue and ambient sound** — "the boss is up the tower."
4. **Subtle UI** — minimap, compass strip.
5. **Diegetic markers** — paint, rope, scratch marks. (FromSoft message system.)
6. **Quest log / objective list** — explicit text. Useful as a fallback.
7. **HUD waypoint arrow / line.** The nuclear option. Use only when explicit guidance is required.

**Rule:** every level should be navigable using only tools 1–4. Tools 5–7 exist as accessibility fallbacks; if a player needs the waypoint arrow to find anything, the world design has failed.

### Fast travel design

1. **Earn it, then offer it.** Don't unlock fast travel until the player has walked the world enough to map it mentally.
2. **One-way (to-hub) is fine; everywhere-to-everywhere is the lazy default.** Constrained fast travel preserves spatial mastery.
3. **Cost can be time, not money.** Travel takes 5 seconds of menu, not a payment.
4. **No fast travel in dungeons.** Dungeons are gauntlets; fast travel breaks pacing.
5. **Reveal cost.** Show the player which discovered points are travel-able. Don't make them guess.

### World map / minimap rules

- **North up is a convention.** Break only if the level is literally non-cardinal (rotating world, etc.).
- **Player at center, rotated to facing direction** for action games. Fixed-orientation map for exploration games.
- **Show the unseen ambiguously.** Fog of war over uncharted area is a 30-year-old convention because it works.
- **Marker density discipline.** More than ~10 markers on-screen = noise.

## Anti-patterns

- **Auto-recenter on input.** Removes player agency over framing.
- **Camera-controlled player.** Avoid designs where the camera *moves* the avatar (rail movement) unless the game is on rails by design.
- **Free camera in a combat encounter.** Pin pitch and yaw partially during high-stakes combat; full freedom = lost player.
- **Spawn-on-camera enemies.** Enemies that pop into view at the boundary of the frustum feel cheap.
- **Cinematic that doesn't return camera to player state.** Cutscenes that snap the camera back to a different yaw than the player chose are jarring.
- **Waypoint arrow as world design.** If the only way to play the game is to follow an arrow, you've built a corridor.

## Procedure (when reviewing a camera)

1. **Identify the rig.** Fixed / side-scroll / isometric / first-person / dynamic third-person? Each has a different rule set.
2. **Apply Nesky's 5 don'ts.** Direction, distance, line-of-sight, sim sickness, usefulness.
3. **For dynamic third-person**, validate lookahead, vertical bias, collision pull-in, restoration timing, yaw deadzone, pitch clamp, context separation.
4. **For 2D**, validate leading, snapping, vertical priority, screen-shake axis.
5. **Test the worst cases.** Combat in a narrow corridor with line-of-sight breaks. Stairs. Tunnels. Glass floors. Indoor → outdoor transitions.
6. **Add the disable-shake option** if shake exists. (Accessibility.)
7. **Output review** with severity-ranked findings, each citing the Nesky principle or rule it touches.

## Sources

- John Nesky — *50 Camera Mistakes*, GDC 2014. GDC Vault and YouTube.
- Cinemachine documentation — Unity's high-quality camera system, distills many of the same rules.
- Squirrel Eiserloh — "Math for Game Programmers: Juicing Your Cameras with Math", GDC 2016 (trauma model).
- Mark Brown / *Game Maker's Toolkit* — "How Cameras in Side-Scrollers Work" (excellent informal survey).
- FromSoftware level design — *Dark Souls* environmental signposting case study.

When this gets stale: re-watch Nesky's talk. The principles are timeless; the example games age.
