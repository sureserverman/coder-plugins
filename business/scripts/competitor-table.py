#!/usr/bin/env python3
"""competitor-table — deterministic lane for the competitor table (method §7–§9).

The competitor table is the main working artifact of a competitive analysis:
competitors down, characteristics across, every cell a quantity. The table is
unreadable; the chart makes it readable. Building bubble charts and sweeping axis
pairs is mechanical work, so it lives here, not in the model.

    competitor-table.py validate   FILE
    competitor-table.py normalize  FILE
    competitor-table.py quadrant   FILE --x COL --y COL [--size COL] [--svg OUT]
    competitor-table.py sweep      FILE [--size COL] [--top N]
    competitor-table.py trajectory FILE --x COL --y COL [--size COL] [--svg OUT] [--ahead N]

Every command prints ONE JSON document on stdout. Exit 0 on success, 1 when the
table fails validation (the JSON carries `errors`), 2 on a usage error. Read-only
by construction except for the SVG an `--svg PATH` explicitly asks for.

This is the SOLE parser of competitor-table.yaml (references/competitor-table-format.md).
business-scan.py never opens it; the row count and coverage the roll-up shows come
from market-research.md's frontmatter, which the skill writes from this script's
`validate` output. No LLM in this lane: which axes matter is the operator's call, and
`sweep` only proposes an order to look in.
"""
import argparse
import datetime
import json
import math
import re
import statistics
import sys
from pathlib import Path

import yaml

