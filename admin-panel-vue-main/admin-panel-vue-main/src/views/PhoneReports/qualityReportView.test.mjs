import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { rejectionRows } from './qualityReportView.js'

test('API reason map renders counts, including zero', () => {
  assert.deepEqual(rejectionRows({ captcha_failed: 5, spam: 0 }), [
    { reason: 'captcha_failed', count: 5 }, { reason: 'spam', count: 0 },
  ])
  assert.deepEqual(rejectionRows(null), [])
  assert.deepEqual(rejectionRows([{ reason: 'spam', count: 2 }]), [{ reason: 'spam', count: 2 }])
  assert.deepEqual(rejectionRows({ broken: 'invalid' }), [])
})

test('quality report component script and template compile', () => {
  const filename = new URL('./PhoneReports.vue', import.meta.url)
  const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename: filename.pathname })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'quality-report-test' })
  const template = compileTemplate({ source: descriptor.template.content, id: 'quality-report-test',
    filename: filename.pathname, compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
})
