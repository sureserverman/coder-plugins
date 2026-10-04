#!/usr/bin/env python3
"""Fixture suite for scripts/context-usage.py — run directly (CI convention):
    python3 planning/skills/executing-plans/tests/test-context-usage.py

Asserts the script's contract: it finds the transcript from CLAUDE_CODE_SESSION_ID
and from --transcript; `now` is input + cache_read + cache_creation on the last
real assistant row (sidechain, <synthetic> and usage-less rows skipped, malformed
lines tolerated); the window comes from the model table for every listed model
id, --window overrides it, and the 1M upgrade needs evidence; anything the script
cannot prove yields `verdict: unknown` with exit 0; bad CLI usage exits 2.

Every subprocess runs with a temp HOME, a temp cwd, and CLAUDE_CODE_SESSION_ID /
ANTHROPIC_MODEL stripped, so the suite never reads the real ~/.claude.

Stdlib only.
"""
import datetime
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "context-usage.py")
FIXTURE = os.path.join(HERE, "fixtures", "context-usage", "synthetic.jsonl")
# A real transcript slice (e8befa8a, rows 2400-3200) scrubbed to usage blocks, the two
# `Stage 1 green` commit commands and the one compaction row. Deltas hand-computed:
# 925299 - 862941 = 62358 (baseline: first turn of the slice), then the compaction,
# then 147636 - 75460 = 72176 (baseline: first turn after the compaction).
STAGED = os.path.join(HERE, "fixtures", "context-usage", "staged.jsonl")
# Stage 1 and 2 share tests/test-entries.py; Stage 3 is disjoint; Stage 4 has no Scope.
PLAN = os.path.join(HERE, "fixtures", "context-usage", "plan.md")

# The fixture's last real assistant row: input 5 + cache_read 90000 + cache_creation 3000.
FIXTURE_NOW = 93005

FAILURES = []


def check(cond, msg):
    if cond:
        print(f"  ok: {msg}")
    else:
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


def env_for(home, **extra):
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDE_CODE_SESSION_ID", "ANTHROPIC_MODEL")}
    env["HOME"] = str(home)
    env.update(extra)
    return env


def run(args, home, cwd=None, **extra_env):
    """Run the script; return (rc, stdout, stderr)."""
    r = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True,
                       env=env_for(home, **extra_env), cwd=str(cwd or home))
    return r.returncode, r.stdout, r.stderr


def run_json(args, home, cwd=None, **extra_env):
    rc, out, err = run(["--format", "json", *args], home, cwd, **extra_env)
    try:
        return rc, json.loads(out), err
    except ValueError:
        return rc, None, f"stdout not JSON: {out!r} stderr: {err!r}"


def rows_transcript(d, name, rows):
    """Write raw rows (dicts) as a transcript; return its path."""
    p = pathlib.Path(d) / name
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return p


def turn(ctx, command=None, model="claude-fable-5-1"):
    """An assistant row whose context is `ctx`, optionally carrying a Bash command."""
    content = []
    if command:
        content.append({"type": "tool_use", "name": "Bash", "input": {"command": command}})
    return {"type": "assistant", "message": {
        "model": model, "content": content,
        "usage": {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
                  "cache_creation_input_tokens": 0}}}


COMPACT = {"type": "user", "isCompactSummary": True,
           "message": {"role": "user", "content": "summary"}}


def transcript_for(d, model, rows=((2, 1000, 500), (4, 20000, 1000))):
    """Write a small transcript whose assistant rows use `model`; return its path."""
    p = pathlib.Path(d) / f"{model}.jsonl"
    lines = [json.dumps({"type": "user", "message": {"role": "user", "content": "x"}})]
    for inp, read, create in rows:
        lines.append(json.dumps({"type": "assistant", "message": {
            "model": model, "usage": {"input_tokens": inp,
                                      "cache_read_input_tokens": read,
                                      "cache_creation_input_tokens": create}}}))
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


