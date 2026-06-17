<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-x-hidden px-[1.875rem] py-[2.0833rem]">

    <div class="flex flex-col lg:flex-row gap-[2.2222rem] flex-1">
      <!-- Left: title + vertical tabs -->
      <aside class="lg:w-[20.1389rem] flex-shrink-0">
        <div class="settings-page-head">
          <h3>Настройки</h3>
          <p>Конфигурация уровня аккаунта.</p>
        </div>
        <div class="settings-sidebar">
          <nav class="flex flex-col gap-[0.2083rem]">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              @click="selectTab(tab.id)"
              :class="[
                'settings-tab-btn',
                activeTab === tab.id ? 'settings-tab-btn--active' : '',
              ]"
            >
              <component :is="tab.icon" class="w-[1.1111rem] h-[1.1111rem] flex-shrink-0" />
              <span class="flex-1">{{ tab.label }}</span>
              <svg v-if="tab.id === 'brand' && !brand.whitelabel_available" class="w-[0.8333rem] h-[0.8333rem] flex-shrink-0 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>
              </svg>
            </button>
          </nav>
        </div>
      </aside>

      <!-- Right: tab content -->
      <div class="flex-1 min-w-0">

        <!-- ===== Tab: Бренд / White Label ===== -->
        <div v-if="activeTab === 'brand'" class="wl-page">
          <div class="wl-page-head">
            <h4>Бренд / White Label</h4>
            <p>Оформите свой бренд через тех. панель</p>
          </div>

          <section v-if="!brand.whitelabel_available" class="wl-feature-panel">
            <h5>Брендируйте отчеты под свое агентство</h5>
            <p>Клиент видит ваш бренд, а не AdMirra. Доступно на тарифе Профи и выше.</p>
            <div class="wl-feature-grid">
              <article v-for="item in wlFeatures" :key="item" class="wl-feature-tile">
                <span class="wl-feature-check">
                  <svg viewBox="0 0 12 10" aria-hidden="true">
                    <path d="M4.2 9.2.4 5.4l1.4-1.4 2.4 2.4L10.2.3l1.4 1.4-7.4 7.5Z" />
                  </svg>
                </span>
                <strong>{{ item }}</strong>
              </article>
            </div>
            <button type="button" class="wl-upgrade-button" @click="selectTab('tariff')">
              Перейти на тариф «Профи»
            </button>
            <img
              class="wl-feature-fox"
              src="/admirra/img/white-label/banner-fox.png"
              alt=""
              aria-hidden="true"
            />
          </section>

          <p v-if="!brand.whitelabel_available" class="wl-preview-title">Как это будет выглядеть — превью:</p>

          <div class="wl-tools" :class="{ 'wl-tools--locked': !brand.whitelabel_available }">
            <section class="wl-tool-card wl-tool-card--logo">
              <h5>Логотип агентства</h5>
              <p>Подставляется в PDF-отчеты, КП и сообщения клиентам.</p>
              <div v-if="brand.brand_logo_url" class="wl-logo-preview">
                <img :src="brand.brand_logo_url" alt="Logo" />
              </div>
              <label v-else class="wl-logo-drop">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M4.5 18.75h15A1.25 1.25 0 0 0 20.75 17.5v-11A1.25 1.25 0 0 0 19.5 5.25h-15A1.25 1.25 0 0 0 3.25 6.5v11a1.25 1.25 0 0 0 1.25 1.25Z" stroke="currentColor" stroke-width="1.5"/>
                  <path d="m7 15 3.05-3.05a1 1 0 0 1 1.41 0L14 14.5l1.05-1.05a1 1 0 0 1 1.41 0L19 16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  <circle cx="8.25" cy="8.75" r="1.25" stroke="currentColor" stroke-width="1.5"/>
                </svg>
                <input
                  v-if="brand.whitelabel_available"
                  type="file"
                  accept="image/png,image/jpeg,image/svg+xml"
                  @change="uploadLogo"
                />
              </label>
              <div class="wl-logo-actions">
                <label v-if="brand.whitelabel_available" class="wl-primary-button">
                  {{ brand.brand_logo_url ? 'Заменить логотип' : 'Загрузить логотип' }}
                  <span>+</span>
                  <input type="file" accept="image/png,image/jpeg,image/svg+xml" @change="uploadLogo" />
                </label>
                <button v-else class="wl-primary-button" type="button" disabled>
                  Загрузить логотип
                  <span>+</span>
                </button>
                <button v-if="brand.whitelabel_available && brand.brand_logo_url" class="wl-text-danger" type="button" @click="deleteLogo">
                  Удалить
                </button>
              </div>
            </section>

            <section class="wl-tool-card wl-tool-card--color">
              <h5>Фирменный цвет</h5>
              <p>Акцент в отчетах и брендированных документах.</p>
              <div class="wl-color-row">
                <button
                  v-for="color in presetColors"
                  :key="color"
                  type="button"
                  class="wl-color-dot"
                  :class="{ 'wl-color-dot--selected': brand.brand_color === color }"
                  :style="{ backgroundColor: color }"
                  :disabled="!brand.whitelabel_available"
                  @click="brand.brand_color = color; saveBrand()"
                />
              </div>
              <input
                v-model="brand.brand_color"
                class="wl-hex-input"
                type="text"
                maxlength="7"
                placeholder="#171717"
                :readonly="!brand.whitelabel_available"
                @blur="brand.whitelabel_available && saveBrand()"
              />
            </section>
          </div>

          <section class="wl-wide-card" :class="{ 'wl-wide-card--locked': !brand.whitelabel_available }">
            <div>
              <h5>Шапка и подпись PDF</h5>
              <p>{{ brand.brand_pdf_header || 'Название агентства, контакты,подпись внизу отчета.' }}</p>
            </div>
            <button
              type="button"
              class="wl-secondary-button"
              :disabled="!brand.whitelabel_available"
              @click="openPdfModal"
            >
              Редактировать
            </button>
          </section>

          <section class="wl-wide-card" :class="{ 'wl-wide-card--locked': !brand.whitelabel_available }">
            <div>
              <h5>Свой домен для ссылок на отчеты</h5>
              <p>{{ brand.brand_custom_domain || 'reports.ваше-агентство.ru вместо домена AdMirra.' }}</p>
            </div>
            <button type="button" class="wl-plan-button" disabled>По тарифу</button>
          </section>
        </div>

        <!-- ===== Tab: Тариф и оплата ===== -->
        <div v-else-if="activeTab === 'tariff'">
          <TariffsContent />
        </div>

      </div>
    </div>

    <!-- PDF edit modal -->
    <Teleport to="body">
      <div v-if="pdfModalOpen" class="fixed inset-0 z-[9000] flex items-center justify-center bg-black/50 p-4" @click.self="pdfModalOpen = false">
        <div class="w-full max-w-[33.3333rem] rounded-[1.3889rem] border border-black/5 bg-white dark:bg-[#2C2F3D] dark:border-white/10 p-[2.0833rem] shadow-[0_1.3889rem_3.4722rem_rgba(0,0,0,0.12)]">
          <h4 class="text-[1.3889rem] font-bold text-[#171717] dark:text-gray-100 mb-[1.3889rem]">Шапка и подпись PDF</h4>
          <div class="flex flex-col gap-[1.0417rem] mb-[1.7361rem]">
            <div>
              <label class="block text-[0.9028rem] font-medium text-[#696969] dark:text-white/55 mb-[0.4861rem]">Название агентства / шапка</label>
              <input v-model="pdfHeaderDraft" type="text" class="settings-input w-full" placeholder="ООО «Рекламное агентство»" />
            </div>
            <div>
              <label class="block text-[0.9028rem] font-medium text-[#696969] dark:text-white/55 mb-[0.4861rem]">Подпись / контакты внизу</label>
              <textarea v-model="pdfSignatureDraft" rows="3" class="settings-input w-full resize-y" placeholder="Телефон, email, адрес"></textarea>
            </div>
          </div>
          <div class="flex gap-[0.6944rem]">
            <button class="settings-btn-primary" @click="savePdf">Сохранить</button>
            <button class="settings-btn-secondary" @click="pdfModalOpen = false">Отмена</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { SwatchIcon, CreditCardIcon } from '@heroicons/vue/24/outline'
