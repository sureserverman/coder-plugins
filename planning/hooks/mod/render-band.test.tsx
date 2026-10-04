import { expect, test } from 'claude-code/testing'

import type { PlanGroup } from '../../types'
import { group, ran, seed, world } from './testing'

const SURFACES = ['terminal', 'desktop'] as const

const band = (bodyColumns: number, maxRows = 10, hasSurvey = false) => ({
  plugin: 'planning',
  component: 'AbovePrompt' as const,
  props: {
    hasSurvey,
    isWorking: false,
    maxRows,
    bodyColumns,
    scroll: { offset: 0, bodyRows: maxRows },
    view: {},
  },
})

const THREE: PlanGroup[] = [
  group({ name: 'master-plan', role: 'master', depth: 0, tail: '' }),
  group({ name: 'sub-plan-01', role: 'pinned', depth: 1 }),
  group({ name: 'another-plan-with-a-rather-long-name', role: 'other', depth: 0, tail: '' }),
]

function answering(groups: PlanGroup[]) {
  return () => ran(JSON.stringify({ groups, detail: null }))
}

// A row is one truncating Text: the drawn tree keeps no key on a Text, and the
// band's only other Text is the spacer before its button.
async function rowsOf(ui: { findAll: (q: { type: string }) => Promise<{ props: Record<string, unknown>; text: string }[]> }) {
  return (await ui.findAll({ type: 'Text' })).filter(t => t.props.wrap === 'truncate')
}

test('a 3-group model draws 3 rows on every surface', async ($, on) => {
  const w = world(on, answering(THREE))
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(120), surface })
    const rows = await rowsOf(ui)
    expect(rows.length).toBe(3)
    expect(rows[0]!.text).toContain('master-plan')
    expect(rows[1]!.text).toContain('sub-plan-01')
    expect(rows[1]!.text).toContain('2/5')
    expect(rows[1]!.text).toContain('▶ T1.3')
    await ui.unmount()
  }
})

test('no row is wider than bodyColumns at 40, 80 and 200', async ($, on) => {
  const w = world(on, answering(THREE))
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    for (const cols of [40, 80, 200]) {
      const ui = await $.ui.mount({ ...band(cols), surface })
      const rows = await rowsOf(ui)
      expect(rows.length).toBe(3)
      for (const row of rows) expect([...row.text].length).toBeLessThanOrEqual(cols)
      const button = await ui.find({ key: 'open-plan' })
      expect(button).toBeDefined()
      expect([...rows[0]!.text].length + '[ Plan ]'.length + 1).toBeLessThanOrEqual(cols)
      await ui.unmount()
    }
  }
})

test('an empty model passes through to what is beneath', async ($, on) => {
  const w = world(on, answering([]))
  on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>beneath: engine band</Text>
  })
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(80), surface })
    expect(await ui.find({ type: 'Text', text: 'beneath:' })).toBeDefined()
    expect((await rowsOf(ui)).length).toBe(0)
    await ui.unmount()
  }
})

test('no model at all passes through', async ($, on) => {
  world(on)
  on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>beneath: engine band</Text>
  })
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(80), surface })
    expect(await ui.find({ type: 'Text', text: 'beneath:' })).toBeDefined()
    await ui.unmount()
  }
})

test('a survey holding the band passes through', async ($, on) => {
  const w = world(on, answering(THREE))
  on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>beneath: survey</Text>
  })
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(80, 10, true), surface })
    expect(await ui.find({ type: 'Text', text: 'beneath:' })).toBeDefined()
    expect((await rowsOf(ui)).length).toBe(0)
    await ui.unmount()
  }
})

test('a 12-group model at maxRows 4 draws 4 rows', async ($, on) => {
  const twelve = Array.from({ length: 12 }, (_, i) => group({ name: `plan-${i}`, role: i === 0 ? 'pinned' : 'other' }))
  const w = world(on, answering(twelve))
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(80, 4), surface })
    const rows = await rowsOf(ui)
    expect(rows.length).toBe(4)
    expect(rows[3]!.text).toContain('9 more')
    await ui.unmount()
  }
})

test('no drawn text carries an escape, even from a hostile name or tail', async ($, on) => {
  const hostile = [group({ name: 'evil\x1b[31mred', tail: '· \x1b]0;title\x07 S1/2' })]
  const w = world(on, answering(hostile))
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(80), surface })
    const texts = await ui.findAll({ type: 'Text' })
    expect(texts.length).toBeGreaterThan(0)
    for (const t of texts) expect(/[\x00-\x1f\x7f]/.test(t.text)).toBe(false)
    await ui.unmount()
  }
})

test('a stale model is marked', async ($, on) => {
  let fail = false
  const w = world(on, () => {
    if (fail) throw new Error('timed out')
    return ran(JSON.stringify({ groups: [group()], detail: null }))
  })
  await seed($ as never, w.clock)
  fail = true
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(80), surface })
    const rows = await rowsOf(ui)
    expect(rows[0]!.text).toContain('stale')
    await ui.unmount()
  }
})

test('a long name is clipped before the counts: bar and done/total always show', async ($, on) => {
  const long = [group({ name: '2026-09-11 coder-plugins Verification Cost Bounds and More', done: 3, total: 6 })]
  const w = world(on, answering(long))
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    for (const cols of [40, 60]) {
      const ui = await $.ui.mount({ ...band(cols), surface })
      const row = (await rowsOf(ui))[0]!.text
      expect(row).toContain('3/6')
      expect(row).toContain('▐')
      await ui.unmount()
    }
  }
})

