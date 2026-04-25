<template>
  <div>
    <div v-if="isLoading" class="admirra-page-wrapper">
      <section class="main-section">
        <div class="py-5 text-center gray56">Загрузка проектов...</div>
      </section>
    </div>

    <div v-else-if="projects.length === 0" class="admirra-page-wrapper">
      <section class="main-section">
        <div class="py-4 mb-3">
          <h3 class="heading-3">Проекты</h3>
        </div>
        <div class="py-5 text-center gray56">У вас пока нет проектов</div>
      </section>
    </div>

    <ProjectCard
      v-else-if="viewType === 'grid'"
      :title="'Проекты'"
      :view-type="viewType"
      :projects="gridProjects"
      :filters="filters"
      @search="search = $event"
      @change-view="viewType = $event"
      @open-project="openProject"
      @bulk-edit="noop"
    />

    <div v-else class="admirra-page-wrapper">
      <section class="main-section">
        <div class="py-4 mb-3">
          <h3 class="heading-3">Проекты</h3>
        </div>
        <ProjectsTable
          :projects="tableProjects"
          :loading="isLoading"
          :search-query="search"
          @viewProject="openProjectById"
          @editProject="openProjectById"
          @deleteProject="confirmDeleteById"
        />
      </section>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import ProjectCard from './ProjectCard.vue'
import ProjectsTable from '../Project/components/ProjectsTable.vue'

const router = useRouter()
const { projects, isLoading, fetchProjects, setCurrentProject } = useProjects()

const viewType = ref('grid')
const search = ref('')
const deleting = ref(false)
const deleteTarget = ref(null)

const filters = computed(() => [
  {
    id: 'scope',
    options: [
      { value: 'all', label: 'Все' }
    ]
  },
  {
    id: 'period',
    options: [
      { value: '14', label: '2 недели' }
    ]
  }
])

onMounted(fetchProjects)

const filteredProjects = computed(() => {
  if (!search.value.trim()) return projects.value
  const q = search.value.toLowerCase()
  return projects.value.filter(p =>
    p.name?.toLowerCase().includes(q) ||
    String(p.id || '').toLowerCase().includes(q)
  )
})

const integrationPlatforms = (project) => {
  const list = (project.integrations || []).map(i => i.platform?.toUpperCase()).filter(Boolean)
  return Array.from(new Set(list))
}

const hasPlatform = (project, platform) => integrationPlatforms(project).includes(platform)

const formatMoney = (value) => {
  const n = Number(value || 0)
  return `${n.toLocaleString('ru-RU')} ₽`
}

const gridProjects = computed(() => {
  return filteredProjects.value.map((project) => {
    const integrationsCount = project.integrations?.length || 0
    const yandex = hasPlatform(project, 'YANDEX')
    const vk = hasPlatform(project, 'VK')

    return {
      id: project.id,
      name: project.name || 'Без названия',
      description: project.description || 'Описание проекта краткое',
      avatar: '/admirra/img/avatars/avatar-40x40.png',
      stats: [
        { label: 'Показы', subtitle: 'По всем каналам', value: '0', change: '+0%', icon: '/admirra/img/svg/sprite.svg#diagrama', badgeClass: '_success', badgeIcon: '/admirra/img/svg/sprite.svg#rating-up' },
        { label: 'Клики', subtitle: 'Все переходы', value: '0', change: '+0%', icon: '/admirra/img/svg/sprite.svg#cursore', badgeClass: '_success', badgeIcon: '/admirra/img/svg/sprite.svg#rating-up' },
        { label: 'CPC', subtitle: 'Стоимость клика', value: formatMoney(0), change: '+0%', icon: '/admirra/img/svg/sprite.svg#world', badgeClass: '_success', badgeIcon: '/admirra/img/svg/sprite.svg#rating-up' },
        { label: 'Расходы', subtitle: 'За период', value: formatMoney(0), change: '+0%', icon: '/admirra/img/svg/sprite.svg#wallet', badgeClass: '_success', badgeIcon: '/admirra/img/svg/sprite.svg#rating-up' },
        { label: 'Лиды', subtitle: 'По всем каналам', value: '0 шт', change: '+0%', icon: '/admirra/img/svg/sprite.svg#group', badgeClass: '_success', badgeIcon: '/admirra/img/svg/sprite.svg#rating-up' },
        { label: 'CPA', subtitle: 'Стоимость лида', value: formatMoney(0), change: '+0%', icon: '/admirra/img/svg/sprite.svg#star', badgeClass: '_success', badgeIcon: '/admirra/img/svg/sprite.svg#rating-up' }
      ],
      balances: [
        ...(yandex ? [{ name: 'Yandex Direct', value: `${integrationsCount} интегр.`, icon: '/admirra/img/icons/yandex-direct.png', bgClass: 'bg-orangelight', textClass: 'c71663e' }] : []),
        ...(vk ? [{ name: 'VK Ads Manager', value: `${integrationsCount} интегр.`, icon: '/admirra/img/icons/vk-ads.png', bgClass: 'bg-oceanlight', textClass: 'c5385C1' }] : [])
      ]
    }
  })
})

const tableProjects = computed(() => {
  return filteredProjects.value.map((project) => {
    const channels = []
    if (hasPlatform(project, 'YANDEX')) channels.push('Яндекс.Директ')
    if (hasPlatform(project, 'VK')) channels.push('ВКонтакте')
    const active = (project.integrations || []).some(i => i.is_active)

    return {
      id: String(project.id),
      title: project.name || 'Без названия',
      description: project.description || '',
      channels,
      impressions: 0,
      clicks: 0,
      expenses: 0,
      leads: 0,
      cpc: 0,
      cpa: 0,
      status: active ? 'active' : 'inactive',
      created_at: project.created_at
    }
  })
})

const openProject = (project) => {
  setCurrentProject(project.id)
  router.push('/dashboard/general-3')
}

const openProjectById = (projectId) => {
  const p = projects.value.find(x => String(x.id) === String(projectId))
  if (p) openProject(p)
}

const confirmDeleteById = (projectId) => {
  const p = projects.value.find(x => String(x.id) === String(projectId))
  if (p) deleteTarget.value = p
}

const doDelete = async () => {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.delete(`clients/${deleteTarget.value.id}`)
    deleteTarget.value = null
    await fetchProjects()
  } catch (err) {
    console.error('Delete project error:', err)
  } finally {
    deleting.value = false
  }
}

const noop = () => {}
</script>

<style scoped>
:global(html.darkmode) .delete-modal,
:global(body.darkmode) .delete-modal,
:global(html.dark) .delete-modal,
:global(body.dark) .delete-modal {
  background: rgba(35, 37, 48, 0.96) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
