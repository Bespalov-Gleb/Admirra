<template>
  <div class="admirra-page-wrapper" :class="{ 'projects-page--dark': isDarkMode }">
    <section class="main-section">
      <div class="py-4 mb-3">
        <h3 class="heading-3">Проекты</h3>
      </div>

      <div class="row gy-3 mb-5">
        <div class="col-12 col-md">
          <div class="projects-filters-row">
            <div class="projects-filters-period">
              <select
                class="projects-period-select"
                :class="{ 'is-dark-input': isDarkMode }"
                v-model.number="periodDays"
                @change="reloadMetrics"
              >
                <option :value="14">2 недели</option>
                <option :value="30">30 дней</option>
                <option :value="90">90 дней</option>
              </select>
            </div>
            <div class="projects-filters-search input-item">
              <input
                class="input _search-project"
                :class="{ 'is-dark-input': isDarkMode }"
                :style="searchInputStyle"
                type="text"
                placeholder="Поиск по проектам, номерам или доменам"
                v-model="search"
              />
              <div class="input-icon">
                <svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#search"></use></svg>
              </div>
            </div>
          </div>
        </div>
        <div class="col-12 col-md-auto">
          <div class="row g-3">
            <div class="col-auto">
              <button type="button" class="btn _primary" @click="openMassEdit">
                <div class="btn__inner">
                  <span class="btn__text">Массовое редактирование</span>
                  <div class="btn__icon"><svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#edit"></use></svg></div>
                </div>
              </button>
            </div>
            <div class="col-auto ms-auto">
              <div class="row">
                <div class="col-auto">
                  <button :class="['btn-ico', { _active: viewType === 'grid' }]" @click="viewType = 'grid'">
                    <svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#grid"></use></svg>
                  </button>
                </div>
                <div class="col-auto">
                  <button :class="['btn-ico', { _active: viewType === 'rows' }]" @click="viewType = 'rows'">
                    <svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#rows"></use></svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="isLoading" class="py-5 text-center gray56">Загрузка проектов...</div>
      <div v-else-if="filteredProjects.length === 0" class="py-5 text-center gray56">
        {{ search ? 'Проекты не найдены' : 'У вас пока нет проектов' }}
      </div>

      <!-- ВИД 1: Карточки (как в новом макете) -->
      <div v-else-if="viewType === 'grid'" class="row gy-4 mb-5">
        <div v-for="project in filteredProjects" :key="project.id" class="col-12 col-xxl-6">
          <div class="h-100 radius-base projects-grid-card">
            <div class="p-5">
              <div class="row pb-3 mb-4">
                <div class="col">
                  <div class="d-flex">
                    <div class="avatar-40x40 align-self-center">
                      <div class="project-avatar-40">{{ projectInitials(project.name) }}</div>
                    </div>
                    <div class="ps-4 align-self-center">
                      <h4 class="mb-1 text-15 gray project-card-title">{{ project.name }}</h4>
                      <p class="gray56 project-card-desc">{{ project.description || 'Описание проекта краткое' }}</p>
                    </div>
                  </div>
                </div>
                <div class="col-auto">
                  <button type="button" class="circle-btn project-card-open" @click="openProject(project)">
                    <svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
                  </button>
                </div>
              </div>

              <div class="row g-4">
                <div v-for="(stat, idx) in getProjectStats(project)" :key="idx" class="col-12 col-sm-6 col-md-4">
                  <div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110 projects-metric-tile">
                    <div class="d-flex pb-2 mb-4">
                      <div class="iconbox">
                        <svg><use :href="stat.icon"></use></svg>
                      </div>
                      <div class="ps-3 align-self-center">
                        <h4 class="mb-1 gray metric-label">{{ stat.label }}</h4>
                        <p class="text-12 gray56 metric-sub">{{ stat.subtitle }}</p>
                      </div>
                    </div>
                    <div class="d-flex align-items-center mt-auto">
                      <b class="text-20 me-3 metric-value">{{ stat.value }}</b>
                      <div class="badge _success">
                        <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                        {{ stat.change }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <hr class="hr-line projects-card-hr" />
            <div class="p-5">
              <div class="gray mb-3 balance-section-title">Актуальный баланс в ЛК:</div>
              <div class="row g-4">
                <div v-if="hasPlatform(project, 'YANDEX')" class="col-12 col-sm-6 col-md-4">
                  <div class="h-100 radius p-3 bg-orangelight">
                    <div class="h-100 d-flex align-items-center justify-content-center">
                      <img width="18" src="/admirra/img/icons/yandex-direct.png" alt="Yandex" />
                      <div class="px-3 c71663e">Yandex Direct</div>
                      <div class="badge-white c71663e">{{ formatMoney(getProjectMetric(project.id).balance) }}</div>
                    </div>
                  </div>
                </div>
                <div v-if="hasPlatform(project, 'VK')" class="col-12 col-sm-6 col-md-4">
                  <div class="h-100 radius p-3 bg-oceanlight">
                    <div class="h-100 d-flex align-items-center justify-content-center">
                      <img width="18" src="/admirra/img/icons/vk-ads.png" alt="VK" />
                      <div class="px-3 c5385C1">VK Ads Manager</div>
                      <div class="badge-white c5385C1">{{ formatMoney(getProjectMetric(project.id).balance) }}</div>
                    </div>
                  </div>
                </div>
                <div v-if="!project.integrations?.length" class="col-12 col-sm-6 col-md-4">
                  <div class="h-100 radius p-3 bg-azurelight d-flex align-items-center justify-content-center gray56">Нет интеграций</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ВИД 2: Таблица (новая локальная вёрстка, не старый экран) -->
      <div v-else class="projects-rows-wrap radius-base py-4 mb-5 projects-table-shell">
        <div class="table-container">
          <table class="projects-rows-table">
            <thead>
              <tr class="gray56">
                <th class="bb-light px-3 pb-3" style="width:2.5rem">
                  <label class="d-flex align-items-center justify-content-center mb-0 cursor-pointer">
                    <input
                      type="checkbox"
                      class="form-check-input"
                      :checked="allRowsSelected"
                      @change="toggleSelectAllRows"
                    />
                  </label>
                </th>
                <th class="bb-light px-3 pb-3">Проект</th>
                <th class="bb-light px-3 pb-3">Интеграции</th>
                <th class="bb-light px-3 pb-3">Показы</th>
                <th class="bb-light px-3 pb-3">Клики</th>
                <th class="bb-light px-3 pb-3">Расходы</th>
                <th class="bb-light px-3 pb-3">Лиды</th>
                <th class="bb-light px-3 pb-3">CPC</th>
                <th class="bb-light px-3 pb-3">CPA</th>
                <th class="bb-light px-3 pb-3">Статус</th>
                <th class="bb-light px-3 pb-3">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="project in filteredProjects" :key="project.id">
                <td class="bb-light px-3 py-4 align-middle">
                  <input
                    type="checkbox"
                    class="form-check-input"
                    :checked="selectedProjectIds.includes(project.id)"
                    @change="toggleProjectRow(project.id)"
                  />
                </td>
                <td class="bb-light px-3 py-4">
                  <div class="d-flex align-items-center">
                    <div class="project-avatar-32 me-3">{{ projectInitials(project.name) }}</div>
                    <div>
                      <div class="weight-500 gray mb-1">{{ project.name }}</div>
                      <div class="text-11 gray56">ID: {{ shortId(project.id) }}</div>
                    </div>
                  </div>
                </td>
                <td class="bb-light px-3 py-4">
                  <div class="d-flex align-items-center gap-2">
                    <img v-if="hasPlatform(project, 'YANDEX')" width="20" src="/admirra/img/icons/yandex-direct.png" alt="Yandex" />
                    <img v-if="hasPlatform(project, 'VK')" width="20" src="/admirra/img/icons/vk-ads.png" alt="VK" />
                    <span v-if="!project.integrations?.length" class="text-13 gray56">—</span>
                  </div>
                </td>
                <td class="bb-light px-3 py-4">{{ formatNumber(getProjectMetric(project.id).impressions) }}</td>
                <td class="bb-light px-3 py-4">{{ formatNumber(getProjectMetric(project.id).clicks) }}</td>
                <td class="bb-light px-3 py-4">{{ formatMoney(getProjectMetric(project.id).expenses) }}</td>
                <td class="bb-light px-3 py-4">{{ formatNumber(getProjectMetric(project.id).leads) }}</td>
                <td class="bb-light px-3 py-4">{{ formatMoney(getProjectMetric(project.id).cpc) }}</td>
                <td class="bb-light px-3 py-4">{{ formatMoney(getProjectMetric(project.id).cpa) }}</td>
                <td class="bb-light px-3 py-4">
                  <span :class="['status-pill', project.integrations?.some(i => i.is_active) ? '_active' : '_inactive']">
                    {{ project.integrations?.some(i => i.is_active) ? 'Активен' : 'Неактивен' }}
                  </span>
                </td>
                <td class="bb-light px-3 py-4">
                  <button class="btn _sm _white" @click="openProject(project)">
                    <div class="btn__inner px-3"><span class="btn__text text-13">Открыть</span></div>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Массовое редактирование -->
      <div
        v-if="massEditOpen"
        class="modal-overlay"
        style="position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;display:flex;align-items:center;justify-content:center;padding:1rem"
        @click.self="massEditOpen = false"
      >
        <div class="radius-base p-5 mass-edit-modal projects-modal-panel" style="max-width:480px;width:100%">
          <h4 class="heading-4 mb-2">Массовое редактирование</h4>
          <p class="text-14 gray56 mb-3">Выбрано проектов: {{ selectedProjectIds.length }}. Укажите новое описание — оно будет записано во все отмеченные проекты.</p>
          <ul class="text-13 gray56 mb-3 ps-3 mass-edit-names">
            <li v-for="id in selectedProjectIdList" :key="id">{{ projectNameById(id) }}</li>
          </ul>
          <textarea
            v-model="massEditDescription"
            class="input w-100 mb-4"
            rows="4"
            placeholder="Описание проекта (необязательно оставить пустым — тогда только список)"
            style="min-height:6rem;resize:vertical"
          />
          <div class="d-flex gap-3 flex-wrap">
            <button class="btn _primary" type="button" :disabled="massSaving" @click="applyMassDescription">
              <div class="btn__inner"><span class="btn__text">{{ massSaving ? 'Сохранение...' : 'Применить описание' }}</span></div>
            </button>
            <button class="btn _white" type="button" :disabled="massSaving" @click="massEditOpen = false">
              <div class="btn__inner"><span class="btn__text gray">Закрыть</span></div>
            </button>
          </div>
        </div>
      </div>

      <!-- Диалог подтверждения удаления -->
      <div
        v-if="deleteTarget"
        class="modal-overlay"
        style="position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;display:flex;align-items:center;justify-content:center"
      >
        <div class="delete-modal radius-base p-5 projects-modal-panel" style="max-width:400px;width:90%">
          <h4 class="heading-4 mb-3">Удалить проект?</h4>
          <p class="text-14 gray56 mb-4">Проект «{{ deleteTarget.name }}» и все его данные будут удалены безвозвратно.</p>
          <div class="d-flex gap-3">
            <button class="btn _primary" :disabled="deleting" @click="doDelete">
              <div class="btn__inner"><span class="btn__text">{{ deleting ? 'Удаление...' : 'Удалить' }}</span></div>
            </button>
            <button class="btn _white" @click="deleteTarget = null">
              <div class="btn__inner"><span class="btn__text gray">Отмена</span></div>
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import { useTheme } from '../../composables/useTheme'
import { useToaster } from '../../composables/useToaster'

const router = useRouter()
const { projects, isLoading, fetchProjects, setCurrentProject } = useProjects()
const { isDarkMode } = useTheme()
const toaster = useToaster()

const viewType = ref('grid')
const periodDays = ref(14)
const search = ref('')
const deleting = ref(false)
const deleteTarget = ref(null)
const metricsByProjectId = ref({})
const selectedProjectIds = ref([])
const massEditOpen = ref(false)
const massEditDescription = ref('')
const massSaving = ref(false)

const searchInputStyle = computed(() => isDarkMode.value
  ? 'background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.16); color:#fff'
  : '')

const filteredProjects = computed(() => {
  if (!search.value.trim()) return projects.value
  const q = search.value.toLowerCase()
  return projects.value.filter(p =>
    p.name?.toLowerCase().includes(q) ||
    String(p.id || '').toLowerCase().includes(q)
  )
})

const allRowsSelected = computed(() => {
  const list = filteredProjects.value
  if (!list.length) return false
  return list.every((p) => selectedProjectIds.value.includes(p.id))
})

const selectedProjectIdList = computed(() => [...selectedProjectIds.value])

const projectNameById = (id) => projects.value.find((p) => p.id === id)?.name || String(id)

const toggleProjectRow = (id) => {
  const idx = selectedProjectIds.value.indexOf(id)
  if (idx > -1) selectedProjectIds.value.splice(idx, 1)
  else selectedProjectIds.value.push(id)
}

const toggleSelectAllRows = () => {
  const ids = filteredProjects.value.map((p) => p.id)
  if (allRowsSelected.value) {
    selectedProjectIds.value = selectedProjectIds.value.filter((id) => !ids.includes(id))
  } else {
    const set = new Set([...selectedProjectIds.value, ...ids])
    selectedProjectIds.value = Array.from(set)
  }
}

const openMassEdit = () => {
  if (viewType.value !== 'rows') {
    toaster.warning('Переключитесь в табличный режим и отметьте проекты галочками.')
    return
  }
  if (!selectedProjectIds.value.length) {
    toaster.warning('Отметьте один или несколько проектов в таблице.')
    return
  }
  massEditDescription.value = ''
  massEditOpen.value = true
}

const applyMassDescription = async () => {
  if (!selectedProjectIds.value.length) return
  const desc = massEditDescription.value.trim()
  if (!desc) {
    toaster.warning('Введите текст описания — он будет записан во все выбранные проекты.')
    return
  }
  massSaving.value = true
  try {
    await Promise.all(
      selectedProjectIds.value.map((id) =>
        api.put(`clients/${id}`, { description: desc })
      )
    )
    toaster.success(`Описание обновлено для ${selectedProjectIds.value.length} проектов.`)
    massEditOpen.value = false
    await fetchProjects()
    await loadProjectMetrics()
  } catch (err) {
    console.error(err)
    toaster.error(err.response?.data?.detail || 'Не удалось сохранить изменения.')
  } finally {
    massSaving.value = false
  }
}

watch(viewType, (v) => {
  if (v !== 'rows') selectedProjectIds.value = []
})

const emptyMetric = () => ({
  expenses: 0,
  impressions: 0,
  clicks: 0,
  leads: 0,
  cpc: 0,
  cpa: 0,
  balance: 0,
  trends: null
})

const getProjectMetric = (projectId) => metricsByProjectId.value[projectId] || emptyMetric()

const integrationPlatforms = (project) => {
  const list = (project.integrations || []).map(i => i.platform?.toUpperCase()).filter(Boolean)
  return Array.from(new Set(list))
}

const hasPlatform = (project, platform) => integrationPlatforms(project).includes(platform)

const formatNumber = (num) => new Intl.NumberFormat('ru-RU').format(Number(num || 0))
const formatMoney = (num) => `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(num || 0))} ₽`

const trendText = (metric, key) => {
  const trend = Number(metric?.trends?.[key] || 0)
  const sign = trend >= 0 ? '+' : ''
  return `${sign}${trend.toFixed(1)}%`
}

const getProjectStats = (project) => {
  const m = getProjectMetric(project.id)
  return [
    { label: 'Показы', subtitle: 'По всем каналам', value: formatNumber(m.impressions), change: trendText(m, 'impressions'), icon: '/admirra/img/svg/sprite.svg#diagrama' },
    { label: 'Клики', subtitle: 'Все переходы', value: formatNumber(m.clicks), change: trendText(m, 'clicks'), icon: '/admirra/img/svg/sprite.svg#cursore' },
    { label: 'CPC', subtitle: 'Стоимость клика', value: formatMoney(m.cpc), change: trendText(m, 'cpc'), icon: '/admirra/img/svg/sprite.svg#world' },
    { label: 'Расходы', subtitle: 'За период', value: formatMoney(m.expenses), change: trendText(m, 'expenses'), icon: '/admirra/img/svg/sprite.svg#wallet' },
    { label: 'Лиды', subtitle: 'По всем каналам', value: `${formatNumber(m.leads)} шт`, change: trendText(m, 'leads'), icon: '/admirra/img/svg/sprite.svg#group' },
    { label: 'CPA', subtitle: 'Стоимость лида', value: formatMoney(m.cpa), change: trendText(m, 'cpa'), icon: '/admirra/img/svg/sprite.svg#star' }
  ]
}

const projectInitials = (name) => (name ? name.trim().slice(0, 2).toUpperCase() : '?')
const shortId = (id) => {
  const v = String(id || '')
  return v.length > 12 ? `${v.slice(0, 8)}...${v.slice(-4)}` : v || '—'
}

const loadProjectMetrics = async () => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - Number(periodDays.value || 14))
  const startDate = start.toISOString().slice(0, 10)
  const endDate = end.toISOString().slice(0, 10)

  const entries = await Promise.all(
    projects.value.map(async (project) => {
      try {
        const { data } = await api.get('dashboard/summary', {
          params: {
            client_id: project.id,
            platform: 'all',
            start_date: startDate,
            end_date: endDate
          }
        })
        return [project.id, data || emptyMetric()]
      } catch {
        return [project.id, emptyMetric()]
      }
    })
  )

  metricsByProjectId.value = Object.fromEntries(entries)
}

