<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePositionsStore } from '@/stores/positions'
import { useLearningStore } from '@/stores/learning'
import PositionCard from '@/components/positions/PositionCard.vue'

const router = useRouter()
const positionsStore = usePositionsStore()
const learningStore = useLearningStore()

const recommendedPositions = computed(() => positionsStore.positions.slice(0, 4))
const expandedPathId = ref<string | null>(null)

onMounted(async () => {
  await positionsStore.fetchPositions()
  if (learningStore.paths.length === 0) {
    await learningStore.fetchPaths()
  }
})

const togglePathExpand = (pathId: string) => {
  expandedPathId.value = expandedPathId.value === pathId ? null : pathId
}

const editingPathName = ref<string | null>(null)
const editNameValue = ref('')

const startEditName = (pathId: string, currentName: string) => {
  editingPathName.value = pathId
  editNameValue.value = currentName
}

const finishEditName = (pathId: string) => {
  if (editNameValue.value.trim()) {
    learningStore.renamePath(pathId, editNameValue.value.trim())
  }
  editingPathName.value = null
}

const goToPosition = (id: string) => router.push(`/positions/${id}`)
</script>

<template>
  <div class="home-page">
    <!-- 上半部分 -->
    <section class="hero-section">
      <div class="welcome-text">
        <h1>早上好，求职者</h1>
        <p>发现最适合你的职业方向，让 AI 帮你打造完美简历</p>
      </div>
      <div class="quick-actions">
        <div class="action-card" @click="router.push('/diagnosis')">
          <el-icon :size="28"><Document /></el-icon>
          <span>简历诊断</span>
        </div>
        <div class="action-card" @click="router.push('/positions')">
          <el-icon :size="28"><Compass /></el-icon>
          <span>探索岗位</span>
        </div>
        <div class="action-card" @click="router.push('/graph')">
          <el-icon :size="28"><Share /></el-icon>
          <span>知识图谱</span>
        </div>
<<<<<<< HEAD
<<<<<<< HEAD
        <div class="action-card" @click="router.push('/career')">
          <el-icon :size="28"><TrendCharts /></el-icon>
          <span>职业发展</span>
=======
        <div class="action-card" @click="router.push('/diagnosis')">
          <el-icon :size="28"><Connection /></el-icon>
          <span>简历诊断</span>
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
=======
        <div class="action-card" @click="router.push('/diagnosis')">
          <el-icon :size="28"><Connection /></el-icon>
          <span>简历诊断</span>
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
        </div>
      </div>
    </section>

    <section class="recommend-section">
      <div class="section-header">
        <h3>推荐岗位</h3>
        <span class="section-link" @click="router.push('/positions')">查看全部 <el-icon><ArrowRight /></el-icon></span>
      </div>
      <div class="position-grid">
        <PositionCard
          v-for="pos in recommendedPositions"
          :key="pos.id"
          :position="pos"
          @click="goToPosition(pos.id)"
        />
      </div>
    </section>

    <!-- 下半部分：我的学习路径 -->
    <section class="learning-section">
      <div class="section-header">
        <h3>我的学习路径</h3>
        <span class="section-link" @click="router.push('/learning')">管理路径 <el-icon><ArrowRight /></el-icon></span>
      </div>

      <div v-if="learningStore.paths.length === 0" class="empty-learning">
        <el-empty description="暂无学习路径，完成匹配诊断后自动生成" />
      </div>

      <div v-else class="path-list">
        <div
          v-for="path in learningStore.paths"
          :key="path.id"
          class="path-card"
          :class="{ expanded: expandedPathId === path.id }"
        >
          <div class="path-header" @click="togglePathExpand(path.id)">
            <div class="path-title-row">
              <el-icon :size="20" class="path-icon"><Guide /></el-icon>
              <template v-if="editingPathName === path.id">
                <input
                  v-model="editNameValue"
                  class="path-name-input"
                  @blur="finishEditName(path.id)"
                  @keyup.enter="finishEditName(path.id)"
                  @click.stop
                  autofocus
                />
              </template>
              <template v-else>
                <span class="path-name" @dblclick.stop="startEditName(path.id, path.name)">{{ path.name }}</span>
                <el-button :icon="'Edit'" text size="small" @click.stop="startEditName(path.id, path.name)" />
              </template>
            </div>
            <div class="path-meta">
              <el-tag size="small" type="success">{{ learningStore.getCompletionPercent(path.id) }}%</el-tag>
              <span class="path-duration">{{ path.totalDuration }}</span>
              <el-icon :size="18" class="expand-icon" :class="{ rotated: expandedPathId === path.id }">
                <ArrowDown />
              </el-icon>
            </div>
          </div>

          <div v-if="expandedPathId === path.id" class="path-body">
            <!-- 流程图占位 - 后续接入 G6 -->
            <div class="flowchart-placeholder">
              <div class="flowchart-mock">
                <div v-for="(step, idx) in path.steps" :key="step.id" class="flow-node-wrapper">
                  <div class="flow-node" :class="{ done: step.completed, active: !step.completed && idx === path.steps.findIndex((s: any) => !s.completed) }">
                    <span class="flow-node-num">{{ idx + 1 }}</span>
                    <span class="flow-node-title">{{ step.title }}</span>
                  </div>
                  <div v-if="idx < path.steps.length - 1" class="flow-arrow">→</div>
                </div>
              </div>
            </div>

            <!-- 学习步骤时间线 -->
            <div class="timeline">
              <div
                v-for="step in path.steps"
                :key="step.id"
                class="timeline-item"
                :class="{ completed: step.completed }"
              >
                <div class="timeline-dot" @click="learningStore.toggleStep(path.id, step.id)">
                  <el-icon v-if="step.completed" :size="14"><Check /></el-icon>
                </div>
                <div class="timeline-content">
                  <div class="step-header">
                    <span class="step-title">{{ step.title }}</span>
                    <span class="step-duration">{{ step.duration }}</span>
                  </div>
                  <p class="step-desc">{{ step.description }}</p>
                  <div class="step-resources">
                    <el-tag
                      v-for="res in step.resources"
                      :key="res.id"
                      size="small"
                      :type="res.type === 'course' ? 'success' : res.type === 'book' ? '' : 'info'"
                    >
                      {{ res.title }}
                    </el-tag>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-page {
  max-width: 1200px;
  margin: 0 auto;
}

