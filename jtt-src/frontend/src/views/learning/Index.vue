<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useLearningStore } from '@/stores/learning'
import { mockLearningPaths } from '@/mock/data/learning'
import { learningApi } from '@/api/learning'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { LearningPath, LearningResource } from '@/types'

const learningStore = useLearningStore()

// ========== 路径展开 ==========
const expandedId = ref<string | null>(null)

// ========== 对话框：新增/重命名路径 ==========
const dialogVisible = ref(false)
const dialogMode = ref<'add' | 'rename'>('add')
const dialogName = ref('')
const dialogPathId = ref('')

// ========== 对话框：学习测试 ==========
const quizVisible = ref(false)
const quizPathId = ref('')
const quizQuestions = ref<any[]>([])
const quizAnswers = ref<Record<string, number>>({})
const quizSubmitted = ref(false)
const quizLoading = ref(false)

// ========== AI 助手 ==========
const chatMessages = ref<{ role: 'user' | 'assistant'; content: string; concepts?: any[]; resources?: any[]; followUps?: string[] }[]>([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatContainerRef = ref<HTMLDivElement>()

// 预设快捷指令
const presetCommands = [
  { label: '生成学习路径', icon: '🎯', msg: '请根据 Java 开发工程师岗位，为我生成一份学习路径' },
  { label: '推荐学习资源', icon: '📚', msg: '推荐 Spring Boot 和微服务的学习资源' },
  { label: '学习路线咨询', icon: '🧭', msg: '我是一名后端开发，想转行 AI 智能体方向，应该怎么学？' },
  { label: '技能差距分析', icon: '📊', msg: '分析我当前技能与目标岗位的差距' },
]

// 资源类型图标映射
const resourceIcons: Record<string, string> = {
  course: '📹',
  book: '📖',
  article: '📄',
  project: '💻',
  video: '🎬',
}

// ========== 初始化 ==========
onMounted(() => {
  if (learningStore.paths.length === 0) {
    learningStore.paths = JSON.parse(JSON.stringify(mockLearningPaths))
  }
})

// ========== 路径操作 ==========
const toggle = (id: string) => {
  expandedId.value = expandedId.value === id ? null : id
}

const openAddDialog = () => {
  dialogMode.value = 'add'
  dialogName.value = ''
  dialogPathId.value = ''
  dialogVisible.value = true
}

const openRenameDialog = (path: LearningPath) => {
  dialogMode.value = 'rename'
  dialogName.value = path.name
  dialogPathId.value = path.id
  dialogVisible.value = true
}

const handleDialogConfirm = async () => {
  if (!dialogName.value.trim()) return
  if (dialogMode.value === 'add') {
    await learningStore.addPath({ name: dialogName.value.trim(), positionId: '', positionName: '', steps: [], totalDuration: '', createdAt: '', updatedAt: '' } as any)
    ElMessage.success('路径已创建')
  } else {
    learningStore.renamePath(dialogPathId.value, dialogName.value.trim())
    ElMessage.success('路径已重命名')
  }
  dialogVisible.value = false
}

const handleDeletePath = async (id: string, name: string) => {
  try {
    await ElMessageBox.confirm(`确定删除「${name}」吗？`, '确认删除', { type: 'warning' })
    await learningStore.removePath(id)
    ElMessage.success('路径已删除')
  } catch { /* 取消 */ }
}

// ========== 学习测试 ==========
const openQuiz = async (path: LearningPath) => {
  quizPathId.value = path.id
  quizVisible.value = true
  quizSubmitted.value = false
  quizAnswers.value = {}
  quizLoading.value = true
  try {
    const res: any = await learningApi.quiz({ pathId: path.id })
    quizQuestions.value = res.data?.questions || []
  } catch {
    ElMessage.error('题目加载失败')
  } finally {
    quizLoading.value = false
  }
}

const submitQuiz = () => {
  quizSubmitted.value = true
  const correct = quizQuestions.value.filter((q: any, i: number) => quizAnswers.value[q.id] === q.correctAnswer).length
  ElMessage.success(`测试完成：${correct} / ${quizQuestions.value.length} 正确`)
}

const getQuizOptionIcon = (qIdx: number, optIdx: number) => {
  if (!quizSubmitted.value) return ''
  const q = quizQuestions.value[qIdx]
  if (optIdx === q.correctAnswer) return ' ✅'
  if (quizAnswers.value[q.id] === optIdx) return ' ❌'
  return ''
}

// ========== AI 聊天 ==========
const scrollChatToBottom = () => {
  nextTick(() => {
    if (chatContainerRef.value) {
      chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
    }
  })
}

const sendMessage = async () => {
  const msg = chatInput.value.trim()
  if (!msg || chatLoading.value) return
  chatInput.value = ''
  chatMessages.value.push({ role: 'user', content: msg })
  chatLoading.value = true
  scrollChatToBottom()
  try {
    const res: any = await learningApi.chat({ message: msg })
    const data = res.data
    chatMessages.value.push({
      role: 'assistant',
      content: data?.reply || '抱歉，我暂时无法回答这个问题。',
      concepts: data?.relatedConcepts,
      resources: data?.suggestedResources,
      followUps: data?.followUpQuestions,
    })
  } catch {
    chatMessages.value.push({ role: 'assistant', content: '网络请求失败，请稍后再试。' })
  } finally {
    chatLoading.value = false
    scrollChatToBottom()
  }
}

const onPresetClick = (msg: string) => {
  chatInput.value = msg
  sendMessage()
}

const onFollowUpClick = (msg: string) => {
  chatInput.value = msg
  sendMessage()
}

/** 简单 Markdown 渲染：处理 **粗体**、- 列表、> 引用、### 标题 */
const renderMarkdown = (text: string): string => {
  return text
    .replace(/### (.+)/g, '<h4 class="md-h4">$1</h4>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^> (.+)$/gm, '<blockquote class="md-quote">$1</blockquote>')
    .replace(/^- (.+)$/gm, '<li class="md-li">$1</li>')
    .replace(/(\d+)\. (.+)/g, '<li class="md-li">$1. $2</li>')
    .replace(/\n\n/g, '<br/>')
}
</script>

<template>
  <div class="learning-platform">
    <!-- ========== 左侧 AI 助手面板 ========== -->
    <aside class="ai-panel">
      <div class="ai-panel-header">
        <div class="ai-title-row">
          <span class="ai-icon">🤖</span>
          <span class="ai-title">AI 学习助手</span>
        </div>
        <span class="ai-subtitle">基于知识图谱的智能学习导师</span>
      </div>

      <!-- 预设指令 -->
      <div class="preset-section">
        <div class="preset-label">快捷指令</div>
        <div class="preset-list">
          <button
            v-for="cmd in presetCommands"
            :key="cmd.label"
            class="preset-chip"
            :disabled="chatLoading"
            @click="onPresetClick(cmd.msg)"
          >
            <span class="preset-icon">{{ cmd.icon }}</span>
            <span>{{ cmd.label }}</span>
          </button>
        </div>
      </div>

      <!-- 聊天记录 -->
      <div ref="chatContainerRef" class="chat-messages">
        <div v-if="chatMessages.length === 0" class="chat-empty">
          <div class="chat-empty-icon">💬</div>
          <div class="chat-empty-text">
            点击上方快捷指令开始对话<br/>
            或输入你的学习问题
          </div>
        </div>
        <div
          v-for="(m, mi) in chatMessages"
          :key="mi"
          class="chat-bubble"
          :class="m.role"
        >
          <div class="chat-role-label">{{ m.role === 'user' ? '👤 你' : '🤖 AI 助手' }}</div>
          <div class="chat-content" v-html="renderMarkdown(m.content)"></div>
          <!-- 关联概念 -->
          <div v-if="m.concepts?.length" class="chat-concepts">
            <span class="concepts-label">🧩 关联概念：</span>
            <span v-for="c in m.concepts" :key="c.name" class="concept-tag">{{ c.name }} <small>({{ c.relation }})</small></span>
          </div>
          <!-- 推荐资源 -->
          <div v-if="m.resources?.length" class="chat-resources">
            <span class="concepts-label">📚 推荐资源：</span>
            <span v-for="r in m.resources" :key="r.id" class="resource-tag">{{ resourceIcons[r.type] || '📌' }} {{ r.title }} <small>@{{ r.platform }}</small></span>
          </div>
          <!-- 追问建议 -->
          <div v-if="m.followUps?.length" class="chat-followups">
            <button
              v-for="(fu, fui) in m.followUps"
              :key="fui"
              class="followup-btn"
              :disabled="chatLoading"
              @click="onFollowUpClick(fu)"
            >
              {{ fu }}
            </button>
          </div>
        </div>
        <!-- 加载状态 -->
        <div v-if="chatLoading" class="chat-bubble assistant">
          <div class="chat-role-label">🤖 AI 助手</div>
          <div class="chat-typing">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          </div>
        </div>
      </div>

      <!-- 输入框 -->
      <div class="chat-input-area">
        <input
          v-model="chatInput"
          class="chat-input"
          placeholder="输入学习问题，按 Enter 发送…"
          :disabled="chatLoading"
          @keydown.enter="sendMessage"
        />
        <button
          class="chat-send-btn"
          :disabled="!chatInput.trim() || chatLoading"
          @click="sendMessage"
        >
          发送
        </button>
      </div>
    </aside>

    <!-- ========== 右侧主区域 ========== -->
    <main class="learning-main">
      <div class="page-head">
        <div class="head-left">
          <h3>学习路径</h3>
          <span class="count">{{ learningStore.paths.length }} 条路径</span>
        </div>
        <button class="btn-add" @click="openAddDialog">+ 新建路径</button>
      </div>

      <!-- 空状态 -->
      <div v-if="learningStore.paths.length === 0" class="empty">
        <div class="empty-icon">📋</div>
        <p>暂无学习路径</p>
        <p class="empty-hint">点击「新建路径」手动创建，或使用左侧 AI 助手自动生成</p>
      </div>

      <!-- 路径卡片列表 -->
      <div v-else class="path-cards">
        <div
          v-for="path in learningStore.paths"
          :key="path.id"
          class="path-card"
          :class="{ expanded: expandedId === path.id }"
        >
          <!-- 路径头部 -->
          <div class="path-header" @click="toggle(path.id)">
            <div class="path-title-row">
              <span class="path-name">{{ path.name }}</span>
              <el-tag size="small" :type="learningStore.getCompletionPercent(path.id) === 100 ? 'success' : 'warning'">
                {{ learningStore.getCompletionPercent(path.id) }}%
              </el-tag>
            </div>
            <div class="path-header-right">
              <span class="path-meta">{{ path.positionName }} · {{ path.totalDuration }}</span>
              <el-icon :size="18" class="expand-icon" :class="{ rotated: expandedId === path.id }"><ArrowDown /></el-icon>
            </div>
          </div>

          <!-- 进度条 -->
          <div class="path-progress-bar">
            <div class="path-progress-fill" :style="{ width: learningStore.getCompletionPercent(path.id) + '%' }"></div>
          </div>

          <!-- 展开内容 -->
          <div v-if="expandedId === path.id" class="path-body">
            <!-- 步骤流程 -->
            <div class="flowchart-line">
              <template v-for="(step, idx) in path.steps" :key="step.id">
                <div class="flow-item">
                  <div class="flow-node" :class="{ done: step.completed }" @click="learningStore.toggleStep(path.id, step.id)">
                    <span class="flow-num">{{ idx + 1 }}</span>
                    <span class="flow-title">{{ step.title }}</span>
                    <span class="flow-duration">{{ step.duration }}</span>
                  </div>
                </div>
                <div v-if="idx < path.steps.length - 1" class="flow-connector">→</div>
              </template>
            </div>

            <!-- 步骤详情时间线 -->
            <div class="timeline">
              <div
                v-for="step in path.steps"
                :key="step.id"
                class="tl-item"
                :class="{ done: step.completed }"
              >
                <div class="tl-dot" @click="learningStore.toggleStep(path.id, step.id)">
                  <el-icon v-if="step.completed" :size="12"><Check /></el-icon>
                </div>
                <div class="tl-content">
                  <div class="tl-header">
                    <span class="tl-title">{{ step.title }}</span>
                    <span class="tl-duration">{{ step.duration }}</span>
                  </div>
                  <p class="tl-desc">{{ step.description }}</p>
                  <!-- 步骤资源 -->
                  <div v-if="step.resources?.length" class="tl-resources">
                    <span
                      v-for="res in step.resources"
                      :key="res.id"
                      class="res-link"
                      :title="`${res.platform} · ${res.title}`"
                    >
                      {{ resourceIcons[res.type] || '📌' }} {{ res.title }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="path-actions">
              <button class="act-btn" @click.stop="openQuiz(path)">
                📝 学习测试
              </button>
              <button class="act-btn" @click.stop="openRenameDialog(path)">
                ✏️ 重命名
              </button>
              <button class="act-btn danger" @click.stop="handleDeletePath(path.id, path.name)">
                🗑️ 删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- ========== 新增 / 重命名对话框 ========== -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'add' ? '新建学习路径' : '重命名学习路径'"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-input
        v-model="dialogName"
        placeholder="请输入路径名称"
        maxlength="50"
        show-word-limit
        @keydown.enter="handleDialogConfirm"
      />
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!dialogName.trim()" @click="handleDialogConfirm">确定</el-button>
      </template>
    </el-dialog>

    <!-- ========== 学习测试对话框 ========== -->
    <el-dialog
      v-model="quizVisible"
      title="📝 学习测试"
      width="640px"
      :close-on-click-modal="false"
    >
      <div v-if="quizLoading" class="quiz-loading">
        <p>正在生成题目…</p>
      </div>
      <div v-else-if="quizQuestions.length === 0" class="quiz-empty">
        <p>暂无题目</p>
      </div>
      <div v-else class="quiz-questions">
        <div v-for="(q, qi) in quizQuestions" :key="q.id" class="quiz-item">
          <div class="quiz-q-header">
            <span class="quiz-q-num">{{ qi + 1 }}.</span>
            <span class="quiz-q-text">{{ q.question }}</span>
          </div>
          <div class="quiz-options">
            <label
              v-for="(opt, oi) in q.options"
              :key="oi"
              class="quiz-option"
              :class="{
                selected: quizAnswers[q.id] === oi,
                correct: quizSubmitted && oi === q.correctAnswer,
                wrong: quizSubmitted && quizAnswers[q.id] === oi && oi !== q.correctAnswer,
              }"
            >
              <input
                type="radio"
                :name="q.id"
                :value="oi"
                :disabled="quizSubmitted"
                v-model="quizAnswers[q.id]"
              />
              <span class="opt-label">{{ ['A', 'B', 'C', 'D'][oi] }}. {{ opt }}{{ getQuizOptionIcon(qi, oi) }}</span>
            </label>
          </div>
          <div v-if="quizSubmitted" class="quiz-explanation">
            💡 {{ q.explanation }}
          </div>
        </div>
      </div>
      <template #footer v-if="!quizSubmitted && quizQuestions.length > 0">
        <el-button @click="quizVisible = false">关闭</el-button>
        <el-button type="primary" :disabled="Object.keys(quizAnswers).length < quizQuestions.length" @click="submitQuiz">
          提交答案
        </el-button>
      </template>
      <template #footer v-if="quizSubmitted">
        <el-button @click="quizVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ========== 整体布局 ========== */
.learning-platform {
  display: flex;
  gap: 16px;
  max-width: 1400px;
  margin: 0 auto;
  height: calc(100vh - 100px);
  min-height: 700px;
}

/* ========== AI 面板 ========== */
.ai-panel {
  width: 380px;
  min-width: 340px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
  overflow: hidden;
}

.ai-panel-header {
  padding: 16px 18px 12px;
  border-bottom: 1px solid var(--hairline);
  flex-shrink: 0;
}

.ai-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.ai-icon { font-size: 22px; }

.ai-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
}

.ai-subtitle {
  font-size: 11px;
  color: var(--weak);
  padding-left: 30px;
}

/* 预设指令 */
.preset-section {
  padding: 12px 14px;
  border-bottom: 1px solid var(--hairline);
  flex-shrink: 0;
}

.preset-label {
  font-size: 11px;
  color: var(--weak);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.preset-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preset-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 16px;
  border: 1px solid var(--hairline);
  background: var(--canvas);
  color: var(--ink);
  font-size: 12px;
  cursor: pointer;
  transition: all .15s;
}

.preset-chip:hover:not(:disabled) {
  border-color: var(--brand);
  color: var(--brand);
  background: #eef2ff;
}

.preset-chip:disabled { opacity: .5; cursor: not-allowed; }
.preset-icon { font-size: 13px; }

/* 聊天区域 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--weak);
  text-align: center;
}

.chat-empty-icon { font-size: 36px; margin-bottom: 8px; }
.chat-empty-text { font-size: 12px; line-height: 1.8; }

.chat-bubble {
  padding: 12px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.7;
}

.chat-bubble.user {
  background: #eef2ff;
  align-self: flex-end;
  max-width: 90%;
}

.chat-bubble.assistant {
  background: var(--canvas);
  border: 1px solid var(--hairline);
}

.chat-role-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--weak);
  margin-bottom: 6px;
}

/* Markdown 样式 */
.chat-content :deep(.md-h4) {
  font-size: 13px;
  font-weight: 700;
  margin: 8px 0 4px;
  color: var(--ink);
}

.chat-content :deep(strong) {
  color: var(--ink);
  font-weight: 600;
}

.chat-content :deep(.md-quote) {
  border-left: 3px solid var(--brand);
  padding: 4px 10px;
  margin: 6px 0;
  background: #fff;
  border-radius: 0 6px 6px 0;
  font-size: 12px;
  color: var(--muted);
}

.chat-content :deep(.md-li) {
  margin: 2px 0 2px 4px;
  list-style-position: inside;
}

/* 关联概念 */
.chat-concepts, .chat-resources {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--hairline);
}

.concepts-label {
  font-size: 11px;
  color: var(--weak);
  display: block;
  margin-bottom: 4px;
}

.concept-tag {
  display: inline-block;
  padding: 2px 8px;
  margin: 2px 4px 2px 0;
  border-radius: 10px;
  background: #eef2ff;
  color: var(--brand);
  font-size: 11px;
}

.concept-tag small { color: var(--weak); }

.resource-tag {
  display: inline-block;
  padding: 2px 8px;
  margin: 2px 4px 2px 0;
  border-radius: 10px;
  background: #f0fdf4;
  color: #059669;
  font-size: 11px;
}

.resource-tag small { color: var(--weak); }

/* 追问建议 */
.chat-followups {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.followup-btn {
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid var(--hairline);
  background: #fff;
  color: var(--brand);
  font-size: 11px;
  cursor: pointer;
  transition: all .15s;
}

.followup-btn:hover:not(:disabled) {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

/* 打字动画 */
.chat-typing {
  display: flex;
  gap: 5px;
  padding: 4px 0;
}

.chat-typing .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--weak);
  animation: bounce 1.4s infinite ease-in-out both;
}

.chat-typing .dot:nth-child(1) { animation-delay: -.32s; }
.chat-typing .dot:nth-child(2) { animation-delay: -.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* 输入框 */
.chat-input-area {
  display: flex;
  gap: 8px;
  padding: 12px 14px;
  border-top: 1px solid var(--hairline);
  flex-shrink: 0;
}

.chat-input {
  flex: 1;
  padding: 8px 12px;
  border-radius: 20px;
  border: 1px solid var(--hairline);
  font-size: 13px;
  outline: none;
  transition: border-color .15s;
}

.chat-input:focus { border-color: var(--brand); }
.chat-input:disabled { background: var(--canvas); }

.chat-send-btn {
  padding: 8px 18px;
  border-radius: 20px;
  border: none;
  background: var(--brand);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity .15s;
}

.chat-send-btn:hover:not(:disabled) { opacity: .85; }
.chat-send-btn:disabled { opacity: .4; cursor: not-allowed; }

/* ========== 右侧主区域 ========== */
.learning-main {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.head-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.head-left h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
}

.count {
  font-size: 13px;
  color: var(--muted);
}

.btn-add {
  padding: 7px 18px;
  border-radius: 8px;
  border: 1px dashed var(--brand);
  background: #fff;
  color: var(--brand);
  font-size: 13px;
  cursor: pointer;
  transition: all .15s;
}

.btn-add:hover {
  background: var(--brand);
  color: #fff;
  border-style: solid;
}

/* 空状态 */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: var(--muted);
}

.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty p { font-size: 14px; }
.empty-hint { font-size: 12px; color: var(--weak); margin-top: 4px; }

/* 路径卡片 */
.path-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.path-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
  overflow: hidden;
  transition: box-shadow .2s;
}

