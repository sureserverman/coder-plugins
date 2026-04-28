---
name: android-ui-design-figma
description: Use when the user asks to change, design, or restyle Android UI — theming, layouts, screens, components, Material 3, Compose, Views, navigation, typography, colors, spacing, or Figma integration for an Android app. Trigger on "redesign this screen", "add a Figma design", "restyle the app", "dark mode", "this screen feels cramped", "make the app look more modern", a screenshot showing a UI issue, or any UI/UX change request for Android.
---

# Android UI Design and Figma Workflow

End-to-end workflow: **standard-first implementation → analyze app → design (spec + Figma when needed) → feedback → amend → apply to app.**

## Core principle: Standard first, DIY only when necessary

Before implementing any design, UI, UX, or layout change:

1. **Check for a standard solution**: Prefer official or widely adopted APIs, components, and patterns. See [references/android-ui-practices.md](references/android-ui-practices.md) and [references/standard-tools-frameworks.md](references/standard-tools-frameworks.md).
2. **Use the standard way**: If a standard component, API, or framework exists and fits the need (Material 3, Compose Material, AndroidX, platform APIs), use it. Do not reimplement what the platform or library already provides.
3. **DIY only when no standard fits**: Build custom views, composables, or layouts only when there is no suitable standard (or the requirement explicitly demands a one-off design). Document why the custom approach was chosen.

Apply this at every step: theming, components, layout, navigation, motion, accessibility.

## Prerequisites

- Android project in the workspace (Gradle, Compose or Views).
- For Figma: Figma MCP server connected. User can create frames in Figma from the spec and share a file URL, or use the remote Figma MCP `generate_figma_design` only for web/captured UI (not for Android screens).
- When applying code: follow the android-gradle-build skill for build and test steps (Gradle, tests, security gates).

## Phase 1: Analyze the App (scale with scope)

- **Small change** (one component, one screen, one layout tweak): Locate the relevant file(s), note current theme and stack (Compose vs Views), and check [references/standard-tools-frameworks.md](references/standard-tools-frameworks.md) for a standard way to implement the change.
- **Larger change** (multi-screen, theme overhaul, full redesign):
  1. Locate the Android app (module, `AndroidManifest.xml`, entry points).
  2. Map screens and navigation (activities, fragments, Compose destinations).
  3. Inventory UI (screens, dialogs, reusable components).
  4. Capture current design (theme, colors, typography, `themes.xml` / `Color.kt` / Compose theme).
  5. Summarize in a short "Current UI summary" so the design phase is grounded in the real app.

## Phase 2: Apply Best Practices and Create Design

- **Small change** (single component, one layout, one style): Use [references/android-ui-practices.md](references/android-ui-practices.md) and [references/standard-tools-frameworks.md](references/standard-tools-frameworks.md) to pick the standard component or API, then implement. Skip full design spec unless the user asks for one or for Figma.
- **Larger change** (multi-screen, theme, or full redesign):
1. **Use references**: Read both reference files. Prefer solving the request with standard tools; only specify custom work where necessary.
2. **Design direction**: Choose a clear direction (e.g. Material 3 expressive, minimal, brand-led) and list concrete changes: color palette, type scale, spacing, component style, motion. Where possible, name the standard component or API (e.g. `TopAppBar`, `NavigationBar`, `ModalBottomSheet`).
3. **Produce design deliverable**:
   - **Design spec**: Structured markdown (or doc) with sections per screen or flow: layout, components, colors, typography, spacing, key interactions. Include exact values (dp, sp, hex/code colors) so implementation is unambiguous.
   - **Optional Figma**: If the user wants Figma:
     - Provide the spec and, if helpful, reference mockup images (e.g. generated from descriptions) so the user can create or duplicate frames in Figma.
     - If the user later shares a Figma file URL and node IDs, use Figma MCP `get_design_context` and `get_screenshot` to implement or refine the app (see Phase 4). Request "Android" or "Compose" output if the MCP supports it; otherwise translate the returned design context into Compose/Views.
   - **Optional reference images**: For key screens, generating reference images from the spec can help the user or designer recreate the UI in Figma.
4. **Present**: Share the design spec (and any images or Figma instructions) and ask for feedback.

## Phase 3: Feedback and Amendments

