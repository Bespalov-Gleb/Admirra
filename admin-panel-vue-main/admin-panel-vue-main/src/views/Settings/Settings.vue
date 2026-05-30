<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-hidden px-[1.7361rem] py-[2.0833rem]">

    <div class="pt-[1.0417rem] pb-[1.0417rem] mb-[1.3889rem]">
      <h3 class="text-[2.0833rem] font-semibold leading-none text-[#171717] dark:text-white">Настройки</h3>
    </div>

    <div class="flex flex-col lg:flex-row gap-[1.7361rem] flex-1">
      <!-- Left: vertical tabs -->
      <aside class="lg:w-[16.6667rem] flex-shrink-0">
        <div class="bg-white dark:bg-[#2C2F3D] dark:border dark:border-white/10 rounded-[1.0417rem] p-[1.0417rem]">
          <nav class="flex flex-col gap-[0.3472rem]">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              @click="selectTab(tab.id)"
              :class="[
                'w-full text-left px-[1.0417rem] py-[0.8333rem] rounded-[0.6944rem] text-[0.9722rem] font-medium transition-colors flex items-center gap-[0.6944rem]',
                activeTab === tab.id
                  ? 'bg-[#ecf3fe] text-[#2563eb] dark:bg-white/10 dark:text-[#4A7AFF]'
                  : 'text-[#696969]/75 hover:bg-[#f5f7f9] hover:text-[#171717] dark:text-white/60 dark:hover:bg-white/5 dark:hover:text-white/90'
              ]"
            >
              <svg v-if="tab.id === 'brand' && !whitelabelAvailable" class="w-4 h-4 flex-shrink-0 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>
              </svg>
              {{ tab.label }}
            </button>
          </nav>
        </div>
      </aside>

      <!-- Right: tab content -->
      <div class="flex-1 min-w-0">

        <!-- Tab: Бренд / White Label -->
        <div v-if="activeTab === 'brand'">

          <!-- Locked state -->
          <div v-if="!whitelabelAvailable">
            <div class="flex items-center gap-[0.6944rem] mb-[1.7361rem]">
              <h4 class="text-[1.6667rem] font-semibold text-[#171717] dark:text-white">Бренд / White Label</h4>
              <span class="inline-flex items-center gap-1 px-[0.6944rem] py-[0.3472rem] rounded-full bg-[#f0f1f3] dark:bg-white/10 text-[0.7639rem] font-semibold text-[#696969] dark:text-white/55">
                <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
                Доступно на старшем тарифе
              </span>
            </div>

            <!-- Upsell card -->
            <div class="rounded-[1.3889rem] p-[2.0833rem] mb-[2.0833rem] relative overflow-hidden"
                 style="background: linear-gradient(135deg, #2563eb 0%, #1f9de4 50%, #06b5d4 100%)">
              <div class="absolute inset-0 pointer-events-none opacity-15" style="background: url('/admirra/img/pattern.png') center/5.3472rem"></div>
              <div class="relative z-10">
                <h4 class="text-[1.3889rem] font-semibold text-white mb-[0.6944rem]">Персонализируйте отчёты под ваш бренд</h4>
                <p class="text-[1.0417rem] text-white/80 mb-[1.3889rem] max-w-[34.7222rem]">
                  Клиенты видят ваш бренд, а не AdMirra — в PDF-отчётах, КП и сообщениях
                </p>
                <ul class="flex flex-col gap-[0.6944rem] mb-[1.7361rem]">
                  <li v-for="item in wlFeatures" :key="item" class="flex items-center gap-[0.6944rem] text-[1.0417rem] text-white">
                    <span class="w-[0.6944rem] h-[0.6944rem] rounded-full bg-white/40 flex-shrink-0"></span>
                    {{ item }}
                  </li>
                </ul>
                <button @click="selectTab('tariff')" class="inline-flex items-center min-h-[3.1944rem] px-[1.6667rem] rounded-[0.8333rem] bg-white text-[0.9722rem] font-semibold text-[#2563eb] hover:bg-white/90 transition-colors">
                  Перейти на старший тариф
                </button>
              </div>
            </div>

            <!-- Dimmed preview -->
            <div class="opacity-40 pointer-events-none select-none grayscale-[30%]">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-[1.0417rem]">
                <div v-for="field in brandFields" :key="field.title" class="bg-white dark:bg-[#2C2F3D] rounded-[1.0417rem] p-[1.3889rem] border border-black/5 dark:border-white/10">
                  <div class="text-[0.9722rem] font-semibold text-[#171717] dark:text-white/80 mb-[0.6944rem]">{{ field.title }}</div>
                  <div class="text-[0.9028rem] text-[#696969]/60 dark:text-white/40">{{ field.placeholder }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Unlocked state -->
          <div v-else>
            <div class="flex items-center gap-[0.6944rem] mb-[1.7361rem]">
              <h4 class="text-[1.6667rem] font-semibold text-[#171717] dark:text-white">Бренд / White Label</h4>
              <span class="inline-flex items-center gap-1 px-[0.6944rem] py-[0.3472rem] rounded-full bg-[#00ff4e]/10 text-[0.7639rem] font-semibold text-[#16a34a] dark:bg-[#00ff4e]/15 dark:text-[#5ee886]">
                Активно
              </span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-[1.0417rem]">
              <!-- Logo -->
              <div class="settings-card">
                <div class="text-[0.9722rem] font-semibold text-[#171717] dark:text-white/90 mb-[0.6944rem]">Логотип агентства</div>
                <div v-if="brandLogo" class="flex items-center gap-[1.0417rem] mb-[0.6944rem]">
                  <img :src="brandLogo" alt="Logo" class="h-[3.4722rem] max-w-[10.4167rem] object-contain rounded" />
                  <div class="flex gap-[0.4861rem]">
                    <label class="settings-link cursor-pointer">
                      Заменить
                      <input type="file" accept="image/png,image/jpeg,image/svg+xml" class="hidden" @change="handleLogoUpload" />
                    </label>
                    <button class="settings-link text-red-500" @click="brandLogo = null">Удалить</button>
                  </div>
                </div>
                <label v-else class="flex items-center justify-center h-[5.5556rem] border-2 border-dashed border-[#e1e1e1] dark:border-white/15 rounded-[0.8333rem] cursor-pointer hover:border-[#2563eb] dark:hover:border-[#4A7AFF] transition-colors">
                  <span class="text-[0.9028rem] text-[#696969]/60 dark:text-white/40">Нажмите для загрузки PNG, SVG или JPG</span>
                  <input type="file" accept="image/png,image/jpeg,image/svg+xml" class="hidden" @change="handleLogoUpload" />
                </label>
              </div>

              <!-- Brand color -->
              <div class="settings-card">
                <div class="text-[0.9722rem] font-semibold text-[#171717] dark:text-white/90 mb-[0.6944rem]">Фирменный цвет</div>
                <div class="flex items-center gap-[0.6944rem] flex-wrap mb-[0.6944rem]">
                  <button
                    v-for="color in presetColors"
                    :key="color"
                    class="w-[2.0833rem] h-[2.0833rem] rounded-full border-2 transition-all"
                    :style="{ backgroundColor: color }"
                    :class="brandColor === color ? 'border-[#171717] dark:border-white scale-110' : 'border-transparent hover:scale-105'"
                    @click="brandColor = color"
                  />
                </div>
                <div class="flex items-center gap-[0.4861rem]">
                  <span class="text-[0.9028rem] text-[#696969]/60 dark:text-white/40">HEX:</span>
                  <input
                    v-model="brandColor"
                    type="text"
                    maxlength="7"
                    class="w-[6.9444rem] px-[0.6944rem] py-[0.4861rem] rounded-[0.4861rem] text-[0.9028rem] bg-[#f5f7f9] dark:bg-white/10 border border-transparent focus:border-[#2563eb] outline-none text-[#171717] dark:text-white"
                    placeholder="#2563EB"
                  />
                  <span class="w-[1.6667rem] h-[1.6667rem] rounded-full border border-black/10 dark:border-white/15" :style="{ backgroundColor: brandColor || '#ccc' }"></span>
                </div>
              </div>

              <!-- PDF header/footer -->
              <div class="settings-card">
                <div class="text-[0.9722rem] font-semibold text-[#171717] dark:text-white/90 mb-[0.6944rem]">Шапка и подпись PDF</div>
                <div v-if="pdfHeader || pdfSignature" class="text-[0.9028rem] text-[#444] dark:text-white/70 mb-[0.4861rem]">
                  <div v-if="pdfHeader">{{ pdfHeader }}</div>
                  <div v-if="pdfSignature" class="text-[#696969]/60 dark:text-white/40 mt-1">{{ pdfSignature }}</div>
                </div>
                <div v-else class="text-[0.9028rem] text-[#696969]/60 dark:text-white/40 mb-[0.4861rem]">Не заполнено</div>
                <button class="settings-link" @click="pdfModalOpen = true">Редактировать</button>
              </div>

              <!-- Custom domain -->
              <div class="settings-card">
                <div class="text-[0.9722rem] font-semibold text-[#171717] dark:text-white/90 mb-[0.6944rem]">Свой домен для отчётов</div>
                <div v-if="customDomain" class="flex items-center gap-[0.6944rem] mb-[0.4861rem]">
                  <span class="text-[0.9028rem] text-[#444] dark:text-white/70">{{ customDomain }}</span>
                  <span :class="domainStatusClass">{{ domainStatusLabel }}</span>
                </div>
                <div v-else class="text-[0.9028rem] text-[#696969]/60 dark:text-white/40 mb-[0.4861rem]">Не настроен</div>
                <input
                  v-model="customDomain"
                  type="text"
                  class="w-full px-[0.6944rem] py-[0.4861rem] rounded-[0.4861rem] text-[0.9028rem] bg-[#f5f7f9] dark:bg-white/10 border border-transparent focus:border-[#2563eb] outline-none text-[#171717] dark:text-white"
                  placeholder="reports.вашдомен.ru"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Tab: Тариф и оплата -->
        <div v-else-if="activeTab === 'tariff'">
          <TariffsContent />
        </div>

      </div>
    </div>

    <!-- PDF edit modal -->
    <Teleport to="body">
      <div v-if="pdfModalOpen" class="fixed inset-0 z-[9000] flex items-center justify-center bg-black/50 p-4" @click.self="pdfModalOpen = false">
        <div class="w-full max-w-[33.3333rem] rounded-2xl border border-black/5 bg-white dark:bg-[#2C2F3D] dark:border-white/10 p-6">
          <h4 class="text-[1.25rem] font-bold text-gray-800 dark:text-gray-100 mb-4">Шапка и подпись PDF</h4>
          <div class="flex flex-col gap-3 mb-5">
            <div>
              <label class="block text-[0.9028rem] text-[#696969] dark:text-white/55 mb-1">Название агентства / шапка</label>
              <input v-model="pdfHeaderDraft" type="text" class="w-full px-3 py-2.5 rounded-xl border border-black/10 dark:border-white/15 bg-transparent text-[0.9722rem] text-gray-700 dark:text-gray-200 outline-none focus:border-[#2563eb]" placeholder="ООО «Рекламное агентство»" />
            </div>
            <div>
              <label class="block text-[0.9028rem] text-[#696969] dark:text-white/55 mb-1">Подпись / контакты внизу отчёта</label>
              <textarea v-model="pdfSignatureDraft" rows="3" class="w-full px-3 py-2.5 rounded-xl border border-black/10 dark:border-white/15 bg-transparent text-[0.9722rem] text-gray-700 dark:text-gray-200 outline-none focus:border-[#2563eb] resize-y" placeholder="Телефон, email, адрес"></textarea>
            </div>
          </div>
          <div class="flex gap-3">
            <button class="h-[3.0556rem] px-5 rounded-xl bg-[#2563eb] text-white text-[0.9722rem] font-medium hover:bg-[#1d4ed8] transition-colors" @click="savePdf">Сохранить</button>
            <button class="h-[3.0556rem] px-5 rounded-xl border border-black/10 dark:border-white/15 bg-white dark:bg-white/5 text-[0.9722rem] text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/10 transition-colors" @click="pdfModalOpen = false">Отмена</button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TariffsContent from '../Tariffs/TariffsPage.vue'

const route = useRoute()
const router = useRouter()

const activeTab = ref('brand')

const tabs = [
  { id: 'brand', label: 'Бренд / White Label' },
  { id: 'tariff', label: 'Тариф и оплата' },
]

const selectTab = (tabId) => {
  activeTab.value = tabId
  router.replace({ path: '/settings', query: tabId === 'tariff' ? { tab: 'tariff' } : {} })
}

onMounted(() => {
  if (route.query.tab === 'tariff') {
    activeTab.value = 'tariff'
  }
})

watch(() => route.query.tab, (val) => {
  if (val === 'tariff') activeTab.value = 'tariff'
})

const whitelabelAvailable = ref(false)

const wlFeatures = [
  'Логотип агентства в отчётах',
  'Фирменный цвет в PDF и документах',
  'Шапка и подпись в отчётах',
  'Собственный домен для ссылок',
]

const brandFields = [
  { title: 'Логотип агентства', placeholder: 'Загрузите PNG, SVG или JPG' },
  { title: 'Фирменный цвет', placeholder: 'Выберите акцентный цвет или введите HEX' },
  { title: 'Шапка и подпись PDF', placeholder: 'Название агентства, контакты, подпись' },
  { title: 'Свой домен для отчётов', placeholder: 'reports.вашдомен.ru' },
]

const brandLogo = ref(null)
const brandColor = ref('#2563EB')
const presetColors = ['#2563EB', '#06B5D4', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#EF4444', '#171717']

const pdfHeader = ref('')
const pdfSignature = ref('')
const pdfModalOpen = ref(false)
const pdfHeaderDraft = ref('')
const pdfSignatureDraft = ref('')

watch(pdfModalOpen, (open) => {
  if (open) {
    pdfHeaderDraft.value = pdfHeader.value
    pdfSignatureDraft.value = pdfSignature.value
  }
})

function savePdf() {
  pdfHeader.value = pdfHeaderDraft.value
  pdfSignature.value = pdfSignatureDraft.value
  pdfModalOpen.value = false
}

const customDomain = ref('')
const domainStatus = ref('none')

const domainStatusClass = ref('inline-flex px-2 py-0.5 rounded-full text-[0.7639rem] font-semibold bg-[#f0f1f3] text-[#696969]')
const domainStatusLabel = ref('')

watch(domainStatus, (s) => {
  if (s === 'verified') {
    domainStatusClass.value = 'inline-flex px-2 py-0.5 rounded-full text-[0.7639rem] font-semibold bg-[#00ff4e]/10 text-[#16a34a]'
    domainStatusLabel.value = 'Подтверждён'
  } else if (s === 'pending') {
    domainStatusClass.value = 'inline-flex px-2 py-0.5 rounded-full text-[0.7639rem] font-semibold bg-[#F59E0B]/10 text-[#92400E]'
    domainStatusLabel.value = 'Ожидает проверки'
  } else if (s === 'error') {
    domainStatusClass.value = 'inline-flex px-2 py-0.5 rounded-full text-[0.7639rem] font-semibold bg-red-500/10 text-red-600'
    domainStatusLabel.value = 'Ошибка DNS'
  }
})

function handleLogoUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  brandLogo.value = URL.createObjectURL(file)
}
</script>

<style scoped>
.settings-card {
  background-color: #fff;
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 1.0417rem;
  padding: 1.3889rem;
}

:global(.dark) .settings-card {
  background-color: #2C2F3D;
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.07);
}

.settings-link {
  font-size: 0.9028rem;
  font-weight: 500;
  color: #2563eb;
  cursor: pointer;
  transition: opacity 0.2s;
}

.settings-link:hover {
  opacity: 0.75;
}

:global(.dark) .settings-link {
  color: #4A7AFF;
}
</style>
