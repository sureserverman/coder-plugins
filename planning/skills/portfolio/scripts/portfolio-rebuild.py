#!/usr/bin/env python3
"""portfolio-rebuild — sidecar v2 enrichment + global rollups into the vault.

- Sidecar v2: writes the PORTFOLIO-STATUS block into each registered project's
  .claude/vault-context.md with Home plus pointer links to plans/, backlog,
  maturity, ship-readiness and inbound integration-debt (counts/verdicts are
  NOT snapshotted here — they'd go stale against the live vault), and the
  ⬆depends_on / ⬇impacts edges (from integration.md).
- Globals: Portfolio/global-backlog.md + Portfolio/global-maturity.md, project
  names as [[wikilinks]], reading from the vault Portfolio tree.

Idempotent: re-running with no upstream change produces byte-identical output
(timestamp suppressed when content is unchanged).
"""
import os, re, subprocess, sys, tempfile, yaml, datetime
from pathlib import Path

REGISTRY = Path.home() / ".claude" / "projects-registry.yaml"
CONFIG = Path.home() / ".claude" / "portfolio-config.yaml"
TODAY = datetime.date.today().isoformat()
BEGIN = "<!-- PORTFOLIO-STATUS-BEGIN — managed by /planning:portfolio rebuild; do not hand-edit -->"
END = "<!-- PORTFOLIO-STATUS-END -->"
WIKI = re.compile(r"\[\[([^\]]+)\]\]")
STRUCTURAL = {"backlog", "open", "closed", "done", "archive", "cross-project items"}


def vault_dir():
    """The configured vault root, or a loud refusal. Never a fallback destination.

    Two ways this can be wrong, and they are ONE posture, not two (SKILL.md
    § Resolver, § Configuration):

      * **Unset** — no config, or no `vault_dir` key. Refused since storage went
        vault-canonical; the `~/.claude/` mirror that used to absorb this was
        retired, so there is nothing left to fall back TO.
      * **Set but missing** — the key names a directory that is not there: an
        unmounted NFS vault, a typo, a machine that never had one. Left
        unchecked this was strictly WORSE than the unset case, because nothing
        downstream refuses on its behalf. `portfolio-migrate.py` mkdir(parents=
        True)s the project home, so a run against an unmounted /mnt/vault would
        materialise a second, empty vault tree at the mount point and migrate a
        repo's only copy of its docs into it — a silent fallback write with the
        real vault still holding the divergent original. A missing vault is not
        an empty vault, and the only safe answer is to stop.

    expanduser() runs BEFORE the check on purpose. `vault_dir: ~/vault` is not
    an absolute path to Python; unexpanded it is RELATIVE, and every write would
    land in `<cwd>/~/vault` — the same defect reached by a different route. It
    also keeps this resolver's definition of the corpus identical to
    plan-progress.py's, which has always expanded (DEC-011: every function
    taking the corpus as an argument must use the same definition of it).
    """
    cfg = yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}
    vd = cfg.get("vault_dir")
    if not vd:
        sys.exit("portfolio not configured: set vault_dir in ~/.claude/portfolio-config.yaml")
    return require_vault(vd, CONFIG)


def vault_problem(path, source):
    """The vault at `path` if it is REACHABLE, else exit with a specific message.

    `path` is the raw configured value (str) or an already-built Path; a str is
    `~`-expanded here so every caller expands identically (DEC-011: one definition
    of the corpus).

    Separate from vault_dir() because the same rule binds paths that never came
    from the config at all — `plan-status-audit.py --vault` (which writes
    `.audit-backups/` into the tree it is handed) and `decisions-relevant.py
    --vault-dir` (which writes nothing, but would otherwise render an unreachable
    register as "bound by no global decisions", an empty result read as truth).
    `source` names where the bad value came from, so the operator is told which
    knob to turn rather than just that one is wrong.

    Three conditions, and the second is the one that matters most in practice:

      * **Not absolute.** `vault_dir: vault` is resolved against the process cwd,
        so one config silently means a different vault per directory you run from.
        Refused rather than resolved, because resolving it would pick one of them.
      * **Not a mounted vault.** `is_dir()` alone CANNOT see the headline case this
        guard exists for. A mountpoint is a directory whether or not anything is
        mounted on it, so an unmounted NFS vault — the exact scenario named here —
        passes `is_dir()` as a local, empty directory. `portfolio-migrate` then
        mkdir(parents=True)s into it and moves a repo's only copy of its docs to a
        phantom tree, with the real vault still holding the divergent original and
        nothing git-tracked to recover from. So a vault is defined by CONTENT:
        it contains `Portfolio/`. An unmounted mountpoint does not.
        (`android-mcp-orchestrator/scripts/up.sh:133` records the same lesson for
        bind mounts: the layer below will happily create an empty directory for a
        source that is not there.)
      * **Missing entirely.** The original case, unchanged.

    First-run is deliberate, not accidental: a brand-new vault is initialised by
    creating `<vault>/Portfolio/` once, by hand. That is the whole cost of making
    an unmounted mount indistinguishable from a fresh one impossible.
    """
    if isinstance(path, str):
        path = Path(path).expanduser()
    elif not isinstance(path, Path):
        return None, (f"vault unreachable: vault_dir (from {source}) must be a path, "
                      f"got {type(path).__name__} — correct vault_dir.")
    if not path.is_absolute():
        return None, (f"vault unreachable: vault_dir {path} (from {source}) is a "
                      f"relative path, so it names a different directory depending "
                      f"on where you run from — refusing. Use an absolute path.")
    try:
        existing = path.is_dir()
        sentinel = existing and (path / "Portfolio").is_dir()
    except OSError as e:
        # A vault that cannot be STATTED is unreachable, not a traceback. Python
        # 3.12's Path.is_dir() propagates OSError rather than returning False, and
        # a dropped or re-exported NFS mount usually surfaces as EACCES or ESTALE
        # rather than ENOENT — so the likeliest real-world failure was the one that
        # escaped this function, which exists to turn unreachability into a message.
        return None, (f"vault unreachable: vault_dir {path} (from {source}) could "
                      f"not be read ({e.__class__.__name__}: {e.strerror or e}) — "
                      f"refusing. Check the mount and its permissions.")
    if not existing:
        return None, (f"vault unreachable: vault_dir {path} (from {source}) is not an "
                      f"existing directory — refusing, because a missing vault is not "
                      f"an empty vault. Mount the vault or correct vault_dir.")
    if not sentinel:
        return None, (f"vault unreachable: vault_dir {path} (from {source}) exists but "
                      f"has no Portfolio/ — refusing, because that is what an UNMOUNTED "
                      f"mountpoint looks like, and writing here would build a phantom "
                      f"vault. Mount the vault; or, for a genuinely new one, create "
                      f"{path / 'Portfolio'} first.")
    return path, None


