// The progress band above the prompt: one row per plan group the model holds,
// sized to the band's own width. It draws what plan-progress.py --json computed —
// the counts, and `tail`, the script's own text after its bar — and never derives
// a phase or a marker itself, so the band and the status line cannot disagree.

import { atom, read } from 'claude-code'
import type { On } from 'claude-code'

import type { ContextFigures, PlanGroup, PlanModelState } from '../../types'
import { PLAN_PANE, PLAN_PANE_TITLE } from './pane-id'

// Declared in each file that reads it: the engine's scan lists a module's state
// reads from atoms written in the reading file itself.
const MODEL = atom({ plugin: 'planning', key: 'model' } as const, null as PlanModelState | null)
const CONTEXT = atom({ plugin: 'planning', key: 'context' } as const, null as ContextFigures | null)

const BAR_CELLS = 10
// "[ Plan ]", the space before it, and the collapse control the engine draws at
// the band's right edge: kept off the first row's text budget.
const BUTTON_CELLS = 12
// Below this the button is not drawn at all; the row keeps the whole width.
const BUTTON_MIN_COLUMNS = 24
// A name is never clipped below this while the row has room for it.
const NAME_MIN = 8
// C0, DEL and C1 (U+0080-U+009F, among them U+009B, a one-byte CSI).
const CONTROL = /[\x00-\x1f\x7f-\x9f]/g

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

const cells = (text: string): number => [...text].length

function clip(text: string, width: number): string {
  const chars = [...text]
  if (chars.length <= width) return text
  return width <= 1 ? chars.slice(0, Math.max(0, width)).join('') : `${chars.slice(0, width - 1).join('')}…`
}

// The pinned row's context figure, ` · context 25%`, from the live window the
// context hook stored; empty when the engine has not reported a percentage yet.
export function contextText(figures: ContextFigures | null): string {
  const percent = figures?.percent
  return typeof percent === 'number' && Number.isSafeInteger(percent) ? ` · context ${percent}%` : ''
}

// One row, fitted to `width` by priority: the indent, the counts and the stale
// marker are kept whole; the context figure is shown whole or not at all, and
// only while the name keeps NAME_MIN beside it; the name gives way next (down to NAME_MIN); the tail,
// free text from the script, gives way first. Only a row too narrow for even
// that is clipped as a whole.
export function rowText(g: PlanGroup, width: number, stale: boolean, context = ''): string {
  const indent = (g.depth ?? 0) > 0 ? '└ ' : ''
  const bare = g.total > 0 ? ` ${bar(g.done, g.total)} ${g.done}/${g.total}` : ''
  const mark = stale ? ' (stale)' : ''
  const name = plain(g.name)
  const tail = plain(g.tail)
  const kept = cells(indent) + cells(bare) + cells(mark) + Math.min(cells(name), NAME_MIN)
  const counts = kept + cells(context) <= width ? bare + context : bare
  const fixed = cells(indent) + cells(counts) + cells(mark)
  const nameRoom = Math.max(Math.min(cells(name), NAME_MIN), width - fixed)
  const shownName = clip(name, nameRoom)
  const tailRoom = width - fixed - cells(shownName) - 1
  const shownTail = tail !== '' && tailRoom >= 2 ? ` ${clip(tail, tailRoom)}` : ''
  return clip(`${indent}${shownName}${counts}${mark}${shownTail}`, width)
}

// At most `maxRows` rows, and the executing plan is always one of them: when the
// groups do not fit, the pinned group (with its master, when it is a sub-plan)
// comes first and the last row counts the rest. None when maxRows is below 1.
export function bandRows(groups: PlanGroup[], maxRows: number): (PlanGroup | number)[] {
  const limit = Math.floor(maxRows)
  if (!(limit >= 1)) return []
  if (groups.length <= limit) return groups
  const at = groups.findIndex(g => g.role === 'pinned')
  const keep: PlanGroup[] = []
  if (at >= 0) {
    const pinned = groups[at]!
    if ((pinned.depth ?? 0) > 0) {
      for (let i = at - 1; i >= 0; i -= 1) {
        if ((groups[i]!.depth ?? 0) === 0) {
          keep.push(groups[i]!)
          break
        }
      }
    }
    keep.push(pinned)
  }
  const room = limit === 1 ? 1 : limit - 1
  const rest = groups.filter(g => !keep.includes(g))
  const shown = [...keep, ...rest].slice(0, room)
  return limit === 1 ? shown : [...shown, groups.length - shown.length]
}

export function registerBand(on: On): void {
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const state = await read($, MODEL)
    const context = contextText(await read($, CONTEXT))
    const groups = state?.model?.groups ?? []
    const rows = bandRows(groups, e.props.maxRows)
    if (rows.length === 0) return next(e)

    const { Box, Button, Text } = $.ui.resolve(e)
    const cols = Math.max(1, Math.floor(e.props.bodyColumns))
    const withButton = cols >= BUTTON_MIN_COLUMNS

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
          const width = i === 0 && withButton ? cols - BUTTON_CELLS : cols
          const text = rowText(row, width, i === 0 && state?.stale === true, row.role === 'pinned' ? context : '')
          const line = (
            <Text color={colour} dimColor={colour === undefined} wrap="truncate">
              {text}
            </Text>
          )
          if (i !== 0 || !withButton) return line
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
