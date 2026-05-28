#!/usr/bin/env python3
"""Extract missing-translation entries into a workpacket the translator can consume.

Reuses the parsers from diff-catalogs.py. Outputs JSON to stdout in the shape:

{
  "source_locale": "en",
  "target_locale": "es",
  "framework": "i18next",
  "entries": [
    {"key": "...", "source": "...", "placeholders": [...], "context": null, "plural": false},
    ...
  ]
}

If --include-stale, also includes keys where the placeholder set differs between
source and target (translation exists but is structurally wrong).

If --include-extra, includes the *extra* keys (present in target but not in
source) so the caller can decide whether to drop them.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


def _load_diff_module():
    here = Path(__file__).resolve().parent.parent.parent / "i18n-audit" / "scripts" / "diff-catalogs.py"
    spec = importlib.util.spec_from_file_location("_diff_catalogs", here)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {here}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--framework", required=True)
    ap.add_argument("--target", required=True, help="target locale code")
    ap.add_argument("--source-locale", default="en")
    ap.add_argument("--include-stale", action="store_true",
                    help="also include keys with placeholder mismatch")
    ap.add_argument("--include-extra", action="store_true",
                    help="also include keys present in target but absent in source")
    args = ap.parse_args()

    root = Path(args.root)
    diff_mod = _load_diff_module()

    catalogs = diff_mod.collect_catalogs(root, args.framework)
    if not catalogs:
        print(json.dumps({"error": "no catalogs found", "framework": args.framework}), file=sys.stderr)
        return 1

    src_loc = args.source_locale if args.source_locale in catalogs else next(iter(catalogs))
    src = catalogs[src_loc]
    tgt = catalogs.get(args.target, {})

    missing_keys = sorted(set(src.keys()) - set(tgt.keys()))

    stale_keys: list[str] = []
    if args.include_stale:
        for k in set(src.keys()) & set(tgt.keys()):
            if diff_mod.placeholders_in(src[k]) != diff_mod.placeholders_in(tgt.get(k, "")):
                stale_keys.append(k)
        stale_keys.sort()

    extra_keys: list[str] = []
    if args.include_extra:
        extra_keys = sorted(set(tgt.keys()) - set(src.keys()))

    def entry(key: str, source_text: str, status: str) -> dict:
        phs = sorted(diff_mod.placeholders_in(source_text))
        # ICU plural / select detection — coarse
        is_plural = bool(re.search(r"\{\w+,\s*(plural|selectordinal)\b", source_text))
        return {
            "key": key,
            "source": source_text,
            "placeholders": phs,
            "context": None,
            "plural": is_plural,
            "status": status,
        }

    entries = []
    for k in missing_keys:
        entries.append(entry(k, src[k], "missing"))
    for k in stale_keys:
        entries.append(entry(k, src[k], "stale"))
    for k in extra_keys:
        entries.append({"key": k, "source": tgt[k], "status": "extra",
                        "placeholders": [], "context": "Present in target but not source"})

    out = {
        "source_locale": src_loc,
        "target_locale": args.target,
        "framework": args.framework,
        "style_guide": None,
        "entries": entries,
        "counts": {
            "missing": len(missing_keys),
            "stale": len(stale_keys),
            "extra": len(extra_keys),
        },
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