def require_vault(path, source):
    """vault_problem(), for the callers that exit rather than return a code.

    Split so `plan-status-audit.py` can apply the SAME conditions and still return
    its own rc 2 instead of sys.exit's 1. Before the split it carried a hand-copied
    single-condition check and therefore silently kept the v1 guard while every
    other reader grew three more — on the one tool here that writes backups into
    whatever tree it is handed.
    """
    path, problem = vault_problem(path, source)
    if problem:
        sys.exit(problem)
    return path


def vault_live(vault):
    """The `Portfolio/` sentinel is still there — ONE stat, at a write boundary.

    `require_vault()` runs once, in `main()`, and the writes follow. If the vault goes away
    in between — an NFS mount dropping mid-run, which `--all` makes a realistic window —
    every `mkdir(parents=True)` downstream happily rebuilds the chain from nothing.
    Reproduced: with the root removed after a passing check, `migrate_project` returned `ok`
    and recreated `<vault>/Portfolio/<area>/<name>/` with the repo's docs inside it.

    Granularity is deliberate: the same sentinel `vault_problem()` uses, checked **per
    project** rather than per file. Per file would be a stat storm on an NFS vault for a
    window that does not meaningfully narrow; per run is what already failed. This does not
    close the race — nothing short of holding an open handle does — it bounds it to one
    project's writes, and says so rather than implying the guard is total.
    """
    try:
        return (Path(vault) / "Portfolio").is_dir()
    except OSError:
        return False


def read_utf8(path):
    """`(text, None)`, or `(None, "decode"|"io")` naming which failure occurred.

    Three reads in this file used a bare `read_text()` and one used
    `errors="ignore"`, and a review showed both halves of that were wrong:

      * **Bare read_text() crashes the run.** One non-UTF-8 byte in a single
        repo's `vault-context.md` aborted the whole rebuild MID sidecar pass, so
        later repos got no sidecar and no roll-up was written at all. A second
        bare read inside `write_if_changed` reproduced the same traceback on the
        roll-up itself, ~200 lines after the read that was supposed to have been
        fixed.
      * **errors="ignore" corrupts silently.** On the one path whose contract is
        "byte-for-byte", dropping undecodable bytes returns a body with characters
        permanently gone and an EMPTY stderr — then writes it back. That is the
        region-level rule of this file applied at the character level, and it was
        latent only because the crash above masked it.

    So: decode strictly, and hand the caller None to decide with. Every caller
    refuses rather than guesses, except the two fully-regenerable roll-ups where
    there is no curated content to lose — and even there, only on a DECODE
    failure. The second element says which failure it was, because "the bytes are
    not UTF-8" and "I could not read the bytes" are different facts that deserve
    different answers, and reporting the second as the first sent readers hunting
    for an encoding problem on an NFS mount that had simply dropped.
    """
    try:
        return path.read_bytes().decode("utf-8"), None
    except UnicodeDecodeError as e:
        print(f"warning: {path} is not valid UTF-8 ({type(e).__name__}) — "
              "not acting on its contents", file=sys.stderr)
        return None, "decode"
    except OSError as e:
        # A DIFFERENT fact, and the one this function used to misreport. EACCES,
        # EIO and NFS ESTALE all arrived here and were announced as "not readable
        # as UTF-8", which names the one cause it probably was not — and on an
        # NFS-backed vault a transient I/O fault is the LIKELY cause. The two
        # failures also want opposite responses: a file whose bytes are wrong may
        # be safe to regenerate, while a file we could not read at all tells us
        # nothing about what is in it, so the safe direction is to refuse.
        print(f"warning: {path} could not be READ ({type(e).__name__}: {e}) — "
              "this is an I/O failure, not a decoding one; not acting on its "
              "contents", file=sys.stderr)
        return None, "io"


def count_backlog(home):
    bl = home / "backlog.md"
    if not bl.exists():
        return 0, []
    t = bl.read_text(errors="ignore")
    idd = re.findall(r"^#{2,3}\s+BL-\d+\s+—\s+(.+)$", t, re.M)
    if idd:
        return len(idd), [x.strip() for x in idd[:3]]
    titles = [m.group(1).strip() for m in re.finditer(r"^##\s+(.+)$", t, re.M)
              if m.group(1).strip().lower() not in STRUCTURAL]
    return len(titles), titles[:3]


