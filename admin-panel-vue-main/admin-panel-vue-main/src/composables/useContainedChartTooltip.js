import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

// Tooltip coordinates belong to the chart, never the page viewport.
export function useContainedChartTooltip({ area, svg, tooltip, index, point, width }) {
  const position = ref({ left: '8px', top: '8px' })
  const dismiss = () => { index.value = -1 }
  let observer
  function measure() {
    if (index.value < 0 || !area.value || !svg.value || !tooltip.value || !point.value) return
    const matrix = svg.value.getScreenCTM()
    if (!matrix) return
    const anchor = svg.value.createSVGPoint()
    anchor.x = point.value.x; anchor.y = point.value.y
    const screen = anchor.matrixTransform(matrix)
    const bounds = area.value.getBoundingClientRect()
    const box = tooltip.value.getBoundingClientRect()
    const x = screen.x - bounds.left, y = screen.y - bounds.top
    const maxX = Math.max(8, bounds.width - box.width - 8)
    const maxY = Math.max(8, bounds.height - box.height - 8)
    position.value = {
      left: `${Math.max(8, Math.min(maxX, x + box.width + 20 <= bounds.width ? x + 12 : x - box.width - 12))}px`,
      top: `${Math.max(8, Math.min(maxY, y - box.height - 12 >= 8 ? y - box.height - 12 : y + 12))}px`,
    }
  }
  const style = computed(() => ({
    position: 'absolute', zIndex: 5, ...position.value, right: 'auto',
    width: `${width.value}px`, minWidth: '0', maxWidth: 'calc(100% - 16px)',
    maxHeight: 'calc(100% - 16px)', overflow: 'hidden', boxSizing: 'border-box',
  }))
  function outside(event) { if (!area.value?.contains(event.target)) dismiss() }
  function keydown(event) { if (event.key === 'Escape') dismiss() }
  function visibility() { if (document.hidden) dismiss() }
  // Capture is required: the dashboard scrolls inside MainLayout, not window.
  onMounted(() => {
    document.addEventListener('scroll', dismiss, { capture: true, passive: true })
    document.addEventListener('wheel', dismiss, { capture: true, passive: true })
    document.addEventListener('pointerdown', outside, true)
    document.addEventListener('keydown', keydown)
    document.addEventListener('visibilitychange', visibility)
    window.addEventListener('resize', dismiss)
    window.visualViewport?.addEventListener('resize', dismiss)
  })
  watch([index, point, tooltip, width], measure, { flush: 'post' })
  watch([area, tooltip], () => {
    observer?.disconnect()
    if (typeof ResizeObserver === 'undefined') return
    observer = new ResizeObserver(measure)
    if (area.value) observer.observe(area.value)
    if (tooltip.value) observer.observe(tooltip.value)
  }, { flush: 'post' })
  onBeforeUnmount(() => {
    observer?.disconnect()
    document.removeEventListener('scroll', dismiss, true)
    document.removeEventListener('wheel', dismiss, true)
    document.removeEventListener('pointerdown', outside, true)
    document.removeEventListener('keydown', keydown)
    document.removeEventListener('visibilitychange', visibility)
    window.removeEventListener('resize', dismiss)
    window.visualViewport?.removeEventListener('resize', dismiss)
  })
  return { style, dismiss }
}
