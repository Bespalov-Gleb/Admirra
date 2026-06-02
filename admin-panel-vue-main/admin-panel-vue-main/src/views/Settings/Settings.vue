<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-x-hidden px-[1.875rem] py-[2.0833rem]">

    <div class="flex flex-col lg:flex-row gap-[2.2222rem] flex-1">
      <!-- Left: title + vertical tabs -->
      <aside class="lg:w-[20.1389rem] flex-shrink-0">
        <div class="pt-[1.0417rem] pb-[1.3889rem]">
          <h3 class="text-[2.0833rem] font-semibold leading-none text-[#171717] dark:text-white">Настройки</h3>
          <p class="text-[1.0417rem] font-medium text-[rgba(105,105,105,0.56)] dark:text-white/55 mt-[0.6944rem]">Конфигурация уровня аккаунта.</p>
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
        <div v-if="activeTab === 'brand'">

          <!-- Locked state -->
          <template v-if="!brand.whitelabel_available">
            <div class="flex items-center gap-[0.6944rem] mb-[1.7361rem]">
              <h4 class="text-[1.6667rem] font-semibold text-[#171717] dark:text-white">Бренд / White Label</h4>
              <span class="wl-lock-badge">
                <svg class="w-[0.7639rem] h-[0.7639rem]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
                Доступно на старшем тарифе
              </span>
            </div>

            <!-- Upsell card -->
            <div class="wl-upsell-card">
              <div class="absolute inset-0 pointer-events-none opacity-[0.12]" style="background: url('/admirra/img/pattern.png') center/5.3472rem"></div>
              <div class="relative z-10 flex flex-col lg:flex-row lg:items-center gap-[2.0833rem]">
                <div class="flex-1">
                  <h4 class="text-[1.5278rem] font-bold text-white mb-[0.6944rem] leading-[1.25]">Персонализируйте отчёты<br>под ваш бренд</h4>
                  <p class="text-[1.0417rem] text-white/75 mb-[1.3889rem] max-w-[31.9444rem] leading-[1.45]">
                    Клиенты видят ваш бренд, а не AdMirra — в PDF-отчётах, КП и сообщениях. Полный контроль над визуалом.
                  </p>
                  <div class="grid grid-cols-2 gap-x-[1.3889rem] gap-y-[0.6944rem] mb-[1.7361rem]">
                    <div v-for="item in wlFeatures" :key="item" class="flex items-center gap-[0.5556rem] text-[0.9722rem] text-white/90">
                      <span class="w-[1.25rem] h-[1.25rem] rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                        <svg class="w-[0.625rem] h-[0.625rem] text-white" viewBox="0 0 12 10" fill="currentColor"><path d="M4.2 9.2.4 5.4l1.4-1.4 2.4 2.4L10.2.3l1.4 1.4-7.4 7.5Z"/></svg>
                      </span>
                      {{ item }}
                    </div>
                  </div>
                  <button @click="selectTab('tariff')" class="wl-upsell-btn">
                    Перейти на старший тариф
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6"/></svg>
                  </button>
                </div>
              </div>
            </div>

            <!-- Dimmed preview -->
            <div class="mt-[2.0833rem] opacity-[0.35] pointer-events-none select-none" style="filter: grayscale(0.3) blur(0.3px)">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-[1.0417rem]">
                <div v-for="field in brandFields" :key="field.title" class="settings-card">
                  <div class="text-[0.9722rem] font-semibold text-[#171717] dark:text-white/80 mb-[0.6944rem]">{{ field.title }}</div>
                  <div class="h-[3.4722rem] rounded-[0.6944rem] bg-[#f5f7f9] dark:bg-white/5"></div>
                  <div class="text-[0.8333rem] text-[#696969]/40 dark:text-white/25 mt-[0.4861rem]">{{ field.placeholder }}</div>
                </div>
              </div>
            </div>
          </template>

          <!-- Unlocked state -->
          <template v-else>
            <div class="wl-config-head">
              <div>
                <div class="flex items-center gap-[0.6944rem] mb-[0.4861rem]">
                  <h4 class="text-[1.6667rem] font-semibold text-[#171717] dark:text-white">Бренд / White Label</h4>
                  <span class="wl-active-badge">Активно</span>
                </div>
                <p>Настройте логотип, фирменный цвет и подписи для клиентских материалов.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-[1.0417rem]">
              <!-- Logo -->
              <div class="settings-card">
                <div class="settings-card-title">Логотип агентства</div>
                <div v-if="brand.brand_logo_url" class="flex items-center gap-[1.0417rem] mb-[0.6944rem]">
                  <div class="w-[6.9444rem] h-[4.1667rem] rounded-[0.6944rem] border border-black/5 dark:border-white/10 flex items-center justify-center bg-[#f9fafb] dark:bg-white/5 overflow-hidden">
                    <img :src="brand.brand_logo_url" alt="Logo" class="max-h-full max-w-full object-contain" />
                  </div>
                  <div class="flex flex-col gap-[0.3472rem]">
                    <label class="settings-link cursor-pointer">
                      Заменить
                      <input type="file" accept="image/png,image/jpeg,image/svg+xml" class="hidden" @change="uploadLogo" />
                    </label>
                    <button class="settings-link settings-link--danger" @click="deleteLogo">Удалить</button>
                  </div>
                </div>
                <label v-else class="logo-upload-zone">
                  <svg class="w-[1.6667rem] h-[1.6667rem] text-[#b0b0b0] dark:text-white/30 mb-[0.3472rem]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/></svg>
                  <span class="text-[0.9028rem] text-[#696969]/50 dark:text-white/35">PNG, SVG или JPG · до 2 МБ</span>
                  <input type="file" accept="image/png,image/jpeg,image/svg+xml" class="hidden" @change="uploadLogo" />
                </label>
              </div>

              <!-- Brand color -->
              <div class="settings-card">
                <div class="settings-card-title">Фирменный цвет</div>
                <div class="flex items-center gap-[0.4861rem] flex-wrap mb-[0.8333rem]">
                  <button
                    v-for="color in presetColors"
                    :key="color"
                    class="color-swatch"
                    :style="{ backgroundColor: color }"
                    :class="{ 'color-swatch--selected': brand.brand_color === color }"
                    @click="brand.brand_color = color; saveBrand()"
                  />
                </div>
                <div class="flex items-center gap-[0.6944rem]">
                  <span class="text-[0.8333rem] text-[#696969]/50 dark:text-white/40 font-medium">HEX</span>
                  <div class="flex items-center gap-[0.4861rem] flex-1">
                    <input
                      v-model="brand.brand_color"
                      type="text"
                      maxlength="7"
                      class="settings-input w-[6.9444rem]"
                      placeholder="#2563EB"
                      @blur="saveBrand"
                    />
                    <span class="w-[2.0833rem] h-[2.0833rem] rounded-[0.4861rem] border border-black/10 dark:border-white/15 flex-shrink-0" :style="{ backgroundColor: brand.brand_color || '#ccc' }"></span>
                  </div>
                </div>
              </div>

              <!-- PDF header/footer -->
              <div class="settings-card">
                <div class="settings-card-title">Шапка и подпись PDF</div>
                <div v-if="brand.brand_pdf_header || brand.brand_pdf_signature">
                  <div class="text-[0.9028rem] text-[#444] dark:text-white/70 leading-[1.4]">{{ brand.brand_pdf_header }}</div>
                  <div v-if="brand.brand_pdf_signature" class="text-[0.8333rem] text-[#696969]/50 dark:text-white/35 mt-[0.2778rem] leading-[1.4]">{{ brand.brand_pdf_signature }}</div>
                </div>
                <div v-else class="text-[0.9028rem] text-[#696969]/40 dark:text-white/30 italic">Не заполнено</div>
                <button class="settings-link mt-[0.6944rem]" @click="openPdfModal">Редактировать</button>
              </div>

              <!-- Preview -->
              <div class="settings-card settings-card--preview">
                <div class="settings-card-title">Предпросмотр</div>
                <div class="brand-preview">
                  <div class="brand-preview__logo">
                    <img v-if="brand.brand_logo_url" :src="brand.brand_logo_url" alt="Logo preview" />
                    <span v-else>WL</span>
                  </div>
                  <div class="min-w-0">
                    <div class="brand-preview__name">{{ brand.brand_pdf_header || 'Ваш бренд' }}</div>
                    <div class="brand-preview__line" :style="{ backgroundColor: brand.brand_color || '#2563EB' }"></div>
                  </div>
                </div>
                <p class="brand-preview__hint">Такой стиль будет использоваться в отчётах и PDF-документах. Собственная ссылка будет подключаться отдельно позже.</p>
              </div>
            </div>
          </template>
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
  'Логотип агентства в отчётах',
  'Фирменный цвет в PDF',
  'Шапка и подпись в документах',
  'Премиальный вид клиентских материалов',
]

const brandFields = [
  { title: 'Логотип агентства', placeholder: 'Загрузите изображение' },
  { title: 'Фирменный цвет', placeholder: 'Выберите цвет или введите HEX' },
  { title: 'Шапка и подпись PDF', placeholder: 'Название, контакты, подпись' },
  { title: 'Предпросмотр', placeholder: 'Проверьте внешний вид материалов' },
]

const presetColors = ['#2563EB', '#06B5D4', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#EF4444', '#171717']

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
