import { ref } from 'vue'

export function useDragScroll() {
  const containerRef = ref(null)
  const isDragging = ref(false)
  const startX = ref(0)
  const scrollLeft = ref(0)

  const handleMouseDown = (e) => {
    if (!containerRef.value) return
    isDragging.value = true
    startX.value = e.pageX - containerRef.value.offsetLeft
    scrollLeft.value = containerRef.value.scrollLeft
    containerRef.value.style.scrollBehavior = 'auto'
  }

  const handleMouseMove = (e) => {
    if (!isDragging.value || !containerRef.value) return
    e.preventDefault()
    e.stopPropagation()
    const x = e.pageX - containerRef.value.offsetLeft
    const walk = (x - startX.value) * 2 // Scroll speed
    containerRef.value.scrollLeft = scrollLeft.value - walk
  }

  const handleMouseUp = () => {
    isDragging.value = false
    if (containerRef.value) {
      containerRef.value.style.scrollBehavior = 'smooth'
    }
  }

  const handleWheel = (e) => {
    if (containerRef.value) {
      // Only horizontal scroll if we are over the container
      e.preventDefault()
      e.stopPropagation()
      containerRef.value.scrollLeft += e.deltaY
    }
  }

  const handleTouchStart = (e) => {
    if (!containerRef.value) return
    isDragging.value = true
    startX.value = e.touches[0].pageX - containerRef.value.offsetLeft
    scrollLeft.value = containerRef.value.scrollLeft
    containerRef.value.style.scrollBehavior = 'auto'
  }

  const handleTouchMove = (e) => {
    if (!isDragging.value || !containerRef.value) return
    e.preventDefault()
    e.stopPropagation()
    const x = e.touches[0].pageX - containerRef.value.offsetLeft
    const walk = (x - startX.value) * 2
    containerRef.value.scrollLeft = scrollLeft.value - walk
  }

  const handleTouchEnd = () => {
    isDragging.value = false
    if (containerRef.value) {
      containerRef.value.style.scrollBehavior = 'smooth'
    }
  }

  const dragScrollHandlers = {
    onMousedown: handleMouseDown,
    onMousemove: handleMouseMove,
    onMouseup: handleMouseUp,
    onMouseleave: handleMouseUp,
    onWheel: handleWheel,
    onTouchstart: handleTouchStart,
    onTouchmove: handleTouchMove,
    onTouchend: handleTouchEnd
  }

  return {
    containerRef,
    isDragging,
    dragScrollHandlers
  }
}
