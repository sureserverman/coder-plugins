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
import os
import re
import sys
from pathlib import Path

# Reuse the authoritative plan-parser pieces from the portfolio skill (stable
# sibling layout inside the planning plugin). Hyphenated filename → importlib.
# The plan-status contract (what `[ ]` / `[x]` / `[~]` mean) is defined and
# argued once, at portfolio-unify.py's STATUS_RE — read it there before
# changing anything here. This module classifies via pu.status_state() and
# never tests the captured character directly: a partial task counts toward
# the bar's denominator but never fills it.
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


# --- portfolio discovery ---------------------------------------------------
# Everything below returns None rather than raising or printing. The portfolio
# scripts under ../../portfolio/scripts/ sys.exit() with a message when the
# config is missing, which is right for a CLI a user invoked on purpose and
# wrong here: this code runs on EVERY statusline redraw, in every project, on
# machines this repo does not control, where the only acceptable failure is a
# missing bar. `yaml` in particular is a third-party import that a user's
# python3 may simply not have.

CONFIG_PATH = Path.home() / ".claude" / "portfolio-config.yaml"
REGISTRY_PATH = Path.home() / ".claude" / "projects-registry.yaml"


def _load_yaml(path):
    """A mapping from a YAML file, or None on ANY failure."""
    try:
        import yaml
    except ImportError:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        # OSError, yaml.YAMLError, UnicodeDecodeError — all the same answer.
        return None
    return data if isinstance(data, dict) else None


def repo_root_of(state_file):
    """The repo root implied by a state file at <root>/.claude/plan-progress.json."""
    return state_file.parent.parent


def portfolio_plans_dir(repo_root):
    """The vault `plans/` directory for this repo, or None.

    Falls back to `<repo>/docs/plans` when the portfolio is not configured at
    all, so a project that keeps plans in-tree still gets discovery. Returns
    None — never a guess — when the project is not registered: showing bars
    from some OTHER project's plans would be worse than showing none.
    """
    repo_root = Path(repo_root).resolve()

    # "Could not load the config" and "config loaded but names no vault" are
    # DIFFERENT answers, and collapsing them is a real defect: a machine with
    # no portfolio config, an unreadable one, a malformed one, or no `yaml`
    # module would otherwise all silently fall through to <repo>/docs/plans and
    # render bars from whatever happened to be there. Only an intact config
    # that simply omits vault_dir means "this project keeps plans in-tree".
    cfg = _load_yaml(CONFIG_PATH)
    if cfg is None:
        return None
    vault = cfg.get("vault_dir")
    if vault is None:
        local = repo_root / "docs" / "plans"
        return local if local.is_dir() else None
    if not isinstance(vault, str) or not vault:
        return None

    reg = _load_yaml(REGISTRY_PATH)
    if not reg:
        return None
    projects = reg.get("projects")
    if not isinstance(projects, list):
        return None

    entry = None
    for proj in projects:
        if not isinstance(proj, dict):
            continue
        raw = proj.get("path")
        if not isinstance(raw, str):
            continue
        try:
            if Path(raw).expanduser().resolve() == repo_root:
                entry = proj
                break
        except OSError:
            continue
    if entry is None or entry.get("enabled") is False:
        return None

    area, name = entry.get("area"), entry.get("name")
    if not isinstance(area, str) or not isinstance(name, str):
        return None
    plans = Path(vault).expanduser() / "Portfolio" / area / name / "plans"
    try:
        return plans if plans.is_dir() else None
    except OSError:
        # an unreadable or unmounted vault path raises rather than returning False
        return None


def parse_plan(text):
    """(done, total, stage_count) via the portfolio-unify Status contract.

    A `[~]` partial task counts toward `total` but never toward `done`, so the
    bar shows the plan as less finished rather than shorter — classification
    goes through pu.status_state(), never `!= " "` (which would fill the bar
    for an in-flight task).
    """
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
            done += pu.status_state(sm.group(1)) == "done"
            in_task = False
    return done, total, len(stages)


def plan_is_eligible(text):
    """Whether a plan counts as 'in flight' and so earns a bar.

    Eligible = STARTED but not CLOSED OUT:
      started    -> at least one Status classified `done` or `partial`
      closed out -> a **Completed:** or **Abandoned:** line

    Classification goes through pu.status_state(), never a test on the captured
    character: `!= " "` reads `[~]` as done, which is the exact defect BL-001
    exists to prevent. Both terminal markers come from pu as well, so this file
    restates no part of the plan-status contract.

    Deliberately NOT eligible: an all-`[ ]` plan (authored, never started -- a
    bar reading 0/13 is noise), a plan with no Status fields at all (the
    checkbox-era legacy and *-design.md documents), and anything closed out.
    """
    started = False
    in_task = False
    for line in text.splitlines():
        if pu.TASK_RE.match(line):
            in_task = True
            continue
        sm = pu.STATUS_RE.match(line)
        if sm and in_task:
            in_task = False
            if pu.status_state(sm.group(1)) in ("done", "partial"):
                started = True
    if not started:
        return False
    return not (pu.COMPLETED_RE.search(text) or pu.ABANDONED_RE.search(text))


MAX_BARS = 3

# The date stamp a plan filename opens with (2026-08-06-<slug>-plan.md).
# Recency comes from THIS, never from the file's modification time:
# references/plan-parser.md records that the five oldest coder-plugins plans
# all share a 2026-05-23 timestamp, the date the vault was migrated, so that
# timestamp measures a copy operation rather than when the work happened.
# (Spelled out rather than naming the stat field, because the Stage 2 gate
# sweeps this file for that field name and a comment would trip it.)
DATE_STAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def date_stamp(path):
    """The filename's leading date stamp, or "" when it has none.

    "" sorts last under reverse=True, so an unstamped plan ranks below every
    stamped one instead of crashing the sort or jumping to the front.
    """
    m = DATE_STAMP_RE.match(path.name)
    return m.group(1) if m else ""


