// The progress band above the prompt: one row per plan group the model holds,
// sized to the band's own width. It draws what plan-progress.py --json computed —
// the counts, and `tail`, the script's own text after its bar — and never derives
// a phase or a marker itself, so the band and the status line cannot disagree.

import { atom, read } from 'claude-code'
import type { On } from 'claude-code'

import type { PlanGroup, PlanModelState } from '../../types'
import { PLAN_PANE, PLAN_PANE_TITLE } from './pane-id'

// Declared in each file that reads it: the engine's scan lists a module's state
// reads from atoms written in the reading file itself.
const MODEL = atom({ plugin: 'planning', key: 'model' } as const, null as PlanModelState | null)

const BAR_CELLS = 10
// "[ Plan ]" plus the space before it, kept off the first row's text budget.
const BUTTON_CELLS = 9
const CONTROL = /[\x00-\x1f\x7f]/g

const COLOUR: Record<PlanGroup['role'], string | undefined> = {
  pinned: 'cyan',
  master: 'magenta',
  child: undefined,
  other: undefined,
}

// The model is the script's output, and a plan name or a task description in it
// is text somebody else wrote: no control character reaches a surface.
function plain(s: unknown): string {
  return typeof s === 'string' ? s.replace(CONTROL, '') : ''
}

function bar(done: number, total: number): string {
  const filled = total > 0 ? Math.round((Math.min(done, total) / total) * BAR_CELLS) : 0
  return `▐${'█'.repeat(filled)}${'░'.repeat(BAR_CELLS - filled)}▌`
}

function clip(text: string, width: number): string {
  const cells = [...text]
  if (cells.length <= width) return text
  return width <= 1 ? cells.slice(0, Math.max(0, width)).join('') : `${cells.slice(0, width - 1).join('')}…`
}

export function rowText(g: PlanGroup, width: number, stale: boolean): string {
  const indent = (g.depth ?? 0) > 0 ? '└ ' : ''
  const counts = g.total > 0 ? ` ${bar(g.done, g.total)} ${g.done}/${g.total}` : ''
  const tail = plain(g.tail)
  const text = `${indent}${plain(g.name)}${counts}${tail ? ` ${tail}` : ''}${stale ? ' (stale)' : ''}`
  return clip(text, width)
}

// At most `maxRows` rows: when the groups do not fit, the last row counts the rest.
export function bandRows(groups: PlanGroup[], maxRows: number): (PlanGroup | number)[] {
  const limit = Math.max(1, Math.floor(maxRows))
  if (groups.length <= limit) return groups
  if (limit === 1) return groups.slice(0, 1)
  return [...groups.slice(0, limit - 1), groups.length - (limit - 1)]
}

export function registerBand(on: On): void {
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const state = await read($, MODEL)
    const groups = state?.model?.groups ?? []
    if (groups.length === 0) return next(e)

    const { Box, Button, Text } = $.ui.resolve(e)
    const cols = Math.max(1, Math.floor(e.props.bodyColumns))
    const rows = bandRows(groups, e.props.maxRows)

    return (
      <Box flexDirection="column">
        {rows.map((row, i) => {
          if (typeof row === 'number') {
            return (
              <Text dimColor wrap="truncate">
                {clip(`… ${row} more`, cols)}
              </Text>
            )
          }
          const colour = COLOUR[row.role]
          const width = i === 0 ? Math.max(1, cols - BUTTON_CELLS) : cols
          const text = rowText(row, width, i === 0 && state?.stale === true)
          const line = (
            <Text color={colour} dimColor={colour === undefined} wrap="truncate">
              {text}
            </Text>
          )
          if (i !== 0) return line
          return (
            <Box key="first" flexDirection="row">
              {line}
              <Text> </Text>
              <Button
                key="open-plan"
                label="Plan"
                onPress={() => void $.ui.open({ id: PLAN_PANE, title: PLAN_PANE_TITLE })}
              />
            </Box>
          )
        })}
      </Box>
    )
  })
}
