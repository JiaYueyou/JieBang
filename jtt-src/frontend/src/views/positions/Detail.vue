<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { JobPosition } from '@/types'
import { mockPositions } from '@/mock/data/positions'
import { mockGraphNodes, mockGraphEdges } from '@/mock/data/skills'
import { useFavoritesStore } from '@/stores/favorites'
import QuickMatchFab from '@/components/common/QuickMatchFab.vue'

const route = useRoute()
const router = useRouter()
const favoritesStore = useFavoritesStore()
const position = ref<JobPosition | null>(null)

onMounted(() => {
  const id = route.params.id as string
  position.value = mockPositions.find((p) => p.id === id) || null
})

const relatedNodes = ref<any[]>([])
const relatedEdges = ref<any[]>([])

onMounted(() => {
  if (position.value) {
    const posId = `pos-${position.value.id}`
    relatedEdges.value = mockGraphEdges.filter((e) => e.source === posId)
    const skillIds = relatedEdges.value.map((e) => e.target)
    relatedNodes.value = mockGraphNodes.filter((n) => skillIds.includes(n.id))
  }
})
</script>

<template>
  <div class="detail-page" v-if="position">
    <div class="detail-header">
      <div class="header-left">
        <h1>{{ position.name }}</h1>
        <div class="header-meta">
          <el-tag :type="position.category === 'new' ? 'success' : ''" effect="plain">
            {{ position.category === 'new' ? '新兴岗位' : '既有岗位' }}
          </el-tag>
          <span class="meta-text">{{ position.careerLevel === 'junior' ? '初级' : position.careerLevel === 'mid' ? '中级' : '高级' }}</span>
          <span class="meta-text salary">{{ position.salaryRange }}</span>
          <span class="meta-text">更新于 {{ position.updatedAt }}</span>
        </div>
      </div>
      <div class="header-actions">
        <el-button
          :type="favoritesStore.isFavorited(position.id) ? 'warning' : 'default'"
          :icon="favoritesStore.isFavorited(position.id) ? 'StarFilled' : 'Star'"
          @click="favoritesStore.toggleFavorite(position.id)"
        >
          {{ favoritesStore.isFavorited(position.id) ? '已收藏' : '收藏岗位' }}
        </el-button>
        <el-button type="primary" @click="router.push(`/diagnosis`)">
          开始匹配诊断
        </el-button>
      </div>
    </div>

    <div class="detail-body">
      <div class="detail-main">
        <!-- 岗位定义 -->
        <el-card class="section-card">
          <template #header><span class="card-header">岗位概述</span></template>
          <p class="summary">{{ position.summary }}</p>
        </el-card>

        <!-- 核心职责 -->
        <el-card class="section-card">
          <template #header><span class="card-header">核心职责</span></template>
          <ul class="responsibility-list">
            <li v-for="(r, i) in position.responsibilities" :key="i">{{ r }}</li>
          </ul>
        </el-card>

        <!-- 技能要求 -->
        <el-card class="section-card">
          <template #header><span class="card-header">必备技能</span></template>
          <div class="skill-group">
            <div v-for="sk in position.requiredSkills" :key="sk.id" class="skill-chip required">
              {{ sk.name }}
            </div>
          </div>
          <template v-if="position.preferredSkills.length > 0">
            <div style="margin-top: 14px; font-size: 14px; font-weight: 600; color: var(--ink); margin-bottom: 8px;">加分技能</div>
            <div class="skill-group">
              <div v-for="sk in position.preferredSkills" :key="sk.id" class="skill-chip preferred">
                {{ sk.name }}
              </div>
            </div>
          </template>
        </el-card>

        <!-- 行业应用场景 -->
        <el-card class="section-card">
          <template #header><span class="card-header">典型行业场景</span></template>
          <div class="scenario-list">
            <el-tag v-for="s in position.industryScenarios" :key="s" size="default" effect="plain" type="success">
              {{ s }}
            </el-tag>
          </div>
        </el-card>
      </div>

      <div class="detail-side">
        <!-- 局部技能图谱 -->
        <el-card class="section-card">
          <template #header><span class="card-header">关联技能</span></template>
          <div class="skill-graph-mini">
            <div class="graph-node-pos">{{ position.name }}</div>
            <div class="graph-links">
              <div v-for="node in relatedNodes" :key="node.id" class="graph-node-skill">
                {{ node.label }}
              </div>
            </div>
          </div>
        </el-card>

        <!-- 既有岗位：能力变化时间线 -->
        <el-card v-if="position.category === 'existing' && position.skillChanges" class="section-card">
          <template #header><span class="card-header">能力动态变化</span></template>
          <div class="change-timeline">
            <div v-for="sc in position.skillChanges" :key="sc.id" class="change-item" :class="sc.type">
              <div class="change-dot" :class="sc.type"></div>
              <div class="change-info">
                <div class="change-skill">
                  <span class="change-type">{{ sc.type === 'added' ? '新增' : sc.type === 'removed' ? '删除' : '修改' }}</span>
                  {{ sc.skillName }}
                </div>
                <p class="change-desc">{{ sc.description }}</p>
                <div class="change-meta">{{ sc.date }} · 来源：{{ sc.source }}</div>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 新兴岗位：生成学习路径 -->
        <el-card v-if="position.category === 'new'" class="section-card">
          <template #header><span class="card-header">学习建议</span></template>
          <p style="font-size:13px;color:var(--muted);margin-bottom:12px;">该岗位为新兴岗位，可根据必备技能自动推导学习路径</p>
          <el-button type="primary" plain size="default">一键生成学习路径</el-button>
        </el-card>
      </div>
    </div>

    <QuickMatchFab mode="detail" :position-id="route.params.id as string" />
  </div>
