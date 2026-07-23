/**
 * 前后端数据格式转换 —— 前端 camelCase ↔ 后端 snake_case
 */
import type { ResumeData, JobPosition, LearningPath, ImprovementSuggestion, MatchResult } from '@/types'

// ========== 简历转换 ==========

/** 工作经历内部字段 camelCase → snake_case */
function expToApi(e: any) {
  return {
    company: e.company,
    position: e.position,
    start_date: e.startDate ?? e.start_date ?? '',
    end_date: e.endDate ?? e.end_date ?? '',
    description: e.description,
    skills: e.skills || [],
  }
}

/** 工作经历内部字段 snake_case → camelCase */
function expFromApi(e: any) {
  return {
    company: e.company,
    position: e.position,
    startDate: e.start_date ?? e.startDate ?? '',
    endDate: e.end_date ?? e.endDate ?? '',
    description: e.description,
    skills: e.skills || [],
  }
}

/** 教育经历内部字段 camelCase → snake_case */
function eduToApi(e: any) {
  return {
    school: e.school,
    degree: e.degree,
    major: e.major,
    start_date: e.startDate ?? e.start_date ?? '',
    end_date: e.endDate ?? e.end_date ?? '',
  }
}

/** 教育经历内部字段 snake_case → camelCase */
function eduFromApi(e: any) {
  return {
    school: e.school,
    degree: e.degree,
    major: e.major,
    startDate: e.start_date ?? e.startDate ?? '',
    endDate: e.end_date ?? e.endDate ?? '',
  }
}

/** 后端 API 返回的简历格式（snake_case） */
interface ResumeApiData {
  id: number
  name: string
  target_position?: string | null
  personal_info: { name: string; email: string; phone: string; location: string }
  job_intent: { desired_position: string; desired_city: string; salary_expectation: string; work_mode: string }
  education: any[]
  work_experience: any[]
  projects: any[]
  skills: any[]
  self_evaluation: string
  source_file?: string | null
  source_file_path?: string | null
  raw_text?: string | null
  created_at?: string | null
  updated_at?: string | null
}

// ========== 岗位转换 ==========

export function positionFromApi(data: any): JobPosition {
  const result: any = {
    id: String(data.id),
    name: data.name || '',
    category: data.category || 'existing',
    aliases: data.aliases || [],
    summary: data.summary || '',
    responsibilities: data.responsibilities || [],
    requiredSkills: (data.required_skills || []).map((s: any) => ({
      id: String(s.id || s.name),
      name: s.name || '',
      level: s.level || 'required',
      category: s.category || '',
    })),
    preferredSkills: (data.preferred_skills || []).map((s: any) => ({
      id: String(s.id || s.name),
      name: s.name || '',
      level: s.level || 'preferred',
      category: s.category || '',
    })),
    industryScenarios: data.industry_scenarios || [],
    techStack: data.tech_stack || [],
    careerLevel: data.career_level || 'mid',
    salaryRange: data.salary_range || '',
    skillChanges: (data.skill_changes || []).map((sc: any) => ({
      id: String(sc.id || sc.skill_name),
      skillName: sc.skill_name || '',
      type: sc.change_type || 'modified',
      date: sc.date || '',
      description: sc.description || '',
      source: sc.source || '',
    })),
    createdAt: data.created_at || '',
    updatedAt: data.updated_at || '',
  }
  // 爬虫数据额外字段
  if (data.company) result.company = data.company
  if (data.city) result.city = data.city
  if (data.experience) result.experience = data.experience
  if (data.education) result.education = data.education
  // 详情页额外字段
  if (data.original_title) result.originalTitle = data.original_title
  if (data.jd_text) result.jdText = data.jd_text
  if (data.responsibilities_text) result.responsibilitiesText = data.responsibilities_text
  if (data.requirements_text) result.requirementsText = data.requirements_text
  if (data.posted_at) result.postedAt = data.posted_at
  if (data.stack) result.stack = data.stack
  if (data.std_job_name) result.stdJobName = data.std_job_name
  return result as JobPosition
}

// ========== 学习路径转换 ==========

