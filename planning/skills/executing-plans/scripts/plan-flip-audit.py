#!/usr/bin/env python3
"""plan-flip-audit.py — checkbox flips need evidence.

    plan-flip-audit.py <plan.md> [--since <rev>] [--flip-threshold N]
                       [--vocab-file F] [--require-all-checks] [--json]
                       [--repo DIR]
    plan-flip-audit.py <plan.md> --snapshot [--repo DIR]

Reports nine patterns, each reconstructed from a real session that shipped a
green gate over work that had not happened:

  1. more than N (default 6) boxes becoming `[x]` in one commit, with fewer than
     N task commits in the range behind them — the bulk regex flip
  2. a ticked box whose own text carries what voids it. Two tiers: a STRONG
     phrase voids alone and is `blocking` (no CM4 / soft residual / exit 2 /
     exit 78 / stubbed / mocked / waived / Not done: / shouted BLOCKED); a WEAK
     qualifier (amended / partial / skipped / manual / blocked / exit 1 / ...)
     is `advisory` when two co-occur, or when one stands in an amendment
     parenthetical that discloses no was-value. See void_hit() for why.
  3. a Preflight access/device box ticked in a commit carrying no probe output
  4. a `**Completed:**` line or master-register tick standing over a gate line
     that matches (2), in this file or a linked sub-plan
  5. a `(judgment)` box ticked in a commit with no evaluator/reviewer artefact
  6. a ticked box recording an OWNER decision ("Owner confirms …", "user
     approves …") that carries no quote of the owner's words — `blocking`
  7. an amendment's `was:` value still standing, unannotated, elsewhere in the
     plan — `advisory` (it may be a true historical statement; say which)
  8. a ticked task whose FIRST Test claim, or any claim that names its break
     "(red if …)", has no valid prove-claim.py record (proof/<plan>/<task>/
     claim-K.json, bound to the commit that added it) — `blocking`; a claim
     recorded as a claim deviation, or only self-reported `mutation:` lines —
     `advisory`. Any other claim needs no record. Needs --repo; without it,
     reported NOT RUN.
  9. a ticked task with a requirement clause that has neither a valid
     req-K.json nor a deviation-K.json record — `advisory`, always: requirement
     accounting carries no blocking mandate until it is measured. Needs --repo.

Exit 0 = no findings, 1 = findings, 2 = usage/IO error, 3 = no findings but some
checks could not run (only with --require-all-checks). A crash must never be
readable as "clean", which is why 2 is reserved rather than reusing 1, and why
main() is wrapped so an unexpected exception exits 2 rather than letting
Python's default exit 1 masquerade as "findings". (That handler prints to
stderr and emits no document, so a --json caller sees empty stdout with exit 2 —
check the exit code before parsing.)

COVERAGE IS PART OF THE OUTPUT, NOT A FOOTNOTE. Findings 2, 4, 6 and 7 read the
file on disk. Findings 1, 3 and 5 read git history, and there are ordinary situations
where that history does not exist — a plan living in a vault that is not a git
repository is the normal case for this repo, and a plan file that is untracked
inside a repo that HAS history is the subtler one. An audit that answered "no
findings" in either case would be asserting a clean bill over three checks it
never ran, which is the same act it exists to detect. So every run reports which
checks ran and which did not, the not-run banner goes to stderr where a caller
cannot drop it by reading only stdout, --json carries both lists, and a caller
that must not tolerate partial coverage passes --require-all-checks to get a
distinct exit code instead of a green one.

THE BASELINE, for a plan with no git history. Every plan in this portfolio
lives in a vault that is not a git repository, so for years findings 1, 3 and 5
could never run on a real plan — "exit 3 is the normal case". That is how a
executor ticked all 13 Preflight boxes of a plan in one edit, owner
confirmation included, with nothing able to notice (metabrush-android,
2026-10-02). So `--snapshot`, run once when the plan is loaded, copies the plan
into `<repo>/.claude/plan-baseline/`. Later runs on a plan outside git compare
the file on disk against that copy instead of against a parent commit, and take
their evidence (task commits, probe artefacts, review ledgers) from the
PROJECT repo's commits since the snapshot. Weaker than history mode, and said
so: the copy is one state, not a per-commit series, so evidence anywhere in
the range counts for every flip in it. A second `--snapshot` is refused — a
re-snapshot after ticking would launder every flip since — and a baseline whose
text no longer matches its recorded hash exits 2, never clean. Hand-editing
both is still possible; this raises the cost of a fake, it does not stop one.

HOW A TICK IS DETECTED, and why it is not a diff. An earlier revision paired
removed `[ ]` lines against added `[x]` lines in the commit diff, keyed on exact
text. That missed the canonical fake outright: an executor amending a gate ticks
the box AND appends the amendment in the same edit, which changes the text and
breaks the key. So this version compares STATE, not diffs — the set of ticked
boxes in the file at the commit against the set at its parent. A box that is
ticked now and was not before is a flip, whether its text changed, whether it
was appended already-ticked, and whether or not the diff pairs cleanly. Identity
is a normalized key with the trailing amendment parenthetical stripped, so
ticking-plus-amending stays the same box.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

# The two shapes a done-marker takes in a plan's PROSE. The bare bullet box is
# the common one; `- **Status:** [x]` is the per-task marker every plan this repo
# produces uses. `+`/`1.` bullets are accepted because markdown does.
#
# There is deliberately NO table-cell pattern here. An earlier revision had one,
# justified as "how master registers tick a sub-plan" — which was false: that
# half of finding 4 lives in `register_ticks()`, which does its own confined
# search and never calls `boxes()`. Measured over 601 real plans the table
# pattern matched ZERO lines while feeding ordinary risk/status tables
# ("| supply chain | [x] | N/A |") into the void-tick scan as false positives.
# Dead for its stated purpose, live for the wrong one.
BULLET_BOX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s*\[([ xX])\]\s*(.*)$")
LABELED_BOX = re.compile(
    r"^\s*(?:[-*+]|\d+[.)])\s*(\*\*[^*]+\*\*:?)\s*\[([ xX])\]\s*(.*)$")

# A trailing amendment parenthetical is commentary ABOUT the box, not part of
# its identity — stripping it is what lets "tick it and amend it in one commit"
# still resolve to the same box across the parent/child comparison.
AMEND_TAIL = re.compile(r"\s*\*?\([^()]*\)\*?\s*$")
EMPHASIS = re.compile(r"[*`_]+")

# TWO TIERS, because a single word cannot tell a voided tick from an honest one.
#
# Measured over 188 non-pi-modem plans: a flat vocabulary produced a 39.8% hard
# false-positive rate and lit up 31.4% of all plans. The dominant cause was bare
# `amended` (44% of hits) -- which in this portfolio is a CEREMONY KEYWORD that
# executing-plans § Amending authored ceremony REQUIRES an honest executor to
# write. A detector that fires on the disclosure protocol punishes the behaviour
# it exists to encourage, and under "a finding is a RED gate" it would be
# switched off within a week, after which it catches nothing.
#
# So: a STRONG phrase voids a tick on its own -- it says the work did not
# happen. A WEAK qualifier voids only in company: two of them on one line. That
# keeps `(amended — exit 2; no CM4)` and `(amended — skipped preceding make
# clean)` firing while `(amended at Preflight … was: 2 of 9 tasks)` stays quiet.
VOID_STRONG = [
    r"\bsoft\s+residual\b",
    r"\bnot\s+(fully\s+)?automated\b",
    r"\bno\s+(CM-?4s?|devices?|hardware|boards?|endpoints?|profiles?|MCU)\b",
    r"\bnot\s+(run|executed|reachable|available|attached|present|actuated|done)\b",
    r"\bnever\s+(ran|run|executed|asserted)\b",
    r"\bstill\s+(open|pending|outstanding)\b",
    r"\bwithout\s+(a\s+|the\s+|dual\s+|recoverable\s+)?"
    r"(hardware|devices?|CM-?4s?|boards?|MCU|endpoints?|profiles?)\b",
    # These have no honest sense in an amendment on a ticked gate line. Nothing
    # in § Amending authored ceremony asks an executor to write them, and no
    # honest homonym appears across 601 vault plans. `exit 2` and `exit 78` in
    # particular ARE the fraud in the incident record — the 2026-08-21 master
    # was marked Completed with every HIL box reading `(amended — exit 2)`, and
    # 78 is the code this very skill defines as the only recordable BLOCKED.
    # Bare `exit 1` stays weak: it is the PASS of the `! grep` idiom.
    r"\bexit\s+(code\s+)?(2|78)\b",
    r"\bstub(bed|s)?\b", r"\bmocked\b", r"\bsimulated\b", r"\bwaived\b",
]
# Case-SENSITIVE: the shouted forms are how a plan records a real stop. Lowercase
# "blocked"/"partial"/"skipped" are ordinary words (multitor has a routing enum
# whose values are Tor/Direct/Blocked) and live in the weak tier instead.
VOID_STRONG_CASED = [r"\bBLOCKED\b", r"\bSKIPPED\b", r"\bPARTIAL\b"]

VOID_WEAK = [
    r"\bamended\b",
    # `exit 0` is the passing outcome; so is `exit 1` for the `! grep` idiom
    # these plans use constantly, which is why this is weak and not strong.
    r"\bpartial(ly)?\b", r"\bskipped\b", r"\bdeferred\b", r"\bwaived\b",
    r"\bmanual(ly)?\b", r"\bexit\s+(code\s+)?1\b",
    r"\bresidual\b", r"\bblocked\b", r"\bunreachable\b",
    r"\bN/A\b", r"\bTODO\b",
]

# Spans where the vocabulary is QUOTED rather than ASSERTED. A gate line reading
# ``! rg -n 'soft residual|BLOCKED' Makefile`` is the anti-stub check itself, and
# an earlier revision flagged it — the detector tripping over its own detector.
# Test-runner summaries ("2610 passed, 52 skipped") are the other big class.
QUOTED_SPAN = re.compile(r"`[^`]*`|~~[^~]*~~")
# A TOOL'S OWN NAME IS NEVER A CONFESSION. `\bstub\b` matches inside
# `gate-stub-audit` because a hyphen is a word boundary — so a gate report that
# CITES this audit by name, which a gate report is required to do, was
# flagged as a ticked box confessing a stub. The detector punished compliance
# with its own mandate. Found 2026-08-26 by running this audit over the very plan
# that ships it, after a real gate report was pasted in. Same class as
# coder-plugins BL-085: a mechanical check over plan prose must not key on a word
# the process requires. Masked like a quoted span, before any matching.
TOOL_NAME = re.compile(
    r"\b(?:gate-stub-audit|plan-flip-audit|probe-device|plan-continue|"
    r"plan-progress|hooks-install|statusline-install|plan-status-audit)"
    r"(?:\.(?:sh|py))?\b")
# "gate not blocked", "complete, not partial", "no residual", "not the old stub".
NEGATED = re.compile(r"\b(no|not|never|zero|without|non)\b[^.]{0,30}$", re.I)
NEGATED_HYPHEN = re.compile(r"non-\s*$", re.I)
# "27 skipped", "52 skipped" — a count, not a confession.
COUNTED = re.compile(r"\d+\s*$")
# What § Amending authored ceremony REQUIRES an amendment to carry: the
# was-value, or the rule that authorised it. Its presence is the whole
# difference between a disclosed amendment and a bare claim that something
# changed — and it is what makes a lone qualifier honest rather than suspect.
DISCLOSED = re.compile(r"\bwas:|\bper\s|\bsee\s|§|\bmeasured\b|\bverified\b", re.I)

ACCESS_VOCAB = re.compile(
    r"\baccess\b|\breachable\b|\bdevice\b|\bhardware\b|\bcredential"
    r"|\btoolchain\b|\bserial\b|\bssh\b|\bflash\b|\bon\s+desk\b",
    re.I,
)

# Finding 3's evidence: a probe artefact ADDED OR MODIFIED in that same commit.
# Deliberately anchored to an evidence-ish directory segment or an explicit
# probe/serial filename — an unrelated `security-history.jsonl`, which this
# portfolio commits routinely, must not launder a flip.
PROBE_PATH = re.compile(
    r"(^|/)(evidence|probes?|transcripts?)(/|$)"
    r"|(^|/)[^/]*probe[^/]*\.(txt|log|json|jsonl|out)$",
    re.I,
)

# Finding 5's evidence: a structured evaluator/review ledger line (the shape the
# gate report actually writes) or a review artefact path — not merely the word
# "review" appearing somewhere in a commit message.
REVIEW_REF = re.compile(
    r"^\s*(evaluator|review|reviewer)\s*:\s*\S", re.I | re.M
)
REVIEW_PATH = re.compile(
    r"(^|/)(reviews?|evaluations?)(/|$)|(^|/)[^/]*(review|evaluat)[^/]*\.(md|json|txt)$",
    re.I,
)

COMPLETED = re.compile(r"^\s*\*\*Completed:\*\*", re.I)
JUDGMENT = re.compile(r"\(judgment\)", re.I)
STAGE_GREEN = re.compile(r"^Stage\s+\d+\s+green\b", re.I)
MD_LINK = re.compile(r"\(([^()]+?\.md)\)")
BARE_MD = re.compile(r"([A-Za-z0-9._\-/]+\.md)")

HISTORY_CHECKS = (1, 3, 5)
STATIC_CHECKS = [2, 4, 6, 7]

# Finding 6: a box whose claim IS an owner decision — the box OPENS with it.
# Measured over 775 vault plans, matching the phrase anywhere fired on 44 plans,
# nearly all prose: "until the user confirms restore" (app behaviour), "pending
# owner approval", "by the user's decision (below)". A box whose claim is the
# owner's act states it first. Decision verbs only. "Owner
# runs `sudo apt install …`" or "owner creates the repo" describe HOW a box gets
# satisfied, and the box's own command proves the result — requiring a quote
# there would fire on every Preflight that needs a sudo step, and a detector
# that reds honest plans gets switched off. "Owner confirms the acceptance
# extends to …" has no command behind it: the owner's words are the only
# evidence there can be, so a tick without them is the executor's say-so.
OWNER_DECISION = re.compile(
    r"^(?:\*\*\(judgment\)\*\*\s*|\(judgment\)\s*|the\s+)?"
    r"(owner|user)(?:'s)?\s+"
    r"(confirm(?:s|ed|ation)?|approv(?:es|ed|al)|accept(?:s|ed|ance)?"
    r"|decid(?:es|ed)|decision|choos(?:es)|chose|agree(?:s|d)?"
    r"|sign(?:s|ed)?[\s-]+off|authori[sz](?:es|ed|ation))\b",
    re.I,
)
# The attestation integration.md already demands for a review opt-out, applied
# here: who, optionally when, and the words in quotes —
# `owner, 2026-10-02: "keep"` (the form DEC-MB-013 records owner calls in).
ATTESTED = re.compile(
    r"\b(owner|user)\b[^\"“”\n]{0,30}:\s*[\"“][^\"”\n]{2,}[\"”]",
    re.I,
)

# Finding 7: the was-value of an amendment. Only a BACKTICKED value that looks
# like an identifier — one token, a digit in it (a commit, a version, a serial)
# — is swept. Measured over 775 vault plans, also sweeping paths and commands
# fired on 9 plans, nearly all false: an amended gate command or file path is
# routinely still valid elsewhere ("`config/config.toml`", "tasks 1.1, 1.2").
# A superseded commit or version number standing elsewhere is the real case.
WAS_VALUE = re.compile(r"\bwas:\s*`([^`]+)`", re.I)
DISTINCTIVE = re.compile(r"^[^\s/]*[0-9][^\s/]*$")
# A line that is itself an amendment, or says it is historical, is the
# disclosure — not a survivor.
STALE_EXEMPT = re.compile(r"\bwas:|\bamended\b|\bhistorical(ly)?\b", re.I)

# Finding 8: a task's Test proves something only if it was seen to FAIL when
# the thing it claims is broken. metabrush-android Task 1.2 (2026-10-03) shipped
# a TMPDIR test that passed with TMPDIR unset and with TMPDIR pointing nowhere;
# its commit recorded one `mutation:` line, for the easiest of its four claims.
# So each claim in a ticked task's Test gets a `mutation:` line in the task's
# commit, naming the break that turned it red (or `mutation: none — <why>`,
# which is a disclosure a reader can judge). Claims are counted the way plans in
# this portfolio write them: `<command>` — claim; claim; claim.
TASK_HEAD = re.compile(r"^\s*#{2,5}\s+Task\s+(\d+\.\d+)\b", re.I)
ANY_HEAD = re.compile(r"^\s*#{1,5}\s")
STATUS_TICKED = re.compile(r"^\s*[-*+]\s*\*\*Status:\*\*\s*\[[xX]\]")
TEST_FIELD = re.compile(r"^\s*[-*+]\s*\*\*Test:\*\*\s*(.*)$")
# The tasks a commit SUBJECT names. One reader for the audit and the git ref hook
# (hooks/git-ref-gate.sh), so they cannot disagree about which commit is whose:
# case-insensitive, "Task 2.1", "task-2.1", "Task #2.1", "Tasks 2.1 and 2.2",
# "Task 1.1 + Task 1.2", and ranges within a stage, "Tasks 2.4-2.7".
TASK_LIST = re.compile(
    r"\btasks?\b\s*[:#-]?\s*(\d+\.\d+(?:\s*(?:,|&|\+|/|\band\b|\bto\b|-|\u2013|\u2014)\s*"
    r"(?:tasks?\b\s*[:#-]?\s*)?\d+\.\d+)*)", re.I)
TASK_RANGE_SEP = re.compile(r"^\s*(?:-|\u2013|\u2014|\bto\b)\s*$", re.I)


def subject_tasks(subject):
    """{'2.1', ...}: every task id the subject line names, ranges expanded."""
    out = set()
    for m in TASK_LIST.finditer(subject or ""):
        span = m.group(1)
        ids = list(re.finditer(r"\d+\.\d+", span))
        for i, cur in enumerate(ids):
            out.add(cur.group(0))
            if i == 0:
                continue
            prev = ids[i - 1]
            sep = re.sub(r"(?i)tasks?\b\s*[:#-]?", "", span[prev.end():cur.start()])
            (a_major, a_minor), (b_major, b_minor) = (
                map(int, prev.group(0).split(".")), map(int, cur.group(0).split(".")))
            if TASK_RANGE_SEP.match(sep) and a_major == b_major and a_minor < b_minor <= a_minor + 50:
                out.update(f"{a_major}.{n}" for n in range(a_minor + 1, b_minor))
    return out
MUTATION_LINE = re.compile(r"^\s*mutation\s*:\s*\S", re.I | re.M)

# Finding 9: the task DESCRIPTION is a contract too, not context. metabrush-android
# Task 1.3 (2026-10-03) passed its Test — three .so files in the APK — while two of
# the five requirements in its description were not met: it copied the NDK version
# instead of reading the one the build pins, and its build step did not rebuild
# when the engine changed although the task said "built from source every time".
# The Test could not see either. So the task's commit carries one line per
# requirement clause: `req: <clause> -> <how it was verified>`, or
# `deviation: <clause> -> <what differs and why>` — a disclosed deviation is a
# finding a reader can judge, a silent one is not. Clauses are the `;`- and
# sentence-separated parts of the task's plain bullets, with code spans masked.
REQ_LINE = re.compile(r"^\s*(req|deviation)\s*:\s*\S", re.I | re.M)
FIELD_BULLET = re.compile(r"^\s*[-*+]\s*\*\*[^*]+:\*\*")
PLAIN_BULLET = re.compile(r"^\s*[-*+]\s+(\S.*)$")
CLAUSE_SPLIT = re.compile(r";|\.\s+(?=[A-Z`(*])")


class Bail(Exception):
    """Usage/IO failure — always exit 2, never 1."""


def die(msg):
    raise Bail(msg)


def git(repo, *args):
    """Run git. Returns (stdout, None) on success, (None, reason) on failure.

    A missing binary, a 'dubious ownership' refusal and 'not a repository' are
    materially different situations and get materially different reasons — the
    earlier version collapsed all three into 'not inside a git repository',
    which is false for two of them and would send a reader looking in the wrong
    place. errors='replace' because a plan file may legitimately contain bytes
    that are not UTF-8, and a decode error must not escape as a bare crash.
    """
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True,
            errors="replace",
            # A translated git turns every message-matching branch into a wrong
            # answer; pin the locale rather than parse an unknown language.
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        )
    except FileNotFoundError:
        return None, "git binary not found on PATH"
    except OSError as e:
        return None, f"could not run git: {e}"
    if r.returncode != 0:
        # next(iter(...)): stderr == "\n" is truthy but strips to "", and
        # "".splitlines() is [] -- an IndexError on the error path.
        fallback = f"git {' '.join(args[:2])} exited {r.returncode}"
        return None, next(iter((r.stderr or "").strip().splitlines()), fallback)
    return r.stdout, None


def gout(repo, *args):
    """git() keeping only stdout, or None."""
    out, _ = git(repo, *args)
    return out


# ------------------------------------------------------------------ parsing

def norm_key(body):
    """Identity of a checkbox, stable across ticking-and-amending."""
    b = AMEND_TAIL.sub("", body)
    b = EMPHASIS.sub("", b)
    b = re.sub(r"\s+", " ", b).strip().lower()
    return b[:80]


def boxes(text):
    """Every checkbox in a file's text: (ticked, key, body, line_no, raw)."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        m = LABELED_BOX.match(line)
        if m:
            ticked, body = m.group(2).lower() == "x", f"{m.group(1)} {m.group(3)}"
            out.append((ticked, norm_key(body), body.strip(), i, line))
            continue
        m = BULLET_BOX.match(line)
        if m:
            ticked, body = m.group(1).lower() == "x", m.group(2)
            out.append((ticked, norm_key(body), body.strip(), i, line))
            continue
    return out


