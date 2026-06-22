<script setup lang="ts">
import type { JobPosition } from '@/types'
import { useFavoritesStore } from '@/stores/favorites'

const props = defineProps<{ position: JobPosition }>()
defineEmits<{ click: [] }>()

const favoritesStore = useFavoritesStore()
</script>

<template>
  <div class="position-card" @click="$emit('click')">
    <button
      class="fav-btn"
      :class="{ active: favoritesStore.isFavorited(props.position.id) }"
      @click.stop="favoritesStore.toggleFavorite(props.position.id)"
    >
      <el-icon :size="16">
        <StarFilled v-if="favoritesStore.isFavorited(props.position.id)" />
        <Star v-else />
      </el-icon>
    </button>
    <div class="card-top">
      <div class="card-title-row">
        <h4 class="card-title">{{ position.name }}</h4>
        <el-tag
          :type="position.category === 'new' ? 'success' : ''"
          size="small"
          effect="plain"
        >
          {{ position.category === 'new' ? '新兴岗位' : '既有岗位' }}
        </el-tag>
      </div>
      <p class="card-desc">{{ position.summary.slice(0, 80) }}...</p>
    </div>
    <div class="card-bottom">
      <div class="card-skills">
        <el-tag
          v-for="sk in position.requiredSkills.slice(0, 3)"
          :key="sk.id"
          size="small"
          class="skill-tag"
        >
          {{ sk.name }}
        </el-tag>
        <span v-if="position.requiredSkills.length > 3" class="more-tag">+{{ position.requiredSkills.length - 3 }}</span>
      </div>
      <span class="card-salary">{{ position.salaryRange }}</span>
    </div>
    <div v-if="position.skillChanges && position.skillChanges.length > 0" class="card-changes">
      <span class="changes-label">最近变化：</span>
      <span v-for="sc in position.skillChanges.slice(0, 2)" :key="sc.id" class="change-item" :class="sc.type">
        {{ sc.type === 'added' ? '+' : sc.type === 'removed' ? '-' : '~' }}{{ sc.skillName }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.position-card {
  position: relative;
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.position-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

.fav-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: var(--canvas);
  color: var(--weak);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
  z-index: 1;
}

.fav-btn:hover {
  background: #FFF7E6;
  color: var(--warning);
}

.fav-btn.active {
  background: #FFF7E6;
  color: var(--warning);
}

.card-top { margin-bottom: 14px; }

.card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}

.card-desc {
  font-size: 13px;
  color: var(--muted);
  line-height: 1.5;
}

.card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-skills {
  display: flex;
  align-items: center;
  gap: 6px;
}

.skill-tag {
  --el-tag-bg-color: var(--brand-light);
  --el-tag-border-color: transparent;
  --el-tag-text-color: var(--brand);
}

.more-tag {
  font-size: 12px;
  color: var(--muted);
}

.card-salary {
  font-size: 14px;
  font-weight: 600;
  color: var(--danger);
}

.card-changes {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--hairline);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.changes-label {
  font-size: 11px;
  color: var(--weak);
}

.change-item {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}

.change-item.added {
  background: #E8F8F2;
  color: var(--brand);
}

.change-item.removed {
  background: #FFF1F0;
  color: var(--danger);
  text-decoration: line-through;
}

.change-item.modified {
  background: #FFF7E6;
  color: var(--warning);
}
</style>
