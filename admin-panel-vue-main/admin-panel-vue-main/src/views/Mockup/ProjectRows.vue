<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="py-4 mb-3">
        <h3 class="heading-3">Проекты</h3>
      </div>

      <div class="row gy-3 mb-5">
        <div class="col-12 col-md">
          <div class="row gy-3">
            <div class="col-auto">
              <select class="wide" v-model="periodDays" @change="reloadMetrics">
                <option :value="14">2 недели</option>
                <option :value="30">30 дней</option>
                <option :value="90">90 дней</option>
              </select>
            </div>
            <div class="col-12 col-sm-auto">
              <div class="input-item">
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
        </div>
        <div class="col-12 col-md-auto">
          <div class="row g-3">
            <div class="col-auto">
              <button class="btn _primary">
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
          <div class="h-100 bg-white radius-base">
            <div class="p-5">
              <div class="row pb-3 mb-4">
                <div class="col">
                  <div class="d-flex">
                    <div class="avatar-40x40 align-self-center">
                      <div class="project-avatar-40">{{ projectInitials(project.name) }}</div>
                    </div>
                    <div class="ps-4 align-self-center">
                      <h4 class="mb-1 text-15 gray">{{ project.name }}</h4>
                      <p class="gray56">{{ project.description || 'Описание проекта краткое' }}</p>
                    </div>
                  </div>
                </div>
                <div class="col-auto">
                  <button class="circle-btn" @click="openProject(project)">
                    <svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
                  </button>
                </div>
              </div>

              <div class="row g-4">
                <div v-for="(stat, idx) in getProjectStats(project)" :key="idx" class="col-12 col-sm-6 col-md-4">
                  <div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
                    <div class="d-flex pb-2 mb-4">
                      <div class="iconbox">
                        <svg><use :href="stat.icon"></use></svg>
                      </div>
                      <div class="ps-3 align-self-center">
                        <h4 class="mb-1 gray">{{ stat.label }}</h4>
                        <p class="text-12 gray56">{{ stat.subtitle }}</p>
                      </div>
                    </div>
                    <div class="d-flex align-items-center mt-auto">
                      <b class="text-20 me-3">{{ stat.value }}</b>
                      <div class="badge _success">
                        <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                        {{ stat.change }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <hr class="hr-line" />
            <div class="p-5">
              <div class="gray mb-3">Актуальный баланс в ЛК:</div>
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
      <div v-else class="projects-rows-wrap bg-white radius-base py-4 mb-5">
        <div class="table-container">
          <table class="projects-rows-table">
            <thead>
              <tr class="gray56">
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

      <!-- Диалог подтверждения удаления -->
      <div
        v-if="deleteTarget"
        class="modal-overlay"
        style="position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;display:flex;align-items:center;justify-content:center"
      >
        <div class="delete-modal bg-white radius-base p-5" style="max-width:400px;width:90%">
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import { useTheme } from '../../composables/useTheme'

const router = useRouter()
const { projects, isLoading, fetchProjects, setCurrentProject } = useProjects()
const { isDarkMode } = useTheme()

const viewType = ref('grid')
const periodDays = ref(14)
const search = ref('')
const deleting = ref(false)
const deleteTarget = ref(null)
const metricsByProjectId = ref({})

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
}

:global(html.darkmode) .projects-rows-wrap,
:global(body.darkmode) .projects-rows-wrap,
:global(html.dark) .projects-rows-wrap,
:global(body.dark) .projects-rows-wrap {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

:global(html.darkmode) .is-dark-input::placeholder,
:global(body.darkmode) .is-dark-input::placeholder,
:global(html.dark) .is-dark-input::placeholder,
:global(body.dark) .is-dark-input::placeholder {
  color: rgba(255, 255, 255, 0.5) !important;
}
</style>
