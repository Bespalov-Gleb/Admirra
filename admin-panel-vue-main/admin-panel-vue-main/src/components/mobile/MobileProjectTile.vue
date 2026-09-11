<template>
  <article class="mw-project">
    <header class="mw-project-head">
      <button
        class="mw-project-avatar"
        :aria-label="`${project.__isFolder ? 'Раскрыть папку' : 'Аватар проекта'} ${project.name}`"
        @click="$emit(project.__isFolder ? 'toggle' : 'avatar')"
      >
        <img v-if="avatar" :src="avatar" alt="" /><span v-else>{{
          initials
        }}</span>
      </button>
      <div class="mw-project-name">
        <button @click="$emit(project.__isFolder ? 'toggle' : 'open')">
          {{ project.name }}
        </button>
        <p v-if="project.description">{{ project.description }}</p>
        <p v-if="paused">На паузе</p>
      </div>
      <button
        v-if="badge?.count"
        class="mw-alert"
        :aria-label="badge.text"
        @click="alertsOpen = true"
      >
        <ExclamationTriangleIcon /><b>{{ badge.count }}</b>
      </button>
    </header>
    <p v-if="syncing" class="mw-muted" role="status">
      Выполняется синхронизация…
    </p>
    <div class="mw-project-kpis">
      <div
        v-for="stat in stats"
        :key="stat.key"
        class="mw-project-kpi"
        :class="{
          accent: stat.key === 'cpa',
          major: ['cpa', 'leads'].includes(stat.key),
        }"
      >
        <span>{{ stat.label }}</span
        ><strong
          :style="{
            '--mw-number-chars': Math.max(
              1,
              String(stat.value).length * 0.6 + 0.2,
            ),
          }"
          >{{ stat.value }}</strong
        >
        <div
          v-if="stat.delta != null"
          class="mw-project-delta"
          :class="stat.tone"
        >
          {{ stat.delta }}
          <small v-if="stat.previous">было {{ stat.previous }}</small>
        </div>
        <small v-else-if="stat.reason">{{ stat.reason }}</small>
      </div>
    </div>
    <div
      v-for="channel in channels"
      :key="channel.code"
      class="mw-channel"
      :aria-label="channel.name"
    >
      <img :src="channel.icon" :alt="channel.name" /><span
        >{{ channel.spendText }} ·
        {{
          channel.needsGoalSelection
            ? "цели не выбраны"
            : `${channel.goalTotal} заявок`
        }}</span
      ><b>{{ channel.cplText }} <small>CPL</small></b>
    </div>
    <p v-if="!channels.length" class="mw-muted">Каналы не подключены</p>
    <details class="mw-traffic">
      <summary>
        <b>Трафик</b
        ><span
          >{{ traffic.impressions }} показов · {{ traffic.clicks }} кликов</span
        ><ChevronDownIcon />
      </summary>
      <div>
        <span
          >CPC <b>{{ traffic.cpc }}</b></span
        ><span v-for="item in traffic.details" :key="item.label"
          >{{ item.label }} <b>{{ item.value }}</b></span
        >
      </div>
    </details>
    <div class="mw-balances">
      <b>Баланс</b
      ><span v-for="balance in balances" :key="balance.code"
        ><img :src="balance.icon" :alt="balance.name" />{{
          balance.value
        }}</span
      ><small v-if="!balances.length">Нет кабинетов</small>
    </div>
    <footer class="mw-project-actions">
      <button class="mw-button" @click="$emit('open')">
        <ChartBarIcon />Аналитика</button
      ><button class="mw-button" @click="$emit('report')">
        <DocumentTextIcon />Отчёт</button
      ><button
        class="mw-button mw-square"
        aria-label="Настройки проекта"
        @click="$emit('settings')"
      >
        <Cog6ToothIcon /></button
      ><button
        v-if="!project.__isFolder"
        class="mw-button mw-square"
        aria-label="Другие действия"
        @click="more = true"
      >
        <EllipsisHorizontalIcon />
      </button>
    </footer>
    <MobileSheet :open="more" title="Действия с проектом" @close="more = false"
      ><button
        class="mw-button mw-full"
        @click="
          $emit('copy');
          more = false;
        "
      >
        Копировать ID {{ project.display_id || project.id }}
      </button>
      <p class="mw-muted">Переместить в папку</p>
      <button
        v-for="folder in folders"
        :key="folder.id"
        class="mw-button mw-full"
        :disabled="folder.id === project.folder_id"
        @click="
          $emit('move', folder.id);
          more = false;
        "
      >
        {{ folder.name }}</button
      ><button
        v-if="project.folder_id"
        class="mw-button mw-full"
        @click="
          $emit('move', null);
          more = false;
        "
      >
        Вынести из папки</button
      ><button
        v-if="paused"
        class="mw-button mw-full"
        @click="
          $emit('resume');
          more = false;
        "
      >
        Возобновить проект
      </button></MobileSheet
    >
    <MobileSheet
      :open="alertsOpen"
      title="Отклонения проекта"
      @close="alertsOpen = false"
      ><p v-for="alert in alerts" :key="alert.id" class="mw-alert-copy">
        {{ alert.hypothesis_text || "Отклонение" }}
      </p>
      <button
        class="mw-button mw-full mw-primary"
        @click="
          $emit('open');
          alertsOpen = false;
        "
      >
        Открыть дашборд
      </button></MobileSheet
    >
  </article>
