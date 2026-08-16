<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useLearningStore } from '@/stores/learning'
import { useFavoritesStore } from '@/stores/favorites'
import { useResumeStore } from '@/stores/resume'
import { learningApi } from '@/api/learning'
import { assistantApi } from '@/api/assistant'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { LearningPath, LearningResource } from '@/types'
import lujingIcon from '@/assets/icon/lujing.svg'
import ziyuanIcon from '@/assets/icon/ziyuan.svg'
import zixunIcon from '@/assets/icon/zixun.svg'
import chajufenxiIcon from '@/assets/icon/chajufenxi.svg'
import xuexiceshiIcon from '@/assets/icon/xuexiceshi.svg'
import chongmingmingIcon from '@/assets/icon/chongmingming.svg'

const learningStore = useLearningStore()
const favoritesStore = useFavoritesStore()
const resumeStore = useResumeStore()

// 构建用户技能上下文（注入 chat，让 AI 回复个性化而非模板）
const buildUserContext = () => {
  const r = resumeStore.resumes?.[0]
  if (!r) return undefined
  const skills = (r.skills || []).map((s: any) => s.name).filter(Boolean)
  if (!skills.length && !r.targetPosition) return undefined
  return {
    name: 'user-profile',
    path: '/learning',
    resumeData: {
      name: r.name || '',
      targetPosition: r.targetPosition || '',
      skills: (r.skills || []).map((s: any) => ({ name: s.name, level: s.level || '', category: s.category || '' })),
      workExperience: (r.workExperience || []).map((w: any) => ({ company: w.company || '', position: w.position || '', description: w.description || '', skills: w.skills || [] })),
      education: (r.education || []).map((e: any) => ({ school: e.school || '', degree: e.degree || '', major: e.major || '' })),
    },
  }
}

// ========== 路径展开 ==========
const expandedId = ref<string | null>(null)

