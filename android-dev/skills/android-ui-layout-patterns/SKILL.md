---
name: android-ui-layout-patterns
description: >
  Jetpack Compose layout patterns and Material 3 styling rules.
  Use when building or fixing Android UI layouts with Compose, spacing, cards, grids, or alignment.
---

# Android UI Layout Patterns (Jetpack Compose)

Common Compose layout patterns, spacing rules, and Material 3 styling for this project's Android apps.

## Layout Primitives

### Column / Row
- Use `verticalArrangement = Arrangement.spacedBy(8.dp)` instead of manual Spacer() between items
- Use `horizontalAlignment = Alignment.CenterHorizontally` on Column for centered content
- Prefer `Arrangement.spacedBy()` over repeated `Spacer(modifier = Modifier.height(X.dp))`

### LazyVerticalGrid
- `GridCells.Fixed(3)` for level/card selection screens
- Unify cell heights (e.g., `40.dp`) to prevent jagged grids
- Use `contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)`

### Card
- `Card(elevation = CardDefaults.cardElevation(defaultElevation = 2.dp))`
- Inner padding: `Modifier.padding(12.dp)` inside the card
- Outer spacing via parent's `Arrangement.spacedBy()`

### Scaffold
- Always pass `innerPadding` from Scaffold to content:
  ```kotlin
  Scaffold { innerPadding ->
      Column(Modifier.padding(innerPadding)) { ... }
  }
  ```
- TopAppBar, BottomBar, and FAB go in Scaffold parameters, not in content

## Spacing Rules

| Context | Value |
|---|---|
| Screen edge padding | 16.dp |
| Between cards/items | 8.dp |
| Inside card padding | 12.dp |
| Between sections | 16.dp |
| Icon-to-text gap | 8.dp |
| Grid cell height (uniform) | 40.dp |

## Common Mistakes

1. **Nested scrolling** — LazyColumn inside a scrollable Column crashes. Use `item {}` blocks inside LazyColumn instead.
2. **Missing innerPadding** — Content under TopAppBar is hidden if Scaffold's innerPadding is ignored.
3. **Hardcoded sizes** — Use `fillMaxWidth()` and `weight()` instead of fixed dp widths for responsive layouts.
4. **Manual spacing** — Using `Spacer()` between every item instead of `Arrangement.spacedBy()`.
5. **Compact mode** — Detect with `WindowSizeClass` and adjust grid columns (3 on phone, 4+ on tablet).

## Modifier Order

Order matters. Apply in this sequence:
```kotlin
Modifier
    .fillMaxWidth()       // size first
    .padding(16.dp)       // outer padding
    .background(color)    // background
    .clip(shape)          // shape
    .clickable { }        // interaction
    .padding(12.dp)       // inner padding (after background)
```
