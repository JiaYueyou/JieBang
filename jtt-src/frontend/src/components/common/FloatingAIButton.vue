<script setup lang="ts">
import { ref, nextTick, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePositionsStore } from '@/stores/positions'
import { useLearningStore } from '@/stores/learning'
import { useFavoritesStore } from '@/stores/favorites'
import { pageData } from '@/stores/pageContext'
import { assistantApi } from '@/api/assistant'
import { resumeApi } from '@/api/resume'
import { matchApi } from '@/api/match'
import type { ChatMessage, PageContext, ChatAction } from '@/types'
import { mockResumes } from '@/mock/data/resume'
import { mockPositions } from '@/mock/data/positions'

const route = useRoute()
const router = useRouter()
const positionsStore = usePositionsStore()
const learningStore = useLearningStore()
const favoritesStore = useFavoritesStore()

// ── State ──
const visible = ref(false)
const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const wrapperRef = ref<HTMLDivElement>()
const chatBodyRef = ref<HTMLDivElement>()
const inputRef = ref<HTMLInputElement>()
const fileInputRef = ref<HTMLInputElement>()
const pendingImages = ref<{ dataUrl: string; name: string }[]>([])
const previewImageUrl = ref('')
const isSending = ref(false)
let msgId = 0

// ── Conversation history (last 20 for context) ──
const conversationHistory = computed(() =>
  messages.value
    .slice(-20)
    .map(m => ({ role: m.role, content: m.content }))
)

// ── Page context ──
const pageContext = computed<PageContext>(() => {
  const ctx: PageContext = {
    name: (route.name as string) || 'unknown',
    path: route.fullPath,
    params: route.params as Record<string, any>,
  }
  if (positionsStore.currentPosition) {
    ctx.positionId = positionsStore.currentPosition.id
    ctx.positionName = positionsStore.currentPosition.name
  }
  // Attach resume data from shared store
  if (pageData.resume) {
    const r = pageData.resume
    ctx.resumeId = r.id
    ctx.resumeData = {
      name: r.name,
      targetPosition: r.targetPosition || '',
      skills: r.skills.map(s => ({ name: s.name, level: s.level, category: s.category })),
      workExperience: r.workExperience.map(w => ({
        company: w.company, position: w.position, description: w.description, skills: w.skills,
      })),
      education: r.education.map(e => ({ school: e.school, degree: e.degree, major: e.major })),
    }
  }
  // [简历分析流程] 用户在悬浮球中选定的简历（覆盖 pageData，agent 工具用真实数据）
  if (selectedResume.value) {
    const r = selectedResume.value
    ctx.resumeData = {
      name: getResumeName(r),
      targetPosition: getResumeTarget(r),
      skills: getResumeSkills(r).map((s: any) => ({ name: s.name || s, level: s.level || '', category: s.category || '' })),
      workExperience: (r.work_experience_list || r.workExperience || []).map((w: any) => ({
        company: w.company || '', position: w.position || '', description: w.description || '', skills: w.skills || [],
      })),
      education: (r.education_list || r.education || []).map((e: any) => ({ school: e.school || '', degree: e.degree || '', major: e.major || '' })),
    }
  }
  // Attach match data from shared store
  if (pageData.match) {
    const m = pageData.match
    ctx.matchData = {
      totalScore: m.totalScore,
      positionName: m.positionName,
      resumeName: m.resumeName,
      dimensions: m.dimensions.map(d => ({ name: d.name, score: d.score, weight: d.weight })),
      missingSkills: m.gapAnalysis.missingSkills.map(s => s.name),
      weakSkills: m.gapAnalysis.weakSkills.map(s => s.name),
      matchSkills: m.gapAnalysis.matchSkills.map(s => s.name),
    }
  }
  return ctx
})

const inputPlaceholder = computed(() => {
  const map: Record<string, string> = {
    'positions-detail': '问关于这个岗位的问题…',
    'positions-index': '搜索你想了解的岗位…',
    match: '问关于匹配结果的问题…',
    'match-result': '如何提高匹配分数？',
    graph: '问关于技能图谱的问题…',
    learning: '问关于学习路径的问题…',
  }
  return map[pageContext.value.name] || '输入问题，Enter 发送…'
})

// ── Smart context-aware suggestions ──
const quickActions = computed(() => {
  const n = pageContext.value.name
  const currentPos = positionsStore.currentPosition
  if (n === 'positions-detail' && currentPos) {
    return [{
      label: `分析「${currentPos.name}」是否适合我`,
      action: () => sendMessage(`分析${currentPos.name}这个岗位的要求和前景`),
    }]
  }
  if (n === 'positions' || n === 'positions-index') {
    return [{ label: '推荐适合我的岗位', action: () => sendMessage('根据我的情况推荐合适的岗位') }]
  }
  if (n?.startsWith('resume')) {
    return [{ label: '简历优化建议', action: () => sendMessage('我想优化简历') }]
  }
  if (n === 'match' || n === 'match-result') {
    return [{ label: '解读匹配得分', action: () => sendMessage('帮我解读匹配结果') }]
  }
  if (n === 'graph') {
    return [{ label: '图谱使用指南', action: () => sendMessage('这个知识图谱怎么用？') }]
  }
  if (n === 'learning') {
    return [{ label: '查看学习计划', action: () => router.push('/learning') }]
  }
  return []
})

