<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useLearningStore } from '@/stores/learning'
import { useMatchStore } from '@/stores/match'
import type { MatchResult, ImprovementSuggestion } from '@/types'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  results: MatchResult[]
  resumeId: string
}>()

const emit = defineEmits<{
  (e: 'edit', resumeId: string): void
  (e: 'apply', resumeId: string, suggestions: ImprovementSuggestion[]): void
}>()

const router = useRouter()
const learningStore = useLearningStore()
const matchStore = useMatchStore()

const activePosIdx = ref(0)
const generatingPath = ref(false)
const applying = ref(false)
const optimizing = ref(false)

const currentResult = computed(() => props.results[activePosIdx.value] ?? null)

const acceptedCount = computed(() => {
  if (!currentResult.value) return 0
  return currentResult.value.suggestions.filter(s => s.accepted).length
})

const toggleAccept = (sg: ImprovementSuggestion) => {
  sg.accepted = !sg.accepted
}

const applyAccepted = async () => {
  const r = currentResult.value
  if (!r || acceptedCount.value === 0) {
    ElMessage.warning('请先选择要应用的优化建议')
    return
  }
  applying.value = true
  try {
    const accepted = r.suggestions.filter(s => s.accepted)
    emit('apply', props.resumeId, accepted)
  } finally {
    applying.value = false
  }
}

const getScoreColor = (score: number) => {
  if (score >= 85) return '#16a34a'
  if (score >= 70) return '#4f6ef6'
  return '#f59e0b'
}

const fetchTailorSuggestions = async () => {
  const r = currentResult.value
  if (!r || optimizing.value) return
  optimizing.value = true
  try {
    const positionCtx = {
      name: r.positionName,
      missingSkills: r.gapAnalysis.missingSkills.map((s: any) => s.name),
      weakSkills: r.gapAnalysis.weakSkills.map((s: any) => s.name),
      matchSkills: r.gapAnalysis.matchSkills.map((s: any) => s.name),
    }
    const fetched = await matchStore.fetchAiSuggestions(props.resumeId, positionCtx)
    const aiSuggestions = fetched.map((s: any) => ({ ...s, id: `ai-${s.id}` }))
    // 替换为 LLM 精修建议，保留原有的作为备选
    r.suggestions = [...aiSuggestions, ...r.suggestions.filter(
      (s: ImprovementSuggestion) => !s.id.startsWith('ai-')
    )]
    ElMessage.success(`AI 已生成 ${aiSuggestions.length} 条优化建议`)
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    const message = detail?.message || error?.response?.data?.message || error?.message
    ElMessage.error(message || 'AI 优化请求失败，请稍后重试')
  } finally {
    optimizing.value = false
  }
}

