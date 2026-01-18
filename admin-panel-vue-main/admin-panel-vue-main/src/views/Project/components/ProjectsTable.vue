<template>
  <div class="bg-white rounded-[1.5rem] overflow-hidden border border-gray-100 shadow-sm">
    <!-- Toolbar -->
    <div class="px-8 py-4 bg-gradient-to-r from-blue-50/50 to-transparent border-b border-gray-100 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <!-- Search -->
        <div class="relative">
          <input 
            v-model="localSearchQuery"
            type="text" 
            placeholder="Поиск по проектам, номерам или доменам"
            class="w-96 px-4 py-2 pl-10 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
          <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        </div>
      </div>
      
      <div class="flex items-center gap-3">
        <button class="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors flex items-center gap-2">
          <PencilSquareIcon class="w-4 h-4" />
          МАССОВОЕ РЕДАКТИРОВАНИЕ
        </button>
        <button 
          @click="$emit('addProject')"
          class="px-4 py-2 text-sm font-black text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors uppercase tracking-wider"
        >
          ДОБАВИТЬ ПРОЕКТ
        </button>
      </div>
    </div>

    <!-- Table -->
    <div class="overflow-x-auto">
      <table class="w-full text-left border-collapse min-w-[1400px]">
        <thead>
          <tr class="bg-gray-50/50 border-b border-gray-100">
            <th class="w-10 px-4 py-3">
              <div 
                @click="toggleSelectAll"
                class="w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all bg-white cursor-pointer" 
                :class="isAllSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-200 hover:border-blue-400'"
              >
                <CheckIcon v-if="isAllSelected" class="w-3.5 h-3.5 text-white" stroke-width="4" />
                <div v-else-if="selected.length > 0" class="w-2 h-0.5 bg-gray-400 rounded-full"></div>
              </div>
            </th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest">Проект</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest">Интеграции</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Показы</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Клики</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Расходы</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Лиды</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">CPC</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">CPA</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest">Дни получения сделок</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest">Статус</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest">Дата создания</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Действия</th>
          </tr>
        </thead>
        <tbody>
          <!-- Loading State -->
          <template v-if="loading">
            <tr v-for="i in 5" :key="i" class="border-b border-gray-50">
              <td class="px-4 py-4"><div class="w-5 h-5 bg-gray-100 rounded animate-pulse"></div></td>
              <td class="px-3 py-4"><div class="w-32 h-4 bg-gray-100 rounded animate-pulse"></div></td>
              <td class="px-3 py-4"><div class="w-20 h-6 bg-gray-100 rounded-full animate-pulse"></div></td>
              <td class="px-3 py-4"><div class="w-16 h-3 bg-gray-100 rounded animate-pulse ml-auto"></div></td>
              <td class="px-3 py-4"><div class="w-16 h-3 bg-gray-100 rounded animate-pulse ml-auto"></div></td>
              <td class="px-3 py-4"><div class="w-20 h-3 bg-gray-100 rounded animate-pulse ml-auto"></div></td>
              <td class="px-3 py-4"><div class="w-12 h-3 bg-gray-100 rounded animate-pulse ml-auto"></div></td>
              <td class="px-3 py-4"><div class="w-16 h-3 bg-gray-100 rounded animate-pulse ml-auto"></div></td>
              <td class="px-3 py-4"><div class="w-16 h-3 bg-gray-100 rounded animate-pulse ml-auto"></div></td>
              <td class="px-3 py-4"><div class="w-32 h-6 bg-gray-100 rounded animate-pulse"></div></td>
              <td class="px-3 py-4"><div class="w-20 h-6 bg-gray-100 rounded-full animate-pulse"></div></td>
              <td class="px-3 py-4"><div class="w-24 h-3 bg-gray-100 rounded animate-pulse"></div></td>
              <td class="px-3 py-4"><div class="w-20 h-6 bg-gray-100 rounded animate-pulse ml-auto"></div></td>
            </tr>
          </template>
          
          <!-- Projects -->
          <template v-else>
            <tr 
              v-for="project in filteredProjects" 
              :key="project.id"
              class="border-b border-gray-50 last:border-none group hover:bg-blue-50/20 transition-all"
              :class="{ 'bg-blue-50/40': selected.includes(project.id) }"
            >
              <!-- Checkbox -->
              <td class="px-4 py-4">
                <div 
                  @click="toggleSelect(project.id)"
                  class="w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all bg-white cursor-pointer" 
                  :class="selected.includes(project.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-200 group-hover:border-gray-400'"
                >
                  <CheckIcon v-if="selected.includes(project.id)" class="w-3.5 h-3.5 text-white" stroke-width="4" />
                </div>
              </td>

              <!-- Project Name -->
              <td class="px-3 py-4">
                <div class="flex items-center gap-2">
                  <GlobeAltIcon class="w-5 h-5 text-green-500 flex-shrink-0" />
                  <div>
                    <div class="font-medium text-sm text-gray-900">{{ project.title }}</div>
                    <div class="text-xs text-gray-500">ID: {{ project.id.substring(0, 8).toUpperCase() }}</div>
                  </div>
                </div>
              </td>

              <!-- Integrations -->
              <td class="px-3 py-4">
                <div class="flex items-center gap-1 flex-wrap">
                  <div 
                    v-for="(channel, idx) in project.channels" 
                    :key="idx"
                    class="px-2 py-1 rounded text-xs font-medium"
                    :class="getChannelBadgeClass(channel)"
                  >
                    {{ getChannelShortName(channel) }}
                  </div>
                  <span v-if="project.channels.length === 0" class="text-xs text-gray-400">Нет</span>
                </div>
              </td>

              <!-- Impressions (Показы) -->
              <td class="px-3 py-4 text-right">
                <span class="text-sm font-medium text-gray-900">{{ formatNumber(project.impressions || 0) }}</span>
              </td>

              <!-- Clicks (Клики) -->
              <td class="px-3 py-4 text-right">
                <span class="text-sm font-medium text-gray-900">{{ formatNumber(project.clicks || 0) }}</span>
              </td>

              <!-- Expenses (Расходы) -->
              <td class="px-3 py-4 text-right">
                <span class="text-sm font-bold text-gray-900">{{ formatExpenses(project.expenses || 0) }}</span>
              </td>

              <!-- Leads (Лиды) -->
              <td class="px-3 py-4 text-right">
                <span class="text-sm font-medium text-gray-900">{{ formatNumber(project.leads || 0) }}</span>
              </td>

              <!-- CPC -->
              <td class="px-3 py-4 text-right">
                <span class="text-sm text-gray-700">{{ formatExpenses(project.cpc || 0) }}</span>
              </td>

              <!-- CPA -->
              <td class="px-3 py-4 text-right">
                <span class="text-sm text-gray-700">{{ formatExpenses(project.cpa || 0) }}</span>
              </td>

              <!-- Days of Week -->
              <td class="px-3 py-4">
                <div class="flex items-center gap-1">
                  <button 
                    v-for="day in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']" 
                    :key="day"
                    class="w-7 h-7 rounded-lg text-[10px] font-bold flex items-center justify-center transition-all"
                    :class="isActiveDayForProject(project, day) ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-400 hover:bg-gray-200'"
                  >
                    {{ day }}
                  </button>
                  <button class="w-7 h-7 rounded-lg text-[10px] font-bold flex items-center justify-center bg-red-100 text-red-600 hover:bg-red-200 transition-all">
                    Вс
                  </button>
                </div>
              </td>

              <!-- Status -->
              <td class="px-3 py-4">
                <div class="flex items-center gap-2">
                  <div 
                    class="w-2 h-2 rounded-full"
                    :class="project.status === 'active' ? 'bg-green-500' : 'bg-red-500'"
                  ></div>
                  <span 
                    class="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider"
                    :class="project.status === 'active' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'"
                  >
                    {{ project.status === 'active' ? 'Активен' : 'Неактивен' }}
                  </span>
                </div>
              </td>

              <!-- Created Date -->
              <td class="px-3 py-4">
                <span class="text-xs text-gray-500">{{ formatDate(project.created_at) }}</span>
              </td>

              <!-- Actions -->
              <td class="px-3 py-4">
                <div class="flex items-center justify-end gap-1">
                  <button 
                    @click="$emit('viewProject', project.id)"
                    class="w-8 h-8 rounded-lg flex items-center justify-center bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                    title="Просмотр"
                  >
                    <EyeIcon class="w-4 h-4" />
                  </button>
                  <button 
                    @click="$emit('editProject', project.id)"
                    class="w-8 h-8 rounded-lg flex items-center justify-center bg-green-50 text-green-600 hover:bg-green-100 transition-colors"
                    title="Редактировать"
                  >
                    <PencilIcon class="w-4 h-4" />
                  </button>
                  <button 
                    @click="$emit('deleteProject', project.id)"
                    class="w-8 h-8 rounded-lg flex items-center justify-center bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                    title="Удалить"
                  >
                    <TrashIcon class="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          </template>

          <!-- Empty State -->
          <tr v-if="!loading && filteredProjects.length === 0">
            <td colspan="13" class="px-4 py-12 text-center">
              <div class="flex flex-col items-center justify-center gap-3">
                <FolderOpenIcon class="w-12 h-12 text-gray-300" />
                <p class="text-sm text-gray-500 font-medium">Проекты не найдены</p>
                <p class="text-xs text-gray-400">Попробуйте изменить параметры поиска</p>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="!loading && filteredProjects.length > 0" class="px-8 py-4 border-t border-gray-100 flex items-center justify-between">
      <div class="text-sm text-gray-500">
        Элементов на странице: 
        <select 
          v-model="itemsPerPage"
          class="ml-2 px-2 py-1 border border-gray-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option :value="10">10</option>
          <option :value="25">25</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </div>
      
      <div class="text-sm text-gray-700">
        1-{{ Math.min(itemsPerPage, filteredProjects.length) }} из {{ filteredProjects.length }}
      </div>
      
      <div class="flex items-center gap-2">
        <button 
          class="px-3 py-1.5 text-sm border border-gray-200 rounded hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          disabled
        >
          ‹
        </button>
        <button 
          class="px-3 py-1.5 text-sm border border-gray-200 rounded hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          disabled
        >
          ›
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { 
  CheckIcon, 
  MagnifyingGlassIcon, 
  PencilSquareIcon,
  GlobeAltIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon,
  FolderOpenIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  projects: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  searchQuery: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['addProject', 'viewProject', 'editProject', 'deleteProject'])

