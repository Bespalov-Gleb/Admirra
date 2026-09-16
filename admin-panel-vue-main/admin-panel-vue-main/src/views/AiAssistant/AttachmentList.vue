<template>
  <div v-if="files.length || busy || error" class="file-area" aria-live="polite">
    <div class="file-list">
      <span v-for="file in files" :key="file.id" class="file-chip">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 2H6v20h12V6zM14 2v5h5M8 12h8M8 16h6" /></svg>
        <span :title="file.name">{{ file.name }}</span>
        <button type="button" :disabled="busy" :aria-label="`Убрать ${file.name}`" @click="$emit('remove', file)">×</button>
      </span>
      <span v-if="busy" class="file-status">Читаю файл…</span>
    </div>
    <p v-if="error" class="file-error" role="alert">{{ error }}</p>
  </div>
</template>

<script setup>
defineProps({ files: { type: Array, default: () => [] }, busy: Boolean, error: String })
defineEmits(['remove'])
</script>

<style scoped>
.file-area { margin: 0 0 .8rem; text-align: left; }
.file-list { display: flex; flex-wrap: wrap; gap: .5rem; }
.file-chip { display: inline-flex; align-items: center; gap: .45rem; max-width: 100%; padding: .4rem .6rem; border: 1px solid var(--assistant-line); border-radius: .65rem; background: var(--assistant-soft); color: var(--assistant-sub); font-size: .85rem; }
.file-chip > span { max-width: 17rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-chip svg { width: 1.05rem; height: 1.05rem; flex-shrink: 0; fill: none; stroke: currentColor; stroke-width: 1.5; }
.file-chip button { padding: 0 .2rem; border: 0; background: transparent; color: inherit; cursor: pointer; font-size: 1.2rem; }
.file-status { color: var(--assistant-muted); font-size: .85rem; }
.file-error { margin: .4rem 0 0; color: #c83c36; font-size: .85rem; }
</style>
