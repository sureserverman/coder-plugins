#!/usr/bin/env python3
"""A plugin's version agrees at every site that mirrors it.

A version is one fact stored in three places: the plugin manifest, the root
marketplace entry, and — for plugins that carry one — a `(vX.Y.Z)` marker in the
README's lead paragraph. Nothing bound them together, so they drifted.

`planning/README.md` sat at `v0.37.0` while the plugin shipped 0.43.0. That line
had been updated at THIRTEEN prior bumps, so it is unambiguously a mirror; it
simply stopped being updated after 0.37.0, and five subsequent bumps missed it.

**The sweep that was supposed to catch it could not have.** It grepped for the
*outgoing* version strings — a line reading `0.37.0` can never match a search for
`0.42.1` — and its path list covered `README.md` and `*/.claude-plugin/` but not
`*/README.md`, the very file the task's own scope named. It returned zero and read
as green. That is the failure this script exists to make impossible: it enumerates
the mirrors POSITIVELY and reconciles them against the manifest, so a site can only
pass by agreeing, never by being unreachable.

  MANIFEST-MISSING   a marketplace entry names a plugin with no manifest.
  MARKETPLACE-DRIFT  the marketplace entry's version != the manifest's.
  README-DRIFT       the README lead paragraph's `(vX.Y.Z)` != the manifest's.
  UNLISTED           a plugin directory with a manifest and no marketplace entry.

**Only the lead paragraph is checked, and only the parenthesized form.** READMEs
legitimately contain version strings that are not mirrors — `git-github/README.md`
documents `"cut v1.4.0"` as a trigger phrase and `release-promo/README.md` shows
`/promote-release v1.4.0` as sample input. Both are usage, not claims about the
plugin, and a looser matcher would demand they track the plugin version. The lead
paragraph (everything before the first `## `) plus parentheses is the convention
actually in use.

A plugin whose README carries no such marker is fine — this reports drift, it does
not mandate a mirror that does not exist.

Read-only. Exit 0 when every mirror agrees, 1 otherwise.
"""
import argparse
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKETPLACE = os.path.join(".claude-plugin", "marketplace.json")
LEAD_VERSION_RE = re.compile(r"\(v(\d+\.\d+\.\d+)\)")


def manifest_version(root, plugin_dir):
    path = os.path.join(root, plugin_dir, ".claude-plugin", "plugin.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("version")


def readme_lead_version(root, plugin_dir):
    """The `(vX.Y.Z)` in the README's lead paragraph, or None.

    Lead paragraph = everything before the first `## ` heading. Scoped that way on
    purpose: a version further down is documentation of a command or an example,
    not a claim about this plugin's own version.
    """
    path = os.path.join(root, plugin_dir, "README.md")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    lead = re.split(r"^## ", text, maxsplit=1, flags=re.M)[0]
    m = LEAD_VERSION_RE.search(lead)
    return m.group(1) if m else None


def check(root):
    problems = []
    mp_path = os.path.join(root, MARKETPLACE)
    with open(mp_path, encoding="utf-8") as fh:
        mp = json.load(fh)

    listed = set()
    for entry in mp.get("plugins", []):
        name = entry.get("name", "?")
        plugin_dir = entry.get("source", "").lstrip("./")
        listed.add(plugin_dir)
        mv = manifest_version(root, plugin_dir)
        if mv is None:
            problems.append(f"{name}: MANIFEST-MISSING — marketplace names "
                            f"{plugin_dir!r}, which has no plugin.json")
            continue
        if entry.get("version") != mv:
            problems.append(f"{name}: MARKETPLACE-DRIFT — marketplace says "
                            f"{entry.get('version')!r}, manifest says {mv!r}")
        rv = readme_lead_version(root, plugin_dir)
        if rv is not None and rv != mv:
            problems.append(f"{name}: README-DRIFT — {plugin_dir}/README.md lead "
                            f"paragraph says (v{rv}), manifest says {mv}")

    # A plugin with a manifest and no marketplace entry ships nowhere, and no
    # version check would ever look at it.
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, ".claude-plugin", "plugin.json")):
            if name not in listed:
                problems.append(f"{name}: UNLISTED — has a manifest but no "
                                "marketplace entry")
    return problems, len(mp.get("plugins", []))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="check-version-mirrors")
    ap.add_argument("--root", default=REPO_ROOT)
    args = ap.parse_args(argv)
    problems, n = check(args.root)
    # honest-gates: name the population, so a run that reconciled nothing cannot
    # read as a run that reconciled everything.
    print(f"{n} plugin(s) reconciled across manifest, marketplace and README lead; "
          f"{len(problems)} problem(s).")
    for p in problems:
        print(f"  {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
