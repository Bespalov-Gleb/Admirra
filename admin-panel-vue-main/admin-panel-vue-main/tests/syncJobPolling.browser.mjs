// Real composable + Axios, synthetic same-origin responses, no production IO.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { createServer } from 'vite'
assert.equal(process.env.WW_TEST, '1')
assert.ok(process.env.WW_TEST_ID)
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE || 'playwright')
const root = fileURLToPath(new URL('../', import.meta.url))
const html = `<html><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';import {useSyncStatus} from '/src/composables/useSyncStatus.js';
window.qaApp=createApp({setup(){window.qaSync=useSyncStatus();return()=>h('div','test')}});window.qaApp.mount('#app');
</script></body></html>`
const server = await createServer({ root, configFile: false,
  resolve: { alias: { '@': path.join(root, 'src') } },
  plugins: [{ name: 'sync-isolated', configureServer(s) {
    s.middlewares.use(async (req, res, next) => {
      if (!req.url.startsWith('/__sync__')) return next()
      res.setHeader('Content-Type', 'text/html')
      res.end(await s.transformIndexHtml('/__sync__', html))
    })
  } }], server: { host: '127.0.0.1', port: 0, open: false },
})
let browser
try {
  await server.listen()
  browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_PATH })
  for (const scenario of ['recover', 'outage', 'failed', 'deadline']) {
    const page = await browser.newPage()
    const errors = [], requests = []
    let poll = 0
    page.on('pageerror', e => errors.push(e.message))
    await page.route('**/*', async route => {
      const req = route.request(), url = new URL(req.url())
      if (url.hostname !== '127.0.0.1') return route.abort()
      if (!url.pathname.startsWith('/api/')) return route.continue()
      requests.push({ method: req.method(), path: url.pathname })
      if (url.pathname === '/api/integrations/') return route.fulfill({ json: [] })
      assert.equal(url.pathname, '/api/integrations/sync/jobs/synthetic')
      poll++
      if (scenario === 'outage' || (scenario === 'recover' && poll === 2)) {
        return route.fulfill({ status: 502, contentType: 'text/html', body: 'Bad gateway' })
      }
      return route.fulfill({ json: { status: scenario === 'failed' ? 'FAILED'
        : scenario === 'recover' && poll >= 3 ? 'SUCCESS' : 'RUNNING', progress: 42 } })
    })
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__sync__`)
    await page.waitForFunction(() => window.qaSync)
    const r = await page.evaluate(async (scenario) => {
      const ticks = []
      try {
        const result = await window.qaSync.waitForSyncJobs(['synthetic'], {
          intervalMs: 10, timeoutMs: scenario === 'deadline' ? 100 : 5000,
          onTick: s => ticks.push(s),
        })
        return { result, ticks }
      } catch (error) { return { error: error.message, ticks } }
      finally { window.qaApp.unmount() }
    }, scenario)
    assert.ok(requests.every(r => r.method === 'GET'), 'never resubmit synchronization')
    if (scenario === 'recover') {
      assert.deepEqual(r.result.finished, ['synthetic'])
      assert.deepEqual(r.result.failed, [])
      assert.equal(r.ticks[1].synthetic.status, 'RUNNING')
      assert.equal(poll, 3)
    } else if (scenario === 'outage') {
      assert.match(r.error, /не означает, что она остановилась/)
      assert.equal(poll, 6)
    } else if (scenario === 'failed') assert.deepEqual(r.result.failed, ['synthetic'])
    else {
      assert.equal(r.result.timedOut, true)
      assert.deepEqual(r.result.failed, [])
      assert.deepEqual(r.result.pending, ['synthetic'])
    }
    assert.deepEqual(errors, [])
    await page.close()
  }
  console.log('PASS: 4 real Vue/Axios scenarios: recovery, bounded outage, true worker failure, deadline; GET-only')
} finally { await browser?.close(); await server.close() }
