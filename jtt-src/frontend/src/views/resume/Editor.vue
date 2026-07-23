<script setup lang="ts">
import { reactive, ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResumeStore } from '@/stores/resume'
import { ElMessage } from 'element-plus'
import type { ResumeData } from '@/types'
import { generateOptimizedPhrases } from '@/mock/data/tailor'

const route = useRoute()
const router = useRouter()
const resumeStore = useResumeStore()

const loading = ref(false)
const saving = ref(false)
const isEdit = ref(false)

const resume = reactive<Partial<ResumeData>>({
  name: '新建简历',
  personalInfo: { name: '', email: '', phone: '', location: '' },
  jobIntent: { desiredPosition: '', desiredCity: '', salaryExpectation: '', workMode: 'fulltime' },
  education: [],
  workExperience: [],
  projects: [],
  skills: [],
  selfEvaluation: '',
})

const skillForm = reactive({ name: '', category: '' })
const addSkill = () => {
  if (!skillForm.name.trim()) return
  resume.skills!.push({ name: skillForm.name.trim(), category: skillForm.category.trim() })
  skillForm.name = ''
  skillForm.category = ''
}

onMounted(async () => {
  const id = route.params.id as string | undefined
  if (!id) return
  isEdit.value = true
  loading.value = true
  try {
    await resumeStore.fetchDetail(id)
    const data = resumeStore.currentResume
    if (data) Object.assign(resume, JSON.parse(JSON.stringify(data)))
  } catch {
    ElMessage.warning('加载简历失败，使用离线数据')
  } finally {
    loading.value = false
  }
})

// AI phrase optimization
const showOptimizer = ref(false)
const optimizingText = ref('')
const optimizedResults = ref<string[]>([])
const optimizeStyle = ref<'professional' | 'concise' | 'match' | 'impact'>('professional')

const openOptimizer = (text: string) => {
  if (!text.trim()) {
    ElMessage.warning('请先选中文字')
    return
  }
  optimizingText.value = text
  optimizedResults.value = generateOptimizedPhrases(text, optimizeStyle.value)
  showOptimizer.value = true
}

const changeStyle = (style: typeof optimizeStyle.value) => {
  optimizeStyle.value = style
  optimizedResults.value = generateOptimizedPhrases(optimizingText.value, style)
}

const applyPhrase = (phrase: string, field: keyof typeof resume) => {
  if (field === 'selfEvaluation') {
    resume.selfEvaluation = phrase
  }
  showOptimizer.value = false
  ElMessage.success('已应用优化语句')
}