/* Hero */
.hero-section {
  background: linear-gradient(135deg, #eef1fe 0%, #FFFFFF 50%, #f8f9fb 100%);
  border-radius: 12px;
  padding: 32px 36px;
  margin-bottom: 24px;
}

.welcome-text h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 8px;
}

.welcome-text p {
  font-size: 14px;
  color: var(--muted);
  margin-bottom: 24px;
}

.quick-actions {
  display: flex;
  gap: 16px;
}

.action-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 12px;
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--brand);
}

.action-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

.action-card span {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink);
}

/* Section */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 18px;
  font-weight: 700;
}

.section-link {
  font-size: 13px;
  color: var(--brand);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.section-link:hover { color: var(--brand-dark); }

.recommend-section {
  margin-bottom: 32px;
}

.position-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

/* Learning Path */
.learning-section {
  margin-bottom: 32px;
}

.empty-learning {
  padding: 40px 0;
}

.path-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.path-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.path-card:hover {
  box-shadow: var(--shadow-hover);
}

.path-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
}

.path-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.path-icon { color: var(--brand); }

.path-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.path-name-input {
  font-size: 15px;
  font-weight: 600;
  border: 1px solid var(--brand);
  border-radius: 4px;
  padding: 2px 8px;
  outline: none;
  width: 260px;
}

.path-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.path-duration {
  font-size: 13px;
  color: var(--muted);
}

.expand-icon {
  transition: transform 0.25s ease;
  color: var(--muted);
}
.expand-icon.rotated {
  transform: rotate(180deg);
}

.path-body {
  padding: 0 20px 20px;
  border-top: 1px solid var(--hairline);
}

/* Flowchart */
.flowchart-placeholder {
  padding: 16px 0;
}

.flowchart-mock {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.flow-node-wrapper {
  display: flex;
  align-items: center;
  gap: 4px;
}

.flow-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 20px;
  background: var(--canvas);
  border: 1px solid var(--hairline);
  font-size: 12px;
  white-space: nowrap;
}

.flow-node.done {
  background: var(--brand-light);
  border-color: var(--brand);
  color: var(--brand);
}

.flow-node.active {
  background: #fff;
  border-color: var(--brand);
  box-shadow: 0 0 0 2px var(--brand-light);
}

.flow-node-num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--canvas);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
}

.flow-arrow {
  color: var(--weak);
  font-size: 14px;
  margin: 0 4px;
}

/* Timeline */
.timeline {
  padding: 8px 0;
}

.timeline-item {
  display: flex;
  gap: 14px;
  padding: 10px 0;
  position: relative;
}

.timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 11px;
  top: 36px;
  bottom: 0;
  width: 2px;
  background: var(--hairline);
}

.timeline-item.completed:not(:last-child)::before {
  background: var(--brand);
}

.timeline-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid var(--hairline);
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;
}

.timeline-dot:hover {
  border-color: var(--brand);
}

.timeline-item.completed .timeline-dot {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}

.timeline-content {
  flex: 1;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.timeline-item.completed .step-title {
  color: var(--muted);
  text-decoration: line-through;
}

.step-duration {
  font-size: 12px;
  color: var(--weak);
}

.step-desc {
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 6px;
  line-height: 1.5;
}

.step-resources {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
