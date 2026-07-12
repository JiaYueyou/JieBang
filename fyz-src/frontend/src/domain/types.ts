export type EntityId = number;
export type FavoriteTargetType = "job" | "resume";
export type HistoryType = "job" | "resume" | "search" | "graph" | "match";
export type JobStatus = "draft" | "open" | "paused" | "closed";
export type GraphType = "Job" | "SkillArea" | "TechStack" | "TechPoint" | "KnowledgePoint" | "SourceDocument" | "GraphSnapshot";

export interface JobSummary {
  id: EntityId;
  title: string;
  department: string;
  headcount: number;
  status: JobStatus;
  created_at: string;
  level: string;
  salary_range: string;
  responsibilities: string[];
  requirements: string[];
  bonus_skills: string[];
  location?: string;
  company?: string;
  experience?: string;
  education?: string;
  skills?: string[];
  jd_text?: string;
  match?: number;
  urgent?: boolean;
}

export type JDGenerationMode = "requirements" | "profile";

export interface GenerateJDRequest {
  mode: JDGenerationMode;
  title: string;
  level?: string;
  department?: string;
  skills_input: string;
}

export interface GeneratedJDDraft {
  title: string;
  standardized_title?: string | null;
  level: string;
  department: string;
  responsibilities: string[];
  requirements: string[];
  skills: string[];
  bonus_skills: string[];
  jd_text: string;
  assumptions: string[];
  warnings: string[];
  generation_mode: "llm" | "template";
}

export interface JobCreatePayload {
  title: string;
  standardized_title?: string | null;
  level: string;
  department: string;
  headcount: number;
  responsibilities: string[];
  requirements: string[];
  skills: string[];
  bonus_skills: string[];
  jd_text: string;
  status: JobStatus;
}

export type JobDetail = JobSummary;

export interface EmergingJob {
  id: EntityId;
  name: string;
  core_skills: string[];
  description: string;
  confidence: number;
  source_count?: number;
  first_seen_at?: string;
  decision?: "confirmed" | "ignored" | "planned" | null;
}

export interface CapabilityChange {
  id: EntityId;
  job_id: EntityId;
  job: string;
  period: string;
  added: string[];
  modified: string[];
  removed: string[];
}

export interface TalentSummary {
  id: EntityId;
  resume_id: EntityId;
  match_id: EntityId;
  name: string;
  position: string;
  score: number;
  isNew: boolean;
  experience: string;
  education: string;
  department: string;
  matched: string[];
  missing: string[];
  targetJobs: string[];
  targetJobIds: EntityId[];
  resumeFile?: string;
  uploadDate?: string;
  urgent?: boolean;
  company?: string;
  location?: string;
  salary?: string;
}

export type TalentDetail = TalentSummary;

export interface MatchReport {
  id: EntityId;
  resume_id: EntityId;
  job_id: EntityId;
  score: number;
  matched: string[];
  missing: string[];
}

export interface DashboardOverview {
  heroCards: Array<{ value: string; label: string; change: string; up: boolean; color: string; action: string; link: string }>;
  kanban: Array<{ job_id: EntityId; title: string; total: number; stages: Array<{ name: string; count: number }> }>;
  highMatches: TalentSummary[];
  hotJobs: Array<{ job_id: EntityId; title: string; demand: number; city: string; trend: number; spark: number[] }>;
  emergingSkills: Array<{ id: EntityId; name: string; combo: string; growth: number; confidence: number }>;
}

export interface LearningStep {
  skill: string;
  time: string;
  difficulty: "easy" | "medium" | "hard";
  resources: string[];
}

export interface CareerRecommendation {
  rank: number;
  job_id: EntityId;
  job: string;
  recommendScore: number;
  currentMatch: number;
  afterMatch: number;
  existing: string[];
  gaps?: string[];
  learningPlan: LearningStep[];
  suggestedProject: string;
  totalTime: string;
  internal: boolean;
  explanation?: string;
}

export interface CareerAnalysisResult {
  recommendations: CareerRecommendation[];
  agentRunId: string;
  agentStatus: "succeeded" | "degraded";
  warnings: string[];
}

export interface ResumeUploadPayload {
  file: File;
  name?: string;
  currentPosition?: string;
  experience?: string;
  education?: string;
  department?: string;
}

