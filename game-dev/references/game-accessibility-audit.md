# game-accessibility-audit

A checklist + audit procedure based on the **Game Accessibility Guidelines** (gameaccessibilityguidelines.com) — the international, multi-organization consensus standard maintained by AbleGamers, SpecialEffect, IGDA Game Accessibility SIG, and industry partners.

## The tiering model

GAG defines three tiers:
- **Basic** — low cost, broad benefit. Ship-gate for any commercial release.
- **Intermediate** — moderate cost, focused benefit. Recommended for games targeting broad audiences.
- **Advanced** — high cost, specific benefit. Required for the strongest accessibility posture; common in AAA.

**This skill enforces Basic as a ship gate.** Intermediate and Advanced are recommended based on audience demographics, but Basic is the minimum.

---

## Basic-tier ship-gate checklist

A game cannot ship without meeting every Basic-tier item below. Each item names the disability category, the requirement, and the test.

### Motor / Mobility

| # | Requirement | Test |
|---|---|---|
| M1 | Option to adjust game speed | Settings menu has a speed slider, or per-mechanic difficulty exists |
| M2 | Toggle/slider for haptics | Vibration / rumble can be disabled |
| M3 | Interactive elements large and well-spaced | UI buttons ≥ 44×44 dp / 48×48 px touch target, with margins |
| M4 | Sensitivity adjustment | Stick / mouse / aim sensitivity is configurable |
| M5 | All UI accessible from one input method | Player never needs both keyboard *and* mouse simultaneously for menus; gamepad-only path exists |
| M6 | Simple controls or a simpler alternative | Game offers a reduced-input control scheme OR is single-input by design |
| M7 | Remappable controls | Every input action can be rebound (no fixed bindings for core actions) |

### Cognitive

| # | Requirement | Test |
|---|---|---|
| C1 | No seizure triggers — no flashing > 3 Hz | Photosensitive epilepsy check: any flash sequence rate < 3 flashes/sec, low red component |
| C2 | Self-paced text — no auto-advance | Dialog and tutorial text wait for input |
| C3 | Interactive tutorials, not text walls | Tutorialization teaches by doing |
| C4 | Simple clear language | Localization-friendly, no jargon at the system level |
| C5 | Game starts without nested menus | Title screen → 1 or 2 clicks → playing |
| C6 | Simple clear text formatting | Subtitles use clear font, adequate contrast, no decorative-only text |
| C7 | Readable default font size | Default font ≥ 22 px / equivalent — readable from couch distance |

### Vision

| # | Requirement | Test |
|---|---|---|
| V1 | High contrast between text/UI and background | WCAG AA-equivalent contrast for UI text |
| V2 | Simple clear text formatting | (same as C6) |
| V3 | Readable default font size | (same as C7) |
| V4 | Avoid VR simulation sickness triggers | If VR: no forced rapid yaw, no fixed-camera induced motion, vignetting on locomotion |
| V5 | No essential info conveyed by color alone | Colorblind test: red/green important info pair has shape, icon, or text differentiator |
| V6 | Interactive elements large and well-spaced | (same as M3) |

### Hearing

| # | Requirement | Test |
|---|---|---|
| H1 | If subtitles used, present clearly | Background panel or stroke, adequate contrast, font ≥ 22 px |
| H2 | No essential info conveyed by sound alone | Visual cue exists for any audio-only mechanic (e.g., enemy approach) |
| H3 | Separate volume controls (FX / speech / music) | Three independent sliders minimum |
| H4 | Subtitles for all important speech | Every cutscene line, every important NPC line, has subtitles |

### General

| # | Requirement | Test |
|---|---|---|
| G1 | Solicit accessibility feedback | In-game or website channel for accessibility reports |
| G2 | All settings saved/remembered | Audio, video, control, accessibility settings persist across sessions and per-profile |
| G3 | In-game accessibility feature list | Settings screen labels accessibility features clearly OR has dedicated Accessibility tab |
| G4 | Accessibility features on packaging/website | Store page lists supported features (subtitles, remap, colorblind, etc.) |
| G5 | Wide difficulty range | At least 3 named difficulties OR continuous difficulty modifier OR accessibility-style assist mode |

---

