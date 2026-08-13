#!/usr/bin/env python3
"""Fixture tests for scripts/check-version-mirrors.py.

The load-bearing cases are the ones proving the guard REJECTS. The check it replaced
returned zero and read as green because it searched for the *outgoing* version string
and never looked in the directory it was supposed to check — so a version-mirror
check that only ever passes is precisely the artifact this one exists to replace.

Two classes deserve their own cases beyond simple drift:

  * **MIRROR-MISSING.** Deleting a marker used to be silent, because "no marker" and
    "no drift" were the same state. A plugin can then go from checked to unchecked
    while the guard still prints green.
  * **CHANGELOG-DRIFT.** Missed by the first cut, and found drifted in the live tree
    at the moment it was added.

Stdlib only.
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "check-version-mirrors.py")

spec = importlib.util.spec_from_file_location("vm", SCRIPT)
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)

FAILURES = []


def check(ok, msg):
    print(f"  {'ok' if ok else 'FAIL'}: {msg}")
    if not ok:
        FAILURES.append(msg)


def build(root, plugins, marketplace=None):
    """plugins: {name: {version, readme?, changelog?}}. marketplace defaults to agreeing."""
    entries = []
    for name, spec_ in plugins.items():
        d = os.path.join(root, name, ".claude-plugin")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "plugin.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": name, "version": spec_["version"]}, fh)
        if "readme" in spec_:
            with open(os.path.join(root, name, "README.md"), "w", encoding="utf-8") as fh:
                fh.write(f"# {name}\n\n{spec_['readme']}\n\n## Installation\n\nx\n")
        if "changelog" in spec_:
            with open(os.path.join(root, name, "CHANGELOG.md"), "w", encoding="utf-8") as fh:
                fh.write(f"# Changelog\n\n{spec_['changelog']}\n\n### Changed\n- x\n")
        entries.append({"name": name, "source": f"./{name}",
                        "version": (marketplace or {}).get(name, spec_["version"])})
    d = os.path.join(root, ".claude-plugin")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "marketplace.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": "m", "metadata": {"version": "1.0.0"}, "plugins": entries}, fh)


def run(root):
    problems, _n, _counts = vm.check(root)
    return problems


def cases():
    with tempfile.TemporaryDirectory() as root:
        build(root, {"alpha": {"version": "1.2.3"}})
        check(run(root) == [], "manifest and marketplace agreeing passes")

    with tempfile.TemporaryDirectory() as root:
        build(root, {"alpha": {"version": "1.2.3"}}, marketplace={"alpha": "1.2.2"})
        p = run(root)
        check(any("MARKETPLACE-DRIFT" in x for x in p), "marketplace drift is caught")

    with tempfile.TemporaryDirectory() as root:
        build(root, {"alpha": {"version": "1.2.3", "readme": "A thing (v1.2.3) that works."}})
        check(run(root) == [], "an agreeing README lead marker passes")

    with tempfile.TemporaryDirectory() as root:
        build(root, {"alpha": {"version": "1.2.3", "readme": "A thing (v1.0.0) that works."}})
        p = run(root)
        check(any("README-DRIFT" in x for x in p), "a stale README lead marker is caught")

    # The exclusion the live tree depends on: usage samples are not mirrors.
    with tempfile.TemporaryDirectory() as root:
        build(root, {"alpha": {"version": "1.2.3",
                               "readme": 'Run `cut v1.4.0` to tag a release.'}})
        check(run(root) == [],
              "an unparenthesised version in prose is a usage sample, not a mirror")

    # ...and one below the lead is history, not a claim about this version.
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "alpha", ".claude-plugin"))
        with open(os.path.join(root, "alpha", ".claude-plugin", "plugin.json"), "w") as fh:
            json.dump({"name": "alpha", "version": "1.2.3"}, fh)
        with open(os.path.join(root, "alpha", "README.md"), "w") as fh:
            fh.write("# alpha\n\nA thing.\n\n## History\n\nTiering shipped (v0.9.0).\n")
        d = os.path.join(root, ".claude-plugin"); os.makedirs(d)
        with open(os.path.join(d, "marketplace.json"), "w") as fh:
            json.dump({"name": "m", "metadata": {"version": "1.0.0"},
                       "plugins": [{"name": "alpha", "source": "./alpha", "version": "1.2.3"}]}, fh)
        check(run(root) == [], "a (vX.Y.Z) below the lead paragraph is not checked")

    with tempfile.TemporaryDirectory() as root:
        build(root, {"alpha": {"version": "1.2.3", "changelog": "## [1.2.3] - 2026-01-01"}})
        check(run(root) == [], "an agreeing changelog top entry passes")

    with tempfile.TemporaryDirectory() as root:
        build(root, {"alpha": {"version": "1.2.3", "changelog": "## [1.0.0] - 2026-01-01"}})
        p = run(root)
        check(any("CHANGELOG-DRIFT" in x for x in p),
              "a stale changelog top entry is caught — the class the first cut missed")

    # An Unreleased section above the top release must not be read as the version.
    with tempfile.TemporaryDirectory() as root:
        build(root, {"alpha": {"version": "1.2.3",
                               "changelog": "## [Unreleased]\n\n- wip\n\n## [1.2.3] - 2026-01-01"}})
        check(run(root) == [], "an `## [Unreleased]` section is skipped, not treated as the top")

    # MIRROR-MISSING: a KNOWN mirror that has been deleted.
    with tempfile.TemporaryDirectory() as root:
        build(root, {"planning": {"version": "1.2.3", "readme": "No marker here."}})
        p = run(root)
        check(any("MIRROR-MISSING" in x for x in p),
              "deleting a KNOWN README marker is caught, not silently uncovered")

    with tempfile.TemporaryDirectory() as root:
        build(root, {"business": {"version": "1.2.3"}})
        p = run(root)
        check(any("MIRROR-MISSING" in x and "CHANGELOG" in x for x in p),
              "deleting a KNOWN changelog is caught too")

    # A plugin nobody ships, and an entry pointing at nothing.
    with tempfile.TemporaryDirectory() as root:
        build(root, {"alpha": {"version": "1.2.3"}})
        os.makedirs(os.path.join(root, "orphan", ".claude-plugin"))
        with open(os.path.join(root, "orphan", ".claude-plugin", "plugin.json"), "w") as fh:
            json.dump({"name": "orphan", "version": "0.1.0"}, fh)
        p = run(root)
        check(any("UNLISTED" in x for x in p), "a manifest with no marketplace entry is caught")

    with tempfile.TemporaryDirectory() as root:
        d = os.path.join(root, ".claude-plugin"); os.makedirs(d)
        with open(os.path.join(d, "marketplace.json"), "w") as fh:
            json.dump({"name": "m", "metadata": {"version": "1.0.0"},
                       "plugins": [{"name": "ghost", "source": "./ghost", "version": "1.0.0"}]}, fh)
        p = run(root)
        check(any("MANIFEST-MISSING" in x for x in p),
              "a marketplace entry with no manifest is caught")


def real_tree():
    check(vm.main([]) == 0, "every shipped mirror agrees")
    _p, n, counts = vm.check(vm.REPO_ROOT)
    check(n >= 13, f"the sweep sees the marketplace's plugins (saw {n})")
    # The population line must not overstate: these are the sites actually reconciled.
    check(counts["readme"] >= 1 and counts["changelog"] >= 1,
          f"README and changelog mirrors are actually reconciled, not merely counted "
          f"(readme={counts['readme']}, changelog={counts['changelog']})")


if __name__ == "__main__":
    print("check-version-mirrors fixtures:")
    cases()
    print("real tree:")
    real_tree()
    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")
