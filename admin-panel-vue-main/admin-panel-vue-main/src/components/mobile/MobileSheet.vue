<template>
  <Teleport to="body">
    <div v-if="open" class="mw-sheet-backdrop" @click.self="close">
      <section
        ref="panel"
        class="mw-sheet"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        tabindex="-1"
        @keydown="onKey"
      >
        <div
          class="mw-sheet-handle"
          @touchstart.passive="touchStart"
          @touchend.passive="touchEnd"
        >
          <i />
        </div>
        <header>
          <button
            v-if="back"
            class="mw-icon"
            aria-label="Назад"
            @click="$emit('back')"
          >
            <ChevronLeftIcon />
          </button>
          <h2>{{ title }}</h2>
          <button class="mw-icon" aria-label="Закрыть" @click="close">
            <XMarkIcon />
          </button>
        </header>
        <div class="mw-sheet-body"><slot /></div>
      </section>
    </div>
  </Teleport>
</template>
<script setup>
import { ref, watch, nextTick, onUnmounted } from "vue";
import { XMarkIcon, ChevronLeftIcon } from "@heroicons/vue/24/outline";
const props = defineProps({ open: Boolean, title: String, back: Boolean });
const emit = defineEmits(["close", "back"]);
const panel = ref(null);
let previousFocus,
  scrollRoot,
  previousOverflow,
  y = 0;
const close = () => emit("close");
const touchStart = (e) => {
  y = e.changedTouches[0].clientY;
};
const touchEnd = (e) => {
  if (e.changedTouches[0].clientY - y > 65) close();
};
function unlock() {
  if (scrollRoot) scrollRoot.style.overflow = previousOverflow;
  scrollRoot = null;
  previousFocus?.focus?.({ preventScroll: true });
}
watch(
  () => props.open,
  async (open) => {
    if (!open) {
      unlock();
      return;
    }
    previousFocus = document.activeElement;
    scrollRoot = document.querySelector("main");
    if (scrollRoot) {
      previousOverflow = scrollRoot.style.overflow;
      scrollRoot.style.overflow = "hidden";
    }
    await nextTick();
    panel.value?.focus({ preventScroll: true });
  },
);
onUnmounted(unlock);
function onKey(e) {
  if (e.key === "Escape") {
    e.preventDefault();
    close();
  }
  if (e.key !== "Tab") return;
  const nodes = [
    ...panel.value.querySelectorAll(
      'button:not(:disabled), input, select, a[href], [tabindex="0"]',
    ),
  ].filter((n) => n.offsetParent);
  const first = nodes[0],
    last = nodes.at(-1);
  if (
    e.shiftKey &&
    (document.activeElement === first || document.activeElement === panel.value)
  ) {
    e.preventDefault();
    last?.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault();
    first?.focus();
  }
}
</script>
