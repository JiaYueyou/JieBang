<script setup lang="ts">
import { reactive, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useResumeStore } from '@/stores/resume'
import { usePositionsStore } from '@/stores/positions'
import { useMatchStore } from '@/stores/match'

const route = useRoute()
const router = useRouter()
const resumeStore = useResumeStore()
const positionsStore = usePositionsStore()
const matchStore = useMatchStore()

const activeTab = ref('editor')

// 编辑表单
const resume = reactive<any>({
  name: '', targetPosition: '',
  personalInfo: { name: '', email: '', phone: '', location: '' },
  jobIntent: { desiredPosition: '', desiredCity: '', salaryExpectation: '', workMode: 'fulltime' },
  education: [], workExperience: [], projects: [], skills: [], selfEvaluation: '',
})

const skillForm = reactive({ name: '', category: '' })
const addSkill = () => {
  if (!skillForm.name.trim()) return
  resume.skills.push({ name: skillForm.name.trim(), category: skillForm.category.trim() })
  skillForm.name = ''
  skillForm.category = ''
}

onMounted(async () => {
  const id = route.params.id as string
  if (id) {
    await resumeStore.fetchDetail(id)
    if (resumeStore.currentResume) {
      Object.assign(resume, JSON.parse(JSON.stringify(resumeStore.currentResume)))
    }
  }
  await positionsStore.fetchPositions()
})

const handleSave = async () => {
  const id = route.params.id as string
  await resumeStore.update(id, { ...resume })
  ElMessage.success('简历已保存')
}

// [Agent 3] 切换到匹配 Tab 时自动触发智能匹配
const handleAiOptimize = () => {
  activeTab.value = 'match'
  triggerAutoMatch()
}

// 自动匹配
const matching = ref(false)   // 复用：自动匹配中
const optimizing = ref(false)
const optimizeDone = ref(false)
const newResumeId = ref<string | null>(null)
const autoMatchDone = ref(false)

const triggerAutoMatch = async () => {
  const resumeId = route.params.id as string
  if (!resumeId || autoMatchDone.value) return
  matching.value = true
  try {
    await matchStore.doAutoMatch(resumeId)
    autoMatchDone.value = true
    // 若从岗位详情页跳转过来（带 positionId），自动展开对应岗位
    const focusPosId = route.query.positionId as string | undefined
    if (focusPosId) {
      const target = matchStore.batchResults.find(r => r.positionId === focusPosId)
      if (target) matchStore.selectBatchResult(target)
    }
  } finally {
    matching.value = false
  }
}

// 进入匹配 Tab 时自动触发
watch(activeTab, (tab) => {
  if (tab === 'match' && !autoMatchDone.value) {
    triggerAutoMatch()
  }
})

const handleOptimize = async () => {
  const resumeId = route.params.id as string
  optimizing.value = true
  try {
    const result = await matchStore.applyOptimization(resumeId)
    if (result) {
      newResumeId.value = String(result.newResumeId)
      optimizeDone.value = true
      ElMessage.success('AI 优化版简历已生成！')
    }
  } catch {
    ElMessage.error('优化失败，请稍后重试')
  } finally {
    optimizing.value = false
  }
}

const sectionLabel = (section: string) => {
  const map: Record<string, string> = {
    skills: '技能', workExperience: '工作经历',
    education: '教育经历', selfEvaluation: '自我评价',
  }
  return map[section] || section
}

const getScoreColor = (score: number) => {
  if (score >= 70) return '#22c55e'
  if (score >= 50) return '#eab308'
  return '#ef4444'
}
</script>

