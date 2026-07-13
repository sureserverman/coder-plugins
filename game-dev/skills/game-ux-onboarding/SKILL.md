---
name: game-ux-onboarding
description: 'Use when reviewing or designing the user experience of a game — menus, HUDs, FTUE, tutorialization, signposting in UI, affordances, button prompts. Triggers: "design my game UI", "review my HUD", "design FTUE", "the UI is confusing". Grounded in Celia Hodent''s The Gamer''s Brain.'
---

# game-ux-onboarding

Rules for game UX, HUDs, menus, and tutorials. Distilled from Celia Hodent's *The Gamer's Brain* (CRC Press), the NN/g player experience research, and a generation of post-mortems.

Game UX differs from app UX: a player is *willing* to learn complexity, but only if the game *teaches* them. The job of game UX is to remove every barrier that isn't a designed challenge.

## Hodent's seven usability pillars

Every UX decision touches one of these. Use them as a review checklist.

1. **Signs and feedback.** Every action produces a perceivable effect within ~100ms. If the player can't tell whether their input registered, the UX has failed.
2. **Clarity.** Each element communicates one thing. If the player has to ask "what is that bar?" twice, rename / re-icon / re-color it.
3. **Form follows function.** Visual design serves utility, not aesthetics. A health bar shaped like a dragon's wing is cute and unreadable.
4. **Consistency.** Same icon = same meaning. Same color = same affordance. Same button = same verb. *Across the entire game.*
5. **Minimum workload.** Players have finite attention. Don't force a 3-tab navigation to do what one button could.
6. **Error prevention / recovery.** Confirm destructive actions. Allow undo. Make it impossible to spend an irreversible currency by accident.
7. **Flexibility.** Multiple ways to do the same thing. Keyboard *and* gamepad. Text *and* icons. Difficulty options.

## HUD design rules

The HUD is the player's nervous system. Build it deliberately.

1. **Show only what's actionable now.** Health, ammo, current objective, primary cooldowns. Hide the rest until needed.
2. **Diegetic > non-diegetic when possible.** A wound on the avatar's body is a better health indicator than a bar. (*Dead Space* did this. *Half-Life 2* did this with the suit.) But: diegetic is harder to read at a glance — use only when the moment-to-moment doesn't demand precision.
3. **Edge mounting.** HUD lives at the screen's edges, not the center, so it doesn't compete with the action.
4. **Animate to draw attention, not to decorate.** Pulse the health bar when it goes critical. Pulse it when it's full = noise.
5. **Numbers + bars together when precision matters.** A 0–100 health bar with no number = imprecise. A bar plus "47/100" = both glanceable and precise.
6. **Difficulty-scaled HUD.** Easy mode shows more (full map, enemy health). Hard mode hides more. Let players choose.
7. **Photosensitivity discipline.** No flashing > 3 Hz (basic accessibility). See [[game-accessibility-audit]].

## Menu / IA rules

Menus are where players quit, not where they play. Make them invisible to navigation.

1. **Time to first interaction ≤ 3 menu transitions.** From the title screen to playing should be 1 click on first launch, 2 max thereafter.
2. **Settings are 1 click from anywhere.** Pause → Settings, no nesting.
3. **Group settings by *symptom, not system*.** "Make text bigger" is one entry, not three (font size + UI scale + subtitle scale). Players don't think in systems.
4. **Persist *everything*.** Volume, key binds, accessibility settings — saved per-profile, never reset. See [[game-accessibility-audit]] basic-tier rule.
5. **Default sensibly.** Out-of-the-box settings should be playable for the median player. Don't ship at max difficulty with subtitles off.
6. **Back must be reliable.** A back button at the same screen position on every menu. Esc and Gamepad-B always go back. Always.
7. **Test cold start.** Have someone unfamiliar open the game and find subtitles in under 30 seconds. If they can't, the IA is broken.

## Button prompts and affordances

1. **Detect input device.** Show keyboard prompts when keyboard was last used; gamepad prompts when gamepad. Switch on input change within 1 frame.
2. **Show the actual binding, not the default.** If the player rebound Jump to spacebar, prompts say "Space", not "the jump button".
3. **Same verb = same color.** Confirm = green/blue, cancel = red, destructive = warning yellow.
4. **Don't reuse a button for two verbs in the same context.** "A to interact, A to drop" = the player will drop something they meant to pick up.
5. **Use icons that match the player's controller.** Xbox layout vs PlayStation vs Switch vs generic gamepad — detect and switch.

## FTUE / onboarding rules (the first 5–15 minutes)

