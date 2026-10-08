// The progress band above the prompt: one row per plan group the model holds,
// sized to the band's own width, drawn in the status line's pieces and colours.
// It draws what plan-progress.py --json computed — the counts, `tail_spans` (the
// script's own text after its bar, split at its colour codes) and the `palette` —
// and never derives a phase, a marker or a marker's colour itself, so the band and
// the status line cannot disagree.

import { atom, read } from 'claude-code'
import type { On } from 'claude-code'

import type { ContextFigures, PlanGroup, PlanModelState, PlanPalette } from '../../types'
import { PLAN_PANE, PLAN_PANE_TITLE } from './pane-id'

// Declared in each file that reads it: the engine's scan lists a module's state
// reads from atoms written in the reading file itself.
const MODEL = atom({ plugin: 'planning', key: 'model' } as const, null as PlanModelState | null)
const CONTEXT = atom({ plugin: 'planning', key: 'context' } as const, null as ContextFigures | null)

// The status line's 20-cell bar where the band is wide, half of it elsewhere.
const BAR_CELLS = 20
const BAR_CELLS_NARROW = 10
const WIDE_COLUMNS = 100
// "[ Plan ]", the space before it, and the collapse control the engine draws at
// the band's right edge: kept off the first row's text budget.
const BUTTON_CELLS = 12
// Below this the button is not drawn at all; the row keeps the whole width.
const BUTTON_MIN_COLUMNS = 24
// A name is never clipped below this while the row has room for it.
const NAME_MIN = 8
// C0, DEL and C1 (U+0080-U+009F, among them U+009B, a one-byte CSI).
// Controls (Cc: C0, DEL and C1, among them U+009B, a one-byte CSI), invisible
// format characters (Cf: bidi overrides, zero-width marks) and lone surrogates
// (Cs) — the classes plan_continue_classify.py's clean() drops.
const CONTROL = /[\p{Cc}\p{Cf}\p{Cs}]/gu

// The fill and the pinned name take the script's palette; an older script sends
// none, and the theme's own keys stand in.
const FALLBACK = { green: 'success', cyan: 'suggestion' }
// A span colour is the script's `#rrggbb` or nothing: no other string reaches a Text.
const HEX = /^#[0-9a-f]{6}$/i

// One piece of a row: its text and how it is drawn.
export type Span = { text: string; color?: string; dim?: boolean }

// The model is the script's output, and a plan name or a task description in it
// is text somebody else wrote: no control character reaches a surface.
function plain(s: unknown): string {
  return typeof s === 'string' ? s.replace(CONTROL, '') : ''
}

const cells = (text: string): number => [...text].length
const width_ = (spans: Span[]): number => spans.reduce((n, s) => n + cells(s.text), 0)

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

// Spans cut to `width` cells, the last kept one ending in … when anything was lost.
export function clipSpans(spans: Span[], width: number): Span[] {
  if (width_(spans) <= width) return spans
  const out: Span[] = []
  let room = Math.max(0, width)
  for (const s of spans) {
    if (room <= 0) break
    const chars = [...s.text]
    if (chars.length <= room) {
      out.push(s)
      room -= chars.length
    } else {
      out.push({ ...s, text: clip(s.text, room) })
      room = 0
    }
  }
  return out
}

// The group's tail as spans: the script's own `tail_spans`, each text made plain
// and each colour a `#rrggbb` or none; the plain `tail` when an older script sent
// no spans.
function tailSpans(g: PlanGroup): Span[] {
  if (!Array.isArray(g.tail_spans)) {
    const tail = plain(g.tail)
    return tail === '' ? [] : [{ text: tail }]
  }
  const out: Span[] = []
  for (const s of g.tail_spans) {
    const text = plain(s?.text)
    if (text === '') continue
    const color = typeof s.color === 'string' && HEX.test(s.color) ? s.color : undefined
    out.push({ text, color, dim: s.dim === true ? true : undefined })
  }
  return out
}

// One row as the status line draws it — `└─ ` for a sub-plan, `⚙ ` and the name
// (cyan when pinned, dim otherwise), `▐` + the green fill + the `░` track `▌`,
// `done/total`, a dim `(pct%)`, the tail's spans, the pinned row's context — fitted
// to `width` by priority: the indent, the counts and the stale marker are kept
// whole; the context figure is shown whole or not at all, and only while the name
// keeps NAME_MIN beside it; the name gives way next (down to NAME_MIN); the tail,
// free text from the script, gives way first. Only a row too narrow for even
// that is clipped as a whole.
export function rowSpans(
  g: PlanGroup,
  width: number,
  stale: boolean,
  context = '',
  palette: PlanPalette | undefined = undefined,
  barCells = BAR_CELLS_NARROW,
): Span[] {
  const green = typeof palette?.green === 'string' && HEX.test(palette.green) ? palette.green : FALLBACK.green
  const cyan = typeof palette?.cyan === 'string' && HEX.test(palette.cyan) ? palette.cyan : FALLBACK.cyan
  const indent: Span[] = (g.depth ?? 0) > 0 ? [{ text: '└─ ', dim: true }] : []
  const counts: Span[] = []
  if (g.total > 0) {
    const filled = Math.round((Math.min(Math.max(g.done, 0), g.total) / g.total) * barCells)
    const pct = Math.floor((Math.min(Math.max(g.done, 0), g.total) * 100) / g.total)
    counts.push(
      { text: ' ' },
      { text: '▐', dim: true },
      { text: '█'.repeat(filled), color: green },
      { text: `${'░'.repeat(barCells - filled)}▌`, dim: true },
      { text: ` ${g.done}/${g.total} ` },
      { text: `(${pct}%)`, dim: true },
    )
  }
  const mark: Span[] = stale ? [{ text: ' (stale)', dim: true }] : []
  const name = plain(g.name)
  const pinned = g.role === 'pinned'
  const head = '⚙ '
  const fixed0 = width_(indent) + cells(head) + width_(counts) + width_(mark)
  const ctx = fixed0 + Math.min(cells(name), NAME_MIN) + cells(context) <= width ? context : ''
  const fixed = fixed0 + cells(ctx)
  const nameRoom = Math.max(Math.min(cells(name), NAME_MIN), width - fixed)
  const shownName = clip(name, nameRoom)
  const tailRoom = width - fixed - cells(shownName) - 1
  const tail = tailSpans(g)
  const shownTail = tail.length > 0 && tailRoom >= 2 ? [{ text: ' ' }, ...clipSpans(tail, tailRoom)] : []
  const row: Span[] = [
    ...indent,
    pinned ? { text: `${head}${shownName}`, color: cyan } : { text: `${head}${shownName}`, dim: true },
    ...counts,
    ...mark,
    ...shownTail,
    ...(ctx === '' ? [] : [{ text: ctx }]),
  ]
  return clipSpans(row, width).filter(s => s.text !== '')
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
    const barCells = cols >= WIDE_COLUMNS ? BAR_CELLS : BAR_CELLS_NARROW
    const palette = state?.model?.palette

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
          const width = i === 0 && withButton ? cols - BUTTON_CELLS : cols
          const spans = rowSpans(
            row,
            width,
            i === 0 && state?.stale === true,
            row.role === 'pinned' ? context : '',
            palette,
            barCells,
          )
          const line = (
            <Text wrap="truncate">
              {spans.map(s => (
                <Text color={s.color} dimColor={s.dim}>
                  {s.text}
                </Text>
              ))}
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
