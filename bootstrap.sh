#!/usr/bin/env bash
# coder-plugins bootstrap
#
# Registers the three marketplaces this stack lives in and sets recommended
# enabledPlugins defaults in ~/.claude/settings.json. Idempotent: user values
# always win over the defaults this script provides, so re-running it after you
# customize settings does not clobber your choices.
#
# Usage:
#   bash <(curl -fsSL https://raw.githubusercontent.com/sureserverman/coder-plugins/main/bootstrap.sh)
# or locally:
#   ./bootstrap.sh

set -euo pipefail

SETTINGS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
SETTINGS_DIR="$(dirname "$SETTINGS")"

die() { echo "bootstrap: $*" >&2; exit 1; }
info() { echo "bootstrap: $*"; }

# --- preflight ---------------------------------------------------------------

command -v jq  >/dev/null || die "jq is required (apt install jq / brew install jq)"

mkdir -p "$SETTINGS_DIR"
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"

# Sanity: settings.json must be valid JSON or we refuse to touch it
jq -e . "$SETTINGS" >/dev/null || die "$SETTINGS is not valid JSON; refusing to modify"

# --- recommended defaults ----------------------------------------------------
#
# These are merged with `$defaults * $current` semantics in jq: every key the
# user already has wins. Adding a key here makes it the default for fresh
# installs; existing machines keep whatever the user already set.

DEFAULTS=$(cat <<'JSON'
{
  "extraKnownMarketplaces": {
    "coder-plugins": {
      "source": { "source": "github", "repo": "sureserverman/coder-plugins" }
    },
    "agent-tooling": {
      "source": { "source": "github", "repo": "sureserverman/agent-tooling" }
    },
    "obsidian-wiki": {
      "source": { "source": "github", "repo": "sureserverman/obsidian-wiki-plugin" },
      "autoUpdate": true
    },
    "sec-audit-marketplace": {
      "source": { "source": "github", "repo": "sureserverman/sec-audit" }
    }
  },
  "enabledPlugins": {
    "rust-dev@coder-plugins": true,
    "android-dev@coder-plugins": true,
    "git-github@coder-plugins": true,
    "release-promo@coder-plugins": true,
    "stingy-agents@coder-plugins": true,
    "browser-extensions@coder-plugins": true,
    "infra-build@coder-plugins": true,
    "planning@coder-plugins": true,
    "loadout@coder-plugins": true
  }
}
JSON
)

# --- backup ------------------------------------------------------------------

BACKUP="$SETTINGS.bak.$(date +%Y%m%d-%H%M%S)"
cp "$SETTINGS" "$BACKUP"
info "backup written to $BACKUP"

# --- merge -------------------------------------------------------------------
#
# jq's `*` operator does a recursive deep merge with the right-hand side
# winning. So `$defaults * $current` keeps every value the user has already
# set and only fills in gaps from $defaults.

jq --argjson defaults "$DEFAULTS" '$defaults * .' "$SETTINGS" > "$SETTINGS.tmp"
mv "$SETTINGS.tmp" "$SETTINGS"

info "merged recommended defaults into $SETTINGS"
info ""
info "Defaults applied for keys you did not already have:"
info "  - 4 marketplaces registered (coder-plugins, agent-tooling, obsidian-wiki, sec-audit-marketplace)"
info "  - 9 coder-plugins enabled (rust-dev, android-dev, git-github,"
info "    release-promo, stingy-agents, browser-extensions, infra-build, planning, loadout)"
info "  - agent-tooling (plugin-dev + platform siblings), obsidian-wiki, and"
info "    sec-audit-marketplace are registered but their plugins are not enabled —"
info "    flip them on per-machine with /plugin or per-project with /loadout once installed."
info ""
info "Restart Claude Code (or /reload-plugins in an active session) to apply."
