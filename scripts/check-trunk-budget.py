#!/usr/bin/env python3
"""A ratchet on skill trunk sizes: no SKILL.md may exceed its recorded ceiling.

A skill's *body* is loaded per invocation, not per session, so every byte in a
trunk is paid every time the skill fires, in every project with the plugin
enabled. Trunks therefore grow the way costs grow when nobody is measuring:
`planning/skills/executing-plans/SKILL.md` gained 34% — 69,527 -> 92,987 B — in
the six days between the token-efficiency plan being authored and executed, one
reasonable section at a time.

`scripts/trunk-budget.txt` records one `<repo-relative-path> <max-bytes>` line
per trunk. The ceiling is seeded at the size measured when the entry is written,
so the ratchet's day-one value does not depend on any extraction happening: a
trunk may shrink freely and may not grow at all. Ceilings are lowered by hand
when an extraction lands, which is what makes the reduction durable rather than
a number that drifts back up.

Two failure modes this deliberately treats as errors rather than skips:

  - A budgeted file that does not exist. Skipping it would let a deleted or
    renamed trunk read as compliant forever.
  - A trunk over `--min-size` with no budget entry. Without this the ratchet is
    opt-in, and a new fat trunk opts out of it by simply never being listed.

Read-only: never writes to the repo. Exit 0 when every trunk is within its
ceiling, 1 otherwise.
"""
import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUDGETS_PATH = os.path.join(REPO_ROOT, "scripts", "trunk-budget.txt")
DEFAULT_MIN_SIZE = 10000

EXCLUDE_PARTS = ("/tests/", "/fixtures/")


def load_budgets(path=BUDGETS_PATH):
    """{repo-relative path: max bytes} from the budget file."""
    budgets = {}
    if not os.path.exists(path):
        return budgets
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            entry = line.split("#", 1)[0].strip()
            if not entry:
                continue
            parts = entry.split()
            if len(parts) != 2:
                continue
            try:
                budgets[parts[0]] = int(parts[1])
            except ValueError:
                continue
    return budgets


def discover_trunks(root):
    """Every `*/skills/*/SKILL.md` in the tree, repo-relative and sorted."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "node_modules", "__pycache__")]
        if "SKILL.md" not in filenames:
            continue
        rel = os.path.relpath(os.path.join(dirpath, "SKILL.md"), root)
        if any(p in f"/{rel}" for p in EXCLUDE_PARTS):
            continue
        if "/skills/" in f"/{rel}":
            out.append(rel)
    return sorted(out)


def measure(root, budgets, min_size):
    """One row per budgeted trunk: size, budget, headroom, over."""
    rows = []
    for rel, cap in sorted(budgets.items()):
        full = os.path.join(root, rel)
        size = os.path.getsize(full) if os.path.exists(full) else None
        rows.append({
            "path": rel,
            "size": size,
            "budget": cap,
            "headroom": None if size is None else cap - size,
            "over": size is None or size > cap,
            "missing": size is None,
        })
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(prog="check-trunk-budget")
    ap.add_argument("--root", default=REPO_ROOT)
    ap.add_argument("--budgets", default=None)
    ap.add_argument("--min-size", type=int, default=DEFAULT_MIN_SIZE,
                    help="trunks at or above this size must carry a budget entry")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    budgets_path = args.budgets or os.path.join(args.root, "scripts",
                                                "trunk-budget.txt")
    budgets = load_budgets(budgets_path)
    rows = measure(args.root, budgets, args.min_size)

    # A big trunk with no entry is a gap in the ratchet, not a pass.
    unbudgeted = []
    for rel in discover_trunks(args.root):
        if rel in budgets:
            continue
        if os.path.getsize(os.path.join(args.root, rel)) >= args.min_size:
            unbudgeted.append(rel)

    over = [r for r in rows if r["over"]]

    if args.json:
        print(json.dumps({"rows": rows, "unbudgeted": unbudgeted}, indent=2))
    else:
        # honest-gates: state the population, so an empty sweep cannot read as
        # a pass over something.
        print(f"{len(rows)} budgeted trunk(s); {len(over)} over ceiling, "
              f"{len(unbudgeted)} unbudgeted over {args.min_size} B.")
        for r in sorted(rows, key=lambda x: -(x["size"] or 0)):
            if r["missing"]:
                print(f"  MISSING  {r['path']}  (budgeted {r['budget']} B)")
                continue
            flag = "OVER  " if r["over"] else "ok    "
            print(f"  {flag}   {r['size']:>7} / {r['budget']:>7} B  "
                  f"({r['headroom']:+d})  {r['path']}")
        for rel in unbudgeted:
            print(f"  NO-BUDGET  {rel}  "
                  f"({os.path.getsize(os.path.join(args.root, rel))} B)")

    return 1 if (over or unbudgeted) else 0


if __name__ == "__main__":
    sys.exit(main())
