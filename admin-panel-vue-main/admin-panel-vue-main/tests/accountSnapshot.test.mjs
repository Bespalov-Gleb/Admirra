import test from 'node:test'
import assert from 'node:assert/strict'
import { createAccountSnapshot } from '../src/utils/accountSnapshot.js'

const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b }); return {promise,resolve,reject} }
function setup() {
  let state, clock=1_000
  const requests=[]
  const store=createAccountSnapshot({load:()=>{const d=deferred();requests.push(d);return d.promise},publish:s=>{state=s},now:()=>clock})
  store.setAccount('one')
  return {store,requests,state:()=>state,advance:()=>{clock+=31_000}}
}
test('no invented balance; dedupe concurrent mounts and cache across layout remount', async()=>{
  const x=setup();assert.equal(x.state().data,null)
  const p=x.store.refresh();assert.equal(x.store.refresh(),p)
  x.requests[0].resolve({ai_requests_remaining:48});await p
  await x.store.refresh();assert.equal(x.requests.length,1);assert.equal(x.state().data.ai_requests_remaining,48)
  x.advance();const next=x.store.refresh();assert.equal(x.state().data.ai_requests_remaining,48)
  x.requests[1].resolve({ai_requests_remaining:47});await next
  assert.equal(x.state().data.ai_requests_remaining,47)
})
test('failed refresh preserves known values, failed initial request leaves unknown',async()=>{
  const x=setup();let p=x.store.refresh();x.requests[0].reject(Error('offline'));await p
  assert.equal(x.state().data,null);assert.equal(x.state().error,true)
  p=x.store.refresh();x.requests[1].resolve({ai_requests_remaining:48});await p
  p=x.store.refresh({force:true});x.requests[2].reject(Error('offline'));await p
  assert.equal(x.state().data.ai_requests_remaining,48);assert.equal(x.state().loading,false)
})
test('usage-change during an in-flight read queues one fresh read and discards older result',async()=>{
  const x=setup();const p=x.store.refresh()
  x.store.refresh({force:true});x.store.refresh({force:true})
  x.requests[0].resolve({ai_requests_remaining:48});await Promise.resolve();await Promise.resolve()
  assert.equal(x.requests.length,2);assert.equal(x.state().data,null)
  x.requests[1].resolve({ai_requests_remaining:47});await p
  assert.equal(x.state().data.ai_requests_remaining,47)
})
test('logout/account switch clears memory; late old-account responses cannot repopulate it',async()=>{
  const x=setup();const old=x.store.refresh()
  x.store.setAccount(null);assert.equal(x.state().data,null);await x.store.refresh();assert.equal(x.requests.length,1)
  x.store.setAccount('two');const next=x.store.refresh()
  x.requests[0].resolve({ai_requests_remaining:48});await old
  assert.equal(x.state().data,null);assert.equal(x.state().loading,true)
  x.requests[1].resolve({ai_requests_remaining:6});await next
  assert.equal(x.state().data.ai_requests_remaining,6)
  x.store.setAccount('two');assert.equal(x.state().data.ai_requests_remaining,6)
  x.store.setAccount('one');assert.equal(x.state().data,null)
})
