<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-hidden px-[25px] py-[30px]">

    <!-- Heading -->
    <div class="pt-[15px] pb-[15px] mb-[10px]">
      <h3 class="text-[30px] font-semibold leading-none text-[#171717] dark:text-white">Команда</h3>
    </div>

    <!-- Toolbar -->
    <div class="flex flex-wrap items-center justify-between gap-[10px] mb-[30px]">
      <!-- Tabs -->
      <div class="flex min-w-0 flex-wrap gap-[10px]">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn"
          :class="currentTab === tab.id
            ? 'tab-btn--active dark:!bg-[#2563eb] dark:!text-white'
            : 'tab-btn--inactive dark:!bg-[#2C2F3D] dark:!text-white/75 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)] dark:hover:!bg-white/10'"
          @click="currentTab = tab.id"
        >{{ tab.label }}</button>
      </div>

      <!-- Add member / client -->
      <button class="add-btn" @click="inviteMember">
        <span>{{ addButtonLabel }}</span>
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
        class="team-item dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10"
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
              <div class="flex flex-wrap items-center gap-[8px] mb-[4px]">
                <div class="text-[15px] font-medium text-[#696969] leading-none truncate dark:!text-white/85">{{ member.name }}</div>
                <span
                  class="status-badge"
                  :class="member.status === 'active' ? 'status-badge--active' : 'status-badge--pending'"
                >{{ member.status === 'active' ? 'Активен' : 'Ожидает' }}</span>
              </div>
              <div class="text-[13px] text-[rgba(105,105,105,0.56)] leading-none truncate dark:!text-white/55">{{ member.email }}</div>
            </div>
          </div>

          <button class="toggle-btn dark:!text-white/75" @click="toggleMember(idx)">
            <span class="text-[15px] text-[#696969] font-medium dark:!text-white/75">Доступ к проектам</span>
            <span class="toggle-arrow dark:!bg-white/10" :class="{ 'toggle-arrow--open': openIndex === idx }">
              <svg width="7" height="5" viewBox="0 0 9 6" fill="none">
                <path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </button>

          <div class="team-actions flex items-center gap-[10px]">
            <button class="access-btn" @click="grantAccess(member)">
              <span>Добавить доступ к&nbsp;проекту</span>
              <span class="icon-plus">+</span>
            </button>
            <button class="delete-btn dark:!bg-white/10" title="Удалить" type="button" @click="openRemoveConfirm(member)">
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
                    class="project-card dark:!bg-white/5 dark:!border-white/10"
                    :style="{ backgroundColor: project.color }"
                  >
                    <div class="project-card__icon dark:!bg-white/10">
                      <span>{{ project.name.slice(0, 2).toUpperCase() }}</span>
                    </div>
                    <div class="text-[14px] font-medium text-[#515151] leading-[1.3] flex-1 dark:!text-white/85">{{ project.name }}</div>
                    <button
                      type="button"
                      class="revoke-btn dark:!border-white/15 dark:!bg-white/10 dark:!text-white/70"
                      @click="openRevokeConfirm(member, project)"
                    >Отозвать доступ</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <div v-else class="team-empty dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
      <p class="text-[15px] font-medium leading-none text-[#696969] dark:!text-white/80">Сотрудники пока не добавлены</p>
      <p class="mt-[8px] text-[13px] leading-[1.4] text-[rgba(105,105,105,0.56)] dark:!text-white/55">Добавьте первого сотрудника, чтобы настроить доступы к проектам.</p>
    </div>

    <!-- Приглашение по email -->
    <Modal
      v-model:isOpen="showInviteModal"
      title="Добавить участника"
      size="md"
      @close="resetInviteModal"
    >
      <div class="space-y-3">
        <p class="text-sm text-gray-600 dark:text-white/65">
          Укажите email — человек получит приглашение в роли «{{ currentTab === 'clients' ? 'клиент' : 'сотрудник' }}».
        </p>
        <div>
          <label for="team-invite-email" class="mb-1 block text-sm font-medium text-gray-800 dark:text-white/85">Email</label>
          <input
            id="team-invite-email"
            v-model="inviteEmail"
            type="email"
            autocomplete="email"
            placeholder="name@company.com"
            class="team-modal-input"
            @keyup.enter="submitInvite"
          >
        </div>
        <p v-if="inviteError" class="text-sm text-red-600 dark:text-red-400">{{ inviteError }}</p>
      </div>
      <template #footer>
        <div class="flex flex-wrap justify-end gap-3">
          <button type="button" class="team-modal-btn team-modal-btn--ghost" @click="showInviteModal = false">Отмена</button>
          <button
            type="button"
            class="team-modal-btn team-modal-btn--primary"
            :disabled="inviteSubmitting"
            @click="submitInvite"
          >
            {{ inviteSubmitting ? 'Отправка…' : 'Отправить приглашение' }}
          </button>
        </div>
      </template>
    </Modal>

    <!-- Выбор проекта для доступа -->
    <Modal
      v-model:isOpen="showGrantModal"
      title="Доступ к проекту"
      size="md"
      @close="resetGrantModal"
    >
      <div v-if="grantMember" class="space-y-3">
        <p class="text-sm text-gray-600 dark:text-white/65">
          Участник: <span class="font-medium text-gray-900 dark:text-white">{{ grantMember.email }}</span>
        </p>
        <p v-if="!availableGrantProjects.length" class="text-sm text-amber-700 dark:text-amber-400">
          Нет проектов без доступа — все доступные проекты уже подключены.
        </p>
        <ul v-else class="max-h-[min(50vh,320px)] space-y-2 overflow-y-auto pr-1">
          <li v-for="p in availableGrantProjects" :key="p.id">
            <button
              type="button"
              class="team-project-pick"
              :disabled="grantSubmitting"
              @click="submitGrantAccess(p)"
            >
              <span class="font-medium text-gray-900 dark:text-white/90">{{ p.name }}</span>
              <span v-if="projectAccessLabel(p.id)" class="text-xs text-gray-500 dark:text-white/50">{{ projectAccessLabel(p.id) }}</span>
              <span class="text-xs text-gray-500 dark:text-white/50">Выдать доступ</span>
            </button>
          </li>
        </ul>
      </div>
      <template #footer>
        <div class="flex justify-end">
          <button type="button" class="team-modal-btn team-modal-btn--ghost" @click="closeGrantModal">Закрыть</button>
        </div>
      </template>
    </Modal>

    <ConfirmModal
      v-model:isOpen="showRemoveConfirm"
      title="Удалить участника?"
      :message="removeConfirmMessage"
      @confirm="performRemoveMember"
    />
    <ConfirmModal
      v-model:isOpen="showRevokeConfirm"
      title="Отозвать доступ?"
      :message="revokeConfirmMessage"
      @confirm="performRevokeAccess"
    />

    <Modal
      v-model:isOpen="showUpgradeModal"
      title="Лимит тарифа"
      size="md"
    >
      <p class="text-sm text-gray-600 dark:text-white/70">{{ upgradeModalMessage }}</p>
      <template #footer>
        <div class="flex flex-wrap justify-end gap-3">
          <button type="button" class="team-modal-btn team-modal-btn--ghost" @click="showUpgradeModal = false">Закрыть</button>
          <router-link to="/tariffs" class="team-modal-btn team-modal-btn--primary" @click="showUpgradeModal = false">
            Перейти к тарифам
          </router-link>
        </div>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import api from '../../api/axios'
