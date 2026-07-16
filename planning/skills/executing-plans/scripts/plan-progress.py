#!/usr/bin/env python3
"""plan-progress — statusline progress bar for executing-plans.

Reads the Claude Code statusline JSON on stdin, walks up from cwd to find
.claude/plan-progress.json (maintained by the executing-plans skill at each
execution transition), parses the referenced plan file with the authoritative
plan-parser regexes from portfolio-unify.py (one contract, one
implementation), and prints ONE line: a filled progress bar over the plan's
Status fields plus the current stage / task / phase.

Prints NOTHING when no plan is executing (no state file, unreadable state,
missing plan) — safe to chain after any existing statusline command; the
extra line only appears mid-execution and disappears at close-out.
"""
import datetime
import importlib.util
import json
import sys
from pathlib import Path

# Reuse the authoritative plan-parser pieces from the portfolio skill (stable
# sibling layout inside the planning plugin). Hyphenated filename → importlib.
_UNIFY = Path(__file__).resolve().parents[2] / "portfolio" / "scripts" / "portfolio-unify.py"
_spec = importlib.util.spec_from_file_location("portfolio_unify", _UNIFY)
pu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pu)

BAR_WIDTH = 20
STALE_AFTER_H = 12  # a state file this old is probably a crashed session

GREEN = "\033[38;2;0;160;0m"
RED = "\033[38;2;255;85;85m"
YELLOW = "\033[38;2;230;200;0m"
CYAN = "\033[38;2;46;149;153m"
PURPLE = "\033[38;2;167;139;250m"
DIM = "\033[2m"
RESET = "\033[0m"


def find_state(start):
    d = Path(start).resolve()
    for p in [d, *d.parents]:
        f = p / ".claude" / "plan-progress.json"
        if f.is_file():
            return f
    return None


def parse_plan(text):
    """(done, total, stage_count) via the portfolio-unify Status contract."""
    stages = set()
    done = total = 0
    in_task = False
    for line in text.splitlines():
        sh = pu.STAGEHDR_RE.match(line)
        if sh:
            stages.add(int(sh.group(1)))
        if pu.TASK_RE.match(line):
            in_task = True
        sm = pu.STATUS_RE.match(line)
        if sm and in_task:
            total += 1
            done += sm.group(1) != " "
            in_task = False
    return done, total, len(stages)


def bar(done, total):
    filled = round(BAR_WIDTH * done / total) if total else 0
    return (
        f"{DIM}▐{RESET}{GREEN}{'█' * filled}{RESET}"
        f"{DIM}{'░' * (BAR_WIDTH - filled)}▌{RESET}"
    )


def phase_part(state):
    phase = state.get("phase", "task")
    stage = state.get("stage")
    if phase == "preflight":
        return f"{YELLOW}⚑ preflight{RESET}"
    if phase == "gate":
        return f"{PURPLE}◆ S{stage} gate{RESET}"
    if phase == "closeout":
        return f"{GREEN}✔ close-out{RESET}"
    if phase == "blocked":
        note = state.get("note") or state.get("task_desc") or ""
        return f"{RED}✘ blocked{RESET}" + (f" {DIM}{note}{RESET}" if note else "")
    task = state.get("task")
    desc = state.get("task_desc") or ""
    label = f"T{task} " if task else ""
    return f"{GREEN}▶ {label}{RESET}{desc}"


def staleness(state):
    upd = state.get("updated")
    if not upd:
        return ""
    try:
        ts = datetime.datetime.fromisoformat(upd.replace("Z", "+00:00"))
    except ValueError:
        return ""
    age = datetime.datetime.now(datetime.timezone.utc) - ts
    hours = age.total_seconds() / 3600
    if hours >= STALE_AFTER_H:
        return f" {DIM}(stale {int(hours)}h){RESET}"
    return ""


def render(state_file):
    state = json.loads(state_file.read_text())
    plan = Path(state["plan"])
    if not plan.is_absolute():
        # relative plan paths resolve against the repo root (.claude's parent)
        plan = state_file.parent.parent / plan
    text = plan.read_text(errors="ignore")
    done, total, stage_count = parse_plan(text)
    name = plan.name
    for suffix in ("-light-plan.md", "-plan.md", ".md"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    out = f"{CYAN}⚙ {name}{RESET} "
    if total:
        pct = done * 100 // total
        out += f"{bar(done, total)} {done}/{total} {DIM}({pct}%){RESET} {DIM}·{RESET} "
    stage = state.get("stage")
    if stage and stage_count:
        out += f"S{stage}/{stage_count} "
    out += phase_part(state) + staleness(state)
    return out


def main():
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    cwd = data.get("cwd") or (data.get("workspace") or {}).get("current_dir") or "."
    state_file = find_state(cwd)
    if not state_file:
        return
    print(render(state_file))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # A statusline must never print a traceback — blank line beats noise.
        sys.exit(0)
