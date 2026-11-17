#!/usr/bin/env python3
"""grade.py — grade stack-pilot runs and, on request, write the verdict.

    grade.py --results DIR [--arms skill,bare] [--expect-runs author=5,audit=3] [--json]
    grade.py --results DIR --verdict

Each run folder DIR/<arm>-<prompt>-<n>/ (written by run.py) holds tree/, the
transcript and meta.json. A run is graded by running
rust-dev/scripts/validate-safety.sh on tree/ and counting the findings for the
six house-rule ids. A run that cannot be measured is UNGRADEABLE and carries no
finding count at all — never "0 findings". A folder named <...>.envfail is a
kept environment-failure first attempt: evidence, not a run.

Table mode prints the per-arm table and exits 1 when an expected run is missing
or ungradeable (a skill/bare run that saw the rule file, or a rule run that did
not, is ungradeable). Verdict mode reads all three arms and writes
DIR/verdict.json by the rule fixed in the pilot plan; it exits 0 once the file
is written, whatever the verdict.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
VALIDATE_SAFETY = os.path.join(REPO, "rust-dev", "scripts", "validate-safety.sh")

HOUSE_IDS = (
    "rust-unsafe-missing-safety-comment",
    "rust-sync-lock-in-async-candidate",
    "rust-unbounded-channel",
    "rust-box-dyn-error-in-pub-api",
    "rust-unwrap-outside-tests",
    "rust-serde-missing-deny-unknown",
)
ARMS = ("skill", "bare", "rule")
PROMPTS = ("author", "audit")
VERDICT_EXPECT = {"author": 5, "audit": 3}
RUN_DIR = re.compile(r"^(skill|bare|rule)-(author|audit)-(\d+)$")
SKIP_DIRS = {"target", ".git", "__pycache__"}

# The files whose change would invalidate a comparison already under way.
INPUTS = ("prompts/author.txt", "prompts/audit.txt", "fixture-author", "fixture-audit", "grade.py")


def _walk_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if not name.endswith(".pyc"):
                yield os.path.join(dirpath, name)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def inputs_sha256(base=HERE):
    """One hash over the prompts, both fixtures and this grader."""
    h = hashlib.sha256()
    for item in INPUTS:
        path = os.path.join(base, item)
        files = list(_walk_files(path)) if os.path.isdir(path) else [path]
        if not files or not all(os.path.isfile(f) for f in files):
            raise FileNotFoundError(f"stack-pilot input missing: {path}")
        for f in files:
            rel = os.path.relpath(f, base).replace(os.sep, "/")
            h.update(rel.encode() + b"\0" + _sha256(f).encode() + b"\n")
    return h.hexdigest()


def rust_sources(root):
    """{relative path: sha256} for every .rs file under root."""
    return {os.path.relpath(f, root): _sha256(f) for f in _walk_files(root) if f.endswith(".rs")}


class ScanError(Exception):
    pass


def scan_tree(tree):
    """Counts per house-rule id from validate-safety.sh --json. Raises ScanError
    when the validator cannot produce a reading."""
    try:
        p = subprocess.run(["bash", VALIDATE_SAFETY, tree, "--json"], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ScanError(f"validate-safety.sh did not run: {e}")
    if p.returncode != 0:
        raise ScanError(f"validate-safety.sh exited {p.returncode}: {(p.stderr or p.stdout).strip()[:300]}")
    try:
        report = json.loads(p.stdout)
        findings = report["findings"]
    except (ValueError, KeyError, TypeError) as e:
        raise ScanError(f"validate-safety.sh output is not its --json contract: {e}")
    counts = dict.fromkeys(HOUSE_IDS, 0)
    for f in findings:
        if f.get("rule") in counts:
            counts[f["rule"]] += 1
    return counts


def _ungradeable(base, reason):
    base.update(status="ungradeable", reason=reason, findings=None, total=None)
    return base


def grade_run(folder, current_hash=None):
    """Grade one run folder. Returns a dict with status gradeable|ungradeable."""
    name = os.path.basename(folder.rstrip("/"))
    m = RUN_DIR.match(name)
    g = {"name": name, "arm": m.group(1) if m else None, "prompt": m.group(2) if m else None,
         "n": int(m.group(3)) if m else None, "skill_invoked": False, "lane_run": False, "rule_loaded": False}
    try:
        with open(os.path.join(folder, "meta.json")) as fh:
            meta = json.load(fh)
    except (OSError, ValueError) as e:
        return _ungradeable(g, f"no readable meta.json ({e.__class__.__name__})")
    g["arm"] = g["arm"] or meta.get("arm")
    g["prompt"] = g["prompt"] or meta.get("prompt")
    for key in ("skill_invoked", "lane_run", "rule_loaded"):
        g[key] = meta.get(key) is True
    g["rule_present"] = meta.get("rule_present")

    if meta.get("environment") == "failure":
        return _ungradeable(g, "environment failure (rate limit or network)")
    if meta.get("exit") != 0:
        return _ungradeable(g, f"claude exit {meta.get('exit')!r}")
    if meta.get("is_error") is True:
        return _ungradeable(g, "claude reported an error result")
    want_rule = g["arm"] == "rule"
    if meta.get("rule_present") is not want_rule:
        return _ungradeable(g, f"rule_present is {meta.get('rule_present')!r}; the {g['arm']} arm needs {want_rule}")
    current_hash = current_hash or inputs_sha256()
    if meta.get("inputs_sha256") != current_hash:
        return _ungradeable(g, "inputs_sha256 differs: prompts, fixtures or grader changed since this run")
    tree = os.path.join(folder, "tree")
    if not os.path.isdir(tree):
        return _ungradeable(g, "no result tree")
    srcs = rust_sources(tree)
    if not srcs:
        return _ungradeable(g, "result tree holds no .rs files")
    if g["prompt"] == "author" and srcs == rust_sources(os.path.join(HERE, "fixture-author")):
        return _ungradeable(g, "author run changed no Rust source in the tree")
    try:
        counts = scan_tree(tree)
    except ScanError as e:
        return _ungradeable(g, str(e))
    g.update(status="gradeable", reason="", findings=counts, total=sum(counts.values()))
    return g


def list_runs(results):
    """Run folders under results, envfail attempts and stray names excluded."""
    try:
        names = os.listdir(results)
    except OSError:
        return []
    return sorted(n for n in names if RUN_DIR.match(n) and os.path.isdir(os.path.join(results, n)))


def build_table(results, arms, expect):
    """Grade every run of the arms. Returns (table, graded, problems)."""
    current = inputs_sha256()
    graded = {}
    for name in list_runs(results):
        arm, prompt, _ = RUN_DIR.match(name).groups()
        if arm in arms and prompt in expect:
            graded[name] = grade_run(os.path.join(results, name), current)
    table, problems = {}, []
    for arm in arms:
        table[arm] = {}
        for prompt, want in expect.items():
            runs = [g for g in graded.values() if g["arm"] == arm and g["prompt"] == prompt]
            ok = [g for g in runs if g["status"] == "gradeable"]
            per_id = dict.fromkeys(HOUSE_IDS, 0)
            for g in ok:
                for rid, c in g["findings"].items():
                    per_id[rid] += c
            table[arm][prompt] = {
                "expected": want, "runs": len(runs), "gradeable": len(ok),
                "findings": sum(per_id.values()), "findings_by_rule": per_id,
                "lane_runs": sum(1 for g in ok if g["lane_run"]),
                "skill_invoked": sum(1 for g in runs if g["skill_invoked"]),
                "rule_loaded": sum(1 for g in runs if g["rule_loaded"]),
            }
            present = {g["n"] for g in runs}
            for n in range(1, want + 1):
                if n not in present:
                    problems.append(f"MISSING {arm}-{prompt}-{n}")
            for g in runs:
                if g["n"] > want:
                    problems.append(f"UNEXPECTED {g['name']} (expected {want} run(s))")
                if g["status"] != "gradeable":
                    problems.append(f"UNGRADEABLE {g['name']}: {g['reason']}")
    return table, graded, problems


def decide(table, expect=None):
    """The verdict rule fixed in the pilot plan, as a pure function of the table."""
    expect = expect or VERDICT_EXPECT

    def cell(arm, prompt):
        return (table.get(arm) or {}).get(prompt) or {}

    c1_values, c1 = {}, True
    for arm in ARMS:
        for prompt, want in expect.items():
            c = cell(arm, prompt)
            runs, ok = c.get("runs", 0), c.get("gradeable", 0)
            c1_values[f"{arm}/{prompt}"] = f"{ok} gradeable of {runs} run(s), {want} expected"
            c1 = c1 and runs == want and ok == want

    c2_values, c2 = {}, True
    for prompt, want in expect.items():
        loaded = cell("rule", prompt).get("rule_loaded", 0)
        c2_values[prompt] = f"{loaded} of {want}"
        c2 = c2 and loaded == want

    rf, sf = cell("rule", "author").get("findings"), cell("skill", "author").get("findings")
    c3 = isinstance(rf, int) and isinstance(sf, int) and rf <= sf + 1
    rl, sl = cell("rule", "audit").get("lane_runs"), cell("skill", "audit").get("lane_runs")
    c4 = isinstance(rl, int) and isinstance(sl, int) and rl >= sl - 1

    conditions = [
        {"id": 1, "rule": "every run of every arm produced a gradeable result", "values": c1_values, "pass": c1},
        {"id": 2, "rule": "every rule run logged the rule as loaded", "values": c2_values, "pass": c2},
        {"id": 3, "rule": "author: rule findings summed <= skill sum + 1",
         "values": {"rule": rf, "skill": sf, "limit": sf + 1 if isinstance(sf, int) else None}, "pass": c3},
        {"id": 4, "rule": "audit: rule runs that ran the validation lane >= skill count - 1",
         "values": {"rule": rl, "skill": sl, "floor": sl - 1 if isinstance(sl, int) else None}, "pass": c4},
    ]
    return {"verdict": "go" if all(c["pass"] for c in conditions) else "no-go", "conditions": conditions}


def render(table, graded):
    lines = [f"{'arm':6} {'prompt':7} {'runs':>9} {'gradeable':>9} {'findings':>8} {'lane_run':>8} "
             f"{'skill_invoked':>13} {'rule_loaded':>11}"]
    for arm, prompts in table.items():
        for prompt, c in prompts.items():
            lines.append(f"{arm:6} {prompt:7} {c['runs']:>4}/{c['expected']:<4} {c['gradeable']:>9} {c['findings']:>8} "
                         f"{c['lane_runs']:>8} {c['skill_invoked']:>13} {c['rule_loaded']:>11}")
    lines.append("")
    for name, g in sorted(graded.items()):
        if g["status"] == "gradeable":
            hit = ", ".join(f"{k}={v}" for k, v in g["findings"].items() if v)
            lines.append(f"  {name}: {g['total']} finding(s){' (' + hit + ')' if hit else ''}")
        else:
            lines.append(f"  {name}: UNGRADEABLE — {g['reason']}")
    return "\n".join(lines)


def parse_expect(text):
    out = {}
    for part in text.split(","):
        prompt, _, n = part.partition("=")
        if prompt.strip() not in PROMPTS or not n.strip().isdigit() or int(n) < 1:
            raise argparse.ArgumentTypeError(f"bad --expect-runs entry {part!r}; want e.g. author=5,audit=3")
        out[prompt.strip()] = int(n)
    return out


def parse_arms(text):
    arms = [a.strip() for a in text.split(",") if a.strip()]
    bad = [a for a in arms if a not in ARMS]
    if bad or not arms:
        raise argparse.ArgumentTypeError(f"bad --arms {text!r}; choose from {','.join(ARMS)}")
    return arms


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--results", required=True, help="the folder holding <arm>-<prompt>-<n>/ run folders")
    ap.add_argument("--arms", type=parse_arms, default=list(ARMS))
    ap.add_argument("--expect-runs", type=parse_expect, default=dict(VERDICT_EXPECT))
    ap.add_argument("--verdict", action="store_true", help="grade all three arms and write verdict.json")
    ap.add_argument("--json", action="store_true", help="print the table as JSON")
    a = ap.parse_args(argv)

    if not os.path.isdir(a.results):
        print(f"grade.py: no results folder {a.results}", file=sys.stderr)
        return 2
    if a.verdict:
        arms, expect = list(ARMS), dict(VERDICT_EXPECT)
    else:
        arms, expect = a.arms, a.expect_runs
    table, graded, problems = build_table(a.results, arms, expect)
    print(json.dumps(table, indent=2) if a.json else render(table, graded))

    if a.verdict:
        v = decide(table, expect)
        out = {"verdict": v["verdict"], "table": table, "conditions": v["conditions"],
               "problems": problems, "inputs_sha256": inputs_sha256(),
               "runs": {n: {k: g[k] for k in ("status", "reason", "total", "lane_run", "skill_invoked", "rule_loaded")}
                        for n, g in sorted(graded.items())}}
        path = os.path.join(a.results, "verdict.json")
        with open(path, "w") as fh:
            json.dump(out, fh, indent=2)
            fh.write("\n")
        print("")
        for c in v["conditions"]:
            print(f"  [{'pass' if c['pass'] else 'FAIL'}] {c['id']}. {c['rule']}: {json.dumps(c['values'])}")
        print(f"verdict: {v['verdict']} (written to {path})")
        return 0

    if problems:
        print("\nFAIL:", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print("\nall expected runs present and gradeable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
