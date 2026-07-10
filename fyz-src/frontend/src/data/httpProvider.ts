import request from "@/api/request";
import type { ApiResponse } from "@/api/types";
import type { DataProvider } from "./provider";
import type {
  AnalysisDataQuality,
  CapabilityChange,
  EmergingJob,
  GeneratedJDDraft,
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

async function post<T>(url: string, data?: unknown): Promise<T> {
  const response = await request.post<ApiResponse<T>>(url, data);
  return response.data.data as T;
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
    generateJD: async (input) => {
      const created = await post<JDGenerationCreated>("/agents/jd-generations", input);
      let task = created.task;
      for (let attempt = 0; attempt < 60 && task.status !== "succeeded" && task.status !== "failed"; attempt += 1) {
        await sleep(500);
        task = await get<AsyncTask<GeneratedJDDraft>>(`/tasks/${task.task_id}`);
      }
      if (task.status !== "succeeded" || !task.result) {
        throw new Error(task.error_message || "JD 生成任务未在预期时间内完成");
      }
      return task.result;
    },
    create: (job) => post("/jobs", job),
    update: (job) => put(`/jobs/${job.id}`, job),
    remove: async (id) => { await request.delete(`/jobs/${id}`); },
    updateStatus: (id,status) => put(`/jobs/${id}/status`,{status}),
  },
  talents: { list:()=>get("/talents"), get:(id)=>get(`/talents/${id}`) },
  career: { analyze:(input)=>post("/career/analyses",{skill_text:input.skillText,internal_jobs:input.enterpriseJobs}) },
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