import Modal from '../../components/Modal.vue'
import ConfirmModal from '../../components/ConfirmModal.vue'
import { useToaster } from '../../composables/useToaster'

const toaster = useToaster()

const showInviteModal = ref(false)
const inviteEmail = ref('')
const inviteSubmitting = ref(false)
const inviteError = ref('')

const showGrantModal = ref(false)
const grantMember = ref(null)
const grantSubmitting = ref(false)
const projectAccessById = ref({})

const tabs = [
  { id: 'staff',   label: 'Сотрудники' },
  { id: 'clients', label: 'Клиенты' },
]
const currentTab = ref('staff')
const openIndex = ref(null)
const members = ref([])
const teamProjects = ref([])
const isLoading = ref(false)

const showRemoveConfirm = ref(false)
const pendingRemoveMember = ref(null)
const addButtonLabel = computed(() =>
  currentTab.value === 'clients' ? 'Добавить клиента' : 'Добавить сотрудника'
)

const removeConfirmMessage = computed(() => {
  const m = pendingRemoveMember.value
  if (!m) return ''
  const label = m.name && m.name !== m.email ? m.name : m.email
  const roleWord = m.role === 'client' ? 'клиента' : 'сотрудника'
  return `Удалить ${roleWord} ${label}? Все доступы будут отозваны.`
})

const showUpgradeModal = ref(false)
const upgradeModalMessage = ref('')

const showRevokeConfirm = ref(false)
const pendingRevoke = ref({ member: null, project: null })
const revokeConfirmMessage = computed(() => {
  const { member, project } = pendingRevoke.value
  if (!member || !project) return ''
  return `Отозвать доступ к проекту «${project.name}» у ${member.email}?`
})

const availableGrantProjects = computed(() => {
  const m = grantMember.value
  if (!m) return []
  const ids = new Set((m.projects || []).map((p) => p.id))
  return teamProjects.value.filter((p) => !ids.has(p.id))
})

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

function resetInviteModal() {
  inviteEmail.value = ''
  inviteError.value = ''
  inviteSubmitting.value = false
}

function inviteMember() {
  resetInviteModal()
  showInviteModal.value = true
}

