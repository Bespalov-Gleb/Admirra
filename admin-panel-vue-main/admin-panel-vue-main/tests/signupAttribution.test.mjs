import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
const code = readFileSync(new URL('../public/signup-attribution.js', import.meta.url), 'utf8')
function browser() {
  let cookie='', writes=0, last=''
  const document={get cookie(){return cookie},set cookie(value){writes++;last=value;cookie=value.split(';')[0]}}
  const visit=url=>vm.runInNewContext(code,{URL,document,window:{location:new URL(url)},Date})
  return { visit, read:()=>JSON.parse(decodeURIComponent(cookie.split('=')[1])), writes:()=>writes, raw:()=>last }
}
test('first tagged visit survives signup, OAuth return, direct and later advertising visits',()=>{
 const b=browser()
 b.visit('https://admirra.ru/?utm_source=yandex&utm_medium=cpc&utm_campaign=Тест%20123')
 for(const path of ['/signup','/auth/yandex/callback?code=secret&state=secret','/?utm_source=vk'])b.visit('https://admirra.ru'+path)
 assert.equal(b.writes(),1);assert.equal(b.read().utm_source,'yandex');assert.equal(b.read().utm_campaign,'Тест 123')
 assert.match(b.raw(),/Path=\/; Max-Age=2592000; SameSite=Lax; Secure/)
 assert.equal(b.raw().includes('secret'),false)
})
test('direct and yclid-only visits do not invent attribution',()=>{
 const b=browser();b.visit('https://admirra.ru/?yclid=123');assert.equal(b.writes(),0)
 b.visit('https://admirra.ru/?utm_source=vk');assert.equal(b.read().utm_source,'vk')
})
test('unicode cookie stays within browser size limit',()=>{
 const b=browser();b.visit('https://admirra.ru/?'+new URLSearchParams({utm_source:'界'.repeat(1000),utm_medium:'界'.repeat(1000),utm_campaign:'界'.repeat(1000)}))
 assert.ok(b.raw().length<4096)
})
test('blocked cookies do not break the page',()=>{
 assert.doesNotThrow(()=>vm.runInNewContext(code,{URL,Date,document:{get cookie(){throw Error('blocked')}},window:{location:new URL('https://admirra.ru/?utm_source=x')}}))
})