<template>
  <div class="detail-page">
    <!-- 头部 -->
    <div class="detail-header">
      <el-button text @click="router.push('/diagnosis')">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
      <el-tabs v-model="activeTab" class="main-tabs">
        <el-tab-pane label="编辑简历" name="editor" />
        <el-tab-pane label="简历匹配" name="match" />
      </el-tabs>
    </div>

    <!-- Tab: 编辑简历 -->
    <div v-if="activeTab === 'editor'" class="editor-layout">
      <div class="editor-form">
        <!-- 简历名称 -->
        <el-card class="form-card">
          <el-input v-model="resume.name" size="large" placeholder="简历名称" />
        </el-card>

        <!-- 基本信息 -->
        <el-card class="form-card">
          <template #header><span class="card-title">基本信息</span></template>
          <el-row :gutter="16">
            <el-col :span="12"><el-input v-model="resume.personalInfo.name" placeholder="姓名" /></el-col>
            <el-col :span="12"><el-input v-model="resume.personalInfo.email" placeholder="邮箱" /></el-col>
          </el-row>
          <el-row :gutter="16" style="margin-top: 12px">
            <el-col :span="12"><el-input v-model="resume.personalInfo.phone" placeholder="电话" /></el-col>
            <el-col :span="12"><el-input v-model="resume.personalInfo.location" placeholder="所在地" /></el-col>
          </el-row>
        </el-card>

        <!-- 求职意向 -->
        <el-card class="form-card">
          <template #header><span class="card-title">求职意向</span></template>
          <el-row :gutter="16">
            <el-col :span="12"><el-input v-model="resume.jobIntent.desiredPosition" placeholder="期望职位" /></el-col>
            <el-col :span="12"><el-input v-model="resume.jobIntent.desiredCity" placeholder="期望城市" /></el-col>
          </el-row>
          <el-row :gutter="16" style="margin-top: 12px">
            <el-col :span="12"><el-input v-model="resume.jobIntent.salaryExpectation" placeholder="期望薪资" /></el-col>
            <el-col :span="12">
              <el-select v-model="resume.jobIntent.workMode" style="width: 100%">
                <el-option label="全职" value="fulltime" />
                <el-option label="实习" value="intern" />
                <el-option label="远程" value="remote" />
              </el-select>
            </el-col>
          </el-row>
        </el-card>

        <!-- 教育经历 -->
        <el-card class="form-card">
          <template #header>
            <div class="section-header">
              <span class="card-title">教育经历</span>
              <el-button type="primary" text size="small" @click="resume.education.push({ school: '', degree: '', major: '', startDate: '', endDate: '' })">
                + 添加
              </el-button>
            </div>
          </template>
          <div v-if="!resume.education.length" class="empty-hint">暂无教育经历</div>
          <div v-for="(edu, i) in resume.education" :key="i" class="exp-block">
            <div class="exp-block-header">
              <span>教育 {{ Number(i) + 1 }}</span>
              <el-button type="danger" text size="small" @click="resume.education.splice(i, 1)">删除</el-button>
            </div>
            <el-row :gutter="12">
              <el-col :span="12"><el-input v-model="edu.school" placeholder="学校名称" /></el-col>
              <el-col :span="12"><el-input v-model="edu.major" placeholder="专业" /></el-col>
            </el-row>
            <el-row :gutter="12" style="margin-top: 8px">
              <el-col :span="8"><el-input v-model="edu.degree" placeholder="学历" /></el-col>
              <el-col :span="8"><el-input v-model="edu.startDate" placeholder="开始日期" /></el-col>
              <el-col :span="8"><el-input v-model="edu.endDate" placeholder="结束日期" /></el-col>
            </el-row>
          </div>
        </el-card>

        <!-- 工作经历 -->
        <el-card class="form-card">
          <template #header>
            <div class="section-header">
              <span class="card-title">工作经历</span>
              <el-button type="primary" text size="small" @click="resume.workExperience.push({ company: '', position: '', startDate: '', endDate: '', description: '', skills: [] })">
                + 添加
              </el-button>
            </div>
          </template>
          <div v-if="!resume.workExperience.length" class="empty-hint">暂无工作经历</div>
          <div v-for="(exp, i) in resume.workExperience" :key="i" class="exp-block">
            <div class="exp-block-header">
              <span>经历 {{ Number(i) + 1 }}</span>
              <el-button type="danger" text size="small" @click="resume.workExperience.splice(i, 1)">删除</el-button>
            </div>
            <el-row :gutter="12">
              <el-col :span="12"><el-input v-model="exp.company" placeholder="公司" /></el-col>
              <el-col :span="12"><el-input v-model="exp.position" placeholder="职位" /></el-col>
            </el-row>
            <el-row :gutter="12" style="margin-top: 8px">
              <el-col :span="12"><el-input v-model="exp.startDate" placeholder="开始日期" /></el-col>
              <el-col :span="12"><el-input v-model="exp.endDate" placeholder="结束日期" /></el-col>
            </el-row>
            <el-input v-model="exp.description" type="textarea" :rows="3" placeholder="工作描述..." style="margin-top: 8px" />
          </div>
        </el-card>

        <!-- 项目经历 -->
        <el-card class="form-card">
          <template #header>
            <div class="section-header">
              <span class="card-title">项目经历</span>
              <el-button type="primary" text size="small" @click="resume.projects.push({ name: '', role: '', description: '', technologies: [], highlights: [] })">
                + 添加
              </el-button>
            </div>
          </template>
          <div v-if="!resume.projects.length" class="empty-hint">暂无项目经历</div>
          <div v-for="(proj, i) in resume.projects" :key="i" class="exp-block">
            <div class="exp-block-header">
              <span>项目 {{ Number(i) + 1 }}</span>
              <el-button type="danger" text size="small" @click="resume.projects.splice(i, 1)">删除</el-button>
            </div>
            <el-row :gutter="12">
              <el-col :span="12"><el-input v-model="proj.name" placeholder="项目名称" /></el-col>
              <el-col :span="12"><el-input v-model="proj.role" placeholder="担任角色" /></el-col>
            </el-row>
            <el-input v-model="proj.description" type="textarea" :rows="3" placeholder="项目描述..." style="margin-top: 8px" />
          </div>
        </el-card>

        <!-- 技能 -->
        <el-card class="form-card">
          <template #header><span class="card-title">技能</span></template>
          <div class="skill-input-row">
            <el-input v-model="skillForm.name" placeholder="技能名称" style="width: 180px" @keyup.enter="addSkill" />
            <el-input v-model="skillForm.category" placeholder="类别" style="width: 160px" @keyup.enter="addSkill" />
            <el-button type="primary" size="small" @click="addSkill">添加</el-button>
          </div>
          <div v-if="resume.skills.length" class="skill-tags">
            <el-tag v-for="(skill, i) in resume.skills" :key="i" closable size="default" @close="resume.skills.splice(i, 1)">
              {{ skill.category ? skill.category + ' / ' : '' }}{{ skill.name }}
            </el-tag>
          </div>
          <div v-else class="empty-hint">暂无技能，在上方输入框中添加</div>
        </el-card>

        <!-- 自我评价 -->
        <el-card class="form-card">
          <template #header><span class="card-title">自我评价</span></template>
          <el-input v-model="resume.selfEvaluation" type="textarea" :rows="4" placeholder="简要介绍自己..." />
        </el-card>

        <!-- 操作按钮 -->
        <div class="form-actions">
          <el-button @click="router.back()">取消</el-button>
          <el-button type="success" plain @click="handleAiOptimize">AI 优化</el-button>
          <el-button type="primary" @click="handleSave">保存简历</el-button>
        </div>
      </div>

      <!-- 预览 -->
      <div class="editor-preview">
        <div class="preview-paper">
          <div class="preview-header">
            <h2>{{ resume.personalInfo?.name || '姓名' }}</h2>
            <p>{{ resume.personalInfo?.email }} | {{ resume.personalInfo?.phone }}</p>
          </div>
          <div class="preview-section" v-if="resume.jobIntent?.desiredPosition">
            <h4>求职意向</h4>
            <p>{{ resume.jobIntent.desiredPosition }} | {{ resume.jobIntent.desiredCity }} | {{ resume.jobIntent.salaryExpectation }}</p>
          </div>
          <div class="preview-section" v-if="resume.education?.length">
            <h4>教育经历</h4>
            <div v-for="edu in resume.education" :key="edu.school" class="pv-exp">
              <h5>{{ edu.degree }} - {{ edu.major }}</h5>
              <p>{{ edu.school }} | {{ edu.startDate }} - {{ edu.endDate }}</p>
            </div>
          </div>
          <div class="preview-section" v-if="resume.workExperience?.length">
            <h4>工作经历</h4>
            <div v-for="exp in resume.workExperience" :key="exp.company" class="pv-exp">
              <h5>{{ exp.position }} - {{ exp.company }}</h5>
              <p>{{ exp.description }}</p>
            </div>
          </div>
          <div class="preview-section" v-if="resume.projects?.length">
            <h4>项目经历</h4>
            <div v-for="proj in resume.projects" :key="proj.name" class="pv-exp">
              <h5>{{ proj.name }}</h5>
              <p>{{ proj.role }}</p>
              <p>{{ proj.description }}</p>
            </div>
          </div>
          <div class="preview-section" v-if="resume.skills?.length">
            <h4>技能</h4>
            <p>
              <el-tag v-for="skill in resume.skills" :key="skill.name" size="small" style="margin-right: 6px; margin-bottom: 4px;">
                {{ skill.name }}
              </el-tag>
            </p>
          </div>
          <div class="preview-section" v-if="resume.selfEvaluation">
            <h4>自我评价</h4>
            <p>{{ resume.selfEvaluation }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab: 简历匹配 —— [Agent 3] 自动匹配所有岗位，生成诊断报告 -->
    <div v-if="activeTab === 'match'" class="match-layout">
      <!-- 自动匹配入口 -->
      <el-card v-loading="matching">
        <template #header><span class="card-title">智能匹配诊断</span></template>
        <p class="match-intro">系统将自动分析您的简历，与所有岗位逐一匹配，生成诊断报告</p>
        <el-button v-if="!autoMatchDone && !matching" type="primary" @click="triggerAutoMatch">
          开始智能匹配
        </el-button>
        <el-button v-if="autoMatchDone && !matching" text @click="autoMatchDone = false; triggerAutoMatch()">重新匹配</el-button>
      </el-card>

      <!-- 匹配报告列表 + 详情（双栏布局） -->
      <div v-if="autoMatchDone && matchStore.batchResults.length > 0" class="match-results-layout">
        <!-- 左侧：岗位排名列表 -->
        <div class="match-rank-list">
          <h4>匹配岗位排名 ({{ matchStore.batchResults.length }})</h4>
          <div
            v-for="r in matchStore.batchResults"
            :key="r.positionId"
            class="rank-item"
            :class="{ active: matchStore.selectedBatchResult?.positionId === r.positionId }"
            @click="matchStore.selectBatchResult(r)"
          >
            <div class="rank-item-header">
              <span class="rank-pos-name">{{ r.positionName }}</span>
              <el-tag :type="r.totalScore >= 70 ? 'success' : r.totalScore >= 50 ? 'warning' : 'danger'" size="small">
                {{ r.totalScore }}分
              </el-tag>
            </div>
            <div class="rank-item-meta">
              匹配 {{ r.gapAnalysis?.matchSkills?.length || 0 }} 项，
              缺失 {{ r.gapAnalysis?.missingSkills?.length || 0 }} 项
            </div>
          </div>
        </div>

        <!-- 右侧：诊断报告详情 -->
        <div class="match-detail-panel" v-if="matchStore.selectedBatchResult">
          <el-card>
            <template #header>
              <div class="result-title">
                <span>诊断报告: {{ matchStore.selectedBatchResult.positionName }}</span>
                <el-tag :type="matchStore.selectedBatchResult.totalScore >= 70 ? 'success' : matchStore.selectedBatchResult.totalScore >= 50 ? 'warning' : 'danger'" size="large">
                  {{ matchStore.selectedBatchResult.totalScore }} 分
                </el-tag>
              </div>
            </template>

            <!-- 维度分数 -->
            <div class="dimensions" v-if="matchStore.selectedBatchResult.dimensions">
              <div v-for="dim in matchStore.selectedBatchResult.dimensions" :key="dim.name" class="dim-item">
                <div class="dim-header">
                  <span>{{ dim.name }}</span>
                  <span :style="{ color: dim.score >= 70 ? '#22c55e' : dim.score >= 50 ? '#eab308' : '#ef4444' }">{{ dim.score }}分</span>
                </div>
                <el-progress :percentage="dim.score" :color="dim.score >= 70 ? '#22c55e' : dim.score >= 50 ? '#eab308' : '#ef4444'" />
              </div>
            </div>

            <!-- 技能差距分析 -->
            <div v-if="matchStore.selectedBatchResult.gapAnalysis" class="gap-analysis">
              <h4>技能差距分析</h4>
              <div class="gap-sections">
                <div v-if="matchStore.selectedBatchResult.gapAnalysis.missingSkills?.length" class="gap-group">
                  <span class="gap-label missing">缺失技能</span>
                  <el-tag v-for="s in matchStore.selectedBatchResult.gapAnalysis.missingSkills" :key="s.name || s" size="small" type="danger" round>{{ s.name || s }}</el-tag>
                </div>
                <div v-if="matchStore.selectedBatchResult.gapAnalysis.weakSkills?.length" class="gap-group">
                  <span class="gap-label weak">薄弱技能（需加强）</span>
                  <el-tag v-for="s in matchStore.selectedBatchResult.gapAnalysis.weakSkills" :key="s.name || s" size="small" type="warning" round>{{ s.name || s }}</el-tag>
                </div>
                <div v-if="matchStore.selectedBatchResult.gapAnalysis.matchSkills?.length" class="gap-group">
                  <span class="gap-label match">已具备技能</span>
                  <el-tag v-for="s in matchStore.selectedBatchResult.gapAnalysis.matchSkills" :key="s.name || s" size="small" type="success" round>{{ s.name || s }}</el-tag>
                </div>
              </div>
            </div>

            <!-- 改进建议（规则生成） -->
            <div v-if="matchStore.selectedBatchResult.suggestions?.length" class="suggestions">
              <h4>改进建议</h4>
              <div v-for="sg in matchStore.selectedBatchResult.suggestions" :key="sg.id" class="sg-item">
                <p><strong>{{ sg.field }}</strong>: {{ sg.suggested }}</p>
                <span class="sg-reason">原因: {{ sg.reason }}</span>
              </div>
            </div>
          </el-card>

          <!-- AI 智能优化建议 -->
          <div v-if="matchStore.aiSuggestions.length > 0 || matchStore.suggestionsLoading" class="match-result">
            <el-card v-loading="matchStore.suggestionsLoading">
              <template #header>
                <div class="result-title">
                  <span>AI 智能优化建议</span>
                  <el-tag type="info" size="small">知识图谱验证</el-tag>
                </div>
              </template>

              <div class="ai-actions-bar">
                <el-button text size="small" @click="matchStore.aiSuggestions.forEach(s => s.accepted = true)">全部接受</el-button>
                <el-button text size="small" type="danger" @click="matchStore.aiSuggestions.forEach(s => s.accepted = false)">全部拒绝</el-button>
                <el-button
                  type="primary"
                  :loading="optimizing"
                  :disabled="matchStore.aiSuggestions.filter(s => s.accepted).length === 0"
                  @click="handleOptimize"
                >
                  一键优化简历 ({{ matchStore.aiSuggestions.filter(s => s.accepted).length }})
                </el-button>
              </div>

              <div class="ai-suggestions-list">
                <div v-for="sg in matchStore.aiSuggestions" :key="sg.id" class="ai-sg-item" :class="{ accepted: sg.accepted }">
                  <div class="ai-sg-header">
                    <span class="ai-sg-section">{{ sectionLabel(sg.section) }}</span>
                    <div class="ai-sg-tags">
                      <el-tag :type="sg.changeType === 'small' ? 'success' : 'warning'" size="small" effect="plain">
                        {{ sg.changeType === 'small' ? '小改' : '大改' }}
                      </el-tag>
                      <el-tooltip v-if="sg.warning" :content="sg.warning" placement="top">
                        <el-tag type="warning" size="small" effect="plain">
                          <el-icon><WarningFilled /></el-icon> 待确认
                        </el-tag>
                      </el-tooltip>
                      <el-tag v-if="sg.verified" type="success" size="small" effect="plain">
                        <el-icon><CircleCheckFilled /></el-icon> 已验证
                      </el-tag>
                    </div>
                  </div>
                  <p class="ai-sg-reason">{{ sg.reason }}</p>
                  <div class="ai-sg-diff">
                    <div v-if="sg.original" class="diff-line removed">
                      <span class="diff-marker">-</span>{{ sg.original }}
                    </div>
                    <div class="diff-line added">
                      <span class="diff-marker">+</span>{{ sg.suggested }}
                    </div>
                  </div>
                  <div class="ai-sg-footer">
                    <el-button
                      :type="sg.accepted ? 'success' : 'default'"
                      :plain="!sg.accepted"
                      size="small"
                      @click="matchStore.toggleAiSuggestion(sg.id)"
                    >
                      {{ sg.accepted ? '已接受' : '接受建议' }}
                    </el-button>
                  </div>
                </div>
              </div>
              <el-empty v-if="!matchStore.suggestionsLoading && matchStore.aiSuggestions.length === 0" description="暂无智能优化建议" :image-size="60" />
            </el-card>
          </div>
        </div>

        <div v-else class="empty-hint" style="text-align: center; padding: 80px 0">
          <p>点击左侧岗位查看详细诊断报告</p>
        </div>
      </div>

      <!-- 优化结果 -->
      <div v-if="optimizeDone && newResumeId" class="match-result">
        <el-card>
          <template #header><span class="card-title">优化完成</span></template>
          <el-result icon="success" title="AI 优化版简历已生成" sub-title="已保存为新简历，可在简历列表中查看">
            <template #extra>
              <el-button type="primary" @click="router.push(`/diagnosis/${newResumeId}`)">查看优化版简历</el-button>
              <el-button @click="router.push('/diagnosis')">返回简历列表</el-button>
            </template>
          </el-result>
        </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-page { max-width: 1200px; margin: 0 auto; }
.detail-header {
  display: flex; align-items: center; gap: 16px;
  background: #fff; padding: 8px 20px; border-radius: var(--radius);
  box-shadow: var(--shadow); margin-bottom: 20px;
}
.main-tabs { flex: 1; }

.editor-layout { display: grid; grid-template-columns: 1fr 400px; gap: 20px; }
.editor-form { min-width: 0; }
.form-card { margin-bottom: 16px; }
.card-title { font-size: 15px; font-weight: 600; }
.section-header { display: flex; align-items: center; justify-content: space-between; width: 100%; }
.exp-block { margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px solid var(--hairline); }
.exp-block-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; font-size: 13px; font-weight: 600; color: var(--muted); }

