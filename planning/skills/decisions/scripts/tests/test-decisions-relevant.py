#!/usr/bin/env python3
"""Fixture tests for the decisions relevance lane (decisions-relevant.py).

Asserts the behaviours that make the digest trustworthy for a planner:

  * a block missing a required field, and a block whose heading is not an id at
    all, both appear in the digest FLAGGED — never dropped. A planner who is
    shown nothing concludes nothing binds them, which is the exact failure the
    register exists to prevent;
  * a superseded entry is included and marked, not filtered — "we believed X and
    stopped" is what stops the rejected approach being re-proposed;
  * an unknown domain slug is reported as unknown, distinct from a domain that
    exists and holds no entries;
  * a project with no decisions.md, and a project absent from the registry, both
    degrade to `project_register: absent` while the global half still returns —
    the greenfield path this lane exists for;
  * the reason digest cuts at a sentence boundary, never mid-word.

No pytest. Plain assertions, non-zero exit on failure.
Run: python3 planning/skills/decisions/scripts/tests/test-decisions-relevant.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXV = HERE / "fixtures" / "vault"
_SCRIPT = HERE.parent / "decisions-relevant.py"
_spec = importlib.util.spec_from_file_location("decisions_relevant", _SCRIPT)
dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dr)

fails: list[str] = []


def chk(cond, msg):
    if not cond:
        fails.append(msg)


def row(rows, rid):
    for r in rows:
        if r["id"] == rid:
            return r
    return None


# --- list_domains -----------------------------------------------------------
domains = dict((s, (n, e)) for s, n, e in dr.list_domains(FIXV))
chk("security" in domains, "list_domains: security register not listed")
chk("malformed" in domains, "list_domains: malformed register not listed")
chk(domains["security"][0] == 1, f"list_domains: security entry count {domains['security'][0]} != 1")
# The malformed register holds three blocks; the unparseable one still counts —
# it is present in the file and must be visible downstream.
chk(domains["malformed"][0] == 3,
    f"list_domains: malformed entry count {domains['malformed'][0]} != 3")

# --- degrade, never drop ----------------------------------------------------
d = dr.global_digest(FIXV, ["malformed"])
rows = d["global"]
chk(len(rows) == 3, f"global_digest: expected 3 rows from malformed register, got {len(rows)}")

missing_reason = row(rows, "GDEC-MAL-001")
chk(missing_reason is not None, "GDEC-MAL-001 (missing Reason) was DROPPED from the digest")
if missing_reason:
    chk(missing_reason["malformed"] is True, "GDEC-MAL-001 not flagged malformed")
    chk("Reason" in missing_reason["missing"],
        f"GDEC-MAL-001 missing-field list does not name Reason: {missing_reason['missing']}")

unparseable = [r for r in rows if r["id"] is None]
chk(len(unparseable) == 1, f"expected 1 unparseable-heading row, got {len(unparseable)}")
if unparseable:
    chk(unparseable[0]["malformed"] is True, "unparseable-heading row not flagged malformed")
    chk("not a GDEC id" in unparseable[0]["heading"],
        "unparseable-heading row lost its raw heading — it must stay visible for repair")

superseded = row(rows, "GDEC-MAL-002")
chk(superseded is not None, "GDEC-MAL-002 (superseded) was DROPPED from the digest")
if superseded:
    chk(superseded["superseded"] is True,
        f"superseded entry not marked: status={superseded['status']!r}")

# --- unknown vs empty domain ------------------------------------------------
u = dr.global_digest(FIXV, ["nosuchdomain"])
chk(u["unknown_domains"] == ["nosuchdomain"],
    f"unknown domain not reported: {u['unknown_domains']}")
chk(u["global"] == [], "unknown domain returned rows")
chk("security" in u["available_domains"],
    "unknown-domain report does not offer the available slugs")

# --- project half: present --------------------------------------------------
p = dr.project_digest(FIXV, "ai-tools", "fixture-project")
chk(p["project_register"] == "present",
    f"fixture-project should resolve: {p.get('project_reason')}")
chk([r["id"] for r in p["project"]] == ["DEC-001"],
    f"fixture-project decisions wrong: {[r['id'] for r in p['project']]}")

# --- project half: absent (unregistered) — the greenfield path ---------------
g = dr.project_digest(FIXV, "nowhere", "ghost-project")
chk(g["project_register"] == "absent", "unregistered project did not degrade to absent")
chk(g["project"] == [], "absent project returned rows")
chk(bool(g["project_reason"]), "absent project gave no stated reason")

# The global half must survive an absent project half: that combination IS the
# new-project case, and losing the global half there would leave a greenfield
# project consulting nothing.
combined = dr.global_digest(FIXV, ["security"])
combined.update(dr.project_digest(FIXV, "nowhere", "ghost-project"))
chk(len(combined["global"]) == 1,
    "global half was lost when the project half was absent — the greenfield path is broken")

# --- project half: absent but REGISTERED -------------------------------------
# Distinct from the unregistered case: the reason text differs, and that
# distinction is the whole point of consulting the registry. Injecting a fixture
# registry also makes this file hermetic — without it, project_digest falls
# through to the real ~/.claude/projects-registry.yaml on whoever's machine runs
# the suite, and the "registered" branch is never exercised at all.
REG = HERE / "fixtures" / "registry.yaml"
r = dr.project_digest(FIXV, "ai-tools", "registered-but-empty", registry=REG)
chk(r["project_register"] == "absent", "registered-but-empty should still be absent")
chk("registered but has" in r["project_reason"],
    f"registered branch not taken; reason was: {r['project_reason']!r}")

# ...and the unregistered branch must take the OTHER message against the same
# fixture registry, so the two are proven distinguishable rather than assumed.
r2 = dr.project_digest(FIXV, "nowhere", "ghost-project", registry=REG)
chk("not in the projects registry" in r2["project_reason"],
    f"unregistered branch not taken; reason was: {r2['project_reason']!r}")

chk(dr.registered_names(REG) == {"registered-but-empty"},
    f"fixture registry parsed wrong: {dr.registered_names(REG)}")

# --- no project identified --------------------------------------------------
n = dr.project_digest(FIXV, "", "")
chk(n["project_register"] == "absent", "no-project-given did not degrade to absent")

# --- first_sentence ---------------------------------------------------------
chk(dr.first_sentence("One. Two.") == "One.",
    f"first_sentence cut wrong: {dr.first_sentence('One. Two.')!r}")
long = "w" * 400
chk(dr.first_sentence(long).endswith("…"), "over-long reason not marked as elided")
chk("  " not in dr.first_sentence("a\n\n   b"), "whitespace not collapsed")
chk(dr.first_sentence("") == "", "empty reason should stay empty")

if fails:
    print(f"FAIL ({len(fails)}):")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("test-decisions-relevant: all assertions passed")
