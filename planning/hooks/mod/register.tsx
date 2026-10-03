// The planning plugin's hooks module (Claude Code 2.1.288+). It is the Claude Code
// layer over the shared Python scripts under ../../skills/executing-plans/scripts/:
// it gathers inputs and draws, and never reimplements rendering, classification or
// a verdict. Hosts without mods keep using the scripts directly.

import type { Register } from 'claude-code'

export const register: Register = on => {
  on('session.start', ($, e, next) => next(e))
}