def compile_vocab(vocab_file, replace=False):
    """(strong, strong_cased, weak) matchers; --vocab-file EXTENDS the weak tier.

    Extending is the safe default: a user adding a project word must not
    silently disable the other patterns, which is what a wholesale rebind did in
    an earlier revision -- a fail-open reachable by using the feature as
    documented. Extra patterns join the WEAK tier, so a bare project keyword
    still needs a co-signal before it can void a tick.
    """
    strong, cased, weak = list(VOID_STRONG), list(VOID_STRONG_CASED), list(VOID_WEAK)
    if vocab_file:
        pth = Path(vocab_file)
        if not pth.is_file():
            die(f"--vocab-file not found: {pth}")
        extra = [ln.strip() for ln in pth.read_text(errors="replace").splitlines()
                 if ln.strip() and not ln.strip().startswith("#")]
        if not extra:
            die(f"--vocab-file is empty: {pth}")
        if replace:
            strong, cased, weak = extra, [], []
        else:
            weak = weak + extra
    try:
        return (re.compile("|".join(strong), re.I) if strong else None,
                re.compile("|".join(cased)) if cased else None,
                re.compile("|".join(weak), re.I) if weak else None)
    except re.error as e:
        die(f"--vocab-file contains an invalid pattern: {e}")


