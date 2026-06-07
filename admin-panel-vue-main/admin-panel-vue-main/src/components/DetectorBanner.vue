<template>
  <transition name="detector-banner">
    <div v-if="visible" class="detector-banner" :class="bannerClass">
      <div class="detector-banner__icon">
        <svg v-if="severity === 'problem'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <div class="detector-banner__text">
        <span class="detector-banner__title">{{ title }}</span>
        <span v-if="hypothesis" class="detector-banner__hypothesis">{{ hypothesis }}</span>
      </div>
      <button v-if="actionLabel" type="button" class="detector-banner__action" @click="$emit('action')">
        {{ actionLabel }}
      </button>
      <button v-if="dismissible" type="button" class="detector-banner__close" @click="$emit('dismiss')">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3.5 3.5 12.5 12.5M12.5 3.5 3.5 12.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
      </button>
    </div>
  </transition>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  warningCount: { type: Number, default: 0 },
  problemCount: { type: Number, default: 0 },
  severity: { type: String, default: null },
  hypothesis: { type: String, default: '' },
  warmupStatus: { type: String, default: null },
  warmupDaysLeft: { type: Number, default: null },
  dismissible: { type: Boolean, default: false },
  actionLabel: { type: String, default: '' },
})

defineEmits(['dismiss', 'action'])

const visible = computed(() => {
  if (props.warmupStatus === 'warming_up') return true
  return props.warningCount > 0 || props.problemCount > 0
})

const title = computed(() => {
  if (props.warmupStatus === 'warming_up') {
    const days = props.warmupDaysLeft ?? '?'
    return `Детектор накапливает данные, заработает через ${days} дн.`
  }
  const total = props.warningCount + props.problemCount
  const word = total === 1 ? 'отклонение' : total < 5 ? 'отклонения' : 'отклонений'
  return `Обнаружено ${total} ${word}`
})

const bannerClass = computed(() => {
  if (props.warmupStatus === 'warming_up') return 'detector-banner--warmup'
  if (props.severity === 'problem') return 'detector-banner--problem'
  return 'detector-banner--warning'
})
</script>

<style scoped>
.detector-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1.25rem;
  border-radius: 0.75rem;
  font-family: Inter, sans-serif;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.detector-banner--warning {
  background: #fef3c7;
  border: 1px solid #fcd34d;
  color: #92400e;
}

.detector-banner--problem {
  background: #fee2e2;
  border: 1px solid #fca5a5;
  color: #991b1b;
}

.detector-banner--warmup {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
}

.detector-banner__icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.detector-banner__text {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.detector-banner__title {
  line-height: 1.3;
}

.detector-banner__hypothesis {
  font-size: 0.8125rem;
  font-weight: 400;
  opacity: 0.75;
}

.detector-banner__action {
  margin-left: auto;
  flex-shrink: 0;
  border: 0;
  border-radius: 999px;
  padding: 0.45rem 0.8rem;
  background: rgba(255, 255, 255, 0.72);
  color: currentColor;
  font-size: 0.8125rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.55);
}

.detector-banner__action:hover {
  background: #ffffff;
}

.detector-banner__close {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 50%;
  border: 0;
  background: transparent;
  cursor: pointer;
  opacity: 0.5;
  transition: opacity 0.2s;
}
.detector-banner__close:hover { opacity: 1; }

.detector-banner-enter-active,
.detector-banner-leave-active {
  transition: all 0.3s ease;
}
.detector-banner-enter-from,
.detector-banner-leave-to {
  opacity: 0;
  transform: translateY(-0.5rem);
}

:root.dark .detector-banner--warning { background: rgba(251, 191, 36, 0.1); border-color: rgba(251, 191, 36, 0.3); color: #fbbf24; }
:root.dark .detector-banner--problem { background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3); color: #ef4444; }
:root.dark .detector-banner--warmup { background: rgba(59, 130, 246, 0.1); border-color: rgba(59, 130, 246, 0.3); color: #60a5fa; }
</style>
