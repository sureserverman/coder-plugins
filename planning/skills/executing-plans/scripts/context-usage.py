#!/usr/bin/env python3
"""Report the current Claude Code session's context size from its transcript.

Why this exists: a plan executor deciding whether to hand off to a fresh session
needs a measured reason, not a feeling that "the context is getting long". Claude
Code writes every assistant turn's API usage into the session transcript, so the
context size at the latest turn is a number the executor can read rather than guess.

The value is exact: it is the sum the API itself reported for the last turn.

    now = input_tokens + cache_read_input_tokens + cache_creation_input_tokens

taken from the LAST main-thread assistant row that carries a usage block. Skipped:
`"isSidechain": true` rows (subagent turns — their context is not this one's),
`"model": "<synthetic>"` rows (client-written placeholders with all-zero usage),
and malformed lines.

Transcript location: `--transcript PATH` if given (the Stop hook receives
`transcript_path`), else `$HOME/.claude/projects/*/<CLAUDE_CODE_SESSION_ID>.jsonl`.

Window resolution — the transcript records no window, and the model id carries no
1M marker (a session running with the `opus[1m]` setting logs plain `claude-opus-…`):

    1. `--window N` wins.
    2. The base window from MODEL_WINDOWS, by exact model id (a dated `-YYYYMMDD`
       suffix is also accepted).
    3. Upgraded to 1M only when the table says the model supports 1M AND there is
       evidence: a `[1m]` suffix on the configured model (ANTHROPIC_MODEL, then
       `model` in <cwd>/.claude/settings.local.json, <cwd>/.claude/settings.json,
       $HOME/.claude/settings.json — first found wins), or a context already
       observed in this transcript above the base window.
    4. A model not in the table has no window → verdict `unknown`.

Verdicts: `handoff` when pct > 50, else `continue`; `unknown` for anything the
script cannot prove. Every verdict carries a `reason` naming the rule and numbers.
An `unknown` verdict never stops a run: exit 0. Exit 2 only on bad CLI usage.

Stdlib only.
"""
import argparse
import glob
import json
import os
import re
import sys

# Source: /home/user/.claude/plugins/marketplaces/anthropic-agent-skills/skills/claude-api/
#   SKILL.md "Current Models (cached: 2026-06-24)" table (lines 177-188) and
#   shared/models.md "Current Models (recommended)" table (lines 58-70);
#   claude-opus-5-5 from https://platform.claude.com/docs/en/about-claude/models/overview
#   "Context window" row (1M tokens), fetched 2026-09-22 — the cached skill predates it.
# model id -> (base window, supports a 1M window). Every 1M model there states 1M
# as its default, so for those the base already is 1M. A model the doc does not
# list is left out on purpose — it resolves to verdict `unknown`, never a guess.
MODEL_WINDOWS = {
    "claude-fable-5-1": (1_000_000, True),
    "claude-opus-5-5": (1_000_000, True),
    "claude-mythos-5-1": (1_000_000, True),
    "claude-fable-5": (1_000_000, True),
    "claude-mythos-5": (1_000_000, True),
    "claude-opus-5": (1_000_000, True),
    "claude-opus-4-8": (1_000_000, True),
    "claude-opus-4-7": (1_000_000, True),
    "claude-opus-4-6": (1_000_000, True),
    "claude-sonnet-5": (1_000_000, True),
    "claude-sonnet-4-6": (1_000_000, True),
    "claude-haiku-4-5": (200_000, False),
}
ONE_M = 1_000_000

HANDOFF_PCT = 50.0

DATED = re.compile(r"-\d{8}$")


def locate_transcript(arg, env, home):
    """Return (path or None, reason when None)."""
    if arg:
        return arg, None
    sid = env.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        return None, "no --transcript and CLAUDE_CODE_SESSION_ID is unset"
    hits = sorted(glob.glob(os.path.join(home, ".claude", "projects", "*",
                                         glob.escape(sid) + ".jsonl")))
    if not hits:
        return None, f"no transcript for session {sid} under {home}/.claude/projects/*/"
    return hits[0], None


def measure(path):
    """Read the transcript. Returns a dict, or None when the file cannot be read.

    Keys: now (int or None), model (str or None), max_seen (int), rows (int).
    """
    now = model = None
    max_seen = rows = 0
    try:
        fh = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return None
    with fh:
        for line in fh:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict) or row.get("type") != "assistant":
                continue
            if row.get("isSidechain") is True:
                continue
            msg = row.get("message")
            if not isinstance(msg, dict) or msg.get("model") == "<synthetic>":
                continue
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                continue
            try:
                ctx = (int(usage.get("input_tokens") or 0)
                       + int(usage.get("cache_read_input_tokens") or 0)
                       + int(usage.get("cache_creation_input_tokens") or 0))
            except (TypeError, ValueError):
                continue
            now, model = ctx, msg.get("model")
            max_seen = max(max_seen, ctx)
            rows += 1
    return {"now": now, "model": model, "max_seen": max_seen, "rows": rows}


