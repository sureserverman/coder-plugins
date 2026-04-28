# Android UI Best Practices and Trends

Reference for the android-ui-design-figma skill. Use when choosing design direction and concrete values.

## Material Design 3 (M3)

- **Prefer M3** for new or refreshed apps. Do not mix M2 and M3 long-term.
- **Material 3 Expressive**: Emotion-driven UX—vibrant color, clear motion, adaptive components, flexible typography, contrasting shapes. Use for distinctive, modern apps.
- **Design tokens**: Use M3 color roles (primary, secondary, tertiary, surface, error, outline, etc.), type scale roles, and shape tokens. Map Figma variables to these when implementing.
- **Resources**: [m3.material.io](https://m3.material.io/) — foundations (color, typography, layout), components, and Figma design kits.

## Typography

- **Roles over raw sizes**: Prefer type roles (e.g. headline, body, label) so scaling and accessibility stay consistent.
- **Variable fonts (M3)**: Weight and width axes for motion and hierarchy; use sparingly for impact.
- **Legibility**: Minimum touch target 48dp; body text large enough for readability (e.g. 14–16sp body).
- **Numerals**: Use the numerals type role for numbers that don’t need localization (e.g. stats, scores).

## Layout and Spacing

- **Spacing scale**: Use a consistent scale (e.g. 4dp base: 4, 8, 12, 16, 24, 32, 48). M3 provides layout and spacing guidance.
- **Insets**: Respect system bars and gesture nav; use `WindowInsets` and Compose `WindowInsets` for padding.
- **Grid and alignment**: Align to a simple grid; avoid one-off margins. Use `Column`/`Row` with consistent spacing in Compose.

## Color and Theme

- **Scheme**: Define light and dark schemes; use semantic roles (primary, surface, error, etc.) instead of raw hex in UI code.
- **Contrast**: Meet WCAG for text and controls; check focus and disabled states.
- **Accent**: One clear primary/accent; use secondary and tertiary for hierarchy, not decoration.

## Components and Patterns

- **Bottom nav / navigation bar**: Standard patterns for 3–5 destinations; use M3 components.
- **FAB**: One primary action per screen; consider extended FAB when the label helps.
- **Cards and lists**: Consistent elevation/surface; clear tap targets and optional states (selected, disabled).
- **Dialogs and sheets**: Modal vs bottom sheet by context; respect safe areas and keyboard.

## Motion and Feedback

- **Duration**: Short (100–300ms) for micro-interactions; longer for transitions (300–500ms).
- **Easing**: Use standard curves (e.g. emphasized decelerate) for consistency.
- **Feedback**: Ripple or state change on tap; loading/skeleton for async content.

## Trends (2024–2025)

- **Generous spacing and clarity**: Less density, more breathing room.
- **Bold color and personality**: Strong primary colors and expressive M3; avoid generic purple-on-white.
- **Rounded and shape**: Consistent corner radius (e.g. 12dp, 16dp) and M3 shape tokens.
- **Dark theme by default**: Support both; consider dark-first for some audiences.
- **Accessibility**: Large touch targets, readable contrast, and optional reduced motion.

## Implementation Notes

- **Compose**: Prefer `MaterialTheme.colorScheme`, `MaterialTheme.typography`, `MaterialTheme.shapes`; avoid hardcoded colors/sizes in composables.
- **Views**: Use `?attr/colorPrimary` and theme attributes; keep dimensions in `dimens.xml` or theme.
- **Figma**: Map Figma variables to M3 tokens or project tokens when applying design to code.
