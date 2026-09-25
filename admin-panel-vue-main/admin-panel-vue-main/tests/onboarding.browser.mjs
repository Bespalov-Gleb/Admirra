// Actual UI components and lifecycle; isolated synthetic account, no outside IO.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import os from 'node:os'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
assert.equal(process.env.WW_TEST,'1');assert.ok(process.env.WW_TEST_ID)
const require=createRequire(import.meta.url)
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright')
const root=fileURLToPath(new URL('../',import.meta.url))
const mocks={
  useAuth:`import {ref} from 'vue';const user=ref({id:'synthetic'});export const useAuth=()=>({user,getToken:()=>window.qaToken,logout:async()=>{user.value=null}});`,
  axios:`export default {get:async(url)=>{window.qaGets.push(url);return {data:url==='billing/signup-discount'?structuredClone(window.qaState):{count:0}}},post:async(url,body)=>{if(url.includes('claim-display')){window.qaClaims++;const show=!window.qaState.toast_seen;window.qaState.toast_seen=true;return {data:{show}}}const name=body?.name;const first=!window.qaMilestones.includes(name);window.qaMilestones.push(name);return {data:{first}}}};`,
  useProjects:`export const useProjects=()=>({fetchProjects:async()=>[],setCurrentProject:()=>{}});`,
  createProject:`export async function createProjectWithOverflow(){window.qaState.projects_count=1;return {data:{id:'project-synthetic',owner_project_count:1}}}`,
}
const html=`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h,computed} from 'vue';import {createRouter,createMemoryHistory,RouterView} from 'vue-router';
import '/src/style.css';import Sidebar from '/src/components/SidebarV2.vue';import Lifecycle from '/src/components/SignupDiscount.vue';
import Create from '/src/views/Mockup/Create.vue';import Offer from '/src/components/IntegrationOffer.vue';import Prompt from '/src/components/ConnectAccountPrompt.vue';
import Toaster from '/src/components/ui/Toaster.vue';import {useOnboarding} from '/src/composables/useOnboarding';import {useSidebar} from '/src/composables/useSidebar';
import {useTheme} from '/src/composables/useTheme';
import {consumeOfferEntry} from '/src/utils/onboardingAnalytics';window.qaConsumeOffer=consumeOfferEntry;
window.qaState={trial_visible:true,trial_days_left:7,trial_total_days:7,trial_ends_at:new Date(Date.now()+604800000).toISOString(),projects_count:0,cabinets_count:0,eligible:true,active:false,discount_state:'not_granted'};
window.qaGets=[];window.qaClaims=0;window.qaMilestones=[];window.qaGoals=[];window.ym=(...args)=>window.qaGoals.push(args);
window.qaToken='e30.'+btoa(JSON.stringify({sub:'synthetic'}))+'.synthetic';sessionStorage.setItem('auth_token',window.qaToken);
const {state,refresh}=useOnboarding(),side=useSidebar();window.qaSide=side;window.qaTheme=useTheme();
window.qaSet=async patch=>{Object.assign(window.qaState,patch);window.dispatchEvent(new Event('admirra:onboarding-changed'));};
const routes=[{path:'/create',component:Create},{path:'/integrations/wizard',component:{render:()=>h('div',[h('h1','Новая интеграция'),h('p','Добавление рекламного канала'),h(Offer,{state:state.value}),h('div',{class:'qa-step'},'1 Проект')])}},
{path:'/dashboard/general-3',component:{render:()=>h(Prompt,{state:state.value,clientId:'project-synthetic'})}},...['/project-card','/project-rows','/tariffs'].map(path=>({path,component:{render:()=>h('p',path)}}))];
const router=createRouter({history:createMemoryHistory(),routes});window.qaRouter=router;
await router.push('/project-card');await router.isReady();
createApp({setup(){return()=>h('div',[h(Sidebar),h(Lifecycle),h('main',{class:'qa-main'},[h(RouterView)]),h(Toaster)])}}).use(router).mount('#app');
</script><style>.qa-main{margin-left:270px;padding:28px;background:#f5f6fa;min-height:100vh}h1{font-size:24px;margin:0 0 10px}p{margin-bottom:14px}.qa-step{padding:20px;background:white;border-radius:12px}@media(max-width:1023px){.qa-main{margin-left:0;padding:16px}}html{font-family:Arial,sans-serif}</style></body></html>`
const server=await createServer({root,configFile:false,plugins:[{
  name:'isolated-onboarding',enforce:'pre',resolveId(id){const key=id.split('/').at(-1).replace(/\.js$/,'');if(mocks[key])return '\0qa:'+key},
  load(id){if(id.startsWith('\0qa:'))return mocks[id.slice(4)]},
  configureServer(s){s.middlewares.use(async(req,res,next)=>{if(!req.url.startsWith('/__onboarding__'))return next();res.setHeader('Content-Type','text/html');res.end(await s.transformIndexHtml('/__onboarding__',html))})}
},vue()],resolve:{alias:{'@':path.join(root,'src')}},server:{host:'127.0.0.1',port:0,open:false}})
let browser
try {
 await server.listen();browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH})
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message))
 await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort())
 for(const width of [320,390,768,1440]){
  await page.setViewportSize({width,height:900});await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__onboarding__')
  await page.waitForSelector('.create-input');assert.equal(await page.locator('dialog[open],.signup-strip').count(),0)
  await page.evaluate(()=>{if(innerWidth<1024)window.qaSide.isMobileMenuOpen.value=true})
  await page.getByRole('button',{name:'Создать проект',exact:true}).first().waitFor({state:'visible'})
  assert.equal(await page.locator('.trial-card').count(),1)
  assert.equal(await page.locator('.trial-card p strong').textContent(),'закрепим скидку 20%')
  assert.equal(await page.locator('.trial-card p strong').evaluate(e=>getComputedStyle(e).display),'inline')
  await page.evaluate(()=>window.qaSide.isMobileMenuOpen.value=false)
  await page.locator('.create-input').fill('Синтетический проект');await page.locator('.create-btn').click()
  await page.waitForSelector('.integration-offer');assert.equal(await page.evaluate(()=>window.qaRouter.currentRoute.value.query.client_id),'project-synthetic')
  await page.evaluate(()=>window.qaRouter.push('/dashboard/general-3'));await page.locator('.connect-account-prompt button').click()
  assert.equal(await page.evaluate(()=>window.qaRouter.currentRoute.value.query.client_id),'project-synthetic')
  await page.locator('.integration-offer').click();await page.locator('.integration-offer').click()
  assert.equal(await page.evaluate(()=>window.qaGoals.filter(x=>x[2]==='signup_offer_click').length),1)
  assert.equal(await page.evaluate(()=>window.qaConsumeOffer()),true)
  assert.equal(await page.evaluate(()=>window.qaConsumeOffer()),false)
  for(let i=0;i<2;i++)await page.locator('.trial-card a').evaluate(e=>{e.addEventListener('click',ev=>ev.preventDefault(),{once:true});e.click()})
  assert.equal(await page.evaluate(()=>window.qaGoals.filter(x=>x[2]==='support_chat_click').length),1)
  await page.evaluate(()=>window.qaSet({active:true,discount_state:'granted',cabinets_count:1,expires_at:window.qaState.trial_ends_at}))
  await page.getByText(/Скидка 20% закреплена/).waitFor();assert.equal(await page.locator('.integration-offer').count(),0)
  assert.equal(await page.evaluate(()=>window.qaClaims),1)
  await page.evaluate(()=>window.qaRouter.push('/tariffs'))
  await page.waitForFunction(()=>document.querySelector('.trial-card button')?.textContent==='Выбрать тариф')
  await page.evaluate(()=>window.qaSet({trial_days_left:0,active:false,eligible:false,discount_state:'expired'}))
  await page.getByText('Пробный период закончился',{exact:true}).waitFor({state:'attached'})
  await page.evaluate(()=>window.qaSet({trial_visible:false,discount_state:'used'}));await page.waitForFunction(()=>!document.querySelector('.trial-card'))
  await page.evaluate(()=>window.qaSet({trial_visible:true,trial_days_left:7,active:false,eligible:true,discount_state:'not_granted',projects_count:0,cabinets_count:0}))
  await page.evaluate(()=>window.qaRouter.push('/project-card'));await page.waitForSelector('.create-input')
  await page.evaluate(()=>window.qaSide.isMobileMenuOpen.value=true)
  await page.waitForSelector('.trial-card')
  await page.waitForFunction(()=>document.querySelector('aside').getBoundingClientRect().x>=0)
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)
  if(width===1440||width===390)for(const dark of [false,true]){
    await page.evaluate(d=>{window.qaTheme.isDarkMode.value=d},dark)
    await page.screenshot({path:path.join(os.tmpdir(),'admirra-onboarding-'+width+(dark?'-dark':'')+'.png')})
  }
  if(width===1440){
    // Short desktop viewport: the complete card and CTA must fit without scrolling.
    await page.setViewportSize({width,height:660})
    await page.evaluate(()=>window.qaTheme.isDarkMode.value=false)
    const layout=await page.locator('.trial-card').evaluate(card=>({
      height:card.getBoundingClientRect().height,
      bottom:card.getBoundingClientRect().bottom,
      visibleBottom:card.parentElement.getBoundingClientRect().bottom,
      overflow:card.parentElement.scrollHeight-card.parentElement.clientHeight,
    }))
    assert.ok(layout.height<=180,JSON.stringify(layout))
    assert.ok(layout.bottom<=layout.visibleBottom,JSON.stringify(layout))
    assert.ok(layout.overflow<=1,JSON.stringify(layout))
    await page.screenshot({path:path.join(os.tmpdir(),'admirra-onboarding-compact-660.png')})
    await page.evaluate(()=>window.qaSide.isCollapsed.value=true);await page.waitForFunction(()=>!document.querySelector('.trial-card'))
  }
 }
 assert.deepEqual(errors,[]);console.log('PASS: real sidebar/create/offer/prompt/toast lifecycle, 4 widths, themes, dedup, expiration, paid, navigation, no overflow/errors')
} finally {await browser?.close();await server.close()}
