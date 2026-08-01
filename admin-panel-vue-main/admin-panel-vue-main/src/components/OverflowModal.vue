<template>
  <Teleport to="body">
    <div v-if="state.open" class="ovf-backdrop" @click.self="onCancel">
      <div class="ovf-modal" role="dialog" aria-modal="true">
        <button class="ovf-close" type="button" aria-label="Закрыть" @click="onCancel">×</button>

        <h4 class="ovf-title">
          {{ state.mode === 'confirm' ? 'Проект сверх лимита' : 'Лимит проектов исчерпан' }}
        </h4>
        <p class="ovf-text">{{ state.detail?.message }}</p>

        <p v-if="state.mode === 'confirm'" class="ovf-note">
          Это временный запас. Решить нужно до конца оплаченного периода: докупить слот,
          перейти на старший тариф или убрать лишний проект.
        </p>

        <div class="ovf-actions">
          <template v-if="state.mode === 'confirm'">
            <button class="ovf-btn ovf-btn--primary" type="button" @click="onConfirm">
              Добавить пока так
            </button>
            <button class="ovf-btn ovf-btn--ghost" type="button" @click="goToPlans">
              Посмотреть тарифы
            </button>
          </template>
          <template v-else>
            <button class="ovf-btn ovf-btn--primary" type="button" @click="goToPlans">
              {{ suggestedLabel }}
            </button>
            <button class="ovf-btn ovf-btn--ghost" type="button" @click="onCancel">
              Закрыть
            </button>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useOverflowModal } from '@/composables/useOverflowModal'

const { state, close } = useOverflowModal()
const router = useRouter()

const PLAN_NAMES = { start: 'Старт', agency: 'Агентство', pro: 'Про', white_label: 'White Label' }
const suggestedLabel = computed(() => {
  const code = state.detail?.suggested_plan
  return code && PLAN_NAMES[code] ? `Перейти на ${PLAN_NAMES[code]}` : 'Посмотреть тарифы'
})

const onConfirm = () => close(true)
const onCancel = () => close(false)
const goToPlans = () => {
  close(false)
  router.push({ path: '/settings', query: { tab: 'tariff', view: 'plans' } })
}
</script>

<style scoped>
.ovf-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.6rem;
  background: rgba(12, 20, 34, 0.45);
}

.ovf-modal {
  position: relative;
  width: 100%;
  max-width: 34rem;
  padding: 2.4rem 2.2rem 2rem;
  border-radius: 1.6rem;
  background: #fff;
  box-shadow: 0 1.6rem 4rem rgba(15, 23, 42, 0.18);
}

.ovf-close {
  position: absolute;
  top: 1.2rem;
  right: 1.4rem;
  border: none;
  background: none;
  color: #94a3b8;
  font-size: 2.2rem;
  line-height: 1;
  cursor: pointer;
}

.ovf-title {
  margin: 0 0 0.9rem;
  color: #0c2950;
  font-size: 1.7rem;
  font-weight: 700;
}

.ovf-text {
  margin: 0 0 0.8rem;
  color: #1f2937;
  font-size: 1.25rem;
  line-height: 1.4;
}

.ovf-note {
  margin: 0 0 1.6rem;
  color: #64748b;
  font-size: 1.1rem;
  line-height: 1.4;
}

.ovf-actions {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.ovf-btn {
  width: 100%;
  padding: 1rem 1.2rem;
  border: none;
  border-radius: 0.9rem;
  font-size: 1.25rem;
  font-weight: 600;
  cursor: pointer;
}

.ovf-btn--primary {
  background: #2563eb;
  color: #fff;
}

.ovf-btn--ghost {
  background: #f1f5f9;
  color: #334155;
}
</style>