mod = None
if os.path.exists(SCRIPT):
    spec = importlib.util.spec_from_file_location("context_usage", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
check(mod is not None, f"script exists and imports ({SCRIPT})")
TABLE = getattr(mod, "MODEL_WINDOWS", {}) if mod else {}

KEYS = {"now", "window", "window_source", "pct", "stage_costs", "last_stage_cost",
        "projected_pct", "model", "transcript", "verdict", "reason", "compactions", "disjoint"}

tmp = tempfile.mkdtemp(prefix="ctxuse-")
try:
    home = pathlib.Path(tmp) / "home"
    home.mkdir()
    work = pathlib.Path(tmp) / "work"
    work.mkdir()

    print("group 1 — locating the transcript")
    sid = "11111111-2222-3333-4444-555555555555"
    proj = home / ".claude" / "projects" / "-some-cwd-slug"
    proj.mkdir(parents=True)
    located = proj / f"{sid}.jsonl"
    shutil.copy(FIXTURE, located)
    rc, j, err = run_json([], home, work, CLAUDE_CODE_SESSION_ID=sid)
    check(rc == 0 and j is not None, f"session-id run exits 0 with JSON ({err.strip()[:200]})")
    j = j or {}
    check(j.get("transcript") == str(located),
          f"transcript located from CLAUDE_CODE_SESSION_ID under $HOME ({j.get('transcript')})")
    check(j.get("now") == FIXTURE_NOW, f"session-id run: now == {FIXTURE_NOW} ({j.get('now')})")

    rc, j, err = run_json(["--transcript", FIXTURE], home, work)
    j = j or {}
    check(rc == 0 and j.get("transcript") == FIXTURE,
          f"--transcript is used with no session id in env ({j.get('transcript')})")
    other = proj / "other-session.jsonl"
    other.write_text("", encoding="utf-8")
    rc, j, err = run_json(["--transcript", FIXTURE], home, work,
                          CLAUDE_CODE_SESSION_ID="other-session")
    j = j or {}
    check(j.get("transcript") == FIXTURE and j.get("now") == FIXTURE_NOW,
          "--transcript overrides CLAUDE_CODE_SESSION_ID")

    print("group 2 — `now` is the exact last-row sum")
    rc, j, err = run_json(["--transcript", FIXTURE], home, work)
    j = j or {}
    check(j.get("now") == FIXTURE_NOW,
          f"now == input+cache_read+cache_creation of last real row ({j.get('now')})")
    check(j.get("now") is not None and j.get("now") != 900001, "isSidechain row is ignored")
    check(j.get("now") is not None and j.get("now") != 0,
          "<synthetic> zero-usage row is ignored")
    check(j.get("model") == "claude-opus-5-5", f"model reported from last row ({j.get('model')})")
    check(set(j) == KEYS, f"JSON has exactly the contract keys ({sorted(set(j) ^ KEYS)})")
    check(j.get("stage_costs") == [] and j.get("last_stage_cost") is None
          and j.get("projected_pct") is None,
          "stage_costs [] / last_stage_cost null / projected_pct null for now")

    print("group 3 — unlisted model yields unknown, exit 0")
    check("claude-unlisted-test" not in TABLE, "claude-unlisted-test is not in MODEL_WINDOWS")
    rc, j, _err = run_json(["--transcript", str(transcript_for(tmp, "claude-unlisted-test"))],
                           home, work)
    j = j or {}
    check(rc == 0 and j.get("verdict") == "unknown",
          f"unlisted model -> verdict unknown, exit 0 (rc={rc}, {j.get('verdict')})")
    check("claude-unlisted-test" in (j.get("reason") or ""), "unknown reason names the model")
    check(j.get("window") is None and j.get("pct") is None,
          "unlisted model -> window and pct are null")

    print("group 4 — window from the table for every listed model id")
    check(len(TABLE) >= 3, f"MODEL_WINDOWS lists models ({len(TABLE)})")
    for model, (base, _supports_1m) in sorted(TABLE.items()):
        t = transcript_for(tmp, model)
        rc, j, err = run_json(["--transcript", str(t)], home, work)
        j = j or {}
        check(rc == 0 and j.get("window") == base and j.get("window_source") == "table",
              f"{model}: window {j.get('window')} == table {base} (source {j.get('window_source')})")
        exp_pct = round(21004 / base * 100, 1)
        check(j.get("pct") == exp_pct and j.get("verdict") == "continue",
              f"{model}: pct {j.get('pct')} == {exp_pct}, verdict continue")
    if "claude-haiku-4-5" in TABLE:
        t = transcript_for(tmp, "claude-haiku-4-5-20251001")
        rc, j, err = run_json(["--transcript", str(t)], home, work)
        j = j or {}
        check(j.get("window") == TABLE["claude-haiku-4-5"][0],
              f"dated suffix claude-haiku-4-5-20251001 resolves ({j.get('window')})")

    print("group 5 — --window overrides; pct and the handoff threshold")
    rc, j, err = run_json(["--transcript", FIXTURE, "--window", "200000"], home, work)
    j = j or {}
    check(j.get("window") == 200000 and j.get("window_source") == "--window",
          f"--window wins over an unlisted model ({j.get('window')}, {j.get('window_source')})")
    check(j.get("pct") == 46.5 and j.get("verdict") == "continue",
          f"pct 93005/200000 -> 46.5, continue ({j.get('pct')}, {j.get('verdict')})")
    rc, j, err = run_json(["--transcript", FIXTURE, "--window", "180000"], home, work)
    j = j or {}
    # No `Stage N green` commit in this fixture: the first stage of a session always runs
    # (Task 1.3), so 51.7% continues here; group 12 covers the handoff with history.
    check(j.get("pct") == 51.7 and j.get("verdict") == "continue",
          f"pct 51.7 with no stage history -> continue ({j.get('pct')}, {j.get('verdict')})")
    check("51.7" in (j.get("reason") or "") and "first stage" in (j.get("reason") or ""),
          f"reason names pct and the first-stage rule ({j.get('reason')})")
    rc, j, err = run_json(["--transcript", FIXTURE, "--window", "186010"], home, work)
    j = j or {}
    check(j.get("pct") == 50.0 and j.get("verdict") == "continue",
          f"pct exactly 50.0 -> continue ({j.get('pct')}, {j.get('verdict')})")
    if TABLE:
        listed = sorted(TABLE)[0]
        t = transcript_for(tmp, listed)
        rc, j, err = run_json(["--transcript", str(t), "--window", "30000"], home, work)
        j = j or {}
        check(j.get("window") == 30000 and j.get("window_source") == "--window"
              and j.get("verdict") in ("continue", "handoff"),
              f"--window overrides a listed model's table window ({j.get('window')})")

    print("group 6 — unknown for anything unproven, always exit 0")
    rc, j, err = run_json([], home, work)
    j = j or {}
    check(rc == 0 and j.get("verdict") == "unknown",
          f"no session id and no --transcript -> unknown, exit 0 (rc={rc})")
    rc, j, err = run_json([], home, work, CLAUDE_CODE_SESSION_ID="no-such-session")
    j = j or {}
    check(rc == 0 and j.get("verdict") == "unknown", "session id with no transcript file -> unknown")
    rc, j, err = run_json(["--transcript", str(pathlib.Path(tmp) / "missing.jsonl")], home, work)
    j = j or {}
    check(rc == 0 and j.get("verdict") == "unknown" and j.get("now") is None,
          f"missing --transcript -> unknown, exit 0 (rc={rc})")
    empty = pathlib.Path(tmp) / "no-usage.jsonl"
    empty.write_text('{"type":"user","message":{"content":"x"}}\nnot json\n', encoding="utf-8")
    rc, j, err = run_json(["--transcript", str(empty), "--window", "200000"], home, work)
    j = j or {}
    check(rc == 0 and j.get("verdict") == "unknown",
          f"no assistant usage rows -> unknown even with --window (rc={rc})")
    for key in ("reason",):
        check(bool(j.get(key)), "unknown verdict carries a reason")

    print("group 7 — one-line text output (the default)")
    rc, out, err = run(["--transcript", FIXTURE, "--window", "200000"], home, work)
    lines = out.strip().splitlines()
    check(rc == 0 and len(lines) == 1, f"text output is one line ({len(lines)})")
    line = lines[0] if lines else ""
    check(line.startswith("context-usage: verdict=continue now=93005 window=200000 pct=46.5 "
                          "projected_pct=null disjoint=null reason: "), f"text line shape ({line[:120]})")
    rc, out, err = run(["--transcript", str(pathlib.Path(tmp) / "missing.jsonl")], home, work)
    check(rc == 0 and out.startswith("context-usage: verdict=unknown ")
          and len(out.strip().splitlines()) == 1, "unknown also prints one text line, exit 0")

    print("group 8 — bad CLI usage exits 2")
    for bad in (["--format", "xml"], ["--window", "abc"], ["--window", "0"], ["--bogus"]):
        rc, out, err = run(bad, home, work)
        # "usage:" proves argparse rejected it — python3 also exits 2 on a missing script.
        check(rc == 2 and "usage:" in err, f"{' '.join(bad)} -> argparse exit 2 (rc={rc})")

    print("group 9 — 1M upgrade needs evidence (unit-level, injected table entry)")
    if mod is not None:
        mod.MODEL_WINDOWS["test-model-200k"] = (200_000, True)
        mod.MODEL_WINDOWS["test-model-no1m"] = (200_000, False)
        rw = mod.resolve_window
        w, src = rw("test-model-200k", None, 50_000, None)
        check(w == 200_000 and src == "table", f"no evidence -> base window ({w}, {src})")
        w, src = rw("test-model-200k", None, 50_000, ("ANTHROPIC_MODEL", "opus[1m]"))
        check(w == 1_000_000 and "[1m]" in src and "ANTHROPIC_MODEL" in src,
              f"[1m] configured -> 1M, source names it ({w}, {src})")
        w, src = rw("test-model-200k", None, 250_000, None)
        check(w == 1_000_000 and "observed" in src, f"observed > base -> 1M ({w}, {src})")
        w, src = rw("test-model-no1m", None, 50_000, ("ANTHROPIC_MODEL", "x[1m]"))
        check(w == 200_000 and src == "table", f"[1m] ignored when model lacks 1M ({w}, {src})")
        w, src = rw("test-model-200k", 123_456, 250_000, ("ANTHROPIC_MODEL", "opus[1m]"))
        check(w == 123_456 and src == "--window", f"--window beats every upgrade ({w}, {src})")
        w, src = rw("not-a-model", None, 1, None)
        check(w is None, f"unlisted model -> no window ({w})")

        cm = mod.configured_model
        h = pathlib.Path(tmp) / "cm-home"
        c = pathlib.Path(tmp) / "cm-cwd"
        (h / ".claude").mkdir(parents=True)
        (c / ".claude").mkdir(parents=True)
        (h / ".claude" / "settings.json").write_text('{"model": "home[1m]"}')
        check(cm({}, str(c), str(h)) == (str(h / ".claude" / "settings.json"), "home[1m]"),
              "falls back to $HOME/.claude/settings.json")
        (c / ".claude" / "settings.json").write_text('{"model": "proj"}')
        check(cm({}, str(c), str(h))[1] == "proj", "project settings.json beats home")
        (c / ".claude" / "settings.local.json").write_text('{"model": "local[1m]"}')
        check(cm({}, str(c), str(h))[1] == "local[1m]", "settings.local.json beats settings.json")
        check(cm({"ANTHROPIC_MODEL": "env"}, str(c), str(h)) == ("ANTHROPIC_MODEL", "env"),
              "ANTHROPIC_MODEL beats every settings file")
        (c / ".claude" / "settings.local.json").write_text('not json')
        check(cm({}, str(c), str(h))[1] == "proj", "malformed settings file is skipped")
        (c / ".claude" / "settings.local.json").unlink()
        os.mkfifo(c / ".claude" / "settings.local.json")
        try:
            r = subprocess.run([sys.executable, SCRIPT, "--transcript", FIXTURE],
                               capture_output=True, text=True, timeout=20, cwd=str(c),
                               env=env_for(h))
            check(r.returncode == 0 and "verdict=" in r.stdout,
                  f"a FIFO settings.local.json is skipped, no hang (rc={r.returncode})")
        except subprocess.TimeoutExpired:
            check(False, "a FIFO settings.local.json hangs the script")
        (c / ".claude" / "settings.local.json").unlink()

    print("group 10 — end-to-end [1m] evidence from $HOME settings")
    if "claude-haiku-4-5" in TABLE:
        (home / ".claude" / "settings.json").write_text('{"model": "haiku[1m]"}')
        t = transcript_for(tmp, "claude-haiku-4-5")
        rc, j, err = run_json(["--transcript", str(t)], home, work)
        j = j or {}
        check(j.get("window") == TABLE["claude-haiku-4-5"][0],
              f"haiku (no 1M in doc) keeps its base window despite [1m] ({j.get('window')})")
        (home / ".claude" / "settings.json").unlink()

    print("group 11 — per-stage cost from `Stage N green` commits, compaction-aware")
    rc, j, err = run_json(["--transcript", STAGED], home, work)
    j = j or {}
    costs = j.get("stage_costs") or []
    check(rc == 0 and [c.get("cost") for c in costs] == [62358, 72176],
          f"real fixture: stage_costs == hand-computed [62358, 72176] ({costs})")
    check([c.get("stage") for c in costs] == [1, 1], "each cost names its stage number")
    check(len(costs) == 2 and costs[1].get("from") == 75460
          and costs[1].get("after_compaction") is True,
          "the compaction resets the baseline to the first turn after it (75460)")
    check(len(costs) == 2 and costs[0].get("after_compaction") is False,
          "the first cost does not span a compaction")
    check(j.get("compactions") == 1, f"compactions counted ({j.get('compactions')})")
    check(j.get("last_stage_cost") == 72176, f"last_stage_cost ({j.get('last_stage_cost')})")
    check(j.get("pct") is not None and j.get("projected_pct")
          == round(j["pct"] + 72176 / 1_000_000 * 100, 1),
          f"projected_pct = pct + last_stage_cost/window ({j.get('projected_pct')})")

    t = rows_transcript(tmp, "nocommit.jsonl", [turn(1000), turn(5000),
                                               turn(9000, 'git log --grep "Stage 1 green"')])
    rc, j, err = run_json(["--transcript", str(t)], home, work)
    j = j or {}
    check(j.get("stage_costs") == [] and j.get("last_stage_cost") is None
          and j.get("projected_pct") is None,
          "a command that only mentions `Stage 1 green` without committing is not a stage")

    t = rows_transcript(tmp, "two.jsonl", [
        turn(1000), turn(4000, 'git commit -m "Stage 2 green"'), turn(4500),
        turn(10000, "git add -A && git commit -q -F - <<'EOF'\nStage 3 green\nEOF"),
        COMPACT, turn(3000), turn(3500)])
    rc, j, err = run_json(["--transcript", str(t)], home, work)
    j = j or {}
    costs = j.get("stage_costs") or []
    check([(c.get("stage"), c.get("cost")) for c in costs] == [(2, 3000), (3, 6000)],
          f"two commits, no compaction between them: deltas 3000 and 6000 ({costs})")
    check(j.get("last_stage_cost") == 6000 and j.get("compactions") == 1,
          "a compaction after the last commit keeps last_stage_cost and is counted")
    check(j.get("now") == 3500, "now is still the last row after a compaction")

    # Measured in the executing session itself: three false boundaries came from Bash
    # commands that WROTE this test file — the commit string sat inside Python source,
    # not in command position. And a gate-fix commit whose BODY mentions the phrase is
    # not a gate commit either. Only the subject of a real `git commit` counts.
    NL = "\n"
    shapes = [
        ("C1 = 'git commit -m " + '"Stage 1 green"' + "'", None),
        ("python3 - <<'PY'" + NL + "turn(4000, 'git commit -m " + '"Stage 2 green"' + "')"
         + NL + "PY", None),
        ("git commit -q -F - <<'EOF'" + NL + "Stage 1 gate fix: x" + NL + NL
         + "after Stage 1 green the suite ran" + NL + "EOF", None),
        ('git -C /repo commit --allow-empty -m "Stage 4 green"', 4),
        ("git commit -m \"$(cat <<'EOF'" + NL + "Stage 5 green" + NL + NL + "body" + NL
         + "EOF" + NL + ")\"", 5),
        ("git commit -q -m \"$(printf 'Stage 6 green\\n\\nbody')\"", 6),
        ('cd /x && git add -A && git commit -q -m "Stage 7 green — gate report"', 7),
        ("git add -A && git commit -q --allow-empty -F - <<'MSG'" + NL + "Stage 8 green" + NL
         + "MSG", 8),
        ("echo x > seed.txt; git add -A; git commit -qm " + '"Stage 11 green"', 11),
        # The subject ends at its closing quote; what follows on the line is not the message.
        ('git commit -m "Fix X" && echo "Stage 12 green"', None),
        ("git commit --allow-empty -q -m 'Stage 13 green'", 13),
        # A heredoc body that is not a commit message is data, whatever it contains.
        ("python3 - <<'PY'" + NL + "x = 1" + NL + "git commit -m " + '"Stage 9 green"' + NL
         + "PY", None),
        # `git` after && but inside an open quote on its line is a string, not a command.
        ("python3 -c \"print('a && git commit -m Stage 9 green')\"", None),
        # A quoted argument spanning lines without heredoc syntax is still one string
        # (Tier-2 finding, Stage 2 gate): the quote state carries across lines.
        ('echo "start' + NL + 'git commit -m \\"Stage 9 green\\"' + NL + 'end"', None),
        # An apostrophe inside a double-quoted subject does not open a single quote for
        # the rest of the command, and neither does one in a shell comment.
        ('git commit -m "Fix: don\'t skip"' + NL + 'git commit -m "Stage 15 green"', 15),
        ("# don't" + NL + 'git commit -m "Stage 16 green"', 16),
        # `commit` inside a filename is not the subcommand.
        ('git add .husky/commit-msg && git commit -m "Stage 17 green"', 17),
        ('git add .husky/commit-msg -m "Stage 18 green"', None),
        # ...and a real commit after such a heredoc still counts.
        ("python3 - <<'PY'" + NL + "print(1)" + NL + "PY" + NL
         + 'git commit -q -m "Stage 10 green"', 10),
    ]
    for cmd, want in shapes:
        t = rows_transcript(tmp, "shape.jsonl", [turn(1000), turn(2000, cmd)])
        rc, j, err = run_json(["--transcript", str(t)], home, work)
        got = [c.get("stage") for c in (j or {}).get("stage_costs") or []]
        check(got == ([] if want is None else [want]),
              f"boundary only on a commit whose subject is Stage N green: {cmd[:60]!r} -> {got}")

    print("group 12 — verdict rules: context threshold, first stage, projection")
    W = ["--window", "100000"]

    def verdict_for(name, rows, *extra):
        rc, j, err = run_json(["--transcript", str(rows_transcript(tmp, name, rows)), *W,
                               *extra], home, work)
        return rc, (j or {})

    C1 = 'git commit -m "Stage 1 green"'
    rc, j = verdict_for("v51.jsonl", [turn(10000), turn(30000, C1), turn(51000)])
    check(j.get("verdict") == "handoff" and "51.0" in (j.get("reason") or ""),
          f"handoff when pct > 50 ({j.get('verdict')}: {j.get('reason')})")
    rc, j = verdict_for("vproj.jsonl", [turn(10000), turn(30000, C1), turn(40000)])
    check(j.get("projected_pct") == 60.0 and j.get("verdict") == "handoff",
          f"handoff when pct + last_stage_cost_pct > 50 (40 + 20) ({j.get('reason')})")
    rc, j = verdict_for("v50.jsonl", [turn(50000, C1)])
    check(j.get("pct") == 50.0 and j.get("projected_pct") == 50.0
          and j.get("verdict") == "continue",
          f"continue at exactly 50 ({j.get('verdict')}: {j.get('reason')})")
    rc, j = verdict_for("vfirst.jsonl", [turn(10000), turn(70000)])
    check(j.get("last_stage_cost") is None and j.get("verdict") == "continue"
          and "first stage" in (j.get("reason") or ""),
          f"continue when last_stage_cost is null, even at 70% ({j.get('reason')})")

    print("group 13 — dead weight: --plan / --next-stage disjointness")
    low = [turn(10000), turn(12000, C1), turn(30000)]      # pct 30, stage cost 2%
    rc, j = verdict_for("dw3.jsonl", low, "--plan", PLAN, "--next-stage", "3")
    check(j.get("disjoint") is True and j.get("verdict") == "handoff",
          f"handoff when disjoint and pct > 25 ({j.get('disjoint')}, {j.get('reason')})")
    rc, j = verdict_for("dw2.jsonl", low, "--plan", PLAN, "--next-stage", "2")
    check(j.get("disjoint") is False and j.get("verdict") == "continue",
          f"continue when the next stage shares a path ({j.get('disjoint')}, {j.get('reason')})")
    rc, j = verdict_for("dwlow.jsonl", [turn(10000), turn(12000, C1), turn(20000)],
                        "--plan", PLAN, "--next-stage", "3")
    check(j.get("disjoint") is True and j.get("verdict") == "continue",
          f"continue when disjoint and pct <= 25 ({j.get('reason')})")
    rc, j = verdict_for("dw4.jsonl", low, "--plan", PLAN, "--next-stage", "4")
    check(j.get("disjoint") == "unknown" and j.get("verdict") == "continue",
          f"next stage without Scope -> disjoint unknown, no stop ({j.get('disjoint')})")
    rc, j = verdict_for("dwdone4.jsonl", [turn(10000), turn(12000, 'git commit -m "Stage 4 green"'),
                                          turn(30000)], "--plan", PLAN, "--next-stage", "3")
    check(j.get("disjoint") == "unknown" and j.get("verdict") == "continue",
          f"a done stage without Scope -> disjoint unknown, no stop ({j.get('disjoint')})")
    rc, j = verdict_for("dwdef.jsonl", low, "--plan", PLAN)
    check(j.get("disjoint") is False,
          f"--next-stage defaults to the last green stage + 1 ({j.get('disjoint')})")
    rc, j = verdict_for("dwnone.jsonl", low)
    check(j.get("disjoint") is None, "no --plan -> disjoint null")
    bad = pathlib.Path(tmp) / "badplan.md"
    bad.write_bytes(b"## Stage 1: Bad\n- **Scope:** foo\xff.py\n## Stage 2: Next\n"
                    b"- **Scope:** `docs/x.md`\n")
    rc, j = verdict_for("dwbad.jsonl", low, "--plan", str(bad), "--next-stage", "2")
    check(rc == 0 and j.get("verdict") in ("continue", "handoff", "unknown")
          and j.get("disjoint") is not None,
          f"a plan that is not valid UTF-8 yields a verdict, exit 0 — never a crash (rc={rc})")
    rc, j = verdict_for("dwmissing.jsonl", low, "--plan", str(pathlib.Path(tmp) / "nope.md"))
    check(rc == 0 and j.get("disjoint") == "unknown", "a missing plan -> disjoint unknown, exit 0")

    print("group 14 — sub-plan boundary and reasons")
    rc, j = verdict_for("sp30.jsonl", low, "--sub-plan-boundary")
    check(j.get("verdict") == "handoff" and "sub-plan boundary" in (j.get("reason") or ""),
          f"--sub-plan-boundary at 30% -> handoff ({j.get('reason')})")
    rc, j = verdict_for("sp20.jsonl", [turn(10000), turn(12000, C1), turn(20000)],
                        "--sub-plan-boundary")
    check(j.get("verdict") == "continue" and "sub-plan boundary" in (j.get("reason") or ""),
          f"--sub-plan-boundary under 25% -> continue ({j.get('reason')})")
    rc, j = verdict_for("sp25.jsonl", [turn(25000)], "--sub-plan-boundary")
    check(j.get("verdict") == "handoff", f"--sub-plan-boundary at exactly 25% -> handoff "
                                          f"(unless pct < 25) ({j.get('reason')})")
    for name, rows, extra in (("r1.jsonl", low, ()), ("r2.jsonl", low, ("--plan", PLAN)),
                              ("r3.jsonl", [turn(60000)], ())):
        rc, j = verdict_for(name, rows, *extra)
        r = j.get("reason") or ""
        check(str(j.get("pct")) in r and ("rule" in r or "unknown" in r),
              f"reason names the rule and the numbers ({r})")

    print("group 15 — live-window sidecar <cwd>/.claude/plan-context.json")
    LSID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    live = pathlib.Path(tmp) / "live"
    (live / ".claude").mkdir(parents=True)
    side = live / ".claude" / "plan-context.json"
    unl = str(transcript_for(tmp, "claude-unlisted-test"))   # now = 21004

    def stamp(minutes_ago, ms=False):
        t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes_ago)
        return t.strftime("%Y-%m-%dT%H:%M:%S") + (".%03dZ" % (t.microsecond // 1000) if ms else "Z")

    def sidecar(window=400000, session_id=LSID, updated=None, raw=None):
        if side.is_symlink() or side.exists():
            side.unlink()
        if raw is None:
            raw = json.dumps({"session_id": session_id, "window": window,
                              "updated": stamp(1) if updated is None else updated})
        side.write_text(raw, encoding="utf-8")

    def live_run(*extra, sid=LSID, cwd=live, timeout=None):
        env = {} if sid is None else {"CLAUDE_CODE_SESSION_ID": sid}
        r = subprocess.run([sys.executable, SCRIPT, "--format", "json", "--transcript", unl,
                            *extra], capture_output=True, text=True, timeout=timeout,
                           env=env_for(home, **env), cwd=str(cwd))
        try:
            return r.returncode, json.loads(r.stdout)
        except ValueError:
            return r.returncode, {"_raw": r.stdout + r.stderr}

    def fell_through(label, rc, j):
        check(rc == 0 and j.get("verdict") == "unknown" and j.get("window") is None
              and "live session" not in (j.get("reason") or ""),
              f"{label} -> ignored, unlisted model stays unknown, exit 0 "
              f"(rc={rc}, {j.get('verdict')}, {j.get('window')})")

    sidecar()
    rc, j = live_run()
    check(rc == 0 and j.get("verdict") not in (None, "unknown") and j.get("window") == 400000
          and j.get("pct") == round(21004 / 400000 * 100, 1),
          f"unknown model + matching fresh sidecar -> window 400000, a real verdict "
          f"({j.get('verdict')}, {j.get('window')}, {j.get('pct')})")
    check("live session" in (j.get("reason") or "")
          and "live session" in (j.get("window_source") or ""),
          f"reason says the window came from the live session ({j.get('reason')})")
    sidecar(updated=stamp(1, ms=True))
    rc, j = live_run()
    check(j.get("window") == 400000,
          f"JS toISOString shape (milliseconds + Z) is accepted ({j.get('window')})")
    sidecar(updated=stamp(-0.5))
    rc, j = live_run()
    check(j.get("window") == 400000, f"30 s in the future is within tolerance ({j.get('window')})")
    # The mod writes the sidecar beside the state file it found walking up from the
    # session's cwd; run from below that root, the reader finds the same file.
    sub = live / "sub" / "deeper"
    sub.mkdir(parents=True)
    sidecar()
    rc, j = live_run(cwd=sub)
    check(j.get("window") is None,
          f"no state file above: a subdirectory's own .claude is read, none there ({j.get('window')})")
    (live / ".claude" / "plan-progress.json").write_text("{}", encoding="utf-8")
    rc, j = live_run(cwd=sub)
    check(j.get("window") == 400000 and "live session" in (j.get("reason") or ""),
          f"run from below the state root -> the root's sidecar is read ({j.get('window')})")
    (live / ".claude" / "plan-progress.json").unlink()

    sidecar(session_id="ffffffff-0000-0000-0000-000000000000")
    fell_through("session-id mismatch", *live_run())
    sidecar()
    fell_through("CLAUDE_CODE_SESSION_ID unset", *live_run(sid=None))
    sidecar(session_id="")
    fell_through("empty session_id with an empty env var", *live_run(sid=""))
    sidecar(updated=stamp(20))
    fell_through("sidecar 20 min old", *live_run())
    sidecar(updated=stamp(-10))
    fell_through("`updated` 10 min in the future", *live_run())
    for bad in ("yesterday", 1759564800, None, stamp(1)[:-1]):
        sidecar(raw=json.dumps({"session_id": LSID, "window": 400000, "updated": bad}))
        fell_through(f"`updated` = {bad!r}", *live_run())
    sidecar(raw=json.dumps({"session_id": LSID, "window": 400000}))
    fell_through("no `updated`", *live_run())
    for bad in (0, -5, True, "400000", 400000.5, None):
        sidecar(window=bad)
        fell_through(f"window = {bad!r}", *live_run())
    for label, raw in (("malformed JSON", "{not json"), ("a JSON list", "[1, 2]"),
                       # Valid JSON padded past the cap with whitespace, so a cut read
                       # still parses: only the size check rejects it.
                       ("an oversized file", json.dumps({"session_id": LSID, "window": 400000,
                                                         "updated": stamp(1)})
                        + " " * (128 * 1024))):
        sidecar(raw=raw)
        fell_through(label, *live_run())

    real = pathlib.Path(tmp) / "elsewhere.json"
    real.write_text(json.dumps({"session_id": LSID, "window": 400000, "updated": stamp(1)}))
    side.unlink()
    side.symlink_to(real)
    fell_through("symlinked sidecar", *live_run())
    side.unlink()
    linked = pathlib.Path(tmp) / "linked-cwd"
    linked.mkdir()
    (linked / ".claude").symlink_to(live / ".claude")
    sidecar()
    fell_through("symlinked .claude directory", *live_run(cwd=linked))
    side.unlink()
    os.mkfifo(side)
    try:
        fell_through("a FIFO sidecar (no hang)", *live_run(timeout=20))
    except subprocess.TimeoutExpired:
        check(False, "a FIFO sidecar hangs the script")
    side.unlink()

    sidecar()
    rc, j = live_run("--window", "300000")
    check(j.get("window") == 300000 and j.get("window_source") == "--window",
          f"--window beats the sidecar ({j.get('window')}, {j.get('window_source')})")
    if "claude-haiku-4-5" in TABLE:
        hk = str(transcript_for(tmp, "claude-haiku-4-5"))
        r = subprocess.run([sys.executable, SCRIPT, "--format", "json", "--transcript", hk],
                           capture_output=True, text=True, cwd=str(live),
                           env=env_for(home, CLAUDE_CODE_SESSION_ID=LSID))
        j = json.loads(r.stdout or "{}")
        check(j.get("window") == 400000 and "live session" in (j.get("window_source") or ""),
              f"the sidecar beats the model table ({j.get('window')}, {j.get('window_source')})")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if FAILURES:
    print(f"FAILED — {len(FAILURES)} check(s):")
    for f in FAILURES:
        print(f"  {f}")
    sys.exit(1)
print("OK — context-usage.py locates the transcript, reports the exact last-row context, "
      "resolves the window from its table, and says unknown for anything it cannot prove")
