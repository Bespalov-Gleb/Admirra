import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'

const root = new URL('../', import.meta.url)
const read = path => readFileSync(new URL(path, root), 'utf8')
const originals = {
  agreement: '570f8eb5ec6a25ef2e45e312300edba451a942cd592986d7017690cb45d04436',
  'user-agreement': '135b27907eb2dacdf4131f670c799d37c1caaabd4974608535d8eca5715bd1a6',
  'personal-data': '9cad790d6ba506dd9a3097af8aa32fe1580b05f2e89ac810e347b7a561bfe8cf',
}

for (const [name, hash] of Object.entries(originals)) {
  test(`${name}: approved legal text preserved, public navigation independent of SPA auth`, () => {
    const html = read(`public/admirra/${name}.html`)
    const text = html.match(/<article[^>]*>([\s\S]*?)<\/article>/)[1].replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim()
    assert.equal(createHash('sha256').update(text).digest('hex'), hash)
    assert.ok(html.includes('href="/admirra/legal.css?v=brand-20260924"'))
    assert.ok(html.includes('href="/"'))
    assert.ok(html.includes(`href="/admirra/${name}.html" aria-current="page"`))
    assert.ok(!/href="(?:#"|index.html|entry.html|reg.html)/.test(html))
    assert.ok(!html.includes('/src/main.js'))
    assert.equal((html.match(/src="\/landing-new\/assets\/img\/logo.png"/g) || []).length, 2)
    assert.ok(html.includes('class="site-header"'))
    for (const section of ['audience', 'dashboard', 'features', 'integrations', 'pricing']) {
      assert.ok(html.includes(`href="/#${section}"`))
    }
    assert.ok(html.includes('aria-controls="mobile-nav" aria-expanded="false"'))
    assert.ok(html.includes('id="mobile-nav" aria-label="Мобильная навигация" hidden'))
    assert.ok(html.includes('src="/admirra/legal.js?v=brand-20260924" defer'))
  })
}

test('authentication footers link to actual documents, not placeholders or registration', () => {
  for (const view of ['SignIn', 'SignUp', 'ResetPassword']) {
    const html = read(`src/views/Auth/${view}.vue`)
    for (const name of Object.keys(originals)) assert.ok(html.includes(`href="/admirra/${name}.html"`))
    assert.ok(!html.includes('href="#">Договор оферты'))
  }
})

test('old landing is only a redirect; legacy pages link to current home', () => {
  const old = read('public/admirra/index.html')
  assert.ok(old.includes('http-equiv="refresh" content="0;url=/"'))
  assert.ok(old.length < 1000)
  for (const page of ['entry', 'reg', 'blog', 'blog-article']) {
    assert.ok(!/href="(?:index.html|\/admirra\/index.html)/.test(read(`public/admirra/${page}.html`)))
  }
})
