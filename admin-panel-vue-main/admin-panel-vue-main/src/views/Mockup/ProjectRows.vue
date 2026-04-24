<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="py-4 mb-3">
        <h3 class="heading-3">Проекты</h3>
      </div>

      <div class="row gy-3 mb-5">
        <div class="col-12 col-md">
          <div class="row gy-3">
            <div class="col-12 col-sm-auto">
              <div class="input-item">
                <input
                  class="input _search-project"
                  :class="{ 'is-dark-input': isDarkMode }"
                  :style="searchInputStyle"
                  type="text"
                  placeholder="Поиск по проектам"
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
          <button class="btn _primary" @click="$router.push('/create')">
            <div class="btn__inner">
              <span class="btn__text">Новый проект</span>
              <div class="btn__icon-plus">+</div>
            </div>
          </button>
        </div>
      </div>

      <div v-if="isLoading" class="py-5 text-center gray56">Загрузка...</div>

      <div v-else-if="filteredProjects.length === 0" class="py-5 text-center gray56">
        {{ search ? 'Проекты не найдены' : 'У вас пока нет проектов' }}
      </div>

      <div v-else class="projects-table-wrap bg-white radius-base py-5 mb-5">
        <div class="table-container">
          <table>
            <thead>
              <tr class="gray56">
                <th class="bb-light px-3 pb-3">Проект</th>
                <th class="bb-light px-3 pb-3">Платформа</th>
                <th class="bb-light px-3 pb-3">Кол-во интеграций</th>
                <th class="bb-light px-3 pb-3">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="project in filteredProjects" :key="project.id">
                <td class="bb-light px-3 py-4">
                  <div class="d-flex align-items-center">
                    <div class="project-avatar avatar-30x30 me-3 align-self-center">
                      <span class="project-avatar-text">{{ projectInitials(project.name) }}</span>
                    </div>
                    <div>
                      <div class="weight-500 gray mb-1">{{ project.name }}</div>
                      <div class="text-11 gray56">ID: {{ project.id }}</div>
                    </div>
                  </div>
                </td>
                <td class="bb-light px-3 py-4">
                  <div class="d-flex align-items-center gap-2">
                    <img v-if="hasPlatform(project, 'YANDEX')" width="22" src="/admirra/img/icons/yandex-direct.png" alt="Yandex" title="Yandex Direct" />
                    <img v-if="hasPlatform(project, 'VK')" width="22" src="/admirra/img/icons/vk-ads.png" alt="VK" title="VK Ads" />
                    <span v-if="!project.integrations || project.integrations.length === 0" class="gray56 text-13">—</span>
                  </div>
                </td>
                <td class="bb-light px-3 py-4">
                  <div class="text-15">{{ project.integrations?.length || 0 }}</div>
                </td>
                <td class="bb-light px-3 py-4">
                  <div class="d-flex gap-2">
                    <button
                      class="btn _sm _white"
                      @click="openProject(project)"
                      title="Открыть аналитику"
                    >
                      <div class="btn__inner px-3">
                        <span class="btn__text text-13">Открыть</span>
                      </div>
                    </button>
                    <button
                      class="btn-action _danger"
                      @click="confirmDelete(project)"
                      title="Удалить"
                    >
                      <svg><use href="/admirra/img/svg/sprite.svg#basket"></use></svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Диалог подтверждения удаления -->
      <div v-if="deleteTarget" class="modal-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;display:flex;align-items:center;justify-content:center">
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

const search = ref('')
const deleteTarget = ref(null)
const deleting = ref(false)

const searchInputStyle = computed(() => isDarkMode.value
  ? 'background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.16); color:#fff'
  : '')

onMounted(fetchProjects)

const filteredProjects = computed(() => {
  if (!search.value.trim()) return projects.value
  const q = search.value.toLowerCase()
  return projects.value.filter(p => p.name?.toLowerCase().includes(q))
})

const projectInitials = (name) => {
  if (!name) return '?'
  return name.trim().slice(0, 2).toUpperCase()
}

const hasPlatform = (project, platform) => {
  return project.integrations?.some(i => i.platform?.toUpperCase() === platform)
}

const openProject = (project) => {
  setCurrentProject(project.id)
  router.push('/dashboard/general-3')
}

const confirmDelete = (project) => {
  deleteTarget.value = project
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
</script>

<style scoped>
.admirra-page-wrapper { }
.btn-nav { background: none; border: none; cursor: pointer; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }

.project-avatar {
  background: #e8eef9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.project-avatar-text {
  font-size: 12px;
  font-weight: 700;
  color: #4b6fa0;
}

:global(html.darkmode) .projects-table-wrap,
:global(body.darkmode) .projects-table-wrap,
:global(html.dark) .projects-table-wrap,
:global(body.dark) .projects-table-wrap {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

:global(html.darkmode) .projects-table-wrap .bb-light,
:global(body.darkmode) .projects-table-wrap .bb-light,
:global(html.dark) .projects-table-wrap .bb-light,
:global(body.dark) .projects-table-wrap .bb-light {
  border-color: rgba(255, 255, 255, 0.1) !important;
}

:global(html.darkmode) .projects-table-wrap .gray,
:global(body.darkmode) .projects-table-wrap .gray,
:global(html.dark) .projects-table-wrap .gray,
:global(body.dark) .projects-table-wrap .gray {
  color: rgba(255, 255, 255, 0.88) !important;
}

:global(html.darkmode) .projects-table-wrap .text-15,
:global(body.darkmode) .projects-table-wrap .text-15,
:global(html.dark) .projects-table-wrap .text-15,
:global(body.dark) .projects-table-wrap .text-15 {
  color: #fff !important;
}

:global(html.darkmode) .project-avatar,
:global(body.darkmode) .project-avatar,
:global(html.dark) .project-avatar,
:global(body.dark) .project-avatar {
  background: rgba(46, 107, 255, 0.18) !important;
}

:global(html.darkmode) .project-avatar-text,
:global(body.darkmode) .project-avatar-text,
:global(html.dark) .project-avatar-text,
:global(body.dark) .project-avatar-text {
  color: #9cc0ff !important;
}

:global(html.darkmode) .input._search-project,
:global(body.darkmode) .input._search-project,
:global(html.dark) .input._search-project,
:global(body.dark) .input._search-project {
  background: rgba(255, 255, 255, 0.07) !important;
  border-color: rgba(255, 255, 255, 0.16) !important;
  color: #fff !important;
}

:global(html.darkmode) .input._search-project::placeholder,
:global(body.darkmode) .input._search-project::placeholder,
:global(html.dark) .input._search-project::placeholder,
:global(body.dark) .input._search-project::placeholder {
  color: rgba(255, 255, 255, 0.45);
}

.is-dark-input::placeholder {
  color: rgba(255, 255, 255, 0.5) !important;
}

:global(html.darkmode) .delete-modal,
:global(body.darkmode) .delete-modal,
:global(html.dark) .delete-modal,
:global(body.dark) .delete-modal {
  background: rgba(35, 37, 48, 0.96) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
