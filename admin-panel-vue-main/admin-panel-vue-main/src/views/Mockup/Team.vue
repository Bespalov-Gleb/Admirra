<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-hidden px-[1.7361rem] py-[2.0833rem]">

    <!-- Heading -->
    <div class="pt-[1.0417rem] pb-[1.0417rem] mb-[0.6944rem]">
      <h3 class="text-[2.0833rem] font-semibold leading-none text-[#171717] dark:text-white">Команда</h3>
    </div>

    <!-- Toolbar -->
    <div class="flex flex-wrap items-center justify-between gap-[0.6944rem] mb-[2.0833rem]">
      <div class="flex min-w-0 flex-wrap gap-[0.6944rem]">
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
      <button class="add-btn" @click="openInviteModal">
        <span>Добавить сотрудника</span>
        <span class="icon-plus">+</span>
      </button>
    </div>

    <div v-if="isLoading" class="team-empty">
      <p class="text-[1.0417rem] font-medium leading-none text-[#696969]">Загрузка команды...</p>
    </div>

    <div v-else-if="members.length" class="flex flex-col gap-[1.0417rem]">
      <div
        v-for="(member, idx) in members"
        :key="member.id"
        class="team-item dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10"
      >
        <div
          class="team-header"
          :class="{ 'team-header--open': openIndex === idx }"
        >
          <div class="flex items-center gap-[1.0417rem] min-w-0">
            <div class="member-avatar flex-shrink-0">
              <span>{{ (member.name || '?').slice(0, 2).toUpperCase() }}</span>
            </div>
            <div class="min-w-0">
              <div class="text-[1.0417rem] font-medium text-[#696969] leading-none mb-[0.2778rem] truncate dark:!text-white/85">{{ member.name }}</div>
              <div class="text-[0.9028rem] text-[rgba(105,105,105,0.56)] leading-none truncate dark:!text-white/55">{{ member.email }}</div>
            </div>
          </div>

          <button class="toggle-btn dark:!text-white/75" @click="toggleMember(idx)">
            <span class="text-[1.0417rem] text-[#696969] font-medium dark:!text-white/75">Доступ к проектам</span>
            <span class="toggle-arrow dark:!bg-white/10" :class="{ 'toggle-arrow--open': openIndex === idx }">
              <svg width="7" height="5" viewBox="0 0 9 6" fill="none">
                <path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </button>

          <div class="team-actions flex items-center gap-[0.6944rem]">
            <button class="access-btn" @click="openGrantModal(member)">
              <span>Добавить доступ к&nbsp;проекту</span>
              <span class="icon-plus">+</span>
            </button>
            <button class="edit-btn dark:!bg-white/10" title="Редактировать" @click="openEditModal(member)">
              <svg width="15" height="15" viewBox="0 0 20 20" fill="none">
                <path d="M14.7 2.3a1 1 0 011.4 1.4l-1 1-1.4-1.4 1-1zM3 14l1-4L13.3 4.7l1.4 1.4L5.4 15.6 3 17l-.3-1.7L3 14z" fill="#afafaf"/>
              </svg>
            </button>
            <button class="delete-btn dark:!bg-white/10" title="Удалить" @click="openConfirmDelete(member)">
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
                <div class="flex flex-wrap gap-[1.0417rem]">
                  <div
                    v-for="(project, pIdx) in member.projects"
                    :key="pIdx"
                    class="project-card dark:!bg-white/5 dark:!border-white/10"
                    :style="{ backgroundColor: project.color }"
                  >
                    <div class="project-card__icon dark:!bg-white/10">
                      <span>{{ project.name.slice(0, 2).toUpperCase() }}</span>
                    </div>
                    <div class="text-[0.9722rem] font-medium text-[#515151] leading-[1.3] flex-1 dark:!text-white/85">{{ project.name }}</div>
                    <button class="revoke-btn dark:!border-white/15 dark:!bg-white/10 dark:!text-white/70" @click="openConfirmRevoke(member, project)">Отозвать доступ</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <div v-else class="team-empty dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
      <p class="text-[1.0417rem] font-medium leading-none text-[#696969] dark:!text-white/80">Сотрудники пока не добавлены</p>
      <p class="mt-[0.5556rem] text-[0.9028rem] leading-[1.4] text-[rgba(105,105,105,0.56)] dark:!text-white/55">Добавьте первого сотрудника, чтобы настроить доступы к проектам.</p>
    </div>

  </div>

  <!-- ── Modal: Invite member ── -->
  <Teleport to="body">
    <div v-if="inviteModal.open" class="tm-overlay" @click.self="inviteModal.open = false">
      <div class="tm-box dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
        <h4 class="tm-title dark:!text-white">{{ currentTab === 'clients' ? 'Добавить клиента' : 'Добавить сотрудника' }}</h4>
        <p class="tm-sub dark:!text-white/55">Введите email — участник получит приглашение</p>
        <input
          v-model="inviteModal.email"
          type="email"
          placeholder="email@company.ru"
          class="tm-input dark:!bg-white/5 dark:!border-white/10 dark:!text-white dark:placeholder:!text-white/30"
          @keydown.enter="submitInvite"
          :disabled="inviteModal.loading"
        />
        <p v-if="inviteModal.error" class="tm-error">{{ inviteModal.error }}</p>
        <div class="tm-actions">
          <button class="tm-btn-cancel dark:!bg-white/8 dark:!text-white/70" @click="inviteModal.open = false">Отмена</button>
          <button class="tm-btn-primary" @click="submitInvite" :disabled="inviteModal.loading || !inviteModal.email.trim()">
            {{ inviteModal.loading ? 'Отправка...' : 'Пригласить' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- ── Modal: Grant access ── -->
  <Teleport to="body">
    <div v-if="grantModal.open" class="tm-overlay" @click.self="grantModal.open = false">
      <div class="tm-box dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
        <h4 class="tm-title dark:!text-white">Доступ к проектам</h4>
        <p class="tm-sub dark:!text-white/55">{{ grantModal.member?.name }} — выберите проекты</p>
        <div v-if="availableProjects.length" class="tm-checklist">
          <label
            v-for="project in availableProjects"
            :key="project.id"
            class="tm-check-item dark:!border-white/8 dark:hover:!bg-white/5"
            :class="{ 'tm-check-item--selected dark:!bg-[#2563eb]/15 dark:!border-[#2563eb]/40': grantModal.selectedIds.has(project.id) }"
          >
            <input type="checkbox" :value="project.id" :checked="grantModal.selectedIds.has(project.id)" @change="toggleProjectSelection(project.id)" class="sr-only" />
            <span class="tm-check-icon" :class="{ 'tm-check-icon--on': grantModal.selectedIds.has(project.id) }">
              <svg v-if="grantModal.selectedIds.has(project.id)" width="10" height="10" viewBox="0 0 12 12" fill="none">
                <path d="M2 6l3 3 5-5" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            <span class="tm-check-label dark:!text-white/80">{{ project.name }}</span>
          </label>
        </div>
        <p v-else class="tm-sub dark:!text-white/40">Все проекты уже доступны этому участнику</p>
        <p v-if="grantModal.error" class="tm-error">{{ grantModal.error }}</p>
        <div class="tm-actions">
          <button class="tm-btn-cancel dark:!bg-white/8 dark:!text-white/70" @click="grantModal.open = false">Отмена</button>
          <button class="tm-btn-primary" @click="submitGrantAccess" :disabled="grantModal.loading || !grantModal.selectedIds.size">
            {{ grantModal.loading ? 'Применение...' : `Применить (${grantModal.selectedIds.size})` }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- ── Modal: Edit member ── -->
  <Teleport to="body">
    <div v-if="editModal.open" class="tm-overlay" @click.self="editModal.open = false">
      <div class="tm-box tm-box--sm dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
        <h4 class="tm-title dark:!text-white">Редактировать участника</h4>
        <p class="tm-sub dark:!text-white/55">{{ editModal.member?.name }} ({{ editModal.member?.email }})</p>
        <div class="tm-role-group">
          <label class="tm-role-option dark:!border-white/10" :class="{ 'tm-role-option--active dark:!bg-[#2563eb]/15 dark:!border-[#2563eb]/50': editModal.role === 'member' }" @click="editModal.role = 'member'">
            <span class="tm-role-radio" :class="{ 'tm-role-radio--on': editModal.role === 'member' }"></span>
            <div>
              <div class="tm-role-label dark:!text-white/85">Сотрудник</div>
              <div class="tm-role-desc dark:!text-white/45">Доступ к назначенным проектам</div>
            </div>
          </label>
          <label class="tm-role-option dark:!border-white/10" :class="{ 'tm-role-option--active dark:!bg-[#2563eb]/15 dark:!border-[#2563eb]/50': editModal.role === 'client' }" @click="editModal.role = 'client'">
            <span class="tm-role-radio" :class="{ 'tm-role-radio--on': editModal.role === 'client' }"></span>
            <div>
              <div class="tm-role-label dark:!text-white/85">Клиент</div>
              <div class="tm-role-desc dark:!text-white/45">Ограниченный просмотр своих проектов</div>
            </div>
          </label>
        </div>
        <p v-if="editModal.error" class="tm-error">{{ editModal.error }}</p>
        <div class="tm-actions">
          <button class="tm-btn-cancel dark:!bg-white/8 dark:!text-white/70" @click="editModal.open = false">Отмена</button>
          <button class="tm-btn-primary" @click="submitEdit" :disabled="editModal.loading || editModal.role === editModal.member?.role">
            {{ editModal.loading ? 'Сохранение...' : 'Сохранить' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- ── Modal: Confirm ── -->
  <Teleport to="body">
    <div v-if="confirmModal.open" class="tm-overlay" @click.self="confirmModal.open = false">
      <div class="tm-box tm-box--sm dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
        <h4 class="tm-title dark:!text-white">{{ confirmModal.title }}</h4>
        <p class="tm-sub dark:!text-white/55">{{ confirmModal.message }}</p>
        <div class="tm-actions">
          <button class="tm-btn-cancel dark:!bg-white/8 dark:!text-white/70" @click="confirmModal.open = false">Отмена</button>
          <button class="tm-btn-danger" @click="runConfirm" :disabled="confirmModal.loading">
            {{ confirmModal.loading ? 'Удаление...' : confirmModal.confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>

</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '../../api/axios'
import { useToaster } from '../../composables/useToaster'
import { reachGoal } from '@/utils/metrika'

const toaster = useToaster()

const tabs = [
  { id: 'staff',   label: 'Сотрудники' },
  { id: 'clients', label: 'Клиенты' },
]
const currentTab = ref('staff')
const openIndex  = ref(null)
const members    = ref([])
const teamProjects = ref([])
const isLoading  = ref(false)

// ── Invite modal ──
const inviteModal = ref({ open: false, email: '', loading: false, error: '' })

function openInviteModal() {
  inviteModal.value = { open: true, email: '', loading: false, error: '' }
}

async function submitInvite() {
  const email = inviteModal.value.email.trim().toLowerCase()
  if (!email) return
  inviteModal.value.loading = true
  inviteModal.value.error = ''
  try {
    await api.post('/team/members/invite', { email, role: roleByTab(currentTab.value) })
    reachGoal('team_member_added')
    inviteModal.value.open = false
    toaster.success('Приглашение отправлено')
    await fetchMembers()
  } catch (e) {
    inviteModal.value.error = e?.response?.data?.detail || 'Не удалось пригласить участника'
  } finally {
    inviteModal.value.loading = false
  }
}

// ── Grant access modal ──
const grantModal = ref({ open: false, member: null, selectedIds: new Set(), loading: false, error: '' })

const availableProjects = computed(() => {
  if (!grantModal.value.member) return []
  const assignedIds = new Set(grantModal.value.member.projects.map(p => p.id))
  return teamProjects.value.filter(p => !assignedIds.has(p.id))
})

async function openGrantModal(member) {
  if (!teamProjects.value.length) await fetchTeamProjects()
  grantModal.value = { open: true, member, selectedIds: new Set(), loading: false, error: '' }
}

function toggleProjectSelection(projectId) {
  const ids = new Set(grantModal.value.selectedIds)
  ids.has(projectId) ? ids.delete(projectId) : ids.add(projectId)
  grantModal.value.selectedIds = ids
}

async function submitGrantAccess() {
  const { member, selectedIds } = grantModal.value
  if (!selectedIds.size) return
  grantModal.value.loading = true
  grantModal.value.error = ''
  try {
    const endpoint = member.role === 'client' ? `/team/clients/${member.id}/projects` : `/team/members/${member.id}/projects`
    await Promise.all([...selectedIds].map(id => api.post(endpoint, { project_id: id })))
    grantModal.value.open = false
    toaster.success('Доступ выдан')
    await fetchMembers()
  } catch (e) {
    grantModal.value.error = e?.response?.data?.detail || 'Не удалось выдать доступ'
  } finally {
    grantModal.value.loading = false
  }
}

// ── Edit modal ──
const editModal = ref({ open: false, member: null, role: 'member', loading: false, error: '' })

function openEditModal(member) {
  editModal.value = { open: true, member, role: member.role, loading: false, error: '' }
}

async function submitEdit() {
  const { member, role } = editModal.value
  if (role === member.role) return
  editModal.value.loading = true
  editModal.value.error = ''
  try {
    await api.patch(`/team/members/${member.id}`, { role })
    editModal.value.open = false
    toaster.success('Роль участника изменена')
    await fetchMembers()
  } catch (e) {
    editModal.value.error = e?.response?.data?.detail || 'Не удалось изменить роль'
  } finally {
    editModal.value.loading = false
  }
}

// ── Confirm modal ──
const confirmModal = ref({ open: false, title: '', message: '', confirmLabel: 'Удалить', loading: false, action: null })

function openConfirmDelete(member) {
  confirmModal.value = {
    open: true,
    title: 'Удалить участника?',
    message: `${member.name} (${member.email}) потеряет доступ ко всем проектам.`,
    confirmLabel: 'Удалить',
    loading: false,
    action: async () => {
      const endpoint = member.role === 'client' ? `/team/clients/${member.id}` : `/team/members/${member.id}`
      await api.delete(endpoint)
      toaster.success('Участник удалён')
      await fetchMembers()
    }
  }
}

function openConfirmRevoke(member, project) {
  confirmModal.value = {
    open: true,
    title: 'Отозвать доступ?',
    message: `Проект «${project.name}» станет недоступен для ${member.name}.`,
    confirmLabel: 'Отозвать',
    loading: false,
    action: async () => {
      const endpoint = member.role === 'client'
        ? `/team/clients/${member.id}/projects/${project.id}`
        : `/team/members/${member.id}/projects/${project.id}`
      await api.delete(endpoint)
      toaster.success('Доступ отозван')
      await fetchMembers()
    }
  }
}

async function runConfirm() {
  confirmModal.value.loading = true
  try {
    await confirmModal.value.action()
    confirmModal.value.open = false
  } catch (e) {
    toaster.error(e?.response?.data?.detail || 'Ошибка выполнения операции')
    confirmModal.value.open = false
  } finally {
    confirmModal.value.loading = false
  }
}

// ── Helpers ──
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
  return {
    id: raw.id,
    email: raw.email,
    role: raw.role,
    status: raw.status,
    userId: raw.user_id,
    name: raw.full_name || raw.email || 'Без имени',
    projects: (raw.projects || []).map(p => ({ id: p.id, name: p.name, color: colorForProject(p.name) })),
  }
}

async function fetchTeamProjects() {
  try {
    const { data } = await api.get('/team/projects')
    teamProjects.value = Array.isArray(data) ? data : []
  } catch (e) {
    teamProjects.value = []
  }
}

async function fetchMembers() {
  isLoading.value = true
  openIndex.value = null
  try {
    const { data } = await api.get('/team/members', { params: { role: roleByTab(currentTab.value) } })
    members.value = Array.isArray(data) ? data.map(normalizeMember) : []
  } catch (e) {
    members.value = []
  } finally {
    isLoading.value = false
  }
}

watch(currentTab, fetchMembers)
onMounted(() => Promise.all([fetchMembers(), fetchTeamProjects()]))
</script>

<style scoped>
/* ── Tabs ── */
.tab-btn {
  display: inline-flex;
  align-items: center;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.3889rem;
  border-radius: 1.5972rem;
  font-size: 0.9028rem;
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
  gap: 0.6944rem;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.3889rem;
  border-radius: 1.5972rem;
  background-color: #2563eb;
  color: #fff;
  font-size: 0.9028rem;
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
  width: 1.0417rem;
  height: 1.0417rem;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.2);
  font-size: 0.7639rem;
  font-weight: 600;
  flex-shrink: 0;
  line-height: 1;
}

/* ── Team item ── */
.team-item {
  background-color: #fff;
  border-radius: 1.0417rem;
  overflow: hidden;
}
.team-empty {
  min-height: 10.4167rem;
  padding: 2.2222rem 1.5278rem;
  border-radius: 1.0417rem;
  background-color: #fff;
  text-align: center;
}
:global(.dark) .team-item,
:global(.darkmode) .team-item,
:global(.dark) .team-empty,
:global(.darkmode) .team-empty {
  background-color: #2C2F3D;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.07);
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
  gap: 1.0417rem;
  align-items: center;
  padding: 1.3889rem 1.5278rem;
  border-bottom: 1px solid transparent;
  transition: border-color 0.3s ease;
}

.team-actions {
  min-width: 0;
}

@media (max-width: 479.25px) {
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
@media (min-width: 768px) {
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
  gap: 1.3889rem;
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
  width: 1.3889rem;
  height: 1.3889rem;
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
  gap: 0.6944rem;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.3889rem;
  border-radius: 1.5972rem;
  background-color: #2563eb;
  color: #fff;
  font-size: 0.9028rem;
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
  width: 3.1944rem;
  height: 3.1944rem;
  border-radius: 0.2778rem;
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
  padding: 1.4583rem 1.5278rem 1.3889rem;
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
  gap: 0.8333rem;
  min-width: 11.1111rem;
  padding: 1.0417rem;
  border-radius: 0.8333rem;
  border: 1px solid rgba(105, 105, 105, 0.08);
}
:global(.dark) .project-card,
:global(.darkmode) .project-card {
  background-color: rgba(255,255,255,0.04) !important;
  border-color: rgba(255,255,255,0.10);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.20), inset 0 1px 0 rgba(255, 255, 255, 0.06);
}
:global(.dark) .project-card__icon,
:global(.darkmode) .project-card__icon {
  background-color: rgba(255,255,255,0.08);
}
.project-card__icon {
  width: 2.0833rem;
  height: 2.0833rem;
  border-radius: 50%;
  background-color: #e8eef9;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.project-card__icon span {
  font-size: 0.6944rem;
  font-weight: 700;
  color: #4b6fa0;
  line-height: 1;
}

/* ── Revoke button ── */
.revoke-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 2.5rem;
  padding: 0.4167rem 1.1111rem;
  border-radius: 1.25rem;
  background-color: #fff;
  color: rgba(105, 105, 105, 0.7);
  font-size: 0.8333rem;
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

/* ── Modals ── */
.tm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1.3889rem;
}
.tm-box {
  background: #fff;
  border-radius: 1.1111rem;
  padding: 2rem;
  width: 100%;
  max-width: 26rem;
  box-shadow: 0 8px 40px rgba(0,0,0,0.14);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.tm-box--sm { max-width: 22rem; }
.tm-title {
  font-size: 1.1111rem;
  font-weight: 600;
  color: #171717;
  margin: 0;
}
.tm-sub {
  font-size: 0.9028rem;
  color: rgba(105,105,105,0.7);
  margin: 0;
  line-height: 1.4;
}
.tm-input {
  width: 100%;
  height: 3.0556rem;
  padding: 0 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.6944rem;
  font-size: 0.9722rem;
  color: #171717;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.tm-input:focus { border-color: #2563eb; }
.tm-error {
  font-size: 0.8611rem;
  color: #ef4444;
  margin: 0;
}
.tm-checklist {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 16rem;
  overflow-y: auto;
}
.tm-check-item {
  display: flex;
  align-items: center;
  gap: 0.8333rem;
  padding: 0.7778rem 0.8333rem;
  border: 1px solid #f0f0f0;
  border-radius: 0.6944rem;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.tm-check-item:hover { background: #f5f7ff; border-color: #c7d7fc; }
.tm-check-item--selected { background: #eff4ff; border-color: #93b4fd; }
.tm-check-icon {
  width: 1.1111rem;
  height: 1.1111rem;
  border-radius: 0.2778rem;
  border: 1.5px solid #d1d5db;
  background: #fff;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, border-color 0.15s;
}
.tm-check-icon--on { background: #2563eb; border-color: #2563eb; }
.tm-check-label {
  font-size: 0.9722rem;
  color: #374151;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tm-actions {
  display: flex;
  gap: 0.6944rem;
  justify-content: flex-end;
  margin-top: 0.5rem;
}
.tm-btn-cancel {
  padding: 0.6111rem 1.2222rem;
  border-radius: 0.6944rem;
  border: none;
  background: #f5f7f9;
  color: #696969;
  font-size: 0.9028rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.tm-btn-cancel:hover { background: #e9ecf0; }
.tm-btn-primary {
  padding: 0.6111rem 1.2222rem;
  border-radius: 0.6944rem;
  border: none;
  background: #2563eb;
  color: #fff;
  font-size: 0.9028rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.tm-btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.tm-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.tm-btn-danger {
  padding: 0.6111rem 1.2222rem;
  border-radius: 0.6944rem;
  border: none;
  background: #ef4444;
  color: #fff;
  font-size: 0.9028rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.tm-btn-danger:hover:not(:disabled) { background: #dc2626; }
.tm-btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Edit button ── */
.edit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3.1944rem;
  height: 3.1944rem;
  border-radius: 0.2778rem;
  background-color: #f5f7f9;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
  transition: background-color 0.3s;
}
.edit-btn:hover { background-color: #dbeafe; }
.edit-btn:hover svg path { fill: #2563eb; }
.edit-btn svg path { transition: fill 0.2s; }
:global(.dark) .edit-btn,
:global(.darkmode) .edit-btn { background-color: rgba(255,255,255,0.08); }

/* ── Role selector ── */
.tm-role-group { display: flex; flex-direction: column; gap: 0.5rem; }
.tm-role-option {
  display: flex; align-items: center; gap: 0.8333rem;
  padding: 0.8333rem 1rem;
  border: 1px solid #e5e7eb; border-radius: 0.6944rem;
  cursor: pointer; transition: background 0.15s, border-color 0.15s;
}
.tm-role-option:hover { background: #f5f7ff; border-color: #c7d7fc; }
.tm-role-option--active { background: #eff4ff; border-color: #93b4fd; }
.tm-role-radio {
  width: 1rem; height: 1rem; border-radius: 50%;
  border: 2px solid #d1d5db; background: #fff;
  flex-shrink: 0; transition: border-color 0.15s;
}
.tm-role-radio--on { border-color: #2563eb; background: #2563eb;
  box-shadow: inset 0 0 0 2px #fff; }
.tm-role-label { font-size: 0.9722rem; font-weight: 500; color: #374151; line-height: 1.2; }
.tm-role-desc { font-size: 0.8333rem; color: #9ca3af; margin-top: 0.2rem; }

/* ── Member avatar ── */
.member-avatar {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: #e8eef9;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.member-avatar span {
  font-size: 0.8333rem;
  font-weight: 700;
  color: #4b6fa0;
  line-height: 1;
}
</style>
