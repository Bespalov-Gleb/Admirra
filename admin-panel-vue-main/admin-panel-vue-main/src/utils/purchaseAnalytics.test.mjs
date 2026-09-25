import { test } from 'node:test'
import assert from 'node:assert/strict'
import { trackPurchase } from './purchaseAnalytics.js'

let sequence=0
const payment = () => ({ payment_id: `test-${++sequence}`, amount:5520, list_price:6900, discount:1380,
  plan:'agency', sku:'basic_month', name:'Агентство', billing:'month', currency:'RUB', goal:'payment_success',signup_discount:true })
function browser() {
  const values=new Map(), calls=[]
  return { location:{hostname:'admirra.ru'},dataLayer:[],calls,
    sessionStorage:{getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)},
    ym:(...args)=>{ calls.push(args); args[4]?.() } }
}
test('actual revenue, stable sku, optional goal, no PII',async()=>{
  const win=browser(), p={...payment(),email:'never@send.invalid'}
  assert.equal(await trackPurchase(p,{win,goalIds:{payment_success:123}}),true)
  const purchase=win.dataLayer[0].ecommerce.purchase
  assert.deepEqual(purchase.actionField,{id:p.payment_id,revenue:5520,goal_id:123})
  assert.equal(purchase.products[0].discount,1380)
  assert.equal(purchase.products[0].id,'basic_month')
  assert.ok(!JSON.stringify(win.dataLayer).includes('never@send'))
  assert.equal(win.calls[0][3].order_price,5520)
})
test('dedup and navigation recovery',async()=>{
  const win=browser(),p=payment()
  await trackPurchase(p,{win}); await trackPurchase(p,{win})
  assert.equal(win.dataLayer.length,1)
  const q=payment(); win.sessionStorage.setItem('admirra:tracked-purchases:v1',JSON.stringify([q.payment_id]))
  assert.equal(await trackPurchase(q,{win}),false)
})
test('dev, blocked and invalid amounts never send',async()=>{
  for(const change of [{amount:0},{amount:'5520'},{amount:NaN},{currency:'USD'},{goal:'refund'}]){
    const win=browser(); assert.equal(await trackPurchase({...payment(),...change},{win}),false); assert.equal(win.dataLayer.length,0)
  }
  for(const hostname of ['localhost','staging.admirra.ru','127.0.0.1','admirra.online']){
    const win=browser(); win.location.hostname=hostname; assert.equal(await trackPurchase(payment(),{win}),false)
  }
  const win=browser(); delete win.ym; assert.equal(await trackPurchase(payment(),{win}),false)
})
test('upgrade preserves actual top-up',async()=>{
  const win=browser(),p={...payment(),goal:'plan_upgrade',amount:1000,discount:5900,coupon:'TEST'}
  await trackPurchase(p,{win})
  assert.equal(win.dataLayer[0].ecommerce.purchase.actionField.revenue,1000)
  assert.equal(win.calls[0][2],'plan_upgrade')
})
test('trial goal has actual amount and discount once, no replay on refresh',async()=>{
  const win=browser(),p={...payment(),trial_to_paid:true,discount_kind:'signup20'}
  await trackPurchase(p,{win});await trackPurchase(p,{win})
  const calls=win.calls.filter(c=>c[2]==='trial_to_paid')
  assert.equal(calls.length,1);assert.equal(calls[0][3].discount,'signup20');assert.equal(calls[0][3].order_price,5520)
})
