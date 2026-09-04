/**
 * 管理决策端 Mock API —— 纯前端实现，签名贴近真实接口，后续可无缝替换为 HTTP 调用。
 * 图谱相关 mock 见 api/graph.ts。
 */
import * as M from '@/mock/data'

const delay = (ms = 240) => new Promise((r) => setTimeout(r, ms))

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v))
}

/* ── 认证（mock：admin / admin123） ── */
export interface AdminProfile {
  id: number
  username: string
  nickname: string
  role: string
  department: string
}

export async function mockLogin(username: string, password: string): Promise<{ token: string; user: AdminProfile }> {
  await delay(420)
  if (username !== 'admin' || password !== 'admin123') {
    throw new Error('账号或密码不正确（演示账号 admin / admin123）')
  }
  return {
    token: 'mock-admin-token',
    user: { id: 1, username: 'admin', nickname: '管理员', role: '超级管理员', department: '数据智能部' },
  }
}

/* ── 工作台 ── */
export async function apiOverview() {
  await delay()
  return {
    kpis: clone(M.kpis),
    trendDays: [...M.trendDays],
    trendJobs: [...M.trendJobs],
    trendMatches: [...M.trendMatches],
    todos: clone(M.todos),
    activities: clone(M.activities),
  }
}

/* ── 职位管理 ── */
export async function apiListAdminJobs(params: { keyword?: string; category?: 'all' | 'emerging' | 'existing' } = {}) {
  await delay()
  let list = clone(M.adminJobs)
  if (params.category && params.category !== 'all') {
    list = list.filter((j) => j.category === params.category)
  }
  if (params.keyword?.trim()) {
    const kw = params.keyword.trim().toLowerCase()
    list = list.filter((j) => j.name.toLowerCase().includes(kw) || j.summary.toLowerCase().includes(kw))
  }
  return list
}

export async function apiAdminJobDetail(id: string) {
  await delay(200)
  const job = M.adminJobs.find((j) => j.id === id)
  if (!job) throw new Error('职位不存在')
  return clone(job)
}

export async function apiToggleJobStatus(id: string) {
  await delay(360)
  const job = M.adminJobs.find((j) => j.id === id)
  if (!job) throw new Error('职位不存在')
  job.status = job.status === '已下线' ? '在招' : '已下线'
  return { id, status: job.status }
}

/* ── 趋势洞察 ── */
export async function apiTrendInsights() {
  await delay()
  return {
    skillTrends: clone(M.skillTrends),
    cityHeat: clone(M.cityHeat),
    donut: clone(M.categoryDonut),
  }
}

/* ── 管理中心 ── */
export async function apiAdminCenter() {
  await delay()
  return {
    reviewStats: clone(M.reviewStats),
    importSources: clone(M.importSources),
    systemStatus: clone(M.systemStatus),
    auditLogs: clone(M.auditLogs),
    users: clone(M.adminUsers),
  }
}
