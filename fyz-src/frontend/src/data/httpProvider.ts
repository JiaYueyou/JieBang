import request from "@/api/request";
import type { ApiResponse } from "@/api/types";
import type { DataProvider } from "./provider";
import type {
  AnalysisBaseline,
  AnalysisDataQuality,
  CapabilityChange,
  DataQualityPage,
  DataQualityQuery,
  EmergingJob,
  GeneratedJDDraft,
  JDInputSuggestion,
  JobImportResult,
  JobSummary,
  InternalPosition,
  ObservedJobDetail,
  ObservedJobPage,
  PageResult,
  RawJobQualityItem,
  SkillFactReviewItem,
  SkillFactReviewPage,
  SkillFactReviewSummary,
  SkillFactVerificationStatus,
  TrendOverview,
  GraphAsyncTask,
} from "@/domain/types";

interface AsyncTask<T> {
  task_id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: number;
  result: T | null;
  error_message: string | null;
}

interface JDGenerationCreated {
  task: AsyncTask<GeneratedJDDraft>;
  agent_run_id: string;
}

const AGENT_POLL_INTERVAL_MS = 2000;
const AGENT_MAX_POLLS = 90;

interface ResumeExtractionResponse {
  filename: string;
  text: string;
  character_count: number;
  warnings: string[];
}

interface CareerAnalysisResponse {
  recommendations: Array<{
    rank: number; job_id: number; job: string; recommend_score: number;
    current_match: number; after_match: number; existing: string[]; gaps: string[];
    learning_plan: Array<{ skill: string; time: string; difficulty: "easy" | "medium" | "hard"; resources: string[] }>;
    suggested_project: string; total_time: string; internal: boolean; explanation: string;
  }>;
  agent_run_id: string;
  agent_status: "succeeded" | "degraded";
  warnings: string[];
}

interface AgentTaskCreated<T> {
  task: AsyncTask<T>;
  agent_run_id: string;
}

interface AnalysisOverviewResponse {
  window: TrendOverview["window"];
  window_label: string;
  granularity: TrendOverview["granularity"];
  stats: { total_jobs: number; new_skills: number; average_salary_k: number | null; active_cities: number };
  months: string[];
  job_demand: Array<{ name: string; values: number[] }>;
  salary: Array<{ name: string; values: number[] }>;
  heatmap_skills: string[];
  heatmap: Array<{ x: number; y: number; value: number }>;
  locations: Array<{ city: string; value: number }>;
  emerging_skills: TrendOverview["emergingSkills"];
  emerging_total?: number;
  new_jobs?: TrendOverview["newJobs"];
  new_jobs_total?: number;
  new_job_observation_total?: number;
  data_quality: AnalysisDataQuality;
  baseline: AnalysisBaseline;
}

interface JobInsightsResponse {
  emerging_jobs: EmergingJob[];
  capability_changes: CapabilityChange[];
  data_quality: AnalysisDataQuality;
  baseline: AnalysisBaseline;
}

const sleep = (milliseconds: number) => new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

function mapTrendOverview(raw: AnalysisOverviewResponse): TrendOverview {
  return {
    window: raw.window,
    windowLabel: raw.window_label,
    granularity: raw.granularity,
    stats: {
      totalJobs: String(raw.stats.total_jobs),
      newSkills: raw.stats.new_skills,
      avgSalary: raw.stats.average_salary_k === null ? "—" : `${raw.stats.average_salary_k}K`,
      activeCities: raw.stats.active_cities,
    },
    months: raw.months,
    jobDemand: raw.job_demand,
    salary: raw.salary,
    heatmapSkills: raw.heatmap_skills,
    heatmap: raw.heatmap,
    locations: raw.locations,
    emergingSkills: raw.emerging_skills,
    emergingTotal: raw.emerging_total ?? raw.emerging_skills.length,
    newJobs: raw.new_jobs ?? [],
    newJobsTotal: raw.new_jobs_total ?? raw.new_jobs?.length ?? 0,
    newJobObservationTotal: raw.new_job_observation_total ?? raw.new_jobs_total ?? raw.new_jobs?.length ?? 0,
    dataQuality: raw.data_quality,
    baseline: raw.baseline,
  };
}

async function get<T>(url: string, params?: object): Promise<T> {
  const response = await request.get<ApiResponse<T>>(url, { params });
  if (response.data.data === null) throw new Error(`接口 ${url} 未返回数据`);
  return response.data.data;
}