# ------------------------------------------------------------------- static

def void_hit(raw, vocab):
    """The phrase that voids this tick, or None. `vocab` is (strong, cased, weak).

    Two tiers, because one word cannot separate a voided tick from an honest
    one. A STRONG phrase says outright that the work did not happen and voids on
    its own. A WEAK qualifier voids only with a second signal on the same line --
    another weak term or a strong one.

    Measured on 188 non-pi-modem plans, a flat vocabulary was 39.8% hard false
    positives and lit 31.4% of plans, driven by bare `amended`: the word this
    portfolio's own amendment protocol REQUIRES an honest executor to write.
    `(amended — exit 2; no CM4)` still fires -- three signals. `(amended at
    Preflight … was: 2 of 9 tasks)` no longer does, and neither does multitor's
    `Blocked` routing enum or the `! grep … — exit 1, no hits` idiom whose exit 1
    is a PASS.

    Filters applied before any of it: spans inside backticks or ~~strikethrough~~
    are blanked (a gate line that greps FOR this vocabulary is the anti-stub
    check, not a confession), a negation within 40 characters is skipped, and a
    term preceded by a count is read as a count ("27 skipped").
    """
    strong, cased, weak = vocab
    masked = QUOTED_SPAN.sub(lambda m: " " * len(m.group(0)), raw)
    masked = TOOL_NAME.sub(lambda m: " " * len(m.group(0)), masked)

    def live(m):
        pre = masked[max(0, m.start() - 40):m.start()]
        if NEGATED.search(pre) or NEGATED_HYPHEN.search(pre):
            return False
        return not COUNTED.search(pre)

    for matcher in (strong, cased):
        if matcher:
            for m in matcher.finditer(masked):
                if live(m):
                    return m.group(0), "blocking"
    if weak:
        hits = [m.group(0) for m in weak.finditer(masked) if live(m)]
        # Two independent qualifiers, not the same word twice.
        if len({h.lower() for h in hits}) >= 2:
            return " + ".join(hits[:3]), "advisory"
        # A LONE qualifier must never be silence. It is advisory when it sits in
        # the trailing amendment parenthetical and that parenthetical discloses
        # nothing: `*(amended)*` on a gate line asserts that something changed
        # while withholding the was-value § Amending authored ceremony requires,
        # so it is exactly the shape that rule exists to forbid. The same word in
        # running prose ("under the amended validator") is not an amendment, and
        # the same word WITH its disclosure ("amended at Preflight … was: …") is
        # the protocol being followed. This rewards disclosure rather than
        # punishing the word, which is what the flat vocabulary got wrong.
        if hits:
            tail = AMEND_TAIL.search(masked)
            if tail and any(h in tail.group(0) for h in hits) \
                    and not DISCLOSED.search(tail.group(0)):
                return hits[0] + " (undisclosed amendment)", "advisory"
    return None


def scan_void_ticks(path, text, vocab):
    """Finding 2 — a ticked box whose own line carries what voids it."""
    out = []
    for ticked, _key, body, line, raw in boxes(text):
        hit = void_hit(raw, vocab)
        if ticked and hit:
            phrase, severity = hit
            out.append({
                "finding": 2,
                "severity": severity,
                "rule": ("ticked box states outright that the work did not happen"
                         if severity == "blocking"
                         else "amendment discloses no was-value"
                         if "undisclosed" in phrase
                         else "ticked box carries two qualifiers that may void it"),
                "file": str(path), "line": line, "text": body,
                "matched": phrase,
            })
    return out