# Block boundaries are found with a GENERIC `## ` heading match, then the ID
# shape is validated per-section. Detecting boundaries with the strict ID regex
# instead would make a mistyped heading (a plain hyphen where the format wants
# an em-dash) invisible: its body would be swallowed into the previous block's
# last field, or — if it were the first heading — dropped entirely. Either way a
# binding decision disappears silently, which is the one outcome this register
# exists to prevent.
BLOCK_HEAD_RE = re.compile(r"^## +(.+?)\s*$", re.M)
# The project tag (`DEC-MT-003`) is optional. Untagged `DEC-003` is the
# canonical form; a tag is accepted because a register whose entries are
# cited from other projects' plans needs an ID that is unambiguous outside
# its own file, and rewriting those citations to drop the tag would break
# every existing reference to buy nothing.
DEC_ID_RE = re.compile(r"^(DEC-(?:[A-Z]{2,4}-)?\d+)\s+—\s+(.+)$")
GDEC_ID_RE = re.compile(r"^(GDEC-[A-Z]+-\d+)\s+—\s+(.+)$")
RULE_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
FIELD_LINE_RE = re.compile(r"^\s*-\s+\*\*([^:*]+):\*\*\s*(.*)$")
GLOBAL_LINK_RE = re.compile(r"\[\[decisions/([A-Za-z0-9_-]+)#(GDEC-[A-Z]+-\d+)\]\]")
APPLIES_LINK_RE = re.compile(r"([A-Za-z0-9_-]+)/\[\[([^\]]+)\]\]")
ANY_WIKILINK_RE = re.compile(r"\[\[([^\]#]+)\]\]")
PROJECT_REQUIRED = ("Decided", "Status", "Domains", "Source", "Reason")
DOMAIN_REQUIRED = ("Decided", "Status", "Reason", "Applies to")


