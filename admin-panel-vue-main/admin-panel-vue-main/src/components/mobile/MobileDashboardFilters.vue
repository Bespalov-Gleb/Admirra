<template>
  <MobileSheet
    :open="open"
    :title="campaignView ? 'Кампании' : 'Фильтры'"
    :back="campaignView"
    @back="campaignView = false"
    @close="$emit('close')"
  >
    <template v-if="campaignView"
      ><input
        v-model="query"
        class="mw-search"
        placeholder="Поиск по кампаниям"
        aria-label="Поиск по кампаниям"
      /><label class="mw-check"
        ><input
          type="checkbox"
          :checked="
            selectedIds.length === scopedCampaigns.length &&
            scopedCampaigns.length > 0
          "
          @change="
            selectedIds = $event.target.checked
              ? scopedCampaigns.map((c) => c.id)
              : []
          "
        /><span>Все кампании</span></label
      ><label
        v-for="campaign in searchedCampaigns"
        :key="campaign.id"
        class="mw-check"
        ><input
          v-model="selectedIds"
          type="checkbox"
          :value="campaign.id"
        /><span>{{ campaign.name }}</span></label
      >
      <p v-if="!searchedCampaigns.length" class="mw-muted">
        Кампании не найдены
      </p></template
    >
    <template v-else>
      <p v-if="channelOptions.length > 1" class="mw-muted">Каналы</p>
      <div v-if="channelOptions.length > 1" class="mw-presets">
        <button
          v-for="channel in channelOptions"
          :key="channel.value"
          :class="{ selected: channel.value === channelValue }"
          @click="
            channelValue = channel.value;
            selectedIds = [];
          "
        >
          {{ channel.name }}
        </button>
      </div>
      <template v-if="directions.length"
        ><p class="mw-muted">{{ directionLabel || "Услуги" }}</p>
        <label class="mw-check"
          ><input
            type="checkbox"
            :checked="allDirectionsSelected"
            @change="
              selectedDirections = $event.target.checked
                ? directions.map((d) => d.id)
                : [];
              selectedIds = [];
            "
          /><span
            >Все {{ (directionLabel || "услуги").toLowerCase() }}</span
          ></label
        >
        <label
          v-for="direction in directions"
          :key="direction.id"
          class="mw-check"
          ><input
            v-model="selectedDirections"
            type="checkbox"
            :value="direction.id"
            @change="selectedIds = []"
          /><span>{{ direction.name }}</span
          ><small>{{ direction.campaign_count }} камп.</small></label
        > </template
      ><button class="mw-button mw-full" @click="openCampaigns">
        Кампании
        <small>{{ selectedIds.length || scopedCampaigns.length }}</small
        ><ChevronRightIcon />
      </button>
    </template>
    <p v-if="emptySelection" class="mw-muted" role="status">
      Выберите хотя бы {{ campaignView ? "одну кампанию" : "одну услугу" }}.
    </p>
    <div class="mw-sheet-actions mw-filter-actions">
      <button class="mw-button" @click="reset">Сбросить</button
      ><button
        class="mw-button mw-primary"
        :disabled="emptySelection"
        @click="apply"
      >
        Показать
      </button>
    </div>
  </MobileSheet>
</template>
<script setup>
import { ref, watch, computed } from "vue";
import { ChevronRightIcon } from "@heroicons/vue/24/outline";
import MobileSheet from "./MobileSheet.vue";
const props = defineProps({
  open: Boolean,
  directions: { type: Array, default: () => [] },
  campaigns: { type: Array, default: () => [] },
  campaignIds: { type: Array, default: () => [] },
  channelOptions: { type: Array, default: () => [] },
  channel: String,
  directionLabel: String,
  directionId: [String, Number],
});
const emit = defineEmits(["close", "apply"]);
const selectedDirections = ref([]),
  selectedIds = ref([]),
  channelValue = ref("all"),
  campaignView = ref(false),
  query = ref("");
let appliedSelection = null;
const signature = (channel, ids, directionId) =>
  JSON.stringify([channel, [...ids].map(String).sort(), directionId]);
watch(
  () => props.open,
  (open) => {
    if (open) {
      const sameSelection =
        appliedSelection?.signature ===
        signature(props.channel, props.campaignIds, props.directionId);
      selectedDirections.value = sameSelection
        ? [...appliedSelection.directions]
        : props.directionId
          ? [props.directionId]
          : props.campaignIds.length
            ? props.directions
                .filter((d) =>
                  (d.campaign_ids || []).some((id) =>
                    props.campaignIds.map(String).includes(String(id)),
                  ),
                )
                .map((d) => d.id)
            : props.directions.map((d) => d.id);
      selectedIds.value = [...props.campaignIds];
      channelValue.value = props.channel;
      campaignView.value = false;
      query.value = "";
    }
  },
);
const allDirectionsSelected = computed(
  () => selectedDirections.value.length === props.directions.length,
);
const directionIds = computed(
  () =>
    new Set(
      props.directions
        .filter((d) => selectedDirections.value.includes(d.id))
        .flatMap((d) => d.campaign_ids || []),
    ),
);
const scopedCampaigns = computed(() =>
  props.campaigns.filter(
    (c) =>
      (!props.directions.length ||
        allDirectionsSelected.value ||
        [...directionIds.value].some((id) => String(id) === String(c.id))) &&
      (channelValue.value === "all" ||
        String(c.platform || "")
          .toLowerCase()
          .includes(channelValue.value)),
  ),
);
const searchedCampaigns = computed(() =>
  scopedCampaigns.value.filter((c) =>
    c.name?.toLowerCase().includes(query.value.trim().toLowerCase()),
  ),
);
const emptySelection = computed(
  () =>
    (props.directions.length > 0 && !selectedDirections.value.length) ||
    (campaignView.value &&
      scopedCampaigns.value.length > 0 &&
      !selectedIds.value.length),
);
function openCampaigns() {
  if (!selectedIds.value.length)
    selectedIds.value = scopedCampaigns.value.map((c) => c.id);
  campaignView.value = true;
}
function reset() {
  selectedDirections.value = props.directions.map((d) => d.id);
  channelValue.value = "all";
  selectedIds.value = campaignView.value
    ? props.campaigns.map((c) => c.id)
    : [];
  query.value = "";
}
function apply() {
  if (emptySelection.value) return;
  const subset = selectedIds.value.filter((id) =>
    scopedCampaigns.value.some((c) => String(c.id) === String(id)),
  );
  const fullScope =
    !subset.length || subset.length === scopedCampaigns.value.length;
  const selection = {
    channel: channelValue.value,
    campaignIds: fullScope
      ? allDirectionsSelected.value
        ? []
        : scopedCampaigns.value.map((c) => c.id)
      : subset,
    directionId:
      selectedDirections.value.length === 1 &&
      !allDirectionsSelected.value &&
      fullScope
        ? selectedDirections.value[0]
        : null,
  };
  appliedSelection = {
    signature: signature(
      selection.channel,
      selection.campaignIds,
      selection.directionId,
    ),
    directions: [...selectedDirections.value],
  };
  emit("apply", selection);
  emit("close");
}
</script>