def scan_owner_attestation(path, text):
    """Finding 6 — a ticked owner decision with no quote of the owner."""
    out = []
    for ticked, _key, body, line, raw in boxes(text):
        if not ticked:
            continue
        # A decision phrase inside backticks is quoted, not claimed.
        masked = QUOTED_SPAN.sub(lambda m: " " * len(m.group(0)), body)
        m = OWNER_DECISION.search(masked.strip())
        if not m or ATTESTED.search(raw):
            continue
        out.append({
            "finding": 6, "severity": "blocking",
            "rule": "ticked box records an owner decision but quotes no owner "
                    "words (expected: owner, <date>: \"<their words>\")",
            "file": str(path), "line": line, "text": body,
            "matched": m.group(0),
        })
    return out


def scan_stale_was_values(path, text):
    """Finding 7 — an amended value still standing elsewhere in the plan."""
    lines = text.splitlines()
    values = {}
    for i, line in enumerate(lines, 1):
        for m in WAS_VALUE.finditer(line):
            v = m.group(1).strip()
            if len(v) >= 6 and DISTINCTIVE.search(v):
                values.setdefault(v, i)
    out = []
    for v, amended_at in values.items():
        for i, line in enumerate(lines, 1):
            if v in line and not STALE_EXEMPT.search(line):
                out.append({
                    "finding": 7, "severity": "advisory",
                    "rule": f"value amended away at line {amended_at} still "
                            "stands here unannotated — update it, or mark it "
                            "historical",
                    "file": str(path), "line": i, "text": line.strip()[:200],
                    "matched": v,
                })
    return out


def task_blocks(text):
    """Every task block: {id, line (Status line if ticked), test, desc}."""
    out, cur = [], None
    for i, line in enumerate(text.splitlines(), 1):
        m = TASK_HEAD.match(line)
        if m:
            cur = {"id": m.group(1), "line": None, "test": "", "desc": ""}
            out.append(cur)
            continue
        if ANY_HEAD.match(line):
            cur = None
            continue
        if cur is None:
            continue
        if STATUS_TICKED.match(line):
            cur["line"] = i
        t = TEST_FIELD.match(line)
        if t:
            cur["test"] = t.group(1)
        elif not FIELD_BULLET.match(line):
            d = PLAIN_BULLET.match(line)
            if d:
                cur["desc"] += " " + d.group(1)
    return out


def ticked_tasks(text):
    """Ticked tasks in the plan: (task id, Status line number, Test text)."""
    out = task_blocks(text)
    return [(t["id"], t["line"], t["test"]) for t in out if t["line"]]


def _masked(text):
    """`text` with every code span blanked to spaces, so positions still line up."""
    return QUOTED_SPAN.sub(lambda m: " " * len(m.group(0)), text)


# An amendment or superseded note is the plan's HISTORY, written by the amendment
# protocol — never a requirement or a claim. Counted as clauses, a note split on
# its own `;` and `. ` and inflated a task's count (found 2026-10-04: one note in
# Task 1.1 of the verification-by-tool plan read as two extra requirements).
# Only a note that reads as history is stripped — it carries a date, a `was:`
# value or a `by commit` — and it is found on the MASKED text, so a code span is
# never part of one. Otherwise wrapping a requirement in `*(amended: …)*` would
# quietly drop it from the count, and with it the proof it needs.
ANNOTATION = re.compile(r"\s*\*\((?:amended|superseded|historical)\b.*?\)\*", re.S | re.I)
HISTORY_MARK = re.compile(r"\d{4}-\d{2}-\d{2}|\bwas:|\bby commit\b", re.I)


def strip_notes(text):
    """`text` without its history notes (see ANNOTATION)."""
    masked, out, last = _masked(text), [], 0
    for m in ANNOTATION.finditer(masked):
        if HISTORY_MARK.search(m.group(0)):
            out.append(text[last:m.start()])
            last = m.end()
    out.append(text[last:])
    return "".join(out)


def requirement_clauses(desc):
    """The requirement clauses of a task description, as their original text.

    Split where the masked text has a separator, so a `;` or `. ` inside a code
    span never splits; filtered on the text with code spans removed, so a clause
    that is only a code span is not a requirement. prove-claim.py reads clause K
    from here, so the audit and the tool can never number them differently.
    """
    desc = strip_notes(desc)
    if not QUOTED_SPAN.sub("", desc).strip():
        return []
    masked, parts, last = _masked(desc), [], 0
    for m in CLAUSE_SPLIT.finditer(masked):
        parts.append(desc[last:m.start()])
        last = m.end()
    parts.append(desc[last:])
    return [p.strip() for p in parts if len(QUOTED_SPAN.sub("", p).strip()) > 2]


def count_requirements(desc):
    """Requirement clauses in a task description; 0 when it has none."""
    return len(requirement_clauses(desc))


def claim_clauses(test):
    """The claims of a Test field, as their original text.

    The `;`-separated clauses after the field's ` — `; a field with no ` — ` is
    one claim, the whole field. Same masking rule as requirement_clauses.
    """
    test = strip_notes(test)
    masked, sep = _masked(test), " \u2014 "
    if sep not in masked:
        return [test.strip()]
    start = masked.index(sep) + len(sep)
    parts, last = [], start
    for i in range(start, len(masked)):
        if masked[i] == ";":
            parts.append(test[last:i])
            last = i + 1
    parts.append(test[last:])
    out = [p.strip() for p in parts if QUOTED_SPAN.sub("", p).strip()]
    return out or [test.strip()]


def count_claims(test):
    """Claims in a Test field: the `;`-separated clauses after its ` — `."""
    return len(claim_clauses(test))


NAMED_BREAK = re.compile(r"\(red if (.+?)\)\s*$", re.S)


def required_claims(test):
    """The claim numbers a ticked task must prove: its FIRST claim, and every claim
    that names its break "(red if …)". A plan that names a break has said what the
    proof is; an unnamed later claim is context the first claim's test covers."""
    claims = claim_clauses(test)
    return [k for k, c in enumerate(claims, 1)
            if k == 1 or NAMED_BREAK.search(_masked(c))]


def claim_deviation_problems(rec, fingerprint, expect):
    """Problems with a claim deviation record (kind `claim-deviation`, stored at
    claim-K.json), [] when valid. It discloses a claim no repo patch can break —
    its evidence lives outside the repo — so it is reported, never proof."""
    p = []
    if not isinstance(rec, dict) or rec.get("kind") != "claim-deviation":
        return ["not a claim deviation"]
    _kind, task, k, text = expect
    if rec.get("task") != task or rec.get("index") != k:
        p.append(f"records Task {rec.get('task')} #{rec.get('index')}, not Task {task} #{k}")
    if text is not None and rec.get("text") != text:
        p.append("recorded against different wording than the plan now has")
    if not isinstance(rec.get("why"), str) or len(rec["why"].strip()) < 10:
        p.append("a claim deviation without a reason")
    fpr = rec.get("fingerprint")
    if not isinstance(fpr, str) or not re.match(r"^[0-9a-f]{64}$", fpr):
        p.append("no valid fingerprint")
    elif fingerprint and fpr != fingerprint:
        p.append("recorded on a different tree than this one")
    return p


def task_commit_evidence(repo):
    """{task id: [commits naming it, mutation: lines across them]}, or None."""
    log = gout(repo, "log", "--format=%x1e%H%x00%s%x00%b", "HEAD")
    if log is None:
        return None
    ev = {}
    for rec in log.split("\x1e"):
        if "\x00" not in rec:
            continue
        _sha, subj, body = (rec.split("\x00", 2) + [""])[:3]
        muts = len(MUTATION_LINE.findall(body))
        reqs = len(REQ_LINE.findall(body))
        for tid in subject_tasks(subj):
            entry = ev.setdefault(tid, [0, 0, 0])
            entry[0] += 1
            entry[1] += muts
            entry[2] += reqs
    return ev


_PC = None


def _prove_claim():
    """prove-claim.py, loaded once: the record format and its validator live there."""
    global _PC
    if _PC is None:
        spec = importlib.util.spec_from_file_location(
            "prove_claim", Path(__file__).resolve().parent / "prove-claim.py")
        _PC = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_PC)
    return _PC