const handleSave = async () => {
  if (!resume.name?.trim()) {
    ElMessage.warning('请输入简历名称')
    return
  }
  saving.value = true
  try {
    if (isEdit.value && route.params.id) {
      await resumeStore.update(route.params.id as string, resume)
      ElMessage.success('简历已更新')
    } else {
      await resumeStore.create(resume)
      ElMessage.success('简历已创建')
    }
    router.push('/diagnosis')
  } catch {
    ElMessage.error('保存失败，请重试')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="editor-page">
    <div class="editor-header">
      <el-input v-model="resume.name" class="name-input" size="large" placeholder="简历名称" />
      <div>
        <el-button @click="router.back()">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </div>
    </div>

    <div v-if="loading" class="editor-loading">
      <el-icon class="loading-spin" :size="32"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <div v-else class="editor-body">
      <!-- Left: Form -->
      <div class="editor-form">
        <el-card class="form-section">
          <template #header><span class="sec-title">基本信息</span></template>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-input v-model="resume.personalInfo!.name" placeholder="姓名" />
            </el-col>
            <el-col :span="12">
              <el-input v-model="resume.personalInfo!.email" placeholder="邮箱" />
            </el-col>
          </el-row>
          <el-row :gutter="16" style="margin-top: 12px;">
            <el-col :span="12">
              <el-input v-model="resume.personalInfo!.phone" placeholder="电话" />
            </el-col>
            <el-col :span="12">
              <el-input v-model="resume.personalInfo!.location" placeholder="所在地" />
            </el-col>
          </el-row>
        </el-card>

        <!-- 教育经历 -->
        <el-card class="form-section">
          <template #header>
            <div class="section-header">
              <span class="sec-title">教育经历</span>
              <el-button type="primary" text size="small" @click="resume.education!.push({ school: '', degree: '', major: '', startDate: '', endDate: '' })">
                + 添加
              </el-button>
            </div>
          </template>
          <div v-if="!resume.education?.length" class="empty-hint">暂无教育经历，点击"添加"录入</div>
          <div v-for="(edu, i) in resume.education" :key="i" class="exp-block">
            <div class="exp-block-header">
              <span>教育 {{ i + 1 }}</span>
              <el-button type="danger" text size="small" @click="resume.education!.splice(i, 1)">删除</el-button>
            </div>
            <el-row :gutter="12">
              <el-col :span="12"><el-input v-model="edu.school" placeholder="学校名称" /></el-col>
              <el-col :span="12"><el-input v-model="edu.major" placeholder="专业" /></el-col>
            </el-row>
            <el-row :gutter="12" style="margin-top: 10px;">
              <el-col :span="8"><el-input v-model="edu.degree" placeholder="学历" /></el-col>
              <el-col :span="8"><el-input v-model="edu.startDate" placeholder="开始日期" /></el-col>
              <el-col :span="8"><el-input v-model="edu.endDate" placeholder="结束日期" /></el-col>
            </el-row>
          </div>
        </el-card>

        <el-card class="form-section">
          <template #header>
            <div class="section-header">
              <span class="sec-title">工作经历</span>
              <el-button type="primary" text size="small" @click="resume.workExperience!.push({ company: '', position: '', startDate: '', endDate: '', description: '', skills: [] })">
                + 添加
              </el-button>
            </div>
          </template>
          <div v-if="!resume.workExperience?.length" class="empty-hint">暂无工作经历，点击"添加"录入</div>
          <div v-for="(exp, i) in resume.workExperience" :key="i" class="exp-block">
            <div class="exp-block-header">
              <span>经历 {{ i + 1 }}</span>
              <el-button type="danger" text size="small" @click="resume.workExperience!.splice(i, 1)">删除</el-button>
            </div>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-input v-model="exp.company" placeholder="公司名称" />
              </el-col>
              <el-col :span="12">
                <el-input v-model="exp.position" placeholder="职位" />
              </el-col>
            </el-row>
            <el-row :gutter="12" style="margin-top: 10px;">
              <el-col :span="12">
                <el-input v-model="exp.startDate" placeholder="开始日期" />
              </el-col>
              <el-col :span="12">
                <el-input v-model="exp.endDate" placeholder="结束日期" />
              </el-col>
            </el-row>
            <div style="margin-top: 10px;">
              <div class="textarea-wrapper">
                <el-input v-model="exp.description" type="textarea" :rows="3" placeholder="工作内容描述" />
                <el-button class="ai-btn" text size="small" type="success" @click="openOptimizer(exp.description || '')">AI 优化</el-button>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 项目经历 -->
        <el-card class="form-section">
          <template #header>
            <div class="section-header">
              <span class="sec-title">项目经历</span>
              <el-button type="primary" text size="small" @click="resume.projects!.push({ name: '', role: '', description: '', technologies: [], highlights: [] })">
                + 添加
              </el-button>
            </div>
          </template>
          <div v-if="!resume.projects?.length" class="empty-hint">暂无项目经历，点击"添加"录入</div>
          <div v-for="(proj, i) in resume.projects" :key="i" class="exp-block">
            <div class="exp-block-header">
              <span>项目 {{ i + 1 }}</span>
              <el-button type="danger" text size="small" @click="resume.projects!.splice(i, 1)">删除</el-button>
            </div>
            <el-row :gutter="12">
              <el-col :span="12"><el-input v-model="proj.name" placeholder="项目名称" /></el-col>
              <el-col :span="12"><el-input v-model="proj.role" placeholder="担任角色" /></el-col>
            </el-row>
            <div style="margin-top: 10px;">
              <el-input v-model="proj.description" type="textarea" :rows="3" placeholder="项目描述" />
            </div>
          </div>
        </el-card>

        <!-- 技能 -->
        <el-card class="form-section">
          <template #header><span class="sec-title">技能</span></template>
          <div class="skill-input-row">
            <el-input v-model="skillForm.name" placeholder="技能名称" style="width: 180px" @keyup.enter="addSkill" />
            <el-input v-model="skillForm.category" placeholder="类别" style="width: 160px" @keyup.enter="addSkill" />
            <el-button type="primary" size="small" @click="addSkill">添加</el-button>
          </div>
          <div v-if="resume.skills?.length" class="skill-tags">
            <el-tag v-for="(skill, i) in resume.skills" :key="i" closable size="default" @close="resume.skills!.splice(i, 1)">
              {{ skill.category ? skill.category + ' / ' : '' }}{{ skill.name }}
            </el-tag>
          </div>
          <div v-else class="empty-hint">暂无技能，在上方输入框中添加</div>
        </el-card>

        <el-card class="form-section">
          <template #header><span class="sec-title">自我评价</span></template>
          <div class="textarea-wrapper">
            <el-input v-model="resume.selfEvaluation" type="textarea" :rows="4" placeholder="简要介绍自己…" />
            <el-button class="ai-btn" :icon="'Edit'" text size="small" type="success" @click="openOptimizer(resume.selfEvaluation || '')">AI 优化</el-button>
          </div>
        </el-card>
      </div>

      <!-- Right: Preview -->
      <div class="editor-preview">
        <div class="preview-paper">
          <div class="preview-header">
            <h2>{{ resume.personalInfo?.name || '姓名' }}</h2>
            <p>{{ resume.personalInfo?.email }} | {{ resume.personalInfo?.phone }}</p>
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

    <!-- AI Phrase Optimizer Dialog -->
    <el-dialog v-model="showOptimizer" title="AI 语句优化" width="520px">
      <div class="optimizer-org">
        <span class="opt-label">原文：</span>
        <p>{{ optimizingText }}</p>
      </div>
      <div class="style-select">
        <span class="opt-label">风格：</span>
        <el-radio-group v-model="optimizeStyle" @change="changeStyle(optimizeStyle)">
          <el-radio-button value="professional">更专业</el-radio-button>
          <el-radio-button value="concise">更简洁</el-radio-button>
          <el-radio-button value="match">更匹配</el-radio-button>
          <el-radio-button value="impact">更有冲击力</el-radio-button>
        </el-radio-group>
      </div>
      <div class="opt-results">
        <div v-for="(text, i) in optimizedResults" :key="i" class="opt-item" @click="applyPhrase(text, 'selfEvaluation')">
          <span class="opt-num">{{ i + 1 }}</span>
          <p>{{ text }}</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.editor-page { max-width: 1200px; margin: 0 auto; }

.editor-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 80px 0;
  color: var(--muted);
  font-size: 14px;
}

.loading-spin { animation: spin 1s linear infinite; color: var(--brand); }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  padding: 12px 20px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin-bottom: 20px;
}

