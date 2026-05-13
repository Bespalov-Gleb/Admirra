<template>
  <div class="bg-white dark:bg-[#2A2D3C] rounded-2xl p-6 sm:p-8 border border-gray-100 dark:border-white/10 shadow-md">
    <h3 class="text-[1.3889rem] font-medium text-[#5F5F5F] dark:text-white mb-1" style="font-family: Inter, sans-serif;">Лучшие посты</h3>
    <p class="text-[1.0417rem] font-normal text-[#ABABAB] dark:text-gray-500 mb-6" style="font-family: 'Open Sans', sans-serif;">По эффективности за период</p>
    <div v-if="loading" class="flex gap-5 overflow-x-auto pb-2">
      <div v-for="i in 4" :key="i" class="flex-shrink-0 w-[min(20rem,82vw)] h-56 rounded-2xl bg-gray-100 dark:bg-white/10 animate-pulse" />
    </div>
    <div v-else-if="posts.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
      Нет данных за выбранный период
    </div>
    <div v-else class="flex gap-6 overflow-x-auto pb-3 custom-scrollbar">
      <div
        v-for="post in posts"
        :key="post.id"
        class="flex-shrink-0 w-[min(20rem,82vw)] rounded-2xl overflow-hidden border border-gray-100 dark:border-white/10 bg-white dark:bg-white/5 hover:shadow-xl hover:scale-[1.02] transition-all duration-300 shadow-md"
      >
        <div class="h-44 bg-gradient-to-br from-blue-600 via-blue-700 to-blue-900 relative flex items-center justify-center overflow-hidden">
          <img v-if="post.image_url" :src="post.image_url" :alt="post.title" class="absolute inset-0 w-full h-full object-cover opacity-80" />
          <div class="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
          <div class="relative z-10 text-center px-4">
            <span class="text-xs font-bold text-white/90 uppercase tracking-wider">{{ post.subtitle || (post.platform === 'yandex' ? 'Яндекс.Директ' : 'VK Ads') }}</span>
            <p class="text-base font-black text-white leading-tight mt-1.5 line-clamp-2">{{ post.title }}</p>
          </div>
        </div>
        <div class="p-5 bg-white dark:bg-transparent">
          <div class="flex flex-wrap gap-x-4 gap-y-1.5 text-sm font-medium text-gray-600 dark:text-gray-300">
            <span>{{ post.impressions?.toLocaleString() }} показов</span>
            <span>{{ post.clicks?.toLocaleString() }} кликов</span>
            <span>CTR {{ post.ctr ?? '—' }}%</span>
            <span>{{ post.cost?.toLocaleString() }} ₽</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import api from '../../../api/axios'

const props = defineProps({
  clientId: { type: String, default: '' },
  startDate: { type: String, required: true },
  endDate: { type: String, required: true },
  platform: { type: String, default: 'all' },
  campaignIds: { type: Array, default: () => [] },
  goalActionIds: { type: Array, default: () => [] }
})

const posts = ref([])
const loading = ref(false)

const fetchPosts = async () => {
  loading.value = true
  try {
    const params = {
      start_date: props.startDate,
      end_date: props.endDate,
      platform: props.platform
    }
    if (props.clientId) params.client_id = props.clientId
    if (props.campaignIds?.length) params.campaign_ids = props.campaignIds
    if (props.goalActionIds?.length) params.goal_action_ids = props.goalActionIds
    const { data } = await api.get('dashboard/top-ads', { params })
    posts.value = data || []
  } catch {
    posts.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.clientId, props.startDate, props.endDate, props.platform, props.campaignIds, props.goalActionIds],
  fetchPosts,
  { immediate: true }
)
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  height: 0.2778rem;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 0.2778rem;
}
</style>
