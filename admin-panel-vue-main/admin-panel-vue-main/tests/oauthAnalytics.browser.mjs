// Actual OAuth callbacks/composable and analytics helper; no provider/marketing IO.
import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
import {createServer} from 'vite'
import vue from '@vitejs/plugin-vue'
assert.equal(process.env.WW_TEST,'1');assert.ok(process.env.WW_TEST_ID)
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE||'playwright')
const root=fileURLToPath(new URL('../',import.meta.url))
const mocks={
 useAuth:`export const useAuth=()=>({setToken:t=>window.qaInstalled=t,fetchCurrentUser:async()=>({success:true,data:{created_at:new Date().toISOString()}}),getErrorMessage:()=> 'synthetic error'});`,
 axios:`export const refreshAccessToken=async()=>{};export default {get:async(url)=>({data:url.endsWith('authorize-url')?{url:'https://max.ru/synthetic',state:'synthetic',poll_interval_ms:1000}:window.qaResponse}),post:async(url)=>{window.qaCalls.push(url);return {data:url.includes('auth/oauth/')?window.qaResponse:{client_id:'synthetic-project'}}}};`,
}
const html=`<html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';import {createRouter,createMemoryHistory,RouterView} from 'vue-router';
import Callback from '/src/views/Auth/YandexCallback.vue';import OAuthCallback from '/src/views/Auth/OAuthLoginCallback.vue';
import {useOAuthLogin} from '/src/composables/useOAuthLogin';
const q=new URLSearchParams(location.search),kind=q.get('kind'),flag=q.get('flag');
window.qaEvents=[];window.qaCalls=[];window.qaIdentity=[];window.qaDone=false;
window.qaToken='e30.'+btoa(JSON.stringify({sub:'synthetic@example.test'}))+'.synthetic';
window.qaResponse={status:'completed',access_token:window.qaToken};if(flag!=='missing')window.qaResponse.is_new_user=flag==='new';
window.ym=(id,event,...args)=>{if(event==='getClientID')args[0]('synthetic-client-id');else window.qaEvents.push({id,event,args})};
localStorage.setItem('ym_yclid','synthetic-click-id');
if(kind==='yandex')sessionStorage.setItem('oauth_site_login','yandex');
const router=createRouter({history:createMemoryHistory(),routes:[
{path:'/auth/yandex/callback',component:Callback},
{path:'/auth/login/yandex/callback',component:OAuthCallback,meta:{oauthProvider:'yandex'}},
{path:'/:pathMatch(.*)*',component:{render:()=>h('div','complete')}}]});
window.qaRouter=router;
if(kind==='max'){
 window.open=()=>({location:{href:'about:blank'},close(){},focus(){}});
 await router.push('/signin');await router.isReady();
 createApp({render:()=>h(RouterView)}).use(router).mount('#app');
 await useOAuthLogin().startMaxLogin();window.qaDone=true;
}else{
 const p=kind==='generic'?'/auth/login/yandex/callback':'/auth/yandex/callback';
 if(kind==='link')sessionStorage.setItem('oauth_profile_link','yandex');
 await router.push({path:kind==='link'?'/auth/login/yandex/callback':p,query:{code:'synthetic',state:kind==='integration'?'integration-synthetic':'site-yandex_synthetic'}});
 await router.isReady();createApp({render:()=>h(RouterView)}).use(router).mount('#app');
}
</script></body></html>`
const server=await createServer({root,configFile:false,plugins:[{
name:'oauth-isolated',enforce:'pre',resolveId(id){const key=id.split('/').at(-1).replace(/\.js$/,'');if(mocks[key])return '\0qa:'+key},
load(id){if(id.startsWith('\0qa:'))return mocks[id.slice(4)]},
configureServer(s){s.middlewares.use(async(req,res,next)=>{if(!req.url.startsWith('/__oauth__'))return next();res.setHeader('Content-Type','text/html');res.end(await s.transformIndexHtml('/__oauth__',html))})}
},vue()],resolve:{alias:{'@':path.join(root,'src')}},server:{host:'127.0.0.1',port:0,open:false}})
let browser
try{
 await server.listen();browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH})
 const errors=[]
 for(const kind of ['yandex','generic','max','link','integration'])for(const flag of ['new','old','missing']){
  const page=await browser.newPage();page.on('pageerror',e=>errors.push(e.message));const identities=[]
  await page.route('**/*',r=>{
   const u=new URL(r.request().url());if(u.pathname==='/api/auth/metrika/identity'){
    identities.push({body:r.request().postDataJSON(),auth:r.request().headers().authorization});return r.fulfill({status:204})
   }
   return u.hostname==='127.0.0.1'?r.continue():r.abort()
  })
  await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__oauth__?kind='+kind+'&flag='+flag)
  if(kind==='max')await page.waitForFunction(()=>window.qaDone)
  else await page.waitForFunction(()=>window.qaRouter.currentRoute.value.path!==('/auth/'+(new URLSearchParams(location.search).get('kind')==='generic'||new URLSearchParams(location.search).get('kind')==='link'?'login/':'')+'yandex/callback'))
  const events=await page.evaluate(()=>window.qaEvents)
  const expected=flag==='new'&&!['link','integration'].includes(kind)
  assert.deepEqual(events.map(e=>e.event),expected?['reachGoal','reachGoal','reachGoal']:[],kind+'/'+flag)
  if(expected){assert.deepEqual(events.map(e=>e.args[0]),['signup_complete','signup','trial_start']);assert.ok(events.every(e=>e.id===109911357))}
  if(kind!=='integration'){
   await page.waitForFunction(()=>window.qaEvents!==undefined)
   assert.equal(identities.length,1,kind+'/'+flag)
   assert.equal(identities[0].auth,'Bearer '+await page.evaluate(()=>window.qaToken))
   assert.deepEqual(identities[0].body,{client_id:'synthetic-client-id',yclid:'synthetic-click-id'})
  }else assert.equal(identities.length,0)
  await page.close()
 }
 assert.deepEqual(errors,[]);console.log('PASS: 15 real callback/MAX scenarios, exact counter and goals, explicit token identity, no false registration on login/link/integration')
}finally{await browser?.close();await server.close()}
