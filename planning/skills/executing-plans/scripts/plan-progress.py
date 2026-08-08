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
import hashlib
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


# pathlib raises ValueError -- NOT OSError -- for a path containing a NUL byte
# ("embedded null byte"). Every guard in this file that means "this path is
# unusable, degrade" therefore has to name both, and a bare `except OSError` is
# a hole wherever the path came from text rather than from a directory listing.
# Three sources feed such paths: the `cwd` in the statusline's stdin JSON, the
# `plan` field of the state file, and -- since Task 3.2 -- the `Master:` /
# `- **Plan:**` links read out of plan PROSE. Found by Tier-1 review and
# reproduced: one NUL in a sub-plan's backlink blanked the whole status line,
# pinned bar included, on every redraw.
#
# WHICH calls raise is not uniform, and guessing it wrong is how the hole got
# there. Measured on CPython 3.12: `stat()`, `resolve()` and `read_text()`
# RAISE, while `is_file()`, `is_dir()` and `exists()` SWALLOW it internally
# (pathlib classes a NUL path as non-encodable and returns False). The guards
# below therefore load-bear on the first group and are belt-and-braces on the
# second; test-plan-progress.py pins both halves, so a future pathlib that
# changes either one fails loudly rather than silently reopening this.
BAD_PATH = (OSError, ValueError)


def find_state(start):
    try:
        d = Path(start).resolve()
    except BAD_PATH:
        return None
    for p in [d, *d.parents]:
        try:
            f = p / ".claude" / "plan-progress.json"
            if f.is_file():
                return f
        except BAD_PATH:
            continue
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
    # `repo_root` reaches here from the statusline's stdin `cwd` when no state
    # file exists, so it is untrusted text like everything else in BAD_PATH's
    # note. Guarded at the top rather than left to render()'s outer try, because
    # the corpus sweep calls this function RAW on purpose — a surface that only
    # degrades when someone else catches for it is not a surface that degrades.
    try:
        repo_root = Path(repo_root).resolve()
    except BAD_PATH:
        return None

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
        try:
            local = repo_root / "docs" / "plans"
            return local if local.is_dir() else None
        except BAD_PATH:
            return None
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
        except BAD_PATH:
            continue
    if entry is None or entry.get("enabled") is False:
        return None

    area, name = entry.get("area"), entry.get("name")
    if not isinstance(area, str) or not isinstance(name, str):
        return None
    plans = Path(vault).expanduser() / "Portfolio" / area / name / "plans"
    try:
        return plans if plans.is_dir() else None
    except BAD_PATH:
        # an unreadable or unmounted vault path raises rather than returning False
        return None


def parse_plan(text, path=None):
    """(done, total, stage_count) via the portfolio-unify Status contract.

    A `[~]` partial task counts toward `total` but never toward `done`, so the
    bar shows the plan as less finished rather than shorter — classification
    goes through pu.status_state(), never `!= " "` (which would fill the bar
    for an in-flight task).
    """
    if pu.is_master_plan(text, path):
        return parse_master(text)
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


def parse_master(text):
    """(done, total, stage_count) for a MASTER plan, from its sub-plan register.

    A master has no `### Task N.N` headings, so the ordinary counter reads every
    master as 0/0 — indistinguishable from a plan nobody has started. That is
    why zero of the vault's 517 plans that are masters had ever classified as in
    flight: not a decision, an artifact of two regexes not matching.

    Its progress is its register: one `### Sub-plan N:` entry per sub-plan, each
    with a `- **Status:**` the master's own close-out flips. stage_count is 0 —
    a master has sub-plans, not stages, so `S2/4` would be a category error.
    Sub-plan registers also carry `**Gate:**` blocks of `- [ ]` checkboxes;
    those are not Status lines and STATUS_RE does not match them.
    """
    done = total = 0
    in_entry = False
    for line in text.splitlines():
        if pu.SUBPLAN_RE.match(line):
            in_entry = True
            continue
        sm = pu.STATUS_RE.match(line)
        if sm and in_entry:
            total += 1
            done += pu.status_state(sm.group(1)) == "done"
            in_entry = False        # one Status per entry; consume it
    return done, total, 0


