<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-hidden px-[25px] py-[30px]">

    <!-- Heading -->
    <div class="pt-[15px] pb-[15px] mb-[10px]">
      <h3 class="text-[30px] font-semibold leading-none text-[#171717] dark:text-white">Команда</h3>
    </div>

    <!-- Toolbar -->
    <div class="flex flex-wrap items-center justify-between gap-[10px] mb-[30px]">
      <!-- Tabs -->
      <div class="flex gap-[10px]">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn"
          :class="currentTab === tab.id ? 'tab-btn--active' : 'tab-btn--inactive'"
          @click="currentTab = tab.id"
        >{{ tab.label }}</button>
      </div>

      <!-- Add member -->
      <button class="add-btn" @click="inviteMember">
        <span>Добавить сотрудника</span>
        <span class="icon-plus">+</span>
      </button>
    </div>

    <div v-if="isLoading" class="team-empty">
      <p class="text-[15px] font-medium leading-none text-[#696969]">Загрузка команды...</p>
    </div>

    <div v-else-if="members.length" class="flex flex-col gap-[15px]">
      <div
        v-for="(member, idx) in members"
        :key="member.id"
        class="team-item"
      >
        <div
          class="team-header"
          :class="{ 'team-header--open': openIndex === idx }"
        >
          <div class="flex items-center gap-[15px] min-w-0">
            <div class="member-avatar flex-shrink-0">
              <span>{{ (member.name || '?').slice(0, 2).toUpperCase() }}</span>
            </div>
            <div class="min-w-0">
              <div class="text-[15px] font-medium text-[#696969] leading-none mb-[4px] truncate">{{ member.name }}</div>
              <div class="text-[13px] text-[rgba(105,105,105,0.56)] leading-none truncate">{{ member.email }}</div>
            </div>
          </div>

          <button class="toggle-btn" @click="toggleMember(idx)">
            <span class="text-[15px] text-[#696969] font-medium">Доступ к проектам</span>
            <span class="toggle-arrow" :class="{ 'toggle-arrow--open': openIndex === idx }">
              <svg width="7" height="5" viewBox="0 0 9 6" fill="none">
                <path d="M0.5 1L4.5 5L8.5 1" stroke="#696969" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </button>

          <div class="flex items-center gap-[10px]">
            <button class="access-btn" @click="grantAccess(member)">
              <span>Добавить доступ к&nbsp;проекту</span>
              <span class="icon-plus">+</span>
            </button>
            <button class="delete-btn" title="Удалить" @click="removeMember(member)">
              <svg width="16" height="16" viewBox="0 0 20 22" fill="none">
                <path d="M1 5H19M8 9V17M12 9V17M3 5L4 19C4 20.1 4.9 21 6 21H14C15.1 21 16 20.1 16 19L17 5M7 5V3C7 1.9 7.9 1 9 1H11C12.1 1 13 1.9 13 3V5" stroke="#afafaf" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>

        <Transition
          name="team-projects"
        >
          <div v-if="openIndex === idx" class="projects-content">
            <div class="projects-content__inner">
              <div class="projects-content__body">
                <div class="flex flex-wrap gap-[15px]">
                  <div
                    v-for="(project, pIdx) in member.projects"
                    :key="pIdx"
                    class="project-card"
                    :style="{ backgroundColor: project.color }"
                  >
                    <div class="project-card__icon">
                      <span>{{ project.name.slice(0, 2).toUpperCase() }}</span>
                    </div>
                    <div class="text-[14px] font-medium text-[#515151] leading-[1.3] flex-1">{{ project.name }}</div>
                    <button class="revoke-btn" @click="revokeAccess(member, project)">Отозвать доступ</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <div v-else class="team-empty">
      <p class="text-[15px] font-medium leading-none text-[#696969]">Сотрудники пока не добавлены</p>
      <p class="mt-[8px] text-[13px] leading-[1.4] text-[rgba(105,105,105,0.56)]">Добавьте первого сотрудника, чтобы настроить доступы к проектам.</p>
    </div>

  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import api from '../../api/axios'

const tabs = [
  { id: 'staff',   label: 'Сотрудники' },
  { id: 'clients', label: 'Клиенты' },
]
const currentTab = ref('staff')
const openIndex = ref(null)
const members = ref([])
const teamProjects = ref([])
const isLoading = ref(false)