import api from '@/api/axios'
import { useToaster } from '@/composables/useToaster'
import TariffsContent from '../Tariffs/TariffsPage.vue'

const route = useRoute()
const router = useRouter()
const toaster = useToaster()

const activeTab = ref('brand')

const tabs = [
  { id: 'brand', label: 'Бренд / White Label', icon: SwatchIcon },
  { id: 'tariff', label: 'Тариф и оплата', icon: CreditCardIcon },
]

const selectTab = (tabId) => {
  activeTab.value = tabId
  router.replace({ path: '/settings', query: tabId === 'tariff' ? { tab: 'tariff' } : {} })
}

onMounted(() => {
  if (route.query.tab === 'tariff') activeTab.value = 'tariff'
  loadBrand()
})

watch(() => route.query.tab, (val) => {
  if (val === 'tariff') activeTab.value = 'tariff'
  else if (!val) activeTab.value = 'brand'
})

const brand = reactive({
  brand_logo_url: null,
  brand_color: '#2563EB',
  brand_pdf_header: '',
  brand_pdf_signature: '',
  brand_custom_domain: '',
  brand_domain_status: 'none',
  whitelabel_available: false,
})

const wlFeatures = [
  'Свой логотип в PDF и сообщениях',
  'Свой домен для ссылок',
  'Фирменный стиль отчетов',
  'Шапка и подпись в PDF',
]

