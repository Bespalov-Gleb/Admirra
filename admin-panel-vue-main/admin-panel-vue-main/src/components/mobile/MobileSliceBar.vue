<template>
  <div class="mw-slice" :class="{ 'mw-slice--dashboard': dashboard }">
    <template v-if="searchOpen"
      ><input
        ref="searchInput"
        class="mw-search"
        :value="search"
        placeholder="Название, папка или ID"
        aria-label="Поиск проектов"
        @input="$emit('update:search', $event.target.value)" /><button
        class="mw-icon"
        aria-label="Закрыть поиск"
        @click="
          searchOpen = false;
          $emit('update:search', '');
        "
      >
        <XMarkIcon /></button
    ></template>
    <template v-else>
      <button
        class="mw-period-pill"
        :class="{ 'mw-period-pill--net': !vat }"
        @click="sheet = true"
      >
        <span>{{ label }}</span
        ><span class="mw-vat-suffix">· {{ vat ? "с НДС" : "без НДС" }}</span
        ><ChevronDownIcon />
      </button>
      <button
        v-if="dashboard"
        class="mw-icon mw-filter"
        aria-label="Фильтры услуг и кампаний"
        @click="$emit('filters')"
      >
        <FunnelIcon /><i v-if="filtered" />
      </button>
      <template v-else
        ><button
          class="mw-icon"
          aria-label="Обновить данные"
          :disabled="syncing"
          @click="$emit('refresh')"
        >
          <ArrowPathIcon :class="{ 'mw-spin': syncing }" /></button
        ><button
          class="mw-icon"
          aria-label="Поиск проектов"
          @click="showSearch"
        >
          <MagnifyingGlassIcon /></button
      ></template>
    </template>
    <MobilePeriodSheet
      :open="sheet"
      :period="period"
      :range="range"
      :vat="vat"
      :sync-text="syncText"
      @close="sheet = false"
      @period="$emit('period', $event)"
      @range="$emit('range', $event)"
      @update:vat="$emit('update:vat', $event)"
    />
  </div>
</template>
<script setup>
import { computed, ref, nextTick } from "vue";
import {
  ChevronDownIcon,
  FunnelIcon,
  ArrowPathIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import { getProjectPeriodLabel } from "../../utils/projectPeriods";
import MobilePeriodSheet from "./MobilePeriodSheet.vue";
const props = defineProps({
  period: String,
  range: Object,
  vat: Boolean,
  dashboard: Boolean,
  filtered: Boolean,
  search: String,
  syncing: Boolean,
  syncText: String,
});
defineEmits([
  "period",
  "range",
  "update:vat",
  "update:search",
  "refresh",
  "filters",
]);
const sheet = ref(false),
  searchOpen = ref(false),
  searchInput = ref(null);
async function showSearch() {
  searchOpen.value = true;
  await nextTick();
  searchInput.value?.focus();
}
const label = computed(() => {
  if (props.period !== "custom" || !props.range?.start || !props.range?.end)
    return getProjectPeriodLabel(props.period);
  const a = new Date(`${props.range.start}T12:00:00`),
    b = new Date(`${props.range.end}T12:00:00`);
  const fmt = (d) =>
    d
      .toLocaleDateString("ru-RU", { day: "numeric", month: "short" })
      .replace(".", "");
  if (a.getFullYear() !== b.getFullYear())
    return `${a.toLocaleDateString("ru-RU", { year: "2-digit", month: "2-digit", day: "2-digit" })}–${b.toLocaleDateString("ru-RU", { year: "2-digit", month: "2-digit", day: "2-digit" })}`;
  if (a.getMonth() === b.getMonth()) return `${a.getDate()} – ${fmt(b)}`;
  return `${fmt(a)} – ${fmt(b)}`;
});
</script>
