#!/usr/bin/env python3
"""Validate a translator-output workpacket.

Input (stdin or file): JSON with shape:

{
  "target_locale": "es",
  "framework": "i18next",
  "entries": [
    {"key": "...", "source": "...", "translation": "..."},
    ...
  ]
}

Checks per entry:
  - Placeholder set in translation == placeholder set in source.
  - ICU MessageFormat brace balance in translation.
  - HTML tag balance if source has tags.
  - No type swap (%s ↔ %d, etc.).
  - Required CLDR plural categories present (for the target locale) when
    source is an ICU plural form.

Output: JSON with defects.

Exit code:
  0 — no defects
  1 — defects found (still prints report)
  2 — usage error
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# CLDR-ish minimal plural-category requirements per language. This is the
# CLDR Cardinal Plural rules summarized — full table at
# https://cldr.unicode.org/index/cldr-spec/plural-rules
CLDR_PLURALS = {
    # one, other
    "en": {"one", "other"},
    "de": {"one", "other"},
    "es": {"one", "other"},
    "it": {"one", "other"},
    "nl": {"one", "other"},
    "pt": {"one", "other"},
    "sv": {"one", "other"},
    "no": {"one", "other"},
    "da": {"one", "other"},
    "fi": {"one", "other"},
    "el": {"one", "other"},
    "tr": {"one", "other"},
    # one, other but with French rounding rules — same categories
    "fr": {"one", "other"},
    # only other
    "ja": {"other"},
    "ko": {"other"},
    "zh": {"other"},
    "th": {"other"},
    "vi": {"other"},
    "id": {"other"},
    # Slavic — one, few, many, other
    "ru": {"one", "few", "many", "other"},
    "uk": {"one", "few", "many", "other"},
    "pl": {"one", "few", "many", "other"},
    "cs": {"one", "few", "many", "other"},
    "sk": {"one", "few", "many", "other"},
    # Arabic — zero, one, two, few, many, other
    "ar": {"zero", "one", "two", "few", "many", "other"},
    # Hebrew — one, two, many, other
    "he": {"one", "two", "many", "other"},
    # Welsh — zero, one, two, few, many, other
    "cy": {"zero", "one", "two", "few", "many", "other"},
    # Romanian — one, few, other
    "ro": {"one", "few", "other"},
    # Latvian — zero, one, other
    "lv": {"zero", "one", "other"},
    # Lithuanian — one, few, many, other
    "lt": {"one", "few", "many", "other"},
}


PRINTF_RE   = re.compile(r"(%(?:\d+\$)?[\d.\-+ #]*[sdifguxXeEoc@])")
HANDLE_RE   = re.compile(r"(\{\{\w+\}\})")
RAILS_RE    = re.compile(r"(%\{\w+\})")


def _find_icu_blocks(text: str) -> list[tuple[int, int, str]]:
    """Return list of (start, end, kind) for ICU placeholders, brace-balanced.

    kind is one of: "simple" ({name}), "plural" ({n, plural, ...}),
    "select" ({n, select, ...}), "selectordinal", "number"/"date"/"time".
    """
    blocks: list[tuple[int, int, str]] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "{":
            # find matching close
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                j += 1
            if depth == 0:
                # Inspect head: {NAME, KIND, ...} ?
                inner = text[i + 1:j - 1]
                head = inner.split(",", 1)[0].strip()
                if head and re.match(r"^\w+$", head):
                    # what's after the name?
                    parts = [p.strip() for p in inner.split(",", 2)]
                    if len(parts) == 1:
                        blocks.append((i, j, "simple"))
                    else:
                        kind = parts[1] if parts[1] in {"plural", "select", "selectordinal", "number", "date", "time"} else "simple"
                        blocks.append((i, j, kind))
                i = j
                continue
        i += 1
    return blocks


def placeholders(text: str) -> set[str]:
    """Set of structural placeholders. ICU plural/select bodies are stripped
    so that two translations of the same plural compare equal."""
    if not text:
        return set()
    out: set[str] = set()
    # ICU blocks
    for start, end, kind in _find_icu_blocks(text):
        inner = text[start + 1:end - 1]
        name = inner.split(",", 1)[0].strip()
        if kind == "simple":
            out.add(f"{{{name}}}")
        else:
            out.add(f"{{{name}, {kind}}}")
    # printf
    for m in PRINTF_RE.finditer(text):
        out.add(m.group(0))
    # Handlebars (note: nested {{}} also looks like two ICU braces — but the
    # ICU pass requires `{NAME[,KIND,...]}` head which fails for `{{name}}`)
    for m in HANDLE_RE.finditer(text):
        out.add(m.group(0))
    # Rails
    for m in RAILS_RE.finditer(text):
        out.add(m.group(0))
    return out


def balanced_braces(text: str) -> bool:
    depth = 0
    for c in text:
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


HTML_TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>")


def html_tags_balanced(text: str) -> bool:
    stack: list[str] = []
    for m in HTML_TAG_RE.finditer(text):
        closing, name = m.group(1), m.group(2).lower()
        # void elements
        if name in {"br", "img", "input", "hr", "meta", "link"}:
            continue
        if closing:
            if not stack or stack[-1] != name:
                return False
            stack.pop()
        else:
            stack.append(name)
    return not stack


def html_tag_set(text: str) -> set[str]:
    return {m.group(2).lower() for m in HTML_TAG_RE.finditer(text)}


PRINTF_TYPE_RE = re.compile(r"%(?:\d+\$)?[\d.\-+ #]*([sdifguxXeEoc@])")


def printf_type_signature(text: str) -> list[str]:
    return [m.group(1) for m in PRINTF_TYPE_RE.finditer(text)]


def icu_plural_cats(text: str) -> set[str]:
    """Extract plural category labels from any ICU plural/selectordinal block.

    Uses brace-balanced extraction so nested braces don't truncate the body.
    """
    out: set[str] = set()
    for start, end, kind in _find_icu_blocks(text):
        if kind not in {"plural", "selectordinal"}:
            continue
        inner = text[start + 1:end - 1]
        # Drop "name, kind," prefix
        parts = inner.split(",", 2)
        if len(parts) < 3:
            continue
        body = parts[2]
        # Walk body, find category labels followed by '{...}' blocks
        i = 0
        while i < len(body):
            m = re.match(r"\s*(zero|one|two|few|many|other|=\d+|offset:\d+)\b", body[i:])
            if not m:
                i += 1
                continue
            label = m.group(1)
            i += m.end()
            # skip whitespace
            while i < len(body) and body[i].isspace():
                i += 1
            # expect '{' — skip its matching body
            if i < len(body) and body[i] == "{":
                if not label.startswith(("=", "offset:")):
                    out.add(label)
                depth = 1
                i += 1
                while i < len(body) and depth > 0:
                    if body[i] == "{":
                        depth += 1
                    elif body[i] == "}":
                        depth -= 1
                    i += 1
    return out


def base_lang(locale: str) -> str:
    return re.split(r"[-_]", locale)[0].lower()


def validate(payload: dict) -> list[dict]:
    target = payload.get("target_locale", "")
    base = base_lang(target)
    expected_cats = CLDR_PLURALS.get(base)

    defects: list[dict] = []
    for e in payload.get("entries", []):
        key = e.get("key", "?")
        src = e.get("source", "")
        tr = e.get("translation", "")
        if not tr:
            defects.append({"key": key, "kind": "empty-translation"})
            continue

        # Placeholder set match
        src_ph = placeholders(src)
        tr_ph = placeholders(tr)
        if src_ph != tr_ph:
            defects.append({
                "key": key, "kind": "placeholder-mismatch",
                "source_placeholders": sorted(src_ph),
                "translation_placeholders": sorted(tr_ph),
                "missing_in_translation": sorted(src_ph - tr_ph),
                "extra_in_translation": sorted(tr_ph - src_ph),
            })

        # Brace balance (catches truncated ICU)
        if not balanced_braces(tr):
            defects.append({"key": key, "kind": "unbalanced-braces", "translation": tr})

        # HTML tag balance + set
        src_tags = html_tag_set(src)
        if src_tags:
            if not html_tags_balanced(tr):
                defects.append({"key": key, "kind": "unbalanced-html", "translation": tr})
            tr_tags = html_tag_set(tr)
            if src_tags != tr_tags:
                defects.append({
                    "key": key, "kind": "html-tag-mismatch",
                    "source_tags": sorted(src_tags),
                    "translation_tags": sorted(tr_tags),
                })

        # printf type signature
        src_sig = printf_type_signature(src)
        tr_sig = printf_type_signature(tr)
        if sorted(src_sig) != sorted(tr_sig):
            defects.append({
                "key": key, "kind": "printf-type-mismatch",
                "source": src_sig, "translation": tr_sig,
            })

        # ICU plural category check
        src_cats = icu_plural_cats(src)
        if src_cats and expected_cats:
            tr_cats = icu_plural_cats(tr)
            missing = expected_cats - tr_cats
            if missing:
                defects.append({
                    "key": key, "kind": "missing-plural-categories",
                    "locale": target, "missing": sorted(missing),
                    "present": sorted(tr_cats),
                    "required_for_locale": sorted(expected_cats),
                })
    return defects


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", help="path to translator output JSON (default stdin)")
    args = ap.parse_args()

    if args.input:
        try:
            payload = json.loads(open(args.input, encoding="utf-8").read())
        except (OSError, json.JSONDecodeError) as e:
            print(f"error: cannot read {args.input}: {e}", file=sys.stderr)
            return 2
    else:
        try:
            payload = json.loads(sys.stdin.read())
        except json.JSONDecodeError as e:
            print(f"error: cannot parse stdin JSON: {e}", file=sys.stderr)
            return 2

    defects = validate(payload)
    report = {
        "target_locale": payload.get("target_locale"),
        "framework": payload.get("framework"),
        "entries_checked": len(payload.get("entries", [])),
        "defects": defects,
        "defect_count": len(defects),
        "defects_by_kind": {},
    }
    for d in defects:
        report["defects_by_kind"][d["kind"]] = report["defects_by_kind"].get(d["kind"], 0) + 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if defects else 0


if __name__ == "__main__":
    sys.exit(main())
