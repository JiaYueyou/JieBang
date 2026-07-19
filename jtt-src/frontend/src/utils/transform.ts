/**
 * 前后端数据格式转换 —— 前端 camelCase ↔ 后端 snake_case
 */
import type { ResumeData, JobPosition, LearningPath, ImprovementSuggestion, MatchResult } from '@/types'

// ========== 简历转换 ==========

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
  created_at?: string | null
  updated_at?: string | null
}

// ========== 岗位转换 ==========

export function positionFromApi(data: any): JobPosition {
  return {
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
    education: data.education || [],
    workExperience: data.work_experience || [],
    projects: data.projects || [],
    skills: data.skills || [],
    selfEvaluation: data.self_evaluation || '',
    sourceFile: data.source_file ?? undefined,
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
  if (data.education !== undefined) result.education = data.education
  if (data.workExperience !== undefined) result.work_experience = data.workExperience
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
