<template>
  <MobileSheet
    :open="open"
    :title="calendar ? 'Указать период' : 'Период и суммы'"
    :back="calendar"
    @back="calendar = false"
    @close="$emit('close')"
  >
    <template v-if="!calendar">
      <p class="mw-muted">Календарные периоды</p>
      <div class="mw-presets">
        <button
          v-for="option in calendarPresets"
          :key="option.value"
          :class="{ selected: period === option.value }"
          @click="choose(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
      <p class="mw-muted">От сегодня назад</p>
      <div class="mw-presets">
        <button
          v-for="option in rollingPresets"
          :key="option.value"
          :class="{ selected: period === option.value }"
          @click="choose(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
      <button
        class="mw-button mw-full"
        :class="{ selected: period === 'custom' }"
        @click="openCalendar"
      >
        <CalendarDaysIcon />Указать период<ChevronRightIcon />
      </button>
      <label class="mw-vat"
        ><span>Цены с НДС 22%</span
        ><input
          type="checkbox"
          :checked="vat"
          @change="$emit('update:vat', $event.target.checked)"
      /></label>
      <p v-if="syncText" class="mw-muted">{{ syncText }}</p>
    </template>
    <template v-else>
      <div class="mw-calendar-nav">
        <button class="mw-icon" aria-label="Предыдущий месяц" @click="move(-1)">
          <ChevronLeftIcon /></button
        ><strong>{{ monthLabel }}</strong
        ><button class="mw-icon" aria-label="Следующий месяц" @click="move(1)">
          <ChevronRightIcon />
        </button>
      </div>
      <div
        class="mw-calendar"
        @touchstart.passive="swipeX = $event.changedTouches[0].clientX"
        @touchend.passive="swipe($event)"
      >
        <span
          v-for="day in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']"
          :key="day"
          class="mw-weekday"
          >{{ day }}</span
        >
        <button
          v-for="day in days"
          :key="day.iso"
          :aria-label="day.label"
          :aria-pressed="day.iso === start || day.iso === end"
          :class="{
            outside: day.outside,
            endpoint: day.iso === start || day.iso === end,
            between: start && end && day.iso > start && day.iso < end,
          }"
          @click="pick(day)"
        >
          {{ day.number }}
        </button>
      </div>
      <p class="mw-calendar-selection">
        {{ start ? dateLabel(start) : "Выберите начало периода"
        }}<template v-if="end">
          — {{ dateLabel(end) }}
          <span class="mw-muted">· {{ dayCount }} дн.</span></template
        ><template v-else-if="start"> — выберите конец</template>
      </p>
      <div class="mw-sheet-actions">
        <button
          class="mw-button"
          @click="
            start = '';
            end = '';
          "
        >
          Сбросить</button
        ><button
          class="mw-button mw-primary"
          :disabled="!start || !end"
          @click="apply"
        >
          Применить
        </button>
      </div>
    </template>
  </MobileSheet>
</template>
<script setup>
import { computed, ref, watch } from "vue";
import {
  CalendarDaysIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from "@heroicons/vue/24/outline";
import MobileSheet from "./MobileSheet.vue";
import {
  selectableProjectPeriodOptions,
  getProjectPeriodRange,
} from "../../utils/projectPeriods";
const props = defineProps({
  open: Boolean,
  period: String,
  range: Object,
  vat: Boolean,
  syncText: String,
});
const emit = defineEmits(["close", "period", "range", "update:vat"]);
const calendar = ref(false),
  start = ref(""),
  end = ref(""),
  month = ref(new Date()),
  swipeX = ref(0);
const calendarPresets = [
  "today",
  "yesterday",
  "this_week",
  "last_week",
  "this_month",
  "last_month",
].map((key) => selectableProjectPeriodOptions.find((o) => o.value === key));
const rollingPresets = selectableProjectPeriodOptions.filter(
  (o) => o.value.startsWith("last_") && o.value.endsWith("_days"),
);
watch(
  () => props.open,
  () => {
    calendar.value = false;
  },
);
const iso = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const dateLabel = (s) => new Date(`${s}T12:00:00`).toLocaleDateString("ru-RU");
const monthLabel = computed(() =>
  month.value.toLocaleDateString("ru-RU", { month: "long", year: "numeric" }),
);
const dayCount = computed(
  () =>
    Math.round(
      (new Date(`${end.value}T12:00:00`) -
        new Date(`${start.value}T12:00:00`)) /
        86400000,
    ) + 1,
);
const days = computed(() => {
  const first = new Date(
    month.value.getFullYear(),
    month.value.getMonth(),
    1,
    12,
  );
  first.setDate(first.getDate() - ((first.getDay() + 6) % 7));
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(first);
    d.setDate(d.getDate() + i);
    return {
      iso: iso(d),
      number: d.getDate(),
      outside: d.getMonth() !== month.value.getMonth(),
      label: d.toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "long",
        year: "numeric",
      }),
      date: d,
    };
  });
});
function choose(key) {
  emit("period", key);
  emit("close");
}
function openCalendar() {
  const range = getProjectPeriodRange(props.period, props.range);
  start.value = range.startDate;
  end.value = range.endDate;
  month.value = new Date(`${start.value}T12:00:00`);
  calendar.value = true;
}
function move(delta) {
  month.value = new Date(
    month.value.getFullYear(),
    month.value.getMonth() + delta,
    1,
    12,
  );
}
function swipe(e) {
  const dx = e.changedTouches[0].clientX - swipeX.value;
  if (Math.abs(dx) > 60) move(dx > 0 ? -1 : 1);
}
function pick(day) {
  if (!start.value || end.value) {
    start.value = day.iso;
    end.value = "";
  } else if (day.iso < start.value) {
    end.value = start.value;
    start.value = day.iso;
  } else end.value = day.iso;
  if (day.outside) month.value = day.date;
}
function apply() {
  emit("range", { start: start.value, end: end.value });
  emit("close");
}
</script>
