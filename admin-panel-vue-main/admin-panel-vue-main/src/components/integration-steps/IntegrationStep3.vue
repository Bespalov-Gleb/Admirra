<template>
  <div class="pr-1 pb-4 space-y-6">
    <div class="space-y-4">
      <!-- The Enriched Table Component -->
      <CampaignPowerTable 
        :campaigns="campaigns"
        :selectedIds="selectedIds"
        :loading="loading"
        :currency="currency"
        @toggle="(id) => $emit('toggle', id)"
        @bulkSelect="handleBulkSelect"
        @bulkDeselect="handleBulkDeselect"
      />
    </div>
  </div>
</template>

<script setup>
import { CheckIcon } from '@heroicons/vue/24/outline'
import CampaignPowerTable from './CampaignPowerTable.vue'

const props = defineProps({
  campaigns: Array,
  selectedIds: Array,
  loading: Boolean,
  allFromProfile: Boolean,
  currency: String
})

const emit = defineEmits(['toggleAll', 'toggle', 'bulkSelect', 'bulkDeselect'])

const handleBulkSelect = (ids) => {
  emit('bulkSelect', ids)
}

const handleBulkDeselect = (ids) => {
  emit('bulkDeselect', ids)
}
</script>
