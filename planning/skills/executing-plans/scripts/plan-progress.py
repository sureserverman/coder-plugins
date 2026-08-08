#!/usr/bin/env python3
"""plan-progress — statusline progress bar for executing-plans.

Reads the Claude Code statusline JSON on stdin, walks up from cwd to find
.claude/plan-progress.json (maintained by the executing-plans skill at each
execution transition), parses the referenced plan file with the authoritative
plan-parser regexes from portfolio-unify.py (one contract, one
implementation), and prints a filled progress bar over the plan's Status
fields plus the current stage / task / phase.

Since Stage 3 it prints UP TO THREE lines, not one, and the state file is no
longer the only source. The plan a session is executing comes first, carrying
the phase indicator; below it come other in-flight plans for the same project,
discovered from the portfolio vault. A consequence worth stating plainly,
because it changes the old contract: a project with in-flight plans renders
bars even when NO execution is running there and no state file exists at all.
What it prints is "this project has unfinished plans", not only "this session
is executing one".

Prints NOTHING when there is nothing to say — no state file AND no discoverable
in-flight plan, or any degradation along the way. Safe to chain after any
existing statusline command; a broken environment costs lines, never noise.
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

def _home():
    """A home directory, never an exception.

    `Path.home()` raises RuntimeError when HOME is unset AND the uid has no
    /etc/passwd entry — the arbitrary-uid container case (OpenShift restricted
    SCC, distroless images). posixpath.expanduser swallows the KeyError and
    returns "~" unchanged, and pathlib then raises on that leading tilde.

    That matters far more than the odds suggest, because these paths are
    computed at MODULE SCOPE: the raise happens at import, before
    `if __name__ == "__main__"` installs the try/except below, so the guard
    that makes this file safe never runs. The statusline prints a traceback and
    exits 1 — the single outcome this script exists to never produce.
    """
    try:
        return Path.home()
    except Exception:
        return Path(os.environ.get("HOME") or "/nonexistent")


CONFIG_PATH = _home() / ".claude" / "portfolio-config.yaml"
REGISTRY_PATH = _home() / ".claude" / "projects-registry.yaml"


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
# (The Stage 2 gate proves this two ways: test_ordering_ignores_mtime reads the
# source of date_stamp/_rank and asserts neither names a stat field, and the
# ordering test utimes the oldest plan to 2038 and asserts the order does not
# move. An earlier draft of that gate grepped the whole file for the field
# name, which would have banned mtime for cache invalidation too — a different
# and necessary use — and matched explanatory comments like this one.)
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


def _safe_cache_name(name):
    """Whether a filename read back from the cache may be joined to plans_dir.

    The cache is trusted to skip the reads, so nothing downstream re-validates
    what it names. `Path(plans_dir) / "/etc/passwd"` DISCARDS plans_dir and
    yields /etc/passwd, and "../../x" is preserved literally — so a planted
    cache entry becomes an arbitrary file read whose name is then displayed in
    the user's terminal chrome. Bare filenames only (CWE-22).
    """
    return (isinstance(name, str)
            and name not in ("", ".", "..")
            and not os.path.isabs(name)
            and os.sep not in name
            and (os.altsep is None or os.altsep not in name))


def _is_file(path):
    """`path.is_file()` that cannot raise.

    pathlib swallows only ENOENT / ENOTDIR / EBADF / ELOOP; **EACCES is not in
    that set**, so `is_file()` on a path inside an unreadable directory raises
    PermissionError. Same platform detail as portfolio_plans_dir's `is_dir()`
    guard above — it was handled there and missed here, and the pinned plan is
    the common case, so this raised on every redraw whose vault directory had
    become unreadable.
    """
    try:
        return path.is_file()
    except OSError:
        return False


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
                if _safe_cache_name(name):
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
    if pinned_r is not None and _is_file(pinned_r):
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


def pinned_plan_path(state, state_file):
    """The absolute path of the plan a state file names.

    A relative `plan` is anchored to the REPO ROOT (.claude's parent), never to
    the process cwd — the statusline runs from wherever the user happens to be.
    This is a shared helper rather than inline code because it had to agree in
    two places and did not: render() re-parsed `state["plan"]` itself, kept it
    relative, and then both discover_plans()'s exclusion and render()'s own
    post-filter resolved it against the OS cwd. The pinned plan therefore
    failed to match itself and was rendered twice — once with its phase part,
    once as a discovered stranger — whenever a relative `plan` pointed inside
    the discovered plans directory, which is exactly the shape of the
    `docs/plans` fallback. It also burned a MAX_BARS slot that a genuinely
    different plan should have had.
    """
    plan = Path(state["plan"])
    if not plan.is_absolute():
        plan = state_file.parent.parent / plan
    return plan


def render_pinned(state_file, state=None):
    """The one line for the plan the state file names.

    Kept as its own function, taking the state file rather than a plan path,
    because its output is pinned byte-for-byte by a golden captured from the
    pre-Task-3.1 renderer. render() below composes it with the rest.
    """
    if state is None:
        state = json.loads(state_file.read_text())
    plan = pinned_plan_path(state, state_file)
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


def render_other(plan_path):
    """A bar line for a discovered plan that is NOT the one being executed.

    No phase part and no staleness marker: those describe an execution this
    session is driving, and nothing is driving these. Task 3.3 makes that
    distinction explicit; here it falls out of not having a state to read.
    """
    text = _read_plan(plan_path)
    done, total, _ = parse_plan(text)
    name = plan_path.name
    for suffix in ("-light-plan.md", "-plan.md", ".md"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    out = f"{DIM}⚙ {name}{RESET} "
    if total:
        pct = done * 100 // total
        out += f"{bar(done, total)} {done}/{total} {DIM}({pct}%){RESET}"
    return out


def render(cwd):
    """Every line the status line should carry, in order — possibly none.

    The pinned plan (the one the state file names) keeps render()'s exact
    byte-for-byte output and comes first. Other in-flight plans for the same
    project follow. Returning a LIST rather than a string is the whole of Task
    3.1: main() prints each element on its own line, so a second bar costs a
    line rather than a rewrite.

    Every step degrades to "fewer lines", never to an exception — this is still
    the statusline. Note which corpus lane proves what: lane A (`python3
    plan-progress.py`) comes through main() into here and so exercises the
    guards below; lane B deliberately BYPASSES this function to call the
    discovery surface raw, precisely so those guards cannot mask a function
    that fails to degrade on its own. Reading lane B as evidence about this
    function's exception safety gets it exactly backwards.
    """
    lines = []
    state_file = find_state(cwd)
    pinned = None
    if state_file is not None:
        try:
            # ONE read, one anchoring. Re-reading here to recompute `pinned`
            # also raced executing-plans' overwrite-not-patch state writes: a
            # rewrite landing between the two reads made the second one fail
            # and silently disabled dedup for that redraw.
            state = json.loads(state_file.read_text())
            lines.append(render_pinned(state_file, state))
            pinned = pinned_plan_path(state, state_file)
        except Exception:
            pinned = None           # an unreadable state file pins nothing

    try:
        root = repo_root_of(state_file) if state_file is not None else Path(cwd)
        plans_dir = portfolio_plans_dir(root)
        if plans_dir is not None:
            cache = root / ".claude" / CACHE_NAME
            for p in discover_plans(plans_dir, pinned=pinned, cache_file=cache):
                if pinned is not None and _same_file(p, pinned):
                    continue        # already rendered above, with its phase part
                lines.append(render_other(p))
    except Exception:
        pass                        # discovery is additive: never costs the pinned bar

    return lines


def main():
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    cwd = data.get("cwd") or (data.get("workspace") or {}).get("current_dir") or "."
    for line in render(cwd):
        print(line)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # A statusline must never print a traceback — blank line beats noise.
        sys.exit(0)