.name-input { width: 320px; }
.name-input :deep(.el-input__inner) { border: none; font-size: 18px; font-weight: 700; }

.editor-body {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 20px;
}

.editor-form { min-width: 0; }

.form-section {
  margin-bottom: 16px;
}

.sec-title { font-size: 15px; font-weight: 600; }

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.empty-hint {
  color: var(--muted);
  font-size: 13px;
  text-align: center;
  padding: 24px 0;
}

.skill-input-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.skill-tags { display: flex; flex-wrap: wrap; gap: 8px; }

.exp-block {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--hairline);
}

.exp-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}

.textarea-wrapper { position: relative; margin-top: 6px; }

.ai-btn {
  position: absolute;
  right: 8px;
  bottom: 8px;
  color: var(--brand) !important;
}

/* Preview */
.editor-preview {
  position: sticky;
  top: 20px;
}

.preview-paper {
  background: #fff;
  padding: 40px 36px;
  box-shadow: var(--shadow-hover);
  border-radius: 4px;
  min-height: 600px;
  font-size: 13px;
  line-height: 1.6;
}

.preview-header {
  text-align: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid var(--ink);
}

.preview-header h2 { font-size: 20px; font-weight: 700; }
.preview-header p { font-size: 12px; color: var(--muted); margin-top: 4px; }

.preview-section { margin-bottom: 20px; }
.preview-section h4 {
  font-size: 14px;
  font-weight: 700;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--hairline);
  margin-bottom: 10px;
}

.pv-exp { margin-bottom: 10px; }
.pv-exp h5 { font-size: 13px; font-weight: 600; }
.pv-exp p { font-size: 12px; color: var(--muted); margin-top: 2px; }

/* Optimizer */
.optimizer-org { margin-bottom: 16px; }
.optimizer-org p { font-size: 13px; color: var(--muted); padding: 8px; background: var(--canvas); border-radius: 6px; }

.opt-label { font-size: 13px; font-weight: 600; margin-bottom: 6px; display: block; }

.style-select { margin-bottom: 16px; }

.opt-results { display: flex; flex-direction: column; gap: 8px; }

.opt-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.15s;
}

.opt-item:hover {
  border-color: var(--brand);
  background: var(--brand-light);
}

.opt-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--canvas);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.opt-item p { font-size: 13px; color: var(--ink); line-height: 1.5; }
</style>
