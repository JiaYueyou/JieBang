<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useLearningStore } from '@/stores/learning'
import { mockLearningPaths } from '@/mock/data/learning'

const learningStore = useLearningStore()
const expandedId = ref<string | null>(null)

onMounted(() => {
  if (learningStore.paths.length === 0) {
    learningStore.paths = JSON.parse(JSON.stringify(mockLearningPaths))
  }
})

const toggle = (id: string) => {
  expandedId.value = expandedId.value === id ? null : id
}
</script>

<template>
  <div class="learning-page">
    <div class="page-head">
      <h3>学习路径管理</h3>
      <span class="count">共 {{ learningStore.paths.length }} 条路径</span>
    </div>

    <div v-if="learningStore.paths.length === 0" class="empty">
      <el-empty description="暂无学习路径" />
    </div>

    <div v-else class="path-cards">
      <div
        v-for="path in learningStore.paths"
        :key="path.id"
        class="path-card"
        :class="{ expanded: expandedId === path.id }"
      >
        <div class="path-header" @click="toggle(path.id)">
          <div class="path-title-row">
            <el-icon :size="20" color="#4f6ef6"><Guide /></el-icon>
            <span class="path-name">{{ path.name }}</span>
            <el-tag size="small" type="success">{{ learningStore.getCompletionPercent(path.id) }}%</el-tag>
          </div>
          <div class="path-header-right">
            <span class="path-meta">{{ path.positionName }} · {{ path.totalDuration }}</span>
            <el-icon :size="18" class="expand-icon" :class="{ rotated: expandedId === path.id }"><ArrowDown /></el-icon>
          </div>
        </div>

        <div v-if="expandedId === path.id" class="path-body">
          <div class="flowchart-line">
            <div v-for="(step, idx) in path.steps" :key="step.id" class="flow-item">
              <div class="flow-node" :class="{ done: step.completed }">
                <span class="flow-num">{{ idx + 1 }}</span>
                <span class="flow-title">{{ step.title }}</span>
              </div>
              <div v-if="idx < path.steps.length - 1" class="flow-connector">→</div>
            </div>
          </div>

          <div class="timeline">
            <div
              v-for="step in path.steps"
              :key="step.id"
              class="tl-item"
              :class="{ done: step.completed }"
            >
              <div class="tl-dot" @click="learningStore.toggleStep(path.id, step.id)">
                <el-icon v-if="step.completed" :size="12"><Check /></el-icon>
              </div>
              <div class="tl-content">
                <div class="tl-header">
                  <span class="tl-title">{{ step.title }}</span>
                  <span class="tl-duration">{{ step.duration }}</span>
                </div>
                <p class="tl-desc">{{ step.description }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.learning-page { max-width: 1000px; margin: 0 auto; }

.page-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-head h3 { font-size: 18px; font-weight: 700; }
.count { font-size: 13px; color: var(--muted); }

.empty { padding: 60px 0; }

.path-cards { display: flex; flex-direction: column; gap: 12px; }

.path-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
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

.path-name { font-size: 15px; font-weight: 600; }

.path-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.path-meta { font-size: 13px; color: var(--muted); }

.expand-icon { transition: transform 0.25s; color: var(--muted); }
.expand-icon.rotated { transform: rotate(180deg); }

.path-body { padding: 0 20px 20px; border-top: 1px solid var(--hairline); }

.flowchart-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  padding: 16px 0;
  gap: 4px;
}

.flow-item { display: flex; align-items: center; gap: 4px; }

.flow-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 18px;
  background: var(--canvas);
  border: 1px solid var(--hairline);
  font-size: 12px;
}

.flow-node.done {
  background: var(--brand-light);
  border-color: var(--brand);
  color: var(--brand);
}

.flow-num {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
}

.flow-connector { color: var(--weak); font-size: 12px; }

.timeline { padding: 8px 0; }

.tl-item {
  display: flex;
  gap: 14px;
  padding: 10px 0;
  position: relative;
}

.tl-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 34px;
  bottom: 0;
  width: 2px;
  background: var(--hairline);
}

.tl-item.done:not(:last-child)::before { background: var(--brand); }

.tl-dot {
  width: 22px;
  height: 22px;
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

.tl-dot:hover { border-color: var(--brand); }
.tl-item.done .tl-dot { background: var(--brand); border-color: var(--brand); color: #fff; }

.tl-content { flex: 1; }
.tl-header { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.tl-title { font-size: 14px; font-weight: 600; }
.tl-item.done .tl-title { color: var(--muted); text-decoration: line-through; }
.tl-duration { font-size: 12px; color: var(--weak); }
.tl-desc { font-size: 13px; color: var(--muted); line-height: 1.5; }
</style>
