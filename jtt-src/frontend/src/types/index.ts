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
  skillChanges?: SkillChange[]
  // 爬虫数据额外字段
  company?: string
  city?: string
  experience?: string
  education?: string
  // 详情页额外字段
  originalTitle?: string
  jdText?: string
  responsibilitiesText?: string
  requirementsText?: string
  postedAt?: string
  stack?: string
  stdJobName?: string
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

// ========== 新图谱（Neo4j fyz 数据模型） ==========
export type Neo4jNodeType = 'Job' | 'SkillArea' | 'TechStack' | 'TechPoint' | 'KnowledgePoint' | 'SourceDocument' | 'GraphSnapshot'

export interface Neo4jGraphNode {
  id: string
  name: string
  type: Neo4jNodeType
  stack: string | null
  level: string | null
  description: string
  importance: number | null
  frequency: number | null
  properties: Record<string, unknown>
}

export interface Neo4jGraphEdge {
  id: string
  source: string
  target: string
  relation: string
  properties: Record<string, unknown>
}

export interface Neo4jGraphSubgraph {
  nodes: Neo4jGraphNode[]
  edges: Neo4jGraphEdge[]
  node_count: number
  edge_count: number
  snapshot_version: string | null
  truncated: boolean
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
  sourceFile?: string
  sourceFilePath?: string
  rawText?: string
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
  verified: boolean // 是否通过知识图谱校验
  warning?: string | null // 校验警告信息
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
  quizPassed: boolean
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
// ========== AI 助手相关 ==========
export interface ChatAction {
  label: string
  to: string
  icon?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  images?: string[]
  timestamp: number
  relatedConcepts?: { name: string; nodeId: string; relation: string }[]
  suggestedResources?: LearningResource[]
  followUpQuestions?: string[]
  actions?: ChatAction[]
}

export interface PageContext {
  name: string
  path: string
  params?: Record<string, any>
  positionId?: string
  positionName?: string
  resumeId?: string
  /** 当前页面的简历数据（完整） */
  resumeData?: {
    name: string
    targetPosition: string
    skills: { name: string; level: string; category: string }[]
    workExperience: { company: string; position: string; description: string; skills: string[] }[]
    education: { school: string; degree: string; major: string }[]
  }
  /** 当前页面的匹配结果数据 */
  matchData?: {
    totalScore: number
    positionName: string
    resumeName: string
    dimensions: { name: string; score: number; weight: number }[]
    missingSkills: string[]
    weakSkills: string[]
    matchSkills: string[]
  }
}

export interface AssistantChatRequest {
  message: string
  images?: string[]
  pageContext?: PageContext
  history?: { role: 'user' | 'assistant'; content: string }[]
}

export interface AssistantChatResponse {
  reply: string
  relatedConcepts?: { name: string; nodeId: string; relation: string }[]
  suggestedResources?: LearningResource[]
  followUpQuestions?: string[]
  actions?: ChatAction[]
}

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