The First-Time User Experience is the single highest-leverage section of any game. More than half of players who quit a game quit during FTUE.

1. **Open in the game, not in the menu.** First boot → 1 click → playing. Settings can wait. (Halo *Combat Evolved*: cinematic → control → play. No menu.)
2. **One mechanic at a time.** Don't introduce movement, shooting, jumping, and the inventory in the first minute. Movement first. Verify mastery. *Then* shooting. *Then* jumping.
3. **Teach by *doing*.** No modal text walls. A locked door with a key on the floor teaches "use the key" without a single line of text.
4. **Exaggerated rewards.** Every action in the first 10 minutes produces audible/visible/numeric feedback. (Dopamine hook.)
5. **Reduced failure cost.** First deaths are forgiving — Souls' Asylum tutorial *can be died-to safely*. Mario's first goomba is at a safe distance.
6. **Show the long-term promise.** Within the first 10 minutes, show the player a glimpse of what's possible at 10 hours. The dragon flying past. The locked tower. The opaque skill tree.
7. **Skip option for veterans.** If your game has a series predecessor, *let veterans skip the tutorial*. They will hate playing it again.
8. **Smooth dissolve.** By minute 30, FTUE is gone and the steady-state core loop has taken over. Don't ramp from FTUE to brutal — taper.

### Anti-patterns in FTUE

- **Modal popups every 10 seconds** explaining what the player can see for themselves.
- **Unskippable cinematics** before the player has held the controller.
- **Locked doors that explain themselves with text** instead of demonstrating in the level.
- **Tutorial that isn't fun.** The FTUE must be the core loop in miniature, or players will quit before they meet the real game.
- **Forced cosmetic / store visits in FTUE.** Players are evaluating whether the game is worth playing. Don't sell to them yet.

## Pause / death / save flow

These are micro-moments players hit hundreds of times. Polish them.

1. **Pause is instant.** No menu animation > 100ms. The player paused because something *now* needs their attention.
2. **Pause never auto-resumes.** Some games auto-resume after a delay. Don't.
3. **Death screen has a default action.** "Respawn at last checkpoint" is selected by default, gamepad-A confirms.
4. **Autosave indicator.** Tiny corner icon during save. Don't pause gameplay. Don't put a giant modal.
5. **Save corruption is a *catastrophic* failure.** Atomic write (write to .tmp, fsync, rename). Multiple save slots. Cloud backup if possible.

## Pause-screen specific

A pause screen is a *menu* but the player is mid-action. Treat it that way.

- Currently equipped items / objectives visible.
- Esc / Start always toggles.
- Resume defaults to selected.
- Don't put settings *inside* a sub-menu of a sub-menu — flatten.

## Localization rules (often missed)

1. **Don't bake text into textures.** Anything you'll translate must be text-rendered.
2. **Reserve 30–50% extra space for non-English UI.** German doubles English string lengths.
3. **Right-to-left support** if you ship in Arabic/Hebrew markets.
4. **CJK font rendering.** Test at minimum supported font sizes. Subtitles especially.

## Procedure (when reviewing game UX)

1. **Cold start.** Open the game fresh. Time from binary launch to playing. Count menu transitions.
2. **Find subtitles.** Without prior knowledge. ≤30 seconds is good.
3. **Find rebind controls.** ≤45 seconds.
4. **Run FTUE.** Note every modal popup. Note every locked mechanic introduction. Note feedback latency on each first action.
5. **Stress-test the HUD.** Maximum simultaneous information (full health bar pulsing, cooldown ready, ammo low, new objective). Is it readable?
6. **Stress-test menus.** Tab through every screen. Does Esc/Back work consistently? Are settings 1 click from anywhere?
7. **Pause / death / save check.** Each should be polished, instant, low-effort.
8. **Apply the Hodent 7-pillar checklist.** Sign-feedback, clarity, form-follows-function, consistency, minimum-workload, error-prevention, flexibility.
9. **Accessibility cross-check.** Hand off to [[game-accessibility-audit]] for the formal Basic-tier pass.
10. **Output severity-ranked findings**, each citing the pillar or FTUE rule violated.

## Sources

- Celia Hodent, *The Gamer's Brain: How Neuroscience and UX Can Impact Video Game Design*, CRC Press, 2018.
- celiahodent.com — UX/onboarding writeups.
- Nielsen Norman Group — player experience research.
- Designer Notes (Soren Johnson) — interviews on tutorialization.
- GDC postmortems on FTUE (e.g., *Halo Combat Evolved*, *Portal*).

When this gets stale: principles don't age. Replace specific game examples with current titles.
