#!/usr/bin/env python3
"""loadout — per-project + per-task plugin scoping for Claude Code.

Computes `enabledPlugins` from layered profiles and writes the result to the
project's `.claude/settings.local.json`. Sticky state (current tech baseline +
active task overlays) lives in `.claude/loadout.json` so it survives sessions.

Profile resolution order (later wins on conflict, but plugins are union-merged):
  1. bundled profiles under   <plugin_root>/profiles/
  2. user overrides under     ~/.claude/loadouts/

Commands:
  show              — print current loadout
  list              — print available profiles
  set <tech>        — set sticky tech baseline for this project
  add <task>        — add a task overlay
  remove <task>     — remove a task overlay
  clear             — drop all task overlays (keep tech)
  reset             — drop tech baseline AND overlays
  detect            — auto-pick a tech baseline from cwd signals (no-op if already set)
  unpin [--dry-run] — remove this project's local install records that a user-scope
                      install makes redundant, then re-apply the loadout
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable

HOME = Path(os.environ.get("HOME", "~")).expanduser()
GLOBAL_SETTINGS = HOME / ".claude" / "settings.json"
USER_PROFILES = HOME / ".claude" / "loadouts"
BUNDLED_PROFILES = Path(__file__).resolve().parent.parent / "profiles"
INSTALLED_PLUGINS = HOME / ".claude" / "plugins" / "installed_plugins.json"

STATE_FILE = ".claude/loadout.json"
SETTINGS_LOCAL = ".claude/settings.local.json"


# ── filesystem helpers ────────────────────────────────────────────────────────
def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")


# ── profile loading ───────────────────────────────────────────────────────────
def load_profile(category: str, name: str) -> dict | None:
    """Look up <category>/<name>.json under user overrides first, then bundled."""
    for root in (USER_PROFILES, BUNDLED_PROFILES):
        path = root / category / f"{name}.json"
        if path.is_file():
            return read_json(path)
    return None


def load_always_on() -> set[str]:
    plugins: set[str] = set()
    for root in (BUNDLED_PROFILES, USER_PROFILES):
        prof = read_json(root / "always-on.json")
        plugins.update(prof.get("plugins", []))
    return plugins


def list_profiles(category: str) -> list[str]:
    names: set[str] = set()
    for root in (BUNDLED_PROFILES, USER_PROFILES):
        d = root / category
        if d.is_dir():
            names.update(p.stem for p in d.glob("*.json"))
    return sorted(names)


# ── state ─────────────────────────────────────────────────────────────────────
def load_state(project: Path) -> dict:
    s = read_json(project / STATE_FILE)
    s.setdefault("tech", None)
    s.setdefault("task_overlays", [])
    return s


def save_state(project: Path, state: dict) -> None:
    write_json(project / STATE_FILE, state)


# ── core: compute and write enabledPlugins ────────────────────────────────────
def installed_keys() -> list[str]:
    data = read_json(INSTALLED_PLUGINS)
    return sorted((data.get("plugins") or {}).keys())


def user_settings_on() -> set[str]:
    """Plugins the user-scope settings.json turns on."""
    plugins = read_json(GLOBAL_SETTINGS).get("enabledPlugins") or {}
    return {k for k, v in plugins.items() if v is True}


def user_installed() -> set[str]:
    """Plugins with a user-scope install record."""
    plugins = read_json(INSTALLED_PLUGINS).get("plugins") or {}
    return {k for k, entries in plugins.items()
            if any(e.get("scope") == "user" for e in entries)}


def user_enabled() -> set[str]:
    """Plugins the user scope loads: turned on in user settings AND installed
    there. A user setting alone is not enough -- with no user-scope install
    there is nothing for a project that omits the plugin to load."""
    return user_settings_on() & user_installed()


def loadout_union(state: dict) -> set[str]:
    """Union of always-on ∪ tech ∪ task overlays."""
    enabled: set[str] = set(load_always_on())

    tech = state.get("tech")
    if tech:
        prof = load_profile("tech", tech)
        if prof:
            enabled.update(prof.get("plugins", []))

    for task in state.get("task_overlays", []):
        prof = load_profile("task", task)
        if prof:
            enabled.update(prof.get("plugins", []))
    return enabled


def compute_enabled(state: dict) -> dict[str, bool]:
    """The map written to settings.local.json (DEC-030).

    Every installed plugin outside the loadout → false, so the loadout fully
    scopes the session. A loadout plugin the user scope already enables is
    omitted: a local `true` makes Claude Code pin the plugin's version in a
    local install record that nothing refreshes. Only a loadout plugin the user
    scope leaves off is written true, because nothing else turns it on.
    """
    enabled = loadout_union(state)
    on_for_user = user_enabled()
    result: dict[str, bool] = {}
    for key in installed_keys():
        if key not in enabled:
            result[key] = False
    for key in sorted(enabled - on_for_user):
        result[key] = True
    return result


def display_map(state: dict) -> dict[str, bool]:
    """What the session loads: the whole loadout on, the written falses off."""
    shown = {k: v for k, v in compute_enabled(state).items() if not v}
    shown.update({k: True for k in loadout_union(state)})
    return shown


def apply(project: Path, state: dict) -> dict[str, bool]:
    enabled_map = compute_enabled(state)
    installed_for_user = user_installed()
    for key in sorted(k for k, v in enabled_map.items() if v):
        why = "is off in user settings" if key in installed_for_user else "has no user-scope install"
        print(f"loadout: {key} {why}; enabling it here pins its version", file=sys.stderr)
    settings_path = project / SETTINGS_LOCAL
    settings = read_json(settings_path)
    settings["enabledPlugins"] = enabled_map
    write_json(settings_path, settings)
    save_state(project, state)
    return display_map(state)


# ── unpin ─────────────────────────────────────────────────────────────────────
def local_records(project: Path) -> tuple[list[str], list[str]]:
    """This project's local install records, split into (redundant, local_only).

    Redundant: the same plugin also has a user-scope install, so removing the
    local record lets the project load the user's (current) version. Local-only:
    no user-scope install exists, so removing it would take the plugin away.
    """
    plugins = read_json(INSTALLED_PLUGINS).get("plugins") or {}
    redundant: list[str] = []
    local_only: list[str] = []
    for key, entries in sorted(plugins.items()):
        mine = any(
            e.get("scope") == "local"
            and e.get("projectPath")
            and Path(e["projectPath"]).resolve() == project
            for e in entries
        )
        if not mine:
            continue
        if any(e.get("scope") == "user" for e in entries):
            redundant.append(key)
        else:
            local_only.append(key)
    return redundant, local_only


def unpin(project: Path, dry_run: bool) -> int:
    redundant, local_only = local_records(project)
    for key in redundant:
        print(f"{'would unpin' if dry_run else 'unpin'}: {key}")
    for key in local_only:
        print(f"kept (no user-scope install): {key}")
    if dry_run:
        return 0
    failed: list[str] = []
    for key in redundant:
        # A local record belongs to the project it was made in, so the
        # uninstall runs from there.
        r = subprocess.run(
            ["claude", "plugin", "uninstall", key, "--scope", "local"], cwd=project
        )
        if r.returncode != 0:
            failed.append(key)
            print(f"loadout: uninstall of {key} failed (exit {r.returncode})", file=sys.stderr)
    if (project / STATE_FILE).exists():
        apply(project, load_state(project))
    return 1 if failed else 0


# ── auto-detect ───────────────────────────────────────────────────────────────
def detect_tech(project: Path) -> str | None:
    """Pick a tech profile from filesystem signals. First match wins."""
    rules: list[tuple[str, Iterable[str]]] = [
        ("rust", ["Cargo.toml"]),
        ("android", ["build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"]),
        ("web-ext", ["manifest.json"]),  # weak — could collide with other manifests
        ("python", ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"]),
        ("plugin-dev", [".claude-plugin/marketplace.json", ".claude-plugin/plugin.json"]),
        ("docs", ["mkdocs.yml", "docusaurus.config.js", "docusaurus.config.ts"]),
    ]
    # manifest.json is too generic at repo root; require it to be a WebExtension
    for tech, files in rules:
        for f in files:
            p = project / f
            if not p.is_file():
                continue
            if tech == "web-ext":
                try:
                    data = json.loads(p.read_text())
                    if not isinstance(data, dict) or "manifest_version" not in data:
                        continue
                except (json.JSONDecodeError, OSError):
                    continue
            return tech
    return None


# ── pretty printing ───────────────────────────────────────────────────────────
def fmt_show(project: Path, state: dict, enabled: dict[str, bool]) -> str:
    on = sorted(k for k, v in enabled.items() if v)
    off = sorted(k for k, v in enabled.items() if not v)
    lines = [
        f"loadout @ {project}",
        f"  tech baseline : {state.get('tech') or '(none — run /loadout set <tech>)'}",
        f"  task overlays : {', '.join(state.get('task_overlays') or []) or '(none)'}",
        "",
        f"  enabled ({len(on)}):",
    ]
    lines += [f"    + {k}" for k in on]
    lines += ["", f"  disabled ({len(off)}):"]
    lines += [f"    - {k}" for k in off]
    lines += [
        "",
        "  NOTE: changes take effect on next session start. Run /clear or restart.",
    ]
    return "\n".join(lines)


def fmt_list() -> str:
    tech = list_profiles("tech")
    task = list_profiles("task")
    lines = ["available profiles:", "", "  tech (sticky baseline — pick one):"]
    lines += [f"    {name}" for name in tech]
    lines += ["", "  task (overlays — combine freely):"]
    lines += [f"    {name}" for name in task]
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────
def main(argv: list[str]) -> int:
    project_env = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("PWD") or "."
    project = Path(project_env).resolve()

    args = argv[1:]
    cmd = args[0] if args else "show"

    if cmd in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    if cmd == "list":
        print(fmt_list())
        return 0

    state = load_state(project)

    if cmd == "show":
        enabled = display_map(state)
        print(fmt_show(project, state, enabled))
        return 0

    if cmd == "set":
        if len(args) < 2:
            print("usage: loadout set <tech>", file=sys.stderr)
            return 2
        tech = args[1]
        if not load_profile("tech", tech):
            print(f"unknown tech profile: {tech}", file=sys.stderr)
            print(fmt_list(), file=sys.stderr)
            return 2
        state["tech"] = tech
        enabled = apply(project, state)
        print(f"tech baseline → {tech}")
        print(fmt_show(project, state, enabled))
        return 0

    if cmd == "add":
        if len(args) < 2:
            print("usage: loadout add <task>", file=sys.stderr)
            return 2
        task = args[1]
        if not load_profile("task", task):
            print(f"unknown task profile: {task}", file=sys.stderr)
            print(fmt_list(), file=sys.stderr)
            return 2
        if task not in state["task_overlays"]:
            state["task_overlays"].append(task)
        enabled = apply(project, state)
        print(f"+ task overlay: {task}")
        print(fmt_show(project, state, enabled))
        return 0

    if cmd == "remove":
        if len(args) < 2:
            print("usage: loadout remove <task>", file=sys.stderr)
            return 2
        task = args[1]
        if task in state["task_overlays"]:
            state["task_overlays"].remove(task)
            enabled = apply(project, state)
            print(f"- task overlay: {task}")
            print(fmt_show(project, state, enabled))
        else:
            print(f"overlay not active: {task}", file=sys.stderr)
            return 1
        return 0

    if cmd == "clear":
        state["task_overlays"] = []
        enabled = apply(project, state)
        print("cleared all task overlays")
        print(fmt_show(project, state, enabled))
        return 0

    if cmd == "reset":
        # Drop tech + overlays. Also remove enabledPlugins from settings.local.json
        # so the global settings.json takes back over.
        settings_path = project / SETTINGS_LOCAL
        settings = read_json(settings_path)
        settings.pop("enabledPlugins", None)
        if settings:
            write_json(settings_path, settings)
        elif settings_path.exists():
            settings_path.unlink()
        state_path = project / STATE_FILE
        if state_path.exists():
            state_path.unlink()
        print("reset: project now inherits global enabledPlugins")
        return 0

    if cmd == "unpin":
        return unpin(project, dry_run="--dry-run" in args[1:])

    if cmd == "detect":
        if state.get("tech"):
            print(f"tech already set: {state['tech']} (use /loadout set <tech> to change)")
            return 0
        tech = detect_tech(project)
        if not tech:
            print("no tech signal detected at this project root")
            return 1
        state["tech"] = tech
        enabled = apply(project, state)
        print(f"auto-detected tech baseline → {tech}")
        print(fmt_show(project, state, enabled))
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
