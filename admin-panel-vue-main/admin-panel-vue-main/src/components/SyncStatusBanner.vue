<template>
  <!-- Баннер синхронизации - не блокирует интерфейс -->
  <transition
    enter-active-class="transition ease-out duration-300"
    enter-from-class="transform translate-y-[-100%] opacity-0"
    enter-to-class="transform translate-y-0 opacity-100"
    leave-active-class="transition ease-in duration-200"
    leave-from-class="transform translate-y-0 opacity-100"
    leave-to-class="transform translate-y-[-100%] opacity-0"
  >
    <div
      v-if="showBanner"
      class="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-blue-500 via-blue-600 to-purple-600 shadow-lg"
    >
      <div class="container mx-auto px-4 py-3">
        <div class="flex items-center justify-between">
          <!-- Левая часть: индикатор и текст -->
          <div class="flex items-center gap-3">
            <!-- Анимированный спиннер -->
            <div class="relative">
              <svg
                class="animate-spin h-6 w-6 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            </div>

            <!-- Текст -->
            <div class="flex flex-col">
              <span class="text-white font-medium text-sm">
                🔄 Идёт синхронизация данных...
              </span>
              <span class="text-white/80 text-xs">
                {{ syncMessage }}
              </span>
            </div>
          </div>

          <!-- Правая часть: кнопка для скрытия (опционально) -->
          <button
            v-if="showDismissButton"
            @click="isDismissed = true"
            class="text-white/80 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/10"
            title="Скрыть уведомление (синхронизация продолжится в фоне)"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- Прогресс-бар (анимированный) -->
        <div class="mt-2 h-1 bg-white/20 rounded-full overflow-hidden">
          <div class="h-full bg-white/40 animate-progress rounded-full"></div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useSyncStatus } from '../composables/useSyncStatus'

const props = defineProps({
  showDismissButton: {
    type: Boolean,
    default: false
  }
})

// Используем composable для отслеживания статуса синхронизации
const { isSyncing, syncingIntegrations } = useSyncStatus()

// Локальное состояние для временного скрытия баннера
const isDismissed = ref(false)

// Показываем баннер только если не скрыт вручную
const showBanner = computed(() => {
  return isSyncing.value && !isDismissed.value
})

// Формируем сообщение в зависимости от состояния
const syncMessage = computed(() => {
  const count = syncingIntegrations.value.length
  
  if (count === 0) return ''
  
  if (count === 1) {
    const platform = syncingIntegrations.value[0].platform
    const platformNames = {
      yandex_direct: 'Яндекс Директ',
      vk_ads: 'VK Реклама',
      google_ads: 'Google Ads',
      facebook_ads: 'Facebook Ads'
    }
    return `Синхронизируем ${platformNames[platform] || platform}. Данные появятся через несколько минут.`
  }
  
  return `Синхронизируем ${count} ${count === 2 ? 'интеграции' : 'интеграций'}. Данные появятся через несколько минут.`
})

// Сбрасываем isDismissed когда синхронизация завершается
watch(isSyncing, (newValue) => {
  if (!newValue && isDismissed.value) {
    isDismissed.value = false
  }
})
</script>

<style scoped>
/* Анимация для прогресс-бара (неопределённый прогресс) */
@keyframes progress-animation {
  0% {
    transform: translateX(-100%) scaleX(0.3);
  }
  50% {
    transform: translateX(0%) scaleX(1);
  }
  100% {
    transform: translateX(100%) scaleX(0.3);
  }
}

.animate-progress {
  animation: progress-animation 1.5s ease-in-out infinite;
  transform-origin: left center;
}
</style>