function toggleMember(idx) {
  openIndex.value = openIndex.value === idx ? null : idx
}

function roleByTab(tabId) {
  return tabId === 'clients' ? 'client' : 'member'
}

function colorForProject(name = '') {
  const palette = ['#fff2f2', '#fff9f2', '#f2f8ff', '#f2f2ff']
  const hash = [...name].reduce((acc, ch) => acc + ch.charCodeAt(0), 0)
  return palette[hash % palette.length]
}

function normalizeMember(raw) {
  const displayName = raw.full_name || raw.email || 'Без имени'
  const projects = (raw.projects || []).map((p) => ({
    id: p.id,
    name: p.name,
    color: colorForProject(p.name),
  }))
  return {
    id: raw.id,
    email: raw.email,
    role: raw.role,
    status: raw.status,
    userId: raw.user_id,
    name: displayName,
    projects,
  }
}

async function fetchTeamProjects() {
  try {
    const { data } = await api.get('/team/projects')
    teamProjects.value = Array.isArray(data) ? data : []
  } catch (e) {
    teamProjects.value = []
    console.warn('Не удалось загрузить список проектов команды', e?.response?.status)
  }
}

async function fetchMembers() {
  isLoading.value = true
  openIndex.value = null
  try {
    const { data } = await api.get('/team/members', {
      params: { role: roleByTab(currentTab.value) },
    })
    members.value = Array.isArray(data) ? data.map(normalizeMember) : []
  } catch (e) {
    members.value = []
    console.warn('Не удалось загрузить участников команды', e?.response?.status)
  } finally {
    isLoading.value = false
  }
}

async function inviteMember() {
  const email = window.prompt('Введите email участника')
  if (!email) return

  try {
    await api.post('/team/members/invite', {
      email: email.trim().toLowerCase(),
      role: roleByTab(currentTab.value),
    })
    await fetchMembers()
  } catch (e) {
    window.alert(e?.response?.data?.detail || 'Не удалось пригласить участника')
  }
}

async function removeMember(member) {
  if (!window.confirm(`Удалить участника ${member.email}?`)) return

  try {
    const endpoint = member.role === 'client' ? `/team/clients/${member.id}` : `/team/members/${member.id}`
    await api.delete(endpoint)
    await fetchMembers()
  } catch (e) {
    window.alert(e?.response?.data?.detail || 'Не удалось удалить участника')
  }
}

async function grantAccess(member) {
  if (!teamProjects.value.length) {
    await fetchTeamProjects()
  }
  if (!teamProjects.value.length) {
    window.alert('Нет доступных проектов для выдачи доступа')
    return
  }

  const options = teamProjects.value.map((p, idx) => `${idx + 1}. ${p.name}`).join('\n')
  const selected = window.prompt(`Выберите номер проекта:\n${options}`)
  const index = Number(selected) - 1
  const project = teamProjects.value[index]
  if (!project) return

  try {
    const endpoint = member.role === 'client' ? `/team/clients/${member.id}/projects` : `/team/members/${member.id}/projects`
    await api.post(endpoint, { project_id: project.id })
    await fetchMembers()
  } catch (e) {
    window.alert(e?.response?.data?.detail || 'Не удалось выдать доступ к проекту')
  }
}

async function revokeAccess(member, project) {
  if (!window.confirm(`Отозвать доступ "${project.name}" у ${member.email}?`)) return
  try {
    const endpoint = member.role === 'client'
      ? `/team/clients/${member.id}/projects/${project.id}`
      : `/team/members/${member.id}/projects/${project.id}`
    await api.delete(endpoint)
    await fetchMembers()
  } catch (e) {
    window.alert(e?.response?.data?.detail || 'Не удалось отозвать доступ')
  }
}

watch(currentTab, async () => {
  await fetchMembers()
})

onMounted(async () => {
  await Promise.all([fetchMembers(), fetchTeamProjects()])
})
</script>