1. **Collect feedback**: Ask the user to review the design (in Figma if used, or the spec and images) and list what to change (e.g. "softer colors", "more spacing on the home screen", "different FAB style").
2. **Amend**:
   - Update the design spec with the requested changes (concrete values, not vague wording).
   - If the user edits Figma, they can share updated node IDs or a new URL; then use `get_design_context` / `get_screenshot` again to align the spec or the next implementation step.
3. **Confirm**: Repeat until the user approves the design (spec and/or Figma).

## Phase 4: Apply Design to the App

1. **Source of truth**: Prefer the approved design spec. If the user provides a Figma URL and node ID, use that as the visual reference and fetch `get_design_context` and `get_screenshot` for the relevant frames.
2. **Implementation (standard-first)**:
   - **Before writing custom UI**: For each element (button, card, nav, sheet, theme, etc.), check [references/standard-tools-frameworks.md](references/standard-tools-frameworks.md). Use the standard component or API if it exists and fits; implement custom only when it does not.
   - **Theming**: Use platform/theme APIs: `themes.xml`, `Theme.kt`, `Color.kt`, `Type.kt`, Compose `MaterialTheme` (colorScheme, typography, shapes). Match the spec with theme tokens, not one-off hardcoded values.
   - **Screens and components**: Prefer Material 3 / Compose Material / AndroidX components; extend or customize via parameters and theme. Create new composables or views only when no standard fits.
   - **Consistency**: Apply the same spacing scale, type scale, and color usage across the app using the chosen standard system.
3. **Figma-to-code (when Figma URL is provided)**: Use the implement-design workflow adapted for Android: call `get_design_context(fileKey, nodeId)` and optionally `get_variable_defs` for tokens. Map Figma elements to standard Android/Compose components where possible; translate only the rest. Use `get_screenshot` to validate visually.
4. **Verify**: Run `./gradlew :app:compileDebugKotlin` (or equivalent) and fix any build issues. Run relevant UI or instrumented tests. Do not mark the task complete with failing tests.

## Rules

- **Standard first, DIY only when necessary**: For every design/UI/UX/layout change, use a standard tool, component, or framework when one exists; implement custom only when none fits. See references for standard options.
- **Never invent screens or flows**: Design only for screens and flows that exist (or are explicitly requested) in the app.
- **Spec over vague intent**: Every design change in the spec must be implementable (values, not only descriptions).
- **One source of truth**: Keep the design spec and any Figma file in sync; when the user amends in Figma, update the spec or re-fetch context before changing code.
- **Android stack**: Apply changes in the project’s actual stack (Compose, Views, or mixed). Follow the project’s architecture and the android-gradle-build skill for builds, tests, and F-Droid/store publishing (metadata, fastlane, pipeline).

## Summary Checklist

- [ ] Standard tools/frameworks checked first; DIY used only where no standard fits.
- [ ] App analyzed (depth scaled to scope: single component vs full app).
- [ ] Design spec produced with concrete values and standard component names where applicable; optional reference images or Figma instructions.
- [ ] User feedback gathered and spec (and Figma, if used) updated until approved.
- [ ] Design applied in code using standard components/APIs where possible; Figma context used when URL provided.
- [ ] Build and tests pass before considering the task complete.

## Delegation (Claude Code only)

> **Skip this section unless you are Claude Code.** The Agent tool with
> `subagent_type:` parameters is a Claude Code feature. Codex, Cursor, Gemini,
> OpenCode, and other hosts do not have it — run the full workflow yourself
> instead.

Once the design spec has been approved by the user, producing the actual
Compose code (the "design applied in code" step) is a Sonnet-tier code
generation job. If you are on Opus, delegate the code-write phase to the
`code-generator` subagent (model: sonnet) via the Agent tool with
`subagent_type: code-generator`. Give it:

- the approved design spec (exact values: tokens, spacing, typography,
  component choices),
- the target file paths,
- the Compose/Material 3 version and any project theme/tokens it must honor,
- 2–3 neighbor files so it matches the project's existing conventions,
- the instruction to verify with the project's build/check command (e.g.
  `./gradlew :app:compileDebugKotlin`) before returning.

Keep app analysis, the design spec itself, the user-feedback loop, and any
Figma work in this session — those are where the design judgment lives.