def plan_is_eligible(text, path=None):
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
    in_entry = False
    # A master's progress lives in its `### Sub-plan N:` register, not in Task
    # headings it does not have. Counting only TASK_RE is why no master had ever
    # been eligible -- every one read as "authored, never started".
    opener = pu.SUBPLAN_RE if pu.is_master_plan(text, path) else pu.TASK_RE
    for line in text.splitlines():
        if opener.match(line):
            in_entry = True
            continue
        sm = pu.STATUS_RE.match(line)
        if sm and in_entry:
            in_entry = False
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
    except BAD_PATH:
        return False


def _rank(path):
    # name as tiebreaker so same-day plans have a stable, reproducible order
    return (date_stamp(path), path.name)


CACHE_NAME = "plan-progress-cache.json"
CACHE_VERSION = 2   # bumped by the rule-signature fix below; discards every v1 cache


def rule_signature():
    """A fingerprint of the CODE that produced a cache's verdicts, or None.

    scan_signature() below fingerprints the plans DIRECTORY, so the cache
    correctly rebuilds whenever a plan file changes. Nothing fingerprinted the
    ELIGIBILITY RULE, and that is an independent axis: when `plan_is_eligible`
    itself changes, every cache on disk keeps serving verdicts computed by the
    OLD rule against a directory whose signature is still perfectly valid — and
    keeps doing so forever, because nothing in the key can ever notice. Only an
    unrelated edit to some plan file breaks the spell.

    Not hypothetical, and not caught by any test. Making masters countable
    (BL-054, `4d45fbf`) changed the rule; measured immediately afterwards, 3 of
    the 4 caches on this machine went on hiding every master bar. The feature
    had shipped and could not fire — twice over, since the tree glyphs that
    render those masters have nothing to render without them.

    Deliberately a digest of the two whole source files rather than of the
    rule's individual functions and regexes. Eligibility depends on
    plan_is_eligible, TASK_RE, SUBPLAN_RE, STATUS_RE, COMPLETED_RE,
    ABANDONED_RE, status_state and is_master_plan; enumerating those here would
    create exactly the lockstep site that drifts, which is the bug class this
    key exists to close. Over-invalidating on a comment edit costs one ~12 ms
    rescan, once.

    CONTENT, not (mtime, size), which is what this first shipped as. Review
    caught the gap: a deployment that preserves timestamps across a real edit —
    `rsync -a`, some Docker COPY layers, a same-second checkout — leaves
    (mtime, size) identical while the rule underneath has changed, which is
    precisely the silent-stale failure this function exists to prevent, sneaking
    back in through the key itself. Measured: 0.048 ms against a 33 ms redraw.
    """
    out = []
    for f in (Path(__file__), _UNIFY):
        try:
            out.append(hashlib.sha256(Path(f).read_bytes()).hexdigest())
        except BAD_PATH:
            return None     # rule unknown -> decline the cache, never trust a stale one
    return out

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
    except BAD_PATH:
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
    except BAD_PATH:
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


