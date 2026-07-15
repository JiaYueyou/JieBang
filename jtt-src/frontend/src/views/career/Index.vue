<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useResumeStore } from '@/stores/resume'
import { careerApi } from '@/api/career'
import { mockPositions } from '@/mock/data/positions'
import { mockCareerPlans } from '@/mock/data/career'
import type { CareerTransitionAssessment, CareerPlan, LearningBudget, ResumeData } from '@/types'
import { ElMessage } from 'element-plus'

const resumeStore = useResumeStore()

const resumes = ref<ResumeData[]>([])
const positions = ref(mockPositions)
const assessing = ref(false)
const saving = ref(false)

// Form
const planForm = reactive({
  resumeId: '',
  targetPositionId: '',
  weeklyHours: 15,
  totalWeeks: 12,
  targetIndustry: '互联网',
  targetRoleType: '技术研发',
  preferredCity: '北京',
  salaryExpectation: '25K-40K',
})

// Assessment result
const assessment = ref<CareerTransitionAssessment | null>(null)
const savedPlan = ref<CareerPlan | null>(null)

onMounted(async () => {
  // Load resumes
  try {
    await resumeStore.fetchList()
  } catch { /* mock */ }
  if (resumeStore.resumes.length > 0) {
    resumes.value = resumeStore.resumes
    planForm.resumeId = resumes.value[0].id
  } else {
    const { mockResumes } = await import('@/mock/data/resume')
    resumes.value = mockResumes
    planForm.resumeId = mockResumes[0].id
  }

  // Try load saved plan
  try {
    const res = await careerApi.getPlan()
    if ((res as any).data) {
      savedPlan.value = (res as any).data
      const sp = savedPlan.value!
      planForm.resumeId = sp.resumeId
      planForm.targetPositionId = sp.targetPositionId
      planForm.weeklyHours = sp.budget.weeklyHours
      planForm.totalWeeks = sp.budget.totalWeeks
      planForm.targetIndustry = sp.preferences.targetIndustry
      planForm.targetRoleType = sp.preferences.targetRoleType
      planForm.preferredCity = sp.preferences.preferredCity
      planForm.salaryExpectation = sp.preferences.salaryExpectation
      if (sp.assessment) assessment.value = sp.assessment
    }
  } catch {
    // Mock fallback
    if (mockCareerPlans.length > 0) {
      const sp = mockCareerPlans[0]
      planForm.targetPositionId = sp.targetPositionId
      planForm.weeklyHours = sp.budget.weeklyHours
      planForm.totalWeeks = sp.budget.totalWeeks
      if (sp.assessment) assessment.value = sp.assessment
    }
  }
})

const runAssessment = async () => {
  if (!planForm.resumeId || !planForm.targetPositionId) {
    ElMessage.warning('请选择简历和目标岗位')
    return
  }
  assessing.value = true
  try {
    const budget: LearningBudget = { weeklyHours: planForm.weeklyHours, totalWeeks: planForm.totalWeeks }
    const res = await careerApi.assess({
      resumeId: planForm.resumeId,
      targetPositionId: planForm.targetPositionId,
      budget,
    })
    assessment.value = (res as any).data
    ElMessage.success('评估完成')
  } catch {
    ElMessage.error('评估失败，请重试')
  } finally {
    assessing.value = false
  }
}