## Strongly recommended (Intermediate-tier highlights)

Not ship-gate, but ship without these and accessibility advocates will notice:

- **Autosave feature** — players with inconsistent play sessions need recovery.
- **Macro / no-repeated-input alternative** — eliminate button mashing where possible.
- **Avoid button-holding** as a sole input requirement.
- **Adjustable contrast.**
- **Cursor / crosshair customization** (color, size).
- **Speaker identification in subtitles** ("ALICE: Hello.").
- **Background-sound captions** ("[engine starts]").
- **Text chat for multiplayer.**
- **Visual indication of direction of significant audio** (footsteps behind you).
- **Progress summaries / control reminders / objective reminders** — restore context for interrupted play.
- **Assist mode** (auto-aim, slowdown, infinite air) — *Celeste*'s Assist Mode is the gold standard; let the player tune the difficulty axis-by-axis.

## Strongly recommended (Advanced highlights)

For projects aiming for best-in-class accessibility:

- **Screen reader support** in menus.
- **Audio description track.**
- **Font size slider.**
- **Switch / eye-tracking compatibility.**
- **Profile-level settings** (couch co-op with siblings, parent + child).
- **Cool-down (post-acceptance delay) between inputs** for tremor support.
- **Hide non-interactive UI elements** option (declutter for cognitive load).
- **Replayable narrative** — let the player re-hear tutorial or cutscene lines.

---

## Common false economies (myths to refute)

- **"Subtitles ruin immersion."** They don't. They are non-negotiable for shipping. Default on for non-native-language audio. Default off is acceptable; default unavailable is not.
- **"Difficulty options ruin the artistic vision."** *Celeste* shipped one of the most acclaimed accessibility implementations *and* won a BAFTA. The vision argument is unsupported by data.
- **"Colorblind mode requires a complete art pass."** False. Most colorblind support is *adding shape/icon differentiation* in addition to color. Cheap.
- **"Remap is a huge engineering effort."** True if the engine wasn't designed for it. Bake remap support from day one — retrofitting is the expensive case.
- **"We'll add accessibility post-launch."** Doesn't happen. Bake it in or it won't ship.

## When Basic-tier deferral is reasonable

Small jam games, prototypes, art-piece projects intentionally targeting a constrained experience — these may legitimately defer parts of the Basic checklist. **Document the deferral explicitly** in the project README so audience expectations are calibrated.

For any commercial release, Basic-tier is non-negotiable.

## Procedure (when running an audit)

1. **Scope the audit.** Commercial release, prototype, jam game? This determines whether Basic-tier is a ship-gate or a recommendation.
2. **Walk each Basic-tier item.** Pass/fail/partial for each. If partial, identify the specific gap.
3. **Stress-test photosensitivity (C1).** Any rapid flashing? Any high-red strobing? Test with the Harding flash analyzer or PEAT (Photosensitive Epilepsy Analysis Tool) if practical.
4. **Stress-test colorblind (V5).** Convert screenshots to deuteranopia / protanopia / tritanopia simulations. Are critical-path objects still distinguishable?
5. **Run a remap-only session.** Try playing the game with all default controls rebound to non-default keys. Do button prompts update? Does anything break?
6. **Validate subtitle quality (H1, H4).** Run a 5-minute scene with audio muted. Can you follow the plot?
7. **Persistence check (G2).** Quit, relaunch, verify every setting persisted.
8. **Output a severity-ranked report:**
   - **HARD** — Basic-tier failures that block ship.
   - **SOFT** — Basic-tier partials and Intermediate-tier gaps recommended for audience.
   - **POLISH** — Advanced-tier opportunities.

## Sources

- Game Accessibility Guidelines — https://gameaccessibilityguidelines.com/full-list/
- AbleGamers — accessibility consulting (resources at https://ablegamers.org/).
- SpecialEffect — UK accessibility charity.
- IGDA Game Accessibility SIG — special interest group.
- *Celeste* — Maddy Thorson, *Assist Mode* design rationale (case study).
- W3C WCAG 2.2 — color/contrast underpinning.

When this gets stale: re-fetch gameaccessibilityguidelines.com Basic-tier section. The tier model is stable; specific items have evolved.
