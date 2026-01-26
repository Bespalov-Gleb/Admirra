<template>
  <div class="bg-white w-full rounded-[40px] px-6 sm:px-10 py-8 shadow-sm border border-gray-50">
    <div class="flex items-center justify-between mb-8">
      <h3 class="text-xl font-bold text-gray-900">Эффективность продвижения</h3>
    </div>
    
    <!-- Labels Row -->
    <div class="flex justify-between px-4 sm:px-12 mb-2 text-center">
      <div v-for="label in funnelLabels" :key="label.text" class="flex flex-col items-center flex-1">
        <span class="text-sm font-black text-gray-900">{{ label.value }}</span>
        <span class="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">{{ label.text }}</span>
      </div>
    </div>

    <!-- Funnel Chart Area -->
    <div class="relative h-32 mb-10 px-4 sm:px-12">
      <svg viewBox="0 0 1080 120" preserveAspectRatio="none" class="w-full h-full">
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

        <!-- 6. Цена цели -->
        <g transform="translate(1000, 60)">
          <rect x="-40" y="-12" width="80" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[5].value }}</text>
        </g>
      </svg>
    </div>

    <!-- Auto-Goals Table Section -->
    <div class="mt-8">
      <div v-if="loadingAutoGoals" class="text-center py-12">
        <div class="inline-flex items-center gap-3 text-sm text-gray-500">
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
            class="bg-white rounded-xl p-5 border-2 transition-all hover:shadow-lg"
            :class="goal.is_primary ? 'border-blue-300 shadow-md' : 'border-gray-200 hover:border-blue-200'"
          >
            <div class="flex items-start justify-between mb-4">
              <div class="flex-1">
                <h5 class="text-sm font-black text-gray-900 mb-1">
                  {{ formatGoalName(goal.name) }}
                </h5>
                <p class="text-xs text-gray-500">ID: {{ goal.id }}</p>
              </div>
              <button
                v-if="goal.is_primary"
                class="flex-shrink-0 px-3 py-1.5 bg-blue-100 text-blue-700 text-[10px] font-black uppercase rounded-md border border-blue-300 flex items-center gap-1.5"
              >
                <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                ОСНОВНАЯ
              </button>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <span class="text-[10px] font-black text-gray-500 uppercase tracking-wider block mb-1">Конверсия</span>
                <span class="text-xl font-black text-gray-900">{{ (goal.count || 0).toLocaleString() }}</span>
              </div>
              <div>
                <span class="text-[10px] font-black text-gray-500 uppercase tracking-wider block mb-1">Стоимость</span>
                <span class="text-xl font-black text-gray-900">{{ formatMoney(goal.cost || 0) }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Right: Donut Chart -->
        <div class="lg:col-span-1">
          <div class="bg-white rounded-xl p-6 border-2 border-gray-200 shadow-md">
            <h4 class="text-sm font-black text-gray-900 uppercase tracking-wider mb-4">Разбивка по целям</h4>
            <div class="relative w-full aspect-square max-w-[280px] mx-auto mb-4">
              <svg viewBox="0 0 200 200" class="w-full h-full">
                <defs>
                  <filter id="shadow">
                    <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.1"/>
                  </filter>
                </defs>
                <!-- Donut Chart -->
                <g transform="translate(100, 100)">
                  <circle 
                    cx="0" 
                    cy="0" 
                    r="80" 
                    fill="none" 
                    stroke="#e5e7eb" 
                    stroke-width="40"
                  />
                  <circle
                    v-for="(segment, index) in donutSegments"
                    :key="index"
                    cx="0"
                    cy="0"
                    r="80"
                    fill="none"
                    :stroke="segment.color"
                    stroke-width="40"
                    :stroke-dasharray="segment.dashArray"
                    :stroke-dashoffset="segment.dashOffset"
                    :transform="`rotate(${segment.startAngle - 90})`"
                    filter="url(#shadow)"
                  />
                  <!-- Center Text -->
                  <text 
                    x="0" 
                    y="0" 
                    text-anchor="middle" 
                    dominant-baseline="middle" 
                    font-size="24"
                    font-weight="900"
                    fill="#111827"
                  >
                    {{ totalConversions }} шт
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
                <div class="flex items-center gap-2">
                  <div 
                    class="w-3 h-3 rounded-full"
                    :style="{ backgroundColor: donutColors[index % donutColors.length] }"
                  ></div>
                  <span class="text-gray-700 font-medium">{{ formatGoalName(goal.name) }}</span>
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
        <p class="text-sm text-gray-500 font-medium">Нет данных по автоцелям</p>
        <p class="text-xs text-gray-400 mt-2">Настройте интеграции с Яндекс.Метрикой для отображения целевых визитов</p>
      </div>
    </div>

    <!-- Selected Goals Section -->
    <div class="mt-8 border-2 border-red-300 bg-red-50/50 rounded-2xl p-6 shadow-sm">
      <div class="mb-4">
        <h4 class="text-sm font-black text-gray-900 uppercase tracking-wider mb-1">Выбранные цели из настроек</h4>
        <p class="text-xs text-gray-600">Статистика по целям, настроенным в интеграциях проекта</p>
      </div>
      
      <div v-if="loadingGoals" class="text-center py-12">
        <div class="inline-flex items-center gap-3 text-sm text-gray-500">
          <div class="w-5 h-5 border-2 border-red-400 border-t-transparent rounded-full animate-spin"></div>
          <span class="font-medium">Загрузка целей...</span>
        </div>
      </div>
      
      <div v-else-if="selectedGoals.length > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <div 
          v-for="goal in selectedGoals" 
          :key="goal.name"
          class="bg-white rounded-xl p-5 border-2 border-gray-200 shadow-md hover:shadow-lg transition-all hover:border-blue-300"
        >
          <div class="flex items-start justify-between mb-3">
            <h5 class="text-sm font-black text-gray-900 line-clamp-2 flex-1 pr-2">{{ goal.name }}</h5>
            <span 
              v-if="goal.is_primary"
              class="flex-shrink-0 px-2 py-1 bg-blue-100 text-blue-700 text-[9px] font-black uppercase rounded-md border border-blue-300"
            >
              Основная
            </span>
          </div>
          <div class="space-y-2.5">
            <div class="flex items-center justify-between pb-2 border-b border-gray-100">
              <span class="text-[10px] font-black text-gray-500 uppercase tracking-wider">Конверсии</span>
              <span class="text-xl font-black text-gray-900">{{ (goal.count || 0).toLocaleString() }}</span>
            </div>
            <div v-if="goal.trend !== undefined" class="flex items-center justify-between">
              <span class="text-[10px] font-black text-gray-500 uppercase tracking-wider">Тренд</span>
              <span 
                class="text-sm font-black px-2 py-0.5 rounded"
                :class="goal.trend >= 0 ? 'text-green-700 bg-green-50' : 'text-red-700 bg-red-50'"
              >
                {{ goal.trend >= 0 ? '+' : '' }}{{ goal.trend.toFixed(1) }}%
              </span>
            </div>
            <!-- CR calculation would require clicks data from YandexStats, skipped for now -->
          </div>
        </div>
      </div>
      
      <div v-else class="text-center py-12">
        <p class="text-sm text-gray-500 font-medium">Цели не выбраны в настройках интеграций</p>
        <p class="text-xs text-gray-400 mt-2">Настройте цели в разделе интеграций для отображения статистики</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../../../api/axios'

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
  }
})