const generateLearningPath = async () => {
  const r = currentResult.value
  if (!r) return
  generatingPath.value = true
  try {
    const missing = r.gapAnalysis.missingSkills.map((s: any) => s.name)
    const weak = r.gapAnalysis.weakSkills.map((s: any) => s.name)
    const matched = r.gapAnalysis.matchSkills.map((s: any) => s.name)
    await learningStore.generateFromGaps(
      r.positionName,
      [...missing, ...weak],
      matched,
      props.resumeId,
    )
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
    <!-- 过滤统计 -->
    <div v-if="matchStore.batchStats" class="filter-stats">
      共匹配 <strong>{{ matchStore.batchStats.totalMatched }}</strong> 个岗位
      <template v-if="matchStore.batchStats.educationFiltered > 0">
        ，<span class="stat-warn">{{ matchStore.batchStats.educationFiltered }} 个因学历不达标被过滤</span>
      </template>
      <template v-if="matchStore.batchStats.scoreFiltered > 0">
        ，<span class="stat-warn">{{ matchStore.batchStats.scoreFiltered }} 个低于 50 分未展示</span>
      </template>
      <span class="stat-src">（数据源: {{ matchStore.batchStats.dataSource === 'raw_job_record' ? '招聘记录' : matchStore.batchStats.dataSource === 'neo4j' ? '知识图谱' : 'MySQL' }}）</span>
    </div>

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
          <el-button type="primary" :loading="optimizing" @click="fetchTailorSuggestions">
            {{ optimizing ? 'AI 分析中...' : '一键优化简历' }}
          </el-button>
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
      <div class="section-header">
        <h5 class="section-title">优化建议</h5>
        <span v-if="acceptedCount > 0" class="accepted-badge">已选 {{ acceptedCount }} 条</span>
      </div>
      <div v-for="sg in currentResult.suggestions" :key="sg.id" class="sg-item" :class="{ accepted: sg.accepted, 'ai-suggestion': sg.id.startsWith('ai-') }">
        <div class="sg-head">
          <span class="sg-tag">{{ sg.section }}</span>
          <el-tag v-if="sg.id.startsWith('ai-')" type="primary" size="small" effect="dark" class="ai-badge">AI</el-tag>
          <el-tag :type="sg.changeType === 'small' ? 'success' : 'warning'" size="small" effect="plain">
            {{ sg.changeType === 'small' ? '小改' : '大改' }}
          </el-tag>
        </div>
        <p class="sg-reason">{{ sg.reason }}</p>
        <div v-if="sg.suggested" class="sg-diff">
          <span class="sg-original">{{ sg.original }}</span>
          <span class="sg-arrow">→</span>
          <span class="sg-suggested">{{ sg.suggested }}</span>
        </div>
        <div class="sg-actions">
          <el-button
            :type="sg.accepted ? 'success' : 'default'"
            size="small"
            :icon="sg.accepted ? 'Check' : 'Plus'"
            @click="toggleAccept(sg)"
          >
            {{ sg.accepted ? '已接受' : '接受' }}
          </el-button>
          <el-button
            v-if="sg.accepted"
            size="small"
            icon="Close"
            @click="toggleAccept(sg)"
          >
            撤销
          </el-button>
        </div>
      </div>
      <div class="apply-bar" v-if="acceptedCount > 0">
        <el-button type="primary" :loading="applying" @click="applyAccepted">
          应用已接受的建议到简历
        </el-button>
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

.filter-stats {
  padding: 10px 20px;
  font-size: 13px;
  color: var(--muted);
  background: #f8fafc;
  border-bottom: 1px solid var(--hairline);
}
.filter-stats strong { color: var(--ink); }
.stat-warn { color: #f59e0b; }
.stat-src { color: var(--weak); font-size: 11px; margin-left: 4px; }

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

.sg-item { padding: 10px 0; border-bottom: 1px solid var(--hairline); transition: background 0.2s; }
.sg-item:last-child { border-bottom: none; }
.sg-item.accepted { background: #f0f9eb; border-radius: 6px; padding: 10px 8px; margin: 0 -8px; }
.sg-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.sg-tag { font-size: 12px; padding: 2px 8px; background: var(--canvas); border-radius: 4px; color: var(--muted); }
.sg-reason { font-size: 13px; color: var(--ink); line-height: 1.5; }

.sg-diff { display: flex; align-items: center; gap: 8px; margin-top: 8px; padding: 8px; background: var(--canvas); border-radius: 4px; font-size: 13px; }
.sg-original { color: var(--danger); text-decoration: line-through; flex: 1; word-break: break-all; }
.sg-arrow { color: var(--muted); flex-shrink: 0; }
.sg-suggested { color: var(--success); flex: 1; word-break: break-all; }

.ai-badge { font-size: 10px; padding: 0 4px; }
.ai-suggestion { border-left: 3px solid var(--brand); padding-left: 8px; }
.sg-actions { display: flex; gap: 6px; margin-top: 8px; }

.section-header { display: flex; align-items: center; gap: 12px; }
.accepted-badge { font-size: 12px; color: var(--success); font-weight: 600; }

.apply-bar { padding-top: 12px; text-align: right; }

.match-empty { padding: 40px 0; }
</style>