def parse_decision_file(text, id_re, required):
    """Parse `## <ID> — <title>` blocks into dicts (see references/decisions-format.md).

    Degrade, never drop: a block missing a required field comes back with a
    populated `missing` list rather than being skipped, so the roll-up can show
    it as malformed. A silently-dropped decision is worse than a flagged one —
    the register's whole job is that nothing binding goes unrecorded.
    """
    out = []
    marks = list(BLOCK_HEAD_RE.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        heading = m.group(1).strip()
        fields, cur, dupes = {}, None, []
        for line in text[m.end():end].splitlines():
            fm = FIELD_LINE_RE.match(line)
            if fm:
                cur = fm.group(1).strip()
                if cur in fields:
                    dupes.append(cur)
                fields[cur] = fm.group(2).strip()
            elif cur and line.strip() and not RULE_RE.match(line.strip()):
                # Continuation: wrapped prose, or the nested bullets of a list
                # field like `Applies to`. Joined flat; links are re-extracted
                # by regex, so the nesting carries no meaning we need to keep.
                fields[cur] = (fields[cur] + " " + line.strip()).strip()
        idm = id_re.match(heading)
        if not idm:
            # Flagged, not skipped — see BLOCK_HEAD_RE. `missing` is a
            # don't-care sentinel here (every required field, regardless of what
            # the body actually holds): the heading has to be repaired before
            # per-field state means anything, and every consumer branches on
            # `id is None` first.
            out.append({"id": None, "heading": heading, "title": heading, "fields": fields,
                        "missing": list(required), "duplicates": dupes,
                        "malformed_heading": True})
            continue
        out.append({"id": idm.group(1), "heading": heading, "title": idm.group(2).strip(),
                    "fields": fields, "duplicates": dupes, "malformed_heading": False,
                    "missing": [f for f in required if not fields.get(f)]})
    return out


def duplicate_id_errors(entries):
    """IDs claimed by more than one block in the same register.

    Cross-FILE GDEC collisions are caught in decision_symmetry; this is the
    within-file case, where two blocks share an ID and every reference to it
    becomes ambiguous. Reported, not resolved — nothing here can know which
    block the author meant to keep.
    """
    seen, dupes = set(), []
    for e in entries:
        if e["id"] is None:
            continue
        if e["id"] in seen and e["id"] not in dupes:
            dupes.append(e["id"])
        seen.add(e["id"])
    return [f"`{d}` is defined by more than one block in this file — "
            f"every reference to it is ambiguous" for d in dupes]


def read_project_decisions(home):
    """{entries, errors} for a project's decisions.md, or None if it has none."""
    f = home / "decisions.md"
    if not f.exists():
        return None
    try:
        text = f.read_text(errors="ignore")
    except OSError as e:
        return {"entries": [], "errors": [f"unreadable: {e}"]}
    entries = parse_decision_file(text, DEC_ID_RE, PROJECT_REQUIRED)
    errors = duplicate_id_errors(entries)
    if not entries:
        errors.append("no DEC-NNN blocks found")
    return {"entries": entries, "errors": errors}


def read_domain_decisions(vd):
    """{domain_slug: {entries, errors}} across Portfolio/decisions/*.md."""
    d = vd / "Portfolio" / "decisions"
    out = {}
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.md")):
        try:
            text = f.read_text(errors="ignore")
        except OSError as e:
            out[f.stem] = {"entries": [], "errors": [f"unreadable: {e}"]}
            continue
        entries = parse_decision_file(text, GDEC_ID_RE, DOMAIN_REQUIRED)
        errors = duplicate_id_errors(entries)
        if not entries:
            errors.append("no GDEC blocks found")
        out[f.stem] = {"entries": entries, "errors": errors}
    return out


def decision_domains(entry):
    raw = entry["fields"].get("Domains", "")
    return [d.strip().lower() for d in raw.split(",") if d.strip() and d.strip().lower() != "none"]


def decision_symmetry(proj_decisions, domain_decisions):
    """Cross-check Global: ↔ Applies to: in both directions.

    Returns (asymmetries, unresolved). Reported, NEVER auto-fixed: repairing one
    side would mean asserting an edge about a project this run has not read —
    the same rule integration.md's symmetry check follows.
    """
    asym, unresolved = [], []
    # index: gdec id -> (domain, set of applied-to project names)
    gindex = {}
    for domain, blk in sorted(domain_decisions.items()):
        for e in blk["entries"]:
            if e["id"] is None:
                continue
            raw = e["fields"].get("Applies to", "")
            applied = {n for _a, n in APPLIES_LINK_RE.findall(raw)}
            # A bare [[name]] with no <area>/ prefix matches neither direction of
            # the symmetry check, so it would silently not exist. Every other
            # malformation in this lane surfaces somewhere; this one must too.
            for bare in ANY_WIKILINK_RE.findall(raw):
                if bare not in applied:
                    unresolved.append(
                        f"`{e['id']}` ({domain}) lists `[[{bare}]]` without an "
                        f"`<area>/` prefix — it is not counted as an edge")
            if e["id"] in gindex:
                # Two domain files claiming one ID make every link to it
                # ambiguous. Report it rather than let the later file win.
                unresolved.append(f"`{e['id']}` is defined in both `{gindex[e['id']][0]}` "
                                  f"and `{domain}` — link targets are ambiguous")
                continue
            gindex[e["id"]] = (domain, applied)

    linked = {}                       # gdec id -> set of projects claiming it
    for pname, blk in sorted(proj_decisions.items()):
        if blk is None:               # project carries no decisions.md
            continue
        for e in blk["entries"]:
            if e["id"] is None:
                # A bad heading doesn't stop the rest of the block parsing, so
                # such an entry can still carry a Global: link. Report it as
                # unresolvable rather than emitting "<project> None links …" —
                # the heading is what has to be fixed first.
                if GLOBAL_LINK_RE.search(e["fields"].get("Global", "")):
                    unresolved.append(f"{pname} has a malformed heading "
                                      f"(`{e['heading']}`) with a Global link — fix the heading first")
                continue
            m = GLOBAL_LINK_RE.search(e["fields"].get("Global", ""))
            if not m:
                continue
            domain, gid = m.group(1), m.group(2)
            linked.setdefault(gid, set()).add(pname)
            if gid not in gindex:
                unresolved.append(f"{pname} {e['id']} → `{gid}` in `{domain}` (no such domain entry)")
                continue
            owner = gindex[gid][0]
            if domain != owner:
                # Resolving on the ID alone would report a link that points at a
                # register which does not contain the entry as correct.
                unresolved.append(f"{pname} {e['id']} links `{gid}` as `{domain}`, "
                                  f"but that entry lives in `{owner}`")
            if pname not in gindex[gid][1]:
                asym.append(f"{pname} {e['id']} links `{gid}`, but `{gid}` does not list {pname} under Applies to")

    for gid, (domain, applied) in sorted(gindex.items()):
        for pname in sorted(applied):
            if proj_decisions.get(pname) is None:
                unresolved.append(f"`{gid}` ({domain}) applies to {pname}, which has no decisions.md")
            elif pname not in linked.get(gid, set()):
                asym.append(f"`{gid}` ({domain}) lists {pname}, but no {pname} decision links back to it")
    return asym, unresolved


def maturity_axes(home):
    mp = home / "MATURITY.md"
    if not mp.exists():
        return None
    t = mp.read_text(errors="ignore")
    axes = {}
    for sec in re.split(r"^## ", t, flags=re.M)[1:]:
        head, *body = sec.split("\n", 1)
        head = head.strip()
        bt = body[0] if body else ""
        if head not in ("Documentation", "Security", "Packaging", "UI/UX", "i18n", "Testing & CI"):
            continue
        present = len(re.findall(r"^- \[[ x]\]", bt, re.M))
        ticked = len(re.findall(r"^- \[x\]", bt, re.M))
        na = len(re.findall(r"^- \[N/A\]", bt, re.M))
        axes[head] = (ticked, present, na)
    return axes


def cell(axes, a):
    if a not in axes:
        return "⚪ –"
    t, p, na = axes[a]
    if p == 0 and na == 0:
        return "⚪ –"
    if p == 0 and na > 0:
        return "⚪ N/A"
    if t == p:
        return f"🟢 {t}/{p}"
    if t == 0:
        return f"🔴 0/{p}"
    return f"🟡 {t}/{p}"


def ship_ready(axes):
    if axes is None:
        return False
    def ok(a):
        s = axes.get(a, (0, 0, 0))
        return s[0] == s[1] and (s[1] > 0 or s[2] > 0)
    return all(ok(a) for a in ("Documentation", "Security", "Packaging", "UI/UX", "i18n", "Testing & CI"))


def integration_edges(home):
    f = home / "integration.md"
    dep, imp = [], []
    if f.exists():
        m = re.match(r"^---\n(.*?)\n---", f.read_text(errors="ignore"), re.S)
        if m:
            try:
                fm = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError:
                fm = {}
            for e in (fm.get("depends_on") or []):
                w = WIKI.search(e.get("target", "")) if isinstance(e, dict) else None
                if w: dep.append((w.group(1), e.get("why", "")))
            for e in (fm.get("impacts") or []):
                w = WIKI.search(e.get("target", "")) if isinstance(e, dict) else None
                if w: imp.append((w.group(1), e.get("why", "")))
    return dep, imp


def inbound_debt(home):
    bl = home / "backlog.md"
    if not bl.exists():
        return 0
    return len(re.findall(r"^\s*-?\s*\*?\*?Integration:\*?\*?\s*from=", bl.read_text(errors="ignore"), re.M))


def maturity_row_emoji(axes):
    if axes is None:
        return "no MATURITY.md"
    def e(a, sym):
        if a not in axes: return f"{sym}⚪"
        t, p, na = axes[a]
        if p == 0 and na == 0: return f"{sym}⚪"
        if t == p: return f"{sym}🟢"
        if t == 0: return f"{sym}🔴"
        return f"{sym}🟡"
    return " ".join([e("Documentation","Docs:"), e("Security","Sec:"), e("Packaging","Pkg:"),
                     e("UI/UX","UI:"), e("i18n","i18n:"), e("Testing & CI","Tests:")])


def write_sidecar(repo, home, vd, write):
    sc = Path(repo) / ".claude" / "vault-context.md"
    dep, imp = integration_edges(home)
    # Pointer-only: counts/verdicts (backlog, maturity, ship-ready, debt) are
    # NOT embedded here. The repo-committed sidecar lags the vault, so an inline
    # value goes stale the moment the vault's backlog/MATURITY change. The block
    # therefore links to the live source files instead of snapshotting them.
    lines = [BEGIN, "## Portfolio status", "",
             f"- **Home:** `{home}`   (plans/backlog/maturity live here, not in this repo's docs/)",
             f"- **Plans:** see [plans/]({home}/plans/)",
             f"- **Backlog:** see [backlog.md]({home}/backlog.md)",
             f"- **Maturity:** see [MATURITY.md]({home}/MATURITY.md)",
             f"- **Ship-ready:** see [global dashboard]({vd}/Portfolio/global-maturity.md)"]
    # Conditional, unlike the lines above: most projects have no decisions.md,
    # and a pointer to a file that doesn't exist is worse than no pointer.
    if (home / "decisions.md").exists():
        lines.append(f"- **Decisions:** see [decisions.md]({home}/decisions.md)")
    if dep:
        lines.append("- **⬆ Depends on:** " + ", ".join(f"[[{t}]] ({w})" for t, w in dep))
    if imp:
        lines.append("- **⬇ Impacts:** " + ", ".join(f"[[{t}]] ({w})" for t, w in imp))
    lines.append(f"- **Inbound integration debt:** see [integration-backlog.md]({vd}/Portfolio/integration-backlog.md)")
    lines += ["", END]
    block = "\n".join(lines)

    cur = None
    if sc.exists():
        # Read ONCE. The old code read the file twice — once to splice, once to
        # compare — which is two chances to crash and one chance to disagree with
        # itself if the file changes between them.
        cur, _ = read_utf8(sc)
        if cur is None:
            # Skip THIS repo, do not abort the run, and never overwrite a file
            # whose contents could not be read: everything outside the sentinels
            # is the user's, and this block promises to preserve it.
            print(f"warning: {sc} could not be decoded — skipping this repo's "
                  "sidecar rather than overwriting content that cannot be read",
                  file=sys.stderr)
            return False
        if BEGIN in cur and END in cur:
            new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), block, cur, count=1, flags=re.S)
        else:
            new = cur.rstrip("\n") + "\n\n" + block + "\n"
    else:
        new = f"# Vault context for {Path(repo).name}\n\n{block}\n"
    if write and (cur is None or new != cur):
        sc.parent.mkdir(parents=True, exist_ok=True)
        sc.write_text(new)
        return True
    return False


