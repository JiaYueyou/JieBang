<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const dragging = ref(false)
const file = ref<File | null>(null)
const parsing = ref(false)
const parsed = ref(false)
const supportedExtensions = ['.pdf', '.docx', '.png', '.jpg', '.jpeg']

const isSupportedFile = (name: string) =>
  supportedExtensions.some((extension) => name.toLowerCase().endsWith(extension))

const handleDrop = (e: DragEvent) => {
  dragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f && isSupportedFile(f.name)) {
    file.value = f
  } else {
    ElMessage.warning('请上传 PDF、DOCX、PNG、JPG 或 JPEG 文件')
  }
}

const handleFileChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) file.value = input.files[0]
}

const startParse = async () => {
  if (!file.value) return
  parsing.value = true
  await new Promise((r) => setTimeout(r, 2000))
  parsing.value = false
  parsed.value = true
  ElMessage.success('简历解析完成！')
}
</script>

<template>
  <div class="upload-page">
    <div class="upload-card" v-if="!parsed">
      <h3>上传简历</h3>
      <p class="upload-desc">支持 PDF、DOCX、PNG、JPG、JPEG 格式，解析准确率目标 ≥ 90%</p>

      <div
        class="drop-zone"
        :class="{ dragging, hasFile: file }"
        @dragover.prevent="dragging = true"
        @dragleave="dragging = false"
        @drop.prevent="handleDrop"
      >
        <template v-if="!file">
          <el-icon :size="48" class="upload-icon"><UploadFilled /></el-icon>
          <p>拖拽文件到此处，或 <label class="file-label">点击上传<input type="file" accept=".pdf,.docx,.png,.jpg,.jpeg" hidden @change="handleFileChange" /></label></p>
        </template>
        <template v-else>
          <el-icon :size="40" class="file-icon"><Document /></el-icon>
          <p class="file-name">{{ file.name }}</p>
          <p class="file-size">{{ (file.size / 1024).toFixed(1) }} KB</p>
          <el-button text size="small" type="danger" @click="file = null">移除</el-button>
        </template>
      </div>

      <el-button type="primary" size="large" class="parse-btn" :loading="parsing" :disabled="!file" @click="startParse">
        {{ parsing ? '解析中…' : '开始解析' }}
      </el-button>
    </div>

    <div v-else class="result-card">
      <div class="result-header">
        <el-icon :size="40" color="#34b37e"><SuccessFilled /></el-icon>
        <h3>解析完成</h3>
      </div>
      <div class="parsed-preview">
        <div class="preview-section">
          <span class="preview-label">姓名</span>
          <span class="preview-value">王五</span>
        </div>
        <div class="preview-section">
          <span class="preview-label">教育</span>
          <span class="preview-value">某某大学 · 软件工程硕士</span>
        </div>
        <div class="preview-section">
          <span class="preview-label">技能</span>
          <div class="preview-skills">
            <el-tag v-for="s in ['Java', 'Python', 'Spring Boot', 'MySQL']" :key="s" size="small" type="success" effect="plain">{{ s }}</el-tag>
          </div>
        </div>
      </div>
      <div class="result-actions">
        <el-button type="primary" @click="router.push('/resume/editor/r-uploaded')">在线编辑</el-button>
        <el-button @click="router.push('/diagnosis')">查看简历诊断</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-page { max-width: 660px; margin: 40px auto; }

.upload-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 40px;
  text-align: center;
}

.upload-card h3 { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
.upload-desc { font-size: 13px; color: var(--muted); margin-bottom: 28px; }

.drop-zone {
  border: 2px dashed var(--hairline);
  border-radius: 12px;
  padding: 48px 24px;
  margin-bottom: 24px;
  transition: all 0.2s ease;
  cursor: pointer;
}

.drop-zone.dragging,
.drop-zone:hover {
  border-color: var(--brand);
  background: var(--brand-light);
}

.drop-zone.hasFile { border-color: var(--brand); background: var(--brand-light); }

.upload-icon { color: var(--weak); margin-bottom: 12px; }
.drop-zone p { font-size: 14px; color: var(--muted); }

.file-label {
  color: var(--brand);
  cursor: pointer;
  text-decoration: underline;
}

.file-icon { color: var(--brand); margin-bottom: 8px; }
.file-name { font-size: 15px; font-weight: 600; color: var(--ink); }
.file-size { font-size: 12px; color: var(--muted); margin-bottom: 8px; }

.parse-btn {
  width: 200px;
  height: 44px;
  border-radius: var(--radius);
  background: var(--brand);
  border-color: var(--brand);
}

.result-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 40px;
  text-align: center;
}

.result-header { margin-bottom: 24px; }
.result-header h3 { font-size: 20px; font-weight: 700; margin-top: 8px; }

.parsed-preview {
  text-align: left;
  margin-bottom: 24px;
}

.preview-section {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--hairline);
}

.preview-label {
  width: 60px;
  font-size: 13px;zhelaingge
  color: var(--muted);
  flex-shrink: 0;
}

.preview-value { font-size: 14px; color: var(--ink); }

.preview-skills { display: flex; flex-wrap: wrap; gap: 6px; }

.result-actions { display: flex; gap: 12px; justify-content: center; }
</style>
