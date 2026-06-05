<template>
  <div class="bg-white dark:bg-[#2A2D3C] w-full rounded-2xl px-4 sm:px-10 py-6 sm:py-8 shadow-md border border-gray-100 dark:border-white/10">
    <div class="flex items-center justify-between mb-8">
      <h3 class="text-xl font-bold text-gray-900 dark:text-white">Эффективность продвижения</h3>
    </div>
    
    <!-- Labels Row -->
    <div class="grid grid-cols-2 gap-3 px-0 sm:grid-cols-3 lg:grid-cols-6 sm:px-12 mb-4 text-center">
      <div v-for="label in funnelLabels" :key="label.text" class="flex min-w-0 flex-col items-center rounded-lg bg-gray-50 px-2 py-2 dark:bg-white/5 lg:bg-transparent lg:p-0 lg:dark:bg-transparent">
        <span class="max-w-full truncate text-sm font-black text-gray-900 dark:text-gray-100">{{ label.value }}</span>
        <span class="text-[0.6944rem] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-tighter">{{ label.text }}</span>
      </div>
    </div>

    <!-- Funnel Chart Area -->
    <div class="relative h-28 sm:h-32 mb-8 sm:mb-10 px-0 sm:px-12 overflow-x-auto overflow-y-hidden">
      <svg viewBox="0 0 1080 120" preserveAspectRatio="none" class="h-full min-w-[50rem] w-full">
        <defs>
          <filter id="shadow">
            <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.1"/>
          </filter>
        </defs>
        
        <!-- Funnel Polygons -->
        <!-- Stage 1 to 2 -->
        <polygon :points="funnelPoints.stage1" fill="#82d944" />
        <!-- Transition 1 (Trapezoid) -->
        <polygon :points="funnelPoints.trans1" fill="#82d944" opacity="0.9" />
        <!-- Stage 2 to 3 -->
        <polygon :points="funnelPoints.stage2" fill="#82d944" />
        <!-- Transition 2 (Trapezoid) -->
        <polygon :points="funnelPoints.trans2" fill="#82d944" opacity="0.9" />
        <!-- Stage 3 (End) -->
        <polygon :points="funnelPoints.stage3" fill="#82d944" />

        <!-- Metric Badges -->
        <!-- 1. Показы -->
        <g transform="translate(100, 60)">
          <rect x="-40" y="-12" width="80" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[0].value }}</text>
        </g>

        <!-- 2. CTR -->
        <g v-if="funnelLabels[1].value" transform="translate(300, 60)">
          <rect x="-35" y="-12" width="70" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[1].value }}</text>
        </g>
        
        <!-- 3. Клики -->
        <g transform="translate(500, 60)">
          <rect x="-40" y="-12" width="80" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[2].value }}</text>
        </g>

        <!-- 4. Конверсии, % (CR) -->
        <g v-if="funnelLabels[3].value" transform="translate(700, 60)">
          <rect x="-35" y="-12" width="70" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[3].value }}</text>
        </g>

        <!-- 5. Конверсии -->
        <g transform="translate(900, 60)">
          <rect x="-40" y="-12" width="80" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[4].value }}</text>
        </g>

        <!-- 6. Бюджет -->
        <g transform="translate(1000, 60)">
          <rect x="-40" y="-12" width="80" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[5].value }}</text>
        </g>
      </svg>
    </div>

    <!-- Auto-Goals Table Section -->
    <div class="mt-8">
      <div v-if="loadingAutoGoals" class="text-center py-12">
        <div class="inline-flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
          <div class="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
          <span class="font-medium">Загрузка автоцелей...</span>
        </div>
      </div>
      
      <div v-else-if="autoGoals.length > 0" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Left: Goals List -->
        <div class="lg:col-span-2 space-y-4">
          <div 
            v-for="goal in autoGoals" 
            :key="goal.id"
            class="bg-white dark:bg-white/5 rounded-xl p-5 border-2 transition-all hover:shadow-lg"
            :class="goal.is_primary ? 'border-blue-300 dark:border-[#4A7AFF]/60 shadow-md' : 'border-gray-200 dark:border-white/10 hover:border-blue-200 dark:hover:border-[#4A7AFF]/45'"
          >
            <div class="flex flex-wrap items-start justify-between gap-3 mb-4">
              <div class="min-w-0 flex-1">
                <h5 class="text-sm font-black text-gray-900 dark:text-gray-100 mb-1 break-words">
                  {{ formatGoalName(goal.name) }}
                </h5>
                <p class="text-xs text-gray-500 dark:text-gray-400">ID: {{ goal.id }}</p>
              </div>
              <button
                v-if="goal.is_primary"
                class="flex-shrink-0 px-3 py-1.5 bg-blue-100 text-blue-700 text-[0.6944rem] font-black uppercase rounded-md border border-blue-300 flex items-center gap-1.5"
              >
                <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                ОСНОВНАЯ
              </button>
            </div>
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div class="min-w-0">
                <span class="text-[0.6944rem] font-black text-gray-500 dark:text-gray-400 uppercase tracking-wider block mb-1">Конверсия</span>
                <span class="block max-w-full truncate text-xl font-black text-gray-900 dark:text-gray-100">{{ (goal.count || 0).toLocaleString() }}</span>
              </div>
              <div class="min-w-0">
                <span class="text-[0.6944rem] font-black text-gray-500 dark:text-gray-400 uppercase tracking-wider block mb-1">Стоимость</span>
                <span class="block max-w-full truncate text-xl font-black text-gray-900 dark:text-gray-100">{{ formatMoney(goal.cost || 0) }}</span>
              </div>
              <div class="min-w-0">
                <span class="text-[0.6944rem] font-black text-gray-500 dark:text-gray-400 uppercase tracking-wider block mb-1">Стоимость одной</span>
                <span class="block max-w-full truncate text-xl font-black text-gray-900 dark:text-gray-100">{{ formatMoney(calculateCPA(goal)) }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Right: Donut Chart -->
        <div class="lg:col-span-1">
          <div class="bg-white dark:bg-white/5 rounded-xl p-6 border-2 border-gray-200 dark:border-white/10 shadow-md">
            <h4 class="text-sm font-black text-gray-900 dark:text-gray-100 uppercase tracking-wider mb-4">Разбивка по целям</h4>
            <div class="relative w-full aspect-square max-w-[19.4444rem] mx-auto mb-4">
              <svg viewBox="0 0 200 200" class="w-full h-full">
                <!-- Donut Chart -->
                <g transform="translate(100, 100)">
                  <path
                    v-for="(segment, index) in donutSegments"
                    :key="index"
                    :d="segment.path"
                    :fill="segment.color"
                    :stroke="isDark ? '#2A2D3C' : 'white'"
                    stroke-width="2"
                  />
                  <!-- Center Text: используем summary.leads как каноничное значение (синхронизация с KPI) -->
                  <text 
                    x="0" 
                    y="0" 
                    text-anchor="middle" 
                    dominant-baseline="middle" 
                    font-size="24"
                    font-weight="900"
                    :fill="isDark ? '#F9FAFB' : '#111827'"
                  >
                    {{ (props.summary?.leads ?? totalConversions) }} шт
                  </text>
                </g>
              </svg>
            </div>
            <!-- Legend -->
            <div class="space-y-2">
              <div 
                v-for="(goal, index) in autoGoals" 
                :key="goal.id"
                class="flex items-center justify-between text-xs"
              >
                <div class="flex min-w-0 items-center gap-2.5">
                  <div 
                    class="w-3.5 h-3.5 rounded-full shadow-sm border border-white dark:border-[#2A2D3C]"
                    :style="{ backgroundColor: donutColors[index % donutColors.length] }"
                  ></div>
                  <span class="min-w-0 truncate text-gray-800 dark:text-gray-200 font-semibold text-xs">{{ formatGoalName(goal.name) }}</span>
                </div>
                <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div v-else class="text-center py-12">
        <p class="text-sm text-gray-500 dark:text-gray-400 font-medium">Нет данных по автоцелям</p>
        <p class="text-xs text-gray-400 dark:text-gray-500 mt-2">Настройте интеграции с Яндекс.Метрикой для отображения целевых визитов</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../../../api/axios'
import { useTheme } from '../../../composables/useTheme'

const { isDarkMode } = useTheme()
const isDark = computed(() => isDarkMode.value)

const props = defineProps({
  summary: {
    type: Object,
    required: true
  },
  campaigns: {
    type: Array,
    default: () => []
  },
  clientId: {
    type: String,
    default: null
  },
  startDate: {
    type: String,
    default: ''
  },
  endDate: {
    type: String,
    default: ''
  }
})

const isTableVisible = ref(true)
const autoGoals = ref([]) // Auto-goals from Metrika (target visits)
const loadingAutoGoals = ref(false)

const funnelLabels = computed(() => [
  { text: 'Показы', value: (props.summary.impressions || 0).toLocaleString() },
  { text: 'CTR', value: (props.summary.ctr || 0).toFixed(2) + '%' },
  { text: 'Клики', value: (props.summary.clicks || 0).toLocaleString() },
  { text: 'Конверсии, % (CR)', value: (props.summary.cr || 0).toFixed(2) + '%' },
  { text: 'Конверсии', value: (props.summary.leads || 0).toLocaleString() },
  { text: 'Бюджет', value: props.summary.expenses ? formatMoney(props.summary.expenses) + ' P' : '0 P' }
])

const formatMoney = (val) => {
  return new Intl.NumberFormat('ru-RU', { 
    minimumFractionDigits: 0,
    maximumFractionDigits: 0 
  }).format(val || 0)
}

const calculateCPA = (goal) => {
  if (!goal || !goal.count || goal.count === 0 || !goal.cost || goal.cost === 0) {
    return 0
  }
  return goal.cost / goal.count
}

const formatGoalName = (name) => name || 'Цель'

const getCTR = (cmp) => {
  if (!cmp.impressions) return 0
  return (cmp.clicks / cmp.impressions) * 100
}

const getConversionRate = (cmp) => {
  if (!cmp.clicks) return 0
  return (cmp.conversions / cmp.clicks) * 100
}

const needsAttention = (cmp) => {
  const hasSignificantSpend = (cmp.cost || 0) > 1000
  const hasLowCTR = getCTR(cmp) < 1
  const isActive = cmp.state === 'ON'
  return hasSignificantSpend && hasLowCTR && isActive
}

const funnelPoints = computed(() => {
  const h1 = 100 // Height of first stage (highest)
  const h2 = Math.max(80, h1 * 0.8) // Height of second stage
  const h3 = 10 // Height of end line (conversions)
  
  const yCenter = 60
  
  return {
    // Rect for Stage 1 (Impressions)
    stage1: `0,${yCenter - h1/2} 200,${yCenter - h1/2} 200,${yCenter + h1/2} 0,${yCenter + h1/2}`,
    // Trapezoid Transition 1
    trans1: `200,${yCenter - h1/2} 400,${yCenter - h2/2} 400,${yCenter + h2/2} 200,${yCenter + h1/2}`,
    // Rect for Stage 2 (Clicks)
    stage2: `400,${yCenter - h2/2} 600,${yCenter - h2/2} 600,${yCenter + h2/2} 400,${yCenter + h2/2}`,
    // Trapezoid Transition 2
    trans2: `600,${yCenter - h2/2} 800,${yCenter - h3/2} 800,${yCenter + h3/2} 600,${yCenter + h2/2}`,
    // Rect for Stage 3 (Conversions)
    stage3: `800,${yCenter - h3/2} 1000,${yCenter - h3/2} 1000,${yCenter + h3/2} 800,${yCenter + h3/2}`
  }
})


// Fetch auto-goals (target visits from Metrika)
const fetchAutoGoals = async () => {
  if (!props.clientId) {
    autoGoals.value = []
    return
  }

  // Use provided dates or default to last 14 days
  let startDate = props.startDate
  let endDate = props.endDate
  
  if (!startDate || !endDate) {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - 13)
    startDate = start.toISOString().split('T')[0]
    endDate = end.toISOString().split('T')[0]
  }

  loadingAutoGoals.value = true
  try {
    // Calculate date range for fetching (3 months back from endDate to ensure we have enough data for filtering)
    const fetchEndDate = new Date(endDate)
    const fetchStartDate = new Date(fetchEndDate)
    fetchStartDate.setMonth(fetchStartDate.getMonth() - 3) // 3 months back
    
    const fetchStartDateStr = fetchStartDate.toISOString().split('T')[0]
    const fetchEndDateStr = fetchEndDate.toISOString().split('T')[0]

    // Get all goals from Metrika (target visits) - fetch 3 months of data for caching
    // But request data for the selected period to get correct aggregated totals
    const doFetch = async () => {
      const { data } = await api.get('dashboard/goals', {
        params: { client_id: props.clientId, date_from: startDate, date_to: endDate }
      })
      return data
    }

    let allGoalsData = await doFetch()

    // Retry after 20s if empty — sync может ещё выполняться или был запущен по требованию
    if ((!allGoalsData || allGoalsData.length === 0) && props.clientId) {
      setTimeout(async () => {
        if (!props.clientId || props.startDate !== startDate || props.endDate !== endDate) return
        const retryData = await doFetch()
        if (retryData && retryData.length > 0) {
          const { data: integrations } = await api.get('integrations/', { params: { client_id: props.clientId } })
          const primaryGoalIds = new Set()
          integrations?.forEach(i => { if (i.primary_goal_id) primaryGoalIds.add(String(i.primary_goal_id)) })
          autoGoals.value = retryData.map(g => ({ ...g, is_primary: primaryGoalIds.has(String(g.id)) }))
            .sort((a, b) => (a.is_primary && !b.is_primary ? -1 : !a.is_primary && b.is_primary ? 1 : (b.count || 0) - (a.count || 0)))
        }
      }, 20000)
    }

    console.log(`[PromotionEfficiency] Got ${allGoalsData?.length || 0} auto-goals from Metrika for period ${startDate} to ${endDate}`)

    // Get integrations to find primary goals
    const { data: integrations } = await api.get('integrations/', {
      params: { client_id: props.clientId }
    })

    const primaryGoalIds = new Set()
    integrations?.forEach(integration => {
      if (integration.primary_goal_id) {
        primaryGoalIds.add(String(integration.primary_goal_id))
      }
    })

    // Map goals and mark primary ones
    autoGoals.value = (allGoalsData || []).map(goal => ({
      ...goal,
      is_primary: primaryGoalIds.has(String(goal.id))
    })).sort((a, b) => {
      // Primary goals first, then by count
      if (a.is_primary && !b.is_primary) return -1
      if (!a.is_primary && b.is_primary) return 1
      return (b.count || 0) - (a.count || 0)
    })
  } catch (err) {
    console.error('[PromotionEfficiency] Failed to fetch auto-goals:', err)
    autoGoals.value = []
  } finally {
    loadingAutoGoals.value = false
  }
}

