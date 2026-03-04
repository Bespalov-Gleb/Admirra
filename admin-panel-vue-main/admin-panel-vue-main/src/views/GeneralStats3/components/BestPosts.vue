<template>
  <div class="bg-white rounded-[32px] p-6 border border-gray-100 shadow-sm">
    <h3 class="text-base font-bold text-gray-900 mb-4">Лучшие посты</h3>
    <div v-if="loading" class="flex gap-4 overflow-x-auto pb-2">
      <div v-for="i in 4" :key="i" class="flex-shrink-0 w-48 h-36 rounded-2xl bg-gray-100 animate-pulse" />
    </div>
    <div v-else-if="posts.length === 0" class="text-center py-8 text-gray-500 text-sm">
      Нет данных за выбранный период
    </div>
    <div v-else class="flex gap-4 overflow-x-auto pb-2 custom-scrollbar">
      <div
        v-for="post in posts"
        :key="post.id"
        class="flex-shrink-0 w-48 rounded-2xl border border-gray-200 overflow-hidden bg-gray-50 hover:shadow-md transition-shadow"
      >
        <div class="h-20 bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center">
          <span class="text-xs font-medium text-gray-500 truncate px-2">{{ post.platform === 'yandex' ? 'Яндекс.Директ' : 'VK Ads' }}</span>
        </div>
        <div class="p-3">
          <p class="text-sm font-semibold text-gray-900 truncate" :title="post.title">{{ post.title }}</p>
          <div class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
            <span>{{ post.impressions?.toLocaleString() }} показов</span>
            <span>{{ post.clicks?.toLocaleString() }} кликов</span>
            <span>CTR {{ post.ctr }}%</span>
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