PRESERVE_BEGIN = "<!-- BEGIN PRESERVE — content below this line is preserved across rebuilds -->"
PRESERVE_END = "<!-- END PRESERVE -->"


def preserved_region(path):
    """The hand-curated body between the PRESERVE sentinels of an existing roll-up.

    Returns the body, `""` when there is nothing to preserve, or **None when the
    file is AMBIGUOUS and must not be rewritten at all.**

    `render_global_backlog` used to take only (vd, projects) and always emit an
    EMPTY sentinel pair, so every `rebuild --write` silently destroyed the curated
    `## Cross-project items` — the one thing `../SKILL.md` § `rebuild` promises
    survives "byte-for-byte", and which `global-formats.md` § Hard rules spells out
    as "Do not silently drop previously curated GBL items".

    **The first fix narrowed that bug without closing it, and the None case is why
    this function now counts sentinels instead of taking the first pair it finds.**
    Two reachable ways to lose data silently, both found by review:

      * **The recovery path this function itself prescribes.** Told that sentinels
        were missing, an operator pastes the recovered section back in — sentinels
        and all — below the generated empty pair. First-match then returns the
        EMPTY generated region and the recovered content is destroyed on the next
        run. That is the run where they have already lost the data once, and the
        vault is not git-tracked (`subcommand-migrate.md`), so there is no second
        recovery.
      * **A curated item containing the literal end sentinel** — exactly the kind of
        cross-project note that documents this mechanism — truncates the region
        there and drops everything after it.

    So an ambiguous file returns None and the caller LEAVES IT ALONE. Returning ""
    on an unreadable-but-non-empty file is the one behavior that must not be
    reachable here: it converts "I do not understand this file" into "this file was
    empty". That is the same degrade-loudly-never-truncate contract
    `rebuild_global_security` already follows.
    """
    if not path.exists():
        return ""
    # STRICT decode, and refuse on failure. An earlier cut used errors="ignore"
    # here on the reasoning that it matched the file's other vault reads. It did
    # not — those reads are of files being counted or parsed, not of the one file
    # whose contract is "byte-for-byte" and whose content is unrecoverable. Ignoring
    # undecodable bytes there returns a curated body with characters silently
    # deleted and then writes it back, which is the region-level rule this
    # function exists to enforce, violated at the character level.
    text, _ = read_utf8(path)
    if text is None:
        print(f"warning: {path.name} could not be decoded as UTF-8 — REFUSING to "
              "rewrite it. Nothing was written.", file=sys.stderr)
        return None
    nb, ne = text.count(PRESERVE_BEGIN), text.count(PRESERVE_END)
    if nb == 0 and ne == 0:
        if text.strip():
            print(f"warning: {path.name} is missing its PRESERVE sentinels; "
                  "writing an empty block — recover curated items from a backup, "
                  "and paste the body only, NOT the sentinel lines",
                  file=sys.stderr)
        return ""
    if nb != 1 or ne != 1:
        # Branch the advice: "resolve the duplicates" is wrong guidance for a file
        # that has too FEW sentinels, and an operator following it looks for
        # something that is not there.
        how = ("Remove the extra pair, keeping the one with your curated items"
               if nb > 1 or ne > 1 else
               "Restore the missing sentinel around your curated items")
        print(f"warning: {path.name} has {nb} BEGIN and {ne} END PRESERVE "
              f"sentinels, expected one of each — REFUSING to rewrite it. {how}; "
              "nothing was written.", file=sys.stderr)
        return None
    i = text.find(PRESERVE_BEGIN)
    j = text.find(PRESERVE_END, i + len(PRESERVE_BEGIN))
    if j == -1:
        print(f"warning: {path.name} has its PRESERVE sentinels out of order — "
              "REFUSING to rewrite it. Nothing was written.", file=sys.stderr)
        return None
    return text[i + len(PRESERVE_BEGIN):j].strip("\n")


