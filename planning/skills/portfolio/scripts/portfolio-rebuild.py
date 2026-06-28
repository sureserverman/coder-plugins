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
import re, sys, yaml, datetime
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


def write_if_changed(path, content):
    def strip_ts(s): return re.sub(r"\n\*\*Last rebuilt:\*\*[^\n]*\n", "\nTS\n", s)
    if path.exists() and strip_ts(path.read_text()) == strip_ts(content):
        return False
    path.write_text(content)
    return True


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
    wrote_gb = wrote_gm = False
    if args.write:
        wrote_gb = write_if_changed(vd / "Portfolio" / "global-backlog.md", gb)
        wrote_gm = write_if_changed(vd / "Portfolio" / "global-maturity.md", gm)

    print(f"sidecars enriched: {enriched} | global-backlog written: {wrote_gb} | "
          f"global-maturity written: {wrote_gm} | {'WRITE' if args.write else 'DRY-RUN'}")


if __name__ == "__main__":
    main()
