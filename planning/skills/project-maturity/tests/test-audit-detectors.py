#!/usr/bin/env python3
"""Fixture tests for the project-maturity deterministic detector lane.

Runs `scripts/audit-detectors.py` end-to-end against the fixture trees under
`tests/fixtures/` and asserts the fired detectors, the AI-tool flag, and the
notes/errors channels. No pytest dependency — plain assertions, non-zero exit
on any failure. Wired into CI via `.github/workflows/validate-maturity-detectors.yml`.

Run locally:  python3 planning/skills/project-maturity/tests/test-audit-detectors.py

Coverage note: the `is_ai_tool` frontmatter-bundle branch (agents/·skills/·
commands/ with name:+description:) is deliberately NOT fixture-tested — a fixture
`agents/*.md` or `skills/*/SKILL.md` would be picked up by the marketplace-wide
`validate-stack-routing.py` walk. That branch is exercised by the live repo tree
(this marketplace is itself an AI-tool project). Fixtures use manifest signals
(`.claude-plugin/*`, `.mcp.json`) for the flag instead.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "audit-detectors.py"
FIXTURES = HERE / "fixtures"

# Expected fired items per axis (as sets — order-independent), the AI-tool flag,
# and invariants on the notes/errors channels.
EXPECTED = {
    "ai-tool-plugin": {
        "is_ai_tool": True,
        "detectors": {
            "documentation": {"README", "LICENSE"},
            "security": {"sec-audit"},
            "packaging": {"Claude Code marketplace", "MCP server"},
            "ui_ux": set(),
            "i18n": set(),
            "testing": {"test suite", "CI"},
        },
        "notes": 0,
        "errors": 0,
    },
    "android-app": {
        "is_ai_tool": False,
        "detectors": {
            "documentation": {"README"},
            "security": set(),
            "packaging": {"F-Droid", "GitHub Releases APK"},
            "ui_ux": {"icon"},
            "i18n": {"Android"},
            "testing": {"test suite", "CI"},
        },
        "notes": 0,
        "errors": 0,
        # spot-check evidence where the value carries meaning
        "evidence": {
            ("i18n", "Android"): "res/values-de,res/values-fr",
            ("ui_ux", "icon"): "res/mipmap-hdpi/ic_launcher.png",
        },
    },
    "edge-cases": {
        "is_ai_tool": False,
        "detectors": {
            "documentation": {"README"},
            "security": set(),
            "packaging": set(),
            "ui_ux": set(),
            "i18n": set(),
            "testing": set(),
        },
        "notes": 1,          # unclean sec-audit -> informational note, not a tick
        "errors": 1,         # malformed chrome/manifest.json -> stale-detector
        "note_contains": "not clean",
        "error_item": "Chrome",
    },
}


def run(fixture: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURES / fixture)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"{fixture}: script exited {proc.returncode}\n{proc.stderr}")
    return json.loads(proc.stdout)


def check(fixture: str, exp: dict, failures: list) -> None:
    out = run(fixture)

    def fail(msg):
        failures.append(f"{fixture}: {msg}")

    if out["is_ai_tool"] != exp["is_ai_tool"]:
        fail(f"is_ai_tool = {out['is_ai_tool']}, expected {exp['is_ai_tool']}")

    for axis, want in exp["detectors"].items():
        got = {i["item"] for i in out["detectors"].get(axis, [])}
        if got != want:
            fail(f"axis {axis}: fired {sorted(got)}, expected {sorted(want)}")

    for (axis, item), want_ev in exp.get("evidence", {}).items():
        got_ev = next((i["evidence"] for i in out["detectors"].get(axis, [])
                       if i["item"] == item), None)
        if got_ev != want_ev:
            fail(f"axis {axis} item {item}: evidence {got_ev!r}, expected {want_ev!r}")

    if len(out["notes"]) != exp["notes"]:
        fail(f"{len(out['notes'])} notes, expected {exp['notes']}: {out['notes']}")
    if "note_contains" in exp and not any(exp["note_contains"] in n for n in out["notes"]):
        fail(f"no note containing {exp['note_contains']!r}: {out['notes']}")

    if len(out["errors"]) != exp["errors"]:
        fail(f"{len(out['errors'])} errors, expected {exp['errors']}: {out['errors']}")
    if "error_item" in exp and not any(e["item"] == exp["error_item"] for e in out["errors"]):
        fail(f"no error on item {exp['error_item']!r}: {out['errors']}")


# --- portfolio-hosted sec-audit reports (BL-003) --------------------------
# From sec-audit v1.29 the report lives at
# <portfolio_home>/security/reports/sec-audit-<ts>.md and NOTHING is written into
# the repo, so without --portfolio-home the Security axis can never fire again
# for any audited project. Each case pins one behaviour of that path.
PORTFOLIO_CASES = [
    # (label, project fixture, portfolio-home fixture or None,
    #  expected fired items, expected scope, notes, errors)
    ("portfolio-only fires with scope=portfolio",
     "portfolio-audited", "portfolio-home", {"sec-audit"}, "portfolio", 0, 0),
    ("without --portfolio-home the same project cannot fire",
     "portfolio-audited", None, set(), None, 0, 0),
    ("newest wins across both roots (portfolio newer than repo)",
     "portfolio-both", "portfolio-both-home", {"sec-audit"}, "portfolio", 0, 0),
    ("repo-only still fires with scope=repo (no regression)",
     "portfolio-both", None, set(), None, 1, 0),
    ("portfolio report with CRITICALs -> note, not a tick",
     "portfolio-dirty", "portfolio-dirty-home", set(), None, 1, 0),
    ("portfolio report missing Findings header -> stale-detector error",
     "portfolio-stale", "portfolio-stale-home", set(), None, 0, 1),
]


def run_with_home(fixture: str, home: str | None) -> dict:
    cmd = [sys.executable, str(SCRIPT), str(FIXTURES / fixture)]
    if home:
        cmd += ["--portfolio-home", str(FIXTURES / home)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"{fixture}: exited {proc.returncode}\n{proc.stderr}")
    return json.loads(proc.stdout)


def check_portfolio(failures: list) -> None:
    for label, fixture, home, want_items, want_scope, n_notes, n_errors in PORTFOLIO_CASES:
        out = run_with_home(fixture, home)
        sec = out["detectors"]["security"]
        got = {i["item"] for i in sec}
        if got != want_items:
            failures.append(f"{label}: fired {sorted(got)}, expected {sorted(want_items)}")
        if want_scope is not None:
            got_scope = next((i.get("scope") for i in sec if i["item"] == "sec-audit"), None)
            if got_scope != want_scope:
                failures.append(f"{label}: scope {got_scope!r}, expected {want_scope!r}")
        sec_notes = [n for n in out["notes"] if n.startswith("security:")]
        sec_errors = [e for e in out["errors"] if e.get("axis") == "security"]
        if len(sec_notes) != n_notes:
            failures.append(f"{label}: {len(sec_notes)} security notes, expected {n_notes}: {sec_notes}")
        if len(sec_errors) != n_errors:
            failures.append(f"{label}: {len(sec_errors)} security errors, expected {n_errors}: {sec_errors}")

    # A portfolio home that does not exist is NORMAL (project never audited, or
    # no vault) and must be silent, not an error.
    out = run_with_home("portfolio-audited", "definitely-not-here")
    if out["detectors"]["security"] or [e for e in out["errors"] if e.get("axis") == "security"]:
        failures.append("absent portfolio home should be silent, "
                        f"got {out['detectors']['security']} / {out['errors']}")


def main() -> int:
    if not SCRIPT.exists():
        print(f"FAIL: detector script not found at {SCRIPT}", file=sys.stderr)
        return 2
    failures: list = []
    for fixture, exp in EXPECTED.items():
        check(fixture, exp, failures)
    check_portfolio(failures)
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"OK — {len(EXPECTED)} fixtures passed "
          f"({', '.join(EXPECTED)}) "
          f"+ {len(PORTFOLIO_CASES)} portfolio-report cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
