// Real collector + landing entry, isolated browser network. No signup/analytics sent.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
assert.equal(process.env.WW_TEST, '1'); assert.ok(process.env.WW_TEST_ID)
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE || 'playwright')
const script = readFileSync(new URL('../public/signup-attribution.js', import.meta.url), 'utf8')
const landing = readFileSync(new URL('../public/landing-new/index.html', import.meta.url), 'utf8')
const entry = readFileSync(new URL('../index.html', import.meta.url), 'utf8')
assert.ok(landing.includes('/signup-attribution.js?v=1'))
assert.ok(entry.includes('/signup-attribution.js?v=1'))
const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH})
try {
 for (const provider of ['email','yandex','vk','max']) {
  const context = await browser.newContext()
  const page = await context.newPage(), requests = []
  await context.route('**/*', async route => {
    const req=route.request(),u=new URL(req.url())
    if(u.hostname==='oauth.example.test')return route.fulfill({contentType:'text/html; charset=utf-8',body:'<a href="https://admirra.example.test/callback">Вернуться</a>'})
    if(u.hostname!=='admirra.example.test')return route.abort()
    if(u.pathname==='/signup-attribution.js')return route.fulfill({contentType:'text/javascript',body:script})
    if(u.pathname.startsWith('/api/')){requests.push(await req.allHeaders());return route.fulfill({json:{ok:true}})}
    if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:landing.replace(/<script(?![^>]*signup-attribution)[\s\S]*?<\/script>/g,'')})
    return route.fulfill({contentType:'text/html; charset=utf-8',body:'<script src="/signup-attribution.js?v=1"></script><a href="https://oauth.example.test/">Авторизация</a>'})
  })
  await page.goto('https://admirra.example.test/?utm_source=yandex&utm_medium=cpc&utm_campaign=Тест_123')
  await page.locator('a[href="/signup"]').first().click()
  await page.waitForURL('**/signup')
  if(['yandex','vk'].includes(provider)) {
    await page.getByText('Авторизация',{exact:true}).click()
    await page.getByText('Вернуться',{exact:true}).click()
    await page.waitForURL('**/callback')
  }
  const path=provider==='email'?'register':provider==='max'?'oauth/max/authorize-url':`oauth/${provider}/callback`
  await page.evaluate(path=>fetch('/api/auth/'+path,{method:path.endsWith('authorize-url')?'GET':'POST'}),path)
  assert.equal(requests.length,1)
  const match=requests[0].cookie.match(/admirra_signup_utm=([^;]+)/)
  const value=JSON.parse(decodeURIComponent(match[1]))
  assert.equal(value.utm_source,'yandex');assert.equal(value.utm_campaign,'Тест_123')
  assert.equal((await context.cookies()).filter(c=>c.name==='admirra_signup_utm')[0].secure,true)
  await context.close()
 }
 console.log(JSON.stringify({passed:true,providers:4,landingToSignup:true,oauthRoundTrip:true,secureCookie:true,realRegistrations:0}))
} finally { await browser.close() }