def configured_model(env, cwd, home):
    """Return (source, model string) for the configured model, or None."""
    if env.get("ANTHROPIC_MODEL"):
        return "ANTHROPIC_MODEL", env["ANTHROPIC_MODEL"]
    for path in (os.path.join(cwd, ".claude", "settings.local.json"),
                 os.path.join(cwd, ".claude", "settings.json"),
                 os.path.join(home, ".claude", "settings.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and isinstance(data.get("model"), str) and data["model"]:
            return path, data["model"]
    return None


def table_entry(model):
    if not model:
        return None
    base = model[:-4] if model.endswith("[1m]") else model
    if base in MODEL_WINDOWS:
        return MODEL_WINDOWS[base]
    return MODEL_WINDOWS.get(DATED.sub("", base))


def resolve_window(model, window_arg, max_seen, configured):
    """Return (window or None, window_source)."""
    if window_arg:
        return window_arg, "--window"
    entry = table_entry(model)
    if entry is None:
        return None, "unlisted model"
    base, supports_1m = entry
    if supports_1m and base < ONE_M:
        if model.endswith("[1m]"):
            return ONE_M, "table+[1m] (transcript model id)"
        if configured and configured[1].endswith("[1m]"):
            return ONE_M, f"table+[1m] ({configured[0]}: {configured[1]})"
        if max_seen > base:
            return ONE_M, f"table+observed ({max_seen} > base {base})"
    return base, "table"


def verdict(result):
    """Return (verdict, reason) for a result dict built by main()."""
    if result.get("_unknown"):
        return "unknown", result["_unknown"]
    pct = result["pct"]
    rule = (f"now={result['now']} of window={result['window']} "
            f"({result['window_source']}) is {pct}%")
    if pct > HANDOFF_PCT:
        return "handoff", f"{rule} > {HANDOFF_PCT:g}% handoff threshold"
    return "continue", f"{rule} <= {HANDOFF_PCT:g}% handoff threshold"


def build(args, env, cwd, home):
    res = {"now": None, "window": None, "window_source": None, "pct": None,
           "stage_costs": [], "last_stage_cost": None, "projected_pct": None,
           "model": None, "transcript": None}
    path, why = locate_transcript(args.transcript, env, home)
    res["transcript"] = path
    if path is None:
        res["_unknown"] = why
        return res
    m = measure(path)
    if m is None:
        res["_unknown"] = f"transcript {path} cannot be read"
        return res
    if m["now"] is None:
        res["_unknown"] = f"transcript {path} has no main-thread assistant row with usage"
        return res
    res["now"], res["model"] = m["now"], m["model"]
    window, source = resolve_window(m["model"], args.window, m["max_seen"],
                                    configured_model(env, cwd, home))
    res["window_source"] = source
    if window is None:
        res["_unknown"] = (f"model {m['model']!r} is not in MODEL_WINDOWS and no --window "
                           f"was given; now={m['now']}")
        return res
    res["window"] = window
    res["pct"] = round(m["now"] / window * 100, 1)
    if res["last_stage_cost"] is not None:
        res["projected_pct"] = round(res["pct"] + res["last_stage_cost"] / window * 100, 1)
    return res


def positive_int(text):
    try:
        n = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {text!r}")
    if n <= 0:
        raise argparse.ArgumentTypeError(f"must be > 0: {n}")
    return n


def fmt(v):
    return "null" if v is None else str(v)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="context-usage")
    ap.add_argument("--transcript", help="transcript JSONL path (overrides the session id)")
    ap.add_argument("--window", type=positive_int, help="context window in tokens (wins)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    args = ap.parse_args(argv)

    res = build(args, os.environ, os.getcwd(), os.path.expanduser("~"))
    res["verdict"], res["reason"] = verdict(res)
    res.pop("_unknown", None)

    if args.format == "json":
        print(json.dumps(res))
    else:
        print(f"context-usage: verdict={res['verdict']} now={fmt(res['now'])} "
              f"window={fmt(res['window'])} pct={fmt(res['pct'])} "
              f"projected_pct={fmt(res['projected_pct'])} reason: {res['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
