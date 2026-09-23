import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import * as vue from 'vue'

let serial = 0
async function setup() {
  const calls = []
  globalThis.localStorage = { getItem: () => 'project-a', setItem() {}, removeItem() {} }
  globalThis.__projectsFixture = { vue, api: { get(path, config) {
    return new Promise((resolve, reject) => calls.push({ path, config, resolve, reject }))
  } } }
  let source = await readFile(new URL('./useProjects.js', import.meta.url), 'utf8')
  source = source.replace("import { ref, computed } from 'vue'", 'const { ref, computed } = globalThis.__projectsFixture.vue')
  source = source.replace("import axios from '../api/axios'", 'const axios = globalThis.__projectsFixture.api')
  source = source.replace("import { getAccessToken } from '@/utils/authToken'", 'const getAccessToken = () => "synthetic"')
  const { useProjects } = await import('data:text/javascript;base64,' + Buffer.from(source + `\n// ${serial++}`).toString('base64'))
  return { state: useProjects(), second: useProjects(), calls }
}

test('shared compact request preserves metadata, selection and cache behavior', async () => {
  const { state, second, calls } = await setup()
  const first = state.fetchProjects(), another = second.fetchProjects()
  assert.equal(calls.length, 1)
  assert.equal(calls[0].path, '/clients/')
  assert.deepEqual(calls[0].config.params, { include_campaigns: false })
  const project = { id: 'project-a', name: 'Synthetic', folder_id: 'folder-a',
    integrations: [{ id: 'integration-a', platform: 'VK_ADS', balance: 100,
      selected_goals: ['1'], last_sync_at: '2026-09-23T10:00:00Z' }] }
  calls[0].resolve({ data: [project] })
  await Promise.all([first, another])
  assert.equal(state.currentProjectId.value, 'project-a')
  assert.deepEqual(state.currentProject.value, project)
  assert.deepEqual(second.projects.value, [project])
  assert.equal(state.isLoading.value, false)
  await state.fetchProjects({ preferCache: true })
  assert.equal(calls.length, 1)
  const refresh = state.fetchProjects()
  assert.equal(calls.length, 2)
  calls[1].resolve({ data: [{ ...project, name: 'Updated' }] })
  await refresh
  assert.equal(state.currentProjectName.value, 'Updated')
})

test('older backend may still return full data without breaking the list', async () => {
  const { state, calls } = await setup()
  const run = state.fetchProjects()
  calls[0].resolve({ data: [{ id: 'project-a', name: 'Synthetic', integrations: [
    { id: 'integration-a', campaigns: [{ id: 'campaign-a' }] },
  ] }] })
  await run
  assert.equal(state.currentProject.value.integrations[0].campaigns[0].id, 'campaign-a')
})
