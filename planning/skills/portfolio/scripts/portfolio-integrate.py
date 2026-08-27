#!/usr/bin/env python3
"""portfolio-integrate — implements `portfolio integrate`.

Reads every <vault>/Portfolio/<area>/<name>/integration.md, builds
Portfolio/integration-graph.md (adjacency + symmetry check), and rolls up
every `integration`-tagged backlog entry into Portfolio/integration-backlog.md.

Symmetry rule: if A declares `impacts: [[B]]`, B must declare `depends_on: [[A]]`
(and vice-versa). Asymmetries are reported under `## Asymmetries (review)` and
NEVER auto-fixed. Dangling targets (not a registered project) are flagged.

See references/integration-format.md for the per-project file schema.
"""
import importlib.util, re, sys, yaml, datetime
from pathlib import Path

# `write_if_changed` is portfolio-rebuild.py's, and it is imported rather than
# copied because it carries a CONTRACT, not just three lines: regenerate the
# document, strip the `**Last rebuilt:**` line, and write only if the rest
# differs. Both roll-ups here embed that timestamp, so without it every run
# rewrote both files — on an NFS-backed Obsidian vault that is not git-tracked,
# where a needless write means sync churn and conflict copies, and where an
# unchanged mtime is the operator's only "nothing moved" signal. A second copy
# of the function would be a second place for that contract to drift. Hyphenated
# filename → importlib, the same mechanism and the same reasoning as
# compass-scan.py's reuse of the plan parser and the decisions register.
_REBUILD = Path(__file__).resolve().parent / "portfolio-rebuild.py"
_spec = importlib.util.spec_from_file_location("portfolio_rebuild", _REBUILD)
_pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pr)
write_if_changed = _pr.write_if_changed

REGISTRY = Path.home() / ".claude" / "projects-registry.yaml"
CONFIG = Path.home() / ".claude" / "portfolio-config.yaml"
TODAY = datetime.date.today().isoformat()
WIKI = re.compile(r"\[\[([^\]]+)\]\]")


def vault_dir():
    cfg = yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}
    vd = cfg.get("vault_dir")
    if not vd:
        sys.exit("portfolio not configured: set vault_dir in ~/.claude/portfolio-config.yaml")
    # Set-but-missing `vault_dir` is REFUSED, never created (SKILL.md § Resolver);
    # rationale in portfolio-rebuild.py's vault_dir(). This file already imports
    # that module for write_if_changed, so it borrows the check rather than
    # keeping a fourth copy of the wording the class test pins.
    return _pr.require_vault(Path(vd).expanduser(), CONFIG)


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def edge_targets(lst):
    out = []
    for e in (lst or []):
        if isinstance(e, dict):
            t = e.get("target", "")
            why = e.get("why", "")
        else:
            t, why = str(e), ""
        m = WIKI.search(t)
        out.append((m.group(1) if m else t.strip(), why))
    return out


def build_graph(vd, registered_names):
    depends, impacts = {}, {}   # name -> [(target, why)]
    for f in sorted((vd / "Portfolio").rglob("integration.md")):
        fm = parse_frontmatter(f.read_text(errors="ignore"))
        name = fm.get("project") or f.parent.name
        depends[name] = edge_targets(fm.get("depends_on"))
        impacts[name] = edge_targets(fm.get("impacts"))

    # symmetry + dangling checks
    asymmetries, dangling = [], []
    for a, deps in depends.items():
        for (b, why) in deps:
            if b not in registered_names:
                dangling.append(f"{a} depends_on [[{b}]] — unresolved target (not a registered project)")
            elif a not in [t for (t, _) in impacts.get(b, [])]:
                asymmetries.append(f"{a} depends_on [[{b}]], but [[{b}]] does not list `impacts: [[{a}]]`")
    for a, imps in impacts.items():
        for (b, why) in imps:
            if b not in registered_names:
                dangling.append(f"{a} impacts [[{b}]] — unresolved target (not a registered project)")
            elif a not in [t for (t, _) in depends.get(b, [])]:
                asymmetries.append(f"{a} impacts [[{b}]], but [[{b}]] does not list `depends_on: [[{a}]]`")
    return depends, impacts, sorted(set(asymmetries)), sorted(set(dangling))


