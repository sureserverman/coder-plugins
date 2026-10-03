// The plan pane: the whole executing plan — its master, its stages with their
// gates, every task with its status — and the agents this session has dispatched.
// Opened only by the person (/plan-view or the band's Plan button), never unasked.
// It draws planning.model.detail, which plan-progress.py --json parsed with the
// same regexes as the bar, and planning.agents.

import { atom, read } from 'claude-code'
import type { On } from 'claude-code'

import type { AgentRecord, PlanGroup, PlanModelState, PlanTask } from '../../types'
import { PLAN_PANE, PLAN_PANE_TITLE } from './pane-id'

// Declared in each file that reads them: the engine's scan lists a module's state
// reads from atoms written in the reading file itself.
const MODEL = atom({ plugin: 'planning', key: 'model' } as const, null as PlanModelState | null)
const AGENTS = atom({ plugin: 'planning', key: 'agents' } as const, [] as AgentRecord[])

// C0, DEL and C1 (U+0080-U+009F, among them U+009B, a one-byte CSI).
const CONTROL = /[\x00-\x1f\x7f-\x9f]/g

const GLYPH: Record<string, string> = { done: '✔', partial: '◐', open: '○' }

const OUTCOME: Record<string, string> = { running: '◌', done: '✔', failed: '✘', denied: '⊘' }

function plain(s: unknown): string {
  return typeof s === 'string' ? s.replace(CONTROL, '') : ''
}

function clip(text: string, width: number): string {
  const cells = [...text]
  if (cells.length <= width) return text
  return width <= 1 ? cells.slice(0, Math.max(0, width)).join('') : `${cells.slice(0, width - 1).join('')}…`
}

function counts(g: PlanGroup): string {
  return g.total > 0 ? ` ${g.done}/${g.total}` : ''
}

function taskLine(t: PlanTask, current: string | null): string {
  const mark = current !== null && t.id === current ? '▶' : ' '
  return `${mark} ${GLYPH[t.status ?? ''] ?? '·'} ${plain(t.id)} ${plain(t.title)}`
}

type Line = { text: string; bold?: boolean; dim?: boolean; colour?: string }

export function paneLines(state: PlanModelState | null, agents: AgentRecord[]): Line[] {
  const groups = state?.model?.groups ?? []
  const pinned = groups.find(g => g.role === 'pinned')
  const detail = state?.model?.detail ?? null
  if (pinned === undefined && detail === null) return [{ text: 'No plan is executing.', dim: true }]

  const lines: Line[] = []
  const master = groups.find(g => g.role === 'master' && (pinned?.depth ?? 0) > 0)
  if (master !== undefined) lines.push({ text: `${plain(master.name)}${counts(master)}`, colour: 'magenta', bold: true })
  if (pinned !== undefined) {
    const indent = master !== undefined ? '└ ' : ''
    const tail = plain(pinned.tail)
    lines.push({ text: `${indent}${plain(pinned.name)}${counts(pinned)}${tail ? ` ${tail}` : ''}`, colour: 'cyan', bold: true })
    // The tail already shows ↻N/M during a gate; outside one, a recorded round
    // gets its own line. Both numbers come from the script, never a default here.
    const round = pinned.remediation_round
    const budget = pinned.remediation_budget
    if (typeof round === 'number' && typeof budget === 'number' && !tail.includes('↻')) {
      lines.push({ text: `remediation ↻${round}/${budget}`, colour: 'yellow' })
    }
  }
  if (state?.stale === true) lines.push({ text: '(stale: the last refresh failed)', dim: true })

  const current = typeof pinned?.task === 'string' && pinned.phase === 'task' ? pinned.task : null
  for (const stage of detail?.stages ?? []) {
    const head = stage.number === null ? 'Tasks' : `Stage ${stage.number}${stage.name ? ` — ${plain(stage.name)}` : ''}`
    const gate = stage.gate_total > 0 ? `  gate ${stage.gate_checked}/${stage.gate_total}` : ''
    lines.push({ text: '' })
    lines.push({ text: `${head}${gate}`, bold: true })
    for (const t of stage.tasks) lines.push({ text: taskLine(t, current), dim: t.status === 'done' })
  }

  if (agents.length > 0) {
    lines.push({ text: '' })
    lines.push({ text: 'Agents', bold: true })
    const running = agents.filter(a => a.outcome === 'running')
    const ended = agents.filter(a => a.outcome !== 'running').reverse()
    for (const a of [...running, ...ended]) {
      lines.push({
        text: `${OUTCOME[a.outcome] ?? '·'} ${plain(a.description)} · ${plain(a.subagentType)}`,
        dim: a.outcome === 'done',
        colour: a.outcome === 'failed' || a.outcome === 'denied' ? 'red' : undefined,
      })
    }
  }
  return lines
}

export function registerPane(on: On): void {
  // Only where a person can type it: a -p run has no use for a slash command.
  on('session.start', { isInteractive: true }, async ($, e, next) => {
    const started = await next(e)
    await $.command.register({
      name: 'plan-view',
      description: 'Show the executing plan, its stages and tasks, and dispatched agents in a pane',
    })
    return started
  })

  on('command.run', { command: 'plan-view' }, async $ => {
    const opened = await $.ui.open({ id: PLAN_PANE, title: PLAN_PANE_TITLE })
    if (opened.isPlaced === false) return { text: `The plan pane is open but waits to be placed: ${opened.reason}` }
    return { text: 'Plan pane opened.' }
  })

  on('ui.render', { component: 'Pane', requestId: PLAN_PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const width = Math.max(1, Math.floor(e.props.bodyColumns))
    const lines = paneLines(await read($, MODEL), await read($, AGENTS))
    return (
      <Box flexDirection="column">
        {lines.map(line => (
          <Text bold={line.bold} dimColor={line.dim} color={line.colour} wrap="truncate">
            {clip(line.text, width) || ' '}
          </Text>
        ))}
      </Box>
    )
  })
}