def proof_records(repo, plan):
    """{task: {(kind, k): problems}} for the plan's proof records at HEAD, or None.

    Read from the COMMITTED tree and validated against the fingerprint of the
    commit that last wrote each record: proof is bound to the code committed with
    it, so a record that does not match its own commit was proven on some other
    tree. `problems` is [] for a valid record.
    """
    pc = _prove_claim()
    stem = Path(plan).stem
    try:
        blocks = {t["id"]: t for t in task_blocks(Path(plan).read_text(errors="replace"))}
    except OSError:
        blocks = {}

    def clause(task, kind, k):
        """The plan's current wording of the clause a record proves, or None."""
        t = blocks.get(task)
        if t is None:
            return None
        items = claim_clauses(t["test"]) if kind == "claim" else requirement_clauses(t["desc"])
        return items[k - 1] if 1 <= k <= len(items) else None

    listing = gout(repo, "ls-tree", "-r", "--name-only", "HEAD", "--",
                   f"{pc.PROOF_DIR}/{stem}/")
    if listing is None:
        return None
    pat = re.compile(rf"{pc.PROOF_DIR}/{re.escape(stem)}/(\d+\.\d+)/"
                     r"(claim|req|deviation)-(\d+)\.json$")
    out, fps = {}, {}
    for rel in listing.split():
        m = pat.match(rel)
        if not m:
            continue
        raw = gout(repo, "show", f"HEAD:{rel}")
        try:
            rec = json.loads(raw) if raw is not None else {"_unreadable": "git show failed"}
        except ValueError:
            rec = {"_unreadable": "not JSON"}
        sha = (gout(repo, "log", "-1", "--format=%H", "--", rel) or "").strip()
        if sha and sha not in fps:
            try:
                fps[sha] = pc.commit_fingerprint(repo, sha)
            except Exception:  # noqa: BLE001 — an unreadable commit is a problem, not a crash
                fps[sha] = None
        kind, task, k = m.group(2), m.group(1), int(m.group(3))
        text = clause(task, kind, k)
        if not fps.get(sha):
            problems = ["its commit is unreadable"]
        elif text is None:
            problems = [f"the plan has no {kind} {k} in Task {task}"]
        elif kind == "claim" and isinstance(rec, dict) and rec.get("kind") == "claim-deviation":
            problems = claim_deviation_problems(rec, fps[sha], (kind, task, k, text))
            if not problems:
                # Disclosed, not proven: the claim stays open, finding 8 names it.
                out.setdefault(task, {})[("claim-deviation", k)] = rec["why"].strip()
                problems = ["recorded as a claim deviation"]
        else:
            try:
                problems = pc.validate(rec, fps[sha], (kind, task, k, text), allow_legacy=True)
            except Exception as e:  # noqa: BLE001 — a record that crashes is not valid
                problems = [f"malformed record ({e.__class__.__name__})"]
            if not problems and pc.is_legacy(rec):
                added = first_added(repo, rel)
                if added is None or added >= datetime.datetime.fromisoformat(LEGACY_CUTOFF):
                    problems = ["a schema-1 req check added after the schema-2 cutover (e0a8cdb) "
                                "— never shown able to fail"]
            if kind == "req" and isinstance(rec, dict) and "covered_by_claim" in rec:
                out.setdefault(task, {})[("cites", k)] = rec["covered_by_claim"]
            if not problems and pc.is_legacy(rec):
                # A schema-1 req check: seen to pass, never to fail. Counted as met so
                # history is not re-litigated, and reported (finding 9, advisory).
                out.setdefault(task, {})[("legacy", k)] = True
        out.setdefault(m.group(1), {})[(m.group(2), int(m.group(3)))] = problems
    return out


def task_numbers(ids):
    """{'1.1', ...} from task ids, whether bare ('1.1') or whole 'Task 1.1' strings."""
    return {m.group(0) for i in ids for m in [re.search(r"\d+\.\d+", str(i))] if m}


# Schema 2 (a req check proven by a break) arrived in engineering-skills e0a8cdb. A schema-1 req
# check is legacy only when the commit that first added it is older than that;
# one added later is what a hand-written record would look like.
LEGACY_CUTOFF = "2026-10-04T10:07:25+00:00"


def first_added(repo, rel):
    """Commit date (aware datetime) of the commit that first added `rel`, or None."""
    out = gout(repo, "log", "--diff-filter=A", "--format=%cI", "--", rel)
    lines = (out or "").split()
    try:
        return datetime.datetime.fromisoformat(lines[-1]) if lines else None
    except ValueError:
        return None


def proven_tasks(repo, plan):
    """Task ids with at least one valid claim record at HEAD — proof the tool watched.

    Finding 1 credits a task commit once per such task: a commit that carries
    Tasks 1.1 and 1.2 with records for both did the work of two. A subject that
    merely NAMES six tasks still counts once (C4b), because naming costs nothing
    and a valid record cannot be written without the tool watching a real run.
    """
    try:
        recs = proof_records(repo, plan) or {}
    except Exception:  # noqa: BLE001 — no credit is the safe answer
        return set()
    try:
        blocks = {b["id"]: b for b in task_blocks(Path(plan).read_text(errors="replace"))}
    except OSError:
        return set()
    # EVERY required claim of the task proven, not one of them: one record would
    # otherwise buy a batched task the same credit as a proven one. A claim
    # deviation is disclosed, not proven, and earns no credit.
    return {t for t, got in recs.items() if t in blocks and required_claims(blocks[t]["test"])
            and all(got.get(("claim", k)) == [] for k in required_claims(blocks[t]["test"]))}


def stray_proof(repo):
    """Committed files under proof/ that are not record paths — proof/ is excluded from
    every fingerprint, so anything there rides along unbound."""
    pc = _prove_claim()
    listing = gout(repo, "ls-tree", "-r", "-z", "--name-only", "HEAD", "--", pc.PROOF_DIR)
    if not listing:
        return []
    return [p for p in listing.split("\0") if p and not pc.RECORD_PATH.match(p)]


def scan_task_mutations(path, text, repo):
    """Finding 8 — a ticked task whose Test claims are not proven.

    A claim is proven by a prove-claim.py record: the tool watched the test pass,
    fail under the break, and the tree come back. `mutation:` lines in commit
    bodies are the retired, self-reported form — an executor wrote false ones —
    so a task carrying only those is "legacy, unverified" (advisory): never
    clean, never blocking, and a plan executed before the tool stays visible
    without being re-run.
    """
    ev, proofs = task_commit_evidence(repo), proof_records(repo, path)
    if ev is None or proofs is None:
        return None
    out = []
    stray = stray_proof(repo)
    if stray:
        out.append({"finding": 8, "severity": "blocking", "file": str(path), "line": None,
                    "text": "proof/",
                    "rule": f"{len(stray)} file(s) under proof/ are not proof records — proof/ is "
                            f"outside every fingerprint, so nothing else may live there: "
                            f"{', '.join(stray[:5])}"})
    for tid, line, test in ticked_tasks(text):
        required = required_claims(test)
        n = len(required)
        got = proofs.get(tid, {})
        commits, muts = ev.get(tid, [0, 0, 0])[:2]
        unproven = [k for k in required if got.get(("claim", k), ["no record"])]
        devs = [k for k in unproven if ("claim-deviation", k) in got]
        unproven = [k for k in unproven if k not in devs]
        base = {"finding": 8, "file": str(path), "line": line, "text": f"Task {tid}"}
        if devs:
            out.append({**base, "severity": "advisory",
                        "rule": f"Task {tid}: claim(s) {devs} recorded as deviations, not proven — "
                                + "; ".join(f"claim {k}: {got[('claim-deviation', k)]}"
                                            for k in devs[:4])})
        if not unproven:
            continue
        if commits == 0 and not got:
            out.append({**base, "severity": "advisory",
                        "rule": f"ticked task has no commit naming 'Task {tid}' in "
                                f"{repo.name} — per-task commits are mandatory"})
        elif not got and muts:
            out.append({**base, "severity": "advisory",
                        "rule": f"Task {tid}: legacy, unverified — {muts} self-reported "
                                "`mutation:` line(s) and no proof record; nothing shows "
                                "its test can fail"})
        else:
            why = "; ".join(f"claim {k}: {(got.get(('claim', k)) or ['no record'])[0]}"
                            for k in unproven[:4])
            out.append({**base, "severity": "blocking",
                        "rule": f"Task {tid}: {len(unproven)} of {n} required claim(s) have no "
                                f"valid proof record — {why}"})
    return out


