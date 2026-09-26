// Actual dashboard dropdown/manager markup + actual data composable, synthetic API only.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import os from 'node:os'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
const require = createRequire(import.meta.url)
assert.equal(process.env.WW_TEST, '1'); assert.ok(process.env.WW_TEST_ID)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const root = fileURLToPath(new URL('../', import.meta.url))
const source = readFileSync(path.join(root, 'src/views/GeneralStats3/GeneralStats3.vue'), 'utf8')
const menu = source.slice(source.indexOf('        <div\n          v-if="directionsEnabled"'), source.indexOf('        <!-- Капсула кампаний'))
const manager = source.slice(source.indexOf('      <div\n        v-if="directionManagerOpen"'), source.indexOf('      <!-- Report channel link modal -->'))
const css = source.match(/<style scoped>([\s\S]*?)<\/style>/)?.[1] || ''
const fixture = `<template><main>${menu}${manager}</main></template><script setup>
import { ref, reactive, computed } from 'vue';
import { useDirectionData } from '@/composables/useDirectionData';
import { XMarkIcon, ChevronDownIcon } from '@heroicons/vue/24/outline';
const filters=reactive({client_id:'one',channel:'yandex',start_date:'2026-09-01',end_date:'2026-09-07'});
const api={get:async(url,config)=>{const response=await fetch('/api/'+url,{signal:config.signal});if(!response.ok)throw Error('failed');return {data:await response.json()}}};
const {directions,directionStats,directionOptions,directionsLoading,directionsError,fetchDirections}=useDirectionData(api,()=>filters);
const openMenu=ref('directions'), directionManagerOpen=ref(false), selectedDirectionId=ref(null), directionSuggestions=ref([]), directionSuggestionsLoading=ref(false), directionLabelSaving=ref(false), selectedDirectionLabelKey=ref('directions');
const directionsEnabled=true, directionLabelLower='направления', directionLabelOptions=[{key:'directions',label:'Направления'}];
const selectedDirectionLabel=computed(()=>directionOptions.value.find(x=>x.id===selectedDirectionId.value)?.name||'Все направления');
const unassignedDirection=null, vClickOutside={};
const toggleMenu=()=>{}, closeMenu=()=>{}, openDirectionEditor=()=>{}, saveDirectionLabel=()=>{}, loadDirectionSuggestions=()=>{}, applyDirectionSuggestion=()=>{}, moveDirection=()=>{}, deleteDirection=()=>{};
const selectDirection=item=>{selectedDirectionId.value=item?.id||null};
const openDirectionManager=()=>{directionManagerOpen.value=true;fetchDirections()};
window.probe={filters,openDirectionManager,selected:()=>selectedDirectionId.value};
</script><style scoped>${css}</style>`
const server = await createServer({ root, configFile: false, resolve: { alias: { '@': path.join(root, 'src') } }, server: { host: '127.0.0.1', port: 0, open: false },
  plugins: [{ name: 'directions-fixture', enforce: 'pre', resolveId(id) { if (id === '/__directions.vue') return id }, load(id) { if (id === '/__directions.vue') return fixture },
    configureServer(s) { s.middlewares.use(async (req, res, next) => {
      if (req.url !== '/__directions') return next()
      res.setHeader('Content-Type', 'text/html')
      res.end(await s.transformIndexHtml('/__directions', '<!doctype html><html><meta name="viewport" content="width=device-width, initial-scale=1"><style>*{box-sizing:border-box}body{font:14px Arial;background:#f5f6fa;margin:24px}main{max-width:1000px}</style><div id="app"></div><script type="module">import {createApp} from "vue";import App from "/__directions.vue";createApp(App).mount("#app")</script></html>'))
    }) } }, vue()],
})
let browser, releaseStats, releaseList
try {
  await server.listen()
  browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) })
  const page = await browser.newPage({ viewport: { width: 1100, height: 780 } })
  const errors = [], calls = []
  page.on('pageerror', e => errors.push(e.message))
  const rows = ['Газобетон', 'Профлист', 'Миксер', 'Ретаргет'].map((name, i) => ({ id: String(i), name, masks: [{ mask: name.toLowerCase() }], campaign_ids: ['c' + i], campaign_count: 1 }))
  let failList = false
  await page.route('**/*', async route => {
    const u = new URL(route.request().url())
    if (u.hostname !== '127.0.0.1') return route.abort()
    if (!u.pathname.startsWith('/api/')) return route.continue()
    calls.push(u.pathname)
    if (u.pathname.endsWith('/stats')) { await new Promise(r => { releaseStats = r }); return route.fulfill({ json: { items: [] } }).catch(() => {}) }
    if (!releaseList) await new Promise(r => { releaseList = r })
    return route.fulfill(failList ? { status: 503, json: {} } : { json: rows })
  })
  await page.goto('http://127.0.0.1:' + server.httpServer.address().port + '/__directions')
  await page.waitForFunction(() => !!window.probe)
  await page.getByRole('button', { name: 'Управление направлениями', exact: true }).click()
  await page.getByRole('dialog').getByText('Загружаем направления…').waitFor()
  assert.equal(await page.getByText('Направления пока не созданы').count(), 0)
  releaseList()
  await page.locator('.direction-manager-row').first().waitFor()
  assert.equal(await page.locator('.direction-manager-row').count(), 4)
  assert.equal(calls.length, 2) // Stats still pending, modal open did not restart list.
  await page.screenshot({ path: path.join(os.tmpdir(), 'admirra-directions-desktop.png') })
  await page.getByRole('button', { name: 'Закрыть', exact: true }).click()
  await page.locator('.direction-option').first().click()
  assert.equal(await page.evaluate(() => window.probe.selected()), '0')
  await page.evaluate(() => window.probe.openDirectionManager())
  assert.equal(calls.length, 2)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(os.tmpdir(), 'admirra-directions-mobile.png') })
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
  failList = true
  await page.evaluate(() => { window.probe.filters.client_id = 'two' })
  await page.getByRole('alert').waitFor()
  assert.equal(await page.locator('.direction-manager-row').count(), 0)
  assert.equal(await page.getByText('Направления пока не созданы').count(), 0)
  failList = false
  await page.getByRole('dialog').getByRole('button', { name: 'Повторить', exact: true }).click()
  await page.locator('.direction-manager-row').first().waitFor()
  assert.deepEqual(errors, [])
  console.log(JSON.stringify({ passed: true, rowsBeforeStats: 4, duplicateListRequests: 0, loadingAndRetry: true, mobileOverflow: false }))
} finally {
  releaseList?.(); releaseStats?.()
  await browser?.close(); await server.close()
}
