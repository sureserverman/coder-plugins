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
import os, re, subprocess, sys, yaml, datetime
from pathlib import Path

REGISTRY = Path.home() / ".claude" / "projects-registry.yaml"
CONFIG = Path.home() / ".claude" / "portfolio-config.yaml"
TODAY = datetime.date.today().isoformat()
BEGIN = "<!-- PORTFOLIO-STATUS-BEGIN — managed by /planning:portfolio rebuild; do not hand-edit -->"
END = "<!-- PORTFOLIO-STATUS-END -->"
WIKI = re.compile(r"\[\[([^\]]+)\]\]")
STRUCTURAL = {"backlog", "open", "closed", "done", "archive", "cross-project items"}


def vault_dir():
    cfg = yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}
    vd = cfg.get("vault_dir")
    if not vd:
        sys.exit("portfolio not configured: set vault_dir in ~/.claude/portfolio-config.yaml")
    return Path(vd)


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
DEC_ID_RE = re.compile(r"^(DEC-\d+)\s+—\s+(.+)$")
GDEC_ID_RE = re.compile(r"^(GDEC-[A-Z]+-\d+)\s+—\s+(.+)$")
RULE_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
FIELD_LINE_RE = re.compile(r"^\s*-\s+\*\*([^:*]+):\*\*\s*(.*)$")
GLOBAL_LINK_RE = re.compile(r"\[\[decisions/([A-Za-z0-9_-]+)#(GDEC-[A-Z]+-\d+)\]\]")
APPLIES_LINK_RE = re.compile(r"([A-Za-z0-9_-]+)/\[\[([^\]]+)\]\]")
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
    return {"entries": entries,
            "errors": [] if entries else ["no DEC-NNN blocks found"]}


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
        out[f.stem] = {"entries": entries,
                       "errors": [] if entries else ["no GDEC blocks found"]}
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
            applied = {n for _a, n in APPLIES_LINK_RE.findall(e["fields"].get("Applies to", ""))}
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
            elif pname not in gindex[gid][1]:
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

    if sc.exists():
        cur = sc.read_text()
        if BEGIN in cur and END in cur:
            new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), block, cur, count=1, flags=re.S)
        else:
            new = cur.rstrip("\n") + "\n\n" + block + "\n"
    else:
        new = f"# Vault context for {Path(repo).name}\n\n{block}\n"
    if write and (not sc.exists() or new != sc.read_text()):
        sc.parent.mkdir(parents=True, exist_ok=True)
        sc.write_text(new)
        return True
    return False


def render_global_backlog(vd, projects):
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
    L += ["---", "", "## Cross-project items", "",
          "<!-- BEGIN PRESERVE — content below this line is preserved across rebuilds -->", "",
          "<!-- END PRESERVE -->", ""]
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


def write_if_changed(path, content):
    def strip_ts(s): return re.sub(r"\n\*\*Last rebuilt:\*\*[^\n]*\n", "\nTS\n", s)
    if path.exists() and strip_ts(path.read_text()) == strip_ts(content):
        return False
    path.write_text(content)
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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    vd = vault_dir()
    reg = yaml.safe_load(REGISTRY.read_text())
    projects = [p for p in reg["projects"] if p.get("enabled", True)]

    enriched = 0
    for p in projects:
        home = vd / "Portfolio" / p["area"] / p["name"]
        if write_sidecar(p["path"], home, vd, args.write):
            enriched += 1

    gb = render_global_backlog(vd, projects)
    gm = render_global_maturity(vd, projects)
    gd = render_global_decisions(vd, projects)
    wrote_gb = wrote_gm = wrote_gd = False
    if args.write:
        wrote_gb = write_if_changed(vd / "Portfolio" / "global-backlog.md", gb)
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

    print(f"sidecars enriched: {enriched} | global-backlog written: {wrote_gb} | "
          f"global-maturity written: {wrote_gm} | global-decisions written: {wrote_gd} | "
          f"{biz_status} | {sec_status} | {'WRITE' if args.write else 'DRY-RUN'}")


if __name__ == "__main__":
    main()
