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
  									<select>
  										<option>Все</option>
  										<option value="1">Some option</option>
  										<option value="2">Another option</option>
  										<option value="3" disabled>A disabled option</option>
  										<option value="4">Potato option</option>
  									</select>
  								</div>
  								<div class="col-auto">
  									<select>
  										<option>2 недели</option>
  										<option value="1">3 недели</option>
  										<option value="2">4 недели</option>
  										<option value="3">5 недель</option>
  									</select>
  								</div>
  								<div class="col-12 col-sm-auto">
  									<div class="input-item">
  										<input class="input _search-project" type="text" placeholder="Поиск по проектам, номерам или доменам" />
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
  											<div class="btn__icon">
  												<svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#edit"></use></svg>
  											</div>
  										</div>
  									</button>
  								</div>
  								<div class="col-auto ms-auto">
  									<div class="row">
  										<div class="col-auto">
  											<button class="btn-ico">
  												<svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#grid"></use></svg>
  											</button>
  										</div>
  										<div class="col-auto">
  											<button class="btn-ico _active">
  												<svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#rows"></use></svg>
  											</button>
  										</div>
  									</div>
  								</div>
  							</div>
  						</div>
  					</div>
  					<div class="bg-white radius-base py-5 mb-5">
  						<div class="table-container">
  							<table>
  								<thead>
  									<tr class="gray56">
  										<th class="bb-light px-3 pb-3">
  											<div class="ps-4">
  												<label class="choise-checkbox">
  													<input class="choise-checkbox__input" type="checkbox" />
  													<span class="choise-checkbox__box">
  														<svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
  													</span>
  												</label>
  											</div>
  										</th>
  										<th class="bb-light px-3 pb-3">Проект</th>
  										<th class="bb-light px-3 pb-3">Интеграции</th>
  										<th class="bb-light px-3 pb-3">Показы</th>
  										<th class="bb-light px-3 pb-3">Клики</th>
  										<th class="bb-light px-3 pb-3">Расходы</th>
  										<th class="bb-light px-3 pb-3">Лиды</th>
  										<th class="bb-light px-3 pb-3">CPC</th>
  										<th class="bb-light px-3 pb-3">CPA</th>
  										<th class="bb-light px-3 pb-3">Актуальный баланс&nbsp;в&nbsp;ЛК:</th>
  										<th class="bb-light px-3 pb-3">Статус</th>
  										<th class="bb-light px-3 pb-3">Дата&nbsp;создания</th>
  										<th class="bb-light px-3 pb-3">Действия</th>
  									</tr>
  								</thead>
  								<tbody>
  									<tr v-for="project in projects" :key="project.id">
  										<td class="bb-light px-3 py-5">
  											<div class="ps-4">
  												<label class="choise-checkbox">
  													<input class="choise-checkbox__input" type="checkbox" />
  													<span class="choise-checkbox__box">
  														<svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
  													</span>
  												</label>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="d-flex">
  												<div class="avatar-30x30 align-self-center">
  													<img class="img-cover" src="/admirra/img/avatars/avatar-40x40.png" alt="#" />
  												</div>
  												<div class="ps-4 align-self-center">
  													<h4 class="mb-1 gray">{{ project.title }}</h4>
  													<p class="text-11 gray56">ID:&nbsp;{{ project.id }}</p>
  												</div>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="d-flex">
  												<img v-if="project.channels.includes('YANDEX_DIRECT')" class="me-2" width="22" src="/admirra/img/icons/yandex-direct.png" alt="Yandex" />
  												<img v-if="project.channels.includes('VK_ADS')" class="me-2" width="22" src="/admirra/img/icons/vk-ads.png" alt="VK" />
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2">{{ project.impressions }}</div>
  											<div class="badge _sm _success" v-if="project.trend > 0">
  												<span class="weight-600">+{{ Number(project.trend).toFixed(1) }}%</span>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2">{{ project.clicks }}</div>
  											<div class="badge _sm _success" v-if="project.trend > 0">
  												<span class="weight-600">+{{ Number(project.trend).toFixed(1) }}%</span>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2"><b>{{ Number(project.expenses).toLocaleString() }}&nbsp;₽</b></div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2">{{ project.leads }}</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2">{{ Number(project.cpc).toFixed(2) }}</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2">{{ Number(project.cpa).toFixed(2) }}</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="h-100 bg-orangelight radius p-3">
  												<div class="h-100 d-flex align-items-center justify-content-center">
  													<div class="px-3 c71663e">Баланс</div>
  													<div class="badge-white c71663e">{{ project.budgetRemaining }}₽</div>
  												</div>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="badge _success">
  												<span class="weight-600">{{ project.status }}</span>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15">{{ project.createdAt }}</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="dropdown">
  												<button class="dropdown-head _no-style">
  													<div class="action-btn-ui">
  														<svg><use href="/admirra/img/svg/sprite.svg#dotts"></use></svg>
  													</div>
  												</button>
  												<div class="dropdown-body _action _right">
  													<div class="dropdown-block">
  														<div class="py-3">
  															<router-link :to="'/project-card?id=' + project.id" class="dropdown-menu-item">
  																<div class="dropdown-menu-item__icon">
  																	<svg class="_sm"><use href="/admirra/img/svg/sprite.svg#eye"></use></svg>
  																</div>
  																<span class="pe-3">Просмотр</span>
  															</router-link>
  															<button class="dropdown-menu-item">
  																<div class="dropdown-menu-item__icon">
  																	<svg class="_stroke _lg"><use href="/admirra/img/svg/sprite.svg#pen"></use></svg>
  																</div>
  																<span class="pe-3">Редактировать</span>
  															</button>
  															<button @click.prevent="deleteProject(project.id)" class="dropdown-menu-item _danger">
  																<div class="dropdown-menu-item__icon">
  																	<svg><use href="/admirra/img/svg/sprite.svg#delete"></use></svg>
  																</div>
  																<span class="pe-3">Удалить</span>
  															</button>
  														</div>
  													</div>
  												</div>
  											</div>
  										</td>
  									</tr>
  									<tr>
  										<td class="bb-light px-3 py-5">
  											<div class="ps-4">
  												<label class="choise-checkbox">
  													<input class="choise-checkbox__input" type="checkbox" checked />
  													<span class="choise-checkbox__box">
  														<svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
  													</span>
  												</label>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="d-flex">
  												<div class="avatar-30x30 align-self-center">
  													<img class="img-cover" src="/admirra/img/avatars/avatar-40x40.png" alt="#" />
  												</div>
  												<div class="ps-4 align-self-center">
  													<h4 class="mb-1 gray">Дейтелинг Иркутск</h4>
  													<p class="text-11 gray56">ID:&nbsp;098409843080980</p>
  												</div>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="d-flex">
  												<img class="me-2" width="22" src="/admirra/img/icons/yandex-direct.png" alt="#" />
  												<img class="me-2" width="22" src="/admirra/img/icons/vk-ads.png" alt="#" />
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2">1205</div>
  											<div class="badge _sm _success">
  												<span class="weight-600">+15.6%</span>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2">1205</div>
  											<div class="badge _sm _success">
  												<span class="weight-600">+15.6%</span>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2"><b>90,190&nbsp;₽</b></div>
  											<div class="badge _sm _success">
  												<span class="weight-600">+15.6%</span>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2">67</div>
  											<div class="badge _sm _success">
  												<span class="weight-600">+15.6%</span>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2">67</div>
  											<div class="badge _sm _success">
  												<span class="weight-600">+15.6%</span>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15 mb-2">67</div>
  											<div class="badge _sm _success">
  												<span class="weight-600">+15.6%</span>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="h-100 bg-orangelight radius p-3">
  												<div class="h-100 d-flex align-items-center justify-content-center">
  													<img width="18" src="/admirra/img/icons/yandex-direct.png" alt="yandex direct" />
  													<div class="px-3 c71663e">Yandex&nbsp;Direct</div>
  													<div class="badge-white c71663e">10&nbsp;200₽</div>
  												</div>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="badge _success">
  												<span class="weight-600">Активен</span>
  											</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="text-15">09.03.2026</div>
  										</td>
  										<td class="bb-light px-3 py-5">
  											<div class="dropdown">
  												<button class="dropdown-head _no-style">
  													<div class="action-btn-ui">
  														<svg><use href="/admirra/img/svg/sprite.svg#dotts"></use></svg>
  													</div>
  												</button>
  												<div class="dropdown-body _action _right">
  													<div class="dropdown-block">
  														<div class="py-3">
  															<router-link to="/project-card" class="dropdown-menu-item">
  																<div class="dropdown-menu-item__icon">
  																	<svg class="_sm"><use href="/admirra/img/svg/sprite.svg#eye"></use></svg>
  																</div>
  																<span class="pe-3">Просмотр</span>
  															</router-link>
  															<button class="dropdown-menu-item">
  																<div class="dropdown-menu-item__icon">
  																	<svg class="_stroke _lg"><use href="/admirra/img/svg/sprite.svg#pen"></use></svg>
  																</div>
  																<span class="pe-3">Редактировать</span>
  															</button>
  															<button class="dropdown-menu-item _danger">
  																<div class="dropdown-menu-item__icon">
  																	<svg><use href="/admirra/img/svg/sprite.svg#delete"></use></svg>
  																</div>
  																<span class="pe-3">Удалить</span>
  															</button>
  														</div>
  													</div>
  												</div>
  											</div>
  										</td>
  									</tr>
  								</tbody>
  							</table>
  						</div>
  						<div class="row pt-5 px-5 align-items-end">
  							<div class="col col-sm-4">
  								<div class="row gy-2 align-items-center">
  									<div class="col-12">
  										<div class="gray weight-500">Элементов на&nbsp;странице:</div>
  									</div>
  									<div class="col-auto">
  										<select class="select-outline wide _sm _dropdown-bottom">
  											<option>10</option>
  											<option value="1">20</option>
  											<option value="2">30</option>
  										</select>
  									</div>
  								</div>
  							</div>
  							<div class="col-12 col-sm-4 order-1 order-sm-0">
  								<div class="py-4 gray weight-500 text-center">1-3 из 3</div>
  							</div>
  							<div class="col-auto col-sm-4 d-flex">
  								<div class="ms-auto">
  									<a class="btn-nav" href="#">
  										<svg><use href="/admirra/img/svg/sprite.svg#prev"></use></svg>
  									</a>
  									<span>&nbsp;</span>
  									<a class="btn-nav" href="#">
  										<svg><use href="/admirra/img/svg/sprite.svg#next"></use></svg>
  									</a>
  								</div>
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