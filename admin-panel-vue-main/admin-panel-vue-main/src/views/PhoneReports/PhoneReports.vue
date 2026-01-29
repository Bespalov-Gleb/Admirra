<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Заголовок -->
    <div class="py-5 px-6 sm:px-8 bg-white/60 backdrop-blur-xl rounded-[32px] border border-white/80 shadow-sm transition-all hover:shadow-md">
      <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1 opacity-70">
        Отчёты
      </label>
      <div class="flex items-center gap-3 mt-0.5">
        <div class="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-200 hidden xs:block">
          <DocumentChartBarIcon class="w-4 h-4 text-white" />
        </div>
        <div class="flex flex-col min-w-0 flex-1">
          <h1 class="text-xl sm:text-2xl font-black text-gray-900 tracking-tight truncate">
            Отчёты по качеству трафика
          </h1>
          <div class="flex items-center gap-1.5 mt-0.5">
            <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse flex-shrink-0"></div>
            <p class="text-[9px] font-bold text-gray-400 uppercase tracking-wider truncate">
              Анализ качества трафика для подрядчиков
            </p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <select
            v-model="reportDays"
            class="px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition text-sm bg-white"
          >
            <option value="7">7 дней</option>
            <option value="14">14 дней</option>
            <option value="30">30 дней</option>
          </select>
          <button
            @click="exportReport"
            :disabled="loading"
            class="px-4 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all shadow-sm hover:shadow-md flex items-center gap-2 font-semibold text-sm"
          >
            <ArrowDownTrayIcon class="w-5 h-5" />
            Экспорт Excel
          </button>
        </div>
      </div>
    </div>

    <!-- Общая статистика -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-white rounded-[32px] p-6 border border-gray-100 shadow-sm">
        <p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Всего заявок</p>
        <p class="text-3xl font-black text-gray-900">{{ report?.overall?.total_leads || 0 }}</p>
      </div>
      <div class="bg-white rounded-[32px] p-6 border border-gray-100 shadow-sm">
        <p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Отклонено</p>
        <p class="text-3xl font-black text-red-600">{{ report?.overall?.total_rejected || 0 }}</p>
      </div>
      <div class="bg-white rounded-[32px] p-6 border border-gray-100 shadow-sm">
        <p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">% отклонения</p>
        <p class="text-3xl font-black text-gray-900">{{ report?.overall?.rejection_rate || 0 }}%</p>
      </div>
    </div>

    <!-- Топ худших площадок -->
    <div class="bg-white rounded-[32px] border border-gray-100 shadow-sm overflow-hidden">
      <div class="p-6 border-b border-gray-200">
        <h2 class="text-lg font-bold text-gray-900">Топ-10 худших площадок</h2>
        <p class="text-sm text-gray-500 mt-1">Площадки с наивысшим процентом отклонения</p>
      </div>
      <div v-if="loading" class="p-12 text-center">
        <div class="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
      <div v-else-if="!report?.top_bad_sources?.length" class="p-12 text-center text-gray-500">
        <p>Нет данных</p>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Источник</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Кампания</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Контент</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Всего</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Отклонено</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">% отклонения</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr
              v-for="(source, index) in report.top_bad_sources"
              :key="index"
              class="hover:bg-gray-50 transition-colors"
            >
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {{ source.source || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {{ source.campaign || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {{ source.content || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ source.total_leads }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-red-600 font-semibold">
                {{ source.rejected_leads }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'px-3 py-1 text-xs font-semibold rounded-full',
                    source.rejection_rate > 70 ? 'bg-red-100 text-red-700' :
                    source.rejection_rate > 50 ? 'bg-orange-100 text-orange-700' :
                    'bg-yellow-100 text-yellow-700'
                  ]"
                >
                  {{ source.rejection_rate }}%
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Причины отклонения -->
    <div class="bg-white rounded-[32px] border border-gray-100 shadow-sm p-8">
      <h2 class="text-lg font-bold text-gray-900 mb-6">Топ причин отклонения</h2>
      <div v-if="loading" class="h-64 flex items-center justify-center">
        <div class="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
      <div v-else-if="!report?.rejection_reasons?.length" class="text-center text-gray-500 py-12">
        <p>Нет данных</p>
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="(reason, index) in report.rejection_reasons"
          :key="index"
          class="flex items-center justify-between p-4 bg-gray-50 rounded-xl"
        >
          <span class="text-sm font-medium text-gray-900">{{ reason.reason || reason }}</span>
          <span class="text-sm font-semibold text-gray-600">{{ reason.count || 0 }}</span>
        </div>
      </div>
    </div>

    <!-- Чёрный список -->
    <div class="bg-white rounded-[32px] border border-gray-100 shadow-sm overflow-hidden">
      <div class="p-6 border-b border-gray-200">
        <h2 class="text-lg font-bold text-gray-900">Чёрный список площадок</h2>
        <p class="text-sm text-gray-500 mt-1">Площадки с высоким процентом мусора</p>
      </div>
      <div v-if="loadingBlacklist" class="p-12 text-center">
        <div class="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
      <div v-else-if="!blacklist?.placements?.length" class="p-12 text-center text-gray-500">
        <p>Чёрный список пуст</p>
      </div>
      <div v-else class="p-6">
        <div class="space-y-2">
          <div
            v-for="(placement, index) in blacklist.placements"
            :key="index"
            class="flex items-center justify-between p-3 bg-red-50 rounded-xl border border-red-200"
          >
            <span class="text-sm font-medium text-red-900">
              {{ placement.source }} / {{ placement.campaign }} / {{ placement.content }}
            </span>
            <span class="text-xs text-red-600">{{ placement.reason }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { DocumentChartBarIcon, ArrowDownTrayIcon } from '@heroicons/vue/24/outline'
import api from '@/api/axios'
import { useToaster } from '@/composables/useToaster'

const toaster = useToaster()
const loading = ref(false)
const loadingBlacklist = ref(false)
const reportDays = ref('7')
const report = ref(null)
const blacklist = ref({ placements: [] })

onMounted(async () => {
  await Promise.all([fetchReport(), fetchBlacklist()])
})

watch(reportDays, () => {
  fetchReport()
})

const fetchReport = async () => {
  try {
    loading.value = true
    const response = await api.get('reports/quality', {
      params: { days: reportDays.value }
    })
    report.value = response.data
  } catch (error) {
    console.error('Error fetching report:', error)
    toaster.error('Не удалось загрузить отчёт')
  } finally {
    loading.value = false
  }
}

const fetchBlacklist = async () => {
  try {
    loadingBlacklist.value = true
    const response = await api.get('reports/blacklist')
    blacklist.value = response.data
  } catch (error) {
    console.error('Error fetching blacklist:', error)
  } finally {
    loadingBlacklist.value = false
  }
}

const exportReport = async () => {
  try {
    const response = await api.get('reports/quality', {
      params: { days: reportDays.value, format: 'excel' },
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `quality_report_${new Date().toISOString().split('T')[0]}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    
    toaster.success('Отчёт успешно экспортирован')
  } catch (error) {
    console.error('Error exporting report:', error)
    toaster.error('Не удалось экспортировать отчёт')
  }
}
</script>