def _write_cache(cache_file, plans_dir, signature, names, rule):
    if cache_file is None or rule is None:
        return              # an unkeyed cache is worse than none — see rule_signature()
    try:
        p = Path(cache_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(json.dumps({
            "version": CACHE_VERSION,
            "rule": rule,
            "plans_dir": str(plans_dir),
            "signature": signature,
            "eligible": names,
        }), encoding="utf-8")
        os.replace(tmp, p)
    except BAD_PATH:
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
        except BAD_PATH:
            pinned_r = None

    eligible = []
    if plans_dir is not None:
        plans_dir = Path(plans_dir)
        sig = scan_signature(plans_dir)
        rule = rule_signature()
        cached = _read_cache(cache_file) if (sig is not None and rule is not None) else None
        if (cached is not None
                # `version` was written from the start and never once read — a
                # key field that existed and did nothing. Checked now, so a
                # future format change invalidates rather than misreads.
                and cached.get("version") == CACHE_VERSION
                and cached.get("rule") == rule
                and cached.get("plans_dir") == str(plans_dir)
                and cached.get("signature") == sig
                and isinstance(cached.get("eligible"), list)):
            for name in cached["eligible"]:
                if _safe_cache_name(name):
                    eligible.append(plans_dir / name)
        elif sig is not None:
            for f in sorted(plans_dir.glob("*.md")):
                try:
                    if plan_is_eligible(_read_plan(f), f):
                        eligible.append(f)
                except BAD_PATH:
                    continue  # deleted or unreadable mid-scan — never raise
            _write_cache(cache_file, plans_dir, sig, [f.name for f in eligible], rule)

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


# Tree glyphs for a master's sub-plans. Box-drawing rather than ASCII `|-`
# because every other glyph in this file is already non-ASCII (█ ░ ⚙ ▶ ◆ ⚑),
# so a terminal that mangles these was already mangling the bar itself.
TREE_MID = "├─ "
TREE_LAST = "└─ "


def _plan_text(path):
    """A plan's text, or "" — grouping must never cost a bar."""
    try:
        return _read_plan(path)
    except BAD_PATH:
        return ""


def master_of(text, path):
    """The path this sub-plan's `Master:` backlink names, or None."""
    m = pu.MASTER_BACKLINK_RE.search(text)
    if not m:
        return None
    target = pu.link_target(m.group(1))
    return path.parent / target if target else None


def subplans_of(text, path):
    """Every path this master's register `- **Plan:**` lines name, in order.

    Order is load-bearing: it is the register's dependency order, which is what
    a reader expects children to be listed in, and it is the only ordering that
    survives a sub-plan whose filename date stamp does not match its number.
    """
    out = []
    for m in pu.SUBPLAN_LINK_RE.finditer(text):
        target = pu.link_target(m.group(1))
        if target:
            out.append(path.parent / target)
    return out


def group_plans(paths, pinned=None):
    """[(path, prefix)] — each master immediately above its own sub-plans.

    Presentation only. This reorders and prefixes what discovery already chose;
    it never adds a plan and never drops one, so the cap and the eligibility
    filter keep meaning exactly what Stage 2 gated them to mean. A sub-plan
    whose master is not among the chosen plans therefore renders as it always
    did — top level, no glyph — which is the COMMON case, since a master earns
    its own bar on its own eligibility and often has none.

    `pinned` keeps the plan this session is executing at the top, as the old
    single-source renderer did. It is the plan's GROUP that is hoisted, not the
    plan: when the pinned plan is a sub-plan, its master has to stay above it or
    the tree glyphs point at nothing.
    """
    # Path keys throughout: discover_plans() already deduplicates by _same_file,
    # so no two entries here name one file under two spellings.
    texts = {p: _plan_text(p) for p in paths}
    masters = [p for p in paths if pu.is_master_plan(texts[p], p)]

    # Union of the two links, not either alone: the backlink is missing from
    # some sub-plans and the register entry from others, and a sub-plan is a
    # sub-plan if EITHER side says so.
    register = {m: subplans_of(texts[m], m) for m in masters}
    parent_of = {}
    for p in paths:
        if p in masters:
            continue
        back = master_of(texts[p], p)
        for m in masters:
            if ((back is not None and _same_file(back, m))
                    or any(_same_file(c, p) for c in register[m])):
                parent_of[p] = m
                break

    def child_order(master, kid):
        # Register position first; a child linked only by its backlink has none
        # and falls back to filename order. The two never compare against each
        # other, so the mixed key types below never meet.
        for i, c in enumerate(register[master]):
            if _same_file(c, kid):
                return (0, i)
        return (1, _rank(kid))

    groups = []
    for m in masters:
        kids = [p for p in paths if parent_of.get(p) == m]
        kids.sort(key=lambda k: child_order(m, k))
        groups.append([m] + kids)
    for p in paths:
        if p not in masters and p not in parent_of:
            groups.append([p])

    # A group ranks by its NEWEST member, so grouping never pushes a recent
    # sub-plan below an older unrelated plan just because its master is old.
    def group_rank(g):
        holds_pinned = pinned is not None and any(_same_file(x, pinned) for x in g)
        return (holds_pinned, max(_rank(x) for x in g))

    groups.sort(key=group_rank, reverse=True)

    out = []
    for g in groups:
        out.append((g[0], ""))
        for i, kid in enumerate(g[1:]):
            glyph = TREE_LAST if i == len(g) - 2 else TREE_MID
            out.append((kid, f"{DIM}{glyph}{RESET}"))
    return out


def bar(done, total):
    filled = round(BAR_WIDTH * done / total) if total else 0
    return (
        f"{DIM}▐{RESET}{GREEN}{'█' * filled}{RESET}"
        f"{DIM}{'░' * (BAR_WIDTH - filled)}▌{RESET}"
    )


# The state file has TWO dialects in the wild, and the renderer only knew one.
# references/progress-state-file.md specifies `phase` as one of five keywords,
# `stage` as an integer and `task` as "N.M". Real executions also write prose
# into those same keys and put the integers in `stage_index`/`stage_total`
# beside them -- android/writer-pad's live file carries
#   "phase": "STOPPED — Stage 2 re-gate FAILED; awaiting user direction"
#   "stage_index": 2, "stage_total": 2   (and no `stage` or `task` at all)
# Neither side is simply wrong: the richer file is more useful to a human
# reading it, which is why the fix is not "make writers comply". The renderer
# reads the ints when they are there, interpolates `stage`/`task` only when they
# are the shape the schema promises, and otherwise says NOTHING -- a status line
# has one line's worth of room, so a paragraph pasted into it is worse than a
# missing field. Verified against the live file, not a fixture.
KNOWN_PHASES = ("preflight", "task", "gate", "closeout", "blocked")
TASK_ID_RE = re.compile(r"^\d+\.\d+$")


def _int(v):
    """`v` when it is a real int, else None.

    `type(v) is int`, not isinstance: bool subclasses int, so a stray
    `"stage_index": true` would otherwise render as stage 1. Same discipline
    the remediation_round field already uses below.
    """
    return v if type(v) is int else None


def _stage_int(v):
    """A POSITIVE int, else None.

    Stages are 1-indexed everywhere in the format (`## Stage 1 — …`), so 0 and
    negatives are malformed rather than edge cases, and both degrade to "no
    stage position" instead of rendering `S0/3` or `S-1/3`. Stated as its own
    predicate because the precedence below then has no falsy-but-valid value
    left to trip over: review flagged the earlier `_int(a) or _int(b)` form for
    silently letting `stage` win over an explicit `stage_index: 0`.
    """
    n = _int(v)
    return n if n is not None and n > 0 else None


def stage_position(state, stage_count):
    """(index, total) for the `S2/4` part, or None when the file does not say.

    Among VALID values, `stage_index`/`stage_total` win over `stage` — a file
    carrying both is one where `stage` holds prose. `stage_total` in turn wins
    over the count parsed from the plan: a sub-plan mid-master knows its own
    stage total, and a master's parsed count is 0 by design.
    """
    idx = _stage_int(state.get("stage_index"))
    if idx is None:
        idx = _stage_int(state.get("stage"))
    total = _stage_int(state.get("stage_total"))
    if total is None:
        total = _stage_int(stage_count)
    return (idx, total) if idx is not None and total is not None else None


def phase_part(state):
    phase = state.get("phase", "task")
    if phase not in KNOWN_PHASES:
        # A prose phase used to fall through every branch into the task case and
        # render a bare "▶ " with nothing after it -- seen live in writer-pad.
        # An unrecognised phase means the file is telling us something this bar
        # has no room for, so it says nothing at all.
        return ""
    stage = _stage_int(state.get("stage_index"))
    if stage is None:
        stage = _stage_int(state.get("stage"))
    if phase == "preflight":
        return f"{YELLOW}⚑ preflight{RESET}"
    if phase == "gate":
        # `S{stage}` only when there IS one; the old form rendered "SNone gate"
        # for a gate whose stage the file did not record.
        part = (f"{PURPLE}◆ S{stage} gate{RESET}" if stage is not None
                else f"{PURPLE}◆ gate{RESET}")
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
    desc = state.get("task_desc")
    desc = desc if isinstance(desc, str) else ""
    if isinstance(task, str) and TASK_ID_RE.match(task):
        label = f"T{task} "
    else:
        # Everything that is not a schema-shaped "N.M" loses only the LABEL.
        # `"task": "close-out: owed review passes dispatched over Stage 2 and
        # whole-plan diffs"` is a real value from a real run; interpolated raw it
        # puts a sentence where `T3.1` belongs and pushes every other bar off the
        # line, so it is dropped. But `task_desc` is free text BY SCHEMA and is
        # not implicated by a malformed sibling field — review caught an earlier
        # version returning "" here, which discarded a perfectly good desc and
        # contradicted the `task is None` case two lines up, where the same desc
        # was kept. One rule now: a bad `task` costs the `T…` label, nothing else.
        label = ""
    if not label and not desc:
        return ""       # nothing to say -- the bare glyph was noise, not data
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
    done, total, stage_count = parse_plan(text, plan)
    name = plan.name
    for suffix in ("-light-plan.md", "-plan.md", ".md"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    out = f"{CYAN}⚙ {name}{RESET} "
    if total:
        pct = done * 100 // total
        out += f"{bar(done, total)} {done}/{total} {DIM}({pct}%){RESET}"

    # Built as a list so the ` · ` separator is emitted only when something
    # actually follows it. The old form appended it unconditionally with the bar
    # and then appended a possibly-empty phase, so a file this renderer could not
    # read left a dangling "(100%) · " — verified live in writer-pad.
    tail = []
    pos = stage_position(state, stage_count)
    if pos:
        tail.append(f"S{pos[0]}/{pos[1]}")
    part = phase_part(state)
    if part:
        tail.append(part)
    if tail:
        if total:
            out += f" {DIM}·{RESET} "
        out += " ".join(tail)
    out += staleness(state)
    return out


def render_other(plan_path):
    """A bar line for a discovered plan that is NOT the one being executed.

    No phase part and no staleness marker: those describe an execution this
    session is driving, and nothing is driving these. Task 3.3 makes that
    distinction explicit; here it falls out of not having a state to read.
    """
    text = _read_plan(plan_path)
    done, total, _ = parse_plan(text, plan_path)
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

    The pinned plan (the one the state file names) keeps render_pinned()'s exact
    byte-for-byte output, and its group leads. Other in-flight plans for the
    same project follow, each master immediately above its own sub-plans.
    Returning a LIST rather than a string is the whole of Task 3.1: main()
    prints each element on its own line, so a second bar costs a line rather
    than a rewrite.

    Every step degrades to "fewer lines", never to an exception — this is still
    the statusline. Note which corpus lane proves what: lane A (`python3
    plan-progress.py`) comes through main() into here and so exercises the
    guards below; lane B deliberately BYPASSES this function to call the
    discovery surface raw, precisely so those guards cannot mask a function
    that fails to degrade on its own. Reading lane B as evidence about this
    function's exception safety gets it exactly backwards.
    """
    state_file = find_state(cwd)
    state = pinned = None
    if state_file is not None:
        try:
            # ONE read, one anchoring. Re-reading to recompute `pinned` also
            # raced executing-plans' overwrite-not-patch state writes: a rewrite
            # landing between the two reads made the second one fail and
            # silently disabled dedup for that redraw.
            state = json.loads(state_file.read_text())
            pinned = pinned_plan_path(state, state_file)
        except Exception:
            state = pinned = None   # an unreadable state file pins nothing

    chosen = []
    try:
        root = repo_root_of(state_file) if state_file is not None else Path(cwd)
        plans_dir = portfolio_plans_dir(root)
        if plans_dir is not None:
            cache = root / ".claude" / CACHE_NAME
            chosen = discover_plans(plans_dir, pinned=pinned, cache_file=cache)
    except Exception:
        chosen = []                 # discovery is additive: never costs the pinned bar

    # Discovery normally returns the pinned plan itself, but it returns nothing
    # at all when the project is unregistered, the vault is unreadable, or the
    # scan raised. The plan this session is executing has to render in every one
    # of those cases -- that is the pre-Stage-2 behavior, and it is the bar that
    # matters most.
    if pinned is not None and _is_file(pinned) and not any(
            _same_file(p, pinned) for p in chosen):
        chosen.insert(0, pinned)

    # BAD_PATH above fixes the root cause; this bounds the blast radius of the
    # NEXT one. group_plans() is the only step between having the plans and
    # printing them, so anything it raises costs every bar at once — including
    # the pinned bar the whole function above works to preserve. Grouping is
    # decoration; losing it must cost the glyphs, never the lines.
    try:
        grouped = group_plans(chosen, pinned=pinned)
    except Exception:
        grouped = [(p, "") for p in chosen]

    lines = []
    for path, prefix in grouped:
        # Per line, not per block: an unreadable plan costs its own bar and
        # leaves its siblings standing.
        try:
            if state is not None and pinned is not None and _same_file(path, pinned):
                lines.append(prefix + render_pinned(state_file, state))
            else:
                lines.append(prefix + render_other(path))
        except Exception:
            continue
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
