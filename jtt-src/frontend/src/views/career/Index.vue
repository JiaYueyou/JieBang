<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useResumeStore } from '@/stores/resume'
import { useMatchStore } from '@/stores/match'
import { useLearningStore } from '@/stores/learning'
import { mockPositions } from '@/mock/data/positions'
import type { ResumeData, MatchResult } from '@/types'
import { ElMessage } from 'element-plus'

const router = useRouter()
const resumeStore = useResumeStore()
const matchStore = useMatchStore()
const learningStore = useLearningStore()

// Mode switching
const activeMode = ref<'known' | 'unknown'>('known')

// Form
const resumes = ref<ResumeData[]>([])
const positions = ref(mockPositions)
const selectedResumeId = ref('')
const selectedPositionId = ref('')
const matching = ref(false)
const generatingPath = ref(false)

// Match results
const matchResults = ref<MatchResult[]>([])
const expandedPositionId = ref<string | null>(null)

onMounted(async () => {
  try {
    await resumeStore.fetchList()
    resumes.value = resumeStore.resumes

  } catch { /* use mock fallback */ }
  if (resumes.value.length === 0) {
    const { mockResumes } = await import('@/mock/data/resume')
    resumes.value = mockResumes
  }
  if (resumes.value.length > 0) {
    selectedResumeId.value = resumes.value[0]!.id
  }
})

// Current selection info
const currentMatchResult = computed(() => {
  if (!selectedPositionId.value) return null
  return matchResults.value.find((r) => r.positionId === selectedPositionId.value) || null
})

const selectedPosition = computed(() =>
  positions.value.find((p) => p.id === selectedPositionId.value),
)

const selectedResumeName = computed(() => {
  const r = resumes.value.find((r) => r.id === selectedResumeId.value)
  return r?.name || ''
})

// Mode A: Analyze skill gap for known target position
const analyzeGap = async () => {
  if (!selectedResumeId.value || !selectedPositionId.value) {
    ElMessage.warning('请选择简历和目标岗位')
    return
  }
  matching.value = true
  try {
    await matchStore.doAutoMatch(selectedResumeId.value)
    matchResults.value = matchStore.batchResults
    ElMessage.success('技能差距分析完成')
  } catch {
    // Fallback to mock
    const { mockHistoryMatches } = await import('@/mock/data/match')
    matchResults.value = mockHistoryMatches.slice(0, 5)
    ElMessage.warning('使用离线数据')
  } finally {
    matching.value = false
  }
}

// Mode B: Recommend positions based on resume
const recommendPositions = async () => {
  if (!selectedResumeId.value) {
    ElMessage.warning('请选择简历')
    return
  }
  matching.value = true
  try {
    await matchStore.doAutoMatch(selectedResumeId.value)
    matchResults.value = matchStore.batchResults
    if (matchResults.value.length === 0) {
      ElMessage.info('暂无匹配的岗位推荐')
    }
  } catch {
    const { mockHistoryMatches } = await import('@/mock/data/match')
    matchResults.value = mockHistoryMatches.slice(0, 5)
    ElMessage.warning('使用离线数据')
  } finally {
    matching.value = false
  }
}

const selectPosition = (positionId: string) => {
  selectedPositionId.value = positionId
  expandedPositionId.value = expandedPositionId.value === positionId ? null : positionId
}

// Generate learning path from skill gaps
const generateLearningPath = async () => {
  if (!selectedResumeId.value || !selectedPositionId.value) return
  generatingPath.value = true
  try {
    await learningStore.generateFromGaps(selectedResumeId.value, selectedPositionId.value)
    ElMessage.success('学习路径已生成！')
    router.push('/learning')
  } catch {
    ElMessage.error('生成学习路径失败，请重试')
  } finally {
    generatingPath.value = false
  }
}

const getScoreColor = (score: number) => {
  if (score >= 80) return 'var(--success)'
  if (score >= 50) return 'var(--warning)'
  return 'var(--danger)'
}
</script>