const reloadMetrics = async () => {
  await loadProjectMetrics()
}

const openProject = (project) => {
  setCurrentProject(project.id)
  router.push('/dashboard/general-3')
}

const doDelete = async () => {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.delete(`clients/${deleteTarget.value.id}`)
    deleteTarget.value = null
    await fetchProjects()
    await loadProjectMetrics()
  } catch (err) {
    console.error('Delete project error:', err)
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  await fetchProjects()
  await loadProjectMetrics()
})
</script>

<style scoped>
.projects-filters-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.projects-filters-period {
  flex: 0 0 auto;
}

.projects-filters-search {
  flex: 1 1 220px;
  min-width: 0;
}

.projects-filters-search :deep(.input._search-project) {
  width: 100%;
  max-width: 35.4rem;
}

.projects-period-select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  display: block;
  min-width: 11.5rem;
  height: 4.4rem;
  padding: 0 2.5rem 0 1.4rem;
  margin: 0;
  border-radius: 1.2rem;
  border: 1px solid rgba(44, 44, 44, 0.12);
  background-color: #fff;
  color: #2c2c2c;
  font-size: 1.4rem;
  font-weight: 500;
  line-height: 1;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
  background-image:
    linear-gradient(45deg, transparent 50%, #7c8597 50%),
    linear-gradient(135deg, #7c8597 50%, transparent 50%);
  background-position:
    calc(100% - 1.6rem) calc(50% - 0.15rem),
    calc(100% - 1.1rem) calc(50% - 0.15rem);
  background-size: 0.5rem 0.5rem, 0.5rem 0.5rem;
  background-repeat: no-repeat;
}

.projects-period-select:hover {
  border-color: rgba(46, 107, 255, 0.35);
}

.projects-period-select:focus {
  border-color: #2e6bff;
  box-shadow: 0 0 0 3px rgba(46, 107, 255, 0.15);
}

.projects-period-select option {
  color: #2c2c2c;
  background: #fff;
}

.projects-period-select.is-dark-input {
  background-color: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.16);
  color: #fff;
  background-image:
    linear-gradient(45deg, transparent 50%, rgba(255, 255, 255, 0.5) 50%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.5) 50%, transparent 50%);
  background-position:
    calc(100% - 1.6rem) calc(50% - 0.15rem),
    calc(100% - 1.1rem) calc(50% - 0.15rem);
  background-size: 0.5rem 0.5rem, 0.5rem 0.5rem;
  background-repeat: no-repeat;
}

