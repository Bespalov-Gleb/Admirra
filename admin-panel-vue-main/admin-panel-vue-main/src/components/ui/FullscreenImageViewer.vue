<template>
  <Teleport to="body">
    <div class="fs-viewer" @click.self="$emit('close')" @wheel.prevent="onWheel">
      <div class="fs-viewer__toolbar">
        <button type="button" title="Уменьшить" @click.stop="zoomOut">−</button>
        <span>{{ Math.round(scale * 100) }}%</span>
        <button type="button" title="Увеличить" @click.stop="zoomIn">+</button>
        <button type="button" title="Сбросить" @click.stop="reset">⟲</button>
        <button type="button" class="fs-viewer__close" aria-label="Закрыть" @click.stop="$emit('close')">×</button>
      </div>
      <img
        :src="src"
        class="fs-viewer__img"
        :style="imgStyle"
        draggable="false"
        alt="Превью отчёта"
        @mousedown.stop.prevent="startDrag"
        @dblclick.stop="toggleZoom"
        @click.stop
      />
      <p class="fs-viewer__hint">Колесо мыши — масштаб · двойной клик — приблизить · перетаскивание — двигать</p>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

defineProps({ src: { type: String, default: '' } })
const emit = defineEmits(['close'])

const MIN = 1
const MAX = 5
const scale = ref(1)
const tx = ref(0)
const ty = ref(0)
const dragging = ref(false)
let startX = 0
let startY = 0
let startTx = 0
let startTy = 0

const clamp = (v, a, b) => Math.min(b, Math.max(a, v))

const imgStyle = computed(() => ({
  transform: `translate(${tx.value}px, ${ty.value}px) scale(${scale.value})`,
  cursor: scale.value > 1 ? (dragging.value ? 'grabbing' : 'grab') : 'zoom-in',
}))

const setScale = (next) => {
  const s = clamp(Number(next.toFixed(2)), MIN, MAX)
  if (s === 1) { tx.value = 0; ty.value = 0 }
  scale.value = s
}
const zoomIn = () => setScale(scale.value + 0.5)
const zoomOut = () => setScale(scale.value - 0.5)
const reset = () => { scale.value = 1; tx.value = 0; ty.value = 0 }
const toggleZoom = () => setScale(scale.value > 1 ? 1 : 2)

const onWheel = (e) => setScale(scale.value + (e.deltaY < 0 ? 0.25 : -0.25))

const onDrag = (e) => {
  tx.value = startTx + (e.clientX - startX)
  ty.value = startTy + (e.clientY - startY)
}
const endDrag = () => {
  dragging.value = false
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', endDrag)
}
const startDrag = (e) => {
  if (scale.value <= 1) return
  dragging.value = true
  startX = e.clientX
  startY = e.clientY
  startTx = tx.value
  startTy = ty.value
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', endDrag)
}

const onKey = (e) => { if (e.key === 'Escape') emit('close') }
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', endDrag)
})
</script>

<style scoped>
.fs-viewer {
  position: fixed;
  inset: 0;
  z-index: 1400;
  display: grid;
  place-items: center;
  padding: 2.5rem;
  background: rgba(6, 12, 28, 0.92);
  overflow: hidden;
  cursor: zoom-out;
}
.fs-viewer__img {
  max-width: 94vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 0.5rem;
  box-shadow: 0 2rem 5rem rgba(0, 0, 0, 0.5);
  background: #fff;
  user-select: none;
  -webkit-user-drag: none;
  transition: transform 0.06s linear;
  will-change: transform;
}
.fs-viewer__toolbar {
  position: fixed;
  top: 1.1rem;
  right: 1.4rem;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.fs-viewer__toolbar button {
  width: 2.4rem;
  height: 2.4rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 0.6rem;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
}
.fs-viewer__toolbar button:hover { background: rgba(255, 255, 255, 0.26); }
.fs-viewer__toolbar span {
  min-width: 3.4rem;
  text-align: center;
  color: #fff;
  font-size: 0.85rem;
  font-weight: 600;
}
.fs-viewer__close { font-size: 1.6rem; }
.fs-viewer__hint {
  position: fixed;
  bottom: 1.1rem;
  left: 50%;
  transform: translateX(-50%);
  margin: 0;
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.8rem;
  pointer-events: none;
}
</style>
