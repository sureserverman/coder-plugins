#!/usr/bin/env python3
"""One-line warning when a script runs from a plugin cache the checkout has moved past.

Claude Code installs plugins into `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`
and keeps every version it has ever installed side by side — this machine currently
carries seven `planning/` trees, 0.8.1 through 0.43.1. Nothing pins which one a
`/planning:portfolio` invocation resolves to, so a script can legitimately be running
from a version whose bug was fixed in the checkout weeks ago. The failure is silent and
self-concealing: the stale copy behaves exactly as its own tests said it should, and the
operator reads a correct-looking result produced by superseded code.

So this is a **diagnostic, never a control**. It writes one line to stderr and returns;
it never exits and never changes what the caller computes. It has exactly one side
effect, and it is about the warning rather than the work: having warned, it sets
`PORTFOLIO_NO_STALE_WARNING` in its own environment so child processes carrying the same
probe stay quiet — see `warn_if_stale`. Every failure
mode — no registry, no checkout, unreadable manifest, unparseable version, not running
from a cache at all — degrades to silence, because a broken staleness probe must not be
able to take down a portfolio run. That asymmetry is deliberate: a missed warning costs
one confusing session, while a probe that raises costs the command.

**stderr, not stdout, is load-bearing.** `compass-scan.py` and `security-scan.py` emit a
single JSON document on stdout that other tools parse. A warning printed there would not
be a nuisance; it would be a syntax error in someone else's input.

DEC-011 governs the lookup: `~/.claude/projects-registry.yaml` is consulted **only** to
resolve the marketplace's repo path, which is precisely the use that decision reserves to
it. The version comparison itself reads the checkout's own `.claude-plugin/marketplace.json`
— the same manifest `scripts/check-version-mirrors.py` treats as a mirror site — so this
never invents a second opinion about what version a plugin is.
"""
import json
import os
import sys
from pathlib import Path


def _cache_coords(path):
    """(marketplace, plugin, version) if `path` sits inside a plugin cache, else None.

    Matched structurally — `.../plugins/cache/<marketplace>/<plugin>/<version>/...` — rather
    than by matching `~/.claude`, because the plugin root is relocatable (CLAUDE_CONFIG_DIR)
    and a probe keyed to one hardcoded home would report "not cached" on exactly the machines
    that relocated it, which is the silent-false-negative this file exists to avoid.
    """
    parts = path.parts
    for i in range(len(parts) - 4):
        if parts[i] == "plugins" and parts[i + 1] == "cache":
            return parts[i + 2], parts[i + 3], parts[i + 4]
    return None


def _version_tuple(s):
    """(1, 2, 3) from "1.2.3", or None if it is not a plain dotted-numeric version.

    None means "cannot compare", and every caller treats that as silence. Guessing an
    ordering for a version this does not understand would produce a warning whose
    direction is unknown — worse than no warning, because the operator would act on it.
    """
    parts = str(s).split(".")
    if not (1 <= len(parts) <= 4):
        return None
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    # Padded to a fixed width, because Python compares tuples lexicographically and
    # therefore reads (0, 44) < (0, 44, 0) — "0.44" and "0.44.0" are the same version
    # and would otherwise compare unequal, in the direction that invents a warning.
    # Padding rather than refusing on a length mismatch: "0.44" IS 0.44.0, so the
    # comparison is knowable, and this function's rule is to stay silent only when
    # the ordering is genuinely unknown.
    return tuple(nums + [0] * (4 - len(nums)))


def _default_registry():
    """The registry path, honouring CLAUDE_CONFIG_DIR.

    `_cache_coords` above deliberately refuses to anchor on `~/.claude` because the
    plugin root is relocatable — and this function used to hardcode exactly that
    path two steps later, so on a machine that HAD relocated, the cache was
    recognised and then the registry was looked for in the wrong home. The probe
    went silent on precisely the configuration the structural match exists to
    support: the argument was sound and the code did not follow it. Same
    `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` form bootstrap.sh:16 already uses.
    """
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    return (Path(base) if base else Path.home() / ".claude") / "projects-registry.yaml"


