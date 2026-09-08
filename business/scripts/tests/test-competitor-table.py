#!/usr/bin/env python3
"""Fixture suite for competitor-table.py — run directly (CI convention):
    python3 business/scripts/tests/test-competitor-table.py

Runs the script as a subprocess over fixtures/competitor-table/*.yaml and
asserts the JSON contract the market-research skill consumes: validation
(types, the conversion rule, schema gate, every rejection class), the −5…+5
normalization arithmetic against hand-computed values, quadrant assignment and
the empty-zone / nearest-neighbour report, the sweep's ranking and its
degenerate-axis exclusion, trajectory vectors and projection, SVG emission only
on request, byte-identical output across runs, and the read-only guarantee.

Every arithmetic check here is against a number computed by hand from the
fixture in the comment beside it, so a changed formula fails rather than
re-deriving the expectation from the code under test.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "competitor-table.py"
FIX = HERE / "fixtures" / "competitor-table"
HAPPY = FIX / "happy.yaml"

FAILURES = []


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                       capture_output=True, text=True)
    try:
        doc = json.loads(r.stdout) if r.stdout.strip() else None
    except json.JSONDecodeError:
        doc = None
    return r.returncode, doc, r.stderr


def tree_hash(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def write(tmp, name, text):
    p = Path(tmp) / name
    p.write_text(text)
    return p


MINI = """schema: 1
project: mini
updated: 2026-09-08
characteristics:
  - {id: a, category: company, type: number}
  - {id: b, category: company, type: number}
competitors:
  - {id: r1, class: direct, values: {a: 1, b: 10}}
  - {id: r2, class: direct, values: {a: 10, b: 20}}
  - {id: r3, class: indirect, values: {a: 1000, b: 30}}
