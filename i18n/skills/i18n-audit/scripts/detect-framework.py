#!/usr/bin/env python3
"""Detect the i18n framework(s) in use in a project.

Outputs JSON to stdout. Multiple frameworks may be reported for monorepos.

Detection is by file signature, not by heuristics — we look for canonical
catalog file locations and config files. False positives are unlikely; false
negatives mean the project uses a framework we don't know about.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "target", "build", "dist",
    ".gradle", ".dart_tool", ".venv", "venv", "__pycache__",
    ".next", ".nuxt", ".cache", ".idea", ".vscode",
}


def walk(root: Path, max_depth: int = 6):
    root = root.resolve()
    base_depth = len(root.parts)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(p in SKIP_DIRS for p in rel_parts):
            continue
        if len(rel_parts) > max_depth:
            continue
        yield path


def detect(root: Path) -> list[dict]:
    findings: list[dict] = []
    files = list(walk(root))
    paths = [str(f.relative_to(root)) for f in files]

    # Android — strings.xml under res/values*/
    android_strings = [p for p in paths if re.search(r"(^|/)res/values[^/]*/strings\.xml$", p)]
    if android_strings:
        locales = sorted({
            (re.search(r"res/values(-[a-zA-Z0-9_-]+)?/strings\.xml$", p).group(1) or "")[1:] or "en"
            for p in android_strings
        })
        findings.append({
            "framework": "android-strings-xml",
            "catalog_glob": "**/res/values*/strings.xml",
            "source_locale": "en",
            "target_locales": [l for l in locales if l != "en"],
            "files_seen": len(android_strings),
        })

    # iOS — .strings or .stringsdict under *.lproj/, or .xcstrings file
    ios_strings = [p for p in paths if re.search(r"\.lproj/[^/]+\.(strings|stringsdict)$", p)]
    xcstrings = [p for p in paths if p.endswith(".xcstrings")]
    if ios_strings or xcstrings:
        locales = sorted({
            re.search(r"([a-zA-Z0-9_-]+)\.lproj/", p).group(1)
            for p in ios_strings
        })
        findings.append({
            "framework": "ios-strings" if not xcstrings else "ios-xcstrings",
            "catalog_glob": "**/*.lproj/*.strings*" if not xcstrings else "**/*.xcstrings",
            "source_locale": "en" if "en" in locales or not locales else (locales[0] if locales else "en"),
            "target_locales": [l for l in locales if l != "en"],
            "files_seen": len(ios_strings) + len(xcstrings),
        })

    # Flutter / Dart — .arb under lib/l10n/ or l10n/
    arb_files = [p for p in paths if p.endswith(".arb")]
    if arb_files:
        locales = sorted({
            m.group(1) for p in arb_files
            if (m := re.search(r"_(\w+)\.arb$", p))
        })
        findings.append({
            "framework": "flutter-arb",
            "catalog_glob": "**/*.arb",
            "source_locale": "en",
            "target_locales": [l for l in locales if l != "en"],
            "files_seen": len(arb_files),
        })

    # gettext .po / .pot
    po_files = [p for p in paths if p.endswith(".po")]
    pot_files = [p for p in paths if p.endswith(".pot")]
    if po_files or pot_files:
        locales = sorted({
            m.group(1) for p in po_files
            if (m := re.search(r"locale[s]?/([a-zA-Z_]+)/", p)) or
               (m := re.search(r"/([a-zA-Z_]+)\.po$", p))
        })
        # Django signature
        is_django = any("LC_MESSAGES" in p for p in po_files)
        framework = "django-gettext" if is_django else "gettext"
        findings.append({
            "framework": framework,
            "catalog_glob": "**/*.po",
            "source_locale": "en",
            "target_locales": [l for l in locales if l != "en"],
            "files_seen": len(po_files),
        })

    # Rails YAML
    rails_yml = [p for p in paths if re.search(r"config/locales/.+\.ya?ml$", p)]
    if rails_yml:
        locales = sorted({
            m.group(1) for p in rails_yml
            if (m := re.search(r"config/locales/(?:.+\.)?([a-zA-Z_-]+)\.ya?ml$", p))
        })
        findings.append({
            "framework": "rails-yaml",
            "catalog_glob": "config/locales/**/*.yml",
            "source_locale": "en",
            "target_locales": [l for l in locales if l != "en"],
            "files_seen": len(rails_yml),
        })

    # Qt .ts
    qt_ts = [p for p in paths if p.endswith(".ts") and "/translations/" in ("/" + p)]
    if qt_ts:
        locales = sorted({
            m.group(1) for p in qt_ts
            if (m := re.search(r"_([a-zA-Z_]+)\.ts$", p))
        })
        findings.append({
            "framework": "qt-ts",
            "catalog_glob": "**/translations/*.ts",
            "source_locale": "en",
            "target_locales": locales,
            "files_seen": len(qt_ts),
        })

    # .NET .resx
    resx_files = [p for p in paths if p.endswith(".resx")]
    if resx_files:
        locales = sorted({
            m.group(1) for p in resx_files
            if (m := re.search(r"\.([a-zA-Z]{2,3}(?:-[A-Z]{2})?)\.resx$", p))
        })
        findings.append({
            "framework": "dotnet-resx",
            "catalog_glob": "**/*.resx",
            "source_locale": "en",
            "target_locales": locales,
            "files_seen": len(resx_files),
        })

    # Java .properties (i18n-specific naming: messages_xx.properties)
    java_props = [p for p in paths if re.search(r"(messages|i18n|labels|strings|bundle)_[a-zA-Z_]+\.properties$", p, re.I)]
    if java_props:
        locales = sorted({
            m.group(1) for p in java_props
            if (m := re.search(r"_([a-zA-Z_]+)\.properties$", p))
        })
        findings.append({
            "framework": "java-properties",
            "catalog_glob": "**/messages*.properties",
            "source_locale": "en",
            "target_locales": locales,
            "files_seen": len(java_props),
        })

    # i18next / react-intl / vue-i18n — JSON catalogs in locales/ or i18n/
    json_locale_files = []
    for p in paths:
        if not p.endswith(".json"):
            continue
        if re.search(r"(^|/)(locales?|i18n|lang|translations?)/[a-zA-Z_-]+\.json$", p):
            json_locale_files.append(p)
        elif re.search(r"(^|/)(locales?|i18n|lang|translations?)/[a-zA-Z_-]+/[a-zA-Z_.-]+\.json$", p):
            json_locale_files.append(p)
    if json_locale_files:
        # Try to disambiguate via package.json deps
        framework = "json-i18n"  # generic
        pkg_json = root / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "i18next" in deps or "react-i18next" in deps:
                    framework = "i18next"
                elif "react-intl" in deps or "@formatjs/intl" in deps:
                    framework = "react-intl"
                elif "vue-i18n" in deps or "@intlify/vue-i18n" in deps:
                    framework = "vue-i18n"
                elif "next-intl" in deps:
                    framework = "next-intl"
            except (json.JSONDecodeError, OSError):
                pass

        locales = sorted({
            m.group(1) for p in json_locale_files
            if (m := re.search(r"(?:locales?|i18n|lang|translations?)/([a-zA-Z_-]+?)(?:\.json|/)", p))
        })
        findings.append({
            "framework": framework,
            "catalog_glob": "**/locales/**/*.json",
            "source_locale": "en",
            "target_locales": [l for l in locales if l != "en"],
            "files_seen": len(json_locale_files),
        })

    # Vue i18n YAML variant
    vue_yaml = [p for p in paths if re.search(r"(^|/)(locales?|i18n)/[a-zA-Z_-]+\.ya?ml$", p)]
    if vue_yaml and not any(f["framework"] == "vue-i18n" for f in findings):
        pkg_json = root / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "vue-i18n" in deps:
                    locales = sorted({
                        m.group(1) for p in vue_yaml
                        if (m := re.search(r"(?:locales?|i18n)/([a-zA-Z_-]+)\.ya?ml$", p))
                    })
                    findings.append({
                        "framework": "vue-i18n",
                        "catalog_glob": "**/locales/**/*.yml",
                        "source_locale": "en",
                        "target_locales": [l for l in locales if l != "en"],
                        "files_seen": len(vue_yaml),
                    })
            except (json.JSONDecodeError, OSError):
                pass

    return findings


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: detect-framework.py <project-root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    findings = detect(root)
    if not findings:
        print(json.dumps({"framework": "none", "frameworks": []}, indent=2))
        return 0

    print(json.dumps({"frameworks": findings}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