<template>
  <div class="career-page">
    <div class="page-head">
      <h2>职业发展</h2>
      <p class="head-sub">分析技能差距，规划学习路线</p>
    </div>

    <!-- Mode Tabs -->
    <div class="mode-tabs">
      <div
        class="mode-tab"
        :class="{ active: activeMode === 'known' }"
        @click="activeMode = 'known'"
      >
        <el-icon><Aim /></el-icon>
        <span>我有目标岗位</span>
      </div>
      <div
        class="mode-tab"
        :class="{ active: activeMode === 'unknown' }"
        @click="activeMode = 'unknown'"
      >
        <el-icon><Search /></el-icon>
        <span>帮我推荐岗位</span>
      </div>
    </div>

    <!-- ========== Mode A: Known Target ========== -->
    <div v-if="activeMode === 'known'" class="mode-panel">
      <div class="form-card">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="我的简历">
              <el-select v-model="selectedResumeId" placeholder="选择简历" style="width: 100%">
                <el-option v-for="r in resumes" :key="r.id" :label="r.name" :value="r.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标岗位">
              <el-select v-model="selectedPositionId" placeholder="选择目标岗位" filterable style="width: 100%">
                <el-option v-for="p in positions" :key="p.id" :label="`${p.name} (${p.salaryRange})`" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-button type="primary" :loading="matching" @click="analyzeGap" style="margin-top: 20px;">
          分析技能差距
        </el-button>
      </div>

      <!-- Gap Result -->
      <div v-if="currentMatchResult" class="result-card">
        <div class="result-hero">
          <div class="score-circle" :style="{ borderColor: getScoreColor(currentMatchResult.totalScore) }">
            <span class="score-num">{{ currentMatchResult.totalScore }}</span>
            <span class="score-label">匹配分</span>
          </div>
          <div class="hero-info">
            <h4>{{ selectedResumeName }} → {{ selectedPosition?.name }}</h4>
            <p class="hero-note">匹配度越高，转岗所需的学习成本越低</p>
          </div>
        </div>

        <div class="gap-section">
          <div class="gap-block">
            <span class="gap-label danger">缺失技能</span>
            <div class="gap-tags">
              <el-tag v-for="sk in currentMatchResult.gapAnalysis.missingSkills" :key="sk.id" type="danger" size="small" effect="plain">{{ sk.name }}</el-tag>
              <span v-if="!currentMatchResult.gapAnalysis.missingSkills.length" class="no-data">无</span>
            </div>
          </div>
          <div class="gap-block">
            <span class="gap-label warning">需加强</span>
            <div class="gap-tags">
              <el-tag v-for="sk in currentMatchResult.gapAnalysis.weakSkills" :key="sk.id" type="warning" size="small" effect="plain">{{ sk.name }}</el-tag>
              <span v-if="!currentMatchResult.gapAnalysis.weakSkills.length" class="no-data">无</span>
            </div>
          </div>
          <div class="gap-block">
            <span class="gap-label success">已匹配</span>
            <div class="gap-tags">
              <el-tag v-for="sk in currentMatchResult.gapAnalysis.matchSkills" :key="sk.id" type="success" size="small" effect="plain">{{ sk.name }}</el-tag>
              <span v-if="!currentMatchResult.gapAnalysis.matchSkills.length" class="no-data">--</span>
            </div>
          </div>
        </div>

        <div class="path-action">
          <el-button type="success" :loading="generatingPath" @click="generateLearningPath">
            生成学习路径
          </el-button>
        </div>
      </div>

      <div v-else-if="!matching" class="empty-hint">
        <el-empty description="选择目标岗位并点击「分析技能差距」查看分析结果" :image-size="80" />
      </div>
    </div>

    <!-- ========== Mode B: Recommend Positions ========== -->
    <div v-if="activeMode === 'unknown'" class="mode-panel">
      <div class="form-card">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="我的简历">
              <el-select v-model="selectedResumeId" placeholder="选择简历" style="width: 100%">
                <el-option v-for="r in resumes" :key="r.id" :label="r.name" :value="r.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-button type="primary" :loading="matching" @click="recommendPositions" style="margin-top: 20px;">
          开始匹配推荐
        </el-button>
      </div>

      <!-- Position Cards -->
      <div v-if="matchResults.length > 0" class="position-cards">
        <div
          v-for="mr in matchResults"
          :key="mr.positionId"
          class="pos-card"
          :class="{ expanded: expandedPositionId === mr.positionId }"
        >
          <div class="pos-card-main" @click="selectPosition(mr.positionId)">
            <div class="pos-score" :style="{ background: getScoreColor(mr.totalScore), color: '#fff' }">
              {{ mr.totalScore }}
            </div>
            <div class="pos-info">
              <h4>{{ mr.positionName }}</h4>
              <p>
                {{ positions.find(p => p.id === mr.positionId)?.salaryRange || '' }}
                <el-tag size="small" effect="plain" style="margin-left:8px">
                  {{ positions.find(p => p.id === mr.positionId)?.category === 'new' ? '新兴岗位' : '现有岗位' }}
                </el-tag>
              </p>
            </div>
            <div class="pos-expand-icon">
              <el-icon :size="16"><ArrowDown /></el-icon>
            </div>
          </div>

          <!-- Expanded Gap Analysis -->
          <div v-if="expandedPositionId === mr.positionId" class="pos-card-detail">
            <div class="gap-section">
              <div class="gap-block">
                <span class="gap-label danger">缺失技能</span>
                <div class="gap-tags">
                  <el-tag v-for="sk in mr.gapAnalysis.missingSkills" :key="sk.id" type="danger" size="small" effect="plain">{{ sk.name }}</el-tag>
                  <span v-if="!mr.gapAnalysis.missingSkills.length" class="no-data">无</span>
                </div>
              </div>
              <div class="gap-block">
                <span class="gap-label warning">需加强</span>
                <div class="gap-tags">
                  <el-tag v-for="sk in mr.gapAnalysis.weakSkills" :key="sk.id" type="warning" size="small" effect="plain">{{ sk.name }}</el-tag>
                  <span v-if="!mr.gapAnalysis.weakSkills.length" class="no-data">无</span>
                </div>
              </div>
              <div class="gap-block">
                <span class="gap-label success">已匹配</span>
                <div class="gap-tags">
                  <el-tag v-for="sk in mr.gapAnalysis.matchSkills" :key="sk.id" type="success" size="small" effect="plain">{{ sk.name }}</el-tag>
                  <span v-if="!mr.gapAnalysis.matchSkills.length" class="no-data">--</span>
                </div>
              </div>
            </div>

            <!-- Dimensions -->
            <div v-if="mr.dimensions.length > 0" class="dim-section">
              <div v-for="d in mr.dimensions" :key="d.name" class="dim-item">
                <span class="dim-name">{{ d.name }}</span>
                <div class="dim-bar-bg">
                  <div class="dim-bar-fill" :style="{ width: d.score + '%', background: getScoreColor(d.score) }"></div>
                </div>
                <span class="dim-score">{{ d.score }}</span>
              </div>
            </div>

            <div class="path-action">
              <el-button type="success" :loading="generatingPath" @click.stop="generateLearningPath">
                生成学习路径
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="!matching" class="empty-hint">
        <el-empty description="选择简历并点击「开始匹配推荐」查看适合你的岗位" :image-size="80" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.career-page { max-width: 1000px; margin: 0 auto; }

