<template>
  <div v-if="loading || error" class="data-state" :class="{ error: Boolean(error) }">
    <span class="data-state-dot"></span>
    <span>{{ error || "正在加载最新数据…" }}</span>
    <button v-if="error" type="button" @click="$emit('retry')">重试</button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ loading: boolean; error: string }>();
defineEmits<{ retry: [] }>();
</script>

<style scoped>
.data-state {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  margin-bottom: 14px;
  padding: 9px 12px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-bg-elevated);
  color: var(--text-secondary);
  font-size: 14px;
}
.data-state.error {
  border-color: rgba(232, 93, 93, 0.26);
  background: var(--color-danger-light);
  color: var(--color-danger);
}
.data-state-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-brand);
  animation: pulse 1s ease-in-out infinite alternate;
}
.error .data-state-dot { background: var(--color-danger); animation: none; }
button {
  margin-left: auto;
  padding: 4px 10px;
  border: 0;
  border-radius: 6px;
  background: var(--color-danger);
  color: #fff;
  cursor: pointer;
}
@keyframes pulse { to { opacity: 0.25; transform: scale(0.75); } }
</style>
