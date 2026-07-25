#!/usr/bin/env python3
"""Fixture tests for the decisions register lane (per-project + per-domain).

Asserts the behaviours that make the register trustworthy:

  * a block missing a required field is FLAGGED, never dropped — an invisible
    decision is worse than a malformed one, since the register's whole job is
    that nothing binding goes unrecorded;
  * link symmetry is checked in BOTH directions (project Global: ↔ domain
    Applies to:) and reported, never auto-repaired — auto-fixing would assert
    an edge about a project the run has not read;
  * a link whose target does not exist is `unresolved`, distinct from an
    asymmetry, because the two need different fixes;
  * wrapped prose and nested list bullets both parse as one field value;
  * a project with no decisions.md contributes nothing and errors nothing.

No pytest. Plain assertions, non-zero exit on failure.
Run: python3 planning/skills/portfolio/tests/test-portfolio-decisions.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures" / "decisions"
_REBUILD = HERE.parent / "scripts" / "portfolio-rebuild.py"
_spec = importlib.util.spec_from_file_location("portfolio_rebuild", _REBUILD)
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)

fails: list[str] = []


def chk(cond, msg):
    if not cond:
        fails.append(msg)


def entry(entries, eid):
    for e in entries:
        if e["id"] == eid:
            return e
    return None


def main() -> int:
    vault = FIX
    port = vault / "Portfolio"

    # ---- per-project parse ------------------------------------------------
    mta = pr.read_project_decisions(port / "android" / "multitor-android")
    chk(mta is not None, "multitor-android decisions.md should be found")
    ids = [e["id"] for e in mta["entries"]]
    chk(ids == ["DEC-007", "DEC-006", "DEC-005"], f"newest-first block order broken: {ids}")

    d7 = entry(mta["entries"], "DEC-007")
    chk(d7["title"] == "Per-app Tor circuits via Orbot, not iptables owner-match",
        f"title parse: {d7['title']!r}")
    chk(d7["missing"] == [], f"DEC-007 is complete, got missing={d7['missing']}")
    chk("GrapheneOS per-app network policy" in d7["fields"]["Reason"],
        "wrapped Reason prose must join across lines")
    chk("hard Orbot dependency" in d7["fields"]["Reason"],
        "wrapped Reason must include its final line")
    chk("---" not in d7["fields"]["Reason"],
        "block separator must not bleed into the last field")
    chk(pr.decision_domains(d7) == ["android", "tor"], f"domains: {pr.decision_domains(d7)}")

    d6 = entry(mta["entries"], "DEC-006")
    chk(d6["fields"]["Status"] == "superseded by DEC-007", "superseded status must survive")

    # degrade-never-drop: DEC-005 lacks Domains / Source / Reason
    d5 = entry(mta["entries"], "DEC-005")
    chk(d5 is not None, "malformed block must still be returned, not dropped")
    chk(sorted(d5["missing"]) == ["Domains", "Reason", "Source"],
        f"malformed block must be flagged: {d5['missing']}")

    # `Domains: none` yields no domains but is not malformed
    orphan = pr.read_project_decisions(port / "ai-tools" / "orphan-proj")
    o1 = entry(orphan["entries"], "DEC-001")
    chk(o1["missing"] == [], f"'none' is a valid Domains value: {o1['missing']}")
    chk(pr.decision_domains(o1) == [], "'none' must expand to zero domains")

    # absent register
    chk(pr.read_project_decisions(port / "android" / "does-not-exist") is None,
        "a project with no decisions.md must return None, not an error")

    # ---- malformed HEADINGS (not just missing fields) ----------------------
    # Regression guard: boundary detection must be generic `## `, not the strict
    # ID regex. Otherwise a mistyped heading either vanishes (first in file) or
    # is swallowed into the previous block's last field (mid file).
    mh = pr.read_project_decisions(port / "android" / "malformed-headings")
    hids = [e["id"] for e in mh["entries"]]
    chk(hids == [None, "DEC-002", None, "DEC-001", None],
        f"malformed headings must be flagged in place, not dropped: {hids}")

    bad_first = mh["entries"][0]
    chk(bad_first["malformed_heading"] is True, "first-in-file bad heading must be flagged")
    chk("Hyphen instead of em-dash" in bad_first["heading"],
        f"raw heading must be preserved for the report: {bad_first['heading']!r}")
    chk("vanish without trace" in bad_first["fields"].get("Reason", ""),
        "a malformed-heading block must still have its body parsed")

    good = entry(mh["entries"], "DEC-002")
    chk("swallowed into DEC-002" not in good["fields"]["Reason"],
        f"following malformed block must NOT bleed into the previous Reason: "
        f"{good['fields']['Reason']!r}")
    chk(good["fields"]["Reason"] == "Final reason line.",
        f"Reason must end at the block boundary: {good['fields']['Reason']!r}")
    chk(good["duplicates"] == ["Status"],
        f"a repeated field must be flagged, not silently overwritten: {good['duplicates']}")
    chk("***" not in good["fields"]["Reason"],
        "non-hyphen horizontal rules must not leak into a field value")

    last = entry(mh["entries"], "DEC-001")
    chk(last["fields"]["Reason"] == "Intact.", "the final well-formed block must survive intact")

    # ---- per-domain parse -------------------------------------------------
    doms = pr.read_domain_decisions(vault)
    chk(sorted(doms) == ["android", "rust", "tor"], f"domain files discovered: {sorted(doms)}")
    g3 = entry(doms["android"]["entries"], "GDEC-AND-003")
    chk(g3 is not None and g3["missing"] == [], f"GDEC-AND-003 complete: {g3 and g3['missing']}")
    applied = pr.APPLIES_LINK_RE.findall(g3["fields"]["Applies to"])
    chk([n for _a, n in applied] == ["multitor-android", "tens-town"],
        f"nested Applies-to bullets must parse as one field: {applied}")

    # ---- symmetry ---------------------------------------------------------
    projs = {}
    for area, name in (("android", "multitor-android"), ("android", "nice-dns-android"),
                       ("ai-tools", "orphan-proj")):
        projs[name] = pr.read_project_decisions(port / area / name)
    asym, unres = pr.decision_symmetry(projs, doms)
    blob = " | ".join(asym)
    ublob = " | ".join(unres)

    # symmetric pair must NOT be reported
    chk("DEC-007" not in blob,
        f"DEC-007 ↔ GDEC-AND-003 is symmetric and must not be flagged: {blob}")

    # domain lists a project that never links back
    chk(any("GDEC-AND-011" in a and "multitor-android" in a for a in asym),
        f"one-sided Applies-to must be an asymmetry: {blob}")

    # project links a GDEC that does not exist
    chk(any("GDEC-AND-009" in u for u in unres),
        f"link to a missing domain entry must be unresolved: {ublob}")

    # domain applies to a project with no register at all
    chk(any("tens-town" in u for u in unres), f"tens-town must be unresolved: {ublob}")
    chk(any("appimage-control" in u for u in unres),
        f"appimage-control must be unresolved: {ublob}")

    # unresolved and asymmetric are distinct buckets
    chk(not any("GDEC-AND-009" in a for a in asym),
        "a missing target is unresolved, not an asymmetry")

    # a GDEC id defined in two domain files makes every link to it ambiguous
    chk(any("defined in both" in u and "GDEC-AND-003" in u for u in unres),
        f"cross-file GDEC id collision must be reported: {ublob}")

    # BL-014(a): an Applies-to wikilink with no `<area>/` prefix matched neither
    # direction of the symmetry check, so the edge silently did not exist.
    chk(any("without an" in u and "appimage-control" in u for u in unres),
        f"unprefixed Applies-to link must be flagged, not dropped: {ublob}")

    # BL-015: resolving on the GDEC id alone reported a link pointing at a
    # register that does not contain the entry as correct.
    chk(any("GDEC-AND-011" in u and "links" in u and "but that entry lives in" in u
            for u in unres),
        f"a Global link naming the wrong domain file must be reported: {ublob}")

    # BL-014(b): two blocks in one file claiming the same ID
    dup = pr.read_project_decisions(port / "ai-tools" / "dup-ids")
    chk(any("more than one block" in e and "DEC-001" in e for e in dup["errors"]),
        f"a duplicate ID within one register must be reported: {dup['errors']}")
    chk(len(dup["entries"]) == 2,
        "both blocks are still parsed — the duplicate is flagged, not dropped")

    # A malformed heading doesn't stop the block's fields parsing, so such an
    # entry can still carry a Global: link. It must report as unresolvable, not
    # emit a garbled "<project> None links ..." line.
    mh_sym, mh_unres = pr.decision_symmetry({"malformed-headings": mh}, doms)
    chk(not any(" None " in a for a in mh_sym + mh_unres),
        f"a None id must never be interpolated into a report line: {mh_sym + mh_unres}")
    chk(any("malformed heading" in u and "fix the heading first" in u for u in mh_unres),
        f"malformed heading + Global link must be reported as unresolvable: {mh_unres}")

    # a project with no decisions.md must not crash the symmetry check
    projs_with_none = dict(projs)
    projs_with_none["tens-town"] = pr.read_project_decisions(port / "android" / "tens-town")
    chk(projs_with_none["tens-town"] is None, "fixture sanity: tens-town has no register")
    try:
        pr.decision_symmetry(projs_with_none, doms)
    except Exception as exc:                                  # noqa: BLE001
        chk(False, f"None-valued project must degrade, not crash: {exc!r}")

    # ---- roll-up render ---------------------------------------------------
    reg = [{"area": "android", "name": "multitor-android"},
           {"area": "android", "name": "nice-dns-android"},
           {"area": "android", "name": "malformed-headings"},
           {"area": "ai-tools", "name": "orphan-proj"},
           {"area": "android", "name": "tens-town"}]        # no decisions.md
    md = pr.render_global_decisions(vault, reg)

    for section in ("# Global Decisions", "## By domain", "## By project",
                    "## Asymmetries (review)", "## Unresolved targets"):
        chk(section in md, f"roll-up missing section {section!r}")

    chk("### android" in md and "### rust" in md, "each domain register needs a section")
    chk("**GDEC-AND-003** — Circuit isolation" in md, "domain entries must be listed")
    chk("android/[[multitor-android]]" in md,
        "applies-to must render as an area-qualified wikilink")
    chk("| android/[[multitor-android]] | 3" in md,
        f"per-project count row wrong:\n{md}")
    chk("| ai-tools/[[orphan-proj]] | 1 | 1 | 0 | – |" in md,
        "a project with no domains renders an en-dash, not an empty cell")
    chk("tens-town" not in md.split("## Asymmetries")[0].split("## By project")[1],
        "a project with no decisions.md must not get a count row")

    # Malformed entries must be VISIBLE and ATTRIBUTABLE in the roll-up — the
    # register's contract is a flagged entry a reader can act on, not a bare
    # warning glyph in a count cell.
    chk("## Malformed entries (review)" in md, "roll-up needs a malformed-entry section")
    mal = md.split("## Malformed entries (review)")[1].split("## Asymmetries")[0]
    chk("DEC-005" in mal and "missing:" in mal,
        f"a block missing required fields must be named with what it lacks:\n{mal}")
    chk("malformed heading" in mal and "Hyphen instead of em-dash" in mal,
        f"a malformed heading must be named verbatim:\n{mal}")
    chk("duplicate field(s): Status" in mal, f"duplicate fields must be named:\n{mal}")
    chk("android/[[multitor-android]] DEC-005" in mal,
        "each malformed entry must say which project it is in")

    # the two report buckets carry the real findings
    tail = md.split("## Asymmetries (review)")[1]
    chk("GDEC-AND-011" in tail, f"asymmetry must be reported in the roll-up:\n{tail}")
    chk("defined in both" in tail, "id collision must be reported in the roll-up")
    chk("_None._" not in tail.split("## Unresolved targets")[0],
        "asymmetry section should not claim None when one exists")

    # ---- idempotency: write_if_changed must write once, not twice ---------
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "global-decisions.md"
        chk(pr.write_if_changed(target, md) is True, "first write must happen")
        chk(pr.write_if_changed(target, md) is False,
            "second identical write must be a no-op — rebuild idempotency guarantee")
        stamped = md.replace(f"**Last rebuilt:** {pr.TODAY}", "**Last rebuilt:** 2020-01-01")
        chk(pr.write_if_changed(target, stamped) is False,
            "a changed rebuild timestamp alone must NOT count as a change")

    # ---- sidecar pointer line ---------------------------------------------
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        (repo / ".claude").mkdir(parents=True)
        vd = Path(td) / "vault"

        # project WITHOUT a register: no Decisions line at all
        bare = vd / "Portfolio" / "x" / "bare"
        bare.mkdir(parents=True)
        pr.write_sidecar(repo, bare, vd, True)
        sc = (repo / ".claude" / "vault-context.md").read_text()
        chk("**Decisions:**" not in sc,
            "no decisions.md → no pointer line (a link to a missing file is worse than none)")
        chk("**Backlog:**" in sc, "unconditional pointers must still be written")

        # project WITH a register: pointer appears, still pointer-only
        withdec = vd / "Portfolio" / "x" / "withdec"
        withdec.mkdir(parents=True)
        (withdec / "decisions.md").write_text("# Decisions\n\n---\n\n## DEC-001 — t\n\n"
                                              "- **Decided:** 2026-01-01\n- **Status:** accepted\n"
                                              "- **Domains:** rust\n- **Source:** direct\n"
                                              "- **Reason:** because.\n")
        repo2 = Path(td) / "repo2"
        (repo2 / ".claude").mkdir(parents=True)
        pr.write_sidecar(repo2, withdec, vd, True)
        sc2 = (repo2 / ".claude" / "vault-context.md").read_text()
        line = [l for l in sc2.splitlines() if l.startswith("- **Decisions:**")]
        chk(len(line) == 1, f"exactly one Decisions pointer expected: {line}")
        chk(str(withdec / "decisions.md") in line[0], f"pointer must resolve: {line[0]}")
        chk(not any(ch.isdigit() for ch in line[0].split("](")[0]),
            f"pointer-only: no count may be embedded: {line[0]}")

        # idempotent: a second identical write is a no-op
        chk(pr.write_sidecar(repo2, withdec, vd, True) is False,
            "re-writing an unchanged sidecar must report no write")

    # ---- read-only guarantee ---------------------------------------------
    # Asserted around the functions that actually touch disk. decision_symmetry
    # operates purely on already-parsed dicts, so wrapping it alone would be a
    # check that cannot fail.
    def tree_state():
        return sorted((str(p.relative_to(port)), p.stat().st_mtime_ns, p.stat().st_size)
                      for p in port.rglob("*") if p.is_file())

    before = tree_state()
    pr.render_global_decisions(vault, reg)      # reads every register
    pr.read_domain_decisions(vault)
    pr.decision_symmetry(projs, doms)
    chk(before == tree_state(),
        "the decisions rebuild path must never write into the vault registers")

    if fails:
        print("FAILURES:", file=sys.stderr)
        for f in fails:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("OK — decisions register: block parse, wrapped/nested fields, "
          "degrade-never-drop, both-direction symmetry, unresolved-vs-asymmetric "
          "split and read-only guarantee all verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