def scan_task_requirements(path, text, repo):
    """Finding 9 — a ticked task whose description's requirements are not shown met.

    Each requirement clause needs a valid `req-K.json` (a passing check, or a
    proven claim covering it) or a `deviation-K.json` (reported, advisory). A task
    with no commit is finding 8's to report. Legacy `req:` lines alone: advisory.
    """
    ev, proofs = task_commit_evidence(repo), proof_records(repo, path)
    if ev is None or proofs is None:
        return None
    out = []
    for t in task_blocks(text):
        if not t["line"]:
            continue
        n = count_requirements(t["desc"])
        got = proofs.get(t["id"], {})
        commits, _muts, reqs = ev.get(t["id"], [0, 0, 0])
        if n == 0 or (commits == 0 and not got):
            continue
        open_, devs, legacy = [], [], []
        n_claims = count_claims(t["test"])
        for k in range(1, n + 1):
            req, dev = got.get(("req", k)), got.get(("deviation", k))
            cites = got.get(("cites", k))
            if req == [] and cites is not None and (
                    not isinstance(cites, int) or not 1 <= cites <= n_claims
                    or got.get(("claim", cites)) != []):
                # A req "covered by claim J" is only as good as claim J's proof.
                req = [f"cites claim {cites}, which is missing or not a valid proof"]
            if req == []:
                if got.get(("legacy", k)):
                    legacy.append(k)
                continue
            if dev == []:
                devs.append(k)
                continue
            open_.append((k, (req or dev or ["no record"])[0]))
        base = {"finding": 9, "file": str(path), "line": t["line"], "text": f"Task {t['id']}"}
        if open_ and not got and reqs:
            out.append({**base, "severity": "advisory",
                        "rule": f"Task {t['id']}: legacy, unverified — {reqs} self-reported "
                                "`req:`/`deviation:` line(s) and no proof record"})
        elif open_:
            # Advisory, never blocking: no blocking mandate until measured.
            why = "; ".join(f"requirement {k}: {p}" for k, p in open_[:4])
            out.append({**base, "severity": "advisory",
                        "rule": f"Task {t['id']}: {len(open_)} of {n} requirement(s) not "
                                f"shown met — {why}"})
        elif devs:
            out.append({**base, "severity": "advisory",
                        "rule": f"Task {t['id']}: requirement(s) {devs} recorded as "
                                "deviations — name each in the gate report"})
        if not open_ and legacy:
            out.append({**base, "severity": "advisory",
                        "rule": f"Task {t['id']}: requirement(s) {legacy} checked by legacy "
                                "schema-1 records — the check was seen to pass, never to fail"})
    return out


def linked_plans(path, text):
    """Sub-plans referenced from this plan, confined to its own subtree."""
    root, found, seen = path.resolve().parent, [], set()
    for line in text.splitlines():
        for m in list(MD_LINK.finditer(line)) + list(BARE_MD.finditer(line)):
            try:
                cand = (root / m.group(1)).resolve()
            except (OSError, ValueError):
                continue
            # Containment: a plan may link its siblings, never `../elsewhere`.
            if root not in cand.parents and cand.parent != root:
                continue
            if cand == path.resolve() or cand in seen or not cand.is_file():
                continue
            seen.add(cand)
            found.append(cand)
    return found


def register_ticks(text):
    """Ticks inside a `## Sub-plans` register."""
    out, in_reg = [], False
    for i, line in enumerate(text.splitlines(), 1):
        if re.match(r"^\s*#{1,4}\s", line):
            in_reg = bool(re.match(r"^\s*#{1,4}\s+Sub-plans\b", line, re.I))
            continue
        if in_reg and re.search(r"\[[xX]\]", line):
            out.append((i, line.strip()))
    return out


def scan_completed_over_void(path, text, vocab, own_dirty):
    """Finding 4 — a done-marker standing over a self-voiding gate line."""
    dirty = list(own_dirty)
    for sub in linked_plans(path, text):
        try:
            dirty += scan_void_ticks(sub, sub.read_text(errors="replace"), vocab)
        except OSError:
            continue
    if not dirty:
        return []

    sev = "blocking" if any(d.get("severity") == "blocking" for d in dirty) else "advisory"
    # Cite the blocking entries FIRST: a reader told "blocking" and handed four
    # advisory citations has been pointed away from the evidence.
    ordered = ([d for d in dirty if d.get("severity") == "blocking"]
               + [d for d in dirty if d.get("severity") != "blocking"])
    ev = "; ".join(f"{Path(d['file']).name}:{d['line']}" for d in ordered[:4])
    if len(ordered) > 4:
        ev += f" (+{len(ordered) - 4} more)"

    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if COMPLETED.match(line):
            out.append({
                "finding": 4, "severity": sev,
                "rule": "**Completed:** stands over a gate line that voids itself",
                "file": str(path), "line": i, "text": line.strip(), "evidence": ev,
            })
    for i, line in register_ticks(text):
        out.append({
            "finding": 4, "severity": sev,
            "rule": "master-register tick stands over a gate line that voids itself",
            "file": str(path), "line": i, "text": line, "evidence": ev,
        })
    return out


# ------------------------------------------------------------------ history

def file_at(repo, rev, rel):
    """File text at a rev, '' when genuinely absent there, None when git failed.

    Existence is decided by `git cat-file -e`'s EXIT STATUS, not by matching
    English in git's stderr. The string-matching version had a catch-all on the
    substring "path", so a repo path merely containing that word turned an
    unrelated git failure into "file absent" -- which this function reports as
    "" and the caller reads as an empty, clean file.
    """
    if gout(repo, "cat-file", "-e", f"{rev}:{rel}") is None:
        # Distinguish "the rev itself is unreachable" (a real failure) from
        # "the rev is fine, the path is not in it" (genuinely absent).
        if gout(repo, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}") is None:
            return None
        return ""
    out, _err = git(repo, "show", f"{rev}:{rel}")
    return out


def touched_paths(repo, sha):
    """Added/modified paths at a commit, plus its raw --name-status rows."""
    rows = [r for r in (gout(repo, "show", "--name-status", "-M", "--format=", sha)
                        or "").split("\n") if r.strip()]
    am = [r.split("\t", 1)[1] for r in rows
          if "\t" in r and r.split("\t", 1)[0][:1] in ("A", "M")]
    return am, rows


def rename_source(rows, rel):
    """The pre-rename path of `rel` at this commit, or None.

    Without this, `git mv` fabricates a full bulk-flip finding: the parent
    lookup uses the CURRENT path, finds nothing there, and every already-ticked
    box reads as newly ticked. Under "a finding is a RED gate" that turns an
    ordinary plan-file reorganisation into a failed gate.
    """
    for row in rows:
        parts = row.split("\t")
        if parts and parts[0].startswith("R") and len(parts) == 3 and parts[2] == rel:
            return parts[1]
    return None


def newly_ticked(repo, sha, rel, rows=None):
    """Boxes ticked at `sha` that were not ticked at its parent.

    State comparison, not diff pairing — see the module docstring. Returns
    (entries, error) where entries are (key, body, line) and a non-None error
    means this commit could not be examined and the caller must NOT treat it as
    clean.
    """
    after = file_at(repo, sha, rel)
    if after is None:
        return None, f"could not read the plan at {sha[:8]}"
    parents = gout(repo, "rev-list", "--parents", "-n", "1", sha)
    before = ""
    if parents and len(parents.split()) > 1:
        # Follow a rename so the parent lookup compares like with like.
        prev_rel = rename_source(rows or [], rel) or rel
        before = file_at(repo, f"{sha}^", prev_rel)
        if before is None:
            return None, f"could not read the plan at {sha[:8]}^"
    return tick_delta(before, after), None


def tick_delta(before, after):
    """Boxes ticked in `after` that were not ticked in `before`: (key, body, line).

    Counter, not set: 21 gate boxes reading the same text are 21 boxes. Set
    membership would collapse them to one and hand the bulk-flip rule a count
    of 1, which is a bypass you get for free by writing repetitive gates.
    """
    prev = Counter(k for t, k, _b, _l, _r in boxes(before) if t)
    seen, res = Counter(), []
    for t, k, b, ln, _r in boxes(after):
        if not t:
            continue
        seen[k] += 1
        if seen[k] > prev[k]:
            res.append((k, b, ln))
    return res


def preflight_keys(text):
    out, inside = set(), False
    for line in text.splitlines():
        if re.match(r"^\s*#{1,4}\s", line):
            inside = bool(re.match(r"^\s*#{1,4}\s+Preflight\b", line, re.I))
            continue
        if inside:
            for _t, k, _b, _l, _r in boxes(line):
                out.add(k)
    return out


