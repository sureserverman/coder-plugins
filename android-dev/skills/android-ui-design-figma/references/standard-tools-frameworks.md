# Standard Tools and Frameworks for Android UI

Use these before implementing custom (DIY) solutions. Only build custom when no entry below fits the requirement.

## Theming and design tokens

| Need | Standard approach | DIY when |
|------|-------------------|----------|
| Colors, typography, shapes | Material 3 `ColorScheme`, `Typography`, `Shapes` in Compose; `themes.xml` + `?attr/` in Views | Brand requires tokens not mappable to M3 roles |
| Dark/light theme | `MaterialTheme.colorScheme` (Compose), theme night qualifiers (Views) | N/A — use standard |
| Dynamic color (Android 12+) | `dynamicLightColorScheme()` / `dynamicDarkColorScheme()` | N/A — use standard |

## Compose UI (Jetpack Compose)

| Need | Standard approach | DIY when |
|------|-------------------|----------|
| Layout | `Column`, `Row`, `Box`, `LazyColumn`, `LazyRow`, `LazyVerticalGrid` | Complex custom layout (e.g. custom measurement) |
| Material 3 components | `androidx.compose.material3.*`: `Button`, `FilledTonalButton`, `OutlinedButton`, `TextField`, `Card`, `TopAppBar`, `NavigationBar`, `FAB`, `ModalBottomSheet`, `Dialog`, `Chip`, `Switch`, `Slider`, etc. | Design requires behavior/appearance not configurable via modifiers/parameters |
| Lists / grids | `LazyColumn`, `LazyRow`, `LazyVerticalGrid`; `item {}` for headers/footers | Custom layout (e.g. staggered grid, custom recycling) |
| Navigation | Compose Navigation (`NavHost`, `NavController`, `composable()`) | Custom transition or back stack behavior |
| Window insets | `WindowInsets`, `Modifier.windowInsetsPadding()` | N/A — use standard |
| Icons | `Material Icons` (Extended), `ImageVector` | Custom icon set or illustration |
| Animation | `animate*AsState`, `AnimatedVisibility`, `AnimatedContent`, `Transition` | Complex orchestration not achievable with built-ins |

## Views (XML / classic UI)

| Need | Standard approach | DIY when |
|------|-------------------|----------|
| Layout | `ConstraintLayout`, `LinearLayout`, `FrameLayout`, `RecyclerView`, `ViewPager2` | Custom layout logic |
| Material components | Material Components library (`com.google.android.material.*`): `MaterialButton`, `MaterialCardView`, `BottomNavigationView`, `FloatingActionButton`, `TextInputLayout`, `TabLayout`, etc. | Design not achievable via style/theme/attrs |
| Lists | `RecyclerView` + `ListAdapter` or `RecyclerView.Adapter` | Custom layout manager or item animator |
| Theming | `themes.xml`, `styles.xml`, `?attr/colorPrimary`, theme overlays | N/A — use standard |

## Navigation

| Need | Standard approach | DIY when |
|------|-------------------|----------|
| Compose | Navigation Component for Compose (`NavHost`, routes, type-safe args if used) | Custom transition or deep-link handling |
| Views | AndroidX Navigation (`NavController`, fragments or activities as destinations) | N/A — use standard |
| Bottom nav / tabs | `NavigationBar` (Compose), `BottomNavigationView` / `TabLayout` (Views) | Custom tab behavior or appearance |

## Dialogs and sheets

| Need | Standard approach | DIY when |
|------|-------------------|----------|
| Modal dialog | `AlertDialog` (Compose), `MaterialAlertDialogBuilder` (Views) | Custom content/layout beyond what dialog APIs allow |
| Bottom sheet | `ModalBottomSheet` (Compose), `BottomSheetDialogFragment` (Views) | Custom drag/peek behavior or layout |
| Full-screen | Full-screen composable or Activity | N/A — use standard |

## Input and forms

| Need | Standard approach | DIY when |
|------|-------------------|----------|
| Text field | `OutlinedTextField` / `TextField` (Compose), `TextInputLayout` (Views) | Custom validation UI or input type |
| Selection | `DropdownMenuItem`, `ModalBottomSheet` for pickers (Compose); `MaterialButton` + popup (Views) | Custom picker UI |
| Checkbox / switch | `Checkbox`, `Switch` (Compose/Views) | N/A — use standard |

## Loading and feedback

| Need | Standard approach | DIY when |
|------|-------------------|----------|
| Loading indicator | `CircularProgressIndicator`, `LinearProgressIndicator` (Compose); `ProgressBar` (Views) | Custom animation or placement |
| Snackbar / toast | `Snackbar` (Compose), `Snackbar` (Material Views) | Custom positioning or action behavior |
| Ripple / touch feedback | Built-in ripple on Material components | N/A — use standard |

## Accessibility and system UI

| Need | Standard approach | DIY when |
|------|-------------------|----------|
| Content descriptions | `contentDescription` (Compose), `android:contentDescription` (Views) | N/A — use standard |
| Touch targets | Min 48dp; `Modifier.sizeIn(minWidth = 48.dp, minHeight = 48.dp)` or equivalent | N/A — use standard |
| Font scaling | Use `sp` and theme typography; avoid fixed `dp` for text | N/A — use standard |
| Edge-to-edge | `WindowInsets`, `enableEdgeToEdge()` (AndroidX Activity) | N/A — use standard |

## When to use DIY

- No standard component matches the required **behavior** or **visual** (e.g. custom chart, custom control).
- Standard component exists but cannot be styled or composed to meet the design (after checking modifiers, theme, and parameters).
- Requirement explicitly calls for a one-off design that diverges from platform guidelines.

When choosing DIY: implement the minimum custom code, reuse layout primitives (`Column`, `Row`, `Box`, or ViewGroup), and document why the standard approach was not used.
