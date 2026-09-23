import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import * as vue from 'vue'

const tick = () => new Promise(resolve => setImmediate(resolve))
let serial = 0
async function setup() {
  const calls = [], cleanup = []
  globalThis.localStorage = { getItem: () => null, setItem() {} }
  globalThis.__dashboardFixture = {
    vue: { ...vue, watch: () => {}, onMounted: () => {}, onUnmounted: fn => cleanup.push(fn) },
    api: { get(path, config) {
      return new Promise((resolve, reject) => calls.push({ path, config, resolve, reject }))
    } },
  }
  let source = await readFile(new URL('./useDashboardStats.js', import.meta.url), 'utf8')
  source = source.replace(/import \{([^}]+)\} from 'vue'/, 'const {$1} = globalThis.__dashboardFixture.vue')
  source = source.replace("import api from '../api/axios'", 'const api = globalThis.__dashboardFixture.api')
  source = source.replace("'../utils/latestRequest'", JSON.stringify(new URL('../utils/latestRequest.js', import.meta.url).href))
  source = source.replace("import { getAccessToken } from '@/utils/authToken'", 'const getAccessToken = () => "synthetic-test-token"')
  source = source.replace("import { getProjectPeriodRange } from '@/utils/projectPeriods'", 'const getProjectPeriodRange = () => ({startDate:"2026-09-14",endDate:"2026-09-20"})')
  const { useDashboardStats } = await import('data:text/javascript;base64,' + Buffer.from(source + `\n// instance ${serial++}`).toString('base64'))
  const state = useDashboardStats({ overviewProjects: true })
  Object.assign(state.filters, { client_id: 'project-a', start_date: '2026-09-14', end_date: '2026-09-20', period: 'last_week' })
  return { state, calls, cleanup: () => cleanup.forEach(fn => fn()), resolveAll: (from = 0, data = {}) => calls.slice(from).forEach(c => c.resolve({ data })) }
}

test('project selector uses compact metadata while campaign selectors stay separate', async () => {
  const f = await setup()
  const run = f.state.fetchClients()
  await tick()
  assert.equal(f.calls[0].path, 'clients/')
  assert.deepEqual(f.calls[0].config.params, { include_campaigns: false })
  f.resolveAll(0, [{ id: 'project-a', integrations: [] }])
  await run
  f.cleanup()
})

test('KPI commits without waiting for slow campaigns; duplicate calls share one generation', async () => {
  const f = await setup()
  const run = f.state.fetchStats()
  assert.equal(f.state.fetchStats(), run)
  await tick()
  assert.equal(f.calls.filter(c => c.path === 'dashboard/campaigns').length, 1)
  assert.ok(f.calls.every(c => c.config.params.period_preset === 'last_week'))
  f.calls.filter(c => c.path === 'dashboard/summary').forEach(c => c.resolve({ data: { impressions: 42, expenses: 100 } }))
  await tick()
  assert.equal(f.state.summary.value.impressions, 42)
  assert.equal(f.state.loading.value, false)
  assert.equal(Object.keys(f.state.channelSummaries.value).length, 3)
  assert.ok(!f.calls.some(c => /devices|placements|top-clients/.test(c.path)))
  f.resolveAll()
  await run
  f.cleanup()
})

test('late old-period responses cannot overwrite the new period, its loading or campaigns', async () => {
  const f = await setup()
  const old = f.state.fetchStats()
  await tick()
  const boundary = f.calls.length
  f.state.filters.start_date = '2026-09-01'
  const current = f.state.fetchStats()
  await tick()
  assert.ok(f.calls.slice(0, boundary).every(c => c.config.signal.aborted))
  f.calls.slice(0, boundary).forEach(c => c.resolve({ data: { impressions: 999 } }))
  await old
  assert.equal(f.state.loading.value, true)
  assert.notEqual(f.state.summary.value.impressions, 999)
  f.resolveAll(boundary, { impressions: 77 })
  await current
  assert.equal(f.state.summary.value.impressions, 77)
  assert.equal(f.state.loading.value, false)
  f.cleanup()
})

test('overall summary skips hidden campaign table, folder keeps its visible table; teardown aborts', async () => {
  const f = await setup()
  f.state.filters.client_id = null
  const overall = f.state.fetchStats()
  await tick()
  assert.ok(!f.calls.some(c => c.path === 'dashboard/campaigns'))
  f.resolveAll()
  await overall
  const boundary = f.calls.length
  f.state.filters.folder_id = 'folder-a'
  const folder = f.state.fetchStats()
  await tick()
  assert.ok(f.calls.slice(boundary).some(c => c.path === 'dashboard/campaigns'))
  assert.ok(f.calls.slice(boundary).every(c => c.config.params.client_id === undefined))
  f.cleanup()
  assert.ok(f.calls.slice(boundary).every(c => c.config.signal.aborted))
  f.resolveAll(boundary)
  await folder
})

test('summary failure is not committed as zero and does not prevent independent data', async () => {
  const f = await setup()
  f.state.filters.channel = 'yandex'
  f.state.summary.value = { impressions: 55 }
  const run = f.state.fetchStats()
  await tick()
  f.calls.find(c => c.path === 'dashboard/summary').reject(new Error('synthetic offline'))
  f.calls.filter(c => c.path !== 'dashboard/summary').forEach(c => c.resolve({ data: [] }))
  await run
  assert.equal(f.state.summary.value.impressions, 55)
  assert.ok(f.state.error.value)
  assert.equal(f.state.loading.value, false)
  f.cleanup()
})
