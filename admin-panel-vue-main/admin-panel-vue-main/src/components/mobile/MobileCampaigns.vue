<template>
  <section class="mw-mobile-campaigns mw-only">
    <header>
      <h2>Рекламные кампании</h2>
      <div>
        <select
          :value="sort"
          aria-label="Сортировка кампаний"
          @change="
            $emit('sort', $event.target.value);
            limit = 4;
            reverse = false;
          "
        >
          <option
            v-for="option in options"
            :value="option.value"
            :key="option.value"
          >
            {{ option.label }}
          </option></select
        ><button
          class="mw-icon"
          :aria-label="reverse ? 'Прямой порядок' : 'Обратный порядок'"
          @click="reverse = !reverse"
        >
          <ArrowsUpDownIcon />
        </button>
      </div>
    </header>
    <article
      v-for="row in ordered.slice(0, limit)"
      :key="row.rowKey"
      :class="{ flagged: row.alertTitle }"
      :style="{
        '--mw-alert-color':
          row.alert?.severity === 'warning' ? '#f59e0b' : '#e5484d',
      }"
    >
      <h3>
        {{ row.name }}
        <span v-if="row.alertTitle" :title="row.alertTitle">⚠</span>
      </h3>
      <div>
        <strong>{{
          sort === "leads" ? row.leads : sort === "cpl" ? row.cpa : row.cost
        }}</strong
        ><span
          :class="
            sort !== 'cost' && trend(row)?.negative
              ? 'bad'
              : sort !== 'cost'
                ? 'good'
                : ''
          "
          >{{ trend(row)?.text }}</span
        >
      </div>
      <p>
        <template v-if="sort === 'cost' || sort === 'alerts'"
          >Лиды {{ row.leads }} · CPA {{ row.cpa }}
          <span :class="row.trendCpa?.negative ? 'bad' : 'good'">{{
            row.trendCpa?.text
          }}</span></template
        ><template v-else
          >Расход {{ row.cost }} ·
          {{
            sort === "leads" ? `CPA ${row.cpa}` : `Лиды ${row.leads}`
          }}</template
        >
      </p>
    </article>
    <p v-if="!ordered.length" class="mw-muted">
      Нет кампаний за выбранный период
    </p>
    <button
      v-if="ordered.length > limit"
      class="mw-button mw-full"
      @click="limit = ordered.length"
    >
      Показать ещё {{ ordered.length - limit }}
    </button>
    <p class="mw-muted">Группы и объявления — в веб-версии на компьютере</p>
  </section>
</template>
<script setup>
import { computed, ref, watch } from "vue";
import { ArrowsUpDownIcon } from "@heroicons/vue/24/outline";
const props = defineProps({
  rows: { type: Array, default: () => [] },
  sort: String,
  options: Array,
});
defineEmits(["sort"]);
const limit = ref(4),
  reverse = ref(false);
const ordered = computed(() =>
  reverse.value ? [...props.rows].reverse() : props.rows,
);
const trend = (row) =>
  props.sort === "leads"
    ? row.trendLeads
    : props.sort === "cpl"
      ? row.trendCpa
      : row.trendCost;
watch(
  () => props.rows,
  () => {
    limit.value = 4;
  },
);
</script>
