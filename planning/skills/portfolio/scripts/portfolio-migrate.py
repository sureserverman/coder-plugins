#!/usr/bin/env python3
"""portfolio-migrate — implements the `portfolio migrate` spec (copy→verify→delete).

Moves a project's operational docs from <repo>/docs/ into the vault at
<vault_dir>/Portfolio/<area>/<name>/. Vault is NOT git-tracked (NFS Obsidian),
so this is a filesystem copy with a sha256 verification gate, never git mv,
never a bare mv. The repo source is the LAST thing removed.

See planning/skills/portfolio/SKILL.md `### migrate` for the authoritative spec.

Usage:
  portfolio-migrate.py --project /home/user/dev/<area>/<name> [--write]
  portfolio-migrate.py --all [--write]
"""
import argparse, hashlib, shutil, subprocess, sys, yaml
from pathlib import Path

REGISTRY = Path.home() / ".claude" / "projects-registry.yaml"
CONFIG = Path.home() / ".claude" / "portfolio-config.yaml"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def vault_dir():
    cfg = yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}
    vd = cfg.get("vault_dir")
    if not vd:
        sys.exit("portfolio not configured: set vault_dir in ~/.claude/portfolio-config.yaml")
    return Path(vd)


def is_git(repo: Path) -> bool:
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def tracked_mods_in_set(repo: Path, rel_paths) -> list:
    """Return migrate-set files that are tracked AND have uncommitted modifications."""
    if not is_git(repo):
        return []
    out = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--", "docs/"],
                         capture_output=True, text=True).stdout
    dirty = []
    for line in out.splitlines():
        code, _, path = line[:2], line[2], line[3:]
        # tracked modification/staged-add: ' M', 'MM', 'M ', 'A ', 'AM', 'R '
        if code.strip() and code not in ("??",):
            if any(path == rp or path.startswith(rp.rstrip("/") + "/") for rp in rel_paths):
                dirty.append(path)
    return dirty


def migrate_set(repo: Path):
    """Return list of (src_abs, rel_under_home) for files to migrate.

    Plans go to plans/. backlog.md and MATURITY.md go to the home root.
    A backlog.md stashed inside docs/plans/ (some projects keep it there
    because docs/plans/ is gitignored) is treated as THE backlog, not a
    plan — destination is <home>/backlog.md, provided no root docs/backlog.md
    exists. Never migrate a *-done.md historical summary as an active plan
    (it still moves, but stays under plans/ with its name).
    """
    items = []
    plans = repo / "docs" / "plans"
    root_backlog = repo / "docs" / "backlog.md"
    stray_backlog = plans / "backlog.md"
    if plans.is_dir():
        # recurse so nested plan groups (e.g. plans/apple-container-migration/*.md)
        # migrate too, preserving their subdir structure under the vault plans/.
        for f in sorted(plans.rglob("*.md")):
            if f.name == "backlog.md" and f.parent == plans:
                continue  # top-level stray backlog handled below, not a plan
            rel = f.relative_to(plans)
            items.append((f, f"plans/{rel.as_posix()}"))
    # backlog: prefer root docs/backlog.md; else a stray docs/plans/backlog.md
    if root_backlog.is_file():
        items.append((root_backlog, "backlog.md"))
    elif stray_backlog.is_file():
        items.append((stray_backlog, "backlog.md"))
    mat = repo / "docs" / "MATURITY.md"
    if mat.is_file():
        items.append((mat, "MATURITY.md"))
    return items


def resolve_home(vd: Path, area: str, name: str) -> Path:
    return vd / "Portfolio" / area / name


