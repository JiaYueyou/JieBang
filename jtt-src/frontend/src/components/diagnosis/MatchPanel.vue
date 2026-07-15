<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useLearningStore } from '@/stores/learning'
import type { MatchResult } from '@/types'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  results: MatchResult[]
  resumeId: string
}>()

const emit = defineEmits<{
  (e: 'edit', resumeId: string): void
}>()

const router = useRouter()
const learningStore = useLearningStore()

const activePosIdx = ref(0)
const generatingPath = ref(false)

const currentResult = computed(() => props.results[activePosIdx.value] ?? null)

const getScoreColor = (score: number) => {
  if (score >= 80) return 'var(--success)'
  if (score >= 50) return 'var(--warning)'
  return 'var(--danger)'
}

const goTailor = () => {
  const r = currentResult.value
  if (r) router.push(`/resume/tailor/${props.resumeId}/${r.positionId}`)
}

const generateLearningPath = async () => {
  const r = currentResult.value
  if (!r) return
  generatingPath.value = true
  try {
    await learningStore.generateFromGaps(props.resumeId, r.positionId)
    ElMessage.success('学习路径已生成！前往学习路径页面查看')
    router.push('/learning')
  } catch {
    ElMessage.error('生成失败，请重试')
  } finally {
    generatingPath.value = false
  }
}
</script>

<template>
  <div class="match-panel" v-if="currentResult">
    <!-- Position tabs -->
    <div class="panel-tabs">
      <div
        v-for="(r, idx) in results"
        :key="r.positionId"
        class="panel-tab"
        :class="{ active: idx === activePosIdx }"
        @click="activePosIdx = idx"
      >
        <span class="tab-name">{{ r.positionName }}</span>
        <span class="tab-score" :style="{ color: getScoreColor(r.totalScore) }">{{ r.totalScore }}分</span>
      </div>
    </div>

    <!-- Score + Actions -->
    <div class="panel-hero">
      <div class="score-circle" :style="{ borderColor: getScoreColor(currentResult.totalScore) }">
        <span class="score-num">{{ currentResult.totalScore }}</span>
        <span class="score-label">匹配分</span>
      </div>
      <div class="hero-info">
        <h4>{{ currentResult.resumeName }} → {{ currentResult.positionName }}</h4>
        <p>{{ currentResult.matchDate }}</p>
        <div class="hero-actions">
          <el-button type="primary" @click="goTailor">一键优化简历</el-button>
          <el-button type="success" :loading="generatingPath" @click="generateLearningPath">生成学习路径</el-button>
          <el-button @click="emit('edit', resumeId)">编辑简历</el-button>
        </div>
      </div>
    </div>

    <!-- Gap Analysis -->
    <div class="panel-section">
      <h5 class="section-title">差距分析</h5>
      <div class="gap-row">
        <div class="gap-block">
          <span class="gap-label danger">缺失技能</span>
          <div class="gap-tags">
            <el-tag v-for="sk in currentResult.gapAnalysis.missingSkills" :key="sk.id" type="danger" size="small" effect="plain">{{ sk.name }}</el-tag>
            <span v-if="!currentResult.gapAnalysis.missingSkills.length" class="no-data">无</span>
          </div>
        </div>
        <div class="gap-block">
          <span class="gap-label warning">需加强</span>
          <div class="gap-tags">
            <el-tag v-for="sk in currentResult.gapAnalysis.weakSkills" :key="sk.id" type="warning" size="small" effect="plain">{{ sk.name }}</el-tag>
            <span v-if="!currentResult.gapAnalysis.weakSkills.length" class="no-data">无</span>
          </div>
        </div>
        <div class="gap-block">
          <span class="gap-label success">已匹配</span>
          <div class="gap-tags">
            <el-tag v-for="sk in currentResult.gapAnalysis.matchSkills" :key="sk.id" type="success" size="small" effect="plain">{{ sk.name }}</el-tag>
            <span v-if="!currentResult.gapAnalysis.matchSkills.length" class="no-data">--</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Dimension details -->
    <div class="panel-section" v-if="currentResult.dimensions.length > 0">
      <h5 class="section-title">维度评分</h5>
      <div class="dim-list">
        <div v-for="d in currentResult.dimensions" :key="d.name" class="dim-item">
          <span class="dim-name">{{ d.name }}</span>
          <div class="dim-bar-bg">
            <div class="dim-bar-fill" :style="{ width: d.score + '%', background: getScoreColor(d.score) }"></div>
          </div>
          <span class="dim-score">{{ d.score }}</span>
        </div>
      </div>
    </div>

    <!-- Suggestions -->
    <div class="panel-section" v-if="currentResult.suggestions.length > 0">
      <h5 class="section-title">优化建议</h5>
      <div v-for="sg in currentResult.suggestions" :key="sg.id" class="sg-item">
        <div class="sg-head">
          <span class="sg-tag">{{ sg.section }}</span>
          <el-tag :type="sg.changeType === 'small' ? 'success' : 'warning'" size="small" effect="plain">
            {{ sg.changeType === 'small' ? '小改' : '大改' }}
          </el-tag>
        </div>
        <p class="sg-reason">{{ sg.reason }}</p>
      </div>
    </div>
  </div>
  <div v-else class="match-empty">
    <el-empty description="暂无匹配结果，请先关联岗位" />
  </div>
</template>

<style scoped>
.match-panel {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.panel-tabs {
  display: flex;
  border-bottom: 1px solid var(--hairline);
  overflow-x: auto;
}
.panel-tab {
  padding: 12px 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
}
.panel-tab:hover { background: var(--canvas); }
.panel-tab.active { border-bottom-color: var(--brand); color: var(--brand); font-weight: 600; }
.tab-score { font-weight: 600; }

.panel-hero {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 24px;
}

.score-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 5px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.score-num { font-size: 28px; font-weight: 800; color: var(--ink); }
.score-label { font-size: 12px; color: var(--muted); }

.hero-info { flex: 1; }
.hero-info h4 { font-size: 16px; font-weight: 700; margin-bottom: 4px; }
.hero-info > p { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.hero-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.panel-section {
  padding: 0 24px 20px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 12px;
  padding-top: 20px;
  border-top: 1px solid var(--hairline);
}

.gap-row { display: flex; flex-direction: column; gap: 12px; }
.gap-block { display: flex; align-items: flex-start; gap: 12px; }
.gap-label {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
  min-width: 56px;
  text-align: center;
}
.gap-label.danger { background: #fef0f0; color: var(--danger); }
.gap-label.warning { background: #fdf6ec; color: var(--warning); }
.gap-label.success { background: #f0f9eb; color: var(--success); }
.gap-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.no-data { font-size: 13px; color: var(--weak); }

.dim-list { display: flex; flex-direction: column; gap: 10px; }
.dim-item { display: flex; align-items: center; gap: 12px; }
.dim-name { font-size: 13px; width: 80px; flex-shrink: 0; }
.dim-bar-bg { flex: 1; height: 8px; background: var(--canvas); border-radius: 4px; overflow: hidden; }
.dim-bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
.dim-score { font-size: 13px; font-weight: 600; width: 32px; text-align: right; }

.sg-item { padding: 10px 0; border-bottom: 1px solid var(--hairline); }
.sg-item:last-child { border-bottom: none; }
.sg-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.sg-tag { font-size: 12px; padding: 2px 8px; background: var(--canvas); border-radius: 4px; color: var(--muted); }
.sg-reason { font-size: 13px; color: var(--ink); line-height: 1.5; }

.match-empty { padding: 40px 0; }
</style>