def history_findings(repo, rel, path, text, since, threshold):
    """Findings 1, 3, 5. Returns (findings, errors)."""
    # --follow so a renamed plan keeps its history rather than looking new.
    shas_out = gout(repo, "log", "--format=%H", "--reverse", "--follow",
                    f"{since}..HEAD", "--", rel)
    if shas_out is None:
        return [], ["could not list commits touching the plan"], 0
    shas = shas_out.split()

    # C4: count COMMITS whose subject matches, not regex occurrences -- one
    # subject reading "Task 1.1 Task 1.2 ... Task 1.6" is one commit. And a task
    # commit must contain WORK: six `git commit --allow-empty -m "Task 1.N"`,
    # or six commits touching only the plan file, otherwise buy a free pass
    # through the bulk-flip rule for the price of six empty commits.
    subj_out = gout(repo, "log", "--format=%H%x00%s", f"{since}..HEAD")
    task_ids, task_commits = set(), 0
    if subj_out:
        for row in subj_out.split("\n"):
            if "\x00" not in row:
                continue
            csha, subj = row.split("\x00", 1)
            ids = sorted(subject_tasks(subj))
            if not ids:
                continue
            am, _rows = touched_paths(repo, csha)
            if not any(pth != rel for pth in am):
                continue
            task_commits += 1
            task_ids.update(i if isinstance(i, str) else i[0] for i in ids)
    # Distinct task identifiers, so six commits all titled "Task 1.1" are one.
    task_commits = min(task_commits, len(task_ids)) if task_ids else task_commits
    task_commits = max(task_commits, len(task_numbers(task_ids) & proven_tasks(repo, path)))

    pre = preflight_keys(text)
    out, errors, total_flips = [], [], 0

    for sha in shas:
        touched, rows = touched_paths(repo, sha)
        entries, err = newly_ticked(repo, sha, rel, rows)
        if err:
            errors.append(err)
            continue
        if not entries:
            continue
        total_flips += len(entries)
        short = sha[:8]
        msg = gout(repo, "log", "-1", "--format=%s%n%b", sha) or ""

        if len(entries) > threshold and task_commits < threshold:
            out.append({
                "finding": 1, "severity": "blocking",
                "rule": (f"{len(entries)} boxes became [x] in one commit with only "
                         f"{task_commits} task commit(s) in the range"),
                "file": str(path), "line": None, "commit": short,
                "text": msg.splitlines()[0] if msg else "",
                "evidence": f"threshold {threshold}",
            })

        if not any(PROBE_PATH.search(p) for p in touched):
            for key, body, line in entries:
                if key in pre or ACCESS_VOCAB.search(body):
                    out.append({
                        "finding": 3, "severity": "blocking",
                        "rule": "access/device box ticked with no probe output "
                                "in the same commit",
                        "file": str(path), "line": line, "commit": short,
                        "text": body,
                        "evidence": f"commit touched: {', '.join(touched[:5]) or '(none)'}",
                    })

        if not REVIEW_REF.search(msg) and not any(REVIEW_PATH.search(p)
                                                  for p in touched):
            for _key, body, line in entries:
                if JUDGMENT.search(body):
                    out.append({
                        "finding": 5, "severity": "blocking",
                        "rule": "(judgment) box ticked with no evaluator or "
                                "reviewer artefact in the commit",
                        "file": str(path), "line": line, "commit": short,
                        "text": body,
                        "evidence": f"subject: {msg.splitlines()[0] if msg else ''}",
                    })

    # C4 (split-the-flip): the same 21 boxes spread over four commits of six
    # defeats every per-commit threshold. Judge the range in aggregate too.
    if (total_flips > threshold and task_commits < threshold
            and not any(f["finding"] == 1 for f in out)):
        out.append({
            "finding": 1, "severity": "blocking",
            "rule": (f"{total_flips} boxes became [x] across {len(shas)} commits "
                     f"in the range with only {task_commits} task commit(s)"),
            "file": str(path), "line": None, "commit": f"{since[:8]}..HEAD",
            "text": "aggregate over the range",
            "evidence": f"threshold {threshold}",
        })
    return out, errors, len(shas)


# ----------------------------------------------------------------- baseline

def baseline_path(root, plan):
    """Where the snapshot of `plan` lives: one file per plan, keyed by its path."""
    key = hashlib.sha256(str(plan.resolve()).encode()).hexdigest()[:16]
    return root / ".claude" / "plan-baseline" / f"{key}.json"


def project_root(args):
    root = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    if not root.is_dir():
        die(f"--repo is not a directory: {root}")
    return root


def take_snapshot(args):
    """--snapshot: record the plan as loaded, before execution ticks anything."""
    path = Path(args.plan)
    if not path.is_file():
        die(f"plan file not found: {path}")
    root = project_root(args)
    bp = baseline_path(root, path)
    if bp.exists():
        # Refusing is the guard. A baseline re-taken after ticking makes every
        # flip before it invisible, which is the whole fraud this file detects.
        die(f"baseline already exists: {bp}. A second snapshot would launder "
            "every flip made since the first. Delete it by hand only when "
            "starting a NEW execution of this plan.")
    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        die(f"cannot read {path}: {e}")
    head = gout(root, "rev-parse", "--verify", "--quiet", "HEAD")
    doc = {
        "plan": str(path.resolve()),
        "captured_at": datetime.datetime.now(datetime.timezone.utc)
                       .isoformat(timespec="seconds"),
        "repo_head": head.strip() if head else None,
        "ticked_at_capture": sum(1 for t, *_ in boxes(text) if t),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "text": text,
    }
    try:
        bp.parent.mkdir(parents=True, exist_ok=True)
        bp.write_text(json.dumps(doc, indent=1))
    except OSError as e:
        die(f"cannot write baseline {bp}: {e}")
    print(f"plan-flip-audit: baseline written {bp}")
    print(f"  {doc['ticked_at_capture']} box(es) already ticked at capture; "
          f"repo HEAD {doc['repo_head'][:8] if doc['repo_head'] else '(no commits yet)'}")
    return 0