SUPPORTED_SCHEMA = 1
CATEGORIES = {"quantitative-product", "qualitative-product", "target-market", "company"}
TYPES = {"number", "percentage", "flag", "score", "categorical"}
SCALES = {"linear", "log", "auto"}
CLASSES = {"direct", "indirect"}
PASSES = {"category", "customer-job", "alternatives"}
CENTERS = {"median", "mean"}
# "ratio between the extremes" — auto picks log when max/min reaches this.
AUTO_LOG_RATIO = 100.0
ID_RE = re.compile(r"^[a-z0-9_]+$")
ROW_ID_RE = re.compile(r"^[a-z0-9_-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TRUE = {"yes", "true", "1", "y"}
FALSE = {"no", "false", "0", "n"}

# SVG geometry. Fixed so two runs over the same table are byte-identical.
SVG_SIZE = 640
SVG_PAD = 40
R_MIN, R_MAX = 5.0, 28.0


# --- loading -----------------------------------------------------------------------

def load(path):
    """Parse and validate the table. Returns (table, errors). `table` is None only
    when nothing usable could be read; otherwise a dict the other commands consume,
    possibly alongside a non-empty errors list (which makes the run exit 1)."""
    errors = []
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        return None, [f"{path}: could not read/parse YAML ({e.__class__.__name__}: {e})"]
    if not isinstance(raw, dict):
        return None, [f"{path}: top level must be a mapping"]

    schema = raw.get("schema")
    if schema is None:
        return None, ["missing 'schema'"]
    if not isinstance(schema, int) or isinstance(schema, bool):
        return None, [f"'schema' must be an integer, got {schema!r}"]
    if schema > SUPPORTED_SCHEMA:
        return None, [f"schema {schema} is newer than supported ({SUPPORTED_SCHEMA}) "
                      f"— upgrade the business plugin"]
    if schema < 1:
        return None, [f"schema {schema} is below 1"]

    project = raw.get("project")
    if not isinstance(project, str) or not project:
        errors.append("missing 'project'")
    updated = raw.get("updated")
    if isinstance(updated, datetime.date):
        updated = updated.isoformat()
    if not isinstance(updated, str) or not DATE_RE.match(updated):
        errors.append(f"'updated' {updated!r} is not YYYY-MM-DD")
        updated = None
    year = raw.get("year")
    if year is None and updated:
        year = int(updated[:4])
    if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
        errors.append(f"'year' must be an integer, got {year!r}")
        year = None
    center = raw.get("center", "median")
    if center not in CENTERS:
        errors.append(f"'center' {center!r} not one of {sorted(CENTERS)}")
        center = "median"

    chars, cerrs = _load_characteristics(raw.get("characteristics"))
    errors += cerrs
    rows, rerrs = _load_rows(raw.get("competitors"), chars, year)
    errors += rerrs

    self_id = raw.get("self")
    if self_id is not None and self_id not in {r["id"] for r in rows}:
        errors.append(f"'self' {self_id!r} is not a competitor id")
        self_id = None

    columns = _expand_columns(chars, rows)
    table = {"project": project, "updated": updated, "year": year, "center": center,
             "self": self_id, "characteristics": chars, "columns": columns, "rows": rows}
    # Column arithmetic problems (a log axis with a zero in it) are table defects,
    # so `validate` surfaces them rather than leaving them for the first chart.
    if not errors:
        for col in columns:
            errors += column_params(table, col)[3]
    return table, errors


def _load_characteristics(raw):
    errors, out, seen = [], [], set()
    if not isinstance(raw, list) or not raw:
        return out, ["'characteristics' must be a non-empty list"]
    for i, c in enumerate(raw):
        if not isinstance(c, dict):
            errors.append(f"characteristics[{i}] must be a mapping")
            continue
        cid = c.get("id")
        if not isinstance(cid, str) or not ID_RE.match(cid):
            errors.append(f"characteristics[{i}]: id {cid!r} must match [a-z0-9_]+")
            continue
        if cid in seen:
            errors.append(f"characteristics[{i}]: duplicate id {cid!r}")
            continue
        seen.add(cid)
        ctype = c.get("type")
        if ctype not in TYPES:
            errors.append(f"characteristic {cid!r}: type {ctype!r} not one of {sorted(TYPES)}")
            continue
        cat = c.get("category")
        if cat not in CATEGORIES:
            errors.append(f"characteristic {cid!r}: category {cat!r} not one of "
                          f"{sorted(CATEGORIES)}")
        scale = c.get("scale", "auto")
        if scale not in SCALES:
            errors.append(f"characteristic {cid!r}: scale {scale!r} not one of {sorted(SCALES)}")
            scale = "auto"
        if ctype == "categorical" and scale != "auto":
            errors.append(f"characteristic {cid!r}: a categorical column has no scale")
        invert = c.get("invert", False)
        if not isinstance(invert, bool):
            errors.append(f"characteristic {cid!r}: invert must be true/false")
            invert = False
        out.append({"id": cid, "label": c.get("label") or cid, "category": cat,
                    "type": ctype, "scale": scale, "invert": invert,
                    "source": c.get("source")})
    return out, errors


def _coerce(value, ctype, where):
    """One cell → (float_or_str_or_None, error_or_None) per the conversion rule."""
    if value is None:
        return None, None
    if ctype == "categorical":
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            return None, f"{where}: categorical value must be a string, got {value!r}"
        return str(value), None
    if ctype == "flag":
        if isinstance(value, bool):
            return (1.0 if value else 0.0), None
        s = str(value).strip().lower()
        if s in TRUE:
            return 1.0, None
        if s in FALSE:
            return 0.0, None
        return None, f"{where}: flag value {value!r} is not yes/no/true/false/1/0"
    if ctype == "percentage" and isinstance(value, str):
        s = value.strip()
        if s.endswith("%"):
            s = s[:-1].strip()
        try:
            return float(s), None
        except ValueError:
            return None, f"{where}: percentage {value!r} is not a number"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, f"{where}: {ctype} value {value!r} is not a number"
    if isinstance(value, float) and not math.isfinite(value):
        return None, f"{where}: {ctype} value {value!r} is not finite"
    return float(value), None


def _load_values(raw, chars, where):
    """A `values`/history mapping → {char_id: coerced}, plus errors."""
    errors, out = [], {}
    if raw is None:
        return out, errors
    if not isinstance(raw, dict):
        return out, [f"{where}: values must be a mapping"]
    by_id = {c["id"]: c for c in chars}
    for k, v in raw.items():
        c = by_id.get(k)
        if c is None:
            errors.append(f"{where}: unknown characteristic {k!r}")
            continue
        val, err = _coerce(v, c["type"], f"{where}.{k}")
        if err:
            errors.append(err)
            continue
        out[k] = val
    return out, errors


def _load_rows(raw, chars, year):
    errors, out, seen = [], [], set()
    if not isinstance(raw, list) or not raw:
        return out, ["'competitors' must be a non-empty list"]
    for i, r in enumerate(raw):
        if not isinstance(r, dict):
            errors.append(f"competitors[{i}] must be a mapping")
            continue
        rid = r.get("id")
        if not isinstance(rid, str) or not ROW_ID_RE.match(rid):
            errors.append(f"competitors[{i}]: id {rid!r} must match [a-z0-9_-]+")
            continue
        if rid in seen:
            errors.append(f"competitors[{i}]: duplicate id {rid!r}")
            continue
        seen.add(rid)
        where = f"competitor {rid!r}"
        cls = r.get("class")
        if cls not in CLASSES:
            errors.append(f"{where}: class {cls!r} not one of {sorted(CLASSES)} "
                          f"(non-consumption is not a row)")
        found_by = r.get("found_by")
        if found_by is not None and found_by not in PASSES:
            errors.append(f"{where}: found_by {found_by!r} not one of {sorted(PASSES)}")
        group = r.get("group")
        if group is not None and not isinstance(group, str):
            errors.append(f"{where}: group must be a string")
            group = None
        values, verrs = _load_values(r.get("values"), chars, f"{where}.values")
        errors += verrs
        history = {}
        hraw = r.get("history") or {}
        if not isinstance(hraw, dict):
            errors.append(f"{where}: history must be a mapping of year → values")
            hraw = {}
        for y, hv in hraw.items():
            try:
                yi = int(y)
            except (TypeError, ValueError):
                errors.append(f"{where}: history year {y!r} is not an integer")
                continue
            if year is not None and yi >= year:
                errors.append(f"{where}: history year {yi} is not before Y0 ({year})")
                continue
            hvals, herrs = _load_values(hv, chars, f"{where}.history[{yi}]")
            errors += herrs
            history[yi] = hvals
        out.append({"id": rid, "name": r.get("name") or rid, "class": cls,
                    "group": group, "found_by": found_by, "source": r.get("source"),
                    "values": values, "history": history})
    return out, errors


def _expand_columns(chars, rows):
    """The numeric column set: every non-categorical characteristic as itself, every
    categorical one as `<id>:<value>` flags over the values observed anywhere (Y0 or
    history). Returns [{id, label, category, scale, invert, source_char}]."""
    cols = []
    for c in chars:
        if c["type"] != "categorical":
            cols.append({"id": c["id"], "label": c["label"], "category": c["category"],
                         "scale": c["scale"], "invert": c["invert"], "type": c["type"],
                         "source_char": c["id"]})
            continue
        observed = set()
        for r in rows:
            v = r["values"].get(c["id"])
            if v is not None:
                observed.add(v)
            for hv in r["history"].values():
                if hv.get(c["id"]) is not None:
                    observed.add(hv[c["id"]])
        for v in sorted(observed):
            cols.append({"id": f"{c['id']}:{v}", "label": f"{c['label']} = {v}",
                         "category": c["category"], "scale": "linear", "invert": c["invert"],
                         "type": "flag", "source_char": c["id"]})
    return cols


def _cell(row_values, col):
    """Raw numeric value of a column for one values-map, or None."""
    src = col["source_char"]
    v = row_values.get(src)
    if v is None:
        return None
    if col["type"] == "flag" and col["id"] != src:      # expanded categorical
        return 1.0 if v == col["id"].split(":", 1)[1] else 0.0
    return v


# --- normalization -------------------------------------------------------------------

def column_params(table, col):
    """(transform, centre, half-range, errors) from the Y0 values of one column."""
    raw = [_cell(r["values"], col) for r in table["rows"]]
    vals = [v for v in raw if v is not None]
    errors = []
    if not vals:
        return None, None, None, [f"column {col['id']!r}: no values"]
    scale = col["scale"]
    if scale == "auto":
        positive = all(v > 0 for v in vals)
        scale = "log" if positive and max(vals) / min(vals) >= AUTO_LOG_RATIO else "linear"
    if scale == "log":
        bad = [r["id"] for r, v in zip(table["rows"], raw) if v is not None and v <= 0]
        if bad:
            return None, None, None, [f"column {col['id']!r}: log scale with non-positive "
                                      f"value(s) in {bad} — set scale: linear or fix the datum"]
        tvals = [math.log10(v) for v in vals]
    else:
        tvals = list(vals)
    centre = statistics.median(tvals) if table["center"] == "median" else statistics.fmean(tvals)
    half = max(max(tvals) - centre, centre - min(tvals))
    return scale, centre, half, errors


def score(value, scale, centre, half, invert):
    if value is None:
        return None
    if scale == "log":
        if value <= 0:
            return None
        value = math.log10(value)
    s = 0.0 if half == 0 else 5.0 * (value - centre) / half
    s = round(s, 4)
    return -s if invert else s


def normalize(table):
    """Every row scored on every column (Y0 and history). Returns (doc, errors)."""
    params, errors = {}, []
    for col in table["columns"]:
        scale, centre, half, errs = column_params(table, col)
        errors += errs
        if scale is not None:
            params[col["id"]] = (scale, centre, half, col["invert"])
    rows = []
    for r in table["rows"]:
        scores, hist = {}, {}
        for col in table["columns"]:
            p = params.get(col["id"])
            if p is None:
                continue
            scores[col["id"]] = score(_cell(r["values"], col), *p)
            for y, hv in r["history"].items():
                hist.setdefault(y, {})[col["id"]] = score(_cell(hv, col), *p)
        rows.append({"id": r["id"], "name": r["name"], "class": r["class"],
                     "group": r["group"], "found_by": r["found_by"],
                     "scores": scores, "history": {str(y): v for y, v in sorted(hist.items())}})
    columns = [{"id": c["id"], "label": c["label"], "category": c["category"],
                "scale": params[c["id"]][0], "centre": round(params[c["id"]][1], 4),
                "half_range": round(params[c["id"]][2], 4), "invert": c["invert"]}
               for c in table["columns"] if c["id"] in params]
    return {"project": table["project"], "center": table["center"], "self": table["self"],
            "columns": columns, "rows": rows}, errors


# --- geometry ------------------------------------------------------------------------

def _col(table, cid, flag):
    for c in table["columns"]:
        if c["id"] == cid:
            return c
    sys.exit(f"usage: --{flag} {cid!r} is not a numeric column "
             f"(have: {', '.join(c['id'] for c in table['columns'])})")


def _quadrant_name(x, y):
    if x >= 0 and y >= 0:
        return "I"          # upper right
    if x < 0 and y >= 0:
        return "II"         # upper left
    if x < 0 and y < 0:
        return "III"        # lower left
    return "IV"             # lower right


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _size_of(row_values, size_col):
    if size_col is None:
        return None
    return _cell(row_values, size_col)


def _points(norm, table, x, y, size_col, values_key="values", year=None):
    """[{id, name, group, class, x, y, size}] for rows carrying both axes."""
    pts, skipped = [], []
    by_id = {r["id"]: r for r in table["rows"]}
    for r in norm["rows"]:
        src = r["scores"] if year is None else r["history"].get(str(year), {})
        sx, sy = src.get(x), src.get(y)
        if sx is None or sy is None:
            skipped.append(r["id"])
            continue
        raw = by_id[r["id"]]["values"] if year is None else by_id[r["id"]]["history"].get(year, {})
        pts.append({"id": r["id"], "name": r["name"], "group": r["group"], "class": r["class"],
                    "x": sx, "y": sy, "size": _size_of(raw, size_col)})
    return pts, skipped


def quadrant(table, x, y, size_id=None):
    norm, errors = normalize(table)
    xc, yc = _col(table, x, "x"), _col(table, y, "y")
    size_col = _col(table, size_id, "size") if size_id else None
    pts, skipped = _points(norm, table, x, y, size_col)
    quads = {"I": [], "II": [], "III": [], "IV": []}
    for p in pts:
        p["quadrant"] = _quadrant_name(p["x"], p["y"])
        quads[p["quadrant"]].append(p["id"])
    nearest = {}
    for p in pts:
        others = [(q["id"], _dist((p["x"], p["y"]), (q["x"], q["y"]))) for q in pts if q is not p]
        if others:
            nid, d = min(others, key=lambda t: (t[1], t[0]))
            nearest[p["id"]] = {"id": nid, "distance": round(d, 4)}
    self_id = table["self"]
    doc = {"project": table["project"],
           "axes": {"x": {"id": x, "label": xc["label"]}, "y": {"id": y, "label": yc["label"]},
                    "size": size_id},
           "points": pts, "quadrants": quads,
           "empty_quadrants": [k for k, v in quads.items() if not v],
           "most_crowded": max(quads, key=lambda k: (len(quads[k]), k)) if pts else None,
           "nearest": nearest, "skipped": skipped,
           "self": ({"id": self_id, **({"nearest": nearest[self_id]} if self_id in nearest else {})}
                    if self_id else None)}
    return doc, errors


def sweep(table, size_id=None, top=10):
    norm, errors = normalize(table)
    size_col = _col(table, size_id, "size") if size_id else None
    cols, excluded = [], {}
    for c in norm["columns"]:
        vals = [r["scores"][c["id"]] for r in norm["rows"] if r["scores"].get(c["id"]) is not None]
        distinct = sorted(set(vals))
        if len(distinct) < 2:
            excluded[c["id"]] = "constant column — no contrast"
            continue
        # A flag (or one-hot categorical value) held by a single row is a degenerate
        # axis: it puts that row alone by construction, which is not the "point where
        # you differ from everyone" the sweep exists to find (method §8).
        if len(distinct) == 2 and min(vals.count(distinct[0]), vals.count(distinct[1])) < 2:
            excluded[c["id"]] = "binary column with a single row in one state — degenerate axis"
            continue
        cols.append(c["id"])
    self_id = table["self"]
    pairs, group_acc = [], {}
    for i, x in enumerate(cols):
        for y in cols[i + 1:]:
            pts, _ = _points(norm, table, x, y, size_col)
            if len(pts) < 2:
                continue
            xy = {p["id"]: (p["x"], p["y"]) for p in pts}
            ids = sorted(xy)
            dists = [_dist(xy[a], xy[b]) for ai, a in enumerate(ids) for b in ids[ai + 1:]]
            spread = statistics.fmean(dists)
            quads = {_quadrant_name(*xy[k]) for k in ids}
            empty = 4 - len(quads)
            iso = None
            if self_id in xy:
                iso = min((_dist(xy[self_id], xy[k]) for k in ids if k != self_id), default=None)
            cohesion = {}
            groups = {}
            for p in pts:
                if p["group"]:
                    groups.setdefault(p["group"], []).append(p["id"])
            for g, members in groups.items():
                if len(members) < 2:
                    continue
                gd = [_dist(xy[a], xy[b]) for ai, a in enumerate(members) for b in members[ai + 1:]]
                ratio = (statistics.fmean(gd) / spread) if spread > 0 else 0.0
                cohesion[g] = round(ratio, 4)
                group_acc.setdefault(g, []).append(ratio)
            pairs.append({"x": x, "y": y, "spread": round(spread, 4), "empty_quadrants": empty,
                          "self_isolation": None if iso is None else round(iso, 4),
                          "rows": len(pts), "group_cohesion": cohesion})
    pairs.sort(key=lambda p: (-(p["self_isolation"] if p["self_isolation"] is not None else -1),
                              -p["empty_quadrants"], -p["spread"], p["x"], p["y"]))
    groups_report = {g: {"mean_cohesion": round(statistics.fmean(v), 4),
                         "pairs": len(v),
                         "scatters": statistics.fmean(v) > 1.0}
                     for g, v in sorted(group_acc.items())}
    return {"project": table["project"], "self": self_id, "columns": cols,
            "excluded_columns": excluded,
            "pairs_evaluated": len(pairs), "top": pairs[:top],
            "groups": groups_report}, errors


def trajectory(table, x, y, size_id=None, ahead=2):
    norm, errors = normalize(table)
    xc, yc = _col(table, x, "x"), _col(table, y, "y")
    size_col = _col(table, size_id, "size") if size_id else None
    y0 = table["year"]
    if y0 is None:
        errors.append("trajectory needs 'year' (or a valid 'updated' date) for Y0")
        return {"project": table["project"], "rows": []}, errors
    now, _ = _points(norm, table, x, y, size_col)
    now_by = {p["id"]: p for p in now}
    rows = []
    for r in table["rows"]:
        if r["id"] not in now_by:
            continue
        states = []
        for yr in sorted(r["history"]):
            pts, _ = _points(norm, table, x, y, size_col, year=yr)
            for p in pts:
                if p["id"] == r["id"]:
                    states.append({"year": yr, "x": p["x"], "y": p["y"], "size": p["size"]})
        cur = now_by[r["id"]]
        states.append({"year": y0, "x": cur["x"], "y": cur["y"], "size": cur["size"]})
        entry = {"id": r["id"], "name": r["name"], "group": r["group"], "class": r["class"],
                 "states": states, "vector": None, "projected": []}
        if len(states) >= 2:
            first, last = states[0], states[-1]
            span = last["year"] - first["year"]
            dx, dy = (last["x"] - first["x"]) / span, (last["y"] - first["y"]) / span
            length = math.hypot(last["x"] - first["x"], last["y"] - first["y"])
            entry["vector"] = {"dx_per_year": round(dx, 4), "dy_per_year": round(dy, 4),
                               "length": round(length, 4), "years": span,
                               "size_change": (None if first["size"] is None or last["size"] is None
                                               else round(last["size"] - first["size"], 4))}
            for k in range(1, ahead + 1):
                px = max(-5.0, min(5.0, last["x"] + dx * k))
                py = max(-5.0, min(5.0, last["y"] + dy * k))
                entry["projected"].append({"year": y0 + k, "x": round(px, 4), "y": round(py, 4),
                                           "quadrant": _quadrant_name(px, py)})
        rows.append(entry)
    occ_now = {q: [] for q in ("I", "II", "III", "IV")}
    occ_end = {q: [] for q in ("I", "II", "III", "IV")}
    for e in rows:
        occ_now[_quadrant_name(e["states"][-1]["x"], e["states"][-1]["y"])].append(e["id"])
        end = e["projected"][-1] if e["projected"] else e["states"][-1]
        occ_end[_quadrant_name(end["x"], end["y"])].append(e["id"])
    clearing = [q for q in occ_now if len(occ_end[q]) < len(occ_now[q])]
    return {"project": table["project"], "year": y0, "ahead": ahead,
            "axes": {"x": {"id": x, "label": xc["label"]}, "y": {"id": y, "label": yc["label"]},
                     "size": size_id},
            "rows": rows, "occupancy_now": occ_now, f"occupancy_y+{ahead}": occ_end,
            "clearing_quadrants": clearing,
            "note": "a trajectory is a hypothesis, not knowledge — only monitoring confirms "
                    "it; a short vector on a small company predicts little (method §9)"}, errors


# --- svg -----------------------------------------------------------------------------

def _px(v):
    """−5..+5 → pixel coordinate on the square canvas."""
    return SVG_PAD + (v + 5.0) / 10.0 * (SVG_SIZE - 2 * SVG_PAD)


def _radius(size, sizes):
    valid = [s for s in sizes if s is not None and s > 0]
    if size is None or size <= 0 or not valid:
        return R_MIN
    lo, hi = math.sqrt(min(valid)), math.sqrt(max(valid))
    if hi == lo:
        return (R_MIN + R_MAX) / 2
    return R_MIN + (math.sqrt(size) - lo) / (hi - lo) * (R_MAX - R_MIN)


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _svg_frame(title, xl, yl):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_SIZE}" height="{SVG_SIZE}" '
           f'viewBox="0 0 {SVG_SIZE} {SVG_SIZE}" font-family="sans-serif" font-size="11">',
           f'<rect width="{SVG_SIZE}" height="{SVG_SIZE}" fill="white"/>',
           f'<text x="{SVG_SIZE/2:.1f}" y="18" text-anchor="middle" font-size="13">{_esc(title)}</text>']
    for i in range(-5, 6):
        p = _px(i)
        out.append(f'<line x1="{p:.1f}" y1="{SVG_PAD}" x2="{p:.1f}" y2="{SVG_SIZE-SVG_PAD}" '
                   f'stroke="#eee"/>')
        out.append(f'<line x1="{SVG_PAD}" y1="{p:.1f}" x2="{SVG_SIZE-SVG_PAD}" y2="{p:.1f}" '
                   f'stroke="#eee"/>')
    mid = _px(0)
    out.append(f'<line x1="{SVG_PAD}" y1="{mid:.1f}" x2="{SVG_SIZE-SVG_PAD}" y2="{mid:.1f}" '
               f'stroke="#333" stroke-width="1.5"/>')
    out.append(f'<line x1="{mid:.1f}" y1="{SVG_PAD}" x2="{mid:.1f}" y2="{SVG_SIZE-SVG_PAD}" '
               f'stroke="#333" stroke-width="1.5"/>')
    out.append(f'<text x="{SVG_SIZE-SVG_PAD}" y="{mid+14:.1f}" text-anchor="end">{_esc(xl)} →</text>')
    out.append(f'<text x="{mid+6:.1f}" y="{SVG_PAD+10}">{_esc(yl)} ↑</text>')
    return out


