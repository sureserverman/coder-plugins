# UI Grading Rubric (screenshot evaluation)

Operationalized scoring for Android UI screenshots, graded against the approved
design spec. Four weighted dimensions, each scored 1–5. Design quality and
originality are deliberately weighted up: under-weighting them produces
generic, templated output (per Anthropic's harness-design findings —
https://www.anthropic.com/engineering/harness-design-long-running-apps).

## Dimensions and weights

| Dimension | Weight | What 1 looks like | What 5 looks like |
|---|---|---|---|
| **Design quality** | 30% | No visual identity; colors/typography/layout don't cohere; screens feel unrelated | A coherent visual identity — palette, type, spacing, and shape language reinforce each other across every screen |
| **Originality** | 30% | Default Material baseline untouched (stock purple scheme, default type scale); indistinguishable from a template or AI-generated boilerplate | Deliberate, brand-led decisions — seeded color scheme, distinctive type pairing, characterful component shapes — while staying within Material 3 idiom |
| **Craft** | 20% | Inconsistent spacing, raw hex colors bypassing theme roles, broken type hierarchy, contrast failures | Consistent spacing grid (4dp multiples), all color via `colorScheme` roles, full type-scale hierarchy, WCAG-AA contrast, correct touch-target sizes |
| **Functionality** | 20% | Flows in the spec are missing, truncated, or unreachable in the screenshots; placeholder/stub content visible | Every spec'd element present and usable on phone and tablet captures; states (empty, loading, error) handled where the spec names them |

**Weighted score** = 0.30·DQ + 0.30·O + 0.20·C + 0.20·F.

**Pass threshold:** weighted score ≥ 3.5 **and** no dimension below 3.
Below threshold → return the lowest-scoring dimension's fix list to the
implementation loop (max 3 re-capture cycles, then surface to the user with
scores attached).

## Scoring anchors (1–5)

- **1** — violates the dimension outright; would embarrass the app in a store listing
- **2** — templated/defaulted; nothing broken, nothing chosen
- **3** — competent but safe; some deliberate decisions, others left at defaults
- **4** — coherent and distinctive; minor inconsistencies only
- **5** — polished identity; a designer would sign it

## Calibration examples

### Example A — "generic template" (fails)

Phone screenshots show: default `Purple40/Purple80` dynamic-color fallback,
untouched default type scale, every screen a `Column` of identical `Card`s,
stock icons, no empty states.

| Dimension | Score | Why |
|---|---|---|
| Design quality | 2 | Screens are consistent only because everything is default |
| Originality | 1 | Zero decisions beyond the project template |
| Craft | 3 | Spacing/theming technically correct — because nothing was customized |
| Functionality | 4 | All spec'd flows reachable; empty states missing |

Weighted: 0.30·2 + 0.30·1 + 0.20·3 + 0.20·4 = **2.3 → iterate.**
Fix list (lowest dimension first): seed a brand color scheme; choose a type
pairing; differentiate list/detail/settings layouts.

### Example B — "coherent identity" (passes)

Screenshots show: brand-seeded light/dark color scheme used via roles, a
display/body type pairing with clear hierarchy, an 8dp rhythm, distinctive
large-corner cards on browse vs. dense rows on manage screens, empty and error
states present.

| Dimension | Score | Why |
|---|---|---|
| Design quality | 4 | Palette, type, and shape language agree across screens |
| Originality | 4 | Deliberate choices everywhere; still recognizably Material 3 |
| Craft | 4 | One spacing inconsistency on the settings screen |
| Functionality | 5 | All spec'd flows + states present on phone and tablet |

Weighted: 0.30·4 + 0.30·4 + 0.20·4 + 0.20·5 = **4.2 → pass.**

## How the evaluator uses this

1. Receive ONLY: the approved design spec, this rubric, and the captured
   screenshots (phone + tablet). Never the implementation transcript or diff —
   external judgment, not self-assessment.
2. For each changed screen, compare screenshot against the spec's section for
   that screen; score the four dimensions with one-line justifications.
3. Report: per-dimension scores, weighted total, pass/iterate verdict, and —
   on iterate — a concrete fix list ordered by lowest-scoring dimension.
4. Score what is visible. If a spec'd flow can't be verified from the captures
   (e.g. needs interaction beyond the capture set), say so explicitly rather
   than assuming it works.