const brandFields = [
  { title: 'Логотип агентства', placeholder: 'Загрузите изображение' },
  { title: 'Фирменный цвет', placeholder: 'Выберите цвет или введите HEX' },
  { title: 'Шапка и подпись PDF', placeholder: 'Название, контакты, подпись' },
  { title: 'Предпросмотр', placeholder: 'Проверьте внешний вид материалов' },
]

const presetColors = ['#CE633C', '#5189D7', '#4FA37D', '#7C70D6']

const pdfModalOpen = ref(false)
const pdfHeaderDraft = ref('')
const pdfSignatureDraft = ref('')

async function loadBrand() {
  try {
    const { data } = await api.get('brand')
    Object.assign(brand, data)
  } catch { /* keep defaults */ }
}

async function saveBrand() {
  if (brand.brand_color && !/^#[0-9A-Fa-f]{6}$/.test(brand.brand_color)) {
    toaster.error('Введите цвет в формате #2563EB')
    return
  }
  try {
    const { data } = await api.put('brand', {
      brand_color: brand.brand_color,
      brand_pdf_header: brand.brand_pdf_header,
      brand_pdf_signature: brand.brand_pdf_signature,
    })
    Object.assign(brand, data)
  } catch (e) {
    const msg = e?.response?.data?.detail
    if (msg) toaster.error(msg)
  }
}

async function uploadLogo(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const form = new FormData()
  form.append('file', file)
  try {
    const { data } = await api.post('brand/logo', form)
    Object.assign(brand, data)
    toaster.success('Логотип загружен')
  } catch (e) {
    toaster.error(e?.response?.data?.detail || 'Не удалось загрузить логотип')
  }
}

async function deleteLogo() {
  try {
    const { data } = await api.delete('brand/logo')
    Object.assign(brand, data)
    toaster.success('Логотип удалён')
  } catch (e) {
    toaster.error(e?.response?.data?.detail || 'Не удалось удалить логотип')
  }
}

function openPdfModal() {
  pdfHeaderDraft.value = brand.brand_pdf_header || ''
  pdfSignatureDraft.value = brand.brand_pdf_signature || ''
  pdfModalOpen.value = true
}

async function savePdf() {
  brand.brand_pdf_header = pdfHeaderDraft.value
  brand.brand_pdf_signature = pdfSignatureDraft.value
  pdfModalOpen.value = false
  await saveBrand()
}
</script>