def _bubble(p, r, is_self):
    cx, cy = _px(p["x"]), _px(-p["y"])
    fill = "#3b6" if is_self else "none"
    # Labels flip to the left near the right edge so long names are not clipped.
    if cx > SVG_SIZE * 0.8:
        label = f'<text x="{cx - r - 3:.1f}" y="{cy + 4:.1f}" text-anchor="end">{_esc(p["name"])}</text>'
    else:
        label = f'<text x="{cx + r + 3:.1f}" y="{cy + 4:.1f}">{_esc(p["name"])}</text>'
    return [f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" fill-opacity="0.5" '
            f'stroke="#222" stroke-width="1.2"/>',
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.5" fill="#222"/>',
            label]


def svg_quadrant(doc):
    sizes = [p["size"] for p in doc["points"]]
    ax = doc["axes"]
    out = _svg_frame(f"{doc['project']}: {ax['x']['label']} × {ax['y']['label']}"
                     + (f" · size = {ax['size']}" if ax["size"] else ""),
                     ax["x"]["label"], ax["y"]["label"])
    self_id = (doc.get("self") or {}).get("id")
    for p in sorted(doc["points"], key=lambda p: p["id"]):
        out += _bubble(p, _radius(p["size"], sizes), p["id"] == self_id)
    out.append("</svg>")
    return "\n".join(out) + "\n"


