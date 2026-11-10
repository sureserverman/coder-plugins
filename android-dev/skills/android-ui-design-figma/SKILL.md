---
name: android-ui-design-figma
description: Use when the user asks to change, design, or restyle Android UI — theming, layouts, screens, components, Material 3, Compose, navigation, or launcher/app icon, including Figma integration. Trigger on "redesign this screen", "add a Figma design", "restyle the app", "dark mode".
---

# Android UI Design and Figma Workflow

For a larger change, agree a design spec with concrete values (dp, sp, colors) with the user before coding. With a Figma URL, use the Figma MCP (`get_design_context`, `get_screenshot`). Build and test through the android-gradle-build skill.

## Visual verification loop (screenshot → grade → iterate)

A green build is not a verified design. For any visible change, after build and tests pass:

1. **Capture**: build the debug APK, then capture every changed screen on the emulator stack through the android-mcp-orchestrator skill (`${CLAUDE_PLUGIN_ROOT}/skills/android-mcp-orchestrator/scripts/run.sh`; every up is paired with a down). Typical sequence: `start-android-tablet-emulators` → `install-app-on-emulators` → `capture-emulator-screenshots`.
2. **Grade**: score the captures against the approved spec with [references/ui-grading-rubric.md](references/ui-grading-rubric.md). Its weighted dimensions, pass threshold and fix-list format are defined there.
3. **Iterate**: below threshold, apply the smallest fix for the lowest-scoring dimension, rebuild, re-capture, re-grade. Max 3 iterations; then present to the user with the scores and the remaining fix list.
4. **Present**: only a passing (or escalated) result goes to the user, with screenshots and per-dimension scores.

**The grader never sees the implementation transcript.** The session that wrote the code grades its own work too generously. The grader gets only the approved spec, the rubric and the screenshot paths. In Claude Code, dispatch a separate subagent (e.g. `general-purpose`) with just those three, never the diff or this session's transcript; apply its fix list here and re-dispatch to re-grade. Hosts without the Agent tool run the grading themselves from those three inputs only.

Skip the loop only when the change cannot show in a screenshot or no emulator stack is available, and say so.

## Launcher icon (adaptive — mandatory)

Every app shipped from this plugin must have an adaptive launcher icon:

- foreground + background + monochrome layers;
- both `ic_launcher.xml` and `ic_launcher_round.xml` in `mipmap-anydpi-v26/`;
- legacy PNG fallbacks at all five densities.

Themed icons on Android 13+ and OEM mask shapes both depend on this structure; a legacy single-PNG icon is not acceptable. When the user asks to add or change the app icon, or before publishing (F-Droid, Play), follow the spec, scaffold and verification recipe in [references/adaptive-icons.md](references/adaptive-icons.md). Generate via Android Studio's Image Asset Studio (*New → Image Asset → Launcher Icons (Adaptive and Legacy)*); there is no first-party CLI.
