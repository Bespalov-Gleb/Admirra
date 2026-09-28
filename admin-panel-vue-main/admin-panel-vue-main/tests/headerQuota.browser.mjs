// Real Header and shared composable; isolated account/API, no production traffic.
import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
import os from 'node:os'
import {createServer} from 'vite'
import vue from '@vitejs/plugin-vue'
assert.equal(process.env.WW_TEST,'1');assert.ok(process.env.WW_TEST_ID)
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE||'playwright')
const root=fileURLToPath(new URL('../',import.meta.url))
const mocks={
 useAuth:`import {ref} from 'vue';const user=ref({id:'one',first_name:'Test'});window.qaUser=user;export const useAuth=()=>({user,logout:async()=>{user.value=null}});`,
 useProjects:`import {ref} from 'vue';const projects=ref([]);export const useProjects=()=>({projects,currentProjectId:ref(null),currentProject:ref(null),currentProjectName:ref('Сводка'),fetchProjects:async()=>{},setCurrentProject:()=>{}});`,
 axios:`export default {get:async(url)=>{const r=await fetch('/api/'+url);if(!r.ok)throw Error('HTTP '+r.status);return {data:await r.json()}}}`,
}
const html=`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';import {createRouter,createMemoryHistory} from 'vue-router';import Header from '/src/components/Header.vue';import '/src/style.css';
const router=createRouter({history:createMemoryHistory(),routes:['/dashboard/general-3','/integrations'].map(path=>({path,component:{render:()=>null}}))});await router.push('/dashboard/general-3');window.qaRouter=router;
createApp({render:()=>h(Header,{key:router.currentRoute.value.path})}).use(router).mount('#app');
</script></body></html>`
const server=await createServer({root,configFile:false,plugins:[{
 name:'header-quota-fixture',enforce:'pre',resolveId(id){const key=id.split('/').at(-1).replace(/\.js$/,'');if(mocks[key])return '\0qa:'+key},load(id){if(id.startsWith('\0qa:'))return mocks[id.slice(4)]},
 configureServer(s){s.middlewares.use(async(req,res,next)=>{if(req.url!='/__quota')return next();res.setHeader('Content-Type','text/html');res.end(await s.transformIndexHtml('/__quota',html))})}
},vue()],resolve:{alias:{'@':path.join(root,'src')}},server:{host:'127.0.0.1',port:0,open:false}})
let browser,release
try{
 await server.listen();browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH})
 const page=await browser.newPage({viewport:{width:1600,height:900}}),errors=[]
 page.on('pageerror',e=>errors.push(e.message))
 let calls=0,remaining=48,fail=false,hold=true
 await page.route('**/*',async route=>{
  const u=new URL(route.request().url());if(u.hostname!=='127.0.0.1')return route.abort()
  if(!u.pathname.startsWith('/api/'))return route.continue()
  if(u.pathname.endsWith('billing/subscription')){
   calls++;if(hold)await new Promise(r=>{release=r})
   return route.fulfill(fail?{status:503,json:{}}:{json:{plan_name:'Старт',projects_used:2,max_projects:3,cabinets_used:2,max_cabinets:9,ai_requests_used:50-remaining,max_ai_requests_per_period:50,ai_requests_remaining:remaining}})
  }
  return route.fulfill({json:u.pathname.includes('folders')?{folders:[],root_projects:[]}:[]})
 })
 await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__quota')
 const balance=page.locator('.usage-gauge').nth(1).locator('.usage-num')
 await balance.waitFor();assert.equal(await balance.textContent(),'—');assert.equal(calls,1)
 hold=false;release();await page.waitForFunction(()=>document.querySelectorAll('.usage-num')[1]?.textContent==='48')
 await page.evaluate(()=>{window.qaSeen=[];new MutationObserver(()=>window.qaSeen.push(document.querySelectorAll('.usage-num')[1]?.textContent)).observe(document.querySelector('#app'),{subtree:true,childList:true,characterData:true})})
 for(const p of ['/integrations','/dashboard/general-3','/integrations']){
  await page.evaluate(p=>window.qaRouter.push(p),p);assert.equal(await balance.textContent(),'48')
 }
 assert.equal(calls,1);assert.equal((await page.evaluate(()=>window.qaSeen)).includes('30'),false)
 fail=true;await page.evaluate(()=>dispatchEvent(new Event('admirra:ai-usage-changed')))
 await page.waitForFunction(()=>document.querySelector('.usage-chip')?.getAttribute('title')?.includes('Не удалось'))
 assert.equal(await balance.textContent(),'48')
 fail=false;remaining=47;await page.evaluate(()=>dispatchEvent(new Event('admirra:ai-usage-changed')))
 await page.waitForFunction(()=>document.querySelectorAll('.usage-num')[1]?.textContent==='47')
 await page.screenshot({path:path.join(os.tmpdir(),'admirra-header-quota.png')})
 hold=true;await page.evaluate(()=>{window.qaUser.value={id:'two',first_name:'Other'}})
 await page.waitForFunction(()=>document.querySelectorAll('.usage-num')[1]?.textContent==='—')
 for(let i=0;calls<4&&i<100;i++)await new Promise(r=>setTimeout(r,20))
 assert.equal(calls,4)
 remaining=6;hold=false;release();await page.waitForFunction(()=>document.querySelectorAll('.usage-num')[1]?.textContent==='6')
 assert.deepEqual(errors,[])
 console.log(JSON.stringify({passed:true,layoutRemounts:3,initialRequests:1,noFake30:true,errorPreservesQuota:true,aiUsageRefresh:true,accountIsolation:true}))
}finally{release?.();await browser?.close();await server.close()}
