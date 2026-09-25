import test from 'node:test'
import assert from 'node:assert/strict'
import { createOAuthTracker } from '../src/utils/oauthAnalytics.js'
const token = sub => `e30.${Buffer.from(JSON.stringify({sub})).toString('base64url')}.synthetic`
function setup(goalOverride) {
  const events=[], identities=[], values=new Map()
  const deps={goal:goalOverride || ((...args)=>{events.push(args);return true}),identity:t=>identities.push(t),
    storage:{getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)}}
  return {deps,events,identities,track:createOAuthTracker(deps)}
}
for(const provider of ['yandex','vk','max']) test(`${provider}: new account once, login and linking never register`,()=>{
  const s=setup(),data={access_token:token('synthetic@example.test'),is_new_user:true}
  s.track(data,provider);s.track(data,provider);createOAuthTracker(s.deps)(data,provider)
  assert.deepEqual(s.events.map(x=>x[0]),['signup_complete','signup','trial_start'])
  assert.ok(s.events.every(x=>x[1].method===provider))
  s.track({...data,is_new_user:false},provider);s.track({access_token:data.access_token},provider)
  assert.equal(s.events.length,3);assert.equal(s.identities.length,5)
})
test('old backend without explicit flag is not a signup; accounts are independent',()=>{
  const s=setup();s.track({access_token:token('a')},'max');assert.equal(s.events.length,0)
  for(const sub of ['a','b'])s.track({access_token:token(sub),is_new_user:true},'max')
  assert.equal(s.events.length,6)
})
test('blocked storage and identity failures never break login or repeat events',()=>{
  let count=0
  const track=createOAuthTracker({goal:()=>{count++;return true},identity:()=>{throw Error()},
    storage:{getItem:()=>{throw Error()},setItem:()=>{throw Error()}}})
  const data={access_token:token('a'),is_new_user:true};track(data,'yandex');track(data,'yandex')
  assert.equal(count,3)
})
test('absent counter does not record a sent event',()=>{
  let enabled=false,count=0
  const s=setup(()=>{if(!enabled)return false;count++;return true})
  const data={access_token:token('a'),is_new_user:true};s.track(data,'vk');enabled=true;s.track(data,'vk')
  assert.equal(count,3)
})
test('invalid provider or unsuccessful response sends nothing',()=>{
  const s=setup();s.track({},'max');s.track({access_token:token('a'),is_new_user:true},'email')
  assert.equal(s.events.length,0);assert.equal(s.identities.length,0)
})
