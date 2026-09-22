import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, compileStyle } from '@vue/compiler-sfc'

function styles(path) {
  const { descriptor } = parse(readFileSync(new URL(path, import.meta.url), 'utf8'))
  return descriptor.styles.map(style => {
    const compiled = compileStyle({ source: style.content, id: 'data-v-qa', scoped: !!style.scoped })
    assert.deepEqual(compiled.errors, [])
    return compiled.code
  }).join('\n')
}
test('dark banner rules target the component, never the root dark element alone', () => {
  const css = styles('./SignupDiscount.vue')
  assert.match(css, /\.dark \.signup-strip\s*\{/)
  assert.match(css, /\.dark \.signup-modal p\s*\{/)
  assert.doesNotMatch(css, /(?:^|\n)\.dark\s*\{/)
})
test('discounted price stays legible on the blue recommended card', () => {
  const css = styles('../views/Tariffs/TariffsPage.vue')
  assert.match(css, /\.plan-card--recommended \.plan-price del[^{}]*\{[^}]*color:\s*#fff;[^}]*opacity:\s*1/)
  assert.match(css, /\.plan-price del[^{}]*\{[^}]*color:\s*#66758a/)
})