</template>

<style scoped>
.detail-page { max-width: 1200px; margin: 0 auto; }

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  background: #fff;
  padding: 24px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.header-left h1 { font-size: 22px; font-weight: 700; margin-bottom: 10px; }

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.meta-text { font-size: 13px; color: var(--muted); }
.meta-text.salary { color: var(--danger); font-weight: 600; }

.detail-body {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
}

.section-card { margin-bottom: 16px; }
.card-header { font-size: 15px; font-weight: 600; }

.summary { font-size: 14px; color: var(--ink); line-height: 1.6; }

.responsibility-list {
  padding-left: 18px;
}
.responsibility-list li {
  font-size: 14px;
  color: var(--ink);
  line-height: 1.8;
}

.skill-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-chip {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}
.skill-chip.required {
  background: var(--brand-light);
  color: var(--brand);
}
.skill-chip.preferred {
  background: var(--canvas);
  color: var(--muted);
  border: 1px solid var(--hairline);
}

.scenario-list { display: flex; flex-wrap: wrap; gap: 8px; }

/* Mini skill graph */
.skill-graph-mini {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.graph-node-pos {
  padding: 8px 16px;
  background: var(--brand);
  color: #fff;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.graph-links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
}

.graph-node-skill {
  padding: 6px 12px;
  background: var(--brand-light);
  color: var(--brand);
  border-radius: 14px;
  font-size: 12px;
}

/* Change timeline */
.change-timeline {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.change-item {
  display: flex;
  gap: 12px;
}

.change-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}
.change-dot.added { background: var(--brand); }
.change-dot.removed { background: var(--danger); }
.change-dot.modified { background: var(--warning); }

.change-skill { font-size: 13px; font-weight: 600; color: var(--ink); }
.change-type { font-size: 11px; padding: 1px 6px; border-radius: 8px; margin-right: 6px; }
.change-item.added .change-type { background: var(--brand-light); color: var(--brand); }
.change-item.removed .change-type { background: #FFF1F0; color: var(--danger); }
.change-item.modified .change-type { background: #FFF7E6; color: var(--warning); }

.change-desc { font-size: 12px; color: var(--muted); margin: 2px 0; }
.change-meta { font-size: 11px; color: var(--weak); }
</style>
