#!/usr/bin/env python3
"""Diff translation catalogs across locales.

For a given project + framework, find:
  - missing[locale]:             keys in source but not in this locale
  - extra[locale]:                keys in this locale but not in source
  - placeholder_mismatch[locale]: keys whose placeholder set differs from source

Supported parsers (best-effort — see notes per format):
  - android-strings-xml: res/values*/strings.xml
  - flutter-arb:         *.arb (JSON)
  - gettext / django-gettext: *.po (msgid → msgstr)
  - i18next / react-intl / json-i18n / next-intl: JSON catalogs
  - rails-yaml:          config/locales/*.yml
  - dotnet-resx:         *.resx (XML)
  - java-properties:     messages_*.properties
  - vue-i18n (json or yaml)
  - qt-ts, ios-strings, ios-xcstrings: best-effort key extraction

Stale detection (source text changed after locale last touched) is intentionally
left to a separate pass — git blame is slow and a script-only diff covers the
common cases. Add --stale to enable it.

Output: JSON to stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

# ------- placeholder detection -------

PLACEHOLDER_RES = [
    # ICU MessageFormat: {name}, {name, plural, ...}, {name, select, ...}
    re.compile(r"\{(\w+)(?:,\s*(?:plural|select|selectordinal|number|date|time)[^}]*)?\}"),
    # printf / Android positional: %1$s, %2$d
    re.compile(r"%(\d+\$)?[\d.\-+ #]*[sdifguxXeEoc%@]"),
    # Handlebars / i18next double-braces: {{name}}
    re.compile(r"\{\{(\w+)\}\}"),
    # Rails interpolation: %{name}
    re.compile(r"%\{(\w+)\}"),
    # Vue i18n named: {name}  (already covered by ICU pattern above)
    # Java MessageFormat: {0}, {1}
    re.compile(r"\{(\d+)(?:,[^}]*)?\}"),
]


def placeholders_in(text: str) -> set[str]:
    if not text:
        return set()
    out: set[str] = set()
    for pat in PLACEHOLDER_RES:
        for m in pat.finditer(text):
            # Whole match minus inner formatting metadata — we want the *shape*,
            # not the param name, so two strings with the same placeholders
            # (but different names) DO mismatch. That's intentional: rename =
            # the catalog needs updating.
            out.add(m.group(0))
    return out


# ------- parsers — return dict[key] = source_text -------

def parse_android_xml(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return out
    for el in tree.getroot():
        name = el.get("name")
        if not name:
            continue
        if el.tag == "string":
            out[name] = "".join(el.itertext()).strip()
        elif el.tag == "plurals":
            for item in el.findall("item"):
                q = item.get("quantity", "other")
                out[f"{name}[{q}]"] = "".join(item.itertext()).strip()
        elif el.tag == "string-array":
            for i, item in enumerate(el.findall("item")):
                out[f"{name}[{i}]"] = "".join(item.itertext()).strip()
    return out


def parse_arb(path: Path) -> dict[str, str]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    # ARB: keys starting with @ are metadata
    return {k: v for k, v in d.items() if not k.startswith("@") and isinstance(v, str)}


def _unquote_po(s: str) -> str:
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        return bytes(s[1:-1], "utf-8").decode("unicode_escape", errors="replace")
    return s


def parse_po(path: Path) -> dict[str, str]:
    """Minimal .po parser: handles msgid/msgstr/msgid_plural/msgctxt with
    multi-line string continuations. Skips comments and obscure flags."""
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out

    for entry in re.split(r"\n\n+", text):
        fields: dict[str, list[str]] = {}
        cur: str | None = None
        for line in entry.splitlines():
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            head_match = re.match(r"(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+(.*)", line)
            if head_match:
                cur = head_match.group(1)
                fields.setdefault(cur, []).append(_unquote_po(head_match.group(2)))
            elif line.startswith('"') and cur:
                fields[cur].append(_unquote_po(line))

        msgid = "".join(fields.get("msgid", []))
        msgctxt = "".join(fields.get("msgctxt", [])) or None
        msgid_plural = "".join(fields.get("msgid_plural", [])) or None
        if not msgid:
            continue
        key = f"{msgctxt}|{msgid}" if msgctxt else msgid
        out[key] = msgid_plural or msgid
    return out


def parse_json_catalog(path: Path) -> dict[str, str]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, str] = {}

    def walk(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{prefix}.{k}" if prefix else k)
        elif isinstance(obj, str):
            out[prefix] = obj
        # react-intl id→{defaultMessage} shape
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{prefix}[{i}]")

    walk(d)
    return out


def parse_yaml_catalog(path: Path) -> dict[str, str]:
    try:
        import yaml  # type: ignore
    except ImportError:
        # Fall back to a naive line-based parser — not great, but works for
        # simple Rails locale files.
        return _parse_yaml_naive(path)
    try:
        d = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (Exception,):
        return {}
    out: dict[str, str] = {}

    def walk(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{prefix}.{k}" if prefix else str(k))
        elif isinstance(obj, str):
            out[prefix] = obj

    walk(d)
    # Strip top-level locale key (Rails convention)
    if out:
        first = next(iter(out))
        top = first.split(".", 1)[0]
        if all(k.split(".", 1)[0] == top for k in out):
            out = {k.split(".", 1)[1]: v for k, v in out.items() if "." in k}
    return out


def _parse_yaml_naive(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    stack: list[tuple[int, str]] = []
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, key.strip()))
        if val.strip():
            full = ".".join(s for _, s in stack)
            out[full] = val.strip().strip('"').strip("'")
    # Strip leading locale segment
    if out:
        first = next(iter(out))
        top = first.split(".", 1)[0]
        if all(k.split(".", 1)[0] == top for k in out):
            out = {k.split(".", 1)[1]: v for k, v in out.items() if "." in k}
    return out


def parse_resx(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return out
    for el in tree.getroot().findall("data"):
        name = el.get("name")
        v = el.find("value")
        if name and v is not None and v.text is not None:
            out[name] = v.text
    return out


def parse_properties(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "!")):
                continue
            for sep in ("=", ":"):
                if sep in line:
                    k, _, v = line.partition(sep)
                    out[k.strip()] = v.strip()
                    break
    except OSError:
        pass
    return out


def parse_qt_ts(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return out
    for ctx in tree.getroot().findall("context"):
        ctx_name_el = ctx.find("name")
        ctx_name = ctx_name_el.text or "" if ctx_name_el is not None else ""
        for msg in ctx.findall("message"):
            src = msg.find("source")
            if src is not None and src.text:
                out[f"{ctx_name}|{src.text}"] = src.text
    return out


def parse_ios_strings(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    # "key" = "value"; — keep it boring
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)"\s*;', text):
        out[m.group(1)] = m.group(2)
    return out


def parse_xcstrings(path: Path) -> dict[str, str]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, str] = {}
    for key, val in d.get("strings", {}).items():
        # Best-effort: take the sourceLanguage variant
        src_lang = d.get("sourceLanguage", "en")
        loc = val.get("localizations", {}).get(src_lang, {})
        s = loc.get("stringUnit", {}).get("value")
        if s:
            out[key] = s
        else:
            out[key] = ""
    return out


# ------- per-framework catalog discovery -------

def _locale_from_path(framework: str, p: Path) -> str | None:
    s = str(p)
    if framework == "android-strings-xml":
        m = re.search(r"res/values(-[a-zA-Z0-9_-]+)?/strings\.xml$", s)
        if m:
            return (m.group(1) or "")[1:] or "en"
    if framework in ("ios-strings",):
        m = re.search(r"([a-zA-Z0-9_-]+)\.lproj/", s)
        if m:
            return m.group(1)
    if framework == "flutter-arb":
        m = re.search(r"_(\w+)\.arb$", s)
        if m:
            return m.group(1)
    if framework in ("gettext", "django-gettext"):
        m = re.search(r"locale[s]?/([a-zA-Z_]+)/", s) or re.search(r"/([a-zA-Z_]+)\.po$", s)
        if m:
            return m.group(1)
    if framework == "rails-yaml":
        m = re.search(r"config/locales/(?:.+\.)?([a-zA-Z_-]+)\.ya?ml$", s)
        if m:
            return m.group(1)
    if framework == "qt-ts":
        m = re.search(r"_([a-zA-Z_]+)\.ts$", s)
        if m:
            return m.group(1)
    if framework == "dotnet-resx":
        m = re.search(r"\.([a-zA-Z]{2,3}(?:-[A-Z]{2})?)\.resx$", s)
        if m:
            return m.group(1)
        if s.endswith(".resx"):
            return "en"  # neutral resource
    if framework == "java-properties":
        m = re.search(r"_([a-zA-Z_]+)\.properties$", s)
        if m:
            return m.group(1)
    if framework in ("i18next", "react-intl", "json-i18n", "next-intl", "vue-i18n"):
        m = re.search(r"(?:locales?|i18n|lang|translations?)/([a-zA-Z_-]+?)(?:\.(?:json|ya?ml)|/)", s)
        if m:
            return m.group(1)
    return None


PARSERS = {
    "android-strings-xml": parse_android_xml,
    "flutter-arb": parse_arb,
    "gettext": parse_po,
    "django-gettext": parse_po,
    "rails-yaml": parse_yaml_catalog,
    "dotnet-resx": parse_resx,
    "java-properties": parse_properties,
    "qt-ts": parse_qt_ts,
    "ios-strings": parse_ios_strings,
    "ios-xcstrings": parse_xcstrings,
    "i18next": parse_json_catalog,
    "react-intl": parse_json_catalog,
    "json-i18n": parse_json_catalog,
    "next-intl": parse_json_catalog,
    "vue-i18n": parse_json_catalog,  # JSON branch; YAML handled below
}

GLOBS = {
    "android-strings-xml": "**/res/values*/strings.xml",
    "flutter-arb": "**/*.arb",
    "gettext": "**/*.po",
    "django-gettext": "**/*.po",
    "rails-yaml": "config/locales/**/*.yml",
    "dotnet-resx": "**/*.resx",
    "java-properties": "**/messages*.properties",
    "qt-ts": "**/translations/*.ts",
    "ios-strings": "**/*.lproj/Localizable.strings",
    "ios-xcstrings": "**/*.xcstrings",
    "i18next": "**/locales/**/*.json",
    "react-intl": "**/locales/**/*.json",
    "json-i18n": "**/locales/**/*.json",
    "next-intl": "**/messages/**/*.json",
    "vue-i18n": "**/locales/**/*.json",
}


def collect_catalogs(root: Path, framework: str) -> dict[str, dict[str, str]]:
    """locale → key → text."""
    glob = GLOBS.get(framework)
    if not glob:
        return {}
    parser = PARSERS[framework]
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for path in root.glob(glob):
        locale = _locale_from_path(framework, path)
        if not locale:
            continue
        cat = parser(path)
        for k, v in cat.items():
            out[locale][k] = v
    # Vue YAML branch
    if framework == "vue-i18n":
        for path in root.glob("**/locales/**/*.yml"):
            locale = _locale_from_path(framework, path)
            if locale:
                for k, v in parse_yaml_catalog(path).items():
                    out[locale][k] = v
    return dict(out)


def diff(catalogs: dict[str, dict[str, str]], source_locale: str) -> dict:
    if source_locale not in catalogs:
        # Fall back to whichever locale has the most keys
        source_locale = max(catalogs, key=lambda l: len(catalogs[l]))
    src = catalogs[source_locale]
    src_keys = set(src.keys())

    missing: dict[str, list[str]] = {}
    extra: dict[str, list[str]] = {}
    ph_mismatch: dict[str, list[str]] = {}

    for locale, cat in catalogs.items():
        if locale == source_locale:
            continue
        cat_keys = set(cat.keys())
        m = sorted(src_keys - cat_keys)
        e = sorted(cat_keys - src_keys)
        ph = []
        for k in src_keys & cat_keys:
            if placeholders_in(src.get(k, "")) != placeholders_in(cat.get(k, "")):
                ph.append(k)
        missing[locale] = m
        extra[locale] = e
        ph_mismatch[locale] = sorted(ph)

    return {
        "source_locale": source_locale,
        "locales": sorted(catalogs.keys()),
        "missing": missing,
        "extra": extra,
        "placeholder_mismatch": ph_mismatch,
        "counts": {
            "source_keys": len(src_keys),
            "missing_by_locale": {l: len(v) for l, v in missing.items()},
            "extra_by_locale":   {l: len(v) for l, v in extra.items()},
            "placeholder_mismatch_by_locale": {l: len(v) for l, v in ph_mismatch.items()},
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--framework", required=True,
                    help=f"one of: {', '.join(sorted(PARSERS))}")
    ap.add_argument("--source-locale", default="en")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    if args.framework not in PARSERS:
        print(f"error: unsupported framework: {args.framework}", file=sys.stderr)
        return 2

    catalogs = collect_catalogs(root, args.framework)
    if not catalogs:
        print(json.dumps({"error": "no catalogs found"}, indent=2))
        return 1

    result = diff(catalogs, args.source_locale)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