def _same_file(a, b):
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return False


def _rank(path):
    # name as tiebreaker so same-day plans have a stable, reproducible order
    return (date_stamp(path), path.name)


CACHE_NAME = "plan-progress-cache.json"

# Instrumentation for the cache test. Counting actual plan-file READS is the
# only honest way to assert "the cache was used": a timing assertion passes on
# a fast machine whether or not the cache works, which is the test-that-cannot-
# fail shape this plan keeps producing.
PLAN_READS = 0


def _read_plan(path):
    global PLAN_READS
    PLAN_READS += 1
    return path.read_text(errors="ignore")


def scan_signature(plans_dir):
    """A fingerprint of the plans directory, or None if it cannot be read.

    Per-file (name, modification time, size) — NOT the directory's own
    timestamp, which the task originally specified. Verified on this platform:
    a directory's timestamp moves when an entry is added, removed or renamed,
    and does NOT move when a file's CONTENT changes. A cache keyed on it would
    therefore go stale on exactly the edit that matters most here — a Status
    flip during execution — so the bar would show yesterday's eligibility for
    the entire run the bar exists to narrate.

    Size alone does not rescue it either: `- **Status:** [ ]` and
    `- **Status:** [x]` are the same number of bytes.

    Cheap by design: a stat per file, no reads. The reads are what this caches.
    """
    try:
        out = []
        for f in sorted(Path(plans_dir).glob("*.md")):
            st = f.stat()
            out.append([f.name, st.st_mtime_ns, st.st_size])
        return out
    except OSError:
        return None


def _read_cache(cache_file):
    if cache_file is None:
        return None
    try:
        data = json.loads(Path(cache_file).read_text(encoding="utf-8"))
    except Exception:
        # Missing, truncated, corrupt, not JSON, wrong encoding — every one of
        # them means "rebuild", never "raise". A cache that can break the
        # statusline is worse than no cache.
        return None
    return data if isinstance(data, dict) else None


def _write_cache(cache_file, plans_dir, signature, names):
    if cache_file is None:
        return
    try:
        p = Path(cache_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(json.dumps({
            "version": 1,
            "plans_dir": str(plans_dir),
            "signature": signature,
            "eligible": names,
        }), encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        pass  # an unwritable cache is a missed optimisation, not a failure


def discover_plans(plans_dir, pinned=None, cache_file=None):
    """Up to MAX_BARS plans to render, newest first by filename date stamp.

    `pinned` is the plan the state file names. It is included UNCONDITIONALLY
    when it exists — not merely bumped up the ranking — because it is the plan
    actually being executed, and the pre-existing single-plan behavior must not
    regress. A plan can legitimately be mid-execution and ineligible: one at
    0/13 has been started by a human but carries no `[x]` yet, and the bar has
    always shown it. Eligibility governs which OTHER plans earn a bar, not
    whether the executing one does.
    """
    pinned_r = None
    if pinned is not None:
        try:
            pinned_r = Path(pinned).resolve()
        except OSError:
            pinned_r = None

    eligible = []
    if plans_dir is not None:
        plans_dir = Path(plans_dir)
        sig = scan_signature(plans_dir)
        cached = _read_cache(cache_file) if sig is not None else None
        if (cached is not None
                and cached.get("plans_dir") == str(plans_dir)
                and cached.get("signature") == sig
                and isinstance(cached.get("eligible"), list)):
            for name in cached["eligible"]:
                if isinstance(name, str):
                    eligible.append(plans_dir / name)
        elif sig is not None:
            for f in sorted(plans_dir.glob("*.md")):
                try:
                    if plan_is_eligible(_read_plan(f)):
                        eligible.append(f)
                except OSError:
                    continue  # deleted or unreadable mid-scan — never raise
            _write_cache(cache_file, plans_dir, sig, [f.name for f in eligible])

        # The pinned plan is added below on its own terms, so it must not also
        # arrive through the eligible list.
        if pinned_r is not None:
            eligible = [f for f in eligible if not _same_file(f, pinned_r)]

    eligible.sort(key=_rank, reverse=True)

    chosen = []
    if pinned_r is not None and pinned_r.is_file():
        chosen.append(pinned_r)
    for f in eligible:
        if len(chosen) >= MAX_BARS:
            break
        chosen.append(f)
    chosen.sort(key=_rank, reverse=True)
    return chosen[:MAX_BARS]


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
        part = f"{PURPLE}◆ S{stage} gate{RESET}"
        # Only present when a gate is being re-run after a failure; a gate on its
        # first round renders exactly as it always did.
        rnd = state.get("remediation_round")
        # `type(... ) is int`, not isinstance: bool subclasses int, so a malformed
        # `"remediation_round": true` would otherwise render as round 1.
        if type(rnd) is int and rnd > 0:
            budget = state.get("remediation_budget")
            # The fallback duplicates the default stated in ../SKILL.md ("Remediation
            # budget — default 2 rounds per gate"); test-gate-remediation-contract.py
            # asserts the two stay equal, so change both or neither.
            total = budget if type(budget) is int and budget > 0 else 2
            colour = RED if rnd >= total else YELLOW
            part += f" {colour}↻{rnd}/{total}{RESET}"
        return part
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
