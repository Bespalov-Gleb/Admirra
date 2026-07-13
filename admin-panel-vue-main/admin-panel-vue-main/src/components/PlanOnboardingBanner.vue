<template>
  <section v-if="visible" class="plan-onboarding" :class="`plan-onboarding--${planStatus}`">
    <div class="plan-onboarding__icon" aria-hidden="true">◎</div>
    <div class="plan-onboarding__copy">
      <strong>{{ title }}</strong>
      <span>{{ description }}</span>
    </div>
    <button type="button" class="plan-onboarding__cta" @click="$emit('set-plan')">{{ cta }}</button>
    <button type="button" class="plan-onboarding__close" aria-label="Скрыть на 30 дней" @click="$emit('dismiss')">×</button>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  planStatus: { type: String, default: 'configured' },
  detectorEnabled: { type: Boolean, default: false },
  paused: { type: Boolean, default: false },
  warmingUp: { type: Boolean, default: false },
  hasCritical: { type: Boolean, default: false },
  // Матрица состояний ит.3 §7: при любых активных алертах показывается баннер
  // детектора — онбординг-плашка ему уступает, даже в варианте «дозаполните»
  hasAlerts: { type: Boolean, default: false },
  dismissedUntil: { type: [String, Date], default: null },
  completionPct: { type: Number, default: null },
})

const emit = defineEmits(['set-plan', 'dismiss', 'shown'])

const dismissed = computed(() => props.dismissedUntil && new Date(props.dismissedUntil) > new Date())
// План нужно предложить задать и при выключенном детекторе: иначе у нового
// проекта с подключённым каналом нет ни подсказки, ни пути к настройке плана.
const visible = computed(() => !props.paused && !props.warmingUp && !props.hasCritical && !props.hasAlerts && !dismissed.value && ['missing', 'incomplete', 'expired'].includes(props.planStatus))

// §8: показ плашки — событие аналитики; одно на появление, не на каждый рендер
const shownReported = ref(false)
watch(visible, (value) => {
  if (value && !shownReported.value) {
    shownReported.value = true
    emit('shown')
  }
  if (!value) shownReported.value = false
}, { immediate: true })

const title = computed(() => {
  if (props.planStatus === 'expired') {
    // §6: итог периода — точка удержания в фиче. Процент — про деньги,
    // формулировка обязана это говорить сама («выполнен на 124%» читалось
    // как успех, хотя 124% бюджета — перерасход)
    return props.completionPct != null
      ? `Бюджет прошлого периода израсходован на ${Math.round(props.completionPct)}%`
      : 'План на прошлый период завершён'
  }
  if (props.planStatus === 'incomplete') return 'Дозаполните план по бюджету и стоимости заявки'
  return 'Задайте план по бюджету и стоимости заявки'
})
const description = computed(() => {
  if (props.planStatus === 'expired') return 'Задайте новый план — AdMirra снова будет сверять факт с договорённостью.'
  return 'AdMirra будет ежедневно сверять факт с планом и предупредит, если проект отстаёт от темпа или заявки дорожают.'
})
const cta = computed(() => props.planStatus === 'incomplete' ? 'Дозаполнить план' : 'Задать план')
</script>

<style scoped>
.plan-onboarding{display:flex;align-items:center;gap:.85rem;padding:.9rem 1.05rem;border:1px solid #cbdaf8;border-radius:1rem;background:#eef4ff;color:#264e9f}.plan-onboarding--expired{background:#f4f6f9;border-color:#dce3ed;color:#536177}.plan-onboarding__icon{display:grid;place-items:center;flex:0 0 auto;width:2.25rem;height:2.25rem;border-radius:.75rem;background:#2f6bea;color:#fff;font-weight:800;font-size:1.25rem}.plan-onboarding__copy{display:flex;flex:1;flex-direction:column;min-width:0;gap:.12rem}.plan-onboarding__copy strong{color:#1f2937;font-size:.95rem}.plan-onboarding__copy span{font-size:.82rem;line-height:1.35}.plan-onboarding__cta{flex:0 0 auto;border:0;border-radius:.65rem;padding:.55rem .8rem;background:#2f6bea;color:#fff;font-size:.82rem;font-weight:800;cursor:pointer}.plan-onboarding__close{flex:0 0 auto;border:0;background:transparent;color:currentColor;font-size:1.4rem;line-height:1;cursor:pointer;opacity:.6}.plan-onboarding__close:hover{opacity:1}@media(max-width:640px){.plan-onboarding{align-items:flex-start;flex-wrap:wrap}.plan-onboarding__cta{margin-left:3.1rem}.plan-onboarding__close{position:absolute;right:1rem}.plan-onboarding{position:relative}}
</style>
