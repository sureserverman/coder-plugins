#!/usr/bin/env python3
"""A plugin's version agrees at every site that mirrors it.

A version is one fact stored in up to FOUR places: the plugin manifest, the root
marketplace entry, a `(vX.Y.Z)` marker in the README's lead paragraph, and the top
entry of a `CHANGELOG.md`. Nothing bound them together, so they drifted.

`planning/README.md` sat at `v0.37.0` while the plugin shipped 0.43.0. That line has
held **17 distinct values** across the repo's history, so it is unambiguously a
mirror rather than a historical marker; it simply stopped being updated after
0.37.0, and **seven** subsequent bumps shipped it stale — 0.38.0, 0.39.0, 0.40.0,
0.41.0, 0.42.0, 0.42.1, and this stage's own 0.43.0. This guard, back-tested against
each of those trees, is red at all seven and clean at the last correct commit.

*(Both figures were wrong in the first cut of this docstring — "thirteen bumps" and
"five" — and a review caught them in the same commit that filed BL-076 for a
non-reproducing count. Counted here rather than recalled.)*

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
  CHANGELOG-DRIFT    the top `## [X.Y.Z]` entry != the manifest's.
  MIRROR-MISSING     a plugin KNOWN to carry a mirror has lost it.
  UNLISTED           a plugin directory with a manifest and no marketplace entry.

The CHANGELOG class was missed by the first cut of this script, and a review caught
it in the state that proves the point: `business/CHANGELOG.md` declared itself the
record of "All notable changes" while its top entry sat at 0.6.0 against a shipped
0.6.3 — three unrecorded releases, the newest made by the very task that claimed to
have swept "all mirror sites". It has a real consumer:
`git-github/skills/release-tag/SKILL.md` sources a tag message from the top entry
"if one exists", so a stale changelog produces a tag describing the wrong release.

The reasoning that skipped it the first time was that the file "records minor
versions only" — 0.6.1 and 0.6.2 had no entries either. That read a gap as a
convention. Three consecutive misses in the only file claiming to document all of
them is drift, and the difference between the two readings is exactly what a guard
settles and prose does not.

MIRROR-MISSING exists because `rv is not None` made marker DELETION silent: a
plugin that loses its README marker becomes indistinguishable from one that never
had it, so the guard can drop from checking a site to checking none while still
printing green. That is the same "unreachable reads as green" class this script was
written for, one level in. Membership is pinned in KNOWN_MIRRORS below.

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
CHANGELOG_ENTRY_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.M)

# Plugins known to carry each optional mirror. Pinned so that DELETING a mirror is a
# finding rather than a silent loss of coverage. Add a plugin here when it gains one.
KNOWN_MIRRORS = {"readme_lead": {"planning"}, "changelog": {"business"}}


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


def changelog_version(root, plugin_dir):
    """The topmost released `## [X.Y.Z]` in a CHANGELOG, or None.

    An `## [Unreleased]` section above it is conventional and is skipped rather
    than treated as the top entry — the regex only matches a semver triple.
    """
    path = os.path.join(root, plugin_dir, "CHANGELOG.md")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        m = CHANGELOG_ENTRY_RE.search(fh.read())
    return m.group(1) if m else None


def check(root):
    problems = []
    mp_path = os.path.join(root, MARKETPLACE)
    with open(mp_path, encoding="utf-8") as fh:
        mp = json.load(fh)

    listed = set()
    counts = {"readme": 0, "changelog": 0}
    for entry in mp.get("plugins", []):
        name = entry.get("name", "?")
        plugin_dir = entry.get("source", "").removeprefix("./")
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
        elif rv is None and name in KNOWN_MIRRORS["readme_lead"]:
            problems.append(f"{name}: MIRROR-MISSING — {plugin_dir}/README.md is known "
                            "to carry a (vX.Y.Z) lead marker and no longer does")
        if rv is not None:
            counts["readme"] += 1

        cv = changelog_version(root, plugin_dir)
        if cv is not None and cv != mv:
            problems.append(f"{name}: CHANGELOG-DRIFT — {plugin_dir}/CHANGELOG.md's top "
                            f"entry is [{cv}], manifest says {mv}")
        elif cv is None and name in KNOWN_MIRRORS["changelog"]:
            problems.append(f"{name}: MIRROR-MISSING — {plugin_dir}/CHANGELOG.md is known "
                            "to carry released entries and has none")
        if cv is not None:
            counts["changelog"] += 1

    # A plugin with a manifest and no marketplace entry ships nowhere, and no
    # version check would ever look at it.
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, ".claude-plugin", "plugin.json")):
            if name not in listed:
                problems.append(f"{name}: UNLISTED — has a manifest but no "
                                "marketplace entry")
    return problems, len(mp.get("plugins", [])), counts


def main(argv=None):
    ap = argparse.ArgumentParser(prog="check-version-mirrors")
    ap.add_argument("--root", default=REPO_ROOT)
    args = ap.parse_args(argv)
    problems, n, counts = check(args.root)
    # honest-gates: name each population SEPARATELY. Reporting "13 plugins reconciled
    # across manifest, marketplace and README lead" was itself an overstatement — one
    # of the 13 has a README marker, so a run reconciling a single lead read as one
    # reconciling thirteen.
    print(f"{n} manifest/marketplace pair(s), {counts['readme']} README lead(s) and "
          f"{counts['changelog']} changelog(s) reconciled; {len(problems)} problem(s).")
    for p in problems:
        print(f"  {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