def _registry_path(marketplace, registry):
    """Repo path for `marketplace` per the registry, or None. Read-only, never written."""
    try:
        import yaml
        reg = yaml.safe_load(Path(registry).read_text()) or {}
    except Exception:
        return None
    if not isinstance(reg, dict):
        return None
    for proj in reg.get("projects") or []:
        if isinstance(proj, dict) and proj.get("name") == marketplace:
            p = proj.get("path")
            return Path(p).expanduser() if p else None
    return None


def _manifest_version(checkout, plugin):
    """`plugin`'s version in the checkout's marketplace.json, or None."""
    try:
        doc = json.loads((checkout / ".claude-plugin" / "marketplace.json")
                         .read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(doc, dict):
        return None
    for entry in doc.get("plugins") or []:
        if isinstance(entry, dict) and entry.get("name") == plugin:
            return entry.get("version")
    return None


def warn_if_stale(script, registry=None, stream=None):
    """Print one stderr line if `script` runs from a cache the checkout has moved past.

    Returns the message it printed, or None. The return value exists for the tests —
    callers are expected to ignore it, and nothing about this function's result may
    change what a caller does.
    """
    stream = stream or sys.stderr
    if os.environ.get("PORTFOLIO_NO_STALE_WARNING"):
        # An operator deliberately running an old cache (bisecting a regression, or
        # reproducing a report against the version that produced it) should not be
        # nagged on every invocation of every subcommand.
        return None
    try:
        coords = _cache_coords(Path(script).resolve())
        if coords is None:
            return None                      # running from a checkout: nothing to compare
        marketplace, plugin, running = coords
        running_v = _version_tuple(running)
        if running_v is None:
            return None
        checkout = _registry_path(marketplace, registry or _default_registry())
        if checkout is None or not checkout.is_dir():
            return None                      # unregistered or absent: not this tool's problem
        latest = _manifest_version(checkout, plugin)
        latest_v = _version_tuple(latest)
        if latest_v is None or latest_v <= running_v:
            # `<=`, so a checkout BEHIND the cache stays silent. That is a real state —
            # a dev branch reverted, a machine mid-rebase — and it is not staleness.
            return None
        msg = (f"warning: running {plugin} {running} from the plugin cache, but "
               f"{checkout} has {latest}. Re-add the marketplace to pick it up, or set "
               f"PORTFOLIO_NO_STALE_WARNING=1 to silence this.")
        print(msg, file=stream)
        # Silence descendants. `portfolio-rebuild --write` forks four children —
        # `security-scan`, `security-rollup`, `business-scan`, `business-rollup` —
        # and `compass-scan` forks `business-scan`. Of those, the two security
        # scripts carry this probe and would otherwise repeat the identical line,
        # so one `portfolio rebuild` printed it three times (self plus two). The
        # child processes inherit os.environ, so setting the opt-out here makes
        # the warning per USER INVOCATION rather than per process, which is what
        # the operator experiences it as. Deliberately a mutation in an otherwise
        # side-effect-free probe: the alternative is every caller remembering to
        # pass a suppressed env to every subprocess it spawns, which is the kind
        # of thing that is correct on the day it is written and wrong six months
        # later when someone adds a fourth subprocess.
        #
        # NOT covered, stated rather than implied: `business/scripts/business-scan.py`
        # and `business-rollup.py` carry no probe. They sit under the same
        # per-version cache hazard and are spawned from the same command paths, so
        # this is a real gap and not a judgement that they are safe — but `business`
        # is a separately versioned plugin that cannot import this module (from a
        # cache install the two live in sibling version trees), so covering it means
        # its own copy comparing its own version. Out of Task 4.4's scope
        # ("portfolio/compass entry-point scripts"); recorded to the backlog rather
        # than described away. This suppression still reaches them — they inherit
        # the variable — so they stay quiet; they simply never speak in the first
        # place.
        os.environ["PORTFOLIO_NO_STALE_WARNING"] = "1"
        return msg
    except Exception:
        # Belt and braces over the per-step guards above: this probe is never worth
        # a traceback in a command that was otherwise going to succeed.
        return None