def svg_trajectory(doc):
    sizes = [s["size"] for e in doc["rows"] for s in e["states"]]
    ax = doc["axes"]
    out = _svg_frame(f"{doc['project']}: trajectories on {ax['x']['label']} × {ax['y']['label']}",
                     ax["x"]["label"], ax["y"]["label"])
    for e in sorted(doc["rows"], key=lambda e: e["id"]):
        pts = [(_px(s["x"]), _px(-s["y"])) for s in e["states"]]
        if len(pts) >= 2:
            d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            out.append(f'<polyline points="{d}" fill="none" stroke="#222" stroke-width="1"/>')
        if e["projected"]:
            last = pts[-1]
            proj = [(_px(s["x"]), _px(-s["y"])) for s in e["projected"]]
            d = " ".join(f"{x:.1f},{y:.1f}" for x, y in [last] + proj)
            out.append(f'<polyline points="{d}" fill="none" stroke="#222" stroke-width="1" '
                       f'stroke-dasharray="4 3"/>')
            ex, ey = proj[-1]
            out.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="3" fill="#222"/>')
            out.append(f'<text x="{ex + 5:.1f}" y="{ey - 4:.1f}" fill="#555">'
                       f'{_esc(e["projected"][-1]["year"])}</text>')
        for i, s in enumerate(e["states"]):
            r = _radius(s["size"], sizes) if i == len(e["states"]) - 1 else R_MIN
            label = e["name"] if i == len(e["states"]) - 1 else str(s["year"])
            out += _bubble({"x": s["x"], "y": s["y"], "name": label}, r, False)
    out.append("</svg>")
    return "\n".join(out) + "\n"


