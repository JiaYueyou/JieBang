<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { ResumeData } from '@/types'
import { mockResumes } from '@/mock/data/resume'
import { pageData } from '@/stores/pageContext'

const route = useRoute()
const router = useRouter()
const resume = ref<ResumeData | null>(null)

onMounted(() => {
  resume.value = mockResumes.find((r) => r.id === route.params.id) || null
})
// Share resume data with AI assistant
watch(resume, (r) => { pageData.resume = r }, { immediate: true })
onUnmounted(() => {
  if (pageData.resume?.id === resume.value?.id) pageData.resume = null
})
</script>

<template>
  <div class="detail-page" v-if="resume">
    <div class="page-head">
      <div>
        <h3>{{ resume.name }}</h3>
        <span class="sub">{{ resume.targetPosition || '未指定方向' }}</span>
      </div>
      <div class="head-actions">
        <el-button @click="router.push(`/resume/editor/${resume.id}`)">编辑</el-button>
        <el-button type="primary" @click="router.push(`/diagnosis`)">开始诊断</el-button>
      </div>
    </div>

    <div class="resume-sections">
      <el-card class="sec">
        <template #header><span class="sec-title">基本信息</span></template>
        <div class="info-grid">
          <div><span class="lbl">姓名</span><span>{{ resume.personalInfo.name }}</span></div>
          <div><span class="lbl">邮箱</span><span>{{ resume.personalInfo.email }}</span></div>
          <div><span class="lbl">电话</span><span>{{ resume.personalInfo.phone }}</span></div>
          <div><span class="lbl">所在地</span><span>{{ resume.personalInfo.location }}</span></div>
        </div>
      </el-card>

      <el-card class="sec">
        <template #header><span class="sec-title">教育经历</span></template>
        <div v-for="edu in resume.education" :key="edu.school" class="exp-item">
          <h4>{{ edu.school }}</h4>
          <p>{{ edu.degree }} · {{ edu.major }} · {{ edu.startDate }} - {{ edu.endDate }}</p>
        </div>
      </el-card>

      <el-card class="sec">
        <template #header><span class="sec-title">工作经历</span></template>
        <div v-for="exp in resume.workExperience" :key="exp.company" class="exp-item">
          <h4>{{ exp.position }} @ {{ exp.company }}</h4>
          <p class="exp-date">{{ exp.startDate }} - {{ exp.endDate }}</p>
          <p class="exp-desc">{{ exp.description }}</p>
        </div>
      </el-card>

      <el-card class="sec">
        <template #header><span class="sec-title">技能清单</span></template>
        <div class="skill-list">
          <div v-for="sk in resume.skills" :key="sk.id" class="skill-chip" :class="sk.level">
            {{ sk.name }}
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.detail-page { max-width: 800px; margin: 0 auto; }

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  padding: 20px 24px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin-bottom: 20px;
}

.page-head h3 { font-size: 18px; font-weight: 700; }
.sub { font-size: 13px; color: var(--muted); }
.head-actions { display: flex; gap: 8px; }

.sec { margin-bottom: 16px; }
.sec-title { font-size: 15px; font-weight: 600; }

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.info-grid .lbl {
  font-size: 13px;
  color: var(--muted);
  margin-right: 8px;
}

.info-grid span {
  font-size: 14px;
  color: var(--ink);
}

.exp-item { margin-bottom: 14px; }
.exp-item h4 { font-size: 14px; font-weight: 600; }
.exp-item p { font-size: 13px; color: var(--muted); margin-top: 2px; }
.exp-date { font-size: 12px; color: var(--weak); }
.exp-desc { margin-top: 4px; line-height: 1.5; }

.skill-list { display: flex; flex-wrap: wrap; gap: 8px; }

.skill-chip {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.skill-chip.advanced { background: var(--brand-light); color: var(--brand); }
.skill-chip.required { background: #E6F7FF; color: #1890FF; }
.skill-chip.preferred { background: var(--canvas); color: var(--muted); border: 1px solid var(--hairline); }
</style>