.projects-period-select.is-dark-input:hover {
  border-color: rgba(46, 107, 255, 0.45);
}

.projects-period-select.is-dark-input:focus {
  border-color: #6b9aff;
  box-shadow: 0 0 0 3px rgba(46, 107, 255, 0.2);
}

.project-avatar-40,
.project-avatar-32 {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #e8eef9;
  color: #4b6fa0;
  font-weight: 700;
}

.project-avatar-40 { width: 40px; height: 40px; font-size: 12px; }
.project-avatar-32 { width: 32px; height: 32px; font-size: 11px; }

.projects-grid-card {
  background: #fff;
  border: 1px solid transparent;
}

.projects-table-shell {
  background: #fff;
  border: 1px solid rgba(44, 44, 44, 0.06);
}

.projects-modal-panel {
  background: #fff;
}

.projects-rows-wrap { overflow: hidden; }
.projects-rows-table { width: 100%; min-width: 1080px; border-collapse: collapse; }
.projects-rows-table th { font-size: 12px; font-weight: 600; }
.projects-rows-table td { font-size: 13px; }

.status-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}
.status-pill._active { background: #eaf9ef; color: #16a34a; }
.status-pill._inactive { background: #fef2f2; color: #dc2626; }

:global(html.darkmode) .delete-modal,
:global(body.darkmode) .delete-modal,
:global(html.dark) .delete-modal,
:global(body.dark) .delete-modal {
  background: rgba(35, 37, 48, 0.96) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e8eaed;
}

:global(html.darkmode) .delete-modal .heading-4,
:global(body.darkmode) .delete-modal .heading-4 {
  color: #f1f5f9 !important;
}

:global(html.darkmode) .delete-modal .gray56,
:global(body.darkmode) .delete-modal .gray56 {
  color: #94a3b8 !important;
}

:global(html.darkmode) .projects-rows-wrap,
:global(body.darkmode) .projects-rows-wrap,
:global(html.dark) .projects-rows-wrap,
:global(body.dark) .projects-rows-wrap,
:global(html.darkmode) .projects-table-shell,
:global(body.darkmode) .projects-table-shell,
:global(html.dark) .projects-table-shell,
:global(body.dark) .projects-table-shell {
  background: rgba(35, 37, 48, 0.94) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

:global(html.darkmode) .projects-rows-table th,
:global(html.darkmode) .projects-rows-table td,
:global(body.darkmode) .projects-rows-table th,
:global(body.darkmode) .projects-rows-table td {
  color: #e8eaed;
}

:global(html.darkmode) .projects-rows-table .bb-light,
:global(body.darkmode) .projects-rows-table .bb-light {
  border-color: rgba(255, 255, 255, 0.1) !important;
}

:global(html.darkmode) .is-dark-input::placeholder,
:global(body.darkmode) .is-dark-input::placeholder,
:global(html.dark) .is-dark-input::placeholder,
:global(body.dark) .is-dark-input::placeholder {
  color: rgba(255, 255, 255, 0.5) !important;
}

/* Тёмная тема: карточки сетки и таблица */
.projects-page--dark :deep(.heading-3) {
  color: #f1f5f9 !important;
}

.projects-page--dark .py-5.text-center.gray56,
.projects-page--dark .text-center.gray56 {
  color: #94a3b8 !important;
}

.projects-page--dark .projects-grid-card {
  background: rgba(35, 37, 48, 0.94) !important;
  border-color: rgba(255, 255, 255, 0.1);
}

.projects-page--dark .project-card-title,
.projects-page--dark .metric-label {
  color: #f1f5f9 !important;
}

.projects-page--dark .project-card-desc,
.projects-page--dark .metric-sub {
  color: #94a3b8 !important;
}

.projects-page--dark .metric-value {
  color: #f8fafc !important;
}

.metric-value {
  white-space: nowrap;
}

.projects-page--dark .projects-metric-tile {
  background: rgba(46, 107, 255, 0.14) !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.projects-page--dark .projects-metric-tile :deep(.iconbox) {
  background: rgba(255, 255, 255, 0.08);
}

.projects-page--dark .projects-metric-tile :deep(.iconbox svg) {
  fill: #93c5fd;
}

.projects-page--dark .projects-metric-tile :deep(.badge._success) {
  background: rgba(34, 197, 94, 0.22);
  color: #86efac;
}

.projects-page--dark .projects-metric-tile :deep(.badge__icon) {
  fill: currentColor;
}

.projects-page--dark .projects-card-hr {
  border: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  opacity: 1;
}

.projects-page--dark .balance-section-title {
  color: #cbd5e1 !important;
}

.projects-page--dark .bg-orangelight {
  background: rgba(255, 140, 66, 0.14) !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.projects-page--dark .bg-oceanlight {
  background: rgba(59, 130, 246, 0.16) !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.projects-page--dark .bg-azurelight {
  background: rgba(46, 107, 255, 0.12) !important;
}

.projects-page--dark .c71663e,
.projects-page--dark .c5385C1 {
  color: #e2e8f0 !important;
}

.projects-page--dark .badge-white {
  background: rgba(255, 255, 255, 0.12) !important;
  color: #f8fafc !important;
  border: 1px solid rgba(255, 255, 255, 0.14);
}

.projects-page--dark .gray56 {
  color: #94a3b8 !important;
}

.projects-page--dark .project-card-open.circle-btn {
  border-color: rgba(255, 255, 255, 0.22);
}

.projects-page--dark .project-card-open.circle-btn svg {
  fill: #cbd5e1;
}

.projects-page--dark .project-avatar-40,
.projects-page--dark .project-avatar-32 {
  background: rgba(46, 107, 255, 0.25);
  color: #bfdbfe;
}

.projects-page--dark .projects-table-shell {
  background: rgba(35, 37, 48, 0.94) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.projects-page--dark .projects-rows-table th,
.projects-page--dark .projects-rows-table td {
  color: #e8eaed;
}

.projects-page--dark .projects-rows-table .gray,
.projects-page--dark .projects-rows-table .weight-500.gray {
  color: #f1f5f9 !important;
}

.projects-page--dark .bb-light {
  border-color: rgba(255, 255, 255, 0.1) !important;
}

.projects-page--dark .projects-rows-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.04);
}

.projects-page--dark .projects-rows-table :deep(.btn._white) {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.projects-page--dark .projects-rows-table :deep(.btn._white .btn__text) {
  color: #e8eaed !important;
}

:global(html.darkmode) .projects-rows-table .btn._white,
:global(body.darkmode) .projects-rows-table .btn._white {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.18);
}

:global(html.darkmode) .projects-rows-table .btn._white .btn__text,
:global(body.darkmode) .projects-rows-table .btn._white .btn__text {
  color: #e8eaed !important;
}

.projects-page--dark .status-pill._active {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.projects-page--dark .status-pill._inactive {
  background: rgba(248, 113, 113, 0.16);
  color: #fca5a5;
}

.projects-page--dark :deep(.btn-ico) {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.06);
}

.projects-page--dark :deep(.btn-ico._active) {
  background: rgba(46, 107, 255, 0.35);
  border-color: rgba(46, 107, 255, 0.5);
}

.projects-page--dark :deep(.btn-ico svg) {
  stroke: #e2e8f0;
}

.projects-page--dark .projects-filters-search :deep(.input-icon) {
  background: rgba(255, 255, 255, 0.1);
}

.projects-page--dark .projects-filters-search :deep(.input-icon svg._stroke) {
  stroke: #94a3b8;
}

.projects-page--dark .projects-modal-panel {
  background: rgba(35, 37, 48, 0.98) !important;
  color: #e8eaed;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.projects-page--dark .projects-modal-panel .heading-4 {
  color: #f1f5f9 !important;
}

.projects-page--dark .projects-modal-panel .gray56 {
  color: #94a3b8 !important;
}

.projects-page--dark .projects-modal-panel textarea.input {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.16);
  color: #f8fafc;
}

.projects-page--dark .projects-modal-panel textarea.input::placeholder {
  color: rgba(255, 255, 255, 0.45);
}

/* Таблица: глобальные классы тёмной темы (если isDarkMode синхронен с html) */
:global(html.darkmode) .projects-grid-card,
:global(body.darkmode) .projects-grid-card,
:global(html.dark) .projects-grid-card,
:global(body.dark) .projects-grid-card {
  background: rgba(35, 37, 48, 0.94) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

:global(html.darkmode) .projects-grid-card .gray,
:global(body.darkmode) .projects-grid-card .gray {
  color: #e8eaed !important;
}

:global(html.darkmode) .projects-grid-card .gray56,
:global(body.darkmode) .projects-grid-card .gray56 {
  color: #94a3b8 !important;
}

:global(html.darkmode) .projects-metric-tile,
:global(body.darkmode) .projects-metric-tile {
  background: rgba(46, 107, 255, 0.14) !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

:global(html.darkmode) .projects-metric-tile b.text-20,
:global(body.darkmode) .projects-metric-tile b.text-20 {
  color: #f8fafc !important;
}
</style>
