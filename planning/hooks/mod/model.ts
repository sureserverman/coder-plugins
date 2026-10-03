// The mod's data layer: the render model plan-progress.py --json prints, held in
// $.state so every drawing that reads it redraws when it changes.
//
// The script is the one implementation of discovery, counting and grouping; this
// file only decides WHEN to run it. A drawing never runs it: a render hook that
// spawned a process would put a vault scan (BL-051's dead-mount stall) on the
// redraw path. Refreshes come from the three triggers below instead.

import { atom, update } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import type { PlanModel, PlanModelState } from '../../types'

export const MODEL = atom({ plugin: 'planning', key: 'model' } as const, null as PlanModelState | null)

const SCRIPT = 'skills/executing-plans/scripts/plan-progress.py'
const TIMEOUT_MS = 5000
const POLL_MS = 30000

// A tool call that can have changed what the model shows: the state file the
// executor mirrors, or a plan file whose Status markers the counts come from.
const PLAN_STATE = /(^|\/)\.claude\/plan-progress\.json$/
const PLAN_FILE = /-plan\.md$/
const MENTIONS = /\.claude\/plan-progress\.json|-plan\.md/

export function touchesPlanState(e: { tool: string; [k: string]: unknown }): boolean {
  const tool = String(e.tool)
  if (tool === 'Write' || tool === 'Edit' || tool === 'MultiEdit') {
    const path = typeof e.file_path === 'string' ? e.file_path : ''
    return PLAN_STATE.test(path) || PLAN_FILE.test(path)
  }
  if (tool === 'Bash') {
    return typeof e.command === 'string' && MENTIONS.test(e.command)
  }
  return false
}

function parseModel(stdout: string): PlanModel | null {
  try {
    const value = JSON.parse(stdout) as unknown
    if (value === null || typeof value !== 'object') return null
    const groups = (value as { groups?: unknown }).groups
    if (!Array.isArray(groups)) return null
    return value as PlanModel
  } catch {
    return null
  }
}

// One refresh at a time per module load: a trigger landing while one runs asks
// for exactly one more after it, never a pile of concurrent scans.
let running: Promise<void> | null = null
let again = false

export function refresh($: EngineInterface): Promise<void> {
  if (running !== null) {
    again = true
    return running
  }
  running = (async () => {
    do {
      again = false
      await refreshOnce($)
    } while (again)
  })().finally(() => {
    running = null
  })
  return running
}

async function refreshOnce($: EngineInterface): Promise<void> {
  let model: PlanModel | null = null
  try {
    const cwd = await $.session.cwd()
    const ran = await $.process.run(['python3', `${$.plugin.root}/${SCRIPT}`, '--json'], {
      cwd,
      stdin: JSON.stringify({ cwd, workspace: { current_dir: cwd } }),
      timeoutMs: TIMEOUT_MS,
    })
    if (ran.exitCode === 0) model = parseModel(ran.stdout)
  } catch {
    model = null
  }
  const fetchedAt = await $.clock.now()
  await update($, MODEL, previous =>
    model !== null
      ? { model, fetchedAt, stale: false }
      : { model: previous?.model ?? null, fetchedAt: previous?.fetchedAt ?? fetchedAt, stale: true },
  )
}

export function registerModel(on: On): void {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await refresh($)
    $.clock.every(POLL_MS, () => void refresh($))
    return started
  })

  on('tool.call', async ($, e, next) => {
    const result = await next(e)
    if (touchesPlanState(e)) await refresh($)
    return result
  })
}