const isTableVisible = ref(true)
const selectedGoals = ref([])
const autoGoals = ref([]) // Auto-goals from Metrika (target visits)
const loadingGoals = ref(false)
const loadingAutoGoals = ref(false)

const funnelLabels = computed(() => [
  { text: 'Показы', value: (props.summary.impressions || 0).toLocaleString() },
  { text: 'CTR', value: (props.summary.ctr || 0).toFixed(2) + '%' },
  { text: 'Клики', value: (props.summary.clicks || 0).toLocaleString() },
  { text: 'Конверсии, % (CR)', value: (props.summary.cr || 0).toFixed(2) + '%' },
  { text: 'Конверсии', value: (props.summary.leads || 0).toLocaleString() },
  { text: 'Цена цели', value: props.summary.cpa ? formatMoney(props.summary.cpa) : formatMoney(0) }
])

const formatMoney = (val) => {
  return new Intl.NumberFormat('ru-RU', { 
    style: 'currency', 
    currency: props.summary.currency || 'RUB', 
    maximumFractionDigits: 0 
  }).format(val)
}

const formatGoalName = (name) => {
  if (!name) return 'Автоцель'
  return name.startsWith('Автоцель:') ? name : `Автоцель: ${name}`
}

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

// Fetch selected goals for the project from database (no API calls to avoid 429)
const fetchSelectedGoals = async () => {
  if (!props.clientId) {
    selectedGoals.value = []
    return
  }

  loadingGoals.value = true
  try {
    // Get integrations for this client to find selected goals
    const { data: integrations } = await api.get('integrations/', {
      params: { client_id: props.clientId }
    })

    console.log('[PromotionEfficiency] Found integrations:', integrations?.length || 0)

    if (!integrations || integrations.length === 0) {
      selectedGoals.value = []
      return
    }

    // Collect selected goal IDs and primary goal IDs from all integrations
    const selectedGoalIds = new Set()
    const primaryGoalIds = new Set()
    
    integrations.forEach(integration => {
      try {
        // Parse selected_goals (stored as JSON string)
        if (integration.selected_goals) {
          const goals = typeof integration.selected_goals === 'string' 
            ? JSON.parse(integration.selected_goals) 
            : integration.selected_goals
          
          if (Array.isArray(goals)) {
            goals.forEach(goalId => selectedGoalIds.add(String(goalId)))
          }
        }
        
        // Add primary goal
        if (integration.primary_goal_id) {
          primaryGoalIds.add(String(integration.primary_goal_id))
          selectedGoalIds.add(String(integration.primary_goal_id)) // Primary is also selected
        }
      } catch (e) {
        console.warn('[PromotionEfficiency] Failed to parse goals for integration:', integration.id, e)
      }
    })

    // If no goals selected, show empty
    if (selectedGoalIds.size === 0) {
      console.log('[PromotionEfficiency] No goals selected in any integration')
      selectedGoals.value = []
      return
    }

    console.log(`[PromotionEfficiency] Selected goal IDs:`, Array.from(selectedGoalIds))
    console.log(`[PromotionEfficiency] Primary goal IDs:`, Array.from(primaryGoalIds))
    console.log(`[PromotionEfficiency] Integrations with goals:`, integrations.map(i => ({
      id: i.id,
      platform: i.platform,
      selected_goals: i.selected_goals,
      primary_goal_id: i.primary_goal_id
    })))

    // Get date range from summary or use default (last 14 days)
    const endDate = new Date().toISOString().split('T')[0]
    const startDate = new Date(Date.now() - 13 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]

    // CRITICAL: Use /dashboard/goals endpoint which reads from DB only (no API calls to Metrika)
    const { data: allGoalsData } = await api.get('dashboard/goals', {
      params: {
        client_id: props.clientId,
        date_from: startDate,
        date_to: endDate
      }
    })

    console.log(`[PromotionEfficiency] Got ${allGoalsData?.length || 0} goals from DB`)
    console.log(`[PromotionEfficiency] Goals from DB:`, allGoalsData)

    // Filter to show only selected goals and mark primary ones
    const filteredGoals = (allGoalsData || [])
      .filter(goal => {
        // Match by goal ID (as string)
        const goalIdStr = String(goal.id || '')
        const goalNameStr = String(goal.name || '')
        const isSelected = selectedGoalIds.has(goalIdStr) || selectedGoalIds.has(goalNameStr)
        if (!isSelected) {
          console.log(`[PromotionEfficiency] Goal ${goalIdStr} (${goalNameStr}) not in selected list`)
        }
        return isSelected
      })
      .map(goal => ({
        ...goal,
        is_primary: primaryGoalIds.has(String(goal.id)) || primaryGoalIds.has(String(goal.name))
      }))

    console.log(`[PromotionEfficiency] Filtered to ${filteredGoals.length} selected goals`)
    selectedGoals.value = filteredGoals.sort((a, b) => {
      // Primary goals first, then by count
      if (a.is_primary && !b.is_primary) return -1
      if (!a.is_primary && b.is_primary) return 1
      return (b.count || 0) - (a.count || 0)
    })
  } catch (err) {
    console.error('[PromotionEfficiency] Failed to fetch goals:', err)
    selectedGoals.value = []
  } finally {
    loadingGoals.value = false
  }
}