// Computed properties for donut chart
const totalConversions = computed(() => {
  return autoGoals.value.reduce((sum, goal) => sum + (goal.count || 0), 0)
})

// Яркая разноцветная палитра для donut chart
const donutColors = [
  '#3b82f6', // Синий
  '#10b981', // Зеленый
  '#f59e0b', // Оранжевый
  '#ef4444', // Красный
  '#8b5cf6', // Фиолетовый
  '#ec4899', // Розовый
  '#06b6d4', // Голубой
  '#84cc16', // Лайм
  '#f97316', // Оранжево-красный
  '#6366f1'  // Индиго
]

// Функция для создания path сегмента donut chart
const createDonutSegment = (startAngle, endAngle, outerRadius, innerRadius) => {
  const startAngleRad = (startAngle - 90) * (Math.PI / 180)
  const endAngleRad = (endAngle - 90) * (Math.PI / 180)
  
  const x1 = outerRadius * Math.cos(startAngleRad)
  const y1 = outerRadius * Math.sin(startAngleRad)
  const x2 = outerRadius * Math.cos(endAngleRad)
  const y2 = outerRadius * Math.sin(endAngleRad)
  
  const x3 = innerRadius * Math.cos(endAngleRad)
  const y3 = innerRadius * Math.sin(endAngleRad)
  const x4 = innerRadius * Math.cos(startAngleRad)
  const y4 = innerRadius * Math.sin(startAngleRad)
  
  const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0
  
  return `M ${x1} ${y1} A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${x4} ${y4} Z`
}

