<template>
  <div v-if="visible" class="ovf-banner" :class="{ 'ovf-banner--hard': state.hard_blocked }">
    <div class="ovf-banner__text"><strong>{{ state.hard_blocked ? 'Нужны дополнительные места' : 'Вы используете временный запас проектов' }}</strong><span>{{ text }}</span></div>
    <button class="ovf-banner__cta" type="button" @click="goToPlans">Места и тарифы →</button>
    <button
      v-if="!state.hard_blocked && !state.permanent"
      class="ovf-banner__close"
      type="button"
      aria-label="Скрыть"
      @click="dismiss"
    >×</button>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/axios'
import { getAccessToken } from '@/utils/authToken'

const route = useRoute()
const router = useRouter()

const state = reactive({
  over_limit: false,
  over_by: 0,
  hard_blocked: false,
  permanent: false,
  serverDismissed: false,
  deadline: null,
  loaded: false,
})
const dismissed = ref(false)

// Баннер только в авторизованной части приложения (не на auth/лендинге).
const inApp = computed(() => {
  const authLayouts = ['auth', 'landing']
  if (authLayouts.includes(route.meta?.layout)) return false
  return Boolean(getAccessToken())
})

const load = async () => {
  if (!inApp.value) return
  try {
    const { data } = await api.get('billing/subscription')
    state.over_limit = Boolean(data?.over_limit)
    state.over_by = Number(data?.over_by || 0)
    state.hard_blocked = Boolean(data?.hard_blocked)
    state.permanent = Boolean(data?.overflow_banner_permanent)
    state.serverDismissed = Boolean(data?.overflow_notice_dismissed)
    state.deadline = data?.overflow_deadline || null
    state.loaded = true
  } catch { /* не критично */ }
}

watch(inApp, (v) => { if (v) load() }, { immediate: true })
watch(() => route.path, () => { if (inApp.value) load() })
onMounted(() => window.addEventListener('billing:updated', load))
onUnmounted(() => window.removeEventListener('billing:updated', load))

const visible = computed(() => (
  inApp.value
  && state.over_limit
  && (state.hard_blocked || state.permanent || (!dismissed.value && !state.serverDismissed))
))

const dismiss = async () => {
  try {
    await api.post('billing/overflow/dismiss')
    dismissed.value = true
    state.serverDismissed = true
  } catch {
    // Сервер мог сделать баннер постоянным между загрузкой и кликом.
    await load()
  }
}

const text = computed(() => {
  if (state.hard_blocked) {
    return 'Создание новых проектов приостановлено: превышение держится второй период. Докупите слоты, перейдите на старший тариф или уберите лишние проекты.'
  }
  const by = state.over_by ? ` (на ${state.over_by})` : ''
  const till = state.deadline ? ` до ${new Date(state.deadline).toLocaleDateString('ru-RU')}` : ''
  return `Проектов больше лимита тарифа${by}. Решите${till}: докупите слоты, перейдите на старший тариф или уберите лишние проекты.`
})

const goToPlans = () => router.push({ path: '/settings', query: { tab: 'tariff', view: 'plans' } })
</script>

<style scoped>
.ovf-banner {
  position: sticky;
  top: 0;
  z-index: 900;
  display: flex;
  flex-wrap: wrap;
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  align-items: center;
  gap: 1.2rem;
  padding: 0.9rem 1.6rem;
  background: #fff4d6;
  border-bottom: 1px solid #f2d68b;
  color: #7a4a08;
  font-size: 1.15rem;
  line-height: 1.35;
}

.ovf-banner--hard {
  background: #fde2e1;
  border-bottom-color: #f3b4b0;
  color: #8a1f18;
}

.ovf-banner__text { flex: 1 1 260px; min-width: 0; overflow-wrap: anywhere; }
.ovf-banner__text strong { display: block; margin-bottom: 4px; font-size: 14px; }
.ovf-banner__text span { display: block; font-size: 13px; line-height: 1.5; }

.ovf-banner__cta {
  flex: 0 0 auto;
  max-width: 100%;
  min-height: 40px;
  padding: 0.5rem 1.1rem;
  border: none;
  border-radius: 0.8rem;
  background: #2563eb;
  color: #fff;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
}

@media (max-width: 600px) {
  .ovf-banner { position: relative; padding: 16px 44px 16px 16px; gap: 12px; }
  .ovf-banner__text { flex-basis: 100%; }
  .ovf-banner__cta { font-size: 13px; }
  .ovf-banner__close { position: absolute; top: 12px; right: 10px; width: 28px; height: 28px; }
}

.ovf-banner__close {
  flex: 0 0 auto;
  border: none;
  background: none;
  color: inherit;
  font-size: 1.8rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0.7;
}
</style>
