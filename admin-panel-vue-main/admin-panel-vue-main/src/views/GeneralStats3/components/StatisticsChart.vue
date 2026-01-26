<template>
  <div class="!bg-white w-full rounded-[40px] px-6 sm:px-10 py-6 sm:py-8 shadow-sm border border-gray-50">
    <!-- Заголовок -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-10">
      <h3 class="text-xl font-bold text-gray-900">Эффективность кампаний</h3>
    </div>
    
    <div class="h-80 relative pb-10 w-full overflow-hidden">
      <Line
        :data="chartData"
        :options="chartOptions"
        :key="chartKey"
      />
    </div>
    
    <!-- Легенда -->
    <div class="flex items-center gap-6 flex-wrap justify-center sm:justify-start">
      <template v-for="dataset in allDatasets" :key="dataset.key">
        <div 
          v-if="selectedMetrics.length === 0 || selectedMetrics.includes(dataset.key)"
          class="flex items-center gap-2"
        >
          <div :style="{ backgroundColor: dataset.borderColor }" class="w-2.5 h-2.5 rounded-full"></div>
          <span class="text-sm font-bold text-gray-500">{{ dataset.label }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { 
  CalendarIcon
} from '@heroicons/vue/24/outline'
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import calendarIcon from '../../../assets/dash/calendar.svg'

const props = defineProps({
  dynamics: {
    type: Object,
    required: true,
    default: () => ({
      labels: [],
      costs: [],
      clicks: [],
      impressions: [],
      leads: [],
      cpc: [],
      cpa: []
    })
  },
  selectedMetrics: {
    type: Array,
    default: () => [] // Array of selected metric keys: ['expenses', 'impressions', etc.]
  },
  period: {
    type: [String, Number],
    default: 7
  }
})

const emit = defineEmits(['update:period'])

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  Tooltip,
  Legend,
  Filler
)

const isMobile = ref(window.innerWidth < 640)
const chartKey = ref(0)
const selectedDays = computed({
  get: () => Number(props.period) || 7,
  set: (val) => emit('update:period', val)
})

// Helper to prepare data - use real values without normalization
const prepareDataset = (data, label) => {
  const cleanData = Array.isArray(data) ? data.map(v => Number(v) || 0) : []
  
  if (cleanData.length === 0) return []
  
  return cleanData.map((val, index) => ({
    x: props.dynamics.labels[index],
    y: val, // Use real value directly
    realValue: val
  }))
}

// Helper to calculate max value for a specific dataset
const getDatasetMax = (data) => {
  if (!data || data.length === 0) return 100
  const max = Math.max(...data.map(p => p.y || 0))
  return max > 0 ? max * 1.1 : 100
}