async function post<T>(url: string, data?: unknown, timeout?: number): Promise<T> {
  const response = timeout
    ? await request.post<ApiResponse<T>>(url, data, { timeout })
    : await request.post<ApiResponse<T>>(url, data);
  return response.data.data as T;
}

async function waitForAgentTask<T>(
  created: AgentTaskCreated<T>,
  onProgress?: (progress: number, status: string) => void,
): Promise<T> {
  let task = created.task;
  onProgress?.(task.progress, task.status);
  for (let attempt = 0; attempt < AGENT_MAX_POLLS && task.status !== "succeeded" && task.status !== "failed"; attempt += 1) {
    if (attempt > 0) await sleep(AGENT_POLL_INTERVAL_MS);
    task = await get<AsyncTask<T>>(`/tasks/${task.task_id}`);
    onProgress?.(task.progress, task.status);
  }
  if (task.status === "failed") throw new Error(task.error_message || "AI 任务执行失败");
  if (task.status !== "succeeded") throw new Error("AI 任务未在预期时间内完成，请稍后刷新重试");
  if (task.result === null) throw new Error("AI 任务已完成，但未返回可用结果");
  return task.result;
}

const CAREER_TASK_STORAGE_KEY = "fyz:career-agent-task:v1";

function mapCareerResult(raw: CareerAnalysisResponse): import("@/domain/types").CareerAnalysisResult {
  return {
    recommendations: raw.recommendations.map((item) => ({
      rank: item.rank,
      job_id: item.job_id,
      job: item.job,
      recommendScore: item.recommend_score,
      currentMatch: item.current_match,
      afterMatch: item.after_match,
      existing: item.existing,
      gaps: item.gaps,
      learningPlan: item.learning_plan,
      suggestedProject: item.suggested_project,
      totalTime: item.total_time,
      internal: item.internal,
      explanation: item.explanation,
    })),
    agentRunId: raw.agent_run_id,
    agentStatus: raw.agent_status,
    warnings: raw.warnings,
  };
}

function saveCareerTask(value: unknown): void {
  try { sessionStorage.setItem(CAREER_TASK_STORAGE_KEY, JSON.stringify(value)); } catch { /* storage is optional */ }
}

