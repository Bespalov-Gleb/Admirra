<template>
  <div class="bg-white rounded-3xl p-6 sm:p-8 border border-gray-100 shadow-md">
    <h3 class="text-xl font-black text-gray-900">Лучшие посты</h3>
    <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mt-1 mb-6">По эффективности за период</p>
    <div v-if="loading" class="flex gap-4 overflow-x-auto pb-2">
      <div v-for="i in 4" :key="i" class="flex-shrink-0 w-56 h-44 rounded-2xl bg-gray-100 animate-pulse" />
    </div>
    <div v-else-if="posts.length === 0" class="text-center py-8 text-gray-500 text-sm">
      Нет данных за выбранный период
    </div>
    <div v-else class="flex gap-5 overflow-x-auto pb-3 custom-scrollbar">
      <div
        v-for="post in posts"
        :key="post.id"
        class="flex-shrink-0 w-60 rounded-2xl overflow-hidden border border-gray-100 hover:shadow-xl hover:scale-[1.02] transition-all duration-300 shadow-md"
      >
        <div class="h-32 bg-gradient-to-br from-blue-600 via-blue-700 to-blue-900 relative flex items-center justify-center overflow-hidden">
          <img v-if="post.image_url" :src="post.image_url" :alt="post.title" class="absolute inset-0 w-full h-full object-cover opacity-80" />
          <div class="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
          <div class="relative z-10 text-center px-3">
            <span class="text-[10px] font-bold text-white/90 uppercase tracking-wider">{{ post.subtitle || (post.platform === 'yandex' ? 'Яндекс.Директ' : 'VK Ads') }}</span>
            <p class="text-sm font-black text-white leading-tight mt-1 line-clamp-2">{{ post.title }}</p>
          </div>
        </div>
        <div class="p-4 bg-white">
          <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs font-medium text-gray-600">
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
  height: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}
</style>