def load_baseline(bp, path):
    """The baseline doc. A baseline that exists but cannot be trusted is exit 2."""
    try:
        doc = json.loads(bp.read_text(errors="replace"))
        text = doc["text"]
        recorded = doc["sha256"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        die(f"baseline {bp} is unreadable: {e}")
    if hashlib.sha256(text.encode()).hexdigest() != recorded:
        die(f"baseline {bp} does not match its own hash — it was edited after "
            "capture, so it is not evidence of anything")
    if doc.get("plan") != str(path.resolve()):
        die(f"baseline {bp} records a different plan: {doc.get('plan')}")
    return doc


def baseline_findings(root, path, text, base, threshold):
    """Findings 1, 3, 5 against the baseline. Returns (findings, errors, n).

    Evidence comes from the PROJECT repo's commits since the snapshot's HEAD.
    No repo, or no commits, means no evidence — not a pass.
    """
    flips = tick_delta(base["text"], text)
    since = base.get("repo_head")
    shas = []
    if gout(root, "rev-parse", "--verify", "--quiet", "HEAD"):
        rng = f"{since}..HEAD" if since else "HEAD"
        out, err = git(root, "rev-list", rng)
        if out is None:
            return [], [f"cannot list commits {rng} in {root}: {err}"], 0
        shas = out.split()

    task_ids, task_commits = set(), 0
    probed = reviewed = False
    for sha in shas:
        msg = gout(root, "log", "-1", "--format=%s%n%b", sha) or ""
        am, _rows = touched_paths(root, sha)
        ids = sorted(subject_tasks(msg.splitlines()[0] if msg else ""))
        if ids and am:
            task_commits += 1
            task_ids.update(ids)
        if any(PROBE_PATH.search(p) for p in am):
            probed = True
        if REVIEW_REF.search(msg) or any(REVIEW_PATH.search(p) for p in am):
            reviewed = True
    task_commits = min(task_commits, len(task_ids)) if task_ids else task_commits
    task_commits = max(task_commits, len(task_numbers(task_ids) & proven_tasks(root, path)))

    out, where = [], "baseline..HEAD"
    if len(flips) > threshold and task_commits < threshold:
        out.append({
            "finding": 1, "severity": "blocking",
            "rule": (f"{len(flips)} boxes became [x] since the baseline with "
                     f"only {task_commits} task commit(s) in {root.name}"),
            "file": str(path), "line": None, "commit": where,
            "text": f"baseline captured {base.get('captured_at')}",
            "evidence": f"threshold {threshold}",
        })
    pre = preflight_keys(text)
    if not probed:
        for key, body, line in flips:
            if key in pre or ACCESS_VOCAB.search(body):
                out.append({
                    "finding": 3, "severity": "blocking",
                    "rule": "access/device box ticked since the baseline with no "
                            "probe output committed in the project repo",
                    "file": str(path), "line": line, "commit": where,
                    "text": body,
                    "evidence": f"{len(shas)} commit(s) since the baseline, none "
                                "adding a probe artefact",
                })
    if not reviewed:
        for _key, body, line in flips:
            if JUDGMENT.search(body):
                out.append({
                    "finding": 5, "severity": "blocking",
                    "rule": "(judgment) box ticked since the baseline with no "
                            "evaluator or reviewer artefact in the project repo",
                    "file": str(path), "line": line, "commit": where,
                    "text": body,
                    "evidence": f"{len(shas)} commit(s) since the baseline",
                })
    return out, [], len(shas)


def resolve_since(repo, rel, explicit):
    if explicit:
        if gout(repo, "rev-parse", "--verify", "--quiet",
                f"{explicit}^{{commit}}") is None:
            return None, f"--since {explicit!r} does not resolve to a commit"
        return explicit, f"--since {explicit}"
    # The stage's first commit == the child of the previous "Stage N green".
    # The whole log rather than a fixed window: an earlier `-n 200` cap silently
    # changed the answer on any repo with more commits than the cap since that
    # boundary, which is a wrong result dressed as a default.
    log = gout(repo, "log", "--format=%H%x00%s", "HEAD")
    if log:
        rows = [r for r in log.split("\n") if "\x00" in r]
        for row in rows[1:]:
            sha, subj = row.split("\x00", 1)
            if STAGE_GREEN.match(subj.strip()):
                return sha, f"default: previous stage boundary {sha[:8]} ({subj.strip()})"
    first = (gout(repo, "log", "--format=%H", "--reverse", "--", rel) or "").split()
    if first:
        return first[0], f"default: first commit touching the plan ({first[0][:8]})"
    return None, "no commit in this repository touches the plan file"


# --------------------------------------------------------------------- main

def build(args):
    path = Path(args.plan)
    if not path.is_file():
        die(f"plan file not found: {path}")
    if args.vocab_replace and not args.vocab_file:
        die("--vocab-replace requires --vocab-file (alone it is a silent no-op)")
    if args.flip_threshold < 1:
        die("--flip-threshold must be >= 1 "
            "(0 would silently disable the bulk-flip check)")
    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        die(f"cannot read {path}: {e}")

    vocab = compile_vocab(args.vocab_file, args.vocab_replace)
    coverage = {}
    own_dirty = scan_void_ticks(path, text, vocab)
    findings = list(own_dirty)
    findings += scan_completed_over_void(path, text, vocab, own_dirty)
    findings += scan_owner_attestation(path, text)
    findings += scan_stale_was_values(path, text)
    checks_run, not_run = list(STATIC_CHECKS), []

    def skip(reason):
        return [{"finding": n, "reason": reason} for n in HISTORY_CHECKS]

    def from_baseline(no_history):
        """No git history for the plan: fall back to its --snapshot baseline."""
        nonlocal checks_run
        root = project_root(args)
        bp = baseline_path(root, path)
        if not bp.is_file():
            return skip(f"{no_history}; no baseline at {bp} — run "
                        "`plan-flip-audit.py <plan> --snapshot` when the plan "
                        "is loaded, before anything is ticked")
        base = load_baseline(bp, path)
        hf, errors, examined = baseline_findings(
            root, path, text, base, args.flip_threshold)
        if errors:
            return [{"finding": n, "reason": "; ".join(errors[:3])}
                    for n in HISTORY_CHECKS]
        findings.extend(hf)
        coverage["since_note"] = (
            f"baseline {bp.name} captured {base.get('captured_at')} with "
            f"{base.get('ticked_at_capture', '?')} box(es) already ticked")
        coverage["commits_examined"] = examined
        coverage["baseline"] = str(bp)
        checks_run = sorted(set(checks_run) | set(HISTORY_CHECKS))
        return []

    top, err = git(path.resolve().parent, "rev-parse", "--show-toplevel")
    if top is None:
        not_run = from_baseline(f"{path.parent}: {err}")
    else:
        repo = Path(top.strip())
        try:
            rel = str(path.resolve().relative_to(repo))
        except ValueError:
            rel = str(path.resolve())
        # C2: a plan that is untracked has no history, however much the
        # REPOSITORY has. Without this the tool reported all five checks run
        # over zero commits and exited 0 — a clean bill it never earned.
        tracked = gout(repo, "ls-files", "--error-unmatch", "--", rel) is not None
        if not tracked:
            not_run = from_baseline(f"{path.name} is not tracked in {repo}")
        else:
            since, note = resolve_since(repo, rel, args.since)
            if since is None:
                not_run = skip(note)
            else:
                hf, errors, examined = history_findings(
                    repo, rel, path, text, since, args.flip_threshold)
                findings += hf
                coverage["since"] = since
                coverage["since_note"] = note
                coverage["commits_examined"] = examined
                if errors:
                    not_run = [{"finding": n, "reason": "; ".join(errors[:3])}
                               for n in HISTORY_CHECKS]
                elif examined == 0:
                    # A range with no commits touching the plan examined nothing.
                    # Reporting 5/5 there is the module docstring's own failure
                    # mode: a clean bill over checks that never ran.
                    not_run = skip(f"no commit in {note} touches {path.name} — "
                                   "history-based checks examined nothing")
                else:
                    checks_run = sorted(set(STATIC_CHECKS) | set(HISTORY_CHECKS))

    # Finding 8 reads the PROJECT repo, where the task commits are. Only an
    # explicit --repo names it: a cwd guess could read some other repo's
    # history and report a clean bill for this plan.
    if args.repo:
        root = project_root(args)
        top8 = gout(root, "rev-parse", "--show-toplevel")
        has_head = top8 and gout(root, "rev-parse", "--verify", "--quiet", "HEAD")
        f8 = scan_task_mutations(path, text, Path(top8.strip())) if has_head else None
        f9 = scan_task_requirements(path, text, Path(top8.strip())) if has_head else None
        for n, fs in ((8, f8), (9, f9)):
            if fs is None:
                not_run.append({"finding": n, "reason": f"{root} is not a git repository "
                                f"with commits — finding {n} reads the task commits there"})
            else:
                findings.extend(fs)
                checks_run = sorted(set(checks_run) | {n})
    else:
        for n in (8, 9):
            not_run.append({"finding": n, "reason": f"no --repo: finding {n} reads the task "
                            "commits in the project repo; pass --repo <project root>"})

    findings.sort(key=lambda f: (f["finding"], f.get("line") or 0))
    doc = {
        "plan": str(path),
        "findings": findings,
        "checks_run": checks_run,
        "checks_not_run": not_run,
    }
    doc.update(coverage)
    return doc


def report(doc, args):
    findings, not_run = doc["findings"], doc["checks_not_run"]
    if args.json:
        print(json.dumps(doc, indent=2))
    else:
        if findings:
            print(f"plan-flip-audit: {len(findings)} finding(s) in {doc['plan']}")
            for f in findings:
                loc = f"{f['file']}:{f['line']}" if f.get("line") else \
                      f"{f['file']}:{f.get('commit', '?')}"
                print(f"  [finding {f['finding']} · {f.get('severity','blocking')}] {loc}")
                print(f"      {f['rule']}")
                print(f"      {f['text']}")
                if f.get("evidence"):
                    print(f"      evidence: {f['evidence']}")
        else:
            print(f"plan-flip-audit: no findings in {doc['plan']}")
        print(f"  checks run: {', '.join(str(c) for c in doc['checks_run'])}")
        if doc.get("baseline"):
            print(f"  range: {doc['since_note']} — "
                  f"{doc.get('commits_examined', 0)} project commit(s) since")
        elif doc.get("since_note"):
            print(f"  range: {doc['since_note']} — "
                  f"{doc.get('commits_examined', 0)} commit(s) touching the plan")

    if not_run:
        ns = ", ".join(str(c["finding"]) for c in not_run)
        print(f"plan-flip-audit: NOT RUN — findings {ns}: {not_run[0]['reason']}",
              file=sys.stderr)
        print("plan-flip-audit: this run checked only the file on disk; "
              "it is not a clean bill for the checks above.", file=sys.stderr)

    if any(f.get("severity") == "blocking" for f in findings):
        return 1
    if findings:
        # Advisory only: real findings that need naming in the gate report, but
        # not a RED gate. A caller gating on $? could not tell them apart while
        # both returned 1, which made the severity split unusable by the very
        # invocation the skill mandates.
        return 4
    if not_run and args.require_all_checks:
        return 3
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("plan")
    ap.add_argument("--since")
    ap.add_argument("--flip-threshold", type=int, default=6)
    ap.add_argument("--vocab-file",
                    help="file of extra regex patterns, one per line; EXTENDS the "
                         "built-in vocabulary unless --vocab-replace is given")
    ap.add_argument("--vocab-replace", action="store_true",
                    help="use --vocab-file INSTEAD of the built-in vocabulary "
                         "(disables all built-in patterns)")
    ap.add_argument("--require-all-checks", action="store_true",
                    help="exit 3 when any check could not run, even with no findings")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--snapshot", action="store_true",
                    help="record the plan as loaded into <repo>/.claude/plan-baseline/ "
                         "and exit; refuses if a baseline already exists")
    ap.add_argument("--repo",
                    help="the project repo the plan is executed in (default: cwd); "
                         "holds the baseline and supplies the evidence commits")
    args = ap.parse_args()
    if args.snapshot:
        sys.exit(take_snapshot(args))
    sys.exit(report(build(args), args))


if __name__ == "__main__":
    try:
        main()
    except Bail as e:
        print(f"plan-flip-audit: {e}", file=sys.stderr)
        sys.exit(2)
    except SystemExit:
        raise
    except Exception as e:  # never let a crash exit 1 and read as "findings"
        print(f"plan-flip-audit: internal error: {e.__class__.__name__}: {e}",
              file=sys.stderr)
        sys.exit(2)
