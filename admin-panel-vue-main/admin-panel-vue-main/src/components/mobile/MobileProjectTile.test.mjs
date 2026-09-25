import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'

let server, Tile
before(async () => {
  server = await createServer({
    configFile: false,
    root: fileURLToPath(new URL('../../../', import.meta.url)),
    plugins: [vue()],
    server: { middlewareMode: true, hmr: false, ws: false },
    optimizeDeps: { noDiscovery: true },
    appType: 'custom',
  })
  Tile = (await server.ssrLoadModule('/src/components/mobile/MobileProjectTile.vue')).default
})
after(async () => { await server?.close() })

async function render({ count = 1, folder = false, unconfigured = false } = {}) {
  return renderToString(createSSRApp({ render: () => h(Tile, {
    project: { id: 'test', name: 'Проект', __isFolder: folder },
    stats: [], traffic: { impressions: '10', clicks: '2', details: [] },
    channels: Array.from({ length: count }, (_, i) => ({
      code: String(i), name: `Канал ${i}`, spendText: '100 ₽', goalTotal: 2,
      cplText: '50 ₽', needsGoalSelection: unconfigured,
    })),
    balances: [{ code: 'vk', name: 'VK', value: '500 ₽' }], folders: [], alerts: [],
  }) }))
}

for (const folder of [false, true]) {
  test(`single-channel ${folder ? 'folder' : 'project'} hides duplicate metrics but keeps balance`, async () => {
    const html = await render({ folder })
    assert.doesNotMatch(html, /class="mw-channel"/)
    assert.match(html, /500 ₽/)
  })
}
test('multiple connected channels keep their breakdown', async () => {
  const html = await render({ count: 2 })
  assert.equal((html.match(/class="mw-channel"/g) || []).length, 2)
})
test('unconfigured goals remain visible for one channel', async () => {
  assert.match(await render({ unconfigured: true }), /Канал 0: цели не выбраны/)
})
test('no channels keeps the empty state', async () => {
  assert.match(await render({ count: 0 }), /Каналы не подключены/)
})
test('actions run from more/settings to report/analytics; folders have no project-only menu', async () => {
  for (const folder of [false, true]) {
    const html = await render({ folder })
    const footer = html.match(/<footer[^>]*>([\s\S]*?)<\/footer>/)[1]
    assert.equal(footer.includes('Другие действия'), !folder)
    const labels = folder ? ['Настройки проекта', 'Отчёт', 'Аналитика']
      : ['Другие действия', 'Настройки проекта', 'Отчёт', 'Аналитика']
    const offsets = labels.map(label => footer.indexOf(label))
    assert.ok(offsets.every((offset, i) => offset >= 0 && (!i || offset > offsets[i - 1])))
  }
})
