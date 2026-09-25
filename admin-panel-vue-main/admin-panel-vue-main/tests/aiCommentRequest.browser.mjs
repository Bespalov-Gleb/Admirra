// Actual dashboard AI-panel template, request state, click handler and styles.
// Other dashboard panels/providers are excluded; all API traffic is synthetic.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
assert.equal(process.env.WW_TEST, '1'); assert.ok(process.env.WW_TEST_ID)
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE || 'playwright')
const root = fileURLToPath(new URL('../', import.meta.url))
const source = readFileSync(path.join(root, 'src/views/GeneralStats3/GeneralStats3.vue'), 'utf8')
const begin = source.indexOf('<article class="panel ai-panel ai-comment"')
const template = source.slice(begin, source.indexOf('</article>', begin) + '</article>'.length)
const state = source.slice(source.indexOf("const reportComment = ref('')"), source.indexOf('const loadSavedComment = async'))
const trigger = source.slice(source.indexOf('const triggerAiComment = async'), source.indexOf('// §7: вместо скачивания'))
const style = source.match(/<style scoped>([\s\S]*?)<\/style>/)[1]
const component = `<template>${template}</template><script setup>
import {ref,reactive,computed,watch,onUnmounted} from 'vue';
import {SparklesIcon,ClipboardDocumentIcon,CheckIcon,ChevronDownIcon,ArrowPathIcon} from '@heroicons/vue/24/outline';
import api from '@/api/axios';import {createAiCommentRequest,aiCommentError} from '@/utils/aiCommentRequest';
const filters=reactive({client_id:'synthetic',start_date:'2026-09-01',end_date:'2026-09-07'});
${state}
${trigger}
const aiComment=computed(()=>reportComment.value?{lead:reportComment.value,body:[],recommendation:''}:null);
const aiCommentCollapsed=ref(false),aiCommentCopied=ref(false),aiCommentGeneratedLabel='сейчас',aiCommentPeriodLabel='1–7 сентября';
const toggleAiCommentCollapsed=()=>aiCommentCollapsed.value=!aiCommentCollapsed.value;
const copyAiComment=()=>{},clarifyAiContext=()=>{},sendAiFeedback=()=>{};
window.qaChangeScope=()=>{filters.client_id='other'};
</script><style scoped>${style}</style>`
const server = await createServer({ root, configFile: false,
  resolve: { alias: { '@': path.join(root, 'src') } },
  plugins: [{ name: 'ai-panel-isolated', enforce: 'pre',
    resolveId(id) { if (id === '/__ai_panel__.vue') return id },
    load(id) { if (id === '/__ai_panel__.vue') return component },
    configureServer(s) { s.middlewares.use(async (req, res, next) => {
      if (req.url !== '/__ai__') return next()
      res.setHeader('Content-Type', 'text/html')
      res.end(await s.transformIndexHtml('/__ai__', `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:#f5f6fa;font:16px Arial;color:#202637}main{max-width:960px;margin:24px auto;padding:12px}*{box-sizing:border-box}button{cursor:pointer}</style></head><body><main id="app"></main><script type="module">import {createApp} from 'vue';import Panel from '/__ai_panel__.vue';window.qaApp=createApp(Panel);window.qaApp.mount('#app')</script></body></html>`))
    }) },
  }, vue()], server: { host: '127.0.0.1', port: 0, open: false },
})
let browser
try {
  await server.listen()
  browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_PATH })
  for (const scenario of ['fresh', 'waiting', 'failed', 'generation502', 'scope', 'unmount']) {
    const page = await browser.newPage({ viewport: { width: 1100, height: 650 } })
    await page.clock.install()
    const calls = [], errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.route('**/*', async route => {
      const req = route.request(), url = new URL(req.url())
      if (url.hostname !== '127.0.0.1') return route.abort()
      if (!url.pathname.startsWith('/api/')) return route.continue()
      calls.push([req.method(), url.pathname])
      if (url.pathname === '/api/ai/comment') return route.fulfill({ json: {
        data_readiness: ['fresh', 'generation502'].includes(scenario) ? null
          : { status: 'waiting', id: 'r', deadline: new Date(Date.now() + 600000).toISOString() },
      } })
      if (url.pathname === '/api/data-refresh/r') return route.fulfill({ json: {
        status: scenario === 'failed' ? 'held' : 'ready', id: 'r', can_retry: true,
      } })
      assert.equal(url.pathname, '/api/ai/generate-report')
      return scenario === 'generation502'
        ? route.fulfill({ status: 502, json: {} })
        : route.fulfill({ json: { text: 'Готовый комментарий по выбранному периоду.' } })
    })
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__ai__`)
    const button = page.getByRole('button', { name: 'Получить комментарий', exact: true })
    await button.waitFor()
    assert.deepEqual(calls, [], 'mount must not start generation/preparation')
    assert.equal(await page.locator('.data-readiness').count(), 0)
    if (scenario === 'fresh') {
      await page.screenshot({ path: '/tmp/admirra-ai-one-click-idle.png' })
      await page.setViewportSize({ width: 390, height: 650 })
      await page.screenshot({ path: '/tmp/admirra-ai-one-click-mobile.png' })
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
    }
    await button.click()
    if (!['fresh', 'generation502'].includes(scenario)) {
      await page.getByText('Подготавливаем анализ…', { exact: true }).waitFor()
      assert.equal(await page.getByRole('button', { name: 'Получить комментарий', exact: true }).count(), 0)
      if (scenario === 'waiting') await page.screenshot({ path: '/tmp/admirra-ai-one-click-waiting.png' })
      if (scenario === 'scope') await page.evaluate(() => window.qaChangeScope())
      if (scenario === 'unmount') await page.evaluate(() => window.qaApp.unmount())
      await page.clock.fastForward(10001)
    }
    if (['fresh', 'waiting'].includes(scenario)) {
      await page.getByText('Готовый комментарий по выбранному периоду.', { exact: true }).waitFor()
      assert.equal(calls.filter(c => c[0] === 'POST').length, 1)
    } else if (['failed', 'generation502'].includes(scenario)) {
      await page.getByRole('alert').waitFor()
      await page.getByRole('button', { name: 'Повторить', exact: true }).waitFor()
      await page.clock.fastForward(30000)
      assert.equal(calls.filter(c => c[0] === 'POST').length, scenario === 'failed' ? 0 : 1)
    } else assert.equal(calls.filter(c => c[0] === 'POST').length, 0)
    assert.deepEqual(errors, [])
    await page.close()
  }
  console.log('PASS: 6 real dashboard-panel scenarios, one click, no banners, scoped cancellation, no generation replay; desktop/mobile screenshots')
} finally { await browser?.close(); await server.close() }
