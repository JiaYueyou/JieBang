// ========== 岗位相关 ==========
export type PositionCategory = 'new' | 'existing'

export interface Skill {
  id: string
  name: string
  level: 'required' | 'preferred' | 'advanced'
  category: string // 技术栈分类：前端/后端/AI/大数据等
}

export interface SkillChange {
  id: string
  skillName: string
  type: 'added' | 'removed' | 'modified'
  date: string
  description: string
  source: string
}

export interface JobPosition {
  id: string
  name: string
  category: PositionCategory
  aliases: string[]
  summary: string
  responsibilities: string[]
  requiredSkills: Skill[]
  preferredSkills: Skill[]
  industryScenarios: string[]
  techStack: string[]
  careerLevel: 'junior' | 'mid' | 'senior'
  salaryRange: string
  skillChanges?: SkillChange[] // 仅既有岗位
  createdAt: string
  updatedAt: string
}

// ========== 图谱相关（五级结构） ==========
export type GraphNodeType = 'root' | 'position' | 'domain_branch' | 'skillset_branch' | 'module' | 'knowledge'

export type GraphRelation = 'derives' | 'applies_to' | 'composes' | 'contains' | 'includes' | 'cross_ref'

export interface GraphNode {
  id: string
  label: string
  type: GraphNodeType
  layer: 1 | 2 | 3 | 4 | 5
  rootId?: string // 所属根技术 ID，用于快速过滤
}

export interface GraphEdge {
  source: string
  target: string
  relation: GraphRelation
  weight: number
}

export interface KnowledgeGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// ========== 简历相关 ==========
export interface Education {
  school: string
  degree: string
  major: string
  startDate: string
  endDate: string
}

export interface WorkExperience {
  company: string
  position: string
  startDate: string
  endDate: string
  description: string
  skills: string[]
}

export interface Project {
  name: string
  role: string
  description: string
  technologies: string[]
  highlights: string[]
}

export interface ResumeData {
  id: string
  name: string // 简历别名，用户自定义
  targetPosition?: string // 目标岗位方向
  personalInfo: {
    name: string
    email: string
    phone: string
    location: string
    avatar?: string
  }
  jobIntent: {
    desiredPosition: string
    desiredCity: string
    salaryExpectation: string
    workMode: 'fulltime' | 'intern' | 'remote'
  }
  education: Education[]
  workExperience: WorkExperience[]
  projects: Project[]
  skills: Skill[]
  selfEvaluation: string
  sourceFile?: string // 上传解析来源文件名
  createdAt: string
  updatedAt: string
}

// ========== 匹配相关 ==========
export interface MatchDimension {
  name: string // 维度名称：技能匹配、经验匹配、学历匹配、综合素质
  score: number // 0-100
  weight: number
  details: string
}

export interface ImprovementSuggestion {
  id: string
  section: string // 简历模块：skills/workExperience/education/selfEvaluation
  field: string
  original: string
  suggested: string
  reason: string
  changeType: 'small' | 'large' // 小改/大改
  accepted: boolean
}

export interface MatchResult {
  id: string
  resumeId: string
  positionId: string
  positionName: string
  resumeName: string
  totalScore: number // 0-100
  dimensions: MatchDimension[]
  gapAnalysis: {
    missingSkills: Skill[]
    weakSkills: Skill[]
    matchSkills: Skill[]
  }
  suggestions: ImprovementSuggestion[]
  matchDate: string
}

// ========== 学习路径相关 ==========
export interface LearningStep {
  id: string
  order: number
  title: string
  description: string
  duration: string // 如 "1-2周"
  resources: LearningResource[]
  completed: boolean
}

export interface LearningResource {
  id: string
  title: string
  type: 'course' | 'book' | 'article' | 'project' | 'video'
  url: string
  platform: string
}

export interface LearningPath {
  id: string
  name: string // 用户可编辑名称
  positionId: string
  positionName: string
  steps: LearningStep[]
  totalDuration: string
  createdAt: string
  updatedAt: string
}

// ========== 用户相关 ==========
export interface UserProfile {
  id: string
  username: string
  email: string
  avatar?: string
  phone?: string
  nickname?: string
  city?: string
  education?: string
  resumeCount: number
  matchHistoryCount: number
}

// ========== 笔记 / 收藏相关 ==========
export interface Note {
  id: string
  title: string
  content: string
  type: 'note' | 'link' | 'resource'
  url?: string
  tags: string[]
  createdAt: string
  updatedAt: string
}

export type FavoriteType = 'position' | 'learning_path' | 'note'

export interface FavoriteItem {
  id: string
  itemType: FavoriteType
  itemId: string
  title: string
  createdAt: string
}

// ========== 职业发展相关 ==========
export interface CareerPreferences {
  targetIndustry: string
  targetRoleType: string
  preferredCity: string
  salaryExpectation: string
}

export interface LearningBudget {
  weeklyHours: number
  totalWeeks: number
}

export type FeasibilityRating = 'high' | 'medium' | 'low' | 'very_low'

export interface CareerTransitionAssessment {
  currentMatchDegree: number
  transferableSkills: Skill[]
  missingSkills: Skill[]
  recommendationReasons: string[]
  advantages: string[]
  risks: string[]
  learningTimeline: string
  feasibilityRating: FeasibilityRating
}

export interface CareerPlan {
  id: string
  resumeId: string
  preferences: CareerPreferences
  budget: LearningBudget
  targetPositionId: string
  targetPositionName: string
  assessment: CareerTransitionAssessment | null
  createdAt: string
  updatedAt: string
}

// ========== API 通用响应 ==========
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PaginatedData<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}