def render_global_backlog(vd, projects, preserved):
    # `preserved` is REQUIRED, not defaulted. With a default, re-introducing the
    # original bug is a legal one-token edit at the call site — dropping the
    # argument — and a test that drives this function directly stays green through
    # it. Mutation-probed by a review: the guard was green against the exact
    # regression it exists to catch. There is one caller.
    L = ["# Global Backlog", "",
         "Auto-generated index of every per-project backlog in the vault Portfolio",
         "tree. Edit the `## Cross-project items` section by hand; everything else is",
         "regenerated by `/planning:portfolio rebuild`.", "",
         f"**Last rebuilt:** {TODAY}", "", "---", "", "## Per-project backlogs", ""]
    for p in sorted(projects, key=lambda x: (x["area"], x["name"])):
        home = vd / "Portfolio" / p["area"] / p["name"]
        n, titles = count_backlog(home)
        if n == 0:
            continue
        L += [f"### {p['area']}/[[{p['name']}]] — {n} open",
              f"- **Path:** `{home}/backlog.md`",
              f"- **3 newest:** {', '.join(titles) or 'none'}", ""]
    L += ["---", "", "## Cross-project items", "", PRESERVE_BEGIN, ""]
    if preserved:
        L += [preserved, ""]
    L += [PRESERVE_END, ""]
    return "\n".join(L)


def render_global_maturity(vd, projects):
    L = ["# Global Maturity Dashboard", "",
         "Auto-generated from per-project MATURITY.md in the vault Portfolio tree.", "",
         f"**Last rebuilt:** {TODAY}", "", "---", "",
         "| Project | Docs | Sec | Pkg | UI/UX | i18n | Tests/CI | Ship-ready? |",
         "|---------|------|-----|-----|-------|------|----------|-------------|"]
    ready = 0; total = 0
    for p in sorted(projects, key=lambda x: (x["area"], x["name"])):
        home = vd / "Portfolio" / p["area"] / p["name"]
        axes = maturity_axes(home)
        if axes is None:
            continue
        total += 1
        cells = [cell(axes, a) for a in ("Documentation","Security","Packaging","UI/UX","i18n","Testing & CI")]
        rr = ship_ready(axes); ready += rr
        L.append(f"| {p['area']}/[[{p['name']}]] | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[4]} | {cells[5]} | {'✅ yes' if rr else '❌ no'} |")
    L += ["", "---", "", f"**{total} projects tracked. {ready} ship-ready.**", ""]
    return "\n".join(L)