const emailLooksValid = (s) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)

async function submitInvite() {
  inviteError.value = ''
  const raw = inviteEmail.value.trim().toLowerCase()
  if (!raw) {
    inviteError.value = 'Введите email'
    return
  }
  if (!emailLooksValid(raw)) {
    inviteError.value = 'Похоже на некорректный email'
    return
  }
  inviteSubmitting.value = true
  try {
    await api.post('/team/members/invite', {
      email: raw,
      role: roleByTab(currentTab.value),
    })
    showInviteModal.value = false
    resetInviteModal()
    toaster.success('Приглашение отправлено')
    await fetchMembers()
  } catch (e) {
    const detail = e?.response?.data?.detail
    const status = e?.response?.status
    if (status === 403 && String(detail || '').toLowerCase().includes('лимит')) {
      upgradeModalMessage.value = typeof detail === 'string' ? detail : 'Достигнут лимит для текущего тарифа. Обновите тариф, чтобы добавить участников.'
      showUpgradeModal.value = true
      inviteError.value = ''
    } else {
      inviteError.value = detail || 'Не удалось пригласить участника'
    }
  } finally {
    inviteSubmitting.value = false
  }
}

function openRemoveConfirm(member) {
  pendingRemoveMember.value = member
  showRemoveConfirm.value = true
}

async function performRemoveMember() {
  const member = pendingRemoveMember.value
  if (!member) return
  try {
    const endpoint = member.role === 'client' ? `/team/clients/${member.id}` : `/team/members/${member.id}`
    await api.delete(endpoint)
    toaster.success('Участник удалён')
    await fetchMembers()
  } catch (e) {
    toaster.error(e?.response?.data?.detail || 'Не удалось удалить участника')
  } finally {
    pendingRemoveMember.value = null
  }
}

function resetGrantModal() {
  grantMember.value = null
  grantSubmitting.value = false
}

function closeGrantModal() {
  showGrantModal.value = false
  resetGrantModal()
}

function projectAccessLabel(projectId) {
  const list = projectAccessById.value[projectId]
  if (!list?.length) return ''
  const names = list.map((m) => m.full_name || m.email).slice(0, 3)
  const more = list.length > 3 ? ` и ещё ${list.length - 3}` : ''
  return `Уже имеют доступ: ${names.join(', ')}${more}`
}

async function loadProjectAccessMap() {
  const map = {}
  await Promise.all(
    teamProjects.value.map(async (p) => {
      try {
        const { data } = await api.get(`/team/projects/${p.id}/members`)
        map[p.id] = Array.isArray(data) ? data : []
      } catch {
        map[p.id] = []
      }
    })
  )
  projectAccessById.value = map
}

async function grantAccess(member) {
  if (!teamProjects.value.length) {
    await fetchTeamProjects()
  }
  if (!teamProjects.value.length) {
    toaster.warning('Нет доступных проектов для выдачи доступа')
    return
  }
  await loadProjectAccessMap()
  grantMember.value = member
  showGrantModal.value = true
  if (!availableGrantProjects.value.length) {
    toaster.info('У участника уже есть доступ ко всем проектам из списка')
  }
}

async function submitGrantAccess(project) {
  const member = grantMember.value
  if (!member || !project) return
  grantSubmitting.value = true
  try {
    const endpoint = member.role === 'client' ? `/team/clients/${member.id}/projects` : `/team/members/${member.id}/projects`
    await api.post(endpoint, { project_id: project.id })
    toaster.success(`Доступ к «${project.name}» выдан`)
    closeGrantModal()
    await fetchMembers()
  } catch (e) {
    toaster.error(e?.response?.data?.detail || 'Не удалось выдать доступ к проекту')
  } finally {
    grantSubmitting.value = false
  }
}

function openRevokeConfirm(member, project) {
  pendingRevoke.value = { member, project }
  showRevokeConfirm.value = true
}

