<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useResumeStore } from '@/stores/resume'
import { useMatchStore } from '@/stores/match'
import type { ResumeData, MatchResult } from '@/types'
import { ElMessage } from 'element-plus'
import MatchPanel from '@/components/diagnosis/MatchPanel.vue'

const router = useRouter()
const resumeStore = useResumeStore()
const matchStore = useMatchStore()

const resumes = ref<ResumeData[]>([])
const expandedResumeId = ref<string | null>(null)
const matchResults = ref<Record<string, MatchResult[]>>({})
const loadingMatch = ref<Record<string, boolean>>({})

// Upload dialog
const uploadVisible = ref(false)
const uploadFile = ref<File | null>(null)
const uploading = ref(false)
const uploadDragging = ref(false)

onMounted(async () => {
  try {
    await resumeStore.fetchList()
    resumes.value = resumeStore.resumes
  } catch {
    // Mock fallback
    const { mockResumes } = await import('@/mock/data/resume')
    resumes.value = JSON.parse(JSON.stringify(mockResumes))
  }
})

// Toggle expand & load match results
const toggleExpand = async (resumeId: string) => {
  if (expandedResumeId.value === resumeId) {
    expandedResumeId.value = null
    return
  }
  expandedResumeId.value = resumeId
  if (!matchResults.value[resumeId]) {
    loadingMatch.value[resumeId] = true
    try {
      const results = await matchStore.autoDetect(resumeId)
      matchResults.value[resumeId] = results || []
    } catch {
      ElMessage.error('加载匹配结果失败')
      matchResults.value[resumeId] = []
    } finally {
      loadingMatch.value[resumeId] = false
    }
  }
}

// Upload handlers
const handleUploadDrop = (e: DragEvent) => {
  const file = e.dataTransfer?.files?.[0]
  if (file) validateAndSetFile(file)
}
const handleFileChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) validateAndSetFile(file)
}
const validateAndSetFile = (file: File) => {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!ext || !['pdf', 'doc', 'docx'].includes(ext)) {
    ElMessage.error('仅支持 PDF、Word 格式文件')
    return
  }
  uploadFile.value = file
}

const startUpload = async () => {
  if (!uploadFile.value) return
  uploading.value = true
  try {
    await resumeStore.uploadFile(uploadFile.value)
    resumes.value = resumeStore.resumes
    ElMessage.success('简历解析完成')
    uploadVisible.value = false
    uploadFile.value = null
  } catch {
    // Mock fallback
    const { mockResumes } = await import('@/mock/data/resume')
    const newResume = JSON.parse(JSON.stringify(mockResumes[0]))
    newResume.id = `r-${Date.now()}`
    newResume.name = uploadFile.value.name.replace(/\.(pdf|doc|docx)$/i, '')
    newResume.sourceFile = uploadFile.value.name
    newResume.createdAt = new Date().toISOString()
    resumes.value.unshift(newResume)
    ElMessage.success('简历解析完成（离线模式）')
    uploadVisible.value = false
    uploadFile.value = null
  } finally {
    uploading.value = false
  }
}

const goEditor = (id?: string) => router.push(`/resume/editor/${id || ''}`)
const handleDuplicate = (id: string) => {
  const r = resumes.value.find((r) => r.id === id)
  if (r) {
    const dup = { ...r, id: `r-${Date.now()}`, name: `${r.name} (副本)`, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }
    resumes.value.unshift(dup)
  }
}
const handleDelete = (id: string) => {
  resumes.value = resumes.value.filter((r) => r.id !== id)
  if (expandedResumeId.value === id) expandedResumeId.value = null
}
const getScoreColor = (score: number) => {
  if (score >= 80) return 'var(--success)'
  if (score >= 50) return 'var(--warning)'
  return 'var(--danger)'
}

// Compute best match score for a resume (for card display)
const bestScoreFor = (resumeId: string): MatchResult | null => {
  const results = matchResults.value[resumeId]
  if (!results || results.length === 0) return null
  return results.reduce((best, r) => r.totalScore > best.totalScore ? r : best, results[0])
}
</script>

