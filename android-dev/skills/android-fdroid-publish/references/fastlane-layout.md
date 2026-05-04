# Fastlane metadata layout for F-Droid

F-Droid reads store-listing copy from the app's **source repo** using the standard fastlane structure. The layout below also works for Google Play (via `fastlane supply`) and IzzyOnDroid, so getting it right once unlocks all three channels.

## Directory shape

```
fastlane/
└── metadata/
    └── android/
        ├── en-US/                              # default locale, REQUIRED
        │   ├── title.txt
        │   ├── short_description.txt
        │   ├── full_description.txt
        │   ├── changelogs/
        │   │   ├── 1.txt                       # filename = versionCode
        │   │   ├── 2.txt
        │   │   └── ...
        │   └── images/
        │       ├── icon.png                    # 512×512, no transparency
        │       ├── featureGraphic.png          # 1024×500 (Play required, F-Droid optional)
        │       ├── promoGraphic.png            # 180×120 (legacy, optional)
        │       ├── tvBanner.png                # 1280×720 (Android TV only)
        │       ├── phoneScreenshots/
        │       │   ├── 01_login.png            # numeric prefix controls order
        │       │   ├── 02_main.png
        │       │   └── ...
        │       ├── sevenInchScreenshots/       # 7" tablet
        │       ├── tenInchScreenshots/         # 10" tablet
        │       └── tvScreenshots/              # Android TV
        ├── de-DE/                              # any number of additional locales
        │   └── ...
        └── fr-FR/
            └── ...
```

## Per-file constraints

| File | Hard limit | Soft rule | Notes |
|---|---|---|---|
| `title.txt` | 50 chars (Play); F-Droid truncates at ~50 | One line, no markdown | F-Droid stores this as `Name:` if missing from YAML |
| `short_description.txt` | 80 chars | One line, plain text, don't repeat the app name | Shown on F-Droid list view and Play Store search results |
| `full_description.txt` | 4000 chars | Plain text or restricted HTML (`<b>`, `<i>`, `<u>`, `<br>`, `<a>`) | No "5-star review" calls-to-action, no Play Store links, no IAP language |
| `changelogs/<versionCode>.txt` | 500 chars | One file per release; missing files render as blank version notes | F-Droid keys by `versionCode`, NOT `versionName` |
| `images/icon.png` | 1 MB | Exactly 512×512 PNG, no transparency, no rounded corners | Don't pre-mask — Play and F-Droid clip themselves |
| `images/featureGraphic.png` | 15 MB | Exactly 1024×500 PNG/JPEG | Required by Play, optional on F-Droid; do it once and reuse |
| `phoneScreenshots/*.png` | 8 MB each, 2–8 images | 320–3840 px each side, aspect ratio 1:2 to 2:1 | Numeric filename prefixes (`01_`, `02_`) control order |
| `sevenInchScreenshots/*.png` | same | 1024×600 typical | Optional but improves tablet listing on Play |
| `tenInchScreenshots/*.png` | same | 1280×720 typical | Optional; Play surfaces on tablet-form devices |

## Locale codes

F-Droid uses BCP 47 codes. Common ones:

| Code | Language | Code | Language |
|---|---|---|---|
| `en-US` | English (US) | `pt-BR` | Portuguese (Brazil) |
| `en-GB` | English (UK) | `pt-PT` | Portuguese (Portugal) |
| `de-DE` | German | `ru-RU` | Russian |
| `fr-FR` | French | `zh-CN` | Chinese (simplified) |
| `es-ES` | Spanish (Spain) | `zh-TW` | Chinese (traditional) |
| `es-419` | Spanish (Latin America) | `ja-JP` | Japanese |
| `it-IT` | Italian | `ko-KR` | Korean |
| `nl-NL` | Dutch | `ar` | Arabic |
| `pl-PL` | Polish | `tr-TR` | Turkish |

If a locale folder is missing a file, F-Droid falls back to `en-US`. So you can ship the screenshots only in `en-US` and translate just the text files.

## Conventions worth following

- Keep `en-US` complete and authoritative. Other locales are diffs against it.
- Numeric screenshot prefixes (`01_`, `02_`) are sortable and avoid surprises in stores that order alphabetically.
- Don't store source files (Figma exports, Sketch files) in `fastlane/`. Keep them in `design/` or `docs/design/` and only commit the rendered PNG/JPEG.
- One `changelogs/<versionCode>.txt` per release, even if the change is metadata-only — without it, the version's release notes render blank.
- `featureGraphic.png` and `icon.png` are referenced on every store page. Never overwrite them in a hurry; old client caches will show the old version for days.