<style scoped>
.settings-page-head {
  margin: 0 0 1.875rem;
}
.settings-page-head h3 {
  margin: 0;
  color: #171717;
  font-size: 2.0833rem;
  font-weight: 700;
  line-height: 1;
}
:global(.dark) .settings-page-head h3 { color: #fff; }
.settings-page-head p {
  margin: 0.8333rem 0 0;
  color: rgba(105, 105, 105, 0.56);
  font-size: 1.0417rem;
  font-weight: 500;
}
:global(.dark) .settings-page-head p { color: rgba(255,255,255,0.55); }

.settings-sidebar {
  background: #fff;
  border-radius: 1.0417rem;
  padding: 0.8333rem;
  border: 1px solid rgba(0,0,0,0.05);
}
:global(.dark) .settings-sidebar {
  background: #2C2F3D;
  border-color: rgba(255,255,255,0.08);
  box-shadow: 0 4px 24px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.07);
}

.settings-tab-btn {
  display: flex;
  align-items: center;
  gap: 0.6944rem;
  width: 100%;
  text-align: left;
  padding: 0.8333rem 1.0417rem;
  border-radius: 0.6944rem;
  font-size: 0.9722rem;
  font-weight: 500;
  color: rgba(105,105,105,0.65);
  transition: all 0.2s;
  border: none;
  background: transparent;
  cursor: pointer;
}
.settings-tab-btn:hover {
  background: #f5f7f9;
  color: #171717;
}
.settings-tab-btn--active {
  background: #ecf3fe;
  color: #2563eb;
  font-weight: 600;
}
:global(.dark) .settings-tab-btn { color: rgba(255,255,255,0.55); }
:global(.dark) .settings-tab-btn:hover { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.85); }
:global(.dark) .settings-tab-btn--active { background: rgba(255,255,255,0.10); color: #4A7AFF; }

.settings-card {
  background: #fff;
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 1.0417rem;
  padding: 1.3889rem;
  box-shadow: 0 0.6944rem 1.9444rem rgba(15, 23, 42, 0.035);
}
:global(.dark) .settings-card {
  background: #2C2F3D;
  border-color: rgba(255,255,255,0.08);
  box-shadow: 0 4px 24px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.07);
}
.settings-card--preview {
  background: linear-gradient(180deg, #ffffff, #f8fbff);
}
:global(.dark) .settings-card--preview {
  background: linear-gradient(180deg, #2C2F3D, rgba(74,122,255,0.08));
}

.settings-card-title {
  font-size: 0.9722rem;
  font-weight: 600;
  color: #171717;
  margin-bottom: 0.8333rem;
}
:global(.dark) .settings-card-title { color: rgba(255,255,255,0.85); }

.settings-input {
  padding: 0.6944rem 0.8333rem;
  border-radius: 0.6944rem;
  font-size: 0.9028rem;
  background: #f5f7f9;
  border: 1px solid transparent;
  outline: none;
  color: #171717;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.settings-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.08);
}
:global(.dark) .settings-input {
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.88);
}

.settings-link {
  font-size: 0.9028rem;
  font-weight: 500;
  color: #2563eb;
  cursor: pointer;
  background: none;
  border: none;
  padding: 0;
  transition: opacity 0.2s;
}
.settings-link:hover { opacity: 0.7; }
.settings-link--danger { color: #ef4444; }
:global(.dark) .settings-link { color: #4A7AFF; }
:global(.dark) .settings-link--danger { color: #f87171; }

.settings-btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3.0556rem;
  padding: 0 1.3889rem;
  border-radius: 0.8333rem;
  font-size: 0.9722rem;
  font-weight: 500;
  color: #fff;
  background: #2563eb;
  border: none;
  cursor: pointer;
  transition: background 0.2s;
}
.settings-btn-primary:hover { background: #1d4ed8; }

.settings-btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3.0556rem;
  padding: 0 1.3889rem;
  border-radius: 0.8333rem;
  font-size: 0.9722rem;
  font-weight: 500;
  color: #696969;
  background: #fff;
  border: 1px solid rgba(0,0,0,0.1);
  cursor: pointer;
  transition: background 0.2s;
}
.settings-btn-secondary:hover { background: #f9fafb; }
:global(.dark) .settings-btn-secondary {
  background: rgba(255,255,255,0.05);
  border-color: rgba(255,255,255,0.15);
  color: rgba(255,255,255,0.7);
}

.wl-page {
  width: 100%;
  max-width: 70.625rem;
}

.wl-page-head {
  margin: 0 0 1.7361rem;
}

.wl-page-head h4 {
  margin: 0;
  color: #2563eb;
  font-size: 2.0833rem;
  font-weight: 800;
  line-height: 1.08;
  letter-spacing: 0;
}

.wl-page-head p {
  margin: 0.6944rem 0 0;
  color: rgba(105, 105, 105, 0.56);
  font-size: 1.0417rem;
  font-weight: 500;
  line-height: 1.35;
}

.wl-feature-panel {
  position: relative;
  min-height: 16.6667rem;
  padding: 1.9444rem 20.1389rem 1.9444rem 2.0833rem;
  overflow: hidden;
  border-radius: 0.8333rem;
  background: url('/admirra/img/white-label/banner-bg.jpg') center / cover no-repeat, #3a5fd9;
}

.wl-feature-panel h5 {
  margin: 0;
  color: #fff;
  font-size: 1.3194rem;
  font-weight: 600;
  line-height: 1.25;
}

.wl-feature-panel p {
  margin: 0.6944rem 0 1.4583rem;
  max-width: 34.7222rem;
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.9722rem;
  font-weight: 500;
  line-height: 1.4;
}

.wl-feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9028rem 2.0833rem;
  max-width: 36.1111rem;
}

.wl-feature-tile {
  display: flex;
  align-items: center;
  gap: 0.6944rem;
  background: transparent;
}

.wl-feature-check {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.1806rem;
  height: 1.1806rem;
  border-radius: 0.2083rem;
  background: #fff;
  color: #2563eb;
}

.wl-feature-check svg {
  width: 0.6597rem;
  height: 0.5498rem;
  fill: currentColor;
}

.wl-feature-tile strong {
  color: #fff;
  font-size: 0.9028rem;
  font-weight: 500;
  line-height: 1.18;
}

.wl-upgrade-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 12.9861rem;
  min-height: 2.7778rem;
  margin-top: 1.7361rem;
  padding: 0 1.1111rem;
  border: 0;
  border-radius: 0.5556rem;
  background: #fff;
  color: #2563eb;
  font-size: 0.8333rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.wl-upgrade-button:hover {
  opacity: 0.92;
}

.wl-feature-fox {
  position: absolute;
  right: 0.2778rem;
  bottom: -1.9444rem;
  height: 21.5278rem;
  width: auto;
  object-fit: contain;
  pointer-events: none;
  user-select: none;
}

.wl-preview-title {
  margin: 3.8889rem 0 1.7361rem;
  color: rgba(105, 105, 105, 0.56);
  font-size: 1.0417rem;
  font-weight: 500;
}

.wl-tools {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.875rem;
  margin-bottom: 1.875rem;
}

.wl-tools--locked {
  opacity: 0.35;
  pointer-events: none;
  user-select: none;
}

.wl-tool-card,
.wl-wide-card {
  background: #fff;
  border: 1px solid rgba(23, 23, 23, 0.03);
  border-radius: 0.8333rem;
  box-shadow: none;
}

.wl-tool-card {
  min-height: 22rem;
  padding: 1.8056rem 2.0833rem 1.7361rem;
}

.wl-tool-card h5,
.wl-wide-card h5 {
  margin: 0;
  color: #171717;
  font-size: 1.3889rem;
  font-weight: 500;
  line-height: 1.2;
}

.wl-tool-card p,
.wl-wide-card p {
  margin: 0.8333rem 0 0;
  color: rgba(105, 105, 105, 0.72);
  font-size: 1.0417rem;
  font-weight: 500;
  line-height: 1.35;
}

.wl-logo-preview,
.wl-logo-drop {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 8.4722rem;
  margin-top: 1.7361rem;
  border: 1px dashed rgba(23, 23, 23, 0.15);
  border-radius: 0.6944rem;
  background: #fff;
  color: rgba(105, 105, 105, 0.24);
}

.wl-logo-preview img {
  max-width: 80%;
  max-height: 80%;
  object-fit: contain;
}

.wl-logo-drop svg {
  width: 2.3611rem;
  height: 2.3611rem;
}

.wl-logo-drop input,
.wl-primary-button input {
  display: none;
}

.wl-logo-actions {
  display: flex;
  align-items: center;
  gap: 0.8333rem;
  margin-top: 1.25rem;
}

.wl-primary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.6944rem;
  width: 100%;
  min-height: 3.2639rem;
  border: 0;
  border-radius: 0.5556rem;
  background: #2563eb;
  color: #fff;
  font-size: 0.9028rem;
  font-weight: 500;
  cursor: pointer;
}

.wl-primary-button span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 0.9028rem;
  height: 0.9028rem;
  padding-bottom: 0.0694rem;
  border-radius: 50%;
  background: rgba(23, 23, 23, 0.2);
  font-size: 0.8333rem;
  font-weight: 700;
  line-height: 1;
}

.wl-text-danger {
  border: 0;
  background: transparent;
  color: #ef4444;
  font-size: 0.9028rem;
  font-weight: 500;
  cursor: pointer;
}

.wl-color-row {
  display: flex;
  align-items: center;
  gap: 0.9028rem;
  margin-top: 2.4306rem;
}

.wl-color-dot {
  width: 5.4167rem;
  height: 5.4167rem;
  border: 3px solid transparent;
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.15s, border-color 0.15s;
}

.wl-color-dot:not(:disabled):hover,
.wl-color-dot--selected {
  border-color: #fff;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25);
  transform: translateY(-1px);
}

.wl-hex-input {
  width: 10.4167rem;
  height: 3.8194rem;
  margin-top: 1.875rem;
  padding: 0 1.25rem;
  border: 1px solid rgba(23, 23, 23, 0.08);
  border-radius: 0.6944rem;
  outline: none;
  background: #fff;
  color: #171717;
  font-size: 1.3889rem;
  font-weight: 500;
  letter-spacing: 0;
}

.wl-hex-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.wl-wide-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.3889rem;
  min-height: 7.9167rem;
  margin-top: 1.875rem;
  padding: 1.7361rem 1.7361rem 1.7361rem 2.0833rem;
}

