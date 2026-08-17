<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useResumeStore } from '@/stores/resume'
import { useMatchStore } from '@/stores/match'
import { useLearningStore } from '@/stores/learning'
import type { ResumeData, MatchResult } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const resumeStore = useResumeStore()
const matchStore = useMatchStore()
const learningStore = useLearningStore()

// Mode switching
const activeMode = ref<'known' | 'unknown'>('known')

// Form
const resumes = ref<ResumeData[]>([])
const selectedResumeId = ref('')
const positionKeyword = ref('')
const matching = ref(false)
const generatingForId = ref<string | null>(null) // which card's button is loading

// Match results
const matchResults = ref<MatchResult[]>([])
const expandedPositionId = ref<string | null>(null)

onMounted(async () => {
  // 从岗位详情页「一键生成学习路径」跳转时，读取岗位名称并自动填充
  const posName = route.query.position as string | undefined
  if (posName) {
    activeMode.value = 'known'
    positionKeyword.value = posName
  }

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

  // 有岗位名且已选择简历时，自动触发技能差距分析
  if (posName && selectedResumeId.value) {
    await analyzeGap()
  }
})

// Mode A: results filtered by user-input keyword
const filteredResults = computed(() => {
  const kw = positionKeyword.value.trim().toLowerCase()
  if (!kw) return matchResults.value
  return matchResults.value.filter(r =>
    r.positionName.toLowerCase().includes(kw)
  )
})

const selectedResumeName = computed(() => {
  const r = resumes.value.find((r) => r.id === selectedResumeId.value)
  return r?.name || ''
})

const emptyHintForKeyword = computed(() =>
  `未找到与「${positionKeyword.value}」相关的岗位，请尝试其他关键词`
)

// Mode A: Analyze skill gap for user-input target position
const analyzeGap = async () => {
  if (!selectedResumeId.value || !positionKeyword.value.trim()) {
    ElMessage.warning('请选择简历并输入目标岗位')
    return
  }
  matching.value = true
  try {
    await matchStore.doAutoMatch(selectedResumeId.value)
    matchResults.value = matchStore.batchResults
    if (filteredResults.value.length === 0) {
      ElMessage.info(`未找到与 "${positionKeyword.value}" 相关的岗位，请尝试其他关键词`)
    } else {
      ElMessage.success(`找到 ${filteredResults.value.length} 个相关岗位`)
    }
  } catch {
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
      return
    }
    // Popup: summarize matches before showing cards
    const top5 = matchResults.value.slice(0, 5)
    const lines = top5.map(r =>
      `<div style="margin:6px 0;font-size:14px"><strong>${r.positionName}</strong> — <span style="color:${getScoreColor(r.totalScore)};font-weight:600">${r.totalScore}分</span></div>`
    ).join('')
    ElMessageBox({
      title: '匹配完成',
      dangerouslyUseHTMLString: true,
      message: `<p style="margin-bottom:12px">你的 <strong>${selectedResumeName.value}</strong> 简历匹配到了 <strong>${matchResults.value.length}</strong> 个岗位：</p>${lines}`,
      showCancelButton: true,
      confirmButtonText: '查看详情（跳转诊断报告）',
      cancelButtonText: '关闭',
    }).then(() => {
      router.push('/diagnosis')
    }).catch(() => {})
  } catch {
    const { mockHistoryMatches } = await import('@/mock/data/match')
    matchResults.value = mockHistoryMatches.slice(0, 5)
    ElMessage.warning('使用离线数据')
  } finally {
    matching.value = false
  }
}

const selectPosition = (positionId: string) => {
  expandedPositionId.value = expandedPositionId.value === positionId ? null : positionId
}

// Generate learning path from skill gaps
const generateLearningPath = async (mr: MatchResult) => {
  if (!selectedResumeId.value) return
  generatingForId.value = mr.positionId
  try {
    const missing = [
      ...mr.gapAnalysis.missingSkills.map((s: any) => s.name),
      ...mr.gapAnalysis.weakSkills.map((s: any) => s.name),
    ]
    const matched = mr.gapAnalysis.matchSkills.map((s: any) => s.name)
    await learningStore.generateFromGaps(mr.positionName, missing, matched, selectedResumeId.value)
    ElMessage.success('学习路径已生成！')
    router.push('/learning')
  } catch {
    ElMessage.error('生成学习路径失败，请重试')
  } finally {
    generatingForId.value = null
  }
}

const getScoreColor = (score: number) => {
  if (score >= 85) return '#16a34a'
  if (score >= 70) return '#4f6ef6'
  return '#f59e0b'
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
              <el-input
                v-model="positionKeyword"
                placeholder="输入想从事的岗位，如 Java后端开发"
                clearable
                @keyup.enter="analyzeGap"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-button type="primary" :loading="matching" @click="analyzeGap" style="margin-top: 20px;">
          分析技能差距
        </el-button>
      </div>

      <!-- Filtered position cards -->
      <div v-if="filteredResults.length > 0" class="position-cards">
        <div
          v-for="mr in filteredResults"
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
              <p>{{ mr.matchDate }}</p>
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
              <el-button type="success" :loading="generatingForId === mr.positionId" @click.stop="generateLearningPath(mr)">
                生成学习路径
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="!matching && matchResults.length > 0" class="empty-hint">
        <el-empty :description="emptyHintForKeyword" :image-size="80" />
      </div>
      <div v-else-if="!matching" class="empty-hint">
        <el-empty description="输入目标岗位名称并点击「分析技能差距」查看相关岗位的匹配结果" :image-size="80" />
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
              <p>{{ mr.matchDate }}</p>
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
              <el-button type="success" :loading="generatingForId === mr.positionId" @click.stop="generateLearningPath(mr)">
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

/* Position Cards */
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
