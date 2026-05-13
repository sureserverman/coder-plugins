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
    "obsidian-wiki": {
      "source": { "source": "github", "repo": "sureserverman/obsidian-wiki-plugin" },
      "autoUpdate": true
    },
    "sec-audit-marketplace": {
      "source": { "source": "github", "repo": "sureserverman/sec-audit" }
    }
  },
  "enabledPlugins": {
    "git-github@coder-plugins": true,
    "planning@coder-plugins": true,
    "plugin-dev@coder-plugins": true,
    "stingy-agents@coder-plugins": true,
    "loadout@coder-plugins": true,
    "rust-dev@coder-plugins": false,
    "android-dev@coder-plugins": false,
    "browser-extensions@coder-plugins": false,
    "release-promo@coder-plugins": false,
    "infra-build@coder-plugins": false,
    "obsidian-wiki@obsidian-wiki": false,
    "vault-context@obsidian-wiki": false,
    "sec-audit@sec-audit-marketplace": false
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
info "  - 3 marketplaces registered (coder-plugins, obsidian-wiki, sec-audit-marketplace)"
info "  - 5 always-on plugins enabled (git-github, planning, plugin-dev, stingy-agents, loadout)"
info "  - 8 plugins registered but disabled (enable per-project via /loadout or globally"
info "    via /plugin)"
info ""
info "Restart Claude Code (or /reload-plugins in an active session) to apply."