async function performRevokeAccess() {
  const { member, project } = pendingRevoke.value
  if (!member || !project) return
  try {
    const endpoint = member.role === 'client'
      ? `/team/clients/${member.id}/projects/${project.id}`
      : `/team/members/${member.id}/projects/${project.id}`
    await api.delete(endpoint)
    toaster.success('Доступ отозван')
    await fetchMembers()
  } catch (e) {
    toaster.error(e?.response?.data?.detail || 'Не удалось отозвать доступ')
  } finally {
    pendingRevoke.value = { member: null, project: null }
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
:global(.dark) .tab-btn--active,
:global(.darkmode) .tab-btn--active {
  color: #fff !important;
}
:global(.dark) .tab-btn--inactive,
:global(.darkmode) .tab-btn--inactive {
  background-color: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.7);
}
:global(.dark) .tab-btn--inactive:hover,
:global(.darkmode) .tab-btn--inactive:hover {
  background-color: rgba(255,255,255,0.12);
}

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
:global(.darkmode) .team-item,
:global(.dark) .team-empty,
:global(.darkmode) .team-empty {
  background-color: #2C2F3D;
  border: 1px solid rgba(255,255,255,0.08);
}
:global(.dark) .team-empty p,
:global(.darkmode) .team-empty p {
  color: rgba(255,255,255,0.72) !important;
}
:global(.dark) .team-item .text-\[\#696969\],
:global(.darkmode) .team-item .text-\[\#696969\],
:global(.dark) .team-item .text-\[\#515151\],
:global(.darkmode) .team-item .text-\[\#515151\] {
  color: rgba(255,255,255,0.82) !important;
}
:global(.dark) .team-item .text-\[rgba\(105\,105\,105\,0\.56\)\],
:global(.darkmode) .team-item .text-\[rgba\(105\,105\,105\,0\.56\)\] {
  color: rgba(255,255,255,0.55) !important;
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

.team-actions {
  min-width: 0;
}

@media (max-width: 639px) {
  .tab-btn,
  .add-btn,
  .access-btn {
    width: 100%;
    justify-content: center;
  }

  .team-actions {
    flex-direction: column;
    align-items: stretch;
    width: 100%;
  }

  .toggle-btn {
    justify-content: space-between;
    width: 100%;
  }
}
@media (min-width: 1024px) {
  .team-header {
    grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) auto;
  }
}
.team-header--open {
  border-bottom-color: rgba(64, 64, 64, 0.12);
}
:global(.dark) .team-header--open,
:global(.darkmode) .team-header--open {
  border-bottom-color: rgba(255,255,255,0.10);
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
:global(.dark) .toggle-btn,
:global(.darkmode) .toggle-btn {
  color: rgba(255,255,255,0.72);
}
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
:global(.dark) .toggle-arrow,
:global(.darkmode) .toggle-arrow {
  background-color: rgba(255,255,255,0.08);
}

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
:global(.dark) .delete-btn,
:global(.darkmode) .delete-btn {
  background-color: rgba(255,255,255,0.08);
}

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
:global(.dark) .project-card,
:global(.darkmode) .project-card {
  background-color: rgba(255,255,255,0.04) !important;
  border-color: rgba(255,255,255,0.10);
}
:global(.dark) .project-card__icon,
:global(.darkmode) .project-card__icon {
  background-color: rgba(255,255,255,0.08);
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
:global(.dark) .revoke-btn,
:global(.darkmode) .revoke-btn {
  background-color: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.70);
}


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

/* ── Modals (контент внутри общего Modal.vue) ── */
.team-modal-input {
  width: 100%;
  border-radius: 10px;
  border: 1px solid rgba(105, 105, 105, 0.2);
  padding: 10px 12px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.team-modal-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}
:global(.dark) .team-modal-input,
:global(.darkmode) .team-modal-input {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.92);
}
.team-modal-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 8px 18px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s, opacity 0.2s;
}
.team-modal-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.team-modal-btn--ghost {
  background: #f3f4f6;
  color: #374151;
}
.team-modal-btn--ghost:hover:not(:disabled) {
  background: #e5e7eb;
}
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.2;
  white-space: nowrap;
}
.status-badge--active {
  background: rgba(34, 197, 94, 0.15);
  color: #15803d;
}
.status-badge--pending {
  background: rgba(234, 179, 8, 0.18);
  color: #a16207;
}
:global(.dark) .status-badge--active,
:global(.darkmode) .status-badge--active {
  background: rgba(34, 197, 94, 0.22);
  color: #86efac;
}
:global(.dark) .status-badge--pending,
:global(.darkmode) .status-badge--pending {
  background: rgba(234, 179, 8, 0.2);
  color: #fde047;
}

.team-modal-btn--primary {
  background: #2563eb;
  color: #fff;
}
.team-modal-btn--primary:hover:not(:disabled) {
  background: #1d4ed8;
}
:global(.dark) .team-modal-btn--ghost,
:global(.darkmode) .team-modal-btn--ghost {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.85);
}
:global(.dark) .team-modal-btn--ghost:hover:not(:disabled),
:global(.darkmode) .team-modal-btn--ghost:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.14);
}
.team-project-pick {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(105, 105, 105, 0.12);
  background: #f9fafb;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}
.team-project-pick:hover:not(:disabled) {
  border-color: #2563eb;
  background: #eff6ff;
}
.team-project-pick:disabled {
  opacity: 0.6;
  cursor: wait;
}
:global(.dark) .team-project-pick,
:global(.darkmode) .team-project-pick {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}
:global(.dark) .team-project-pick:hover:not(:disabled),
:global(.darkmode) .team-project-pick:hover:not(:disabled) {
  background: rgba(37, 99, 235, 0.15);
  border-color: rgba(96, 165, 250, 0.45);
}
</style>