const presetPages = computed(() => [
  { label: '浏览岗位', icon: 'Search', action: () => router.push('/positions') },
  { label: '学习路径', icon: 'Guide', action: () => router.push('/learning') },
  { label: '简历优化', icon: 'Edit', action: () => sendMessage('__resume_optimize__') },
  { label: '匹配诊断', icon: 'DataAnalysis', action: () => sendMessage('__match_diagnose__') },
])

// 示例问题：让用户一眼看出可以问什么（展示 agent 的能力面）
const exampleQuestions = [
  '我想转行做系统架构师，需要学什么？',
  '分析我的简历，哪些技能需要加强？',
  'Java 后端 2026 年的就业前景如何？',
  '微服务和单体架构怎么选？',
  '帮我对比几个适合我的岗位',
]

// ── Time formatting ──
const formatTime = (ts: number) => {
  const d = Date.now() - ts
  if (d < 60_000) return '刚刚'
  if (d < 3_600_000) return `${Math.floor(d / 60_000)} 分钟前`
  if (d < 86_400_000) return `${Math.floor(d / 3_600_000)} 小时前`
  return new Date(ts).toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const hasMessages = () => messages.value.length > 0

// ── Scroll ──
const scrollToBottom = (smooth = false) => {
  nextTick(() => {
    if (chatBodyRef.value) {
      chatBodyRef.value.scrollTo({
        top: chatBodyRef.value.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto',
      })
    }
  })
}

// ── Keyboard ──
const onGlobalKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && visible.value) { visible.value = false }
}

// 点击面板外部区域时收起聊天框
const onClickOutside = (e: MouseEvent) => {
  if (visible.value && wrapperRef.value && !wrapperRef.value.contains(e.target as Node)) {
    visible.value = false
  }
}

onMounted(() => {
  document.addEventListener('keydown', onGlobalKeydown)
  document.addEventListener('click', onClickOutside)
})
onUnmounted(() => {
  document.removeEventListener('keydown', onGlobalKeydown)
  document.removeEventListener('click', onClickOutside)
})

watch(visible, v => { if (v) nextTick(() => inputRef.value?.focus()) })