export interface MatchExplanation {
  match_id: EntityId;
  score: number;
  summary: string;
  strengths: Array<{ title: string; explanation: string; evidence_ids: number[] }>;
  gaps: Array<{ title: string; explanation: string; evidence_ids: number[] }>;
  risks: string[];
  interview_suggestions: string[];
  generation_mode: "llm" | "template";
  warnings: string[];
  agent_run_id: string;
}

export interface GraphNode {
  id: string;
  name: string;
  type: GraphType;
  stack?: "ai" | "backend" | "data" | "devops" | null;
  level?: "junior" | "middle" | "senior" | null;
  x: number;
  y: number;
  description: string;
  importance?: number;
  frequency?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: "REQUIRES_AREA" | "CONTAINS" | "REFINES_TO" | "HAS_KNOWLEDGE" | "RELATED_TO" | "SAME_AS";
}

export interface GraphSubgraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count?: number;
  edge_count?: number;
  snapshot_version?: string | null;
  truncated?: boolean;
}

export interface GraphQuery {
  stack?: "ai" | "backend" | "data" | "devops";
  level?: "junior" | "middle" | "senior";
  nodeType?: GraphType;
  keyword?: string;
  limit?: number;
}

export interface TrendSeries {
  name: string;
  values: number[];
}

export interface HeatmapPoint {
  x: number;
  y: number;
  value: number;
}

export interface AnalysisDataQuality {
  total_records: number;
  valid_time_records: number;
  fallback_time_records: number;
  valid_salary_records: number;
  verified_skill_facts: number;
  observed_months: number;
  coverage_start: string | null;
  coverage_end: string | null;
  insufficient_data: boolean;
  notes: string[];
}

export interface TrendQuery {
  months: number;
  keyword?: string;
  city?: string;
}

export interface TrendOverview {
  stats: { totalJobs: string; newSkills: number; avgSalary: string; activeCities: number };
  months: string[];
  jobDemand: TrendSeries[];
  salary: TrendSeries[];
  heatmapSkills: string[];
  heatmap: HeatmapPoint[];
  locations: Array<{ city: string; value: number }>;
  emergingSkills: Array<{ id: EntityId; skill: string; category: string; growth: number; stage: string; sparkline: number[] }>;
  dataQuality: AnalysisDataQuality;
}

export interface FavoriteRecord {
  id: EntityId;
  target_type: FavoriteTargetType;
  target_id: EntityId;
  title: string;
  subtitle: string;
  company: string;
  location: string;
  salary: string;
  experience: string;
  education: string;
  skills: string[];
  match: number;
  savedAt: string;
  savedOrder: number;
  note: string;
  urgent?: boolean;
}

export interface HistoryRecord {
  id: EntityId;
  type: HistoryType;
  targetId?: number | string;
  title: string;
  description: string;
  source: string;
  dateKey: "today" | "yesterday" | "week" | "month";
  date: string;
  time: string;
  tags: string[];
  url: string;
  badge?: string;
}

export interface HistoryInsights {
  focusStats: Array<{ label: string; percent: number; count: number }>;
  frequentRecords: Array<{ history_id: EntityId; count: number }>;
}

export interface DataSource {
  id: EntityId;
  name: string;
  short: string;
  endpoint: string;
  tone: string;
  enabled: boolean;
  running: boolean;
  today: string;
  success: number;
  duration: string;
  progress: number;
  schedule: string;
  nextRun: string;
}

export interface SystemUser {
  id: EntityId;
  name: string;
  email: string;
  department: string;
  role: string;
  roleTone: string;
  status: "active" | "disabled";
  lastLogin: string;
}

export interface AdminOverview {
  metrics: any[];
  services: any[];
  resources: any[];
  recentTasks: any[];
  systemEvents: any[];
  crawlers: DataSource[];
  qualities: any[];
  crawlerPolicy: { concurrency: number; retries: number; interval: number; deduplicate: boolean };
  performanceCards: any[];
  endpoints: any[];
  alertRules: any[];
  logs: any[];
  users: SystemUser[];
  roles: any[];
  settings: Record<string, any>;
  integrations: any[];
}

export interface MockDatabase {
  version: 1;
  jobs: JobSummary[];
  emergingJobs: EmergingJob[];
  capabilityChanges: CapabilityChange[];
  talents: TalentSummary[];
  matches: MatchReport[];
  favorites: FavoriteRecord[];
  history: HistoryRecord[];
  graph: GraphSubgraph;
  admin: AdminOverview;
}