.form-actions {
  display: flex; gap: 10px; justify-content: flex-end;
  background: #fff; padding: 16px 20px; border-radius: var(--radius);
  box-shadow: var(--shadow); margin-bottom: 20px;
}

/* Preview */
.editor-preview { position: sticky; top: 20px; }
.preview-paper {
  background: #fff; padding: 40px 36px; box-shadow: var(--shadow-hover);
  border-radius: 4px; min-height: 600px; font-size: 13px; line-height: 1.6;
}
.preview-header { text-align: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid var(--ink); }
.preview-header h2 { font-size: 20px; font-weight: 700; }
.preview-header p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.preview-section { margin-bottom: 20px; }
.preview-section h4 { font-size: 14px; font-weight: 700; padding-bottom: 6px; border-bottom: 1px solid var(--hairline); margin-bottom: 10px; }
.pv-exp { margin-bottom: 10px; }
.pv-exp h5 { font-size: 13px; font-weight: 600; }
.pv-exp p { font-size: 12px; color: var(--muted); margin-top: 2px; }

/* Match */
.match-layout { max-width: 1100px; }
.match-intro { font-size: 14px; color: var(--muted); margin-bottom: 12px; }

/* 匹配结果双栏布局 */
.match-results-layout {
  display: grid; grid-template-columns: 280px 1fr; gap: 20px;
  margin-top: 20px; align-items: start;
}
.match-rank-list {
  background: #fff; border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 16px;
  position: sticky; top: 20px; max-height: calc(100vh - 140px); overflow-y: auto;
}
.match-rank-list h4 { font-size: 14px; font-weight: 600; margin-bottom: 12px; }
.rank-item {
  padding: 12px; border-radius: 8px; cursor: pointer;
  border: 1px solid var(--hairline); margin-bottom: 8px;
  transition: all 0.2s;
}
.rank-item:hover { border-color: var(--brand); background: var(--brand-light); }
.rank-item.active { border-color: var(--brand); background: var(--brand-light); }
.rank-item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.rank-pos-name { font-size: 14px; font-weight: 600; }
.rank-item-meta { font-size: 12px; color: var(--muted); }
.match-detail-panel { min-width: 0; }
.result-title { display: flex; justify-content: space-between; align-items: center; font-size: 16px; font-weight: 600; }
.dimensions { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }
.dim-header { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }

