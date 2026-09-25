// Isolated UI fixture: no credentials, production API or real projects.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import os from 'node:os'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
assert.equal(process.env.WW_TEST, '1')
assert.ok(process.env.WW_TEST_ID)
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const root = fileURLToPath(new URL('../', import.meta.url))
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>
html{font-size:67.5%}*{box-sizing:border-box}body{margin:0;background:#f5f6fa;font-family:Arial,sans-serif}button{font:inherit;color:inherit;cursor:pointer}button,p{margin:0}button{background:none;border:0;padding:0}svg{width:20px;height:20px}.mobile-workspace{--m:var(--mw-unit)}.projects-tile-grid{display:grid}.qa-header{background:white;padding:18px 12px;font-size:18px;font-weight:600}
</style></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';
import Tile from '/src/components/mobile/MobileProjectTile.vue';
import Bar from '/src/components/mobile/MobileSliceBar.vue';
import '/src/components/mobile/mobile.css';
const params=new URLSearchParams(location.search),n=Number(params.get('channels')??1),folder=params.has('folder');
const icon='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><circle cx="16" cy="16" r="16" fill="#3674f5"/></svg>');
window.qaEvents=[];
createApp({render:()=>h('main',{class:'mobile-workspace mobile-projects'},[
h('div',{class:'qa-header'},'Все проекты'),h(Bar,{period:'this_week',vat:true}),
h('div',{class:'projects-tile-grid'},[h(Tile,{
project:{id:'qa',name:folder?'Like Store | Яндекс':'БВК Новый / ВК',__isFolder:folder,description:folder?'Папка · 14 проектов':''},initials:folder?'📁':'БВК',
stats:[{key:'cpa',label:'Сводный CPL',value:'1 498 ₽'},{key:'leads',label:'Лиды',value:'4',delta:'↑ 1 шт',previous:'3',tone:'good'},{key:'expenses',label:'Расход',value:'5 992 ₽'},{key:'cr',label:'CR в лид',value:'1,99%'}],
channels:Array.from({length:n},(_,i)=>({code:String(i),name:i?'Яндекс Директ':'VK Реклама',icon,spendText:'5 992 ₽',goalTotal:4,cplText:'1 498 ₽',needsGoalSelection:params.has('unconfigured')})),
balances:[{code:'vk',icon,name:'VK',value:'52 028 ₽'}],traffic:{impressions:'49 611',clicks:'201',cpc:'29 ₽',details:[]},folders:[],alerts:[],
onOpen:()=>window.qaEvents.push('open'),onReport:()=>window.qaEvents.push('report'),onSettings:()=>window.qaEvents.push('settings')})])])}).mount('#app');
</script></body></html>`
const server=await createServer({root,configFile:false,plugins:[vue(),{
  name:'isolated-mobile-cards',configureServer(s){s.middlewares.use(async(req,res,next)=>{
    if(!req.url.startsWith('/__mobile_cards__'))return next()
    res.setHeader('Content-Type','text/html');res.end(await s.transformIndexHtml('/__mobile_cards__',html))
  })}
}],resolve:{alias:{'@':path.join(root,'src')}},server:{host:'127.0.0.1',port:0,open:false}})
let browser
try{
  await server.listen()
  browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})})
  const page=await browser.newPage(), errors=[]
  page.on('pageerror',e=>errors.push(e.message))
  await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort())
  for(const width of [320,375,390,430]){
    await page.setViewportSize({width,height:844})
    for(const suffix of ['', '&folder', '&channels=2', '&channels=0', '&unconfigured']){
      await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__mobile_cards__?test=1${suffix}`)
      await page.waitForSelector('.mw-project-actions')
      assert.equal(await page.locator('.mw-channel').count(),suffix.includes('channels=2')?2:0)
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)
      const buttons=page.locator('.mw-project-actions > button')
      assert.deepEqual(await buttons.evaluateAll(es=>es.map(e=>e.getAttribute('aria-label')||e.textContent.trim())),
        suffix==='&folder'?['Настройки проекта','Отчёт','Аналитика']:['Другие действия','Настройки проекта','Отчёт','Аналитика'])
      assert.ok(await buttons.evaluateAll(es=>es.every(e=>e.scrollWidth<=e.clientWidth+1)))
      for(const [name,event] of [['Настройки проекта','settings'],['Отчёт','report'],['Аналитика','open']]){
        await page.getByRole('button',{name,exact:true}).click()
        assert.equal((await page.evaluate(()=>window.qaEvents)).at(-1),event)
      }
      if(suffix==='&unconfigured')assert.equal(await page.getByText('VK Реклама: цели не выбраны',{exact:true}).count(),1)
      assert.ok(await page.locator('.mw-balances').isVisible())
      const gap=await page.locator('.mw-slice').evaluate(e=>e.getBoundingClientRect().bottom-e.querySelector('.mw-period-pill').getBoundingClientRect().bottom)
      assert.ok(gap>=8,`period bottom gap ${gap}`)
      if(width===390&&!suffix)await page.screenshot({path:path.join(os.tmpdir(),'admirra-mobile-cards-release.png')})
      if(!suffix){
        await page.getByRole('button',{name:'Другие действия',exact:true}).click()
        assert.ok(await page.getByText('Действия с проектом',{exact:true}).isVisible())
      }
    }
  }
  assert.deepEqual(errors,[])
  console.log('PASS: 20 mobile variants, layout, channel states, actions, period spacing, no JS errors')
}finally{await browser?.close();await server.close()}