# --- cli -----------------------------------------------------------------------------

def _emit(doc, errors, svg=None, render=None):
    doc = dict(doc)
    doc["errors"] = errors
    doc["ok"] = not errors
    if svg and not errors and render is not None:
        Path(svg).write_text(render(doc), encoding="utf-8")
        doc["svg"] = str(svg)
    print(json.dumps(doc, indent=2, sort_keys=False))
    return 0 if not errors else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "normalize", "quadrant", "sweep", "trajectory"):
        p = sub.add_parser(name)
        p.add_argument("file")
        if name in ("quadrant", "trajectory"):
            p.add_argument("--x", required=True)
            p.add_argument("--y", required=True)
            p.add_argument("--svg")
        if name in ("quadrant", "sweep", "trajectory"):
            p.add_argument("--size")
        if name == "sweep":
            p.add_argument("--top", type=int, default=10)
        if name == "trajectory":
            p.add_argument("--ahead", type=int, default=2)
    a = ap.parse_args(argv)

    table, errors = load(a.file)
    if table is None:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    if a.cmd == "validate":
        groups = {r["group"] for r in table["rows"] if r["group"]}
        standalone = [r["id"] for r in table["rows"] if not r["group"]]
        return _emit({"project": table["project"], "updated": table["updated"],
                      "year": table["year"], "self": table["self"],
                      "competitors_raw": len(table["rows"]),
                      "rows": len(groups) + len(standalone),
                      "groups": sorted(groups), "standalone": standalone,
                      "classes": {c: sum(1 for r in table["rows"] if r["class"] == c)
                                  for c in sorted(CLASSES)},
                      "found_by": {p: sum(1 for r in table["rows"] if r["found_by"] == p)
                                   for p in sorted(PASSES)},
                      "columns": [c["id"] for c in table["columns"]],
                      "history_years": sorted({y for r in table["rows"] for y in r["history"]})},
                     errors)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    if a.cmd == "normalize":
        return _emit(*normalize(table))
    if a.cmd == "quadrant":
        doc, errs = quadrant(table, a.x, a.y, a.size)
        return _emit(doc, errs, a.svg, svg_quadrant)
    if a.cmd == "sweep":
        return _emit(*sweep(table, a.size, a.top))
    if a.cmd == "trajectory":
        doc, errs = trajectory(table, a.x, a.y, a.size, a.ahead)
        return _emit(doc, errs, a.svg, svg_trajectory)
    return 2


if __name__ == "__main__":
    sys.exit(main())
