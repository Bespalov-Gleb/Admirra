<template>
  <div class="flex flex-col lg:flex-row gap-6 min-h-[calc(100vh-200px)]">
    <!-- Левая боковая панель -->
    <aside class="lg:w-64 flex-shrink-0">
      <div class="bg-white rounded-lg  p-4 lg:p-6 shadow-sm border border-gray-100">
        <h2 class="text-lg font-semibold text-gray-900 mb-4 hidden lg:block">Настройки</h2>
        
        <!-- Меню табов -->
        <nav class="space-y-1">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="selectTab(tab.id)"
            :class="[
              'w-full text-left px-4 py-3 rounded-lg transition-colors',
              activeTab === tab.id
                ? 'bg-gray-100 text-gray-900 font-medium'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            ]"
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>
    </aside>

    <!-- Основная область контента -->
    <main class="flex-1">
      <div class="bg-white rounded-lg p-6 sm:p-8 shadow-sm border border-gray-100">
        <!-- Контент табов -->
        <div v-if="activeTab === 'integrations'">
          <IntegrationsTab />
        </div>
        <div v-else>
          <h1 class="text-2xl sm:text-3xl font-bold text-gray-900 mb-6">{{ activeTabLabel }}</h1>
          <div class="text-center py-12">
            <p class="text-gray-500">Настройка {{ activeTabLabel.toLowerCase() }} в разработке</p>
          </div>
        </div>
      </div>
    </main>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import IntegrationsTab from './components/IntegrationsTab.vue'

const activeTab = ref('integrations')

const tabs = [
  { id: 'appearance', label: 'Внешний вид' },
  { id: 'privacy', label: 'Конфиденциальность' },
  { id: 'integrations', label: 'Интеграции' },
  { id: 'payment', label: 'Оплата' },
  { id: 'notifications', label: 'Уведомления' },
  { id: 'language', label: 'Язык' },
  { id: 'hotkeys', label: 'Горячие клавиши' },
  { id: 'additional', label: 'Дополнительно' }
]

const activeTabLabel = computed(() => {
  const tab = tabs.find(t => t.id === activeTab.value)
  return tab ? tab.label : 'Настройки'
})

const selectTab = (tabId) => {
  activeTab.value = tabId
}

</script>