def migrate_project(proj, vd: Path, write: bool):
    repo = Path(proj["path"])
    home = resolve_home(vd, proj["area"], proj["name"])
    label = f"{proj['area']}/{proj['name']}"
    items = migrate_set(repo)
    if not items:
        return ("skip", label, "nothing to migrate (no plans/backlog/MATURITY)")

    # Preflight: vault home already populated?
    for sub in ("plans", "backlog.md", "MATURITY.md"):
        if (home / sub).exists():
            return ("skip", label, "vault home already populated; resolve manually")

    # Dirty-guard: tracked modifications only (use ACTUAL repo-relative source paths)
    src_relpaths = [str(src.relative_to(repo)) for src, _ in items]
    dirty = tracked_mods_in_set(repo, src_relpaths)
    if dirty:
        return ("skip", label, f"tracked uncommitted modifications: {', '.join(dirty)}")

    gitrepo = is_git(repo)
    flag = "" if gitrepo else " [no-git-fallback]"

    if not write:
        dests = ", ".join(rel for _, rel in items)
        return ("dry", label, f"{len(items)} files → {home}{flag}  ({dests})")

    # COPY
    (home / "plans").mkdir(parents=True, exist_ok=True)
    copied = []
    try:
        for src, rel in items:
            dest = home / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append((src, dest, rel))
        # VERIFY (load-bearing gate)
        for src, dest, rel in copied:
            if sha256(src) != sha256(dest):
                raise RuntimeError(f"sha256 mismatch on {rel}")
    except Exception as e:
        # abort: delete partial vault copies, leave repo untouched
        for _, dest, _ in copied:
            dest.unlink(missing_ok=True)
        return ("fail", label, f"{e} — repo left intact, partial vault copy removed")

    # DELETE from repo (last). Prefer `git rm` for tracked files so the
    # deletion is in git history (archaeology fallback); fall back to plain
    # rm for gitignored/untracked files (e.g. a gitignored docs/plans/) and
    # non-git repos — there the vault copy is the only copy.
    for src, _, rel in copied:
        removed = False
        if gitrepo:
            r = subprocess.run(["git", "-C", str(repo), "rm", "-q", "--", str(src.relative_to(repo))],
                               capture_output=True, text=True)
            removed = (r.returncode == 0)
        if not removed:
            src.unlink(missing_ok=True)
    # remove docs/plans if empty, then docs/ if empty
    pld = repo / "docs" / "plans"
    if pld.is_dir() and not any(pld.iterdir()):
        pld.rmdir()
    dd = repo / "docs"
    if dd.is_dir() and not any(dd.iterdir()):
        dd.rmdir()

    # step 7: record portfolio_home in the repo sidecar (create if absent)
    write_sidecar_home(repo, home)
    # step 8: rewrite migrated MATURITY.md auto-evidence with repo: prefix
    rewrite_maturity_evidence(home / "MATURITY.md")

    return ("ok", label, f"migrated {len(copied)} files → {home}{flag}")


SIDECAR_BEGIN = "<!-- PORTFOLIO-STATUS-BEGIN — managed by /planning:portfolio rebuild; do not hand-edit -->"
SIDECAR_END = "<!-- PORTFOLIO-STATUS-END -->"


def write_sidecar_home(repo: Path, home: Path):
    """Ensure .claude/vault-context.md carries portfolio_home in the managed block.
    Creates a minimal sidecar if none exists. Idempotent. Full enrichment
    (counts/impacts/debt) happens later in the portfolio rebuild (Stage 7)."""
    sc = repo / ".claude" / "vault-context.md"
    sc.parent.mkdir(parents=True, exist_ok=True)
    block = (f"{SIDECAR_BEGIN}\n## Portfolio status\n\n"
             f"- **Home:** `{home}`   (plans/backlog/maturity live here, not in this repo's docs/)\n"
             f"{SIDECAR_END}")
    if sc.exists():
        cur = sc.read_text()
        import re as _re
        if SIDECAR_BEGIN in cur and SIDECAR_END in cur:
            new = _re.sub(_re.escape(SIDECAR_BEGIN) + r".*?" + _re.escape(SIDECAR_END),
                          block, cur, count=1, flags=_re.DOTALL)
        else:
            new = cur.rstrip("\n") + "\n\n" + block + "\n"
        if new != cur:
            sc.write_text(new)
    else:
        sc.write_text(f"# Vault context for {repo.name}\n\n{block}\n")


def rewrite_maturity_evidence(mat: Path):
    """Rewrite `auto:<path>` → `auto:repo:<path>` for repo-relative evidence,
    so the vault checklist makes clear the evidence lives in the repo.
    Idempotent: skips already-prefixed `auto:repo:` lines. Leaves http(s) and
    sec-audit-report (repo-root) evidence as repo: too."""
    if not mat.is_file():
        return
    import re as _re
    out = []
    changed = False
    for line in mat.read_text().splitlines():
        m = _re.match(r"^(\s*-\s*\[x\]\s*auto:)(?!repo:)(.+)$", line)
        if m:
            out.append(f"{m.group(1)}repo:{m.group(2)}")
            changed = True
        else:
            out.append(line)
    if changed:
        mat.write_text("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--project")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    vd = vault_dir()
    reg = yaml.safe_load(REGISTRY.read_text())
    projects = [p for p in reg["projects"] if p.get("enabled", True)]
    if args.project:
        pr = str(Path(args.project))
        projects = [p for p in projects if p["path"] == pr]
        if not projects:
            sys.exit(f"not in registry: {pr}")

    counts = {"ok": 0, "dry": 0, "skip": 0, "fail": 0}
    for proj in projects:
        status, label, msg = migrate_project(proj, vd, args.write)
        counts[status] += 1
        print(f"[{status.upper():4}] {label}: {msg}")
    print(f"\n{'WRITE' if args.write else 'DRY-RUN'} summary: "
          f"migrated={counts['ok']} dry={counts['dry']} skipped={counts['skip']} failed={counts['fail']}")
    return 1 if counts["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
