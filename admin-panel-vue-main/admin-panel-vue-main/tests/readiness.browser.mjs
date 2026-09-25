// Isolated component fixture. No auth, real API, sync, LLM or report operations.
// PLAYWRIGHT_MODULE can point to an existing Playwright runtime installation.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import os from 'node:os'
import { createServer } from 'vite'
const require = createRequire(import.meta.url)
assert.equal(process.env.WW_TEST, '1'); assert.ok(process.env.WW_TEST_ID)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const root = fileURLToPath(new URL('../', import.meta.url))
const fixture = `
import {createApp,ref,h} from 'vue';
import Detector from '@/components/DetectorBanner.vue';
import Notice from '@/components/DataReadinessNotice.vue';
const issues=ref([]), mode=ref('detector'), key=ref(0), readiness=ref(null);
let refreshes=0, actions=0, completions=0, remove=true;
window.probe={
 setup(value, generic=false, autoRemove=true){key.value++;refreshes=actions=completions=0;remove=autoRemove;mode.value=generic?'action':'detector';readiness.value=value;issues.value=value?[{text:value.message||'old text',data_readiness:value}]:[{text:'Полнота данных не подтверждена. Обновите данные проекта.'}];},
 replace(value){readiness.value=value;issues.value=[{text:'old text',data_readiness:value}];},
 unmount(){mode.value='none'},
 stats(){return {refreshes,actions,completions}},
 hidden(value){Object.defineProperty(document,'hidden',{configurable:true,value});document.dispatchEvent(new Event('visibilitychange'));}
};
createApp({setup(){return ()=>h('main',{style:'max-width:1100px;margin:20px auto;padding:12px'},[
 h('h2','Отчёт: БВК Новый / ВК'),
 mode.value==='detector'&&issues.value.length?h(Detector,{key:key.value,syncIssues:issues.value,onRefreshData(){refreshes++;if(remove)issues.value=[]}}):null,
 mode.value==='action'?h(Notice,{key:key.value,readiness:readiness.value,onReady(){completions++},onReadyAction(){actions++}}):null
])}}).mount('#app');
`
const server = await createServer({
  root, configFile:path.join(root,'vite.config.js'),
  server:{host:'127.0.0.1',port:0,open:false},
  plugins:[{name:'isolated-readiness-fixture',
    resolveId(id){if(id==='virtual:readiness-fixture')return '\0virtual:readiness-fixture'},
    load(id){if(id==='\0virtual:readiness-fixture')return fixture},
    configureServer(s){s.middlewares.use('/__readiness_probe__',(_req,res)=>{
      res.setHeader('Content-Type','text/html');
      res.end('<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;font:14px Arial;background:#f5f6fa;color:#252d3d}body.dark{background:#111827;color:#eee}</style><div id="app"></div><script type="module" src="/@id/__x00__virtual:readiness-fixture"></script></html>')
    })},
  }],
})
let browser
try {
 await server.listen()
 const port=server.httpServer.address().port
 browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})})
 const page=await browser.newPage({viewport:{width:1100,height:700}})
 const errors=[], calls=[]
 page.on('pageerror',e=>errors.push(e.message))
 let response, fail=false
 await page.route('**/*', async route=>{
   const u=new URL(route.request().url())
   if(u.hostname!=='127.0.0.1')return route.abort()
   if(u.pathname.startsWith('/api/')){
     calls.push({path:u.pathname,method:route.request().method()})
     assert.match(u.pathname,/^\/api\/data-refresh\/request(?:\/retry)?$/)
     return fail?route.fulfill({status:503,json:{}}):route.fulfill({json:response})
   }
   return route.continue()
 })
 await page.clock.install()
 await page.goto('http://127.0.0.1:'+port+'/__readiness_probe__')
 await page.waitForFunction(()=>!!window.probe)
 const waiting={id:'request',status:'waiting',deadline:new Date(Date.now()+3600000).toISOString(),message:'Обновляем недостающие данные. Повторите действие после завершения.'}
 const setup=async(v,generic=false,remove=true)=>{await page.evaluate(({v,generic,remove})=>window.probe.setup(v,generic,remove),{v,generic,remove});await page.waitForTimeout(10)}
 await setup(waiting)
 assert.equal(await page.getByText('Анализируем данные…',{exact:true}).count(),1)
 assert.equal(await page.locator('.data-readiness').count(),0)
 assert.equal(await page.locator('.detector-banner__hypothesis').count(),0)
 assert.equal(await page.locator('.data-readiness small').count(),0)
 assert.equal(await page.locator('.detector-banner').evaluate(e=>getComputedStyle(e).borderTopWidth),'0px')
 assert.equal(await page.locator('.detector-banner__title').evaluate(e=>getComputedStyle(e).textTransform),'none')
 await page.screenshot({path:path.join(os.tmpdir(),'admirra-readiness-desktop.png')})
 await page.setViewportSize({width:390,height:700})
 await page.screenshot({path:path.join(os.tmpdir(),'admirra-readiness-mobile.png')})
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)
 await page.evaluate(()=>document.body.classList.add('dark'))
 await page.waitForFunction(()=>getComputedStyle(document.querySelector('.detector-banner--sync')).backgroundColor==='rgba(0, 0, 0, 0)')
 assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),'rgb(17, 24, 39)')
 assert.equal(await page.locator('.data-readiness').count(),0)
 await page.waitForFunction(()=>getComputedStyle(document.querySelector('.detector-banner__title')).color==='rgb(194, 204, 218)')
 await page.screenshot({path:path.join(os.tmpdir(),'admirra-readiness-dark.png')})
 await page.evaluate(()=>document.body.classList.remove('dark'))
 response={...waiting,status:'ready'}
 await page.clock.fastForward(30001)
 await page.waitForFunction(()=>window.probe.stats().refreshes===1)
 await page.waitForFunction(()=>!document.querySelector('.detector-banner'))
 assert.deepEqual(calls,[{path:'/api/data-refresh/request',method:'GET'}])
 await page.clock.fastForward(60001)
 assert.equal(calls.length,1)
 // Same receipt does not loop if parent still shows it (e.g. refresh failed).
 await setup(response,false,false)
 await page.waitForFunction(()=>window.probe.stats().refreshes===1)
 await page.evaluate(v=>window.probe.replace(v),response)
 await page.waitForTimeout(10)
 assert.equal((await page.evaluate(()=>window.probe.stats())).refreshes,1)
 // Generic consumer readiness cannot invoke a paid action automatically.
 await setup(waiting,true)
 assert.equal(await page.locator('.data-readiness small').count(),1)
 await page.clock.fastForward(30001)
 await page.waitForFunction(()=>window.probe.stats().completions===1)
 assert.equal((await page.evaluate(()=>window.probe.stats())).actions,0)
 await page.getByRole('button',{name:'Повторить действие',exact:true}).click()
 assert.equal((await page.evaluate(()=>window.probe.stats())).actions,1)
 // Hidden tabs stop polling; resume performs one status read.
 await setup(waiting)
 let before=calls.length
 await page.evaluate(()=>window.probe.hidden(true))
 await page.clock.fastForward(60001)
 assert.equal(calls.length,before)
 await page.evaluate(()=>window.probe.hidden(false))
 await page.waitForFunction(()=>window.probe.stats().refreshes===1)
 assert.equal(calls.length,before+1)
 // Error stops retries until explicit user action, not a tight request loop.
 fail=true
 await setup(waiting)
 await page.clock.fastForward(30001)
 await page.getByRole('button',{name:'Проверить статус',exact:true}).waitFor()
 await page.getByText('Не удалось проверить данные',{exact:true}).waitFor()
 assert.equal(await page.locator('.detector-banner--preparing').count(),0)
 before=calls.length
 await page.clock.fastForward(60001)
 assert.equal(calls.length,before)
 fail=false
 await page.getByRole('button',{name:'Проверить статус',exact:true}).click()
 await page.waitForFunction(()=>window.probe.stats().refreshes===1)
 // Held state offers only explicit, permission-controlled preparation retry.
 await setup({...waiting,status:'held',can_retry:true})
 assert.equal(await page.getByText('Подготовка истории приостановлена',{exact:true}).count(),1)
 before=calls.length
 await page.clock.fastForward(60001)
 assert.equal(calls.length,before)
 response={...waiting,status:'waiting'}
 await page.getByRole('button',{name:'Повторить подготовку данных',exact:true}).click()
 await page.getByText('Анализируем данные…',{exact:true}).waitFor()
 assert.deepEqual(calls.at(-1),{path:'/api/data-refresh/request/retry',method:'POST'})
 await page.evaluate(()=>window.probe.unmount())
 before=calls.length
 await page.clock.fastForward(60001)
 assert.equal(calls.length,before)
 await setup(null)
 assert.equal(await page.getByText('Проверяем полноту данных для детектора',{exact:true}).count(),1)
 assert.deepEqual(errors,[])
 console.log(JSON.stringify({passed:true,automaticDetectorRefresh:true,paidActionsRequireClick:true,hiddenTabsPaused:true,unmountStopsPolling:true,duplicateText:false,mobileOverflow:false,apiCalls:calls}))
} finally {
 await browser?.close()
 await server.close()
}