.wl-wide-card--locked {
  opacity: 0.35;
  pointer-events: none;
  user-select: none;
}

.wl-secondary-button,
.wl-plan-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 12.2222rem;
  min-height: 2.7778rem;
  padding: 0 1.25rem;
  border: 0;
  border-radius: 0.5556rem;
  font-size: 0.9028rem;
  font-weight: 500;
}

.wl-secondary-button {
  background: #2563eb;
  color: #fff;
  cursor: pointer;
}

.wl-plan-button {
  background: rgba(34, 197, 94, 0.10);
  color: #59bd6a;
}

.wl-secondary-button:disabled,
.wl-primary-button:disabled {
  cursor: default;
}

:global(.dark) .wl-page-head h4,
:global(.dark) .wl-tool-card h5,
:global(.dark) .wl-wide-card h5 {
  color: #fff;
}

:global(.dark) .wl-tool-card,
:global(.dark) .wl-wide-card {
  background: #2c2f3d;
  border-color: rgba(255, 255, 255, 0.08);
}

:global(.dark) .wl-logo-preview,
:global(.dark) .wl-logo-drop,
:global(.dark) .wl-hex-input {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.85);
}

@media (max-width: 1024px) {
  .wl-page {
    width: 100%;
  }
  .wl-feature-panel {
    padding-right: 2.0833rem;
  }
  .wl-feature-fox {
    display: none;
  }
  .wl-feature-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .wl-tools {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .wl-page-head h4 {
    font-size: 1.7361rem;
  }
  .wl-feature-panel,
  .wl-tool-card,
  .wl-wide-card {
    padding: 1.25rem;
  }
  .wl-feature-grid {
    grid-template-columns: 1fr;
  }
  .wl-wide-card {
    align-items: stretch;
    flex-direction: column;
  }
  .wl-secondary-button,
  .wl-plan-button {
    width: 100%;
  }
}

.wl-lock-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  padding: 0.3472rem 0.8333rem;
  border-radius: 2.7778rem;
  background: #f0f1f3;
  font-size: 0.7639rem;
  font-weight: 600;
  color: #696969;
}
:global(.dark) .wl-lock-badge { background: rgba(255,255,255,0.10); color: rgba(255,255,255,0.55); }

