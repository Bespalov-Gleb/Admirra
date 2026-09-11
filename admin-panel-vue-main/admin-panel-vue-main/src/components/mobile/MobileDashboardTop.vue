<template>
  <div class="mw-dashboard-top mw-only">
    <div class="mw-project-heading">
      <img v-if="avatar" :src="avatar" alt="" /><span
        v-else
        class="mw-project-mark"
        >{{ title.slice(0, 2) }}</span
      ><button @click="projectMenu = true">
        <strong>{{ title }} <ChevronDownIcon /></strong
        ><small>{{ syncText }}</small></button
      ><button
        v-if="alertCount"
        class="mw-icon mw-heading-alert"
        :aria-label="`${alertCount} отклонений`"
        @click="$emit('detector')"
      >
        <ExclamationTriangleIcon /><b>{{ alertCount }}</b>
      </button>
    </div>
    <div ref="sentinel" class="mw-title-sentinel" />
    <div class="mw-view-row">
      <div role="tablist" aria-label="Вид отчёта">
        <button
          v-for="tab in [
            { key: 'report', label: 'Отчёт' },
            { key: 'dynamics', label: 'Динамика' },
          ]"
          :key="tab.key"
          role="tab"
          :aria-selected="view === tab.key"
          :class="{ selected: view === tab.key }"
          @click="$emit('update:view', tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>
      <button class="mw-button" :disabled="syncing" @click="$emit('refresh')">
        <ArrowPathIcon :class="{ 'mw-spin': syncing }" />Обновить
      </button>
    </div>
    <div class="mw-dash-balances">
      <b>Баланс</b
      ><span v-for="channel in channels" :key="channel.key"
        ><img :src="channel.asset" :alt="channel.key" />{{
          channel.balance
        }}</span
      ><button
        class="mw-icon"
        aria-label="Подключить кабинет"
        @click="$emit('connect')"
      >
        <PlusIcon />
      </button>
    </div>
    <div class="mw-sheet-actions">
      <button class="mw-button" @click="exportMenu = true">
        <ArrowDownTrayIcon />Экспорт</button
      ><button
        class="mw-button mw-primary"
        :disabled="sending"
        @click="$emit('send')"
      >
        <PaperAirplaneIcon />{{ sending ? "Формируем…" : "Отправить" }}
      </button>
    </div>
    <MobileSheet :open="projectMenu" title="Проект" @close="projectMenu = false"
      ><button
        class="mw-button mw-full"
        @click="
          $emit('settings');
          projectMenu = false;
        "
      >
        Настройки проекта</button
      ><button
        class="mw-button mw-full"
        @click="
          $emit('switch');
          projectMenu = false;
        "
      >
        Сменить проект</button
      ><button
        class="mw-button mw-full"
        @click="
          $emit('delivery');
          projectMenu = false;
        "
      >
        Настройки доставки отчётов
      </button></MobileSheet
    >
    <MobileSheet
      :open="exportMenu"
      title="Экспорт отчёта"
      @close="exportMenu = false"
      ><button
        v-for="format in ['pdf', 'png', 'link']"
        :key="format"
        class="mw-button mw-full"
        @click="
          $emit('export', format);
          exportMenu = false;
        "
      >
        {{
          format === "link"
            ? "Ссылка для клиента"
            : `Скачать ${format.toUpperCase()}`
        }}
      </button></MobileSheet
    >
  </div>
</template>
<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import {
  ChevronDownIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  PlusIcon,
  ArrowDownTrayIcon,
  PaperAirplaneIcon,
} from "@heroicons/vue/24/outline";
import MobileSheet from "./MobileSheet.vue";
defineProps({
  title: String,
  avatar: String,
  syncText: String,
  alertCount: Number,
  view: String,
  channels: Array,
  syncing: Boolean,
  sending: Boolean,
});
const emit = defineEmits([
  "update:view",
  "refresh",
  "connect",
  "send",
  "settings",
  "switch",
  "delivery",
  "export",
  "detector",
  "pickup",
]);
const projectMenu = ref(false),
  exportMenu = ref(false),
  sentinel = ref(null);
let observer;
onMounted(() => {
  const root = sentinel.value.closest("main");
  const sliceHeight =
    root.querySelector(".mw-slice")?.getBoundingClientRect().height || 48;
  observer = new IntersectionObserver(
    ([entry]) =>
      emit(
        "pickup",
        !entry.isIntersecting &&
          entry.boundingClientRect.top < (entry.rootBounds?.top || 0),
      ),
    { root, rootMargin: `-${sliceHeight}px 0px 0px 0px`, threshold: 0 },
  );
  observer.observe(sentinel.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