def render_global_decisions(vd, projects):
    """Portfolio/global-decisions.md — the cross-project view of why things are
    the way they are. Returns (markdown, wrote_anything_worth_writing)."""
    proj_dec, homes = {}, {}
    for p in projects:
        home = vd / "Portfolio" / p["area"] / p["name"]
        blk = read_project_decisions(home)
        if blk is not None:
            proj_dec[p["name"]] = blk
            homes[p["name"]] = p["area"]
    domains = read_domain_decisions(vd)
    asym, unresolved = decision_symmetry(proj_dec, domains)

    L = ["# Global Decisions", "",
         "Auto-generated index of every architectural decision recorded in the",
         "vault Portfolio tree — per-project registers (`decisions.md`) and the",
         "per-domain registers under `Portfolio/decisions/`. Regenerated by",
         "`/planning:portfolio rebuild`; edit the registers, never this file.", "",
         f"**Last rebuilt:** {TODAY}", "", "---", "", "## By domain", ""]
    if not domains:
        L += ["_No domain registers yet._", ""]
    for domain in sorted(domains):
        blk = domains[domain]
        L.append(f"### {domain}")
        for e in blk["entries"]:
            if e["id"] is None:
                L.append(f"- ⚠️ **malformed heading** — `{e['heading']}`")
                continue
            status = e["fields"].get("Status", "?")
            mark = "" if status == "accepted" else f" _({status})_"
            L.append(f"- **{e['id']}** — {e['title']}{mark}")
            applied = APPLIES_LINK_RE.findall(e["fields"].get("Applies to", ""))
            if applied:
                L.append("  - applies to: " + ", ".join(f"{a}/[[{n}]]" for a, n in applied))
            if e["missing"]:
                L.append(f"  - ⚠️ missing: {', '.join(e['missing'])}")
            if e["duplicates"]:
                L.append(f"  - ⚠️ duplicate field(s): {', '.join(sorted(set(e['duplicates'])))}")
        for err in blk["errors"]:
            L.append(f"- ⚠️ {err}")
        L.append("")

    L += ["---", "", "## By project", "",
          "| Project | Decisions | Accepted | Superseded | Domains |",
          "|---------|-----------|----------|------------|---------|"]
    total = 0
    for name in sorted(proj_dec, key=lambda n: (homes[n], n)):
        entries = proj_dec[name]["entries"]
        real = [e for e in entries if e["id"] is not None]
        acc = sum(1 for e in real if e["fields"].get("Status") == "accepted")
        sup = sum(1 for e in real if str(e["fields"].get("Status", "")).startswith("superseded"))
        doms = sorted({d for e in real for d in decision_domains(e)})
        flag = " ⚠️" if len(real) != len(entries) or any(e["missing"] for e in real) else ""
        total += len(real)
        L.append(f"| {homes[name]}/[[{name}]] | {len(real)}{flag} | {acc} | {sup} | "
                 f"{', '.join(doms) or '–'} |")
    if not proj_dec:
        L.append("| _none yet_ | – | – | – | – |")

    # Project-side malformations get their own section rather than a bare ⚠️ in
    # a table cell: the register's contract is that a flagged entry is visible
    # and actionable, and "something is wrong with one of 12 decisions" is not.
    L += ["", "---", "", "## Malformed entries (review)", ""]
    bad = []
    for name in sorted(proj_dec, key=lambda n: (homes[n], n)):
        for e in proj_dec[name]["entries"]:
            where = f"{homes[name]}/[[{name}]]"
            if e["id"] is None:
                bad.append(f"- {where} — malformed heading: `{e['heading']}`")
                continue
            if e["missing"]:
                bad.append(f"- {where} {e['id']} — missing: {', '.join(e['missing'])}")
            if e["duplicates"]:
                bad.append(f"- {where} {e['id']} — duplicate field(s): "
                           f"{', '.join(sorted(set(e['duplicates'])))}")
        for err in proj_dec[name]["errors"]:
            bad.append(f"- {homes[name]}/[[{name}]] — {err}")
    L += (bad or ["_None._"])

    L += ["", "## Asymmetries (review)", ""]
    # Reported, never auto-fixed — repairing one side would assert an edge about
    # a project this run has not read. Same rule as integration-graph.md.
    L += ([f"- {a}" for a in sorted(asym)] or ["_None._"])
    L += ["", "## Unresolved targets", ""]
    L += ([f"- {u}" for u in sorted(unresolved)] or ["_None._"])
    L += ["", "---", "",
          f"**{total} decisions across {len(proj_dec)} projects and "
          f"{len(domains)} domains.**", ""]
    return "\n".join(L)


def atomic_write(path, content):
    """Write via a temp file in the same directory, then `os.replace`.

    `path.write_text()` is truncate-then-write: an interrupted run leaves a
    truncated roll-up in a tree with no version control, so the failure mode of a
    crash mid-write was a half-file that still looks like a file. `os.replace` is
    atomic within a filesystem, and the temp file is created beside the target so
    it is always the same filesystem. The temp file is cleaned up on failure —
    leaving `global-backlog.md.tmp123` beside the real one is its own small mess.
    """
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_if_changed(path, content):
    # TWO stamp forms, because the roll-ups do not agree on one. Four of them use
    # `**Last rebuilt:**` (rendered here); `global-business.md` comes from
    # business-rollup.py, a separately versioned plugin, and stamps a bare
    # `Generated:` on line 2 instead. Normalising only the first form meant
    # global-business.md was the one roll-up that still rewrote itself on every
    # date change — invisible in a same-day double-run, and it survived the
    # stage that set out to stop exactly this churn. Anchored to line start and
    # limited to the header region (count=1), so a `Generated:` occurring in a
    # project's own content further down is left alone.
    def strip_ts(s):
        s = re.sub(r"\n\*\*Last rebuilt:\*\*[^\n]*\n", "\nTS\n", s)
        return re.sub(r"(?m)^Generated:[^\n]*$", "TS", s, count=1)
    if path.exists():
        cur, why = read_utf8(path)
        if why == "io":
            # REFUSE. An unreadable file tells us nothing about what is in it, so
            # overwriting it is a guess dressed as a repair — and the likely cause
            # on an NFS-backed vault is a transient fault that will clear. This is
            # the one branch where the decode/I-O distinction changes behaviour
            # rather than only the message.
            print(f"warning: {path.name} could not be read — REFUSING to rewrite "
                  "it. Nothing was written.", file=sys.stderr)
            return False
        if cur is None:
            # Regenerating is safe HERE and only here, and only for a DECODE
            # failure: the roll-ups that reach this function with an undecodable
            # existing file carry no curated content. global-backlog.md cannot:
            # `preserved_region` decodes it strictly first and returns None, and
            # main() skips the write, so an undecodable roll-up with a curated
            # block never gets this far.
            print(f"warning: {path.name} is not valid UTF-8 — regenerating it "
                  "from scratch", file=sys.stderr)
        elif strip_ts(cur) == strip_ts(content):
            return False
    atomic_write(path, content)
    return True


def business_scripts():
    """(scan, rollup) paths for the OPTIONAL business plugin, or (None, None) if
    it isn't installed alongside. BUSINESS_SCAN_PATH overrides the scan path
    (used by the degradation test to force the layer off). Additive by design:
    the business layer never changes portfolio-rebuild's existing outputs."""
    root = Path(__file__).resolve().parents[4]          # marketplace root (…/coder-plugins)
    scan = Path(os.environ.get("BUSINESS_SCAN_PATH")
                or root / "business" / "scripts" / "business-scan.py")
    rollup = root / "business" / "scripts" / "business-rollup.py"
    return (scan, rollup) if scan.exists() and rollup.exists() else (None, None)


