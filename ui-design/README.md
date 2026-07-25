# ui-design

Five per-platform UI subagents — one expert per surface — that design, review, and facelift interfaces against the platform's *own* guidelines rather than a generic notion of good design. They share one protocol shape, so switching surfaces doesn't mean learning a new interaction; what changes is the design system each one cites and defends.

## Install

```text
/plugin install ui-design@coder-plugins
```

No external dependencies. Each agent reads your source to detect the surface it's working on.

> **Android UI is not here.** It lives in `android-dev` as `ui-android`, because Android UI work is inseparable from the Gradle/Compose build tooling that plugin owns. If you came looking for it, install `android-dev`.

## The five agents

All five are pinned to `sonnet` and carry the same tools — `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`, `WebFetch`, `TaskCreate`, `TaskUpdate`. They can edit and write source, so scope your request to the files you mean.

| Agent | Surface | Cites and defends |
|---|---|---|
| **`ui-web`** | Web UIs, framework-agnostic | WCAG 2.2 AA, WAI-ARIA APG, semantic HTML, Nielsen Norman heuristics |
| **`ui-gnome`** | GNOME / Ubuntu desktop, GTK4 | GNOME HIG, libadwaita, adaptive layouts |
| **`ui-macos`** | macOS, SwiftUI / AppKit | Apple HIG, menu-bar-first conventions |
| **`ui-windows`** | Windows 10/11 desktop | Fluent 2, via WinUI 3 / WPF / WinForms |
| **`ui-garmin`** | Garmin Connect IQ, Monkey C | Connect IQ guidelines for watch faces, data fields, widgets, glances — power-budget and device-matrix aware |

**How they fire.** Three ways:

- **Automatic delegation** on a matching request — "design a GNOME app", "accessibility audit", "SwiftUI facelift", "libadwaita migration", "design a watch face".
- **Direct request** — "have `ui-web` run an accessibility audit on `src/checkout/`".
- **From plan execution** — `planning`'s `dispatching-parallel-agents` selects the right one from the task's stack signal via `references/stack-routing.md` (GTK4 → `ui-gnome`, WCAG/a11y → `ui-web`, `*.mc`/`monkey.jungle` → `ui-garmin`, and so on). `planning:applying-design-handoff` also delegates cross-platform implementation to whichever agent matches the target.

### The six protocols (identical across all five)

Each agent announces its protocol before acting. They compose.

| # | Protocol | Input | Output |
|---|---|---|---|
| 1 | **Surface detection** | an unfamiliar codebase | what UI toolkit, version, and layout conventions are actually in use — run before any judgment |
| 2 | **Design review** | existing UI | findings against the platform's named guidelines, not generic taste |
| 3 | **Facelift** | UI that works but looks dated | incremental changes that respect the existing structure |
| 4 | **Greenfield** | a new surface | a design built to the platform's conventions from the start |
| 5 | **Accessibility audit** | any UI | contrast, focus order, semantics, assistive-technology behavior |
| 6 | **Coach** | "why this way?" | a cited explanation, with tradeoffs where the guidance is contested |

Protocol 1 runs first on anything unfamiliar — a review that assumes the wrong toolkit produces confident, wrong advice.

## Artifacts

**None persisted as reports.** Reviews and audits come back in the conversation; the agents write to disk only when a facelift or greenfield protocol edits your actual source files. If you want a UI/UX readiness verdict recorded durably, `planning:project-maturity` owns that axis.

## Worked example

```text
/plugin install ui-design@coder-plugins

"audit the settings window for accessibility — it's a GTK4 app"
```

`ui-gnome` runs Protocol 1 (confirms GTK4 + libadwaita and the adaptive breakpoints in use), then Protocol 5, reporting focus-order and contrast findings against the GNOME HIG by section — not against generic WCAG numbers that may not match the platform's own guidance.

```text
"now facelift it to match"
```

Protocol 3 edits the source incrementally, preserving the existing widget structure rather than rewriting the window.

## Related plugins

- **`android-dev`** — ships the sixth surface, `ui-android` (Compose / Material 3).
- **`planning`** — `applying-design-handoff` delegates per-platform implementation to these agents when reproducing a Claude Design handoff pack; `dispatching-parallel-agents` routes by stack signal; `project-maturity` records the UI/UX axis.
- **`browser-extensions`** — extension UI is web UI; pair with `ui-web`.