.wl-active-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.3472rem 0.8333rem;
  border-radius: 2.7778rem;
  background: rgba(0,255,78,0.10);
  font-size: 0.7639rem;
  font-weight: 700;
  color: #16a34a;
}
:global(.dark) .wl-active-badge { background: rgba(0,255,78,0.15); color: #5ee886; }

.wl-config-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.7361rem;
}
.wl-config-head p {
  margin: 0;
  color: rgba(105,105,105,0.56);
  font-size: 0.9722rem;
  font-weight: 500;
  line-height: 1.45;
}
:global(.dark) .wl-config-head p { color: rgba(255,255,255,0.48); }

.wl-upsell-card {
  position: relative;
  overflow: hidden;
  border-radius: 1.3889rem;
  padding: 2.5rem 2.0833rem;
  background: linear-gradient(135deg, #1e40af 0%, #2563eb 35%, #1f9de4 70%, #06b5d4 100%);
}

.wl-upsell-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5556rem;
  min-height: 3.1944rem;
  padding: 0 1.6667rem;
  border-radius: 0.8333rem;
  background: #fff;
  color: #2563eb;
  font-size: 0.9722rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
}
.wl-upsell-btn:hover {
  transform: scale(1.03);
  box-shadow: 0 0.6944rem 2.0833rem rgba(0,0,0,0.15);
}