const savePlan = async () => {
  saving.value = true
  try {
    const planData: Partial<CareerPlan> = {
      resumeId: planForm.resumeId,
      preferences: {
        targetIndustry: planForm.targetIndustry,
        targetRoleType: planForm.targetRoleType,
        preferredCity: planForm.preferredCity,
        salaryExpectation: planForm.salaryExpectation,
      },
      budget: { weeklyHours: planForm.weeklyHours, totalWeeks: planForm.totalWeeks },
      targetPositionId: planForm.targetPositionId,
      targetPositionName: positions.value.find((p) => p.id === planForm.targetPositionId)?.name || '',
      assessment: assessment.value,
    }
    await careerApi.savePlan(planData)
    ElMessage.success('计划已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const getScoreColor = (score: number) => {
  if (score >= 80) return 'var(--success)'
  if (score >= 50) return 'var(--warning)'
  return 'var(--danger)'
}

const feasibilityColors: Record<string, string> = {
  high: 'var(--success)',
  medium: 'var(--warning)',
  low: 'var(--danger)',
  very_low: 'var(--danger)',
}

const feasibilityLabels: Record<string, string> = {
  high: '高 — 建议转岗',
  medium: '中等 — 需充分准备',
  low: '较低 — 慎重考虑',
  very_low: '极低 — 不建议转岗',
}

const industryOptions = ['互联网', '金融', '教育', '医疗', '制造', '能源', '零售', '物流', '其他']
const roleOptions = ['技术研发', '产品', '设计', '运营', '市场', '数据分析', '项目管理', '其他']
</script>

<template>
  <div class="career-page">
    <div class="page-head">
      <h2>职业发展</h2>
      <p class="head-sub">规划学习路线，评估转岗可行性</p>
    </div>

    <div class="career-layout">
      <!-- Left: Settings -->
      <div class="settings-card">
        <h4 class="card-title">学习计划设置</h4>
        <el-form label-position="top" class="plan-form">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="我的简历">
                <el-select v-model="planForm.resumeId" placeholder="选择简历" style="width:100%">
                  <el-option v-for="r in resumes" :key="r.id" :label="r.name" :value="r.id" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="目标岗位">
                <el-select v-model="planForm.targetPositionId" placeholder="选择目标岗位" filterable style="width:100%">
                  <el-option v-for="p in positions" :key="p.id" :label="`${p.name} (${p.salaryRange})`" :value="p.id" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="每周学习时长（小时）">
                <el-input-number v-model="planForm.weeklyHours" :min="1" :max="40" :step="1" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="计划总周数">
                <el-input-number v-model="planForm.totalWeeks" :min="1" :max="52" :step="1" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="目标行业">
                <el-select v-model="planForm.targetIndustry" style="width:100%">
                  <el-option v-for="ind in industryOptions" :key="ind" :label="ind" :value="ind" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="目标岗位类型">
                <el-select v-model="planForm.targetRoleType" style="width:100%">
                  <el-option v-for="r in roleOptions" :key="r" :label="r" :value="r" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="期望城市">
                <el-input v-model="planForm.preferredCity" placeholder="如 北京" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="薪资期望">
                <el-input v-model="planForm.salaryExpectation" placeholder="如 25K-40K" />
              </el-form-item>
            </el-col>
          </el-row>

          <div class="form-actions">
            <el-button type="primary" :loading="assessing" @click="runAssessment">
              <el-icon><Connection /></el-icon>开始转岗评估
            </el-button>
            <el-button :loading="saving" @click="savePlan">保存计划</el-button>
          </div>
        </el-form>
      </div>

      <!-- Right: Assessment Results -->
      <div class="result-area" v-if="assessment">
        <div class="result-hero">
          <div class="score-circle" :style="{ borderColor: getScoreColor(assessment.currentMatchDegree) }">
            <span class="score-num">{{ assessment.currentMatchDegree }}</span>
            <span class="score-label">匹配分</span>
          </div>
          <div class="hero-right">
            <div class="feasibility-badge" :style="{ background: feasibilityColors[assessment.feasibilityRating], color: '#fff' }">
              转岗可行性：{{ feasibilityLabels[assessment.feasibilityRating] }}
            </div>
            <div class="timeline-badge">
              <el-icon><Clock /></el-icon>预计学习周期：{{ assessment.learningTimeline }}
            </div>
            <div class="hours-badge">
              <el-icon><Timer /></el-icon>总学习时间：约 {{ planForm.weeklyHours * planForm.totalWeeks }} 小时
            </div>
          </div>
        </div>

        <!-- Skills -->
        <el-card class="res-card">
          <template #header><span class="card-h">可迁移技能</span></template>
          <div class="skill-tags">
            <el-tag v-for="sk in assessment.transferableSkills" :key="sk.id" type="success" effect="plain" size="large">
              {{ sk.name }} <span class="skill-level">{{ sk.level }}</span>
            </el-tag>
            <span v-if="!assessment.transferableSkills.length" class="no-data">无</span>
          </div>
        </el-card>

        <el-card class="res-card">
          <template #header><span class="card-h">需补充技能</span></template>
          <div class="skill-tags">
            <el-tag v-for="sk in assessment.missingSkills" :key="sk.id" type="danger" effect="plain" size="large">
              {{ sk.name }} <span class="skill-level">{{ sk.level }}</span>
            </el-tag>
            <span v-if="!assessment.missingSkills.length" class="no-data">无</span>
          </div>
        </el-card>

        <!-- Analysis -->
        <el-card class="res-card">
          <template #header><span class="card-h">推荐原因</span></template>
          <ul class="point-list">
            <li v-for="(reason, idx) in assessment.recommendationReasons" :key="idx">{{ reason }}</li>
          </ul>
        </el-card>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-card class="res-card">
              <template #header><span class="card-h" style="color:var(--success)">优势总结</span></template>
              <ul class="point-list">
                <li v-for="(a, idx) in assessment.advantages" :key="idx">{{ a }}</li>
              </ul>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card class="res-card">
              <template #header><span class="card-h" style="color:var(--danger)">主要风险</span></template>
              <ul class="point-list">
                <li v-for="(r, idx) in assessment.risks" :key="idx">{{ r }}</li>
              </ul>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- Empty state -->
      <div v-else class="result-empty">
        <el-empty description="选择目标岗位并点击「开始转岗评估」查看分析结果">
          <template #image>
            <el-icon :size="60" color="var(--weak)"><TrendCharts /></el-icon>
          </template>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<style scoped>
.career-page { max-width: 1200px; margin: 0 auto; }

.page-head { margin-bottom: 24px; }
.page-head h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.head-sub { font-size: 14px; color: var(--muted); }

.career-layout { display: flex; flex-direction: column; gap: 24px; }

.settings-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 24px;
}
.card-title { font-size: 16px; font-weight: 700; margin-bottom: 20px; }

.plan-form .el-form-item { margin-bottom: 16px; }

.form-actions { display: flex; gap: 10px; margin-top: 8px; }

/* Results */
.result-hero {
  display: flex;
  align-items: center;
  gap: 32px;
  background: #fff;
  padding: 28px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.score-circle {
  width: 110px;
  height: 110px;
  border-radius: 50%;
  border: 5px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.score-num { font-size: 32px; font-weight: 800; color: var(--ink); }
.score-label { font-size: 12px; color: var(--muted); }

.hero-right { display: flex; flex-direction: column; gap: 10px; }
.feasibility-badge { display: inline-block; padding: 6px 16px; border-radius: 6px; font-size: 14px; font-weight: 600; width: fit-content; }
.timeline-badge, .hours-badge {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: var(--ink);
}

.res-card { margin-bottom: 16px; }
.card-h { font-size: 14px; font-weight: 600; }

.skill-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.skill-level {
  font-size: 11px;
  opacity: 0.7;
}
.no-data { font-size: 13px; color: var(--weak); }

.point-list {
  margin: 0;
  padding-left: 20px;
}
.point-list li {
  font-size: 13px;
  color: var(--ink);
  line-height: 1.8;
}

.result-empty {
  padding: 60px 0;
}
</style>