// Compute all datasets from props with individual Y-axes
const allDatasets = computed(() => {
  if (!props.dynamics || !props.dynamics.labels) return []

  const d = props.dynamics
  
  const datasets = [
    {
      label: 'Расход',
      key: 'expenses',
      data: prepareDataset(d.costs, 'Расход'),
      yAxisID: 'y-expenses', // Assign to specific Y-axis
      borderColor: '#f97316', // Orange - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 5 : 6,
      pointBackgroundColor: '#f97316',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 2 : 2.5,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    },
    {
      label: 'Показы',
      key: 'impressions',
      data: prepareDataset(d.impressions, 'Показы'),
      yAxisID: 'y-impressions', // Assign to specific Y-axis
      borderColor: '#3b82f6', // Blue - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#3b82f6',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    },
    {
      label: 'Переходы',
      key: 'clicks',
      data: prepareDataset(d.clicks, 'Переходы'),
      yAxisID: 'y-clicks', // Assign to specific Y-axis
      borderColor: '#22c55e', // Green - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#22c55e',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    },
    {
      label: 'Лиды',
      key: 'leads',
      data: prepareDataset(d.leads, 'Лиды'),
      yAxisID: 'y-leads', // Assign to specific Y-axis
      borderColor: '#ef4444', // Red - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#ef4444',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    },
    {
      label: 'CPC',
      key: 'cpc',
      data: prepareDataset(d.cpc, 'CPC'),
      yAxisID: 'y-cpc', // Assign to specific Y-axis
      borderColor: '#a855f7', // Purple - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#a855f7',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    },
    {
      label: 'CPA',
      key: 'cpa',
      data: prepareDataset(d.cpa, 'CPA'),
      yAxisID: 'y-cpa', // Assign to specific Y-axis
      borderColor: '#ec4899', // Pink - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#ec4899',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    }
  ]
  
  // Store max values for each dataset
  datasets.forEach(dataset => {
    dataset._maxValue = getDatasetMax(dataset.data)
  })
  
  return datasets
})

const chartData = computed(() => ({
  labels: props.dynamics.labels || [],
  datasets: props.selectedMetrics.length > 0
    ? allDatasets.value.filter(dataset => props.selectedMetrics.includes(dataset.key))
    : allDatasets.value
}))

// Helper to get max value for a specific axis based on visible datasets
const getAxisMax = (axisId) => {
  const visibleDatasets = props.selectedMetrics.length > 0
    ? allDatasets.value.filter(dataset => props.selectedMetrics.includes(dataset.key))
    : allDatasets.value
  
  // Find dataset(s) using this axis
  const datasetsForAxis = visibleDatasets.filter(d => d.yAxisID === axisId)
  
  if (datasetsForAxis.length === 0) return 100
  
  // Get max value from all datasets using this axis
  let max = 0
  datasetsForAxis.forEach(dataset => {
    dataset.data.forEach(point => {
      const value = point.y || 0
      if (value > max) max = value
    })
  })
  
  return max > 0 ? max * 1.1 : 100
}

const handleResize = () => {
  isMobile.value = window.innerWidth < 640
  chartKey.value++
}

watch(() => props.dynamics, () => {
  chartKey.value++
}, { deep: true })

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

// Calculate number of visible metrics
const visibleMetricsCount = computed(() => {
  if (props.selectedMetrics.length === 0) {
    return allDatasets.value.length
  }
  return props.selectedMetrics.length
})

// Get visible datasets in order
const visibleDatasets = computed(() => {
  if (props.selectedMetrics.length === 0) {
    return allDatasets.value
  }
  return allDatasets.value.filter(dataset => props.selectedMetrics.includes(dataset.key))
})

// Determine which axes to show based on count
const shouldShowAxis = (axisId) => {
  const count = visibleMetricsCount.value
  
  if (count === 0) return false
  if (count === 1) {
    // Show only the first metric's axis (regardless of left/right position)
    const firstDataset = visibleDatasets.value[0]
    return firstDataset && firstDataset.yAxisID === axisId
  }
  if (count === 2) {
    // Show first metric's axis on left, second on right
    const firstDataset = visibleDatasets.value[0]
    const secondDataset = visibleDatasets.value[1]
    if (firstDataset && firstDataset.yAxisID === axisId) return true
    if (secondDataset && secondDataset.yAxisID === axisId) return true
    return false
  }
  // 3+ metrics: hide all axes
  return false
}

const chartOptions = computed(() => {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    animation: {
      duration: 0 // Disable animation for immediate rendering
    },
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        enabled: true,
        mode: 'index',
        intersect: false,
        usePointStyle: true,
        boxWidth: 12,
        boxHeight: 12,
        boxPadding: 8,
        padding: 16,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#ffffff',
        bodyColor: '#ffffff',
        borderColor: 'transparent',
        borderWidth: 0,
        cornerRadius: 10,
        displayColors: true,
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            // Use the actual y value (which is now the real value)
            const realValue = context.parsed.y !== undefined ? context.parsed.y : (context.raw.realValue || context.raw.y || 0);
            if (realValue !== undefined && realValue !== null) {
               if (['Расход', 'CPC', 'CPA'].includes(context.dataset.label)) {
                label += new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(realValue);
              } else {
                label += new Intl.NumberFormat('ru-RU').format(Math.round(realValue));
              }
            }
            return label;
          }
        }
      }
    },
    scales: {
      // Individual Y-axes for each metric to allow independent scaling
      'y-expenses': {
        type: 'linear',
        position: 'left',
        beginAtZero: true,
        max: getAxisMax('y-expenses'),
        ticks: {
          display: shouldShowAxis('y-expenses'),
          font: { size: isMobile.value ? 9 : 11 },
          color: '#f97316', // Match color to dataset
          callback: function(value) {
            if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
            if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
            return value;
          }
        },
        grid: { 
          color: '#e5e7eb',
          display: shouldShowAxis('y-expenses'),
          drawBorder: false,
          lineWidth: 1
        }
      },
      'y-impressions': {
        type: 'linear',
        position: 'right',
        beginAtZero: true,
        max: getAxisMax('y-impressions'),
        ticks: {
          display: shouldShowAxis('y-impressions'),
          font: { size: isMobile.value ? 9 : 11 },
          color: '#3b82f6',
          callback: function(value) {
            if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
            if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
            return value;
          }
        },
        grid: { 
          display: shouldShowAxis('y-impressions'),
          color: '#e5e7eb',
          drawBorder: false,
          lineWidth: 1
        }
      },
      'y-clicks': {
        type: 'linear',
        position: 'left',
        beginAtZero: true,
        max: getAxisMax('y-clicks'),
        ticks: {
          display: shouldShowAxis('y-clicks'),
          font: { size: isMobile.value ? 9 : 11 },
          color: '#22c55e',
          callback: function(value) {
            if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
            if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
            return value;
          }
        },
        grid: { 
          display: shouldShowAxis('y-clicks'),
          color: '#e5e7eb',
          drawBorder: false,
          lineWidth: 1
        }
      },
      'y-leads': {
        type: 'linear',
        position: 'right',
        beginAtZero: true,
        max: getAxisMax('y-leads'),
        ticks: {
          display: shouldShowAxis('y-leads'),
          font: { size: isMobile.value ? 9 : 11 },
          color: '#ef4444',
          callback: function(value) {
            if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
            if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
            return value;
          }
        },
        grid: { 
          display: shouldShowAxis('y-leads'),
          color: '#e5e7eb',
          drawBorder: false,
          lineWidth: 1
        }
      },
      'y-cpc': {
        type: 'linear',
        position: 'left',
        beginAtZero: true,
        max: getAxisMax('y-cpc'),
        ticks: {
          display: shouldShowAxis('y-cpc'),
          font: { size: isMobile.value ? 9 : 11 },
          color: '#a855f7',
          callback: function(value) {
            if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
            if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
            return value;
          }
        },
        grid: { 
          display: shouldShowAxis('y-cpc'),
          color: '#e5e7eb',
          drawBorder: false,
          lineWidth: 1
        }
      },
      'y-cpa': {
        type: 'linear',
        position: 'right',
        beginAtZero: true,
        max: getAxisMax('y-cpa'),
        ticks: {
          display: shouldShowAxis('y-cpa'),
          font: { size: isMobile.value ? 9 : 11 },
          color: '#ec4899',
          callback: function(value) {
            if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
            if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
            return value;
          }
        },
        grid: { 
          display: shouldShowAxis('y-cpa'),
          color: '#e5e7eb',
          drawBorder: false,
          lineWidth: 1
        }
      },
      x: {
        grid: {
          display: false
        },
        ticks: {
          display: true,
          font: {
            size: isMobile.value ? 9 : 11
          },
          color: '#6b7280',
          maxRotation: 0,
          minRotation: 0
        }
      }
    }
  }
})

</script>

<style>
/* Custom Tooltip Styles */
.chartjs-tooltip-key {
  border-radius: 50% !important;
  width: 12px !important;
  height: 12px !important;
}
</style>
