import { http, HttpResponse, delay } from 'msw'
import { mockPositions } from './data/positions'
import { mockGraphNodes, mockGraphEdges } from './data/skills'
import { mockResumes } from './data/resume'
import { mockMatchResults, mockHistoryMatches } from './data/match'
import { mockTailorSuggestions, generateOptimizedPhrases } from './data/tailor'
import { mockLearningPaths } from './data/learning'

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

  http.get(`${BASE}/positions/graph`, () =>
    HttpResponse.json({ code: 200, message: 'ok', data: { nodes: mockGraphNodes, edges: mockGraphEdges } })),

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
  http.get(`${BASE}/learning-paths`, async () => {
    await delay(300)
    return HttpResponse.json({ code: 200, message: 'ok', data: mockLearningPaths })
  }),
]
