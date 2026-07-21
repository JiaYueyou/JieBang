import { http, HttpResponse, delay } from 'msw'
import { mockPositions } from './data/positions'
import { mockGraphNodes, mockGraphEdges } from './data/skills'
import { mockResumes } from './data/resume'
import { mockMatchResults, mockHistoryMatches } from './data/match'
import { mockTailorSuggestions, generateOptimizedPhrases } from './data/tailor'
import { mockLearningPaths } from './data/learning'
import { mockNotes } from './data/notes'
import { mockCareerAssessments, mockCareerPlans } from './data/career'

const BASE = '/api'

// Mutable mock profile state — edits persist within the browser session
const mockUserProfile = {
  id: 'u-1',
  username: '求职者',
  email: 'user@example.com',
  phone: '',
  nickname: '',
  city: '',
  education: '',
  resumeCount: 2,
  matchHistoryCount: 3,
}

export const handlers = [
  // Auth
  http.post(`${BASE}/auth/login`, async ({ request }) => {
    await delay(500)
    const body = (await request.json()) as any
    if (body.username === '123456' && body.password === '123456') {
      return HttpResponse.json({
        code: 200,
        message: 'ok',
        data: {
          token: 'mock-jwt-token-xxx',
          user: { ...mockUserProfile },
        },
      })
    }
    return HttpResponse.json(
      { code: 401, message: '用户名或密码错误', data: null },
      { status: 401 },
    )
  }),

  http.post(`${BASE}/auth/register`, async ({ request }) => {
    await delay(500)
    const body = await request.json() as any
    return HttpResponse.json({
      code: 200, message: 'ok',
      data: { token: 'mock-jwt-token-xxx', user: { id: 'u-1', username: body.username, email: body.email, resumeCount: 0, matchHistoryCount: 0 } },
    })
  }),

  http.post(`${BASE}/auth/logout`, () => HttpResponse.json({ code: 200, message: 'ok', data: null })),

  http.get(`${BASE}/auth/profile`, () => HttpResponse.json({
    code: 200, message: 'ok',
    data: { ...mockUserProfile },
  })),

  http.put(`${BASE}/auth/profile`, async ({ request }) => {
    await delay(300)
    const body = await request.json() as Partial<typeof mockUserProfile>
    Object.assign(mockUserProfile, body)
    return HttpResponse.json({ code: 200, message: 'ok', data: { ...mockUserProfile } })
  }),

  http.put(`${BASE}/auth/password`, async ({ request }) => {
    await delay(300)
    const body = await request.json() as { oldPassword: string; newPassword: string }
    if (body.oldPassword !== '123456') {
      return HttpResponse.json({ code: 400, message: '原密码错误', data: null }, { status: 400 })
    }
    return HttpResponse.json({ code: 200, message: '密码修改成功', data: null })
  }),

  // Positions
  http.get(`${BASE}/positions`, async ({ request }) => {
    await delay(300)
    const url = new URL(request.url)
    const category = url.searchParams.get('category')
    const keyword = url.searchParams.get('keyword')
    let list = [...mockPositions]
    if (category && category !== 'all') list = list.filter((p) => p.category === category)
    if (keyword) list = list.filter((p) => p.name.includes(keyword) || p.summary.includes(keyword))
    return HttpResponse.json({
      code: 200, message: 'ok',
      data: { list, total: list.length, page: 1, pageSize: 20 },
    })
  }),

  http.get(`${BASE}/positions/:id`, async ({ params }) => {
    await delay(300)
    const pos = mockPositions.find((p) => p.id === params.id)
    if (!pos) return HttpResponse.json({ code: 404, message: 'not found', data: null }, { status: 404 })
    return HttpResponse.json({ code: 200, message: 'ok', data: pos })
  }),

  http.get(`${BASE}/positions/graph`, ({ request }) => {
    const url = new URL(request.url)
    const rootTech = url.searchParams.get('rootTech')
    if (rootTech) {
      const reachable = new Set<string>([rootTech])
      let changed = true
      while (changed) {
        changed = false
        for (const e of mockGraphEdges) {
          if (reachable.has(e.source) && !reachable.has(e.target)) { reachable.add(e.target); changed = true }
          if (reachable.has(e.target) && !reachable.has(e.source)) { reachable.add(e.source); changed = true }
        }
      }
      return HttpResponse.json({
        code: 200, message: 'ok',
        data: {
          nodes: mockGraphNodes.filter((n) => reachable.has(n.id)),
          edges: mockGraphEdges.filter((e) => reachable.has(e.source) && reachable.has(e.target)),
        },
      })
    }
    return HttpResponse.json({ code: 200, message: 'ok', data: { nodes: mockGraphNodes, edges: mockGraphEdges } })
  }),

  // Resume
  http.get(`${BASE}/resumes`, async () => {
    await delay(300)
    return HttpResponse.json({ code: 200, message: 'ok', data: mockResumes })
  }),

  http.get(`${BASE}/resume/:id`, async ({ params }) => {
    const r = mockResumes.find((r) => r.id === params.id)
    if (!r) return HttpResponse.json({ code: 404, message: 'not found', data: null }, { status: 404 })
    return HttpResponse.json({ code: 200, message: 'ok', data: r })
  }),

  http.post(`${BASE}/resume`, async ({ request }) => {
    const body = await request.json() as any
    const newResume = { ...body, id: `r-${Date.now()}`, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }
    return HttpResponse.json({ code: 200, message: 'ok', data: newResume })
  }),

  http.put(`${BASE}/resume/:id`, async ({ params, request }) => {
    const body = await request.json() as any
    return HttpResponse.json({ code: 200, message: 'ok', data: { ...body, id: params.id, updatedAt: new Date().toISOString() } })
  }),

  http.delete(`${BASE}/resume/:id`, () => HttpResponse.json({ code: 200, message: 'ok', data: null })),

  http.post(`${BASE}/resume/:id/duplicate`, async ({ params }) => {
    const r = mockResumes.find((r) => r.id === params.id)
    if (!r) return HttpResponse.json({ code: 404, message: 'not found' }, { status: 404 })
    const dup = { ...r, id: `r-${Date.now()}`, name: `${r.name} (副本)`, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }
    return HttpResponse.json({ code: 200, message: 'ok', data: dup })
  }),

  http.post(`${BASE}/resume/upload`, async () => {
    await delay(1500) // Simulate parsing time
    return HttpResponse.json({
      code: 200, message: 'ok',
      data: {
        id: 'r-uploaded', name: '新上传简历', targetPosition: '',
        personalInfo: { name: '王五', email: 'wangwu@example.com', phone: '156****7890', location: '深圳' },
        jobIntent: { desiredPosition: '', desiredCity: '', salaryExpectation: '', workMode: 'fulltime' },
        education: [{ school: '某某大学', degree: '硕士', major: '软件工程', startDate: '2020-09', endDate: '2023-06' }],
        workExperience: [{ company: '某科技公司', position: '后端开发', startDate: '2023-07', endDate: '2026-06', description: '参与系统架构设计，编写核心模块代码', skills: ['Java', 'Python'] }],
        projects: [],
        skills: [
          { id: 's1', name: 'Java', level: 'advanced', category: '编程语言' },
          { id: 's2', name: 'Python', level: 'required', category: '编程语言' },
          { id: 's3', name: 'Spring Boot', level: 'required', category: '框架' },
        ],
        selfEvaluation: '',
        createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
      },
    })
  }),

  // Match
  http.post(`${BASE}/match`, async ({ request }) => {
    await delay(1200)
    const body = await request.json() as any
    const key = `${body.resumeId}_${body.positionId}`
    const result = mockMatchResults[key] || {
      id: `m-${Date.now()}`,
      resumeId: body.resumeId,
      positionId: body.positionId,
      positionName: mockPositions.find((p) => p.id === body.positionId)?.name || '未知岗位',
      resumeName: mockResumes.find((r) => r.id === body.resumeId)?.name || '未知简历',
      totalScore: Math.floor(Math.random() * 30) + 55, // Random 55-85
      dimensions: [
        { name: '技能匹配', score: 70, weight: 0.4, details: '' },
        { name: '经验匹配', score: 65, weight: 0.3, details: '' },
        { name: '学历匹配', score: 80, weight: 0.15, details: '' },
        { name: '综合素质', score: 60, weight: 0.15, details: '' },
      ],
      gapAnalysis: { missingSkills: [], weakSkills: [], matchSkills: [] },
      suggestions: [],
      matchDate: new Date().toISOString(),
    }
    return HttpResponse.json({ code: 200, message: 'ok', data: result })
  }),

  http.post(`${BASE}/match/batch`, async ({ request }) => {
    await delay(600)
    const body = await request.json() as { resumeId: string; positionIds: string[] }
    const results = body.positionIds.map((positionId) => {
      const key = `${body.resumeId}_${positionId}`
      return mockMatchResults[key] || {
        id: `m-${Date.now()}-${positionId}`,
        resumeId: body.resumeId,
        positionId,
        positionName: mockPositions.find((p) => p.id === positionId)?.name || '未知岗位',
        resumeName: mockResumes.find((r) => r.id === body.resumeId)?.name || '未知简历',
        totalScore: Math.floor(Math.random() * 30) + 55,
        dimensions: [
          { name: '技能匹配', score: 70, weight: 0.4, details: '' },
          { name: '经验匹配', score: 65, weight: 0.3, details: '' },
          { name: '学历匹配', score: 80, weight: 0.15, details: '' },
          { name: '综合素质', score: 60, weight: 0.15, details: '' },
        ],
        gapAnalysis: { missingSkills: [], weakSkills: [], matchSkills: [] },
        suggestions: [],
        matchDate: new Date().toISOString(),
      }
    })
    return HttpResponse.json({ code: 200, message: 'ok', data: results })
  }),

  http.get(`${BASE}/match/result/:resumeId/:positionId`, async () => {
    await delay(300)
    const result = mockMatchResults['r-1_ep-1']
    return HttpResponse.json({ code: 200, message: 'ok', data: result })
  }),

  http.get(`${BASE}/match/history`, () =>
    HttpResponse.json({ code: 200, message: 'ok', data: mockHistoryMatches })),

  // Tailor
  http.get(`${BASE}/tailor/suggestions/:resumeId/:positionId`, async () => {
    await delay(800)
    const suggestions = mockTailorSuggestions['r-1_ep-1'] || []
    return HttpResponse.json({ code: 200, message: 'ok', data: suggestions })
  }),

  http.post(`${BASE}/tailor/accept`, () =>
    HttpResponse.json({ code: 200, message: 'ok', data: null })),

  http.post(`${BASE}/tailor/apply-all`, async () => {
    await delay(500)
    return HttpResponse.json({ code: 200, message: 'ok', data: { newResumeId: `r-${Date.now()}` } })
  }),

  http.post(`${BASE}/tailor/save-as-new`, async () => {
    await delay(500)
    return HttpResponse.json({ code: 200, message: 'ok', data: { newResumeId: `r-${Date.now()}` } })
  }),

  http.post(`${BASE}/tailor/optimize-phrase`, async ({ request }) => {
    await delay(600)
    const body = await request.json() as any
    const suggestions = generateOptimizedPhrases(body.text, body.style)
    return HttpResponse.json({ code: 200, message: 'ok', data: { suggestions } })
  }),

  // Learning Paths
  http.get(`${BASE}/learning/paths`, async () => {
    await delay(300)
    return HttpResponse.json({ code: 200, message: 'ok', data: mockLearningPaths })
  }),

  http.post(`${BASE}/learning/paths`, async ({ request }) => {
    await delay(300)
    const body = await request.json() as any
    const newPath = { id: `lp-${Date.now()}`, steps: [], totalDuration: '', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), ...body }
    return HttpResponse.json({ code: 200, message: 'ok', data: newPath })
  }),

  http.put(`${BASE}/learning/paths/:id`, async ({ params, request }) => {
    const body = await request.json() as any
    return HttpResponse.json({ code: 200, message: 'ok', data: { ...body, id: params.id, updatedAt: new Date().toISOString() } })
  }),

  http.delete(`${BASE}/learning/paths/:id`, () =>
    HttpResponse.json({ code: 200, message: 'ok', data: null })),

  // AI 学习助手
  http.post(`${BASE}/learning/assistant/chat`, async ({ request }) => {
    await delay(1200)
    const body = await request.json() as any
    const msg = body.message || ''
    // 模拟 AI 回复
    let reply = ''
    if (msg.includes('Java') || msg.includes('java')) {
      reply = `## Java 开发学习建议\n\n要成为一名合格的 Java 开发工程师，建议按以下路径学习：\n\n1. **Java 基础**（2-3周）：掌握面向对象编程、集合框架、IO流\n2. **数据库**（2周）：MySQL 增删改查、索引优化、事务管理\n3. **主流框架**（3-4周）：Spring Boot、MyBatis、Spring Cloud 微服务\n4. **中间件**（2周）：Redis 缓存、Kafka/RabbitMQ 消息队列\n5. **项目实战**（3-4周）：搭建一个完整的电商/企业应用后台\n\n> 建议配合实际项目练习，只看不练效果很差。`
    } else if (msg.includes('Agent') || msg.includes('agent') || msg.includes('智能体')) {
      reply = `## 什么是 AI Agent（智能体）？\n\n**Agent** 是一种能够自主感知环境、做出决策并执行行动的 AI 系统。\n\n与传统程序的区别：\n- 传统程序：按固定规则执行\n- Agent：自主推理 + 调用工具 + 记忆上下文\n\n**核心组成**：\n1. **LLM 大脑**：负责任务理解和规划\n2. **工具调用**：调用 API、数据库、代码执行等\n3. **记忆系统**：短期记忆（上下文）+ 长期记忆（向量库）\n\n**主流框架**：LangChain、AutoGPT、CrewAI\n\n想深入学习 Agent 开发，可以从 LangChain 入手。`
    } else if (msg.includes('学习') || msg.includes('转行') || msg.includes('怎么学')) {
      reply = `## 个性化学习建议\n\n根据你的目标岗位和当前简历，建议优先补齐以下技能：\n\n1. **微服务架构** — 这是你当前最大的短板，建议先学 Spring Cloud\n2. **缓存技术** — Redis 是面试高频考点\n3. **容器化** — Docker + K8s 是现代开发的标配\n\n预估学习周期：6-8 周\n\n需要我生成详细的学习路径吗？`
    } else {
      reply = `感谢你的提问！关于「${msg.slice(0, 20)}」这个问题：\n\n根据知识图谱中的信息，这个问题涉及到的技能领域包括多个方面。建议你：\n\n1. 明确你的目标岗位方向\n2. 查看该岗位的技能要求\n3. 对照自己的技能差距，制定学习计划\n\n你可以问我更具体的问题，比如：\n- "如何学习 Spring Boot？"\n- "转行 Java 开发需要学什么？"\n- "推荐 Docker 学习资源"`
    }

    // 模拟关联概念
    const relatedConcepts = [
      { name: 'Java', nodeId: 'root-java', relation: '核心技术' },
      { name: 'Spring Boot', nodeId: 'kp-springboot', relation: '核心框架' },
      { name: '微服务架构', nodeId: 'mod-microservice', relation: '相关技能' },
    ]

    const suggestedResources = [
      { id: 'res-1', title: 'Spring Boot 实战课程', type: 'course', url: '', platform: '慕课网' },
      { id: 'res-2', title: 'Java 核心编程', type: 'book', url: '', platform: '京东' },
    ]

    const followUpQuestions = ['学习周期大概多久？', '有哪些推荐的学习资源？', '这个技术的前景如何？']

    return HttpResponse.json({
      code: 200, message: 'ok',
      data: { reply, relatedConcepts, suggestedResources, followUpQuestions },
    })
  }),

  http.post(`${BASE}/learning/assistant/generate-path`, async ({ request }) => {
    await delay(2000)
    const body = await request.json() as any
    const path = {
      id: `lp-ai-${Date.now()}`,
      name: `${body.positionId === 'np-1' ? 'AI智能体开发' : 'Java工程师'}学习路径（AI生成）`,
      positionId: body.positionId || 'ep-1',
      positionName: 'Java开发工程师',
      steps: [
        { id: 'step-1', order: 1, title: 'Java 核心基础', description: '掌握面向对象、集合、并发编程', duration: '2-3周', resources: [
          { id: 'r1', title: 'Java编程思想', type: 'book', url: '', platform: '京东' },
          { id: 'r2', title: 'Java入门到精通', type: 'video', url: '', platform: 'B站' },
        ], completed: false },
        { id: 'step-2', order: 2, title: 'Spring Boot 框架', description: '学习依赖注入、自动配置、Web MVC', duration: '2-3周', resources: [
          { id: 'r3', title: 'Spring Boot实战', type: 'course', url: '', platform: '慕课网' },
        ], completed: false },
        { id: 'step-3', order: 3, title: '数据库与中间件', description: 'MySQL优化、Redis缓存、消息队列', duration: '3-4周', resources: [
          { id: 'r4', title: '高性能MySQL', type: 'book', url: '', platform: '当当' },
          { id: 'r5', title: 'Redis实战', type: 'course', url: '', platform: 'Coursera' },
        ], completed: false },
        { id: 'step-4', order: 4, title: '微服务与分布式', description: 'Spring Cloud、Docker、K8s', duration: '3-4周', resources: [
          { id: 'r6', title: '微服务架构设计', type: 'video', url: '', platform: 'YouTube' },
        ], completed: false },
        { id: 'step-5', order: 5, title: '项目实战', description: '完成一个电商后台项目，整合所有技能', duration: '3-4周', resources: [
          { id: 'r7', title: '电商项目实战', type: 'project', url: '', platform: 'GitHub' },
        ], completed: false },
      ],
      totalDuration: '13-18周',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    return HttpResponse.json({ code: 200, message: 'ok', data: path })
  }),

  http.post(`${BASE}/learning/assistant/recommend-resources`, async ({ request }) => {
    await delay(800)
    const body = await request.json() as any
    const skills: Record<string, any[]> = {}
    for (const skill of (body.skill_names || ['Java'])) {
      skills[skill] = [
        { id: `r-${Date.now()}-1`, title: `${skill} 实战课程`, type: 'course', url: '', platform: '慕课网' },
        { id: `r-${Date.now()}-2`, title: `${skill} 权威指南`, type: 'book', url: '', platform: '京东' },
        { id: `r-${Date.now()}-3`, title: `${skill} 项目实战`, type: 'project', url: '', platform: 'GitHub' },
      ]
    }
    return HttpResponse.json({ code: 200, message: 'ok', data: { skills } })
  }),

  // Match auto-detect
  http.post(`${BASE}/match/auto-detect`, async ({ request }) => {
    await delay(800)
    const body = await request.json() as { resumeId: string }
    // 返回该简历对应所有已知匹配结果，未预计算的随机低分
    const allPositions = mockPositions.map((pos) => {
      const key = `${body.resumeId}_${pos.id}`
      return mockMatchResults[key] || {
        id: `m-auto-${Date.now()}-${pos.id}`,
        resumeId: body.resumeId,
        positionId: pos.id,
        positionName: pos.name,
        resumeName: mockResumes.find((r) => r.id === body.resumeId)?.name || '未知简历',
        totalScore: Math.floor(Math.random() * 40) + 45,
        dimensions: [
          { name: '技能匹配', score: 65, weight: 0.4, details: '' },
          { name: '经验匹配', score: 60, weight: 0.3, details: '' },
          { name: '学历匹配', score: 75, weight: 0.15, details: '' },
          { name: '综合素质', score: 55, weight: 0.15, details: '' },
        ],
        gapAnalysis: { missingSkills: [], weakSkills: [], matchSkills: [] },
        suggestions: [],
        matchDate: new Date().toISOString(),
      }
    })
    return HttpResponse.json({ code: 200, message: 'ok', data: allPositions })
  }),

  // Learning: generate path from skill gaps
  http.post(`${BASE}/learning/generate-from-gaps`, async ({ request }) => {
    await delay(1500)
    const body = await request.json() as { resumeId: string; positionId: string }
    const position = mockPositions.find((p) => p.id === body.positionId)
    const gapPath = {
      id: `lp-gap-${Date.now()}`,
      name: `${position?.name || '目标岗位'} 技能补齐路径`,
      positionId: body.positionId,
      positionName: position?.name || '',
      steps: (position?.requiredSkills || []).map((skill, idx) => ({
        id: `gap-step-${idx + 1}`,
        order: idx + 1,
        title: `学习 ${skill.name}`,
        description: `掌握 ${skill.name}（${skill.category}）的核心知识和实践技能`,
        duration: idx < 2 ? '1-2周' : '2-3周',
        resources: [
          { id: `gr-${idx}-1`, title: `${skill.name} 入门实战`, type: 'course' as const, url: '', platform: '慕课网' },
          { id: `gr-${idx}-2`, title: `${skill.name} 官方文档`, type: 'article' as const, url: '', platform: '官网' },
        ],
        completed: false,
      })),
      totalDuration: `${(position?.requiredSkills?.length || 3) * 2}周`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    return HttpResponse.json({ code: 200, message: 'ok', data: gapPath })
  }),

  // Favorites
  http.post(`${BASE}/favorites/position`, async () => {
    await delay(200)
    return HttpResponse.json({ code: 200, message: 'ok', data: null })
  }),

  http.get(`${BASE}/favorites/learning-paths`, async () => {
    await delay(200)
    return HttpResponse.json({ code: 200, message: 'ok', data: mockLearningPaths.map((p) => p.id) })
  }),

  http.post(`${BASE}/favorites/learning-path`, async () => {
    await delay(200)
    return HttpResponse.json({ code: 200, message: 'ok', data: null })
  }),

  http.get(`${BASE}/favorites/notes`, async () => {
    await delay(200)
    return HttpResponse.json({ code: 200, message: 'ok', data: mockNotes })
  }),

  http.post(`${BASE}/favorites/notes`, async ({ request }) => {
    await delay(300)
    const body = await request.json() as any
    const note = {
      id: `n-${Date.now()}`,
      ...body,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    mockNotes.unshift(note)
    return HttpResponse.json({ code: 200, message: 'ok', data: note })
  }),

  http.put(`${BASE}/favorites/notes/:id`, async ({ params, request }) => {
    await delay(300)
    const body = await request.json() as any
    const idx = mockNotes.findIndex((n) => n.id === params.id)
    if (idx >= 0) {
      mockNotes[idx] = { ...mockNotes[idx], ...body, updatedAt: new Date().toISOString() }
      return HttpResponse.json({ code: 200, message: 'ok', data: mockNotes[idx] })
    }
    return HttpResponse.json({ code: 404, message: 'not found', data: null }, { status: 404 })
  }),

  http.delete(`${BASE}/favorites/notes/:id`, async ({ params }) => {
    await delay(200)
    const idx = mockNotes.findIndex((n) => n.id === params.id)
    if (idx >= 0) mockNotes.splice(idx, 1)
    return HttpResponse.json({ code: 200, message: 'ok', data: null })
  }),

  // Career
  http.get(`${BASE}/career/plan`, async () => {
    await delay(200)
    const plan = mockCareerPlans[0] || null
    return HttpResponse.json({ code: 200, message: 'ok', data: plan })
  }),

  http.post(`${BASE}/career/plan`, async ({ request }) => {
    await delay(300)
    const body = await request.json() as any
    const plan = {
      id: `cp-${Date.now()}`,
      ...body,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    if (mockCareerPlans.length > 0) {
      mockCareerPlans[0] = plan
    } else {
      mockCareerPlans.push(plan)
    }
    return HttpResponse.json({ code: 200, message: 'ok', data: plan })
  }),

  http.post(`${BASE}/career/assess`, async ({ request }) => {
    await delay(1500)
    const body = await request.json() as { resumeId: string; targetPositionId: string; budget: { weeklyHours: number; totalWeeks: number } }
    const key = `${body.resumeId}_${body.targetPositionId}`
    const assessment =
      mockCareerAssessments[key] || {
        currentMatchDegree: Math.floor(Math.random() * 30) + 45,
        transferableSkills: [],
        missingSkills: mockPositions.find((p) => p.id === body.targetPositionId)?.requiredSkills || [],
        recommendationReasons: ['该岗位与你的技能有一定关联', '行业发展前景良好'],
        advantages: ['具备编程基础能力'],
        risks: ['需要系统学习新领域知识', '学习成本较高'],
        learningTimeline: `${Math.ceil((mockPositions.find((p) => p.id === body.targetPositionId)?.requiredSkills.length || 4) / 2)}-${mockPositions.find((p) => p.id === body.targetPositionId)?.requiredSkills.length || 4}个月`,
        feasibilityRating: 'medium' as const,
      }
    return HttpResponse.json({ code: 200, message: 'ok', data: assessment })
  }),

  http.post(`${BASE}/learning/assistant/quiz`, async () => {
    await delay(1000)
    return HttpResponse.json({
      code: 200, message: 'ok',
      data: {
        questions: [
          { id: 'q-1', type: 'choice', question: '以下哪个不是 Java 的垃圾回收器？', options: ['G1', 'CMS', 'ZGC', 'Nginx'], correctAnswer: 3, explanation: 'Nginx 是 Web 服务器，不是 JVM 垃圾回收器' },
          { id: 'q-2', type: 'choice', question: 'Spring Boot 的自动配置基于什么原理？', options: ['反射', '条件注解 @Conditional', 'AOP', '动态代理'], correctAnswer: 1, explanation: 'Spring Boot 通过 @Conditional 系列注解实现条件化自动配置' },
          { id: 'q-3', type: 'choice', question: 'Redis 中用于实现分布式锁的命令是？', options: ['SET', 'GET', 'SETNX', 'INCR'], correctAnswer: 2, explanation: 'SETNX（SET if Not eXists）可以实现分布式锁' },
          { id: 'q-4', type: 'choice', question: 'Docker 中构建镜像的文件是？', options: ['package.json', 'Dockerfile', 'docker-compose.yml', 'Makefile'], correctAnswer: 1, explanation: 'Dockerfile 是 Docker 镜像的构建描述文件' },
          { id: 'q-5', type: 'choice', question: 'Kafka 中消息的基本单位是？', options: ['Topic', 'Partition', 'Message', 'Broker'], correctAnswer: 2, explanation: 'Message（消息）是 Kafka 中最基本的数据单元' },
        ],
      },
    })
  }),
]