test('the stale marker survives a long tail', async ($, on) => {
  let fail = false
  const w = world(on, () => {
    if (fail) throw new Error('timed out')
    return ran(JSON.stringify({ groups: [group({ tail: `· S1/2 ▶ T1.3 ${'very long task description '.repeat(6)}` })], detail: null }))
  })
  await seed($ as never, w.clock)
  fail = true
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(60), surface })
    expect((await rowsOf(ui))[0]!.text).toContain('stale')
    await ui.unmount()
  }
})

test('maxRows 0 draws nothing of its own', async ($, on) => {
  const w = world(on, answering(THREE))
  on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>beneath: engine band</Text>
  })
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(80, 0), surface })
    expect((await rowsOf(ui)).length).toBe(0)
    expect(await ui.find({ type: 'Text', text: 'beneath:' })).toBeDefined()
    await ui.unmount()
  }
})

test('the pinned plan stays visible when the rows run out', async ($, on) => {
  const many = Array.from({ length: 12 }, (_, i) =>
    group({ name: `plan-${i}`, role: i === 7 ? 'pinned' : 'other', depth: 0 }),
  )
  const w = world(on, answering(many))
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    for (const maxRows of [1, 4]) {
      const ui = await $.ui.mount({ ...band(80, maxRows), surface })
      const rows = await rowsOf(ui)
      expect(rows.length).toBe(maxRows)
      expect(rows.some(r => r.text.includes('plan-7'))).toBe(true)
      await ui.unmount()
    }
  }
})

test('a pinned sub-plan keeps its master above it when rows run out', async ($, on) => {
  const groups = [
    group({ name: 'other-a', role: 'other', depth: 0 }),
    group({ name: 'other-b', role: 'other', depth: 0 }),
    group({ name: 'the-master', role: 'master', depth: 0 }),
    group({ name: 'sub-1', role: 'child', depth: 1 }),
    group({ name: 'sub-2', role: 'pinned', depth: 1 }),
  ]
  const w = world(on, answering(groups))
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(80, 3), surface })
    const rows = (await rowsOf(ui)).map(r => r.text)
    expect(rows[0]).toContain('the-master')
    expect(rows[1]).toContain('sub-2')
    expect(rows[1]).toContain('└ ')
    expect(rows[2]).toContain('more')
    await ui.unmount()
  }
})

test('below 24 columns the Plan button is dropped and the row keeps the width', async ($, on) => {
  const w = world(on, answering(THREE))
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(20), surface })
    expect(await ui.find({ key: 'open-plan' })).toBe(undefined)
    for (const row of await rowsOf(ui)) expect([...row.text].length).toBeLessThanOrEqual(20)
    await ui.unmount()
  }
})

test('C1 controls (CSI U+009B) never reach a surface', async ($, on) => {
  const w = world(on, answering([group({ name: 'evil\u009b31mred', tail: '· \u0085next' })]))
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(80), surface })
    for (const t of await ui.findAll({ type: 'Text' })) expect(/[\x00-\x1f\x7f-\x9f]/.test(t.text)).toBe(false)
    await ui.unmount()
  }
})

test('drawing the band runs no process', async ($, on) => {
  const w = world(on, answering(THREE))
  await seed($ as never, w.clock)
  const before = w.runs.length
  for (const surface of SURFACES) {
    for (const cols of [40, 120]) {
      const ui = await $.ui.mount({ ...band(cols), surface })
      await ui.unmount()
    }
  }
  expect(w.runs.length).toBe(before)
})

// The live window as a main-loop turn's end reports it: `engineUsage` answers
// beneath (registered before the test first calls $), `turnEnds` ends a turn, and
// the context hook stores the figures for the band (no state file on disk here,
// so no sidecar is written).
function engineUsage(on: Parameters<typeof world>[0], percent: number) {
  on('session.usage', () => ({ value: { startedAt: 0, context: { window: 1_000_000, tokens: 250_000, percent }, rateLimits: [] } }) as never)
  on('turn.complete', () => ({ text: '' }))
}

const turnEnds = ($: unknown) =>
  ($ as { turn: { complete: (i: never) => Promise<unknown> } }).turn.complete(
    { answer: '', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' } as never,
  )

test('the pinned row shows the context in use, and only the pinned row', async ($, on) => {
  const w = world(on, answering(THREE))
  engineUsage(on, 25)
  await seed($ as never, w.clock)
  await turnEnds($)
  for (const surface of ['terminal', 'desktop'] as const) {
    for (const cols of [60, 160]) {
      const ui = await $.ui.mount({ ...band(cols), surface })
      const rows = await rowsOf(ui)
      expect(rows[1]!.text).toContain('context 25%')
      expect(rows[1]!.text).toContain('2/5')
      expect(rows[0]!.text).not.toContain('%')
      expect(rows[2]!.text).not.toContain('context')
      for (const row of rows) expect([...row.text].length).toBeLessThanOrEqual(cols)
      await ui.unmount()
    }
  }
})

test('no context figure yet: the pinned row shows none', async ($, on) => {
  const w = world(on, answering([group()]))
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band(120), surface })
    expect((await rowsOf(ui))[0]!.text).not.toContain('context')
    await ui.unmount()
  }
})