def render_graph(depends, impacts, asymmetries, dangling):
    L = ["# Integration Graph", "",
         "Auto-generated from every `Portfolio/<area>/<project>/integration.md` by",
         "`/planning:portfolio integrate`. Edges are declared per-project and",
         "symmetry-checked here. Do not hand-edit — edit the per-project files.", "",
         f"**Last rebuilt:** {TODAY}", "", "---", "", "## Edges (depends_on → upstream)", ""]
    for a in sorted(depends):
        for (b, why) in depends[a]:
            L.append(f"- `{a}` → `{b}`  — {why}")
    L += ["", "## Asymmetries (review)", ""]
    if asymmetries:
        L += [f"- ⚠ {x}" for x in asymmetries]
    else:
        L.append("_None — every declared edge is reciprocated._")
    if dangling:
        L += ["", "## Unresolved targets", ""] + [f"- ❓ {x}" for x in dangling]
    L.append("")
    return "\n".join(L)


def rollup_integration_backlog(vd):
    """Scan every project backlog for integration-tagged entries; group by edge."""
    rows = []  # (edge, project, bl_id, title)
    for bl in sorted((vd / "Portfolio").rglob("backlog.md")):
        proj = bl.parent.name
        text = bl.read_text(errors="ignore")
        for block in re.findall(r"^## (BL-\d+) — (.+?)\n(.*?)(?=^## BL-|\Z)", text, re.S | re.M):
            bid, title, body = block
            if re.search(r"^\s*-?\s*\*?\*?Tags:\*?\*?.*\bintegration\b", body, re.M) or \
               re.search(r"^\s*-?\s*\*?\*?Integration:\*?\*?", body, re.M):
                em = re.search(r"edge=([^\s]+)|plan=([^\s]+)", body)
                edge = (em.group(1) or em.group(2)) if em else "unspecified"
                rows.append((edge, proj, bid, title.strip()))
    L = ["# Integration Backlog", "",
         "Every `integration`-tagged backlog item across all projects, grouped by",
         "edge. Auto-generated by `/planning:portfolio integrate`. The items live in",
         "their project's own backlog; this is a cross-project rollup view.", "",
         f"**Last rebuilt:** {TODAY}", "", "---", ""]
    if not rows:
        L += ["_No integration-tagged backlog items yet._", ""]
    else:
        by_edge = {}
        for edge, proj, bid, title in rows:
            by_edge.setdefault(edge, []).append((proj, bid, title))
        for edge in sorted(by_edge):
            L.append(f"## edge: {edge}")
            L.append("")
            for proj, bid, title in by_edge[edge]:
                L.append(f"- `{proj}` {bid} — {title}")
            L.append("")
    return "\n".join(L), len(rows)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    vd = vault_dir()
    reg = yaml.safe_load(REGISTRY.read_text())
    names = {p["name"] for p in reg["projects"]}

    depends, impacts, asym, dangling = build_graph(vd, names)
    graph_md = render_graph(depends, impacts, asym, dangling)
    ibl_md, n_items = rollup_integration_backlog(vd)

    n_edges = sum(len(v) for v in depends.values())
    print(f"edges: {n_edges} | asymmetries: {len(asym)} | dangling: {len(dangling)} | integration-backlog items: {n_items}")
    for x in asym:
        print(f"  ⚠ {x}")
    if args.write:
        # Reported per file, and "unchanged" is reported as loudly as "wrote":
        # the old line claimed both files were written unconditionally, which
        # was true only because they unconditionally were. A run that says it
        # wrote nothing is the evidence that the no-change path is live.
        wrote, same = [], []
        for fn, body in (("integration-graph.md", graph_md),
                         ("integration-backlog.md", ibl_md)):
            (wrote if write_if_changed(vd / "Portfolio" / fn, body) else same).append(fn)
        print(f"wrote: {', '.join(wrote) or 'nothing'} | "
              f"unchanged: {', '.join(same) or 'nothing'}")
    else:
        print("(dry-run — pass --write to persist)")


if __name__ == "__main__":
    main()