<style scoped>
/* ── Tabs ── */
.tab-btn {
  display: inline-flex;
  align-items: center;
  min-height: 46px;
  padding: 8px 20px;
  border-radius: 23px;
  font-size: 13px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: background-color 0.3s, color 0.3s;
  white-space: nowrap;
}
.tab-btn--active  { background-color: #2563eb; color: #fff; }
.tab-btn--inactive { background-color: #fff; color: rgba(105, 105, 105, 0.7); }
.tab-btn--inactive:hover { background-color: #f5f7f9; }

/* ── Add member button ── */
.add-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  padding: 8px 20px;
  border-radius: 23px;
  background-color: #2563eb;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: background-color 0.3s, transform 0.3s;
  white-space: nowrap;
}
.add-btn:hover { background-color: #1d4ed8; }
.icon-plus {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.2);
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
  line-height: 1;
}

/* ── Team item ── */
.team-item {
  background-color: #fff;
  border-radius: 15px;
  overflow: hidden;
}
.team-empty {
  min-height: 150px;
  padding: 32px 22px;
  border-radius: 15px;
  background-color: #fff;
  text-align: center;
}
:global(.dark) .team-item,
:global(.dark) .team-empty {
  background-color: #1f2937;
}

/* ── Header ── */
.team-header {
  display: grid;
  grid-template-columns: 1fr;
  gap: 15px;
  align-items: center;
  padding: 20px 22px;
  border-bottom: 1px solid transparent;
  transition: border-color 0.3s ease;
}
@media (min-width: 1024px) {
  .team-header {
    grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) auto;
  }
}
.team-header--open {
  border-bottom-color: rgba(64, 64, 64, 0.12);
}

/* ── Projects toggle ── */
.toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 20px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  color: #696969;
  transition: color 0.5s;
}
.toggle-btn:hover { color: #2563eb; }
.toggle-btn:hover .toggle-arrow { background-color: #dbeafe; }
.toggle-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: #f5f7f9;
  flex-shrink: 0;
  transition: transform 0.5s, background-color 0.5s;
}
.toggle-arrow--open { transform: rotate(180deg); }

/* ── Access button ── */
.access-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  padding: 8px 20px;
  border-radius: 23px;
  background-color: #2563eb;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.3s;
}
.access-btn:hover { background-color: #1d4ed8; }

/* ── Delete button ── */
.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  border-radius: 4px;
  background-color: #f5f7f9;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
  transition: background-color 0.3s, transform 0.3s;
}
.delete-btn:hover {
  background-color: #ef4444;
  transform: scale(1.03);
}
.delete-btn:hover svg path { stroke: #fff; }
.delete-btn svg path { transition: stroke 0.3s; }

/* ── Projects content ── */
.projects-content {
  display: grid;
  grid-template-rows: 1fr;
  opacity: 1;
  overflow: hidden;
  will-change: grid-template-rows, opacity;
}
.projects-content__inner {
  min-height: 0;
  overflow: hidden;
}
.projects-content__body {
  padding: 21px 22px 20px;
}
.team-projects-enter-active,
.team-projects-leave-active {
  transition:
    grid-template-rows 0.42s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.28s ease;
}
.team-projects-enter-from,
.team-projects-leave-to {
  grid-template-rows: 0fr;
  opacity: 0;
}
.team-projects-enter-to,
.team-projects-leave-from {
  grid-template-rows: 1fr;
  opacity: 1;
}

/* ── Project card ── */
.project-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 160px;
  padding: 15px;
  border-radius: 12px;
  border: 1px solid rgba(105, 105, 105, 0.08);
}
.project-card__icon {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: #e8eef9;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.project-card__icon span {
  font-size: 10px;
  font-weight: 700;
  color: #4b6fa0;
  line-height: 1;
}

/* ── Revoke button ── */
.revoke-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  padding: 6px 16px;
  border-radius: 18px;
  background-color: #fff;
  color: rgba(105, 105, 105, 0.7);
  font-size: 12px;
  font-weight: 500;
  border: 1px solid rgba(105, 105, 105, 0.15);
  cursor: pointer;
  margin-top: auto;
  transition: border-color 0.2s, color 0.2s;
  white-space: nowrap;
}
.revoke-btn:hover { border-color: #ef4444; color: #ef4444; }


/* ── Member avatar ── */
.member-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e8eef9;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.member-avatar span {
  font-size: 12px;
  font-weight: 700;
  color: #4b6fa0;
  line-height: 1;
}
</style>
