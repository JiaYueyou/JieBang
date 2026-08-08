import type { DataProvider } from "./provider";
import { loadMockDatabase, saveMockDatabase } from "./mockDatabase";
import type { CareerRecommendation, DashboardOverview, FavoriteRecord, FavoriteTargetType, JobSummary, TalentSummary } from "@/domain/types";

const delay = <T>(value: T, ms = 30) => new Promise<T>((resolve) => setTimeout(() => resolve(structuredClone(value)), ms));
const db = () => loadMockDatabase();
const persist = (value: ReturnType<typeof db>) => saveMockDatabase(value);

function syncJobFavorite(data: ReturnType<typeof db>, job: JobSummary): void {
  const favorite = data.favorites.find((item) => item.target_type === "job" && item.target_id === job.id);
  if (!favorite) return;
  Object.assign(favorite, {
    title: job.title,
    subtitle: `${job.level}岗位`,
    company: job.company || job.department,
    location: job.location || "",
    salary: job.salary_range,
    experience: job.experience || "",
    education: job.education || "",
    skills: job.skills || [],
    match: job.match || 0,
    urgent: job.urgent,
  });
}

function favoriteFromEntity(type: FavoriteTargetType, targetId: number, title?: string): FavoriteRecord | null {
  const data = db();
  const entity = type === "job"
    ? data.jobs.find((item) => item.id === targetId)
    : data.talents.find((item) => item.resume_id === targetId);
  if (!entity && !title) return null;
  if (!entity) {
    return {
      id: Math.max(0, ...data.favorites.map((item) => item.id)) + 1,
      target_type: type, target_id: targetId, title: title!, subtitle: "候选岗位",
      company: "AI 岗位洞察", location: "", salary: "", experience: "",
      education: "", skills: [], match: 0, savedAt: "刚刚",
      savedOrder: Date.now(), note: "",
    };
  }
  return {
    id: Math.max(0, ...data.favorites.map((item) => item.id)) + 1,
    target_type: type,
    target_id: targetId,
    title: title || ("name" in entity ? entity.name : entity.title),
    subtitle: "position" in entity ? entity.position : `${entity.level}岗位`,
    company: entity.company || entity.department || "",
    location: entity.location || "",
    salary: "resume_id" in entity ? entity.salary || "" : entity.salary_range,
    experience: entity.experience || "",
    education: entity.education || "",
    skills: "matched" in entity ? entity.matched : entity.skills || [],
    match: "resume_id" in entity ? entity.score : entity.match || 0,
    savedAt: "刚刚",
    savedOrder: Date.now(),
    note: "",
    urgent: entity.urgent,
  };
}

