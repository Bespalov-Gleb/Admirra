<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="section-header pt-4">
        <h3 class="heading-3">{{ title }}</h3>
      </div>
      <div class="row gy-3 mb-5">
        <div class="col">
          <div class="row gy-3">
            <div v-for="tab in tabs" :key="tab.id" class="col-auto">
              <button
                :class="['btn', currentTab === tab.id ? '_primary' : '_white']"
                @click="switchTab(tab.id)"
              >
                <div class="btn__inner">
                  <span :class="['btn__text', { gray: currentTab !== tab.id }]">{{ tab.label }}</span>
                </div>
              </button>
            </div>
          </div>
        </div>
        <div class="col-auto">
          <button class="btn _primary" @click="handleAddMember">
            <div class="btn__inner">
              <span class="btn__text">{{ currentTab === 'staff' ? 'Добавить сотрудника' : 'Добавить клиента' }}</span>
              <div class="btn__icon-plus">+</div>
            </div>
          </button>
        </div>
      </div>
      
      <div v-for="(member, mIdx) in members" :key="member.id || mIdx" class="mb-4 pb-2">
        <div :class="['team-item', { 'is-open': member.isOpen }]">
          <div class="row team-item__header">
            <div class="col col-lg-4 col-xl-3">
              <div class="d-flex">
                <div class="avatar-36x36 me-4">
                  <img class="img-cover" :src="member.avatar" alt="#" />
                </div>
                <div class="weight-500">
                  <div class="mb-1 text-15 gray">{{ member.name }}</div>
                  <div class="gray56">{{ member.email }}</div>
                </div>
              </div>
            </div>
            <div class="col-auto col-lg">
              <button class="team-item__project-toggle" @click="member.isOpen = !member.isOpen">
                <span>{{ projectsToggleLabel }}</span>
                <div class="circle-arrow _light">
                  <svg><use :href="arrowIcon"></use></svg>
                </div>
              </button>
            </div>
            <div class="col-12 col-lg-auto">
              <div class="row">
                <div class="col col-lg-auto">
                  <button class="btn _primary" @click="addAccess(member)">
                    <div class="btn__inner">
                      <span class="btn__text">Добавить доступ к проекту</span>
                      <div class="btn__icon-plus">+</div>
                    </div>
                  </button>
                </div>
                <div class="col-auto col-lg-auto">
                  <button class="btn-action _danger" @click="deleteMember(member)">
                    <svg><use :href="basketIcon"></use></svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div v-if="member.isOpen" class="team-item__project-content row g-4" style="display: flex;">
            <div v-for="(project, pIdx) in member.projects" :key="pIdx" class="col-12 col-sm-auto">
              <div :class="['card-base', project.variantClass]">
                <div class="avatar-30x30 mb-2">
                  <img class="img-cover" :src="project.icon" alt="#" />
                </div>
                <div class="weight-500 gray500">{{ project.name }}</div>
                <button class="btn _sm _white mt-auto" @click="revokeAccess(member, project)">
                  <div class="btn__inner">
                    <span class="btn__text gray">Отозвать доступ</span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../../api/axios'

const title = 'Команда'
const tabs = [
  { id: 'staff', label: 'Сотрудники' },
  { id: 'clients', label: 'Клиенты' }
]
const currentTab = ref('staff')
const members = ref([])
const projects = ref([])
const arrowIcon = '/admirra/img/svg/sprite.svg#arrow'
const basketIcon = '/admirra/img/svg/sprite.svg#basket'

const roleVariant = (idx) => (idx % 2 ? '_aliceblue' : '_oldlace')

const tabEndpoint = computed(() => (currentTab.value === 'staff' ? 'team/members?role=member' : 'team/clients'))

const loadProjects = async () => {
  try {
    const { data } = await api.get('team/projects')
    projects.value = data || []
  } catch {
    projects.value = []
  }
}

const normalizeMembers = (list) => (list || []).map((m, idx) => ({
  id: m.id,
  user_id: m.user_id,
  name: m.full_name || m.email,
  email: m.email,
  status: m.status,
  avatar: '/admirra/img/avatars/user1.jpg',
  isOpen: true,
  projects: (m.projects || []).map((p, pIdx) => ({
    id: p.id,
    name: p.name,
    icon: '/admirra/img/avatars/avatar-36x36.png',
    variantClass: roleVariant(pIdx),
  })),
}))

const loadMembers = async () => {
  const { data } = await api.get(tabEndpoint.value)
  members.value = normalizeMembers(data)
}

const switchTab = async (tabId) => {
  currentTab.value = tabId
  await loadMembers()
}

const handleAddMember = async () => {
  const email = window.prompt(`Email ${currentTab.value === 'staff' ? 'сотрудника' : 'клиента'}`)
  if (!email) return
  const endpoint = currentTab.value === 'staff' ? 'team/members/invite' : 'team/clients/invite'
  await api.post(endpoint, { email })
  await loadMembers()
}

const addAccess = async (member) => {
  const memberKey = member.user_id || member.id
  if (!memberKey) {
    window.alert('Пользователь еще не принял приглашение')
    return
  }
  const excluded = new Set((member.projects || []).map((p) => p.id))
  const available = projects.value.filter((p) => !excluded.has(p.id))
  if (!available.length) {
    window.alert('Нет доступных проектов для выдачи')
    return
  }
  const optionsText = available.map((p) => `${p.id}: ${p.name}`).join('\n')
  const selectedId = window.prompt(`Введите ID проекта для доступа:\n${optionsText}`)
  if (!selectedId) return
  const endpoint = currentTab.value === 'staff' ? `team/members/${memberKey}/projects` : `team/clients/${memberKey}/projects`
  await api.post(endpoint, { project_id: selectedId })
  await loadMembers()
}

const revokeAccess = async (member, project) => {
  const ok = window.confirm(`Отозвать доступ к проекту "${project.name}" у "${member.name}"?`)
  if (!ok) return
  const memberKey = member.user_id || member.id
  const endpoint = currentTab.value === 'staff'
    ? `team/members/${memberKey}/projects/${project.id}`
    : `team/clients/${memberKey}/projects/${project.id}`
  await api.delete(endpoint)
  await loadMembers()
}

const deleteMember = async (member) => {
  const ok = window.confirm(`Удалить ${member.name}? Все доступы будут отозваны.`)
  if (!ok) return
  const memberKey = member.user_id || member.id
  const endpoint = currentTab.value === 'staff' ? `team/members/${memberKey}` : `team/clients/${memberKey}`
  await api.delete(endpoint)
  await loadMembers()
}

onMounted(async () => {
  await loadProjects()
  await loadMembers()
})
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
/* Ensure project content handles visibility correctly if not using jQuery slideToggle */
.team-item__project-content {
  transition: all 0.3s ease;
}
</style>