.path-card:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,.1);
}

.path-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
}

.path-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.path-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.path-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.path-meta {
  font-size: 12px;
  color: var(--weak);
}

.expand-icon {
  transition: transform .25s;
  color: var(--muted);
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

/* 进度条 */
.path-progress-bar {
  height: 3px;
  background: var(--canvas);
  margin: 0 20px;
  border-radius: 2px;
  overflow: hidden;
}

.path-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4f6ef6, #34d399);
  border-radius: 2px;
  transition: width .4s ease;
}

.path-body {
  padding: 16px 20px 20px;
}

/* 步骤流程图 */
.flowchart-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  padding: 8px 0 16px;
  gap: 4px;
}

.flow-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.flow-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  background: var(--canvas);
  border: 1px solid var(--hairline);
  font-size: 12px;
  cursor: pointer;
  transition: all .2s;
}

.flow-node:hover {
  border-color: var(--brand);
  background: #eef2ff;
}

.flow-node.done {
  background: #f0fdf4;
  border-color: #34d399;
  color: #059669;
}

.flow-num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.flow-node.done .flow-num {
  background: #34d399;
  color: #fff;
}

.flow-duration {
  font-size: 10px;
  color: var(--weak);
  margin-left: 2px;
}

.flow-connector {
  color: var(--weak);
  font-size: 14px;
  font-weight: 600;
}

