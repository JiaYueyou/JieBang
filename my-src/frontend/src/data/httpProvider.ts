import request from "@/api/request";
import type { ApiResponse } from "@/api/types";
import type { DataProvider } from "./provider";

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
    getInsights: async () => ({ emergingJobs: await get("/emerging-jobs"), capabilityChanges: await get("/jobs/changes") }),
    generateJD: (input) => post("/jobs/generate-jd", input),
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
  trends: { getOverview:()=>get("/trends/overview") },
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
