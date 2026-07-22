<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePositionsStore } from '@/stores/positions'
import PositionCard from '@/components/positions/PositionCard.vue'

const router = useRouter()
const positionsStore = usePositionsStore()
const activeTab = ref<'all' | 'new' | 'existing'>('all')
const keyword = ref('')

// 加载岗位数据，根据 tab 传 category 参数
const loadPositions = () => {
  const params: Record<string, any> = { pageSize: 200 }
  if (activeTab.value !== 'all') params.category = activeTab.value
  positionsStore.fetchPositions(params)
}

onMounted(() => loadPositions())

// 切换 tab 时重新请求后端
watch(activeTab, () => loadPositions())

const filtered = computed(() => {
  let list = positionsStore.positions
  if (keyword.value) {
    list = list.filter((p) => p.name.includes(keyword.value) || p.summary.includes(keyword.value))
  }
  return list
})

const goDetail = (id: string) => router.push(`/positions/${id}`)
</script>

<template>
  <div class="positions-page">
    <div class="page-toolbar">
      <div class="tabs">
        <span class="tab" :class="{ active: activeTab === 'all' }" @click="activeTab = 'all'">全部岗位</span>
        <span class="tab" :class="{ active: activeTab === 'new' }" @click="activeTab = 'new'">新兴岗位</span>
        <span class="tab" :class="{ active: activeTab === 'existing' }" @click="activeTab = 'existing'">既有岗位</span>
      </div>
      <el-input v-model="keyword" placeholder="搜索岗位名称或关键词" prefix-icon="Search" clearable class="search" />
    </div>

    <div v-if="positionsStore.total > 0" class="result-count">共 {{ positionsStore.total }} 个岗位</div>

    <div class="position-grid">
      <PositionCard v-for="pos in filtered" :key="pos.id" :position="pos" @click="goDetail(pos.id)" />
    </div>

    <div v-if="filtered.length === 0 && !positionsStore.loading" class="empty">
      <el-empty description="暂无匹配岗位" />
    </div>
  </div>
</template>

<style scoped>
.positions-page { max-width: 1200px; margin: 0 auto; }

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.tabs { display: flex; gap: 8px; }

.tab {
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}

.tab:hover { color: var(--brand); background: var(--brand-light); }
.tab.active { color: #fff; background: var(--brand); }

.search { width: 300px; }
.search :deep(.el-input__wrapper) { border-radius: 20px; }

.result-count {
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 12px;
}

.position-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.empty { padding: 60px 0; }
</style>
