<template>
  <el-tooltip :content="active ? '取消收藏' : '加入收藏'" placement="top" :show-after="350">
    <button
      class="favorite-toggle"
      :class="{ active, compact }"
      type="button"
      :aria-label="active ? `取消收藏${title}` : `收藏${title}`"
      :aria-pressed="active"
      @click.stop="handleToggle"
    >
      <el-icon>
        <StarFilled v-if="active" />
        <Star v-else />
      </el-icon>
      <span v-if="showLabel">{{ active ? "已收藏" : "收藏" }}</span>
    </button>
  </el-tooltip>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { ElMessage } from "element-plus";
import { Star, StarFilled } from "@element-plus/icons-vue";
import { useFavorites, type FavoriteTargetType } from "@/composables/useFavorites";

const props = withDefaults(
  defineProps<{
    type: FavoriteTargetType;
    targetId: string | number;
    title: string;
    showLabel?: boolean;
    compact?: boolean;
  }>(),
  { showLabel: false, compact: false },
);

const emit = defineEmits<{ change: [active: boolean] }>();
const { isFavorite, toggleFavorite } = useFavorites();
const active = computed(() => isFavorite(props.type, props.targetId));

function handleToggle() {
  const nextState = toggleFavorite(props.type, props.targetId, props.title);
  ElMessage({
    type: "success",
    message: nextState ? `已收藏“${props.title}”` : `已取消收藏“${props.title}”`,
    duration: 1600,
  });
  emit("change", nextState);
}
</script>

<style scoped>
.favorite-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-width: 32px;
  height: 32px;
  padding: 0 9px;
  border: 1px solid var(--color-border);
  border-radius: 9px;
  background: var(--color-bg-elevated);
  color: var(--text-muted);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  transition: all var(--duration-fast) var(--ease-out);
}

.favorite-toggle.compact {
  min-width: 28px;
  height: 28px;
  padding: 0 7px;
  border-radius: 8px;
}

.favorite-toggle:hover {
  border-color: rgba(245, 158, 75, 0.4);
  background: var(--color-warning-light);
  color: var(--color-warning);
  transform: translateY(-1px);
}

.favorite-toggle.active {
  border-color: rgba(245, 158, 75, 0.24);
  background: var(--color-warning-light);
  color: var(--color-warning);
}

.favorite-toggle.active:hover {
  border-color: var(--color-warning);
  box-shadow: 0 3px 10px rgba(245, 158, 75, 0.14);
}
</style>