export function pathFromApi(data: any): LearningPath {
  return {
    id: String(data.id),
    name: data.name || '',
    positionId: String(data.position_id || ''),
    positionName: data.position_name || '',
    steps: (data.steps || []).map((s: any) => ({
      id: String(s.id || ''),
      order: s.order || 0,
      title: s.title || '',
      description: s.description || '',
      duration: s.duration || '',
      resources: (s.resources || []).map((r: any) => ({
        id: String(r.id || r.title),
        title: r.title || '',
        type: r.type || 'article',
        url: r.url || '',
        platform: r.platform || '',
      })),
      completed: s.completed || false,
    })),
    totalDuration: data.total_duration || '',
    createdAt: data.created_at || '',
    updatedAt: data.updated_at || '',
  }
}

export function resumeFromApi(data: ResumeApiData): ResumeData {
  return {
    id: String(data.id),
    name: data.name,
    targetPosition: data.target_position ?? undefined,
    personalInfo: {
      name: data.personal_info?.name || '',
      email: data.personal_info?.email || '',
      phone: data.personal_info?.phone || '',
      location: data.personal_info?.location || '',
    },
    jobIntent: {
      desiredPosition: data.job_intent?.desired_position || '',
      desiredCity: data.job_intent?.desired_city || '',
      salaryExpectation: data.job_intent?.salary_expectation || '',
      workMode: (data.job_intent?.work_mode as any) || 'fulltime',
    },
    education: (data.education || []).map(eduFromApi),
    workExperience: (data.work_experience || []).map(expFromApi),
    projects: data.projects || [],
    skills: data.skills || [],
    selfEvaluation: data.self_evaluation || '',
    sourceFile: data.source_file ?? undefined,
    sourceFilePath: data.source_file_path ?? undefined,
    rawText: data.raw_text ?? undefined,
    createdAt: data.created_at ?? '',
    updatedAt: data.updated_at ?? '',
  }
}

export function resumeToApi(data: Partial<ResumeData>): Record<string, any> {
  const result: Record<string, any> = {}
  if (data.name !== undefined) result.name = data.name
  if (data.targetPosition !== undefined) result.target_position = data.targetPosition
  if (data.selfEvaluation !== undefined) result.self_evaluation = data.selfEvaluation
  if (data.personalInfo) {
    result.personal_info = {
      name: data.personalInfo.name,
      email: data.personalInfo.email,
      phone: data.personalInfo.phone,
      location: data.personalInfo.location,
    }
  }
  if (data.jobIntent) {
    result.job_intent = {
      desired_position: data.jobIntent.desiredPosition,
      desired_city: data.jobIntent.desiredCity,
      salary_expectation: data.jobIntent.salaryExpectation,
      work_mode: data.jobIntent.workMode,
    }
  }
  if (data.education !== undefined) result.education = data.education.map(eduToApi)
  if (data.workExperience !== undefined) result.work_experience = data.workExperience.map(expToApi)
  if (data.projects !== undefined) result.projects = data.projects
  if (data.skills !== undefined) result.skills = data.skills
  return result
}

// ========== 匹配结果转换 ==========

export function suggestionFromApi(data: any): ImprovementSuggestion {
  return {
    id: String(data.id || ''),
    section: data.section || '',
    field: data.field || '',
    original: data.original || '',
    suggested: data.suggested || '',
    reason: data.reason || '',
    changeType: data.change_type || 'small',
    accepted: data.accepted || false,
    verified: data.verified !== false,
    warning: data.warning || null,
  }
}

export function matchResultFromApi(data: any): MatchResult {
  const toSkill = (s: any) => ({
    id: String(s.name || s.id || ''),
    name: s.name || '',
    level: s.level || 'required',
    category: s.category || '未知',
  })
  return {
    id: String(data.id || ''),
    resumeId: String(data.resume_id || ''),
    positionId: String(data.position_id || ''),
    positionName: data.position_name || '',
    resumeName: data.resume_name || '',
    totalScore: data.total_score || 0,
    dimensions: (data.dimensions || []).map((d: any) => ({
      name: d.name || '',
      score: d.score || 0,
      weight: d.weight || 0,
      details: d.details || '',
    })),
    gapAnalysis: {
      missingSkills: (data.gap_analysis?.missing_skills || []).map(toSkill),
      weakSkills: (data.gap_analysis?.weak_skills || []).map(toSkill),
      matchSkills: (data.gap_analysis?.match_skills || []).map(toSkill),
    },
    suggestions: (data.suggestions || []).map(suggestionFromApi),
    matchDate: data.match_date || '',
  }
}