const donutSegments = computed(() => {
  if (autoGoals.value.length === 0 || totalConversions.value === 0) return []
  
  const outerRadius = 80
  const innerRadius = 62 // Внутренний радиус для donut
  const gapAngle = 2 // Угол пробела между сегментами в градусах
  
  let currentAngle = 0
  
  return autoGoals.value.map((goal, index) => {
    const percentage = (goal.count || 0) / totalConversions.value
    const segmentAngle = (360 - (gapAngle * autoGoals.value.length)) * percentage
    const startAngle = currentAngle
    const endAngle = currentAngle + segmentAngle
    
    const segment = {
      color: donutColors[index % donutColors.length],
      path: createDonutSegment(startAngle, endAngle, outerRadius, innerRadius),
      startAngle: startAngle,
      endAngle: endAngle
    }
    
    currentAngle = endAngle + gapAngle
    return segment
  })
})

// Watch for client_id changes
watch(() => props.clientId, () => {
  fetchAutoGoals()
}, { immediate: true })

// Watch for date changes to reload goals when period changes
watch([() => props.startDate, () => props.endDate], () => {
  if (props.clientId && props.startDate && props.endDate) {
    fetchAutoGoals()
  }
})

onMounted(() => {
  fetchAutoGoals()
})
</script>

<style scoped>
.text-nowrap {
  white-space: nowrap;
}
</style>