.page-head { margin-bottom: 20px; }
.page-head h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.head-sub { font-size: 14px; color: var(--muted); }

/* Mode Tabs */
.mode-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 24px;
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}
.mode-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 20px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--muted);
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
}
.mode-tab:hover { color: var(--ink); background: var(--canvas); }
.mode-tab.active { color: var(--brand); border-bottom-color: var(--brand); font-weight: 600; }

/* Form */
.form-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 24px;
  margin-bottom: 24px;
}
.form-card .el-form-item { margin-bottom: 0; }

/* Result Card */
.result-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.result-hero {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 24px;
}

.score-circle {
  width: 90px;
  height: 90px;
  border-radius: 50%;
  border: 4px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.score-num { font-size: 24px; font-weight: 800; color: var(--ink); }
.score-label { font-size: 12px; color: var(--muted); }

.hero-info h4 { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
.hero-note { font-size: 13px; color: var(--muted); }

/* Gap Analysis */
.gap-section {
  padding: 0 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.gap-block { display: flex; align-items: flex-start; gap: 12px; }
.gap-label {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  min-width: 56px;
  text-align: center;
  flex-shrink: 0;
}
.gap-label.danger { background: #fef0f0; color: var(--danger); }
.gap-label.warning { background: #fdf6ec; color: var(--warning); }
.gap-label.success { background: #f0f9eb; color: var(--success); }
.gap-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.no-data { font-size: 13px; color: var(--weak); }

/* Dimensions */
.dim-section {
  padding: 0 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.dim-item { display: flex; align-items: center; gap: 10px; }
.dim-name { font-size: 12px; width: 70px; flex-shrink: 0; color: var(--muted); }
.dim-bar-bg { flex: 1; height: 6px; background: var(--canvas); border-radius: 3px; overflow: hidden; }
.dim-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.dim-score { font-size: 12px; font-weight: 600; width: 28px; text-align: right; }

.path-action {
  padding: 16px 24px;
  border-top: 1px solid var(--hairline);
  text-align: right;
}

.empty-hint { padding: 40px 0; }

/* Position Cards (Mode B) */
.position-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pos-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.pos-card-main {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  cursor: pointer;
  transition: background 0.15s;
}
.pos-card-main:hover { background: var(--canvas); }

.pos-score {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
}

.pos-info { flex: 1; min-width: 0; }
.pos-info h4 { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
.pos-info p { font-size: 13px; color: var(--muted); }

.pos-expand-icon {
  color: var(--muted);
  transition: transform 0.2s;
  flex-shrink: 0;
}
.pos-card.expanded .pos-expand-icon { transform: rotate(180deg); }

.pos-card-detail {
  border-top: 1px solid var(--hairline);
  padding-top: 12px;
}
</style>