function readCareerTask(): { created?: AgentTaskCreated<CareerAnalysisResponse>; result?: import("@/domain/types").CareerAnalysisResult } | null {
  try {
    const raw = sessionStorage.getItem(CAREER_TASK_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

async function waitForTask<T>(task: AsyncTask<T>, maxPolls = AGENT_MAX_POLLS): Promise<T> {
  let current = task;
  for (let attempt = 0; attempt < maxPolls && current.status !== "succeeded" && current.status !== "failed"; attempt += 1) {
    if (attempt > 0) await sleep(AGENT_POLL_INTERVAL_MS);
    current = await get<AsyncTask<T>>(`/tasks/${current.task_id}`);
  }
  if (current.status === "failed") throw new Error(current.error_message || "导入任务执行失败");
  if (current.status !== "succeeded") throw new Error("导入任务未在预期时间内完成，请稍后重试");
  if (current.result === null) throw new Error("导入任务已完成，但未返回结果");
  return current.result;
}

async function put<T>(url: string, data?: unknown): Promise<T> {
  const response = await request.put<ApiResponse<T>>(url, data);
  if (response.data.data === null) throw new Error(`接口 ${url} 未返回数据`);
  return response.data.data;
}

async function patch<T>(url: string, data?: unknown): Promise<T> {
  const response = await request.patch<ApiResponse<T>>(url, data);
  if (response.data.data === null) throw new Error(`接口 ${url} 未返回数据`);
  return response.data.data;
}

export const httpDataProvider: DataProvider = {
  dashboard: {
    getOverview: (query) => get("/dashboard/overview", {
      hot_jobs_page: query?.hotJobsPage || 1,
      hot_jobs_page_size: query?.hotJobsPageSize || 10,
      emerging_page: query?.emergingPage || 1,
      emerging_page_size: query?.emergingPageSize || 10,
    }),
  },
  jobs: {
    list: async (query = {}) => {
      const page = query.page ?? 1;
      const pageSize = query.pageSize ?? 20;
      const response = await request.get<ApiResponse<JobSummary[]>>("/jobs", {
        params: {
          page,
          page_size: pageSize,
          status: query.status || undefined,
          keyword: query.keyword || undefined,
        },
      });
      const meta = response.data.meta;
      return {
        items: response.data.data ?? [],
        page: meta?.page ?? page,
        pageSize: meta?.page_size ?? pageSize,
        total: meta?.total ?? 0,
        totalPages: meta?.total_pages ?? 0,
      } satisfies PageResult<JobSummary>;
    },
    listObserved: async (query) => {
      const response = await request.get<ApiResponse<ObservedJobDetail[]>>("/jobs/observed", {
        params: {
          page: query.page,
          page_size: query.pageSize,
          keyword: query.keyword,
          city: query.city,
          source: query.source,
        },
      });
      const meta = response.data.meta;
      return {
        items: response.data.data ?? [],
        page: meta?.page ?? query.page,
        pageSize: meta?.page_size ?? query.pageSize,
        total: meta?.total ?? 0,
        totalPages: meta?.total_pages ?? 0,
      } satisfies ObservedJobPage;
    },
    getObserved: (id) => get(`/jobs/observed/${id}`),
    getInsights: async (skill) => {
      const raw = await get<JobInsightsResponse>("/analysis/job-insights", {
        skill: skill || undefined,
      });
      return {
        emergingJobs: raw.emerging_jobs,
        capabilityChanges: raw.capability_changes,
        dataQuality: raw.data_quality,
        baseline: raw.baseline,
      };
    },
    decideInsight: async (id, decision, note) => {
      await put(`/analysis/emerging-jobs/${id}/decision`, { decision, note });
    },
    suggestJDInput: async (input) => {
      const created = await post<AgentTaskCreated<JDInputSuggestion>>(
        "/agents/jd-input-suggestions",
        input,
      );
      return waitForAgentTask(created);
    },
    generateJD: async (input) => {
      const created = await post<JDGenerationCreated>("/agents/jd-generations", input);
      return waitForAgentTask(created);
    },
    create: (job) => post("/jobs", job),
    update: (job) => put(`/jobs/${job.id}`, job),
    remove: async (id) => { await request.delete(`/jobs/${id}`); },
    updateStatus: (id,status) => put(`/jobs/${id}/status`,{status}),
  },
  talents: {
    list:()=>get("/talents"), get:(id)=>get(`/talents/${id}`),
    getDetails: (id) => get(`/talents/${id}/details`),
    upload: async (input) => {
      const form = new FormData();
      form.append("file", input.file);
      const fields = { name: input.name, current_position: input.currentPosition, experience: input.experience, education: input.education, department: input.department };
      Object.entries(fields).forEach(([key, value]) => { if (value) form.append(key, value); });
      await request.post("/resumes", form);
    },
    download: async (resumeId, filename) => {
      const response = await request.get(`/resumes/${resumeId}/file`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click();
      URL.revokeObjectURL(url);
    },
    preview: async (resumeId) => {
      const response = await request.get(`/resumes/${resumeId}/file`, { responseType: "blob" });
      return {
        url: URL.createObjectURL(response.data),
        contentType: response.headers["content-type"] || response.data.type || "application/octet-stream",
      };
    },
    matchJobs: (resumeId, jobIds) => post(`/resumes/${resumeId}/matches`, { job_ids: jobIds }),
    recalculate: () => post("/matches/recalculate", {}),
    explain: async (matchId, onProgress) => waitForAgentTask(
      await post<AgentTaskCreated<import("@/domain/types").MatchExplanation>>(
        "/agents/match-explanations", { match_id: matchId }, 60000,
      ),
      onProgress,
    ),
  },
  career: {
    analyze: async (input) => {
      async function extractFiles(files: File[] = []) {
        const texts: string[] = [];
        for (const file of files) {
          const form = new FormData();
          form.append("file", file);
          const response = await request.post<ApiResponse<ResumeExtractionResponse>>("/career/resume-extractions", form);
          if (response.data.data?.text) texts.push(response.data.data.text);
        }
        return texts.join("\n");
      }
      const resumeText = await extractFiles(input.resumeFiles);
      const enterpriseFileText = await extractFiles(input.enterpriseFiles);
      const created = await post<AgentTaskCreated<CareerAnalysisResponse>>("/agents/career-plannings", {
        skill_text: input.skillText,
        resume_text: resumeText,
        enterprise_tech: [input.enterpriseTech, enterpriseFileText].filter(Boolean).join("\n"),
        internal_jobs: input.enterpriseJobs,
        target_job_ids: input.targetJobIds ?? [],
      }, 60000);
      saveCareerTask({ created });
      const result = mapCareerResult(await waitForAgentTask(created));
      saveCareerTask({ result });
      return result;
    },
    recover: async () => {
      const saved = readCareerTask();
      if (saved?.result) return saved.result;
      if (!saved?.created) return null;
      const result = mapCareerResult(await waitForAgentTask(saved.created));
      saveCareerTask({ result });
      return result;
    },
  },
  internalTransfer: {
    searchEmployeeDirectory: (keyword) => get("/internal-transfer/employee-directory", { keyword, limit: 10 }),
    createTalentFromDirectory: (employeeId) => post(`/internal-transfer/talents/from-directory/${employeeId}`, {}),
    listPositions: async () => (
      await httpDataProvider.internalTransfer.listPositionsPage({ page: 1, pageSize: 100 })
    ).items,
    listPositionsPage: async (query) => {
      const response = await request.get<ApiResponse<InternalPosition[]>>("/internal-transfer/positions", {
        params: {
          page: query.page,
          page_size: query.pageSize,
          status: query.status || undefined,
          keyword: query.keyword || undefined,
        },
      });
      const meta = response.data.meta;
      return {
        items: response.data.data ?? [],
        page: meta?.page ?? query.page,
        pageSize: meta?.page_size ?? query.pageSize,
        total: meta?.total ?? 0,
        totalPages: meta?.total_pages ?? 0,
      } satisfies PageResult<InternalPosition>;
    },
    createPosition: (input) => post("/internal-transfer/positions", input),
    updatePositionStatus: (id, status) => put(`/internal-transfer/positions/${id}/status`, { status }),
    listTalents: () => get("/internal-transfer/talents"),
    createTalent: (input) => post("/internal-transfer/talents", input),
    listSkillDemands: () => get("/internal-transfer/skill-demands"),
    listRuleSets: () => get("/internal-transfer/rule-sets"),
    createRuleSet: (input) => post("/internal-transfer/rule-sets", input),
    matchByTalent: (input) => post("/internal-transfer/matches/by-talent", input),
    matchByPosition: (input) => post("/internal-transfer/matches/by-position", input),
    listDecisions: () => get("/internal-transfer/decisions"),
    createDecision: (input) => post("/internal-transfer/decisions", input),
  },
  graph: {
    getOverview:(query)=>get("/graph/overview",query?{
      stack:query.stack,level:query.level,keyword:query.keyword,
      cursor:query.cursor,page_size:query.pageSize,max_layer:query.maxLayer,
    }:undefined),
    getNeighbors:(nodeId,query)=>get(`/graph/nodes/${encodeURIComponent(nodeId)}/neighbors`,query?{
      cursor:query.cursor,page_size:query.pageSize,max_layer:query.maxLayer,
    }:undefined),
    getPanorama:(query)=>get("/graph/panorama",query?{
      stack:query.stack,level:query.level,node_type:query.nodeType,
      keyword:query.keyword,limit:query.limit,
    }:undefined),
    getNode:(nodeId)=>get(`/graph/nodes/${encodeURIComponent(nodeId)}`),
    expand:(nodeId,depth=2)=>get("/graph/expand",{node_id:nodeId,depth}),
    search:(query,type)=>get("/graph/search",{q:query,types:type}),
    path:(fromId,toId)=>get("/graph/path",{from_id:fromId,to_id:toId}),
    sync: async () => {
      const task = await post<AsyncTask<{ node_count: number; edge_count: number; fact_count: number }>>(
        "/graph/sync",
        { mode: "full", enrich_top_skills: false },
      );
      return waitForTask(task);
    },
    startSync: () => post<GraphAsyncTask>(
      "/graph/sync", { mode: "full", enrich_top_skills: false },
    ),
    startEnrichment: () => post<GraphAsyncTask>("/graph/enrichment/generate"),
    startPublication: (candidateIds = []) => post<GraphAsyncTask>(
      "/graph/enrichment/publish", { candidate_ids: candidateIds },
    ),
    getTask: (taskId) => get<GraphAsyncTask>(`/tasks/${taskId}`),
    generateEnrichment: async () => waitForTask(
      await post("/graph/enrichment/generate"),
      600,
    ),
    listEnrichment: (query) => get("/graph/enrichment/candidates", query ? {
      page: query.page, page_size: query.pageSize, review_status: query.reviewStatus,
    } : undefined),
    reviewEnrichment: (candidateId, input) => patch(
      `/graph/enrichment/candidates/${candidateId}/review`,
      { action: input.action, note: input.note, lock_version: input.lockVersion },
    ),
    publishEnrichment: async (candidateIds = []) => waitForTask(await post(
      "/graph/enrichment/publish", { candidate_ids: candidateIds },
    )),
  },
  trends: {
    getOverview: async (query) => mapTrendOverview(
      await get<AnalysisOverviewResponse>("/analysis/overview", {
        window: query.window,
        keyword: query.keyword || undefined,
        city: query.city || undefined,
        emerging_page: query.emergingPage || 1,
        emerging_page_size: query.emergingPageSize || 10,
        new_job_page: query.newJobPage || 1,
        new_job_page_size: query.newJobPageSize || 10,
        new_job_keyword: query.newJobKeyword || undefined,
      }),
    ),
  },
  skillReviews: {
    list: async ({ page, pageSize, status, keyword }) => {
      const response = await request.get<ApiResponse<{
        items: SkillFactReviewItem[];
        summary: SkillFactReviewSummary;
      }>>("/skills/facts/reviews", {
        params: {
          page,
          page_size: pageSize,
          status: status || undefined,
          keyword: keyword || undefined,
        },
      });
      if (response.data.data === null) throw new Error("技能事实审核接口未返回数据");
      return {
        ...response.data.data,
        meta: response.data.meta ?? {
          page,
          page_size: pageSize,
          total: response.data.data.items.length,
          total_pages: response.data.data.items.length ? 1 : 0,
        },
      } satisfies SkillFactReviewPage;
    },
    review: (
      factId: number,
      decision: Exclude<SkillFactVerificationStatus, "unverified">,
      note?: string,
    ) => patch(`/skills/facts/${factId}/review`, { decision, note }),
    reviewBatch: (factIds, decision, note) => post(
      "/skills/facts/reviews/batch",
      { fact_ids: factIds, decision, note },
    ),
    approveAll: (keyword) => post(
      "/skills/facts/reviews/approve-all",
      { keyword: keyword || undefined },
    ),
  },
  favorites: {
    list:()=>get("/favorites"),
    toggle:async(type,targetId,title)=>{
      const result=await post<{active:boolean}>("/favorites",{target_type:type,target_id:targetId,title});
      return result.active;
    },
    removeMany:async(ids)=>{await post("/favorites/batch-delete",{ids});},
    updateNote:async(id,note)=>{await request.put(`/favorites/${id}/note`,{note});},
  },
  history: {
    list:()=>get("/history"),
    record:(input)=>post("/history",input),
    remove:async(id)=>{await request.delete(`/history/${id}`);},
    clear:async()=>{await request.delete("/history");},
    getInsights:()=>get("/history/insights"),
  },
  admin: {
    getOverview:()=>get("/admin/overview"),
    getResources:()=>get("/admin/resources"),
    listAgentRuns: async ({ page, pageSize, agentType, status }) => {
      const response = await request.get<ApiResponse<import("@/domain/types").AgentRunAudit[]>>(
        "/agents/runs",
        {
          params: {
            page,
            page_size: pageSize,
            agent_type: agentType || undefined,
            status: status || undefined,
          },
        },
      );
      return {
        items: response.data.data ?? [],
        total: response.data.meta?.total ?? 0,
        page,
        pageSize,
      };
    },
    listQuality: async (query: DataQualityQuery) => {
      const response = await request.get<ApiResponse<Omit<DataQualityPage, "meta">>>(
        "/admin/data-quality/records",
        {
          params: {
            page: query.page,
            page_size: query.pageSize,
            source: query.source || undefined,
            quality_status: query.qualityStatus || undefined,
            quality_flag: query.qualityFlag || undefined,
            near_duplicate_group_id: query.nearDuplicateGroupId || undefined,
            excluded: query.excluded,
          },
        },
      );
      if (response.data.data === null) throw new Error("数据质量接口未返回数据");
      return {
        ...response.data.data,
        meta: response.data.meta ?? {
          page: query.page,
          page_size: query.pageSize,
          total: response.data.data.items.length,
          total_pages: response.data.data.items.length ? 1 : 0,
        },
      };
    },
    decideQuality: (id, action, reason) => patch<RawJobQualityItem>(
      `/admin/data-quality/records/${id}`,
      { action, reason },
    ),
    toggleCrawler:async(id)=>{await request.put(`/admin/data-sources/${id}`,{});},
    runCrawler:async(id)=>{await post(`/admin/data-sources/${id}/run`);},
    pollCrawler:async(id)=>get(`/admin/data-sources/${id}/poll`),
    importCrawlerOutput:async(filename)=>waitForTask(
      await post<AsyncTask<JobImportResult>>("/data-imports/jobs",{files:[filename]}),
    ),
  },
};