export const mockDataProvider: Omit<DataProvider, "jobs" | "trends" | "internalTransfer" | "skillReviews" | "admin"> = {
  dashboard: {
    async getOverview(query) {
      const data = db();
      const openJobs = data.jobs.filter((job) => job.status === "open");
      const hotJobs = data.jobs.slice(0, 12).map((job, index) => ({
        standard_job_id: job.id,
        title: job.title,
        demand: [243, 156, 187, 132, 108, 165][index] ?? 100,
        city: job.location || "全国",
        trend: [-5, 23, 8, 18, 15, -3][index] ?? 0,
        spark: [[260, 255, 250, 248, 245, 243], [30, 45, 62, 85, 110, 156], [140, 148, 155, 165, 175, 187], [40, 55, 68, 85, 108, 132], [35, 48, 60, 75, 92, 108], [170, 172, 168, 166, 164, 165]][index] ?? [0, 0, 0, 0, 0, 0],
        core_skills: (job.skills ?? []).slice(0, 5),
      }));
      const hotJobsPage = query?.hotJobsPage || 1;
      const hotJobsPageSize = query?.hotJobsPageSize || 10;
      const emergingPage = query?.emergingPage || 1;
      const emergingPageSize = query?.emergingPageSize || 10;
      const hotJobsSlice = hotJobs.slice(
        (hotJobsPage - 1) * hotJobsPageSize,
        (hotJobsPage - 1) * hotJobsPageSize + hotJobsPageSize,
      );
      const emergingSkills: DashboardOverview["emergingSkills"] = [
        { id: 1, name: "LangChain", combo: "AI 应用开发", growth: 12, confidence: 87 },
        { id: 2, name: "RAG", combo: "AI 应用开发", growth: 9, confidence: 82 },
        { id: 3, name: "向量数据库", combo: "数据工程", growth: 7, confidence: 78 },
      ];
      const emergingSlice = emergingSkills.slice(
        (emergingPage - 1) * emergingPageSize,
        (emergingPage - 1) * emergingPageSize + emergingPageSize,
      );
      return delay({
        heroCards: [
          { value: String(openJobs.length), label: "在招岗位", change: "+12.5%", up: true, color: "brand", action: "发布岗位", link: "/jobs" },
          { value: String(data.talents.filter((talent) => talent.urgent).length), label: "高优待处理", change: "+8.3%", up: true, color: "green", action: "上传简历", link: "/matching" },
          { value: "347", label: "本周新发岗位", change: "-2.1%", up: false, color: "amber", action: "岗位洞察", link: "/jobs" },
          { value: "3", label: "长期未跟进", change: "-1", up: false, color: "rose", action: "联系人才", link: "/matching" },
        ],
        kanban: openJobs.slice(0, 3).map((job, index) => {
          const high = [12, 6, 3][index] || 3;
          const progress = [8, 4, 2][index] || 2;
          const gap = [5, 2, 1][index] || 1;
          const pending = [3, 2, 2][index] || 2;
          const total = high + progress + gap + pending;
          return {
            job_id: job.id,
            title: job.title,
            department: job.department,
            location: job.location || "地点待确认",
            headcount: 2,
            urgent: Boolean(job.urgent),
            skills: (job.skills ?? []).slice(0, 5),
            total,
            evaluated: total - pending,
            pending,
            coverage: Math.round((total - pending) / total * 100),
            stages: [
              { name: "高匹配", kind: "high" as const, count: high },
              { name: "可推进", kind: "progress" as const, count: progress },
              { name: "待补强", kind: "gap" as const, count: gap },
              { name: "待评估", kind: "pending" as const, count: pending },
            ],
          };
        }),
        highMatches: [...data.talents].sort((a,b)=>b.score-a.score).slice(0,6),
        hotJobs: hotJobsSlice,
        hotJobsTotal: hotJobs.length,
        emergingSkills: emergingSlice,
        emergingSkillsTotal: emergingSkills.length,
      });
    },
  },
  talents: {
    async list(){return delay(db().talents);},
    async get(resumeId){return delay(db().talents.find((item)=>item.resume_id===resumeId)||null);},
    async getDetails(){throw new Error("简历详情仅支持后端数据模式");},
    async upload(){throw new Error("简历上传仅支持后端数据模式");},
    async download(){throw new Error("简历下载仅支持后端数据模式");},
    async preview(){throw new Error("简历预览仅支持后端数据模式");},
    async matchJobs(){throw new Error("岗位匹配仅支持后端数据模式");},
    async recalculate(){return delay({resumes_processed:db().talents.length,matches_upserted:0});},
    async explain(){throw new Error("匹配解释仅支持后端数据模式");},
  },
  career: {
    async analyze(input) {
      const internal=input.enterpriseJobs;
      const rows: CareerRecommendation[] = [
        {rank:1,job_id:4,job:"AI 大模型应用工程师",recommendScore:94,currentMatch:68,afterMatch:91,existing:["Java","Python基础","Spring Boot","MySQL","Redis"],learningPlan:[{skill:"PyTorch 基础",time:"4 周",difficulty:"medium",resources:["官方教程","动手学深度学习"]},{skill:"LangChain 框架",time:"2 周",difficulty:"easy",resources:["官方文档","实战教程"]}],suggestedProject:"构建内部智能知识库问答系统",totalTime:"6-8 周",internal:internal.some((job)=>job.includes("AI"))},
        {rank:2,job_id:8,job:"大数据开发工程师",recommendScore:87,currentMatch:55,afterMatch:87,existing:["Java","Python","SQL","MySQL"],learningPlan:[{skill:"Spark 核心开发",time:"3 周",difficulty:"medium",resources:["Spark权威指南"]}],suggestedProject:"将离线报表迁移为实时数据看板",totalTime:"6-10 周",internal:internal.some((job)=>job.includes("数据"))},
        {rank:3,job_id:9,job:"DevOps 工程师",recommendScore:82,currentMatch:48,afterMatch:84,existing:["Linux","Shell","Git","Docker基础"],learningPlan:[{skill:"Kubernetes 实战",time:"4 周",difficulty:"hard",resources:["K8s官方教程"]}],suggestedProject:"搭建自动化 CI/CD 流水线",totalTime:"5-7 周",internal:internal.some((job)=>job.includes("DevOps"))},
      ];
      return delay({
        recommendations: rows.sort((a,b)=>Number(b.internal)-Number(a.internal)||b.recommendScore-a.recommendScore),
        agentRunId: "mock-career-run", agentStatus: "succeeded" as const, warnings: [],
      },300);
    },
    async recover(){return null;},
  },
  graph: {
    async getOverview(query){
      const graph=structuredClone(db().graph),text=query?.keyword?.trim().toLowerCase();
      const nodes=graph.nodes.filter(node=>
        ["Job","SkillArea","TechStack"].includes(node.type)&&
        (!query?.stack||node.stack===query.stack)&&(!query?.level||node.level===query.level)&&
        (!text||`${node.name} ${node.description}`.toLowerCase().includes(text))
      );
      const ids=new Set(nodes.map(node=>node.id));
      return delay({nodes,edges:graph.edges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target)),has_more:false,next_cursor:null});
    },
    async getNeighbors(nodeId){
      const graph=structuredClone(db().graph),ids=new Set([nodeId]);
      graph.edges.forEach(edge=>{if(edge.source===nodeId)ids.add(edge.target);if(edge.target===nodeId)ids.add(edge.source);});
      return delay({nodes:graph.nodes.filter(node=>ids.has(node.id)),edges:graph.edges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target)),has_more:false,next_cursor:null});
    },
    async getPanorama(query){
      const graph=structuredClone(db().graph);
      if(!query)return delay(graph);
      const text=query.keyword?.trim().toLowerCase();
      const nodes=graph.nodes.filter(node=>
        (!query.stack||node.stack===query.stack)&&
        (!query.level||node.level===query.level)&&
        (!query.nodeType||node.type===query.nodeType)&&
        (!text||`${node.name} ${node.description}`.toLowerCase().includes(text))
      );
      const ids=new Set(nodes.map(node=>node.id));
      return delay({nodes,edges:graph.edges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target))});
    },
    async getNode(nodeId){
      const graph=structuredClone(db().graph),ids=new Set([nodeId]);
      graph.edges.forEach(edge=>{if(edge.source===nodeId)ids.add(edge.target);if(edge.target===nodeId)ids.add(edge.source);});
      return delay({nodes:graph.nodes.filter(node=>ids.has(node.id)),edges:graph.edges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target))});
    },
    async expand(){return delay(db().graph);},
    async search(query,type){
      const graph=structuredClone(db().graph),text=query.toLowerCase();
      const nodes=graph.nodes.filter(node=>(!type||node.type===type)&&`${node.name} ${node.description}`.toLowerCase().includes(text));
      const ids=new Set(nodes.map(node=>node.id));
      return delay({nodes,edges:graph.edges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target))});
    },
    async path(fromId,toId){
      const graph=structuredClone(db().graph),ids=new Set([fromId,toId]);
      return delay({nodes:graph.nodes.filter(node=>ids.has(node.id)),edges:graph.edges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target))});
    },
    async sync(){throw new Error("图谱同步仅支持后端数据模式");},
    async generateEnrichment(){throw new Error("L4/L5 候选生成仅支持后端数据模式");},
    async startSync(){throw new Error("图谱同步仅支持后端数据模式");},
    async startEnrichment(){throw new Error("L4/L5 候选生成仅支持后端数据模式");},
    async startPublication(){throw new Error("候选发布仅支持后端数据模式");},
    async getTask(){throw new Error("异步任务查询仅支持后端数据模式");},
    async listEnrichment(){return delay({items:[],total:0,page:1,page_size:12});},
    async reviewEnrichment(){throw new Error("候选审核仅支持后端数据模式");},
    async publishEnrichment(){throw new Error("候选发布仅支持后端数据模式");},
  },
  favorites: {
    async list(){return delay(db().favorites);},
    async toggle(type,targetId,title){const data=db(); const index=data.favorites.findIndex((item)=>item.target_type===type&&item.target_id===targetId); if(index>=0){data.favorites.splice(index,1);persist(data);return false;} const favorite=favoriteFromEntity(type,targetId,title);if(!favorite)return false;data.favorites.unshift(favorite);persist(data);return true;},
    async removeMany(ids){const data=db();data.favorites=data.favorites.filter((item)=>!ids.includes(item.id));persist(data);},
    async updateNote(id,note){const data=db();const favorite=data.favorites.find((item)=>item.id===id);if(favorite)favorite.note=note;persist(data);},
  },
  history: {
    async list(){return delay(db().history);},
    async record(input){const data=db();const now=new Date();const record={...input,id:Math.max(0,...data.history.map(item=>item.id))+1,dateKey:"today" as const,date:now.toISOString().slice(0,10),time:now.toTimeString().slice(0,5)};data.history.unshift(record);persist(data);return delay(record);},
    async remove(id){const data=db();data.history=data.history.filter((item)=>item.id!==id);persist(data);},
    async clear(){const data=db();data.history=[];persist(data);},
    async getInsights(){const data=db();return delay({focusStats:[{label:"AI / 大模型",percent:88,count:12},{label:"后端开发",percent:72,count:9},{label:"云原生",percent:48,count:6}],frequentRecords:data.history.slice(0,3).map((item,index)=>({history_id:item.id,count:5-index}))});},
  },
};
