<template>
  <div class="table-shell">
    <table>
      <thead>
        <tr>
          <th v-for="column in columns" :key="column.key" :class="column.class">
            <button v-if="column.sortable" class="sort-button" @click="$emit('sort', column.key)">
              {{ column.label }} <ArrowsUpDownIcon />
            </button>
            <span v-else>{{ column.label }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="row.id || row.user_id || index">
          <td v-for="column in columns" :key="column.key" :class="column.class">
            <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]">
              {{ row[column.key] ?? '—' }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
    <EmptyState v-if="!rows.length" :title="emptyTitle" :description="emptyDescription" />
    <footer v-if="total > pageSize" class="pagination">
      <span>{{ start }}–{{ end }} из {{ total }}</span>
      <div>
        <button class="icon-button" :disabled="page <= 1" @click="$emit('page', page - 1)"><ChevronLeftIcon /></button>
        <strong>{{ page }} / {{ pages }}</strong>
        <button class="icon-button" :disabled="page >= pages" @click="$emit('page', page + 1)"><ChevronRightIcon /></button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowsUpDownIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/outline'
import EmptyState from './EmptyState.vue'
const props = defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 25 },
  emptyTitle: { type: String, default: 'Ничего не найдено' },
  emptyDescription: { type: String, default: 'Попробуйте изменить параметры поиска.' },
})
defineEmits(['page', 'sort'])
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const start = computed(() => (props.total ? (props.page - 1) * props.pageSize + 1 : 0))
const end = computed(() => Math.min(props.page * props.pageSize, props.total))
</script>
