export type EntityId = number;
export interface PageResult<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}
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

export interface ObservedJobSummary {
  id: number;
  title: string;
  standardized_title: string | null;
  company: string | null;
  city: string | null;
  salary_text: string | null;
  experience_text: string | null;
  education_text: string | null;
  source: string;
  source_url: string | null;
  posted_at: string | null;
  crawled_at: string | null;
  dedup_status: string;
  verified_skill_count: number;
  pending_skill_count: number;
}

export interface ObservedJobSkillEvidence {
  fact_id: number;
  skill_id: number;
  skill_name: string;
  category: string;
  kind: string;
  confidence: number;
  evidence_text: string;
  verification_status: "verified" | "unverified" | "rejected";
  extraction_method: string;
  source_count: number;
}

export interface ObservedJobDetail extends ObservedJobSummary {
  jd_text: string;
  responsibilities: string;
  requirements: string;
  skills: ObservedJobSkillEvidence[];
}

export interface ObservedJobPage {
  items: ObservedJobSummary[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export type JDGenerationMode = "requirements" | "profile";
export type JDGenerationTarget = "public" | "internal";

export interface GenerateJDRequest {
  target: JDGenerationTarget;
  mode: JDGenerationMode;
  title: string;
  level?: string;
  department?: string;
  skills_input: string;
  headcount?: number;
  internal_reason?: string;
  receiving_manager?: string;
}

export interface JDInputSuggestionRequest {
  target: JDGenerationTarget;
  mode: JDGenerationMode;
  title: string;
  level?: string;
  department?: string;
}

export interface JDInputSuggestion {
  title: string;
  target: JDGenerationTarget;
  mode: JDGenerationMode;
  suggestions: string[];
  generation_mode: "llm" | "template";
  warnings: string[];
}

export interface GeneratedJDDraft {
  title: string;
  target: JDGenerationTarget;
  standardized_title?: string | null;
  level: string;
  department: string;
  responsibilities: string[];
  requirements: string[];
  skills: string[];
  bonus_skills: string[];
  trainable_skills: string[];
  transfer_profile: string[];
  manager_confirmations: string[];
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

export type InternalPositionStatus = "draft" | "pending_approval" | "open" | "paused" | "filled" | "closed";

export interface InternalPosition {
  id: EntityId;
  title: string;
  standardized_title?: string | null;
  department: string;
  receiving_manager?: string | null;
  level: string;
  headcount: number;
  open_reason: string;
  responsibilities: string[];
  requirements: string[];
  required_skills: string[];
  trainable_skills: string[];
  transfer_profile: string[];
  manager_confirmations: string[];
  min_tenure_months: number;
  min_position_tenure_months: number;
  allowed_departments: string[];
  restrictions: string[];
  target_start_date?: string | null;
  open_from?: string | null;
  open_until?: string | null;
  internal_description: string;
  status: InternalPositionStatus;
  created_at: string;
  updated_at: string;
}

export type InternalPositionCreate = Omit<InternalPosition, "id" | "created_at" | "updated_at">;

export interface EnterpriseTalent {
  id: EntityId;
  employee_no: string;
  name: string;
  department: string;
  current_position: string;
  level: string;
  location?: string | null;
  tenure_months: number;
  position_tenure_months: number;
  skills: string[];
  project_highlights: string[];
  status: "active" | "inactive" | "restricted";
  created_at: string;
  updated_at: string;
}

export type EnterpriseTalentCreate = Omit<EnterpriseTalent, "id" | "created_at" | "updated_at">;

export interface EnterpriseEmployeeDirectory {
  id: EntityId;
  employee_no: string;
  name: string;
  department: string;
  current_position: string;
  level: string;
  location?: string | null;
  tenure_months: number;
  position_tenure_months: number;
  skills: string[];
  project_highlights: string[];
  status: "active" | "inactive";
  source: string;
  in_talent_pool: boolean;
  synced_at: string;
}

export type EnterpriseEmployeeDirectoryInput = Omit<EnterpriseEmployeeDirectory, "id" | "in_talent_pool" | "synced_at">;

export interface EnterpriseDepartment {
  id: EntityId;
  code: string;
  name: string;
  manager?: string | null;
  location?: string | null;
  status: "active" | "inactive";
  employee_count: number;
  created_at: string;
  updated_at: string;
}

export type EnterpriseDepartmentInput = Omit<EnterpriseDepartment, "id" | "employee_count" | "created_at" | "updated_at">;

export interface TransferRuleSet {
  id: EntityId;
  name: string;
  version: number;
  min_tenure_months: number;
  min_position_tenure_months: number;
  min_match_score: number;
  skill_weight: number;
  tenure_weight: number;
  status: "draft" | "active" | "inactive";
  created_at: string;
  updated_at: string;
}

export type TransferRuleSetCreate = Omit<TransferRuleSet, "id" | "version" | "created_at" | "updated_at">;

export interface ResumeAdmissionPayload {
  department: string;
  current_position: string;
  level: string;
  location?: string | null;
}

export interface InternalMatchResult {
  talent_id: EntityId;
  employee_no: string;
  talent_name: string;
  current_department: string;
  current_position: string;
  position_id: EntityId;
  position_title: string;
  target_department: string;
  eligible: boolean;
  disqualifications: string[];
  score: number;
  matched_skills: string[];
  missing_skills: string[];
  trainable_gaps: string[];
  estimated_development_weeks: number;
  rule_set_id: EntityId | null;
  rule_version: number;
}

export interface SkillDemandSummary {
  skill: string;
  position_count: number;
  demand_headcount: number;
  talent_supply: number;
  gap: number;
  departments: string[];
  requirement_type: "required" | "trainable";
}

export interface TransferDecision {
  id: EntityId;
  talent_id: EntityId;
  talent_name: string;
  position_id: EntityId;
  position_title: string;
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  status: string;
  note: string;
  created_at: string;
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
  strengthened?: string[];
  weakened?: string[];
  removed: string[];
  change_type?: "comparison";
  previous_sample_count?: number;
  current_sample_count?: number;
}

export interface TechnologyStackBaseline {
  key: string;
  label: string;
  standard_job_count: number;
  source_count: number;
  top_skills: string[];
}

export interface JobReferenceStandard {
  id: EntityId;
  name: string;
  stack: string;
  stack_label: string;
  level: string;
  aliases: string[];
  core_skills: string[];
  source_count: number;
  company_count: number;
  active_period_count: number;
  maturity_stage: "mature" | "established" | "observed";
  description: string;
  first_seen_at: string;
  last_seen_at: string;
}

export interface AnalysisBaseline {
  version: string;
  source_note: string;
  minimum_source_count: number;
  standard_job_count: number;
  technology_stack_count: number;
  verified_skill_count: number;
  verified_fact_count: number;
  mature_job_count: number;
  established_job_count: number;
  baseline_at: string | null;
  technology_stacks: TechnologyStackBaseline[];
  job_standards: JobReferenceStandard[];
}

export interface JobReferenceStandardPage {
  items: JobReferenceStandard[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
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
  phone?: string;
  email?: string;
  salary?: string;
  matches?: TalentMatch[];
}

export interface ResumeSkillDetail {
  name: string;
  category: string;
  confidence: number;
  evidence_text: string;
  extraction_method: string;
}

export interface TalentMatch extends MatchReport {
  job_title: string;
  job_department?: string;
  job_level?: string;
  algorithm_version: string;
  urgent: boolean;
  evidence?: MatchEvidence[];
}

export interface MatchEvidence {
  id: EntityId;
  evidence_type: "resume_skill" | "job_requirement" | string;
  skill_name: string;
  evidence_text: string;
  source_ref: Record<string, unknown>;
}

export interface TalentDetail extends TalentSummary {
  file_size: number;
  content_type?: string | null;
  parsed_text: string;
  profile: Record<string, unknown>;
  parse_warnings: string[];
  skills: ResumeSkillDetail[];
  matches: TalentMatch[];
}

export interface MatchReport {
  id: EntityId;
  resume_id: EntityId;
  job_id: EntityId;
  score: number;
  matched: string[];
  missing: string[];
}

export interface DashboardQuery {
  hotJobsPage?: number;
  hotJobsPageSize?: number;
  emergingPage?: number;
  emergingPageSize?: number;
}

export interface DashboardOverview {
  heroCards: Array<{ value: string; label: string; change: string; up: boolean; color: string; action: string; link: string }>;
  kanban: Array<{
    job_id: EntityId;
    title: string;
    department: string;
    location: string;
    headcount: number;
    urgent: boolean;
    skills: string[];
    total: number;
    evaluated: number;
    pending: number;
    coverage: number;
    stages: Array<{ name: string; kind: "high" | "progress" | "gap" | "pending"; count: number }>;
  }>;
  highMatches: TalentSummary[];
  hotJobs: Array<{ standard_job_id: EntityId; title: string; demand: number; city: string; trend: number; spark: number[]; core_skills: string[]; lifecycle_stage: "mature" | "established" | "observed"; active_period_count: number }>;
  hotJobsTotal: number;
  emergingSkills: Array<{ id: EntityId; name: string; combo: string; growth: number; confidence: number }>;
  emergingSkillsTotal: number;
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

export type AgentRunStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "degraded"
  | "failed"
  | "cancelled";

export interface AgentRunAudit {
  id: string;
  agent_type: string;
  provider: string;
  model: string;
  prompt_version: string;
  input_summary: string;
  structured_output: Record<string, unknown> | null;
  status: AgentRunStatus;
  duration_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  retry_count: number;
  error_code: string | null;
  error_message: string | null;
  created_by: number | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface AgentRunAuditPage {
  items: AgentRunAudit[];
  total: number;
  page: number;
  pageSize: number;
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
  strengths: Array<{ title: string; explanation: string; evidence_ids: string[] }>;
  gaps: Array<{ title: string; explanation: string; evidence_ids: string[] }>;
  risks: Array<{ title: string; explanation: string; evidence_ids: string[] }>;
  interview_suggestions: string[];
  generation_mode: "llm" | "template";
  warnings: string[];
  agent_run_id: string;
  evidence: MatchEvidence[];
}

export interface TalentUpdatePayload {
  name: string;
  phone: string;
  email: string;
  current_position: string;
  experience: string;
  education: string;
  department: string;
  company: string;
  location: string;
}

export interface GraphNode {
  id: string;
  name: string;
  type: GraphType;
  stack?: "ai" | "backend" | "data" | "devops" | null;
  level?: "junior" | "middle" | "senior" | null;
  level_label?: string;
  x: number;
  y: number;
  description: string;
  importance?: number;
  frequency?: number;
  color?: string;
  size?: number;
  total_records?: number;
  category_key?: string;
  job_count?: number;
  category?: string;
  parent_skill?: string;
  parent_tech_point?: string;
  difficulty?: string;
  prerequisites?: string[];
  core_stack?: string[];
  common_solutions?: Array<{ name: string; purpose: string }>;
  evidence_ids?: number[];
  source_count?: number;
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
  returned?: number;
  total_available?: number | null;
  next_cursor?: string | null;
  has_more?: boolean;
  query_scope?: string | null;
}

export interface GraphEnrichmentCandidate {
  id: number;
  snapshot_id: string;
  skill_id: number;
  skill_name: string;
  candidate_data: {
    tech_points?: Array<{
      name: string;
      detail: string;
      confidence: number;
      evidence_ids?: string[];
      knowledge_points?: Array<{ name: string; description: string; confidence: number; evidence_ids?: string[] }>;
    }>;
    reason?: string | null;
    [key: string]: unknown;
  };
  evidence_source_ids: string[];
  confidence: number;
  machine_validation_status: string;
  review_status: "pending" | "approved" | "rejected";
  publication_status: "draft" | "approved" | "published" | "superseded" | "rejected";
  review_note: string | null;
  reviewed_at: string | null;
  published_at: string | null;
  lock_version: number;
  agent_run_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface GraphEnrichmentCandidatePage {
  items: GraphEnrichmentCandidate[];
  total: number;
  page: number;
  page_size: number;
  machine_failed_pending_count: number;
}

export interface GraphTaskResult {
  node_count?: number;
  edge_count?: number;
  fact_count?: number;
  stage?: string;
  detail?: string;
  completed?: number | null;
  total?: number | null;
}

export interface GraphAsyncTask {
  task_id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: number;
  result: GraphTaskResult | null;
  error_message: string | null;
}

export interface GraphQuery {
  stack?: "ai" | "backend" | "data" | "devops";
  level?: "junior" | "middle" | "senior";
  nodeType?: GraphType;
  keyword?: string;
  limit?: number;
  cursor?: string;
  pageSize?: number;
  maxLayer?: 1 | 2 | 3;
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
  deduplicated_records: number;
  duplicate_records: number;
  independent_job_clusters: number;
  independent_companies: number;
  valid_time_records: number;
  fallback_time_records: number;
  valid_salary_records: number;
  verified_skill_facts: number;
  reviewable_skill_facts: number;
  observed_months: number;
  observed_periods: number;
  period_unit: "day" | "month";
  coverage_start: string | null;
  coverage_end: string | null;
  insufficient_data: boolean;
  notes: string[];
}

export interface TrendQuery {
  window: "15d" | "1m" | "3m" | "6m";
  keyword?: string;
  city?: string;
  emergingPage?: number;
  emergingPageSize?: number;
  newJobPage?: number;
  newJobPageSize?: number;
  newJobKeyword?: string;
}

export interface TrendOverview {
  window: TrendQuery["window"];
  windowLabel: string;
  granularity: "day" | "month";
  stats: { totalJobs: string; newSkills: number; avgSalary: string; activeCities: number };
  months: string[];
  jobDemand: TrendSeries[];
  salary: TrendSeries[];
  heatmapSkills: string[];
  heatmap: HeatmapPoint[];
  locations: Array<{ city: string; value: number }>;
  emergingSkills: Array<{
    id: EntityId;
    skill: string;
    category: string;
    growth: number | null;
    stage: string;
    sparkline: number[];
    current_count: number;
    previous_count: number;
    current_companies: number;
    previous_companies: number;
    current_sources: number;
    current_periods: number;
    trend_score: number;
    evidence_note: string;
  }>;
  emergingTotal: number;
  newJobs: Array<{
    id: EntityId;
    name: string;
    core_skills: string[];
    description: string;
    confidence: number;
    source_count: number;
    first_seen_at: string;
    decision: string | null;
  }>;
  newJobsTotal: number;
  newJobObservationTotal: number;
  dataQuality: AnalysisDataQuality;
  baseline: AnalysisBaseline;
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
  success: number | null;
  duration: string;
  progress: number;
  progress_info?: string;
  schedule: string;
  nextRun: string;
}

export interface CrawlerAutomationConfig {
  enabled: boolean;
  source_ids: number[];
  schedule_type: "interval" | "daily" | "weekly";
  interval_minutes: number;
  run_time: string;
  weekdays: number[];
  max_records: number;
  max_pages: number;
  retry_count: number;
  retry_delay_minutes: number;
  timeout_seconds: number;
  next_run_at?: string | null;
}

export interface JobImportValidation {
  file: string;
  total: number;
  passed: number;
  failed: number;
  errors: Array<{ index: number | null; title: string; errors: string[] }>;
  warning_count: number;
  warnings: Array<{ index: number; title: string; warnings: string[] }>;
}

export interface JobImportResult {
  files: string[];
  total: number;
  imported: number;
  duplicates: number;
  near_duplicates: number;
  low_quality: number;
  time_anomalies: number;
  quality_status_counts: Record<DataQualityStatus, number>;
  cross_source_verified: number;
  skill_facts: number;
  verified_skill_facts: number;
  unverified_skill_facts: number;
  validation: JobImportValidation[];
}

export type DataQualityStatus = "accepted" | "warning" | "rejected" | "pending";

export interface DataQualitySummary {
  total: number;
  accepted: number;
  warning: number;
  rejected: number;
  pending: number;
  near_duplicates: number;
  excluded: number;
  average_quality_score: number;
  flag_counts: Record<string, number>;
}

export interface RawJobQualityItem {
  id: EntityId;
  title: string;
  standard_job_id: EntityId | null;
  standardized_title: string | null;
  company: string | null;
  source: string;
  source_url: string | null;
  posted_at: string | null;
  crawled_at: string | null;
  posted_at_text: string | null;
  crawled_at_text: string | null;
  quality_score: number;
  freshness_score: number;
  source_trust_score: number;
  quality_status: DataQualityStatus;
  quality_flags: string[];
  dedup_status: string;
  near_duplicate_group_id: string | null;
  near_duplicate_score: number;
  is_excluded: boolean;
  exclusion_reason: string | null;
  quality_evaluated_at: string | null;
}

export interface DataQualityPage {
  items: RawJobQualityItem[];
  summary: DataQualitySummary;
  meta: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface DataQualityQuery {
  page: number;
  pageSize: number;
  source?: string;
  qualityStatus?: DataQualityStatus;
  qualityFlag?: string;
  nearDuplicateGroupId?: string;
  excluded?: boolean;
}

export type SkillFactVerificationStatus = "unverified" | "verified" | "rejected";

export interface SkillFactReviewItem {
  id: EntityId;
  skill_id: EntityId;
  skill_name: string;
  category: string;
  kind: "required" | "preferred";
  importance: number;
  frequency: number;
  confidence: number;
  evidence_text: string;
  verification_status: SkillFactVerificationStatus;
  extraction_method: string;
  source_count: number;
  job_id: EntityId | null;
  raw_job_record_id: EntityId | null;
  job_title: string;
  company: string | null;
  source: string;
  source_url: string | null;
  reviewed_by: EntityId | null;
  reviewer_name: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_at: string;
}

export interface SkillFactReviewSummary {
  all: number;
  unverified: number;
  verified: number;
  rejected: number;
}

export interface SkillFactReviewPage {
  items: SkillFactReviewItem[];
  summary: SkillFactReviewSummary;
  meta: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface PipelineSummary {
  totalJobs: number;
  todayImported: number;
  sourceCount: number;
  validRecords: number;
  validRate: number;
  failedTasks: number;
  processedToday: number;
  duplicatesToday: number;
  verifiedFacts: number;
  unverifiedFacts: number;
  overallQuality: number;
}

export interface PipelineRun {
  id: string;
  trigger: "manual" | "scheduled" | string;
  status: "queued" | "running" | "succeeded" | "partial" | "failed";
  stage: string;
  progress: number;
  requested_sources: number[];
  stage_results: Record<string, unknown>;
  quality_summary: Record<string, number>;
  error_message: string | null;
  scheduled_for: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface AdminOverview {
  metrics: any[];
  services: Array<{
    name: string;
    desc: string;
    icon: string;
    tone: string;
    latency: string;
    status: "healthy" | "degraded" | "unavailable";
    statusLabel: string;
  }>;
  resources: Array<{
    label: string;
    value: number;
    color: string;
    detail: string;
  }>;
  traffic: {
    inbound: string;
    outbound: string;
    receivedTotal: string;
    sentTotal: string;
  };
  recentTasks: any[];
  systemEvents: any[];
  crawlers: DataSource[];
  pipelineSummary: PipelineSummary;
  pipelineRuns?: PipelineRun[];
  currentPipelineRun?: PipelineRun | null;
  qualities: any[];
  performanceCards: any[];
  endpoints: Array<{
    key: string;
    title: string;
    description: string;
    value: string;
    percent: number;
  }>;
  logs: any[];
  generatedAt: string;
}

export type AdminResourceSnapshot = Pick<AdminOverview, "resources" | "traffic"> & {
  sampledAt: string;
};

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
}