.logo-upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 6.25rem;
  border: 2px dashed #e1e1e1;
  border-radius: 0.8333rem;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.logo-upload-zone:hover {
  border-color: #2563eb;
  background: rgba(37,99,235,0.02);
}
:global(.dark) .logo-upload-zone { border-color: rgba(255,255,255,0.12); }
:global(.dark) .logo-upload-zone:hover { border-color: #4A7AFF; background: rgba(74,122,255,0.04); }

.color-swatch {
  width: 2.0833rem;
  height: 2.0833rem;
  border-radius: 50%;
  border: 2.5px solid transparent;
  cursor: pointer;
  transition: transform 0.15s, border-color 0.15s;
}
.color-swatch:hover { transform: scale(1.1); }
.color-swatch--selected {
  border-color: #171717;
  transform: scale(1.15);
  box-shadow: 0 0 0 2px #fff, 0 0 0 4px currentColor;
}
:global(.dark) .color-swatch--selected { border-color: #fff; box-shadow: 0 0 0 2px #2C2F3D, 0 0 0 4px currentColor; }

.brand-preview {
  display: flex;
  align-items: center;
  gap: 0.9722rem;
  min-height: 5.5556rem;
  padding: 1.0417rem;
  border-radius: 0.8333rem;
  background: #fff;
  border: 1px solid rgba(0,0,0,0.05);
}
:global(.dark) .brand-preview {
  background: rgba(255,255,255,0.05);
  border-color: rgba(255,255,255,0.08);
}
.brand-preview__logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 4.1667rem;
  height: 4.1667rem;
  flex-shrink: 0;
  border-radius: 0.8333rem;
  background: #f5f7f9;
  color: #2563eb;
  font-size: 1.1111rem;
  font-weight: 900;
  overflow: hidden;
}
.brand-preview__logo img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.brand-preview__name {
  color: #171717;
  font-size: 1.1111rem;
  font-weight: 800;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:global(.dark) .brand-preview__name { color: rgba(255,255,255,0.9); }
.brand-preview__line {
  width: 8.3333rem;
  height: 0.4167rem;
  max-width: 100%;
  margin-top: 0.6944rem;
  border-radius: 2.7778rem;
}
.brand-preview__hint {
  margin: 0.8333rem 0 0;
  color: rgba(105,105,105,0.48);
  font-size: 0.8333rem;
  line-height: 1.45;
}
:global(.dark) .brand-preview__hint { color: rgba(255,255,255,0.36); }

.domain-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.2083rem 0.5556rem;
  border-radius: 2.7778rem;
  font-size: 0.7639rem;
  font-weight: 600;
}
.domain-badge--verified { background: rgba(0,255,78,0.10); color: #16a34a; }
.domain-badge--pending { background: rgba(245,158,11,0.10); color: #92400e; }
.domain-badge--error { background: rgba(239,68,68,0.10); color: #dc2626; }
</style>