// Fetch auto-goals (target visits from Metrika)
const fetchAutoGoals = async () => {
  if (!props.clientId) {
    autoGoals.value = []
    return
  }

  loadingAutoGoals.value = true
  try {
    // Get date range from summary or use default (last 14 days)
    const endDate = new Date().toISOString().split('T')[0]
    const startDate = new Date(Date.now() - 13 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]

    // Get all goals from Metrika (target visits)
    const { data: allGoalsData } = await api.get('dashboard/goals', {
      params: {
        client_id: props.clientId,
        date_from: startDate,
        date_to: endDate
      }
    })

    console.log(`[PromotionEfficiency] Got ${allGoalsData?.length || 0} auto-goals from Metrika`)

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

const donutColors = ['#4b5563', '#6b7280', '#9ca3af', '#d1d5db', '#e5e7eb', '#f3f4f6']

const donutSegments = computed(() => {
  if (autoGoals.value.length === 0 || totalConversions.value === 0) return []
  
  const circumference = 2 * Math.PI * 80 // radius = 80
  let accumulatedLength = 0
  
  return autoGoals.value.map((goal, index) => {
    const percentage = (goal.count || 0) / totalConversions.value
    const segmentLength = circumference * percentage
    const startAngle = (accumulatedLength / circumference) * 360
    
    const segment = {
      color: donutColors[index % donutColors.length],
      dashArray: `${segmentLength} ${circumference}`,
      dashOffset: -accumulatedLength,
      startAngle: startAngle
    }
    
    accumulatedLength += segmentLength
    return segment
  })
})

// Watch for client_id changes
watch(() => props.clientId, () => {
  fetchSelectedGoals()
  fetchAutoGoals()
}, { immediate: true })

onMounted(() => {
  fetchSelectedGoals()
  fetchAutoGoals()
})
</script>

<style scoped>
.text-nowrap {
  white-space: nowrap;
}
</style>
