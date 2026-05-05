# Adaptive Launcher Icons (mandatory)

Every Android app shipped from this plugin **must** ship an adaptive launcher
icon (Android 8.0 / API 26+). Legacy single-PNG `ic_launcher` only is not
acceptable: themed icons (Android 13+) and OEM mask shapes both depend on the
adaptive structure.

Authoritative source: developer.android.com — "Create app icons" (Image Asset
Studio) and the Android 8.0 / Android 13 features pages. This file is a
distilled spec; when in doubt, re-fetch the live docs.

## Required output

Three layers, each a vector drawable when possible:

- **Foreground** — the logo / glyph. Transparent background. Lives within the
  72×72dp safe zone of the 108×108dp canvas.
- **Background** — solid color or simple pattern. Fills the full 108×108dp.
- **Monochrome** — single-color silhouette of the foreground for Android 13+
  themed icons. Same safe-zone rules.

The OS applies the mask shape (circle, squircle, rounded-square, teardrop) per
device — apps **must not pre-mask** their assets.

## Canvas and safe zone

| Region | Size | Use |
|---|---|---|
| Total canvas | 108×108 dp | All three layers |
| Visible safe zone | 72×72 dp (centered) | Logo / important content here |
| Mask reserve | 18 dp on each side | Reserved for OEM masking — do not place meaningful content here |
| Worst-case mask | 66 dp diameter circle | Design for this for full compatibility |

## Required files

```
res/
  drawable/
    ic_launcher_foreground.xml          # vector, 108×108dp viewport
    ic_launcher_background.xml          # vector OR a <color> in colors.xml
    ic_launcher_monochrome.xml          # vector, 108×108dp viewport (single tint)
  mipmap-anydpi-v26/
    ic_launcher.xml                     # adaptive declaration (below)
    ic_launcher_round.xml               # same content as ic_launcher.xml
  mipmap-mdpi/    ic_launcher.png       #  48×48 px legacy fallback
  mipmap-hdpi/    ic_launcher.png       #  72×72 px
  mipmap-xhdpi/   ic_launcher.png       #  96×96 px
  mipmap-xxhdpi/  ic_launcher.png       # 144×144 px
  mipmap-xxxhdpi/ ic_launcher.png       # 192×192 px
  # plus matching ic_launcher_round.png in each density bucket
```

`mipmap-anydpi-v26/ic_launcher.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
    <monochrome android:drawable="@drawable/ic_launcher_monochrome"/>
</adaptive-icon>
```

`AndroidManifest.xml`:

```xml
<application
    android:icon="@mipmap/ic_launcher"
    android:roundIcon="@mipmap/ic_launcher_round"
    ...>
```

## Generation tool: Image Asset Studio (canonical)

Android Studio is the only first-party generator. There is no CLI equivalent.

1. Right-click `res/` → **New → Image Asset**.
2. **Icon Type:** *Launcher Icons (Adaptive and Legacy)*.
3. Provide foreground source (SVG / PNG / clip art / text). Trim and pad until
   the live preview shows the logo fully inside every mask shape (circle,
   squircle, rounded-square, teardrop) with comfortable margin.
4. Set background as a solid color or another asset.
5. **Switch to the Monochrome tab.** Provide the same glyph as a single-color
   vector. The wizard does not auto-generate it from the foreground — skipping
   this step silently breaks themed icons on Android 13+.
6. Confirm. The wizard writes all `mipmap-*` PNGs, the two
   `mipmap-anydpi-v26/*.xml` files, and the three `drawable/*.xml` layers.

When Image Asset Studio is not available (CI, headless, or working from
Figma exports), hand-write the three vector drawables and the
`adaptive-icon` XML following the structure above, then generate the
legacy-PNG fallbacks at the five densities listed.

## Verification recipe

Run from the Android module root. All four checks must pass:

```bash
# 1. Adaptive declaration exists with all three layers.
test -f src/main/res/mipmap-anydpi-v26/ic_launcher.xml \
  && grep -q '<background'  src/main/res/mipmap-anydpi-v26/ic_launcher.xml \
  && grep -q '<foreground'  src/main/res/mipmap-anydpi-v26/ic_launcher.xml \
  && grep -q '<monochrome'  src/main/res/mipmap-anydpi-v26/ic_launcher.xml \
  || echo "FAIL: adaptive icon missing a layer"

# 2. Round variant exists (some launchers force it).
test -f src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml \
  || echo "FAIL: ic_launcher_round.xml missing"

# 3. Legacy PNG fallbacks present for all five densities.
for d in mdpi hdpi xhdpi xxhdpi xxxhdpi; do
  test -f "src/main/res/mipmap-$d/ic_launcher.png" \
    || echo "FAIL: mipmap-$d/ic_launcher.png missing"
done

# 4. Manifest references both icon and roundIcon.
grep -q 'android:icon="@mipmap/ic_launcher"'        src/main/AndroidManifest.xml \
  && grep -q 'android:roundIcon='                   src/main/AndroidManifest.xml \
  || echo "FAIL: manifest icon attrs missing"
```

## Common mistakes

- **Pre-masking the foreground** (drawing a circle around the logo). The OEM
  mask then double-clips, leaving a small icon inside a ring.
- **Logo touches the 18dp mask reserve.** Looks fine on a square mask, gets
  beheaded on circle/teardrop. Fix: pad the foreground until the entire glyph
  fits the 66dp worst-case circle.
- **Monochrome layer omitted.** Themed icons fail silently on Android 13+ — the
  launcher falls back to a desaturated default, looking outdated.
- **Monochrome layer copied from foreground with colors intact.** The OS only
  reads the alpha channel — multi-color glyphs flatten unpredictably. Fix:
  collapse to a single solid fill (any color; alpha is what matters).
- **Hardcoded white background.** Vanishes on themed light surfaces. Use a
  branded color or a vector pattern.
- **Only `mipmap-anydpi-v26` provided, no PNG fallbacks.** App still installs
  on API 25 and below but shows the system default icon there.

## Play Store / F-Droid implications

- **Google Play store-listing icon** (`fastlane/.../images/icon.png`, 512×512
  PNG, no transparency) is a **separate asset** from the in-APK launcher icon.
  Both must exist. Play does not synthesize one from the other.
- **F-Droid** also reads the in-APK adaptive icon for the catalog entry. An
  app shipped without an adaptive icon renders as a generic gray square in
  the F-Droid client even if `fastlane/.../images/icon.png` is set.
