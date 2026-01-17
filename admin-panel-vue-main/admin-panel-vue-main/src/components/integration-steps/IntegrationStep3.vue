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
        @bulkSelect="(ids) => $emit('bulkSelect', ids)"
        @bulkDeselect="(ids) => $emit('bulkDeselect', ids)"
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

defineEmits(['toggleAll', 'toggle', 'bulkSelect', 'bulkDeselect'])
</script>