.gap-analysis { margin-bottom: 20px; }
.gap-analysis h4, .suggestions h4 { font-size: 15px; margin-bottom: 10px; }
.gap-sections { display: flex; flex-direction: column; gap: 10px; }
.gap-group { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.gap-label { font-size: 12px; font-weight: 600; min-width: 60px; }
.gap-label.missing { color: #ef4444; }
.gap-label.weak { color: #eab308; }
.gap-label.match { color: #22c55e; }

.sg-item { background: var(--canvas); padding: 10px 14px; border-radius: 6px; margin-bottom: 8px; }
.sg-item p { font-size: 13px; margin-bottom: 4px; }
.sg-reason { font-size: 12px; color: var(--muted); }

.match-result { margin-top: 20px; }
.empty-hint { font-size: 13px; color: var(--muted); padding: 12px 0; }
.skill-input-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.skill-tags { display: flex; flex-wrap: wrap; gap: 8px; }

/* AI Suggestions */
.ai-actions-bar {
  display: flex; align-items: center; gap: 10px;
  padding-bottom: 12px; margin-bottom: 12px;
  border-bottom: 1px solid var(--hairline);
}

.ai-suggestions-list { display: flex; flex-direction: column; gap: 12px; }

.ai-sg-item {
  padding: 16px; border: 1px solid var(--hairline);
  border-radius: var(--radius); transition: all 0.2s;
}
.ai-sg-item.accepted { border-color: var(--brand); background: var(--brand-light); }

.ai-sg-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.ai-sg-section { font-size: 13px; font-weight: 600; }
.ai-sg-tags { display: flex; gap: 6px; }
.ai-sg-reason { font-size: 13px; color: var(--muted); margin-bottom: 10px; }
.ai-sg-diff { background: #fafafa; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; }
.diff-line { font-size: 13px; line-height: 1.5; padding: 2px 0; }
.diff-line.removed { color: var(--danger); text-decoration: line-through; }
.diff-line.added { color: var(--brand); }
.diff-marker { display: inline-block; width: 18px; font-weight: 700; }
.ai-sg-footer { display: flex; gap: 8px; }
</style>