// ── Markdown ──
const renderMarkdown = (text: string): string => {
  return text
    .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre class="md-code"><code>$2</code></pre>')
    .replace(/## (.+)/g, '<h3 class="md-h3">$1</h3>')
    .replace(/### (.+)/g, '<h4 class="md-h4">$1</h4>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code class="md-inline-code">$1</code>')
    .replace(/^> (.+)$/gm, '<blockquote class="md-quote">$1</blockquote>')
    .replace(/^- (.+)$/gm, '<li class="md-li">$1</li>')
    .replace(/(\d+)\. (.+)/g, '<li class="md-li">$2</li>')
    .replace(/\n\n/g, '<br/>')
}

// ── Local flow helpers ──

const addAssistantMsg = (content: string, actions?: ChatAction[], followUps?: string[]) => {
  messages.value.push({
    id: `m-${++msgId}`,
    role: 'assistant',
    content,
    timestamp: Date.now(),
    actions,
    followUpQuestions: followUps,
  })
}

// 从后端加载真实简历（失败时用 mock 兜底）
const realResumes = ref<any[]>([])
const loadResumes = async () => {
  try {
    const res: any = await resumeApi.getList()
    realResumes.value = res.data || []
  } catch {
    realResumes.value = mockResumes
  }
  return realResumes.value
}

// 兼容后端 snake_case 和前端 camelCase
const getResumeName = (r: any) => r.name || ''
const getResumeTarget = (r: any) => r.target_position || r.targetPosition || ''
const getResumeSkills = (r: any) => r.skill_list || r.skills || []

// ── [简历分析流程] 意图拦截 → 选简历 → 拉详情 → 走 agent ──
const selectedResume = ref<any>(null)
const awaitingResumePick = ref(false)

const RESUME_INTENT = /简历|技能.*(加强|提升|差距|分析|薄弱)|(分析|评估).*(技能|履历)/

const startResumeAnalysis = async (userMsg: string) => {
  awaitingResumePick.value = false
  const resumes = await loadResumes()
  if (resumes.length === 0) {
    addAssistantMsg('你还没有简历。可以选择：', [
      { label: '📋 上传简历文件', to: '/resume/upload', icon: 'Upload' },
      { label: '✏️ 新建空白简历', to: '/resume/editor', icon: 'Edit' },
    ])
    return
  }
  const list = resumes.map((r: any) => '- **' + getResumeName(r) + '**' + (getResumeTarget(r) ? '（目标：' + getResumeTarget(r) + '）' : '')).join('\n')
  addAssistantMsg(
    '好的！要分析哪份简历？\n\n' + list + '\n\n也可以直接粘贴简历文本、上传图片，或去简历诊断页查看：',
    [
      ...resumes.map((r: any) => ({ label: '分析「' + getResumeName(r) + '」', to: '__analyze_resume__:' + r.id, icon: 'Document' })),
      { label: '📋 上传新简历', to: '/resume/upload', icon: 'Upload' },
      { label: '🏥 简历诊断页', to: '/diagnosis', icon: 'Search' },
    ],
  )
}

const analyzeWithResume = async (resumeId: string) => {
  // 拉取该简历完整详情，注入 agent 上下文
  let detail: any = null
  try {
    const res: any = await resumeApi.getDetail(resumeId)
    detail = res.data
  } catch {
    detail = realResumes.value.find((r: any) => String(r.id) === resumeId)
  }
  if (!detail) {
    addAssistantMsg('简历加载失败，请稍后再试。')
    return
  }
  selectedResume.value = detail

  // 直接走 agent 循环（带完整简历数据）
  await sendMessage('请分析我的简历「' + getResumeName(detail) + '」，哪些技能需要加强？结合知识图谱给出具体建议')
}

// ══════════ [网站数据整合] 四个高价值数据采集器 ══════════

// 1️⃣ 学习进度：读学习路径 store，汇总各路径完成度/卡点
const gatherLearningProgress = (): string => {
  const paths = learningStore.paths || []
  if (paths.length === 0) return '用户暂无学习路径'
  const lines: string[] = []
  for (const p of paths) {
    const total = p.steps?.length || 0
    const done = p.steps?.filter((s: any) => s.completed).length || 0
    const pct = total ? Math.round((done / total) * 100) : 0
    const passed = p.steps?.filter((s: any) => s.quizPassed).length || 0
    lines.push(`- ${p.name}：${done}/${total} 步完成（${pct}%），测验通过 ${passed} 项`)
    // 找第一个未完成步骤 = 卡点
    const stuck = p.steps?.find((s: any) => !s.completed)
    if (stuck && done > 0) lines.push(`  当前卡在：${stuck.title}（${stuck.duration || ''}）`)
  }
  return `[用户学习进度数据（来自学习路径页）]\n${lines.join('\n')}`

}

// 2️⃣ 匹配历史：拉历次匹配分数做趋势
const gatherMatchHistory = async (): Promise<string> => {
  try {
    const res: any = await matchApi.getHistory()
    const history = res.data || []
    if (history.length === 0) return '[匹配历史] 用户暂无匹配记录'
    const sorted = [...history].sort((a: any, b: any) =>
      String(a.match_date || '').localeCompare(String(b.match_date || '')))
    const lines = sorted.slice(-8).map((m: any) =>
      `${String(m.match_date || '').slice(0, 10)} ${m.position_name || m.positionName || '?'}：${m.total_score ?? m.totalScore ?? '?'}分`)
    return `[用户匹配历史（来自匹配诊断页，时间升序）]\n${lines.join('\n')}`
  } catch {
    return '[匹配历史] 数据加载失败'
  }
}

// 3️⃣ 收藏夹：岗位/资源收藏
const gatherFavorites = (): string => {
  const favs = favoritesStore.allFavorites || []
  if (favs.length === 0) return '[收藏夹] 用户暂无收藏'
  const pos = favs.filter((f: any) => f.item_type === 'position').map((f: any) => f.title)
  const res = favs.filter((f: any) => f.item_type === 'learning_resource').map((f: any) => f.title)
  const parts: string[] = []
  if (pos.length) parts.push(`收藏的岗位（${pos.length}个）：${pos.join('、')}`)
  if (res.length) parts.push(`收藏的学习资源（${res.length}个）：${res.join('、')}`)
  return parts.length ? `[用户收藏夹数据]\n${parts.join('\n')}` : '[收藏夹] 用户暂无收藏'
}

// 4️⃣ 错题本：测验答错的题
const gatherQuizErrors = (): string => {
  const errs = favoritesStore.errorFavs || []
  if (errs.length === 0) return '[错题本] 暂无错题记录'
  const lines = errs.map((e: any) => {
    const meta = e.metadata || {}
    return `- ${e.title}${meta.related_skills?.length ? '（关联：' + meta.related_skills.join('、') + '）' : ''}`
  })
  return `[用户错题本（来自学习测验）]\n${lines.join('\n')}`
}

// 意图识别 → 采集对应数据 → 注入 agent 消息
const SITE_INTENTS: { re: RegExp; gather: () => Promise<string> | string; note: string }[] = [
  { re: /学得怎么样|学习进度|学习情况|进度怎么样|卡在|继续学什么/, gather: gatherLearningProgress, note: '学习进度分析' },
  { re: /匹配历史|几次匹配|匹配.*变好|匹配.*趋势|历次匹配/, gather: gatherMatchHistory, note: '匹配趋势分析' },
  { re: /收藏|收藏夹|收藏的岗位|收藏的岗位哪个/, gather: gatherFavorites, note: '收藏分析' },
  { re: /错题|复习.*题|答错|薄弱.*题/, gather: gatherQuizErrors, note: '错题复习' },
]

// 命中站点数据意图时：采集真实数据拼进消息发给 agent
const trySiteDataIntent = async (msg: string): Promise<string | null> => {
  for (const intent of SITE_INTENTS) {
    if (intent.re.test(msg)) {
      const data = await intent.gather()
      // 收藏数据懒加载
      if (intent.note === '收藏分析' && (favoritesStore.allFavorites || []).length === 0) {
        try { await favoritesStore.fetchAll() } catch { /* 忽略 */ }
        return await intent.gather()
      }
      return data
    }
  }
  return null
}

const handleResumeOptimize = async () => {
  const resumes = await loadResumes()
  if (resumes.length === 0) {
    addAssistantMsg('你还没有简历，是否新建一份？', [
      { label: '新建简历', to: '/resume/editor', icon: 'Plus' },
    ])
    return
  }
  const list = resumes.map((r: any) => '- **' + getResumeName(r) + '**' + (getResumeTarget(r) ? '（目标：' + getResumeTarget(r) + '）' : '')).join('\n')
  addAssistantMsg(
    '你有 ' + resumes.length + ' 份简历，想优化哪一份？\n\n' + list,
    resumes.map((r: any) => ({ label: '优化「' + getResumeName(r) + '」', to: '/resume/editor/' + r.id, icon: 'Edit' }))
  )
}

const handleMatchDiagnose = async () => {
  const resumes = await loadResumes()
  if (resumes.length === 0) {
    addAssistantMsg('请先创建一份简历再进行匹配诊断。', [
      { label: '新建简历', to: '/resume/editor', icon: 'Plus' },
    ])
    return
  }
  const list = resumes.map((r: any) => '- **' + getResumeName(r) + '**' + (getResumeTarget(r) ? '（目标：' + getResumeTarget(r) + '）' : '')).join('\n')
  addAssistantMsg(
    '用哪份简历去匹配？\n\n' + list,
    resumes.map((r: any) => ({ label: '用「' + getResumeName(r) + '」匹配', to: '__match_resume__:' + r.id, icon: 'DataAnalysis' }))
  )
}

const showMatchResults = (resumeId: string) => {
  const resume = realResumes.value.find((r: any) => String(r.id) === resumeId)
  const resumeSkills: string[] = (resume ? getResumeSkills(resume) : []).map((s: any) => (s.name || '').toLowerCase())

  // Compute scores for each position
  const scored = mockPositions.map(pos => {
    const posSkills = [...(pos.requiredSkills || []), ...(pos.preferredSkills || [])].map(s => s.name.toLowerCase())
    const matched = posSkills.filter(s => resumeSkills.some(rs => rs.includes(s) || s.includes(rs)))
    const matchRate = posSkills.length ? Math.round((matched.length / posSkills.length) * 100) : 0
    return { pos, score: Math.min(matchRate + Math.floor(Math.random() * 15), 100) }
  })

  scored.sort((a, b) => b.score - a.score)
  const top = scored.slice(0, 8)

  const results = top.map((s, i) =>
    (i + 1) + '. **' + s.pos.name + '** — ' + s.score + ' 分' + (s.score >= 80 ? ' 🟢' : s.score >= 50 ? ' 🟡' : ' 🔴')
  ).join('\n')

  addAssistantMsg(
    '根据你的简历「' + (resume ? getResumeName(resume) : '') + '」，以下是匹配度最高的岗位：\n\n' + results,
    top.map(s => ({ label: s.pos.name + '（' + s.score + '分）', to: '__match_position__:' + resumeId + ':' + s.pos.id, icon: 'DataAnalysis' }))
  )
}

// ── Send ──
const sendMessage = async (text?: string) => {
  const msg = (text ?? inputText.value).trim()
  if ((!msg && pendingImages.value.length === 0) || loading.value || isSending.value) return
  isSending.value = true
  inputText.value = ''

  const images = pendingImages.value.map(p => p.dataUrl)
  pendingImages.value = []

  messages.value.push({
    id: `m-${++msgId}`,
    role: 'user',
    content: msg.startsWith('__') ? '(操作请求)' : msg || (images.length > 0 ? '[图片]' : ''),
    images: images.length > 0 ? images : undefined,
    timestamp: Date.now(),
  })
  loading.value = true
  scrollToBottom(true)

  // ── Local flows (intercepted before AI call) ──
  if (msg === '__resume_optimize__') {
    loading.value = false; isSending.value = false
    await handleResumeOptimize()
    scrollToBottom(true)
    nextTick(() => inputRef.value?.focus())
    return
  }
  if (msg === '__match_diagnose__') {
    loading.value = false; isSending.value = false
    await handleMatchDiagnose()
    scrollToBottom(true)
    nextTick(() => inputRef.value?.focus())
    return
  }

  // ── [简历分析流程] 意图拦截：简历相关问题且未选简历 → 先问哪份 ──
  if (!selectedResume.value && RESUME_INTENT.test(msg)) {
    loading.value = false; isSending.value = false
    await startResumeAnalysis(msg)
    scrollToBottom(true)
    nextTick(() => inputRef.value?.focus())
    return
  }
  // 已选简历后的对话结束，清掉选择（下次重新问哪份）
  if (selectedResume.value) {
    setTimeout(() => { selectedResume.value = null }, 1500)
  }

  // ── [网站数据整合] 命中进度/历史/收藏/错题意图 → 采集真实数据注入 agent ──
  let agentMsg = msg
  const siteData = await trySiteDataIntent(msg)
  if (siteData) {
    agentMsg = msg + '\n\n' + siteData + '\n（以上是网站的真实数据，基于它回答；如果数据为空就引导用户去对应页面使用）'
  }

  // ── [P1] Agent 循环对话：LLM 自主调工具，思考过程逐步展示 ──
  const thinkMsg: ChatMessage = {
    id: `m-${++msgId}`,
    role: 'assistant',
    content: '🤖 分析你的问题，规划工具调用…',
    timestamp: Date.now(),
  }
  messages.value.push(thinkMsg)
  scrollToBottom(true)

  try {
    const res: any = await assistantApi.agentChat({
      message: agentMsg || '',
      images,
      pageContext: pageContext.value,
      history: conversationHistory.value,
    })
    const d = res.data

    // 逐步回放思考步骤（工具调用轨迹，每步 500ms）
    const steps: { icon: string; text: string }[] = d?.thinkingSteps || []
    for (let i = 0; i < steps.length; i++) {
      thinkMsg.content = steps.slice(0, i + 1).map(s => s.icon + ' ' + s.text).join('\n')
      scrollToBottom(true)
      await new Promise(r => setTimeout(r, 500))
    }

    // 思考完成后，紧接最终回答
    await new Promise(r => setTimeout(r, 300))
    messages.value.push({
      id: `m-${++msgId}`,
      role: 'assistant',
      content: d?.reply || '抱歉，我暂时无法回答这个问题。',
      timestamp: Date.now(),
      followUpQuestions: d?.followUpQuestions,
    })
  } catch {
    thinkMsg.content = '⚠️ Agent 调用失败，回退普通对话重试…'
    try {
      const res: any = await assistantApi.chat({
        message: msg || '',
        images,
        pageContext: pageContext.value,
        history: conversationHistory.value,
      })
      messages.value.push({
        id: `m-${++msgId}`,
        role: 'assistant',
        content: res.data?.reply || '抱歉，我暂时无法回答这个问题。',
        timestamp: Date.now(),
        relatedConcepts: res.data?.relatedConcepts,
        suggestedResources: res.data?.suggestedResources,
        followUpQuestions: res.data?.followUpQuestions,
        actions: res.data?.actions,
      })
    } catch {
      messages.value.push({
        id: `m-${++msgId}`,
        role: 'assistant',
        content: '网络请求失败，请稍后再试。',
        timestamp: Date.now(),
        actions: [{ label: '重新发送', to: '__retry__', icon: 'Refresh' }],
      })
    }
  } finally {
    loading.value = false
    isSending.value = false
    nextTick(() => inputRef.value?.focus())
    scrollToBottom(true)
  }
}

const onActionClick = async (act: ChatAction) => {
  if (act.to === '__retry__') {
    const lastUser = [...messages.value].reverse().find(m => m.role === 'user')
    if (lastUser) {
      messages.value = messages.value.slice(0, -1)
      sendMessage(lastUser.content)
    }
    return
  }
  // 简历分析：选定的简历 → 拉详情走 agent
  if (act.to.startsWith('__analyze_resume__:')) {
    const rid = act.to.split(':')[1] || ''
    if (rid) await analyzeWithResume(rid)
    return
  }
  // Match flow: resume selected → compute scores
  if (act.to.startsWith('__match_resume__:')) {
    const resumeId = act.to.split(':')[1] || ''
    if (resumeId) showMatchResults(resumeId)
    return
  }
  // Match flow: position selected → navigate to match result
  if (act.to.startsWith('__match_position__:')) {
    const parts = act.to.split(':')
    router.push('/match/result/' + parts[1] + '/' + parts[2])
    return
  }
  router.push(act.to)
}

// ── Controls ──
const toggle = () => { visible.value = !visible.value }
const onClose = () => { visible.value = false; pendingImages.value = [] }
const newConversation = () => { messages.value = []; pendingImages.value = []; msgId = 0 }

// ── Images ──
const triggerFilePick = () => fileInputRef.value?.click()
const onFilesSelected = (e: Event) => {
  const files = (e.target as HTMLInputElement).files
  if (!files) return
  Array.from(files).filter(f => f.type.startsWith('image/')).forEach(file => {
    const reader = new FileReader()
    reader.onload = () => pendingImages.value.push({ dataUrl: reader.result as string, name: file.name })
    reader.readAsDataURL(file)
  })
  ;(e.target as HTMLInputElement).value = ''
}
const removePendingImage = (idx: number) => { pendingImages.value.splice(idx, 1) }
const onPaste = (e: ClipboardEvent) => {
  const items = e.clipboardData?.items
  if (!items) return
  Array.from(items).filter(i => i.type.startsWith('image/')).forEach(item => {
    const file = item.getAsFile()
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => pendingImages.value.push({ dataUrl: reader.result as string, name: `clipboard-${Date.now()}.png` })
    reader.readAsDataURL(file)
  })
}
const showPreview = (url: string) => { previewImageUrl.value = url }
const closePreview = () => { previewImageUrl.value = '' }
</script>

<template>
  <div ref="wrapperRef" class="ai-float-wrapper">
    <!-- ═══ Panel ═══ -->
    <transition name="slide-up">
      <div v-if="visible" class="ai-panel">
        <!-- Header -->
        <div class="ai-header">
          <div class="ai-header-left">
            <span class="ai-header-icon">✨</span>
            <span class="ai-header-title">AI 助手</span>
            <span v-if="messages.length > 0" class="ai-header-count">{{ messages.length }}</span>
          </div>
          <div class="ai-header-actions">
            <button v-if="hasMessages()" class="header-btn" title="新对话" @click="newConversation">
              <el-icon :size="16"><Plus /></el-icon>
            </button>
            <button class="header-btn" title="关闭" @click="onClose">
              <el-icon :size="16"><Close /></el-icon>
            </button>
          </div>
        </div>

        <!-- ═══ Body ═══ -->
        <div ref="chatBodyRef" class="ai-body">
          <!-- Welcome -->
          <div v-if="!hasMessages()" class="welcome">
            <div class="welcome-avatar">🤖</div>
            <p class="welcome-greeting">你好！我是 AI 智能体</p>
            <p class="welcome-sub">我会自主调用工具（知识图谱 / 联网搜索 / 简历分析）来回答你的问题，不只是聊天</p>

            <div class="welcome-section">
              <span class="welcome-label">💡 你可以这样问我（点击直接发）</span>
              <div class="example-list">
                <button
                  v-for="ex in exampleQuestions" :key="ex"
                  class="example-chip" :disabled="loading"
                  @click="sendMessage(ex)"
                >{{ ex }}</button>
              </div>
            </div>

            <div v-if="quickActions.length > 0" class="welcome-section">
              <span class="welcome-label">当前页面</span>
              <button
                v-for="qa in quickActions" :key="qa.label"
                class="chip chip-primary" :disabled="loading"
                @click="qa.action"
              >{{ qa.label }}</button>
            </div>

            <div class="welcome-section">
              <span class="welcome-label">快捷导航</span>
              <div class="welcome-grid">
                <button
                  v-for="p in presetPages" :key="p.label"
                  class="nav-card" :disabled="loading"
                  @click="p.action"
                >
                  <el-icon :size="18"><component :is="p.icon" /></el-icon>
                  <span>{{ p.label }}</span>
                </button>
              </div>
            </div>

            <p class="welcome-hint">任意职业问题都可以问 · 支持图片分析（Ctrl+V 粘贴）</p>
          </div>

          <!-- Messages -->
          <template v-for="(msg, idx) in messages" :key="msg.id">
            <div
              class="msg" :class="msg.role"
              :style="{ animationDelay: `${idx * 0.05}s` }"
            >
              <!-- Label -->
              <div class="msg-label">
                <span class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</span>
                <span class="msg-author">{{ msg.role === 'user' ? '你' : 'AI 助手' }}</span>
                <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
              </div>

              <!-- Bubble -->
              <div class="msg-bubble" :class="msg.role">
                <!-- Images -->
                <div v-if="msg.images?.length" class="msg-images">
                  <img
                    v-for="(img, ii) in msg.images" :key="ii"
                    :src="img" class="msg-img"
                    @click="showPreview(img)"
                  />
                </div>
                <!-- Text -->
                <div v-if="msg.role === 'user'" class="msg-text">{{ msg.content }}</div>
                <div v-else class="msg-text md-body" v-html="renderMarkdown(msg.content)"></div>

                <!-- Actions -->
                <div v-if="msg.actions?.length" class="msg-actions">
                  <button
                    v-for="act in msg.actions" :key="act.label"
                    class="act-btn"
                    @click="onActionClick(act)"
                  >
                    <el-icon v-if="act.icon" :size="13"><component :is="act.icon" /></el-icon>
                    {{ act.label }}
                  </button>
                </div>

                <!-- Concepts + Resources -->
                <div v-if="msg.relatedConcepts?.length || msg.suggestedResources?.length" class="msg-extras">
                  <div v-if="msg.relatedConcepts?.length" class="extra-row">
                    <span class="extra-emoji">🧩</span>
                    <span v-for="c in msg.relatedConcepts" :key="c.name" class="tag tag-concept">{{ c.name }}</span>
                  </div>
                  <div v-if="msg.suggestedResources?.length" class="extra-row">
                    <span class="extra-emoji">📚</span>
                    <span v-for="r in msg.suggestedResources" :key="r.id" class="tag tag-resource">{{ r.title }}</span>
                  </div>
                </div>

                <!-- Follow-ups -->
                <div v-if="msg.followUpQuestions?.length" class="msg-followups">
                  <button
                    v-for="(q, qi) in msg.followUpQuestions" :key="qi"
                    class="fup-btn" :disabled="loading"
                    @click="sendMessage(q)"
                  >{{ q }}</button>
                </div>
              </div>
            </div>
          </template>

          <!-- Typing -->
          <div v-if="loading" class="msg assistant">
            <div class="msg-label">
              <span class="msg-avatar">🤖</span>
              <span class="msg-author">AI 助手</span>
            </div>
            <div class="msg-bubble assistant">
              <div class="typing-dots">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </div>
            </div>
          </div>
        </div>

        <!-- ═══ Footer ═══ -->
        <div class="ai-footer">
          <div v-if="pendingImages.length > 0" class="image-strip">
            <div v-for="(img, idx) in pendingImages" :key="idx" class="image-strip-item">
              <img :src="img.dataUrl" class="strip-thumb" />
              <button class="strip-remove" @click="removePendingImage(idx)">×</button>
            </div>
          </div>

          <div class="input-bar">
            <input ref="fileInputRef" type="file" accept="image/*" multiple class="file-hidden" @change="onFilesSelected" />
            <button class="ibar-btn" title="上传图片" :disabled="loading" @click="triggerFilePick">
              <el-icon :size="18"><PictureFilled /></el-icon>
            </button>
            <input
              ref="inputRef"
              v-model="inputText"
              class="ibar-input"
              :placeholder="inputPlaceholder"
              :disabled="loading"
              @keydown.enter.prevent="sendMessage()"
              @paste="onPaste"
            />
            <button
              class="ibar-btn ibar-send"
              :disabled="(!inputText.trim() && pendingImages.length === 0) || loading"
              @click="sendMessage()"
            >
              <el-icon :size="18"><Promotion /></el-icon>
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- ═══ Image preview overlay ═══ -->
    <transition name="fade">
      <div v-if="previewImageUrl" class="overlay" @click.self="closePreview">
        <button class="overlay-close" @click="closePreview">×</button>
        <img :src="previewImageUrl" class="overlay-img" />
      </div>
    </transition>

    <!-- ═══ FAB ═══ -->
    <button class="ai-fab" :class="{ active: visible }" @click="toggle">
      <el-icon :size="28">
        <component :is="visible ? 'Close' : 'ChatDotRound'" />
      </el-icon>
    </button>
  </div>
</template>

<style scoped>
.ai-float-wrapper {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 999;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

/* ─── FAB ─── */
.ai-fab {
  width: 52px; height: 52px;
  border-radius: 50%;
  background: var(--brand);
  color: #fff;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(79,110,246,.35);
  cursor: pointer;
  transition: all .25s ease;
}
.ai-fab:hover {
  background: var(--brand-dark);
  transform: scale(1.08);
}
.ai-fab.active { background: #fff; color: var(--ink); box-shadow: var(--shadow-hover); }

/* ─── Panel ─── */
.ai-panel {
  width: 380px;
  height: 580px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 8px 40px rgba(0,0,0,.13);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--hairline);
  flex-shrink: 0;
}
.ai-header-left { display: flex; align-items: center; gap: 8px; }
.ai-header-icon { font-size: 18px; }
.ai-header-title { font-size: 15px; font-weight: 700; }
.ai-header-count {
  font-size: 11px;
  background: var(--brand-light);
  color: var(--brand);
  padding: 1px 7px;
  border-radius: 10px;
  font-weight: 600;
}
.ai-header-actions { display: flex; gap: 4px; }
.header-btn {
  width: 30px; height: 30px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all .15s;
}
.header-btn:hover { background: var(--canvas); color: var(--ink); }

/* ─── Body ─── */
.ai-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-body::-webkit-scrollbar { width: 4px; }
.ai-body::-webkit-scrollbar-thumb { background: var(--weak); border-radius: 2px; }

/* Welcome */
.welcome { text-align: center; padding: 16px 0 8px; }
.welcome-avatar { font-size: 40px; margin-bottom: 8px; }
.welcome-greeting { font-size: 15px; font-weight: 700; margin-bottom: 4px; }
.welcome-sub { font-size: 12px; color: var(--weak); margin-bottom: 18px; line-height: 1.5; }
.welcome-hint { font-size: 11px; color: var(--weak); margin-top: 12px; opacity: .7; }
.welcome-section { margin-bottom: 14px; text-align: left; }
.welcome-label {
  display: block;
  font-size: 10px;
  color: var(--weak);
  text-transform: uppercase;
  letter-spacing: .6px;
  margin-bottom: 8px;
  padding-left: 2px;
}
.welcome-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.nav-card {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid var(--hairline);
  background: var(--canvas);
  color: var(--ink);
  font-size: 13px;
  cursor: pointer;
  transition: all .15s;
  flex: 1;
  justify-content: center;
  min-width: calc(50% - 4px);
}
.nav-card:hover:not(:disabled) { border-color: var(--brand); color: var(--brand); background: var(--brand-light); }
.nav-card:disabled { opacity: .5; cursor: not-allowed; }

/* Chips */
.chip {
  display: inline-flex; align-items: center;
  padding: 7px 14px;
  border-radius: 20px;
  border: 1px solid var(--hairline);
  background: #fff;
  font-size: 12px;
  cursor: pointer;
  margin: 3px;
  transition: all .15s;
}
.chip-primary { border-color: var(--brand); color: var(--brand); }
.chip-primary:hover:not(:disabled) { background: var(--brand); color: #fff; }
.chip:disabled { opacity: .5; cursor: not-allowed; }

/* 示例问题（可点击直接发送） */
.example-list { display: flex; flex-direction: column; gap: 6px; }
.example-chip {
  text-align: left;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid var(--hairline);
  background: var(--canvas);
  color: var(--ink);
  font-size: 12px;
  cursor: pointer;
  transition: all .15s;
  line-height: 1.4;
}
.example-chip:hover:not(:disabled) {
  border-color: var(--brand);
  color: var(--brand);
  background: var(--brand-light);
}
.example-chip:disabled { opacity: .5; cursor: not-allowed; }

/* ─── Messages ─── */
.msg {
  display: flex;
  flex-direction: column;
  gap: 4px;
  animation: msgIn .3s ease both;
}
@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.msg.user { align-items: flex-end; }
.msg.assistant { align-items: flex-start; }

.msg-label { display: flex; align-items: center; gap: 6px; padding: 0 4px; }
.msg-avatar { font-size: 14px; line-height: 1; }
.msg-author { font-size: 11px; font-weight: 600; color: var(--muted); }
.msg-time { font-size: 10px; color: var(--weak); }

.msg-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.7;
  max-width: 90%;
  position: relative;
}
.msg-bubble.user {
  background: var(--brand);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-bubble.assistant {
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-bottom-left-radius: 4px;
}

.msg-text { word-break: break-word; white-space: pre-wrap; }

/* Markdown */
.md-body :deep(.md-h3) { font-size: 14px; font-weight: 700; margin: 8px 0 4px; }
.md-body :deep(.md-h4) { font-size: 13px; font-weight: 700; margin: 6px 0 3px; }
.md-body :deep(strong) { font-weight: 600; }
.md-body :deep(.md-inline-code) { background: #e8ebf0; padding: 1px 5px; border-radius: 4px; font-size: 12px; font-family: 'JetBrains Mono', monospace; }
.md-body :deep(.md-code) { background: #1a1d28; color: #e4e4e7; padding: 10px 14px; border-radius: 8px; overflow-x: auto; font-size: 12px; line-height: 1.6; margin: 6px 0; }
.md-body :deep(.md-code code) { font-family: 'JetBrains Mono', monospace; }
.md-body :deep(.md-quote) { border-left: 3px solid var(--brand); padding: 4px 10px; margin: 4px 0; background: #fff; border-radius: 0 6px 6px 0; font-size: 12px; color: var(--muted); }
.md-body :deep(.md-li) { margin: 2px 0 2px 4px; }

/* Images in bubbles */
.msg-images { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }
.msg-img {
  max-width: 180px; max-height: 140px;
  border-radius: 8px; cursor: pointer;
  border: 1px solid rgba(255,255,255,.2);
  transition: opacity .2s;
}
.msg-img:hover { opacity: .85; }
.msg-bubble.user .msg-img { border-color: rgba(255,255,255,.3); }

/* Action buttons inside bubbles */
.msg-actions { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.act-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 5px 12px;
  border-radius: 8px;
  border: none;
  background: var(--brand);
  color: #fff;
  font-size: 12px;
  cursor: pointer;
  transition: opacity .15s;
}
.act-btn:hover { opacity: .85; }
.msg-bubble.user .act-btn { background: rgba(255,255,255,.2); }
.msg-bubble.user .act-btn:hover { background: rgba(255,255,255,.3); }

/* Extras */
.msg-extras { margin-top: 8px; padding-top: 6px; border-top: 1px dashed var(--hairline); }
.extra-row { display: flex; align-items: center; gap: 4px; margin-bottom: 4px; flex-wrap: wrap; }
.extra-emoji { font-size: 11px; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; line-height: 1.5; }
.tag-concept { background: #eef2ff; color: var(--brand); }
.tag-resource { background: #f0fdf4; color: #059669; }

/* Follow-ups */
.msg-followups { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px; }
.fup-btn {
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid var(--hairline);
  background: #fff;
  color: var(--brand);
  font-size: 11px;
  cursor: pointer;
  transition: all .15s;
}
.fup-btn:hover:not(:disabled) { background: var(--brand); color: #fff; border-color: var(--brand); }
.fup-btn:disabled { opacity: .5; cursor: not-allowed; }
.msg-bubble.user .fup-btn { background: rgba(255,255,255,.1); border-color: rgba(255,255,255,.2); color: #fff; }
.msg-bubble.user .fup-btn:hover:not(:disabled) { background: rgba(255,255,255,.25); }

/* Typing */
.typing-dots { display: flex; gap: 4px; padding: 4px 0; }
.typing-dots .dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--weak);
  animation: bounce 1.4s infinite ease-in-out both;
}
.typing-dots .dot:nth-child(1) { animation-delay: -.32s; }
.typing-dots .dot:nth-child(2) { animation-delay: -.16s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* ─── Footer ─── */
.ai-footer { flex-shrink: 0; }

/* Image strip */
.image-strip {
  display: flex;
  gap: 8px;
  padding: 8px 14px 0;
  overflow-x: auto;
}
.image-strip-item { position: relative; flex-shrink: 0; }
.strip-thumb { width: 52px; height: 52px; object-fit: cover; border-radius: 8px; border: 1px solid var(--hairline); }
.strip-remove {
  position: absolute; top: -5px; right: -5px;
  width: 17px; height: 17px;
  border-radius: 50%; border: none;
  background: var(--danger); color: #fff;
  font-size: 11px; line-height: 1;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 1px 3px rgba(0,0,0,.2);
}

/* Input bar */
.input-bar {
  display: flex; gap: 6px; align-items: center;
  padding: 8px 14px 12px;
}
.file-hidden { display: none; }
.ibar-btn {
  width: 34px; height: 34px;
  border-radius: 50%;
  border: 1px solid var(--hairline);
  background: #fff;
  color: var(--muted);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all .15s;
}
.ibar-btn:hover:not(:disabled) { border-color: var(--brand); color: var(--brand); }
.ibar-btn:disabled { opacity: .4; cursor: not-allowed; }
.ibar-send { background: var(--brand); color: #fff; border-color: var(--brand); }
.ibar-send:hover:not(:disabled) { background: var(--brand-dark); border-color: var(--brand-dark); }
.ibar-send:disabled { opacity: .4; cursor: not-allowed; }
.ibar-input {
  flex: 1;
  padding: 7px 12px;
  border-radius: 20px;
  border: 1px solid var(--hairline);
  font-size: 13px;
  outline: none;
  transition: border-color .15s;
  min-width: 0;
}
.ibar-input:focus { border-color: var(--brand); }
.ibar-input:disabled { background: var(--canvas); }

/* ─── Image overlay ─── */
.overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.75);
  z-index: 10000;
  display: flex; align-items: center; justify-content: center;
  padding: 40px;
}
.overlay-close {
  position: absolute; top: 20px; right: 24px;
  width: 36px; height: 36px;
  border-radius: 50%;
  border: none;
  background: rgba(255,255,255,.2);
  color: #fff;
  font-size: 22px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.overlay-close:hover { background: rgba(255,255,255,.35); }
.overlay-img { max-width: 100%; max-height: 90vh; border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,.3); }

/* ─── Transitions ─── */
.slide-up-enter-active, .slide-up-leave-active { transition: all .3s ease; }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateY(20px) scale(.95); }
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