// AI 生成路径的序号：扫描已有路径名里的「学习路径X：」，取当前存在的最大编号 +1 顺延
const nextPathSeq = () => {
  const cnMap: Record<string, number> = { '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10 }
  let max = 0
  for (const p of learningStore.paths) {
    const m = (p.name || '').match(/学习路径([一二三四五六七八九十]|\d+)[：:]/)
    if (m && m[1]) {
      const n = cnMap[m[1]] ?? parseInt(m[1], 10)
      if (!isNaN(n) && n > max) max = n
    }
  }
  return max + 1
}

// ========== 对话框：新增/重命名路径 ==========
const dialogVisible = ref(false)
const dialogMode = ref<'add' | 'rename'>('add')
const dialogName = ref('')
const dialogPathId = ref('')

// ========== 对话框：学习测试 ==========
const quizVisible = ref(false)
const quizPathId = ref('')
const quizStepTitle = ref('')
const quizStepId = ref('') // 空 = 整条路径，非空 = 单个步骤
const quizQuestions = ref<any[]>([])
const quizAnswers = ref<Record<string, number>>({})
const quizSubmitted = ref(false)
const quizLoading = ref(false)
const quizTargetStepIds = ref<string[]>([])
const quizIsFinal = ref(false)

// ========== 步骤学习链接（AI 生成） ==========
const stepLinks = ref<Record<string, any[]>>({}) // stepId -> resources
const stepLinksLoading = ref<Record<string, boolean>>({}) // stepId -> loading
const stepLinksError = ref<Record<string, boolean>>({})

// ========== AI 助手 ==========
const chatMessages = ref<{ role: 'user' | 'assistant'; content: string; concepts?: any[]; resources?: any[]; followUps?: string[]; isPath?: boolean }[]>([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatContainerRef = ref<HTMLDivElement>()
const flowState = ref<'idle' | 'awaiting_position' | 'awaiting_skill' | 'awaiting_scenario' | 'awaiting_target'>('idle')

// ========== 面板拖拽分隔线 ==========
const panelWidth = ref(380)
const dragging = ref(false)
const MIN_PANEL = 280
const MAX_RATIO = 0.55

const onDividerDown = (e: MouseEvent) => {
  e.preventDefault()
  dragging.value = true
  document.addEventListener('mousemove', onDividerMove)
  document.addEventListener('mouseup', onDividerUp)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

const onDividerMove = (e: MouseEvent) => {
  if (!dragging.value) return
  const container = (e.target as HTMLElement).closest('.learning-platform')
  const rect = container?.getBoundingClientRect()
  if (!rect) return
  const w = e.clientX - rect.left
  const maxW = rect.width * MAX_RATIO
  panelWidth.value = Math.min(Math.max(w, MIN_PANEL), maxW)
}

const onDividerUp = () => {
  dragging.value = false
  document.removeEventListener('mousemove', onDividerMove)
  document.removeEventListener('mouseup', onDividerUp)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

onUnmounted(() => {
  document.removeEventListener('mousemove', onDividerMove)
  document.removeEventListener('mouseup', onDividerUp)
})

// 预设快捷指令（msg 为内部标记，onPresetClick 按标记走"先问清再处理"流程）
const presetCommands = [
  { label: '生成学习路径', icon: lujingIcon, msg: '__gen_path__' },
  { label: '推荐学习资源', icon: ziyuanIcon, msg: '__rec_resource__' },
  { label: '学习路线咨询', icon: zixunIcon, msg: '__career_advice__' },
  { label: '技能差距分析', icon: chajufenxiIcon, msg: '__gap_analysis__' },
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
onMounted(async () => {
  if (learningStore.paths.length === 0) {
    await learningStore.fetchPaths()
  }
  await favoritesStore.fetchAll()
})

// ========== 路径操作 ==========
const toggle = (id: string) => {
  expandedId.value = expandedId.value === id ? null : id
}

// 手动点击步骤：仅允许取消完成；标记完成需通过测验（≥80%）
const handleStepClick = (path: LearningPath, step: any) => {
  if (step.completed) {
    learningStore.toggleStep(path.id, step.id)
    return
  }
  ElMessage.info('完成本步骤需先通过「测验」且得分 ≥80%')
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
const openQuiz = async (path: LearningPath, stepIds: string[], isFinal = false) => {
  quizPathId.value = path.id
  quizTargetStepIds.value = stepIds
  quizIsFinal.value = isFinal
  quizStepId.value = stepIds.length === 1 ? (stepIds[0] || '') : ''
  const titles = isFinal
    ? '综合测试'
    : path.steps.filter(s => stepIds.includes(s.id)).map(s => s.title).join(' + ') || '当前步骤'
  quizStepTitle.value = titles
  quizVisible.value = true
  quizSubmitted.value = false
  quizAnswers.value = {}
  quizLoading.value = true
  try {
    const res: any = await learningApi.quiz({ pathId: path.id, stepIds, questionCount: isFinal ? 5 : 3 })
    quizQuestions.value = res.data?.questions || []
  } catch {
    ElMessage.error('题目加载失败')
  } finally {
    quizLoading.value = false
  }
}

const submitQuiz = async () => {
  quizSubmitted.value = true
  const correct = quizQuestions.value.filter((q: any) => quizAnswers.value[q.id] === q.correctAnswer).length
  const total = quizQuestions.value.length
  const pct = total ? Math.round((correct / total) * 100) : 0
  const passed = total > 0 && pct >= 80
  ElMessage[passed ? 'success' : 'warning'](
    passed ? '测试通过：' + correct + ' / ' + total + ' 正确（' + pct + '%）' : '测试未通过：' + correct + ' / ' + total + ' 正确（需 ≥80%）'
  )

  // 步骤测试：通过后标记 quizPassed + completed 并持久化
  if (!quizIsFinal.value && passed) {
    const path = learningStore.paths.find(p => p.id === quizPathId.value)
    if (path) {
      path.steps.forEach(s => {
        if (quizTargetStepIds.value.includes(s.id)) {
          s.quizPassed = true
          s.completed = true
        }
      })
      try {
        await learningApi.update(quizPathId.value, { steps: path.steps })
      } catch {
        ElMessage.error('状态保存失败')
      }
    }
  }
}

const isStepUnlocked = (path: LearningPath, idx: number): boolean => {
  if (idx === 0) return true
  return path.steps[idx - 1]?.quizPassed === true
}

const allStepsPassed = (path: LearningPath): boolean => {
  return path.steps.length > 0 && path.steps.every(s => s.quizPassed)
}

const getQuizOptionIcon = (qIdx: number, optIdx: number) => {
  if (!quizSubmitted.value) return ''
  const q = quizQuestions.value[qIdx]
  if (optIdx === q.correctAnswer) return ' ✅'
  if (quizAnswers.value[q.id] === optIdx) return ' ❌'
  return ''
}

// ========== 步骤学习链接（AI 联网生成） ==========
const generateStepLinks = async (step: any) => {
  if (stepLinksLoading.value[step.id]) return
  stepLinksLoading.value[step.id] = true
  stepLinksError.value[step.id] = false
  try {
    const res: any = await assistantApi.generateLinks(step.title + ' ' + step.description)
    const resources = res.data?.resources || []
    // 合并到已有资源（保留原有 mock 资源）
    const existing = stepLinks.value[step.id] || []
    const merged = [...existing]
    for (const r of resources) {
      if (!merged.some(m => m.title === r.title)) merged.push({ ...r, id: 'ai-' + Date.now() + '-' + merged.length })
    }
    stepLinks.value[step.id] = merged
    if (merged.length === existing.length) {
      ElMessage.info('未找到新的学习链接')
    }
  } catch {
    stepLinksError.value[step.id] = true
    ElMessage.error('生成学习链接失败，请稍后重试')
  } finally {
    stepLinksLoading.value[step.id] = false
  }
}

// ========== AI 聊天（含学习路径生成流程）==========
const scrollChatToBottom = () => {
  nextTick(() => {
    if (chatContainerRef.value) {
      chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
    }
  })
}

const addAssistantMsg = (content: string, extras?: { concepts?: any[]; resources?: any[]; followUps?: string[]; isPath?: boolean }) => {
  const msg: { role: 'user' | 'assistant'; content: string; concepts?: any[]; resources?: any[]; followUps?: string[]; isPath?: boolean } = { role: 'assistant', content, ...extras }
  chatMessages.value.push(msg)
  return msg
}

const sendMessage = async () => {
  const msg = chatInput.value.trim()
  if (!msg || chatLoading.value) return
  chatInput.value = ''
  chatMessages.value.push({ role: 'user', content: msg })
  chatLoading.value = true
  scrollChatToBottom()

  // ── Flow: user answered the clarifying question ──
  const currentFlow = flowState.value
  flowState.value = 'idle'

  if (currentFlow === 'awaiting_position') {
    const positionName = msg

    // [P3] 等待期间逐步展示思考节奏（API 返回后用真实步骤数据补全细节）
    const thinkMsg = addAssistantMsg('🎯 分析目标岗位「' + positionName + '」的技能要求…')
    scrollChatToBottom()

    // 等待期节奏步骤（不依赖 API 数据的先行步骤，每 4 秒一条，避免干等）
    const waitSteps = [
      '🔍 查询知识图谱：获取岗位技能树结构…',
      '🌐 联网搜索最新招聘技能要求…',
      '🧠 综合图谱与搜索结果，规划学习路径…',
    ]
    let waitIdx = 0
    const waitTimer = setInterval(() => {
      if (waitIdx < waitSteps.length) {
        thinkMsg.content += '\n' + waitSteps[waitIdx]
        waitIdx++
        scrollChatToBottom()
      }
    }, 4000)

    try {
      const res: any = await assistantApi.generateLearningPath(positionName)
      clearInterval(waitTimer)
      const data = res.data
      if (!data || !data.steps || data.steps.length === 0) {
        throw new Error('未生成有效路径')
      }

      // API 返回：逐条淡入真实思考步骤（含图谱命中数等真实数据），替代一次性刷出
      const steps: { icon: string; text: string; detail?: string }[] = data.thinkingSteps || []
      if (steps.length) {
        for (let i = 0; i < steps.length; i++) {
          const st = steps[i]
          if (!st) continue
          thinkMsg.content = (i === 0 ? '' : thinkMsg.content + '\n') +
            st.icon + ' ' + st.text + (st.detail ? '（' + st.detail + '）' : '')
          scrollChatToBottom()
          await new Promise(r => setTimeout(r, 450))
        }
        await new Promise(r => setTimeout(r, 400))
      }

      // Build detailed step display
      let reply = '## ' + data.pathName + '\n\n'
      reply += '**目标岗位**：' + data.positionName + '\n'
      reply += '**总时长**：' + data.totalDuration + '\n'
      reply += '**信息来源**：' + data.sourceNote
      if (data.searchResultsCount) {
        reply += '（检索到 ' + data.searchResultsCount + ' 条相关信息）'
      }
      reply += '\n\n---\n\n'

      for (let i = 0; i < data.steps.length; i++) {
        const s = data.steps[i]
        reply += '### ' + (i + 1) + '. ' + s.title + '（' + s.duration + '）\n'
        reply += s.description + '\n\n'
        if (s.resources && s.resources.length > 0) {
          reply += '推荐资源：\n'
          for (const r of s.resources) {
            reply += '- ' + (resourceIcons[r.type] || '📌') + ' **' + r.title + '** @' + r.platform + '\n'
          }
          reply += '\n'
        }
      }

      chatLoading.value = false
      addAssistantMsg(reply, {
        followUps: ['其他岗位推荐', '优化这个学习路径', '生成测试题'],
        isPath: true,
      })
      scrollChatToBottom()

      // Add to learning paths store (right panel)
      // 命名与既有路径统一：「学习路径一：xxx」…（按当前存在的最大编号顺延，删除后编号复用）
      const nextSeq = nextPathSeq()
      const cnNum = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
      const seqLabel = nextSeq <= 10 ? cnNum[nextSeq - 1] : String(nextSeq)
      const newPath: any = {
        id: 'lp-gen-' + Date.now(),
        name: '学习路径' + seqLabel + '：' + data.positionName,
        positionId: '',
        positionName: data.positionName,
        steps: data.steps.map((s: any, idx: number) => ({
          id: 'step-gen-' + idx + '-' + Date.now(),
          order: idx + 1,
          title: s.title,
          description: s.description,
          duration: s.duration,
          resources: (s.resources || []).map((r: any, ri: number) => ({
            id: 'res-gen-' + idx + '-' + ri,
            title: r.title,
            type: r.type || 'course',
            url: '',
            platform: r.platform || '',
          })),
          completed: false,
        })),
        totalDuration: data.totalDuration,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }
      learningStore.paths.unshift(newPath)
      nextTick(() => { expandedId.value = newPath.id })
      ElMessage.success('学习路径已生成并添加到列表')
      return
    } catch (e: any) {
      clearInterval(waitTimer)
      chatLoading.value = false
      const errMsg = e?.response?.data?.detail?.message || e?.message || '生成失败'
      addAssistantMsg('抱歉，生成学习路径时出错：' + errMsg + '\n\n请重试或换个岗位名称。', {
        followUps: ['重新生成', '换个岗位'],
      })
      scrollChatToBottom()
      return
    }
  }

  	  // ── Normal AI chat (all flows reach here) ──
	try {
    // 确保简历已加载（首次对话时懒加载），并注入用户技能上下文
    if (resumeStore.resumes.length === 0) {
      try { await resumeStore.fetchList() } catch { /* 离线时忽略 */ }
    }
    const res: any = await learningApi.chat({ message: msg, pageContext: buildUserContext() })
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
  if (chatLoading.value) return

  if (msg === '__gen_path__') {
    flowState.value = 'awaiting_position'
    chatMessages.value.push({ role: 'user', content: '生成学习路径' })
    addAssistantMsg('好的！请问您想要生成**哪个岗位**的学习路径呢？\n\n例如：Java开发工程师、AI智能体开发、前端工程师、大数据工程师…')
    scrollChatToBottom()
    return
  }

  if (msg === '__rec_resource__') {
    flowState.value = 'awaiting_skill'
    chatMessages.value.push({ role: 'user', content: '推荐学习资源' })
    addAssistantMsg('好的！请问您想学习**哪个技能或技术方向**的资源？\n\n例如：Spring Boot、Python、Docker、机器学习…')
    scrollChatToBottom()
    return
  }

  if (msg === '__career_advice__') {
    flowState.value = 'awaiting_scenario'
    chatMessages.value.push({ role: 'user', content: '学习路线咨询' })
    addAssistantMsg('好的！请简单描述一下您的情况和问题，例如：\n\n- "我是一名后端开发，想转行 AI 方向，应该怎么学？"\n- "我是零基础，想学前端开发，从哪开始？"\n- "工作3年了，想提升系统架构能力，有什么路线？"')
    scrollChatToBottom()
    return
  }

  if (msg === '__gap_analysis__') {
    flowState.value = 'awaiting_target'
    chatMessages.value.push({ role: 'user', content: '技能差距分析' })
    addAssistantMsg('好的！请问您的**目标岗位**是什么？我来对比您当前的技能进行分析。\n\n例如：Java后端工程师、AI算法工程师、全栈开发…')
    scrollChatToBottom()
    return
  }

  // Fallback: normal chat
  chatInput.value = msg
  sendMessage()
}

const onFollowUpClick = (msg: string) => {
  if (chatLoading.value) return
  chatInput.value = msg
  sendMessage()
}

// 收藏学习资源
const collectResource = async (res: LearningResource, stepTitle: string) => {
  const itemId = `resource-${res.id}`
  if (favoritesStore.isFavorited('learning_resource', itemId)) {
    const fav = favoritesStore.allFavorites.find((f: any) => f.item_type === 'learning_resource' && f.item_id === itemId)
    if (fav) { await favoritesStore.remove(fav.id); ElMessage.success('已取消收藏') }
  } else {
    await favoritesStore.add({
      item_type: 'learning_resource',
      item_id: itemId,
      title: res.title,
      summary: `${stepTitle} · ${res.type}`,
      metadata: { resource_id: res.id, title: res.title, type: res.type, url: res.url, platform: res.platform },
      tags: [res.type, res.platform],
    })
    ElMessage.success('已收藏学习资料')
  }
}

// 加入错题本
const addQuizError = async (q: any) => {
  const userAnswer = quizAnswers.value[q.id]
  if (userAnswer === undefined) return
  const itemId = `quiz-${q.id}`
  if (favoritesStore.isFavorited('quiz_error', itemId)) {
    ElMessage.info('该题已在错题本中')
    return
  }
  await favoritesStore.add({
    item_type: 'quiz_error',
    item_id: itemId,
    title: q.question?.slice(0, 50) || '错题',
    summary: `正确答案: ${q.options[q.correctAnswer]}`,
    metadata: {
      quiz_id: quizPathId.value,
      question: q.question,
      user_answer: q.options[userAnswer],
      correct_answer: q.options[q.correctAnswer],
      explanation: q.explanation,
    },
    tags: ['quiz'],
  })
  ElMessage.success('已加入错题本')
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
    <aside class="ai-panel" :style="{ width: panelWidth + 'px', minWidth: 'unset' }">
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
            <img class="preset-icon" :src="cmd.icon" />
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

    <!-- 拖拽分隔线 -->
    <div class="panel-divider" @mousedown="onDividerDown"></div>

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
                  <div class="flow-node" :class="{ done: step.completed }" @click="handleStepClick(path, step)">
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
                v-for="(step, idx) in path.steps"
                :key="step.id"
                class="tl-item"
                :class="{ done: step.completed }"
              >
                <div class="tl-dot" @click="handleStepClick(path, step)">
                  <el-icon v-if="step.completed" :size="12"><Check /></el-icon>
                </div>
                <div class="tl-content">
                  <div class="tl-header">
                    <span class="tl-title">{{ step.title }}</span>
                    <span class="tl-duration">{{ step.duration }}</span>
                    <!-- 步骤测试按钮：未解锁 / 已通过 / 可测试 -->
                    <button v-if="!isStepUnlocked(path, idx)" class="step-quiz-btn locked" disabled>🔒 未解锁</button>
                    <button v-else-if="step.quizPassed" class="step-quiz-btn passed" @click.stop="openQuiz(path, [step.id])">
                      <img class="quiz-icon" :src="xuexiceshiIcon" /> 已通过
                    </button>
                    <button v-else class="step-quiz-btn" @click.stop="openQuiz(path, [step.id])">
                      <img class="quiz-icon" :src="xuexiceshiIcon" /> 测试
                    </button>
                  </div>
                  <p class="tl-desc">{{ step.description }}</p>

                  <!-- 步骤学习链接 -->
                  <div class="tl-actions">
                    <button
                      class="step-btn links"
                      :disabled="stepLinksLoading[step.id]"
                      @click.stop="generateStepLinks(step)"
                    >
                      {{ stepLinksLoading[step.id] ? '⏳ 生成中…' : '🔗 学习链接' }}
                    </button>
                  </div>

                  <!-- 步骤已有资源（预置） -->
                  <div v-if="step.resources?.length" class="tl-resources">
                    <span
                      v-for="res in step.resources"
                      :key="res.id"
                      class="res-link"
                      :title="`${res.platform} · ${res.title}`"
                    >
                      {{ resourceIcons[res.type] || '📌' }} {{ res.title }}
                      <el-button
                        text
                        size="small"
                        :type="favoritesStore.isFavorited('learning_resource', 'resource-' + res.id) ? 'warning' : 'default'"
                        :icon="favoritesStore.isFavorited('learning_resource', 'resource-' + res.id) ? 'StarFilled' : 'Star'"
                        @click.stop="collectResource(res, step.title)"
                        style="margin-left: 4px; padding: 0 4px; font-size: 12px;"
                      />
                    </span>
                  </div>

                  <!-- AI 生成的学习链接 -->
                  <div v-if="stepLinks[step.id]?.length" class="ai-links">
                    <div class="ai-links-label">🔗 AI 推荐学习链接</div>
                    <div v-for="link in stepLinks[step.id]" :key="link.id" class="ai-link-item">
                      <a v-if="link.url" :href="link.url" target="_blank" rel="noopener">
                        {{ resourceIcons[link.type] || '📌' }} {{ link.title }}
                        <small>@{{ link.platform }}</small>
                      </a>
                      <span v-else class="ai-link-no-url">
                        {{ resourceIcons[link.type] || '📌' }} {{ link.title }}
                        <small>@{{ link.platform }}</small>
                      </span>
                    </div>
                  </div>
                  <div v-if="stepLinksError[step.id]" class="ai-links-error">
                    学习链接生成失败，请稍后重试
                  </div>
                </div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="path-actions">
              <button v-if="allStepsPassed(path)" class="act-btn final-test" @click.stop="openQuiz(path, path.steps.map(s => s.id), true)">
                <img class="btn-icon" :src="xuexiceshiIcon" /> 综合测试
              </button>
              <button class="act-btn" @click.stop="openRenameDialog(path)">
                <img class="btn-icon" :src="chongmingmingIcon" /> 重命名
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
      width="640px"
      :close-on-click-modal="false"
    >
      <template #header>
        <div class="quiz-dialog-title">
          <img :src="xuexiceshiIcon" class="quiz-title-icon" />
          <span>学习测试：{{ quizStepTitle }}</span>
        </div>
      </template>
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
              <span class="opt-label">{{ ['A', 'B', 'C', 'D'][Number(oi)] }}. {{ opt }}{{ getQuizOptionIcon(qi, Number(oi)) }}</span>
            </label>
          </div>
          <div v-if="quizSubmitted" class="quiz-explanation">
            💡 {{ q.explanation }}
            <el-button
              text size="small" type="danger"
              :disabled="favoritesStore.isFavorited('quiz_error', 'quiz-' + q.id)"
              @click="addQuizError(q)"
              style="margin-top: 6px;"
            >
              {{ favoritesStore.isFavorited('quiz_error', 'quiz-' + q.id) ? '已加入错题本' : '+ 加入错题本' }}
            </el-button>
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
  min-width: 280px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
  overflow: hidden;
  flex-shrink: 0;
}

/* 面板拖拽分隔线 */
.panel-divider {
  width: 6px;
  cursor: col-resize;
  background: transparent;
  border-radius: 3px;
  transition: background .2s;
  flex-shrink: 0;
  margin: 0 2px;
}

.panel-divider:hover,
.panel-divider:active {
  background: var(--brand);
  opacity: 0.5;
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
.preset-icon { width: 14px; height: 14px; }

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

.step-quiz-btn {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 10px;
  border: 1px solid var(--hairline);
  background: #fff;
  color: var(--brand);
  cursor: pointer;
  transition: all .15s;
  margin-left: auto;
}

.step-quiz-btn:hover {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

.step-quiz-btn.locked {
  color: var(--weak);
  cursor: not-allowed;
  opacity: 0.6;
}

.step-quiz-btn.passed {
  color: #059669;
  border-color: #34d399;
  background: #f0fdf4;
}

.step-quiz-btn.passed:hover {
  background: #34d399;
  color: #fff;
  border-color: #34d399;
}

.quiz-icon {
  width: 14px;
  height: 14px;
  vertical-align: middle;
  margin-right: 2px;
}

.quiz-dialog-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
}

.quiz-title-icon {
  width: 22px;
  height: 22px;
}

.act-btn.final-test {
  color: #059669;
  border-color: #34d399;
  background: #f0fdf4;
}

.act-btn.final-test:hover {
  background: #34d399;
  color: #fff;
  border-color: #34d399;
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

/* 步骤操作按钮 */
.tl-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.step-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: 16px;
  border: 1px solid var(--hairline);
  background: #fff;
  font-size: 12px;
  cursor: pointer;
  transition: all .15s;
}

.step-btn:hover:not(:disabled) { border-color: var(--brand); color: var(--brand); }
.step-btn:disabled { opacity: .5; cursor: not-allowed; }

.step-btn.quiz { border-color: var(--brand); color: var(--brand); }
.step-btn.quiz:hover:not(:disabled) { background: var(--brand); color: #fff; }
.step-btn.links { border-color: #f59e4b; color: #d97706; }
.step-btn.links:hover:not(:disabled) { background: #f59e4b; color: #fff; }

.step-done-mark { font-size: 11px; color: #059669; }

/* AI 生成的学习链接 */
.ai-links {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.ai-links-label {
  font-size: 11px;
  color: #059669;
  font-weight: 600;
  margin-bottom: 6px;
}

.ai-link-item { margin-bottom: 4px; font-size: 12px; }

.ai-link-item a {
  color: var(--brand);
  text-decoration: none;
  transition: color .15s;
}

.ai-link-item a:hover { color: var(--brand-dark); text-decoration: underline; }

.ai-link-item small { color: var(--weak); margin-left: 4px; }

.ai-link-no-url { color: #059669; cursor: default; }

.ai-links-error {
  margin-top: 8px;
  font-size: 12px;
  color: var(--danger);
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

.btn-icon { width: 14px; height: 14px; vertical-align: middle; margin-right: 2px; }

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