def rebuild_global_business(vd, scan, rollup):
    """Run business-scan | business-rollup and write global-business.md. Returns
    True if written, False if unchanged, None on failure (degrade loudly, leave
    any existing file intact — never truncate on a failed sweep)."""
    try:
        scan_p = subprocess.run([sys.executable, str(scan)], capture_output=True,
                                text=True, timeout=120)
        if scan_p.returncode != 0:
            print(f"business-scan failed: {scan_p.stderr.strip().splitlines()[:1]}", file=sys.stderr)
            return None
        roll = subprocess.run([sys.executable, str(rollup)], input=scan_p.stdout,
                              capture_output=True, text=True, timeout=120)
        if roll.returncode != 0:
            print(f"business-rollup failed: {roll.stderr.strip().splitlines()[:1]}", file=sys.stderr)
            return None
    except subprocess.TimeoutExpired:
        print("business layer timed out — left global-business.md untouched", file=sys.stderr)
        return None
    return write_if_changed(vd / "Portfolio" / "global-business.md", roll.stdout)


def rebuild_global_security(vd, write):
    """Run security-scan | security-rollup and write global-security.md.

    Same contract as the business layer: True written, False unchanged, None on
    failure — degrade loudly and leave any existing file intact, because a
    truncated security dashboard is worse than a stale one.
    """
    here = Path(__file__).resolve().parent
    scan, rollup = here / "security-scan.py", here / "security-rollup.py"
    if not (scan.exists() and rollup.exists()):
        return None
    try:
        s = subprocess.run([sys.executable, str(scan)], capture_output=True,
                           text=True, timeout=120)
        if s.returncode != 0:
            print(f"security-scan failed: {s.stderr.strip().splitlines()[:1]}", file=sys.stderr)
            return None
        r = subprocess.run([sys.executable, str(rollup)], input=s.stdout,
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print(f"security-rollup failed: {r.stderr.strip().splitlines()[:1]}", file=sys.stderr)
            return None
    except subprocess.TimeoutExpired:
        print("security layer timed out — left global-security.md untouched", file=sys.stderr)
        return None
    if not write:
        return "DRY-RUN"
    return write_if_changed(vd / "Portfolio" / "global-security.md", r.stdout)


def main():
    # Staleness probe, first thing and diagnostic only: one stderr line if this
    # copy is an older cached plugin than the checkout. Guarded because a probe
    # that cannot import must not be able to stop the command it is advising on.
    # Inside main() rather than at module scope on purpose — these modules
    # importlib-load each other, and a sibling import would then resolve against
    # the CALLER's sys.path[0] and fail for a reason having nothing to do with
    # staleness.
    try:
        import _staleness
        _staleness.warn_if_stale(__file__)
    except Exception:
        pass
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    vd = vault_dir()
    reg = yaml.safe_load(REGISTRY.read_text())
    projects = [p for p in reg["projects"] if p.get("enabled", True)]

    enriched = 0
    skipped_gone = 0
    for p in projects:
        # BL-099: the sentinel is re-checked at the WRITE boundary, once per project.
        # require_vault() ran in main() and the writes follow it; a mount that drops in
        # between let every downstream mkdir rebuild the chain from nothing. Per project
        # rather than per file, so an NFS vault pays one stat per project, not one per write.
        if not vault_live(vd):
            skipped_gone += 1
            continue
        home = vd / "Portfolio" / p["area"] / p["name"]
        if write_sidecar(p["path"], home, vd, args.write):
            enriched += 1
    if skipped_gone:
        print(f"warning: vault went away mid-run — skipped {skipped_gone} project(s) "
              f"rather than recreating it. Check the mount; nothing was written for them.",
              file=sys.stderr)

    gb_path = vd / "Portfolio" / "global-backlog.md"
    # None means the existing file is ambiguous (duplicate or out-of-order
    # sentinels). Skip the write entirely rather than rewrite it: the roll-up is
    # regenerable, the curated block is not, and the vault has no version control
    # behind it. The warning has already named the counts on stderr.
    preserved = preserved_region(gb_path)
    gb = None if preserved is None else render_global_backlog(vd, projects, preserved)
    gm = render_global_maturity(vd, projects)
    gd = render_global_decisions(vd, projects)
    wrote_gb = wrote_gm = wrote_gd = False
    if args.write:
        wrote_gb = write_if_changed(gb_path, gb) if gb is not None else False
        wrote_gm = write_if_changed(vd / "Portfolio" / "global-maturity.md", gm)
        wrote_gd = write_if_changed(vd / "Portfolio" / "global-decisions.md", gd)

    # Business layer — additive, degrade loudly. Present → also rebuild
    # global-business.md; absent → one clear line, everything above unchanged.
    scan, rollup = business_scripts()
    if scan and rollup:
        biz = rebuild_global_business(vd, scan, rollup) if args.write else "DRY-RUN"
        biz_status = f"global-business written: {biz}"
    else:
        biz_status = "business layer: unavailable (business plugin not installed)"

    # Security layer — additive and independent of the business layer; a
    # failure here must not disturb anything rendered above.
    sec = rebuild_global_security(vd, args.write)
    sec_status = ("security layer: unavailable (scripts missing)" if sec is None
                  else f"global-security written: {sec}")

    # `SKIPPED (ambiguous PRESERVE)` rather than `False`: a refusal and a no-op
    # look identical in this line otherwise, and the refusal is the one an
    # operator has to act on.
    gb_status = "SKIPPED (ambiguous PRESERVE)" if gb is None else wrote_gb
    print(f"sidecars enriched: {enriched} | global-backlog written: {gb_status} | "
          f"global-maturity written: {wrote_gm} | global-decisions written: {wrote_gd} | "
          f"{biz_status} | {sec_status} | {'WRITE' if args.write else 'DRY-RUN'}")


if __name__ == "__main__":
    main()