"""


def test_validate_happy():
    rc, d, err = run("validate", HAPPY)
    check(rc == 0 and d and d["ok"], f"validate happy: exit 0, ok (stderr {err[:100]!r})")
    check(d["competitors_raw"] == 7, "validate: 7 raw competitors")
    check(d["rows"] == 5, "validate: 5 rows (2 groups + 3 standalone)")
    check(d["groups"] == ["point", "suites"], "validate: groups listed sorted")
    check(d["standalone"] == ["c3", "c6", "us"], "validate: standalone rows")
    check(d["classes"] == {"direct": 5, "indirect": 2}, "validate: class counts")
    check(d["found_by"] == {"alternatives": 2, "category": 3, "customer-job": 2},
          "validate: per-pass counts")
    check("color:green" in d["columns"] and "color" not in d["columns"],
          "validate: categorical expanded into color:<value>, no bare categorical column")
    check(d["history_years"] == [2024, 2025], "validate: history years collected")
    check(d["self"] == "us" and d["year"] == 2026, "validate: self and Y0 year from updated")


def test_normalize_math():
    rc, d, _ = run("normalize", HAPPY)
    check(rc == 0 and d["ok"], "normalize: exit 0")
    cols = {c["id"]: c for c in d["columns"]}
    rows = {r["id"]: r for r in d["rows"]}
    # rating: values 4.5 3.6 2.4 4.0 4.7 4.1 3.8 → median 4.0; half = max(0.7, 1.6) = 1.6
    check(cols["rating"]["centre"] == 4.0 and cols["rating"]["half_range"] == 1.6,
          "normalize: rating centre 4.0 / half 1.6 (median)")
    check(rows["c5"]["scores"]["rating"] == 2.1875, "normalize: c5 rating 5*(0.7)/1.6 = 2.1875")
    check(rows["c3"]["scores"]["rating"] == -5.0, "normalize: c3 rating at the −5 pole")
    # geo_difficulty: 2 2 4 3 1 3 → median 2.5, half 1.5; c5=1 → −5 → invert → +5
    check(rows["c5"]["scores"]["geo_difficulty"] == 5.0, "normalize: invert negates (c5 geo → +5)")
    check(rows["c6"]["scores"]["geo_difficulty"] is None, "normalize: missing value → null score")
    # revenue is declared log: log10 values 6.301 6.176 5.114 5 4.903 4.699 4.301 → median 5.0
    check(cols["revenue"]["scale"] == "log" and cols["revenue"]["centre"] == 5.0,
          "normalize: revenue log scale, centre log10(100000)=5")
    check(rows["c1"]["scores"]["revenue"] == 5.0, "normalize: max revenue at +5 on log axis")
    # growth: "8%" string → 8; values 8 4 1 15 7 2 40 → median 7, half = 33
    check(cols["growth"]["centre"] == 7.0 and cols["growth"]["half_range"] == 33.0,
          "normalize: percentage strings coerced ('8%' → 8)")
    check(rows["c1"]["scores"]["growth"] == round(5 * 1 / 33, 4), "normalize: c1 growth 5*(1/33)")
    # flags: yes/true → 1.0, no → 0.0; median of 1 1 0 0 1 1 1 = 1, half = 1
    check(rows["c6"]["scores"]["self_service"] == 0.0 and rows["c3"]["scores"]["self_service"] == -5.0,
          "normalize: flag yes/true → +0 at centre, no → −5")
    check(rows["us"]["scores"]["color:multi"] == 5.0 and rows["c1"]["scores"]["color:multi"] == 0.0,
          "normalize: one-hot categorical scored (median 0, half 1)")
    # history projected on the Y0 map: c1 2024 revenue 900000 → log 5.954 → 5*(0.954)/1.301
    h = rows["c1"]["history"]["2024"]["revenue"]
    check(abs(h - 5 * (5.9542 - 5.0) / 1.301) < 0.01, f"normalize: history scored on Y0 params (got {h})")


def test_auto_scale_and_mean():
    with tempfile.TemporaryDirectory() as td:
        p = write(td, "mini.yaml", MINI)
        rc, d, _ = run("normalize", p)
        cols = {c["id"]: c for c in d["columns"]}
        check(cols["a"]["scale"] == "log", "auto: ratio 1000 ≥ 100 → log")
        check(cols["b"]["scale"] == "linear", "auto: ratio 3 → linear")
        p2 = write(td, "mean.yaml", MINI.replace("updated: 2026-09-08", "updated: 2026-09-08\ncenter: mean"))
        rc, d2, _ = run("normalize", p2)
        cols2 = {c["id"]: c for c in d2["columns"]}
        check(cols2["b"]["centre"] == 20.0 and cols["b"]["centre"] == 20.0,
              "centre: b median==mean==20 (sanity)")
        # a on log: 0,1,3 → median 1, mean 1.3333
        check(cols["a"]["centre"] == 1.0 and cols2["a"]["centre"] == 1.3333,
              "centre: median 1.0 vs mean 1.3333 on the log axis")


def test_rejections():
    with tempfile.TemporaryDirectory() as td:
        cases = {
            "schema-missing": (MINI.replace("schema: 1\n", ""), "missing 'schema'"),
            "schema-newer": (MINI.replace("schema: 1", "schema: 2"), "upgrade the business plugin"),
            "schema-bool": (MINI.replace("schema: 1", "schema: true"), "must be an integer"),
            "unknown-char": (MINI.replace("{a: 1, b: 10}", "{a: 1, b: 10, zz: 3}"),
                             "unknown characteristic 'zz'"),
            "bad-flag": (MINI.replace("type: number}\n  - {id: b", "type: flag}\n  - {id: b")
                         .replace("{a: 1, b: 10}", "{a: maybe, b: 10}"), "not yes/no/true/false"),
            "log-nonpositive": (MINI.replace("{id: a, category: company, type: number}",
                                             "{id: a, category: company, type: number, scale: log}")
                                .replace("{a: 1, b: 10}", "{a: 0, b: 10}"), "non-positive"),
            "dup-row": (MINI.replace("id: r2", "id: r1"), "duplicate id 'r1'"),
            "dup-char": (MINI.replace("id: b,", "id: a,"), "duplicate id 'a'"),
            "bad-class": (MINI.replace("class: indirect", "class: non-consumption"),
                          "non-consumption is not a row"),
            "bad-category": (MINI.replace("{id: a, category: company", "{id: a, category: vibes"),
                             "category 'vibes'"),
            "cat-scale": (MINI.replace("{id: b, category: company, type: number}",
                                       "{id: b, category: company, type: categorical, scale: log}")
                          .replace("b: 10", "b: x").replace("b: 20", "b: y").replace("b: 30", "b: z"),
                          "categorical column has no scale"),
            "self-unknown": (MINI.replace("updated: 2026-09-08", "updated: 2026-09-08\nself: nobody"),
                             "'self' 'nobody' is not a competitor id"),
            "history-future": (MINI.replace("{id: r1, class: direct, values: {a: 1, b: 10}}",
                                            "{id: r1, class: direct, values: {a: 1, b: 10}, "
                                            "history: {2027: {a: 2}}}"), "not before Y0"),
            "bad-date": (MINI.replace("2026-09-08", "yesterday"), "not YYYY-MM-DD"),
            "bad-pass": (MINI.replace("class: indirect", "class: indirect, found_by: guess"),
                         "found_by 'guess'"),
        }
        for name, (text, needle) in cases.items():
            p = write(td, f"{name}.yaml", text)
            rc, d, _ = run("validate", p)
            errs = " | ".join((d or {}).get("errors", []))
            check(rc == 1 and d is not None and not d["ok"] and needle in errs,
                  f"reject {name}: exit 1 with {needle!r} (got {errs[:120]!r})")
        # a validation error blocks every downstream command, and writes no SVG
        p = write(td, "bad.yaml", cases["unknown-char"][0])
        svg = Path(td) / "never.svg"
        rc, d, _ = run("quadrant", p, "--x", "a", "--y", "b", "--svg", svg)
        check(rc == 1 and not svg.exists(), "quadrant on an invalid table: exit 1, no SVG written")
        # top-level junk
        p = write(td, "junk.yaml", "- just\n- a list\n")
        rc, d, _ = run("validate", p)
        check(rc == 1 and "top level must be a mapping" in " ".join(d["errors"]),
              "reject junk: top-level list")


def test_quadrant():
    rc, d, _ = run("quadrant", HAPPY, "--x", "revenue", "--y", "rating", "--size", "headcount")
    check(rc == 0 and d["ok"], "quadrant: exit 0")
    q = {p["id"]: p["quadrant"] for p in d["points"]}
    # revenue log scores: c1 +5, c2 +4.52, c3 +0.44, c4 0, c5 −0.37, c6 −1.16, us −2.69
    # rating scores:      c1 +1.56, c2 −1.25, c3 −5, c4 0, c5 +2.19, c6 +0.31, us −0.63
    check(q == {"c1": "I", "c2": "IV", "c3": "IV", "c4": "I", "c5": "II", "c6": "II", "us": "III"},
          f"quadrant: assignments (got {q})")
    check(d["empty_quadrants"] == [] and d["most_crowded"] == "IV",
          "quadrant: no empty quadrant; IV most crowded (c2, c3)")
    check(d["self"] == {"id": "us", "nearest": {"id": "c6", "distance": 1.7938}},
          f"quadrant: self nearest is c6 at 1.7938 (got {d['self']})")
    check(d["points"][0]["size"] == 120.0, "quadrant: size carries the raw headcount")
    # geo_difficulty is missing for c6 → skipped on that axis, and reported
    rc, d2, _ = run("quadrant", HAPPY, "--x", "geo_difficulty", "--y", "rating")
    check(d2["skipped"] == ["c6"] and all(p["id"] != "c6" for p in d2["points"]),
          "quadrant: row with a missing axis value is skipped and named")
    # an axis pair that leaves quadrants empty is reported as such
    with tempfile.TemporaryDirectory() as td:
        p = write(td, "mini.yaml", MINI)
        rc, d3, _ = run("quadrant", p, "--x", "a", "--y", "b")
        # a log: −5 0 +5 ; b: −5 0 +5 → all on the diagonal → II and IV empty
        check(sorted(d3["empty_quadrants"]) == ["II", "IV"], f"quadrant: empty zones (got {d3['empty_quadrants']})")
    rc, d4, err = run("quadrant", HAPPY, "--x", "nope", "--y", "rating")
    check(rc != 0 and "not a numeric column" in err, "quadrant: unknown axis is a usage error")


def test_sweep():
    rc, d, _ = run("sweep", HAPPY, "--top", "5")
    check(rc == 0 and d["ok"], "sweep: exit 0")
    ex = d["excluded_columns"]
    check(set(ex) == {"color:green", "color:multi", "color:red", "color:white", "color:yellow"},
          f"sweep: single-row one-hot columns excluded as degenerate (got {sorted(ex)})")
    check("color:blue" in d["columns"] and "self_service" in d["columns"],
          "sweep: a two-row flag state is a real axis")
    iso = [p["self_isolation"] for p in d["top"]]
    check(iso == sorted(iso, reverse=True) and iso[0] > 4.5,
          f"sweep: ranked by self isolation desc (got {iso})")
    check(d["pairs_evaluated"] == 28, "sweep: C(8,2)=28 pairs over the 8 admissible columns")
    check(set(d["groups"]) == {"point", "suites"} and d["groups"]["suites"]["scatters"] is False,
          "sweep: per-group cohesion report, neither group scatters")
    rc2, d2, _ = run("sweep", HAPPY, "--top", "5")
    check(d == d2, "sweep: deterministic across runs")
    with tempfile.TemporaryDirectory() as td:
        # no self → ranked by empty quadrants then spread
        p = write(td, "mini.yaml", MINI)
        rc, d3, _ = run("sweep", p)
        check(d3["top"][0]["self_isolation"] is None and d3["top"][0]["empty_quadrants"] == 2,
              "sweep without self: isolation null, empty-quadrant rank leads")
        # a group that scatters is flagged
        scat = MINI.replace("{id: r1, class: direct,", "{id: r1, class: direct, group: g,") \
                   .replace("{id: r3, class: indirect,", "{id: r3, class: indirect, group: g,")
        p = write(td, "scatter.yaml", scat)
        rc, d4, _ = run("sweep", p)
        check(d4["groups"]["g"]["scatters"] is True, "sweep: a group at the two poles scatters")


def test_trajectory_and_svg():
    with tempfile.TemporaryDirectory() as td:
        svg = Path(td) / "t.svg"
        rc, d, _ = run("trajectory", HAPPY, "--x", "revenue", "--y", "customers",
                       "--size", "headcount", "--svg", svg)
        check(rc == 0 and d["ok"] and d["year"] == 2026, "trajectory: exit 0, Y0 2026")
        rows = {r["id"]: r for r in d["rows"]}
        v = rows["c1"]["vector"]
        check(v["years"] == 2 and v["size_change"] == 60.0, "trajectory: c1 spans 2 years, +60 headcount")
        check([s["year"] for s in rows["c1"]["states"]] == [2024, 2025, 2026], "trajectory: Y-2 Y-1 Y0 states")
        check([p["year"] for p in rows["c1"]["projected"]] == [2027, 2028], "trajectory: projected Y+1 Y+2")
        check(rows["c1"]["projected"][1]["x"] == 5.0, "trajectory: projection clamped to +5")
        check(rows["c3"]["vector"] is None and rows["c3"]["projected"] == [],
              "trajectory: no history → no vector")
        # us: 2025 → 2026, one year; moving right strongly on revenue
        check(rows["us"]["vector"]["years"] == 1 and rows["us"]["vector"]["dx_per_year"] > 2,
              "trajectory: single prior year gives a one-year vector")
        check(d["clearing_quadrants"] == ["III"], f"trajectory: III clears (us leaves it) (got {d['clearing_quadrants']})")
        check(svg.exists() and d["svg"] == str(svg), "trajectory: SVG written on request")
        text = svg.read_text()
        check("<svg" in text and "Alpha" in text and "stroke-dasharray" in text,
              "trajectory: SVG carries names and the dashed projection")
        rc, d2, _ = run("trajectory", HAPPY, "--x", "revenue", "--y", "customers", "--ahead", "1")
        check(len(rows and d2["rows"][0]["projected"]) == 1 and "occupancy_y+1" in d2,
              "trajectory: --ahead 1 projects one year")
        rc, d5, _ = run("trajectory", HAPPY, "--x", "revenue", "--y", "customers")
        check("svg" not in d5, "trajectory: no SVG key without --svg")

        q1 = Path(td) / "q1.svg"
        q2 = Path(td) / "q2.svg"
        run("quadrant", HAPPY, "--x", "revenue", "--y", "rating", "--size", "headcount", "--svg", q1)
        run("quadrant", HAPPY, "--x", "revenue", "--y", "rating", "--size", "headcount", "--svg", q2)
        check(q1.read_bytes() == q2.read_bytes(), "quadrant: SVG byte-identical across runs")
        qt = q1.read_text()
        check('fill="#3b6"' in qt and "Gamma" in qt and 'text-anchor="end">Alpha' in qt,
              "quadrant: self filled, names labelled, right-edge label flipped")


def test_read_only():
    before = tree_hash(FIX)
    for args in (["validate"], ["normalize"], ["sweep"],
                 ["quadrant", "--x", "revenue", "--y", "rating"],
                 ["trajectory", "--x", "revenue", "--y", "customers"]):
        run(args[0], HAPPY, *args[1:])
    check(tree_hash(FIX) == before, "read-only: fixture tree unchanged by every command")


def main():
    for t in (test_validate_happy, test_normalize_math, test_auto_scale_and_mean,
              test_rejections, test_quadrant, test_sweep, test_trajectory_and_svg,
              test_read_only):
        print(f"== {t.__name__}")
        t()
    if FAILURES:
        print(f"\nFAIL: {len(FAILURES)} check(s) failed:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("\nOK — competitor-table.py contract holds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
