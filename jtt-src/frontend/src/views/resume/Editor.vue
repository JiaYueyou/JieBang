<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { ResumeData } from '@/types'
import { mockResumes } from '@/mock/data/resume'
import { generateOptimizedPhrases } from '@/mock/data/tailor'

const route = useRoute()
const router = useRouter()

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

watch(() => route.params.id, (id) => {
  if (id) {
    const existing = mockResumes.find((r) => r.id === id)
    if (existing) Object.assign(resume, JSON.parse(JSON.stringify(existing)))
  }
}, { immediate: true })

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

const handleSave = () => {
  ElMessage.success('简历已保存')
  router.push('/resumes')
}
</script>

<template>
  <div class="editor-page">
    <div class="editor-header">
      <el-input v-model="resume.name" class="name-input" size="large" placeholder="简历名称" />
      <div>
        <el-button @click="router.back()">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </div>
    </div>

    <div class="editor-body">
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

        <el-card class="form-section">
          <template #header><span class="sec-title">工作经历</span></template>
          <div v-for="(exp, i) in resume.workExperience" :key="i" class="exp-block">
            <el-input v-model="exp.company" placeholder="公司" size="small" />
            <el-input v-model="exp.position" placeholder="职位" size="small" style="margin-top: 6px;" />
            <div class="textarea-wrapper">
              <el-input v-model="exp.description" type="textarea" :rows="3" placeholder="工作描述…" />
              <el-button class="ai-btn" :icon="'Edit'" text size="small" type="success" @click="openOptimizer(exp.description)">AI 优化</el-button>
            </div>
          </div>
          <el-button text type="primary" size="small">+ 添加经历</el-button>
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
          <div class="preview-section">
            <h4>工作经历</h4>
            <div v-for="exp in resume.workExperience" :key="exp.company" class="pv-exp">
              <h5>{{ exp.position }} - {{ exp.company }}</h5>
              <p>{{ exp.description }}</p>
            </div>
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

.exp-block {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--hairline);
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