</template>
<script setup>
import { ref } from "vue";
import {
  ExclamationTriangleIcon,
  ChevronDownIcon,
  ChartBarIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
  EllipsisHorizontalIcon,
} from "@heroicons/vue/24/outline";
import MobileSheet from "./MobileSheet.vue";
defineProps({
  project: Object,
  avatar: String,
  initials: String,
  stats: Array,
  channels: Array,
  balances: Array,
  traffic: Object,
  badge: Object,
  alerts: Array,
  folders: Array,
  paused: Boolean,
  syncing: Boolean,
});
defineEmits([
  "open",
  "report",
  "settings",
  "avatar",
  "move",
  "copy",
  "resume",
  "toggle",
]);
const more = ref(false),
  alertsOpen = ref(false);
</script>
<style scoped>
.mw-project {
  --m: var(--mw-unit);
  background: white;
  border: 1px solid #e9edf4;
  border-radius: calc(0.875 * var(--m));
  padding: calc(1.125 * var(--m));
  min-width: 0;
  color: #1b2333;
}
.mw-project-head {
  display: flex;
  align-items: center;
  gap: calc(0.6875 * var(--m));
  margin-bottom: calc(0.875 * var(--m));
}
.mw-project-avatar {
  width: calc(2.75 * var(--m));
  height: calc(2.75 * var(--m));
  flex: none;
  border-radius: calc(0.6875 * var(--m));
  background: #eff4fe;
  color: #2563eb;
  font-size: calc(0.9375 * var(--m));
  font-weight: 700;
}
.mw-project-avatar img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: inherit;
  background: white;
}
.mw-project-name {
  flex: 1;
  min-width: 0;
}
.mw-project-name button {
  font-size: calc(1.125 * var(--m));
  font-weight: 700;
  letter-spacing: -0.015em;
  text-align: left;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.25;
  min-height: calc(2.75 * var(--m));
}
.mw-project-name p {
  margin: 0;
  font-size: calc(0.8125 * var(--m));
  color: #98a1b3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mw-alert {
  position: relative;
  flex: none;
  width: calc(2.75 * var(--m));
  height: calc(2.75 * var(--m));
  display: grid;
  place-items: center;
  border-radius: calc(0.625 * var(--m));
  color: #92610a;
}
.mw-alert svg {
  width: calc(2.125 * var(--m));
  height: calc(2.125 * var(--m));
  background: #fef6e7;
  padding: calc(0.4375 * var(--m));
  border-radius: calc(0.625 * var(--m));
}
.mw-alert b {
  position: absolute;
  top: 0;
  right: 0;
  min-width: calc(1.125 * var(--m));
  height: calc(1.125 * var(--m));
  background: #f59e0b;
  color: white;
  border: 2px solid white;
  border-radius: 20px;
  font-size: calc(0.6875 * var(--m));
  display: grid;
  place-items: center;
}
.mw-project-kpis {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: calc(0.5625 * var(--m));
  margin-bottom: var(--m);
}
.mw-project-kpi {
  container-type: inline-size;
  --mw-value-size: calc(1.375 * var(--m));
  min-width: 0;
  border-radius: calc(0.6875 * var(--m));
  padding: calc(0.75 * var(--m)) calc(0.8125 * var(--m));
  background: #f7f9fc;
}
.mw-project-kpi > span {
  display: block;
  color: #5b6579;
  font-size: calc(0.8125 * var(--m));
  margin-bottom: calc(0.1875 * var(--m));
}
.mw-project-kpi.accent {
  background: #eff4fe;
}
.mw-project-kpi.accent > span {
  color: #2563eb;
}
.mw-project-kpi > strong {
  display: block;
  font-size: calc(1.375 * var(--m));
  line-height: 1.1;
  letter-spacing: -0.015em;
  white-space: nowrap;
}
.mw-project-kpi.major {
  --mw-value-size: calc(1.625 * var(--m));
}
.mw-project-kpi > strong {
  font-size: clamp(
    calc(0.8125 * var(--m)),
    calc(100cqi / var(--mw-number-chars)),
    var(--mw-value-size)
  ) !important;
}
.mw-project-delta {
  font-size: calc(0.8125 * var(--m));
  font-weight: 600;
  margin-top: calc(0.25 * var(--m));
  color: #98a1b3;
  display: flex;
  gap: calc(0.375 * var(--m));
  flex-wrap: wrap;
}
.mw-project-delta.bad {
  color: #e5484d;
}
.mw-project-delta.good {
  color: #18a05e;
}
.mw-project-kpi small {
  color: #98a1b3;
  font-size: calc(0.8125 * var(--m));
  font-weight: 400;
}
.mw-channel {
  display: flex;
  align-items: center;
  min-height: calc(2.75 * var(--m));
  gap: calc(0.75 * var(--m));
}
.mw-channel > img {
  width: calc(1.75 * var(--m));
  height: calc(1.75 * var(--m));
  border-radius: calc(0.5 * var(--m));
  object-fit: contain;
  flex: none;
}
.mw-channel > span {
  flex: 1;
  min-width: 0;
  font-size: calc(0.9375 * var(--m));
  color: #5b6579;
}
.mw-channel > b {
  flex: none;
  font-size: calc(1.125 * var(--m));
  white-space: nowrap;
}
.mw-channel small {
  font-size: calc(0.8125 * var(--m));
  color: #98a1b3;
  font-weight: 400;
}
.mw-traffic {
  border-block: 1px solid #f1f4f9;
  margin: calc(0.375 * var(--m)) 0 calc(0.75 * var(--m));
}
.mw-traffic summary {
  display: flex;
  align-items: center;
  gap: calc(0.5625 * var(--m));
  min-height: calc(2.75 * var(--m));
  cursor: pointer;
  list-style: none;
}
.mw-traffic summary::-webkit-details-marker {
  display: none;
}
.mw-traffic summary > b,
.mw-balances > b {
  font-size: calc(0.9375 * var(--m));
  font-weight: 600;
}
.mw-traffic summary > span {
  font-size: calc(0.8125 * var(--m));
  color: #5b6579;
  flex: 1;
  min-width: 0;
}
.mw-traffic summary > svg {
  width: var(--m);
  height: var(--m);
  flex: none;
  color: #98a1b3;
}
.mw-traffic[open] summary > svg {
  transform: rotate(180deg);
}
.mw-traffic > div {
  padding-bottom: calc(0.75 * var(--m));
  display: flex;
  flex-wrap: wrap;
  gap: calc(0.5 * var(--m));
  font-size: calc(0.8125 * var(--m));
  color: #5b6579;
}
.mw-balances {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: calc(0.625 * var(--m));
  margin-bottom: calc(0.875 * var(--m));
}
.mw-balances > span {
  display: flex;
  align-items: center;
  gap: calc(0.375 * var(--m));
  min-height: calc(2 * var(--m));
  font-size: calc(0.9375 * var(--m));
  font-weight: 600;
  white-space: nowrap;
}
.mw-balances img {
  width: calc(1.375 * var(--m));
  height: calc(1.375 * var(--m));
  object-fit: contain;
}
.mw-project-actions {
  display: flex;
  gap: calc(0.5 * var(--m));
}
.mw-project-actions > button {
  flex: 1;
  min-width: 0;
  padding: calc(0.5 * var(--m)) calc(0.375 * var(--m));
  font-size: calc(0.9375 * var(--m));
}
.mw-project-actions .mw-square {
  flex: none;
  width: calc(2.75 * var(--m));
}
.mw-alert-copy {
  padding: var(--m) 0;
  border-bottom: 1px solid #e9edf4;
}
@media (max-width: 23em) {
  .mw-project {
    padding: calc(0.75 * var(--m));
  }
  .mw-project-actions > button:not(.mw-square) > svg {
    display: none;
  }
  .mw-project-kpi {
    padding: calc(0.75 * var(--m)) calc(0.5 * var(--m));
  }
  .mw-project-kpi.major > strong {
    font-size: calc(1.375 * var(--m));
  }
  .mw-channel {
    gap: calc(0.5 * var(--m));
  }
  .mw-channel > span {
    font-size: calc(0.8125 * var(--m));
  }
}
</style>