<template>
  <div class="diagnosis-page">
    <!-- Action Bar -->
    <div class="action-bar">
      <h3>简历诊断</h3>
      <div class="action-buttons">
        <el-button type="primary" @click="uploadVisible = true">
          <el-icon class="btn-icon"><Upload /></el-icon>上传简历
        </el-button>
        <el-button @click="goEditor()">
          <el-icon class="btn-icon"><Edit /></el-icon>新建简历
        </el-button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="resumes.length === 0" class="empty-state">
      <el-empty description="暂无简历，上传或创建一份简历开始诊断">
        <el-button type="primary" @click="uploadVisible = true">上传简历</el-button>
        <el-button @click="goEditor()">新建简历</el-button>
      </el-empty>
    </div>

    <!-- Resume Grid -->
    <div v-else class="resume-grid">
      <div
        v-for="r in resumes"
        :key="r.id"
        class="resume-card"
        :class="{ expanded: expandedResumeId === r.id }"
      >
        <div class="card-main" @click="toggleExpand(r.id)">
          <div class="card-icon">
            <el-icon :size="24"><Document /></el-icon>
          </div>
          <div class="card-info">
            <h4>{{ r.name }}</h4>
            <p class="card-meta">{{ r.targetPosition || '未指定方向' }} · {{ r.updatedAt }}</p>
            <div class="card-skills">
              <el-tag v-for="sk in r.skills.slice(0, 4)" :key="sk.id" size="small" class="skill-tag">
                {{ sk.name }}
              </el-tag>
            </div>
            <!-- Mini match scores -->
            <div v-if="matchResults[r.id]" class="card-mini-scores">
              <span
                v-for="mr in matchResults[r.id].slice(0, 3)"
                :key="mr.positionId"
                class="mini-score"
                :style="{ color: getScoreColor(mr.totalScore) }"
              >
                {{ mr.positionName }} {{ mr.totalScore }}分
              </span>
            </div>
            <div v-else-if="loadingMatch[r.id]" class="card-mini-loading">
              <el-icon class="loading-icon"><Loading /></el-icon>正在匹配...
            </div>
          </div>
          <div class="card-actions" @click.stop>
            <el-button :icon="'CopyDocument'" text size="small" @click="handleDuplicate(r.id)">复制</el-button>
            <el-button :icon="'Delete'" text size="small" type="danger" @click="handleDelete(r.id)">删除</el-button>
          </div>
          <div class="card-expand-icon">
            <el-icon :size="20"><ArrowDown /></el-icon>
          </div>
        </div>

        <!-- Expanded match panel -->
        <div v-if="expandedResumeId === r.id" class="card-expand-body">
          <div v-if="loadingMatch[r.id]" class="expand-loading">
            <el-icon class="loading-spin" :size="32"><Loading /></el-icon>
            <span>正在匹配诊断...</span>
          </div>
          <MatchPanel
            v-else-if="matchResults[r.id] && matchResults[r.id].length > 0"
            :results="matchResults[r.id]"
            :resume-id="r.id"
            @edit="goEditor"
          />
          <div v-else class="expand-empty">
            <el-empty description="暂无匹配结果" />
          </div>
        </div>
      </div>
    </div>

    <!-- Upload Dialog -->
    <el-dialog v-model="uploadVisible" title="上传简历" width="480px" :close-on-click-modal="false">
      <div
        class="upload-zone"
        :class="{ dragging: uploadDragging }"
        @dragover.prevent="uploadDragging = true"
        @dragleave="uploadDragging = false"
        @drop.prevent="handleUploadDrop($event as DragEvent); uploadDragging = false"
      >
        <template v-if="!uploadFile">
          <el-icon :size="40" class="upload-icon"><UploadFilled /></el-icon>
          <p class="upload-hint">拖拽文件到此处，或</p>
          <label class="upload-label-btn">点击上传
            <input type="file" accept=".pdf,.doc,.docx" hidden @change="handleFileChange" />
          </label>
          <p class="upload-note">支持 PDF、Word 格式 (.pdf / .doc / .docx)</p>
        </template>
        <template v-else>
          <el-icon :size="40" class="upload-file-icon"><Document /></el-icon>
          <p class="upload-filename">{{ uploadFile.name }}</p>
          <p class="upload-filesize">{{ (uploadFile.size / 1024).toFixed(1) }} KB</p>
          <el-button text type="danger" size="small" @click="uploadFile = null">移除</el-button>
        </template>
      </div>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!uploadFile" :loading="uploading" @click="startUpload">
          开始解析
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.diagnosis-page { max-width: 1000px; margin: 0 auto; }

.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.action-bar h3 { font-size: 20px; font-weight: 700; }
.action-buttons { display: flex; gap: 10px; }
.btn-icon { margin-right: 4px; }

.empty-state { padding: 60px 0; }

.resume-grid { display: flex; flex-direction: column; gap: 16px; }

.resume-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
  transition: box-shadow 0.2s;
}
.resume-card:hover { box-shadow: var(--shadow-hover); }

.card-main {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  cursor: pointer;
}

.card-icon {
  width: 44px;
  height: 44px;
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
.card-meta { font-size: 12px; color: var(--muted); margin-bottom: 6px; }
.card-skills { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px; }
.skill-tag { --el-tag-bg-color: var(--brand-light); --el-tag-text-color: var(--brand); --el-tag-border-color: transparent; }

.card-mini-scores { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.mini-score { font-size: 12px; font-weight: 600; padding: 2px 6px; background: var(--canvas); border-radius: 4px; }
.card-mini-loading { font-size: 12px; color: var(--muted); margin-top: 4px; display: flex; align-items: center; gap: 4px; }
.loading-icon { animation: spin 1s linear infinite; }

.card-actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
}
.card-expand-icon {
  color: var(--muted);
  transition: transform 0.2s;
  flex-shrink: 0;
}
.resume-card.expanded .card-expand-icon { transform: rotate(180deg); }

.card-expand-body { border-top: 1px solid var(--hairline); }
.expand-loading {
  padding: 40px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--muted);
  font-size: 14px;
}
.expand-empty { padding: 20px 0; }

.loading-spin { animation: spin 1s linear infinite; color: var(--brand); }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Upload Dialog */
.upload-zone {
  border: 2px dashed var(--hairline);
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  transition: border-color 0.2s, background 0.2s;
}
.upload-zone.dragging { border-color: var(--brand); background: var(--brand-light); }
.upload-icon { color: var(--muted); }
.upload-hint { font-size: 14px; color: var(--ink); margin: 12px 0 8px; }
.upload-label-btn {
  display: inline-block;
  color: var(--brand);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}
.upload-label-btn:hover { text-decoration: underline; }
.upload-note { font-size: 12px; color: var(--weak); margin-top: 12px; }
.upload-file-icon { color: var(--brand); }
.upload-filename { font-size: 15px; font-weight: 600; color: var(--ink); margin: 8px 0 4px; }
.upload-filesize { font-size: 12px; color: var(--muted); margin-bottom: 8px; }
</style>
