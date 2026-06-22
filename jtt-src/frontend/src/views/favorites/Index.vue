<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useFavoritesStore } from '@/stores/favorites'
import PositionCard from '@/components/positions/PositionCard.vue'

const router = useRouter()
const favoritesStore = useFavoritesStore()

const goDetail = (id: string) => router.push(`/positions/${id}`)
</script>

<template>
  <div class="favorites-page">
    <div class="page-header">
      <div class="header-text">
        <h2>我的收藏</h2>
        <p class="header-sub">已收藏 {{ favoritesStore.favoriteCount }} 个岗位</p>
      </div>
    </div>

    <div v-if="favoritesStore.favorites.length > 0" class="position-grid">
      <PositionCard
        v-for="pos in favoritesStore.favorites"
        :key="pos.id"
        :position="pos"
        @click="goDetail(pos.id)"
      />
    </div>

    <div v-else class="empty-state">
      <el-empty description="暂无收藏岗位">
        <el-button type="primary" @click="router.push('/positions')">去探索岗位</el-button>
      </el-empty>
    </div>
  </div>
</template>

<style scoped>
.favorites-page { max-width: 1200px; margin: 0 auto; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-text h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.header-sub { font-size: 13px; color: var(--muted); }

.position-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.empty-state {
  padding: 80px 0;
}
</style>