/* 时间线 */
.timeline {
  padding: 4px 0 12px;
}

.tl-item {
  display: flex;
  gap: 14px;
  padding: 10px 0;
  position: relative;
}

.tl-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 36px;
  bottom: 0;
  width: 2px;
  background: var(--hairline);
}

.tl-item.done:not(:last-child)::before {
  background: #34d399;
}

.tl-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid var(--hairline);
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all .2s;
  margin-top: 1px;
}

.tl-dot:hover {
  border-color: var(--brand);
}

.tl-item.done .tl-dot {
  background: #34d399;
  border-color: #34d399;
  color: #fff;
}

.tl-content {
  flex: 1;
  min-width: 0;
}

.tl-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.tl-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.tl-item.done .tl-title {
  color: var(--muted);
  text-decoration: line-through;
}

.tl-duration {
  font-size: 11px;
  color: var(--weak);
  background: var(--canvas);
  padding: 2px 8px;
  border-radius: 10px;
}

.tl-desc {
  font-size: 13px;
  color: var(--muted);
  line-height: 1.6;
}

/* 步骤资源 */
.tl-resources {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.res-link {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  background: #fefce8;
  color: #a16207;
  font-size: 11px;
  cursor: default;
}

/* 操作按钮 */
.path-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--hairline);
}

