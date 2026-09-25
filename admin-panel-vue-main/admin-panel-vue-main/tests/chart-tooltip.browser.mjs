// Real tooltip composable + dashboard styles + production hover handler;
// synthetic series only, isolated scroll container, no auth or API requests.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { parse } from '@vue/compiler-sfc'
assert.equal(process.env.WW_TEST,'1');assert.ok(process.env.WW_TEST_ID)
const root=fileURLToPath(new URL('../',import.meta.url))
const source=fs.readFileSync(path.join(root,'src/views/GeneralStats3/GeneralStats3.vue'),'utf8')
const css=parse(source).descriptor.styles.map(s=>s.content).join('\n')
const handler=source.slice(source.indexOf('const handleChartHover ='),source.indexOf('const formatChartMetricValue ='))
assert.match(source,/@pointercancel="dismissChartTooltip"/)
assert.match(source,/watch\(chartSvgRef, svg =>/)
const fixture=`import {createApp,h,ref,computed,nextTick} from 'vue';
import {useContainedChartTooltip} from '/src/composables/useContainedChartTooltip.js';
import '/src/components/mobile/mobile.css';
import '/src/components/mobile/dashboard.css';
const app=createApp({setup(){
const chartHoverIndex=ref(-1),chartSvgRef=ref(null),chartAreaRef=ref(null),chartTooltipRef=ref(null),all=ref(false);
const chartViewWidth=ref(320),chartPoints=ref([{x:44,y:260},{x:160,y:140},{x:308,y:10}]);
const {style:chartTooltipStyle,dismiss:dismissChartTooltip}=useContainedChartTooltip({area:chartAreaRef,svg:chartSvgRef,tooltip:chartTooltipRef,index:chartHoverIndex,point:computed(()=>chartHoverIndex.value<0?null:chartPoints.value[chartHoverIndex.value]),width:computed(()=>all.value?272:220)});
${handler}
window.probe={show(i,a=false){all.value=a;chartHoverIndex.value=i},dismiss:dismissChartTooltip};
return()=>h('div',{class:'mobile-dashboard figma-dashboard'},[h('div',{class:'chart-goals-grid'},[h('section',{class:['panel','chart-panel',all.value?'chart-panel--all-channels':'']},[
h('h2','Эффективность кампаний'),h('div',{ref:chartAreaRef,class:'chart-area',onPointerdown:handleChartHover,onPointermove:handleChartHover,onPointercancel:dismissChartTooltip},[
h('svg',{ref:chartSvgRef,viewBox:'0 0 320 300',preserveAspectRatio:'xMidYMid meet'},[
h('path',{d:'M 34 10 V 264 H 316',stroke:'#dce2ec',fill:'none'}),h('path',{d:'M 44 260 L 160 140 L 308 10',stroke:'#2f6bea',fill:'none','stroke-width':3}),
...[44,160,308].map((x,i)=>h('text',{x,y:290,'text-anchor':'middle',fill:'#65738a'},['23 сен','24 сен','25 сен'][i]))]),
chartHoverIndex.value>=0?h('div',{ref:chartTooltipRef,class:'chart-tooltip',style:chartTooltipStyle.value},[
h('div',{class:'chart-tooltip__date'},'25 сентября'),...['Расход|15 920 ₽','Лиды|24','CPL|663,33 ₽','Клики|812'].map(t=>h('div',{class:'chart-tooltip__main'},all.value?[h('i',{class:'chart-tooltip__marker'}),h('span',t.split('|')[0]),h('strong',t.split('|')[1])]:[h('i',{class:'chart-tooltip__dot'}),t.replace('|',' — ')]))]):null])])])])}});
app.mount('#app');window.dispose=()=>app.unmount();`
const server=await createServer({root,configFile:false,plugins:[vue(),{
name:'chart-tooltip-fixture',resolveId(id){if(id==='virtual:chart-tooltip')return '\0virtual:chart-tooltip'},load(id){if(id==='\0virtual:chart-tooltip')return fixture},
configureServer(s){s.middlewares.use('/__chart__',(_q,r)=>{r.setHeader('Content-Type','text/html; charset=utf-8');r.end('<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'\nhtml{font-size:67.5%}*{box-sizing:border-box}body{margin:0;background:#f4f6f8;font-family:Arial}.scroll-host{height:100vh;overflow:auto}.spacer{height:800px}.before{height:100px}.chart-panel{max-width:none !important}button{height:44px}</style><div class="scroll-host"><button id="outside">Вне графика</button><div class="before"></div><div id="app"></div><div class="spacer"></div></div><script type="module" src="/@id/__x00__virtual:chart-tooltip"></script></html>')})}
}],resolve:{alias:{'@':path.join(root,'src')}},optimizeDeps:{noDiscovery:true,include:['vue']},server:{host:'127.0.0.1',port:0,open:false}})
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE||'playwright')
let browser
try{
await server.listen();browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH})
const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message))
await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort())
for(const width of [320,375,390,430,1200]){
await page.setViewportSize({width,height:844});await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__chart__');await page.waitForFunction(()=>!!window.probe)
const show=async(i=1,all=false)=>{await page.evaluate(({i,all})=>window.probe.show(i,all),{i,all});await page.locator('.chart-tooltip').waitFor();await page.waitForTimeout(50)}
for(const all of [false,true])for(const i of [0,1,2]){
await show(i,all)
const bounds=await page.locator('.chart-area').boundingBox(),tip=await page.locator('.chart-tooltip').boundingBox()
assert.ok(tip.x>=bounds.x+7&&tip.y>=bounds.y+7,JSON.stringify({width,all,i,bounds,tip,style:await page.locator('.chart-tooltip').getAttribute('style')}))
assert.ok(tip.x+tip.width<=bounds.x+bounds.width-7&&tip.y+tip.height<=bounds.y+bounds.height-7)
assert.equal(await page.locator('.chart-tooltip').evaluate(e=>e.scrollHeight>e.clientHeight+1),false)
}
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)
if(width<=430){
const sizes=await page.locator('.chart-panel').evaluate(p=>({panel:p.clientWidth,area:p.querySelector('.chart-area').clientWidth}))
assert.ok(sizes.panel-sizes.area<=17)
}
if(width===390){await show(1,false);await page.screenshot({path:path.join(os.tmpdir(),'admirra-chart-tooltip-mobile.png')})}
await page.evaluate(()=>document.querySelector('.scroll-host').scrollTop=40);await page.waitForFunction(()=>!document.querySelector('.chart-tooltip'))
await show();await page.locator('#outside').dispatchEvent('pointerdown');await page.waitForFunction(()=>!document.querySelector('.chart-tooltip'))
await show();await page.keyboard.press('Escape');assert.equal(await page.locator('.chart-tooltip').count(),0)
await show();await page.locator('.chart-area').dispatchEvent('pointercancel',{pointerType:'touch'});assert.equal(await page.locator('.chart-tooltip').count(),0)
await show();await page.locator('.chart-area').dispatchEvent('pointermove',{pointerType:'touch',clientX:100,clientY:200});assert.equal(await page.locator('.chart-tooltip').count(),0)
await page.locator('.chart-area').dispatchEvent('pointerdown',{pointerType:'touch',clientX:width/2,clientY:200});await page.locator('.chart-tooltip').waitFor()
await page.setViewportSize({width:width+1,height:844});await page.waitForFunction(()=>!document.querySelector('.chart-tooltip'))
await page.evaluate(()=>window.dispose());await page.locator('#outside').dispatchEvent('pointerdown')
}
assert.deepEqual(errors,[]);console.log('PASS: 30 positions, chart bounds, wider plot, nested scroll, outside tap, Escape, gesture cancel/move, resize, unmount')
}finally{await browser?.close();await server.close()}
