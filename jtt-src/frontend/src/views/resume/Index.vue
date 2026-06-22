<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { ResumeData } from '@/types'
import { mockResumes } from '@/mock/data/resume'

const router = useRouter()
const resumes = ref<ResumeData[]>([])

onMounted(() => { resumes.value = JSON.parse(JSON.stringify(mockResumes)) })

const goEditor = (id?: string) => router.push(`/resume/editor/${id || ''}`)
const goDetail = (id: string) => router.push(`/resume/${id}`)
const handleDuplicate = (id: string) => {
  const r = resumes.value.find((r) => r.id === id)
  if (r) {
    const dup = { ...r, id: `r-${Date.now()}`, name: `${r.name} (副本)`, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }
    resumes.value.unshift(dup)
  }
}
const handleDelete = (id: string) => {
  resumes.value = resumes.value.filter((r) => r.id !== id)
}
</script>

<template>
  <div class="resume-list-page">
    <div class="page-head">
      <h3>我的简历</h3>
      <el-button type="primary" @click="goEditor()">新建简历</el-button>
    </div>

    <div v-if="resumes.length === 0" class="empty">
      <el-empty description="暂无简历">
        <el-button type="primary" @click="router.push('/resume/upload')">上传简历</el-button>
      </el-empty>
    </div>

    <div v-else class="resume-grid">
      <div v-for="r in resumes" :key="r.id" class="resume-card" @click="goDetail(r.id)">
        <div class="card-icon">
          <el-icon :size="28"><Document /></el-icon>
        </div>
        <div class="card-info">
          <h4>{{ r.name }}</h4>
          <p class="card-meta">{{ r.targetPosition || '未指定方向' }} · {{ r.updatedAt }}</p>
          <div class="card-skills">
            <el-tag v-for="sk in r.skills.slice(0, 4)" :key="sk.id" size="small" class="skill-tag">
              {{ sk.name }}
            </el-tag>
          </div>
        </div>
        <div class="card-actions" @click.stop>
          <el-button :icon="'CopyDocument'" text size="small" @click="handleDuplicate(r.id)">复制</el-button>
          <el-button :icon="'Delete'" text size="small" type="danger" @click="handleDelete(r.id)">删除</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.resume-list-page { max-width: 1000px; margin: 0 auto; }

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-head h3 { font-size: 18px; font-weight: 700; }

.empty { padding: 60px 0; }

.resume-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.resume-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 20px;
  display: flex;
  gap: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.resume-card:hover { box-shadow: var(--shadow-hover); transform: translateY(-2px); }

.card-icon {
  width: 48px;
  height: 48px;
  background: var(--brand-light);
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--brand);
  flex-shrink: 0;
}

.card-info { flex: 1; min-width: 0; }
.card-info h4 { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
.card-meta { font-size: 12px; color: var(--muted); margin-bottom: 8px; }

.card-skills { display: flex; flex-wrap: wrap; gap: 4px; }
.skill-tag { --el-tag-bg-color: var(--brand-light); --el-tag-text-color: var(--brand); --el-tag-border-color: transparent; }

.card-actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
}
</style>