const selected = ref([])
const localSearchQuery = ref(props.searchQuery)
const itemsPerPage = ref(10)

watch(() => props.searchQuery, (newVal) => {
  localSearchQuery.value = newVal
})

const filteredProjects = computed(() => {
  let result = props.projects

  if (localSearchQuery.value) {
    const query = localSearchQuery.value.toLowerCase()
    result = result.filter(project =>
      project.title?.toLowerCase().includes(query) ||
      project.id?.toLowerCase().includes(query) ||
      project.description?.toLowerCase().includes(query)
    )
  }

  return result
})

const isAllSelected = computed(() => 
  filteredProjects.value.length > 0 && selected.value.length === filteredProjects.value.length
)

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selected.value = []
  } else {
    selected.value = filteredProjects.value.map(p => p.id)
  }
}

const toggleSelect = (id) => {
  const index = selected.value.indexOf(id)
  if (index > -1) {
    selected.value.splice(index, 1)
  } else {
    selected.value.push(id)
  }
}

const getChannelBadgeClass = (channel) => {
  const channelClasses = {
    'Яндекс.Директ': 'bg-red-50 text-red-700 border border-red-200',
    'ВКонтакте': 'bg-blue-50 text-blue-700 border border-blue-200',
    'Google Ads': 'bg-green-50 text-green-700 border border-green-200',
    'Facebook Ads': 'bg-indigo-50 text-indigo-700 border border-indigo-200'
  }
  return channelClasses[channel] || 'bg-gray-50 text-gray-700 border border-gray-200'
}

const getChannelShortName = (channel) => {
  const shortNames = {
    'Яндекс.Директ': 'ЯД',
    'ВКонтакте': 'ВК',
    'Google Ads': 'GA',
    'Facebook Ads': 'FB'
  }
  return shortNames[channel] || channel.substring(0, 2).toUpperCase()
}

const isActiveDayForProject = (project, day) => {
  // Placeholder logic - все дни активны кроме воскресенья
  return day !== 'Вс'
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const formatNumber = (num) => {
  if (!num) return '0'
  return new Intl.NumberFormat('ru-RU').format(num)
}

const formatExpenses = (num) => {
  if (!num) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', { 
    style: 'decimal',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2 
  }).format(num) + ' ₽'
}
</script>

