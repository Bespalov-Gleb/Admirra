import fs from 'node:fs'
import path from 'node:path'

const ROOT = path.resolve(new URL('..', import.meta.url).pathname)
const SRC_DIR = path.join(ROOT, 'src')
const DRY_RUN = process.argv.includes('--dry-run')

const VISUAL_SCALE = 0.75
const CURRENT_ROOT_PX = 14.4 // html font-size was 90%, so 1rem = 14.4px.
const PX_TO_REM_DIVISOR = CURRENT_ROOT_PX

const FILE_EXTENSIONS = new Set(['.vue', '.css', '.scss', '.js', '.ts'])
const SKIP_VALUES = new Set([0, 1])
const SKIP_PROPERTIES = new Set([
  'border',
  'border-width',
  'border-top',
  'border-right',
  'border-bottom',
  'border-left',
  'outline',
  'outline-width',
  'box-shadow',
])

const PX_RE = /(-?(?:\d+|\d*\.\d+))px/g
const PROTECTED_PREFIX = '__UI_SCALE_KEEP_PX_'

function walk(dir, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      walk(fullPath, files)
      continue
    }

    if (FILE_EXTENSIONS.has(path.extname(entry.name))) {
      files.push(fullPath)
    }
  }

  return files
}

function formatNumber(value, maxDigits = 4) {
  const fixed = Number(value.toFixed(maxDigits))
  return Object.is(fixed, -0) ? '0' : `${fixed}`
}

function pxToRem(px) {
  return `${formatNumber(px / PX_TO_REM_DIVISOR)}rem`
}

function scaleBreakpoint(px) {
  return `${formatNumber(px * VISUAL_SCALE, 2)}px`
}

function protectPxValues(source) {
  const protectedValues = []

  const protect = (value) => {
    const token = `${PROTECTED_PREFIX}${protectedValues.length}__`
    protectedValues.push(value)
    return token
  }

  let content = source

  content = content.replace(
    /(@media[^{]*?\(\s*(?:min|max)-width\s*:\s*)(-?(?:\d+|\d*\.\d+))px(\s*\))/g,
    (_, before, value, after) => `${before}${protect(scaleBreakpoint(Number(value)))}${after}`,
  )

  content = content.replace(
    /(matchMedia\(\s*['"`][^'"`]*?\(\s*(?:min|max)-width\s*:\s*)(-?(?:\d+|\d*\.\d+))px(\s*\)[^'"`]*?['"`]\s*\))/g,
    (_, before, value, after) => `${before}${protect(scaleBreakpoint(Number(value)))}${after}`,
  )

  content = content.replace(
    /((?:min|max)-\[)(-?(?:\d+|\d*\.\d+))px(\])/g,
    (_, before, value, after) => `${before}${protect(scaleBreakpoint(Number(value)))}${after}`,
  )

  content = content.replace(
    /((?:^|[\s'"`])(?:[A-Za-z0-9_-]+:)*shadow-\[[^\]]*?\])/g,
    (match) => protect(match),
  )

  return {
    content,
    restore: (converted) => converted.replace(
      new RegExp(`${PROTECTED_PREFIX}(\\d+)__`, 'g'),
      (_, index) => protectedValues[Number(index)],
    ),
  }
}

function convertTailwindArbitraryValues(source) {
  return source.replace(/\[([^\]]*?)(-?(?:\d+|\d*\.\d+))px([^\]]*?)\]/g, (match, before, value, after) => {
    const px = Number(value)
    if (SKIP_VALUES.has(px)) return match
    return `[${before}${pxToRem(px)}${after}]`
  })
}

function propertyBefore(content, index) {
  const start = Math.max(
    content.lastIndexOf(';', index),
    content.lastIndexOf('{', index),
    content.lastIndexOf('}', index),
    content.lastIndexOf(',', index),
    content.lastIndexOf('\n', index),
  )
  const segment = content.slice(start + 1, index)
  const match = segment.match(/([A-Za-z-]+)\s*:\s*(?:(?:['"`])?[^:;{},\n]*)$/)
  return match?.[1]?.toLowerCase() ?? null
}

function shouldSkipPx(content, matchIndex, px) {
  if (SKIP_VALUES.has(px)) return true

  const prop = propertyBefore(content, matchIndex)
  if (!prop) return false

  return SKIP_PROPERTIES.has(prop)
}

function convertRemainingPx(source) {
  return source.replace(PX_RE, (match, value, offset) => {
    const px = Number(value)
    if (shouldSkipPx(source, offset, px)) return match
    return pxToRem(px)
  })
}

function convertContent(source) {
  const { content, restore } = protectPxValues(source)
  const withTailwindArbitraryValues = convertTailwindArbitraryValues(content)
  const withCssValues = convertRemainingPx(withTailwindArbitraryValues)
  return restore(withCssValues)
}

const changes = []

for (const file of walk(SRC_DIR)) {
  const before = fs.readFileSync(file, 'utf8')
  const after = convertContent(before)

  if (before !== after) {
    const beforeCount = (before.match(PX_RE) ?? []).length
    const afterCount = (after.match(PX_RE) ?? []).length
    changes.push({
      file: path.relative(ROOT, file),
      beforeCount,
      afterCount,
      convertedCount: Math.max(0, beforeCount - afterCount),
    })

    if (!DRY_RUN) {
      fs.writeFileSync(file, after)
    }
  }
}

for (const change of changes) {
  console.log(`${change.file}: ${change.convertedCount} px tokens converted, ${change.afterCount} px tokens left`)
}

console.log(`${DRY_RUN ? 'Dry run' : 'Applied'}: ${changes.length} files changed`)