.act-btn {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid var(--hairline);
  background: #fff;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  transition: all .15s;
}

.act-btn:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.act-btn.danger:hover {
  border-color: #ef4444;
  color: #ef4444;
}

/* ========== 测试对话框 ========== */
.quiz-loading, .quiz-empty {
  text-align: center;
  padding: 40px;
  color: var(--muted);
}

.quiz-questions {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.quiz-q-header {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}

.quiz-q-num {
  font-weight: 700;
  color: var(--brand);
  font-size: 14px;
}

.quiz-q-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.quiz-options {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.quiz-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--hairline);
  cursor: pointer;
  transition: all .15s;
  font-size: 13px;
}

.quiz-option:hover:not(.correct):not(.wrong) {
  border-color: var(--brand);
  background: #eef2ff;
}

.quiz-option.selected {
  border-color: var(--brand);
  background: #eef2ff;
}

.quiz-option.correct {
  border-color: #34d399;
  background: #f0fdf4;
}

.quiz-option.wrong {
  border-color: #ef4444;
  background: #fef2f2;
}

.quiz-option input[type="radio"] {
  accent-color: var(--brand);
}

.opt-label {
  flex: 1;
}

.quiz-explanation {
  margin-top: 6px;
  padding: 8px 12px;
  background: #fefce8;
  border-radius: 8px;
  font-size: 12px;
  color: #a16207;
  line-height: 1.5;
}

/* ========== 响应式 ========== */
@media (max-width: 900px) {
  .learning-platform {
    flex-direction: column;
    height: auto;
  }

  .ai-panel {
    width: 100%;
    min-width: unset;
    height: 500px;
  }
}
</style>
