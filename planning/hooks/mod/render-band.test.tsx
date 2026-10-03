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
