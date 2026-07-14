import request from "@/api/request";
import type { ApiResponse } from "@/api/types";
import type { DataProvider } from "./provider";
import type {
  AnalysisDataQuality,
  CapabilityChange,
  EmergingJob,
  GeneratedJDDraft,
  JDInputSuggestion,
  TrendOverview,
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
  stats: { total_jobs: number; new_skills: number; average_salary_k: number | null; active_cities: number };
  months: string[];
  job_demand: Array<{ name: string; values: number[] }>;
  salary: Array<{ name: string; values: number[] }>;
  heatmap_skills: string[];
  heatmap: Array<{ x: number; y: number; value: number }>;
  locations: Array<{ city: string; value: number }>;
  emerging_skills: TrendOverview["emergingSkills"];
  data_quality: AnalysisDataQuality;
}

interface JobInsightsResponse {
  emerging_jobs: EmergingJob[];
  capability_changes: CapabilityChange[];
  data_quality: AnalysisDataQuality;
}

const sleep = (milliseconds: number) => new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

function mapTrendOverview(raw: AnalysisOverviewResponse): TrendOverview {
  return {
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
    dataQuality: raw.data_quality,
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

async function waitForAgentTask<T>(created: AgentTaskCreated<T>): Promise<T> {
  let task = created.task;
  for (let attempt = 0; attempt < AGENT_MAX_POLLS && task.status !== "succeeded" && task.status !== "failed"; attempt += 1) {
    if (attempt > 0) await sleep(AGENT_POLL_INTERVAL_MS);
    task = await get<AsyncTask<T>>(`/tasks/${task.task_id}`);
  }
  if (task.status === "failed") throw new Error(task.error_message || "AI 任务执行失败");
  if (task.status !== "succeeded") throw new Error("AI 任务未在预期时间内完成，请稍后刷新重试");
  if (task.result === null) throw new Error("AI 任务已完成，但未返回可用结果");
  return task.result;
}

async function put<T>(url: string, data?: unknown): Promise<T> {
  const response = await request.put<ApiResponse<T>>(url, data);
  if (response.data.data === null) throw new Error(`接口 ${url} 未返回数据`);
  return response.data.data;
}

export const httpDataProvider: DataProvider = {
  dashboard: { getOverview: () => get("/dashboard/overview") },
  jobs: {
    list: () => get("/jobs"),
    getInsights: async (skill) => {
      const raw = await get<JobInsightsResponse>("/analysis/job-insights", {
        skill: skill || undefined,
      });
      return {
        emergingJobs: raw.emerging_jobs,
        capabilityChanges: raw.capability_changes,
        dataQuality: raw.data_quality,
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
    explain: async (matchId) => waitForAgentTask(
      await post<AgentTaskCreated<import("@/domain/types").MatchExplanation>>(
        "/agents/match-explanations", { match_id: matchId }, 60000,
      ),
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
      const raw = await waitForAgentTask(await post<AgentTaskCreated<CareerAnalysisResponse>>("/agents/career-plannings", {
        skill_text: input.skillText,
        resume_text: resumeText,
        enterprise_tech: [input.enterpriseTech, enterpriseFileText].filter(Boolean).join("\n"),
        internal_jobs: input.enterpriseJobs,
      }, 60000));
      return { recommendations: raw.recommendations.map((item) => ({
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
      })), agentRunId: raw.agent_run_id, agentStatus: raw.agent_status, warnings: raw.warnings };
    },
  },
  graph: {
    getPanorama:(query)=>get("/graph/panorama",query?{
      stack:query.stack,level:query.level,node_type:query.nodeType,
      keyword:query.keyword,limit:query.limit,
    }:undefined),
    getNode:(nodeId)=>get(`/graph/nodes/${encodeURIComponent(nodeId)}`),
    expand:(nodeId,depth=2)=>get("/graph/expand",{node_id:nodeId,depth}),
    search:(query,type)=>get("/graph/search",{q:query,types:type}),
    path:(fromId,toId)=>get("/graph/path",{from_id:fromId,to_id:toId}),
  },
  trends: {
    getOverview: async (query) => mapTrendOverview(
      await get<AnalysisOverviewResponse>("/analysis/overview", query),
    ),
  },
  favorites: {
    list:()=>get("/favorites"),
    toggle:async(type,targetId)=>{await post("/favorites",{target_type:type,target_id:targetId});return true;},
    removeMany:async(ids)=>{await post("/favorites/batch-delete",{ids});},
    updateNote:async(id,note)=>{await request.put(`/favorites/${id}/note`,{note});},
  },
  history: {
    list:()=>get("/history"),
    remove:async(id)=>{await request.delete(`/history/${id}`);},
    clear:async()=>{await request.delete("/history");},
    getInsights:()=>get("/history/insights"),
  },
  admin: {
    getOverview:()=>get("/admin/overview"),
    toggleCrawler:async(id)=>{await request.put(`/admin/data-sources/${id}`,{});},
    runCrawler:async(id)=>{await post(`/admin/data-sources/${id}/run`);},
    toggleUser:async(id)=>{await request.put(`/admin/users/${id}/status`,{});},
    saveSettings:async(settings)=>{await request.put("/admin/settings",settings);},
  },
};
