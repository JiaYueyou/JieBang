import type { DataProvider } from "./provider";
import { loadMockDatabase, saveMockDatabase } from "./mockDatabase";
import type { CareerRecommendation, FavoriteRecord, FavoriteTargetType, JobSummary, TalentSummary } from "@/domain/types";

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

export const mockDataProvider: Omit<DataProvider, "jobs" | "trends" | "internalTransfer"> = {
  dashboard: {
    async getOverview() {
      const data = db();
      const openJobs = data.jobs.filter((job) => job.status === "open");
      return delay({
        heroCards: [
          { value: String(openJobs.length), label: "在招岗位", change: "+12.5%", up: true, color: "brand", action: "发布岗位", link: "/jobs" },
          { value: String(data.talents.filter((talent) => talent.urgent).length), label: "高优待处理", change: "+8.3%", up: true, color: "green", action: "上传简历", link: "/matching" },
          { value: "347", label: "本周新发岗位", change: "-2.1%", up: false, color: "amber", action: "岗位洞察", link: "/jobs" },
          { value: "3", label: "长期未跟进", change: "-1", up: false, color: "rose", action: "联系人才", link: "/matching" },
        ],
        kanban: openJobs.slice(0, 3).map((job, index) => ({ job_id: job.id, title: job.title, total: [28,14,8][index] || 8, stages: [{ name:"筛选",count:[12,10,5][index]||5},{name:"面试",count:[3,1,0][index]||0},{name:"发放",count:index===0?1:0},{name:"入职",count:0}] })),
        highMatches: [...data.talents].sort((a,b)=>b.score-a.score).slice(0,6),
        hotJobs: data.jobs.slice(0,6).map((job,index)=>({job_id:job.id,title:job.title,demand:[243,156,187,132,108,165][index],city:job.location||"全国",trend:[-5,23,8,18,15,-3][index],spark:[[260,255,250,248,245,243],[30,45,62,85,110,156],[140,148,155,165,175,187],[40,55,68,85,108,132],[35,48,60,75,92,108],[170,172,168,166,164,165]][index]})),
        emergingSkills: [],
      });
    },
  },
  talents: {
    async list(){return delay(db().talents);},
    async get(resumeId){return delay(db().talents.find((item)=>item.resume_id===resumeId)||null);},
    async upload(){throw new Error("简历上传仅支持后端数据模式");},
    async download(){throw new Error("简历下载仅支持后端数据模式");},
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
  },
  graph: {
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
  },
  favorites: {
    async list(){return delay(db().favorites);},
    async toggle(type,targetId,title){const data=db(); const index=data.favorites.findIndex((item)=>item.target_type===type&&item.target_id===targetId); if(index>=0){data.favorites.splice(index,1);persist(data);return false;} const favorite=favoriteFromEntity(type,targetId,title);if(!favorite)return false;data.favorites.unshift(favorite);persist(data);return true;},
    async removeMany(ids){const data=db();data.favorites=data.favorites.filter((item)=>!ids.includes(item.id));persist(data);},
    async updateNote(id,note){const data=db();const favorite=data.favorites.find((item)=>item.id===id);if(favorite)favorite.note=note;persist(data);},
  },
  history: {
    async list(){return delay(db().history);},
    async remove(id){const data=db();data.history=data.history.filter((item)=>item.id!==id);persist(data);},
    async clear(){const data=db();data.history=[];persist(data);},
    async getInsights(){const data=db();return delay({focusStats:[{label:"AI / 大模型",percent:88,count:12},{label:"后端开发",percent:72,count:9},{label:"云原生",percent:48,count:6}],frequentRecords:data.history.slice(0,3).map((item,index)=>({history_id:item.id,count:5-index}))});},
  },
  admin: {
    async getOverview(){return delay(db().admin);},
    async toggleCrawler(id){const data=db();const item=data.admin.crawlers.find((value)=>value.id===id);if(item)item.enabled=!item.enabled;persist(data);},
    async runCrawler(id){const data=db();const item=data.admin.crawlers.find((value)=>value.id===id);if(item){item.running=true;item.progress=8;item.nextRun="运行中";}persist(data);},
    async pollCrawler(){return {done:true,result:null};},
    async importCrawlerOutput(filename){return delay({files:[filename],total:0,imported:0,duplicates:0,skill_facts:0,verified_skill_facts:0,unverified_skill_facts:0,validation:[{file:filename,total:0,passed:0,failed:0,errors:[],warning_count:0,warnings:[]}]});},
    async toggleUser(id){const data=db();const user=data.admin.users.find((value)=>value.id===id);if(user)user.status=user.status==="active"?"disabled":"active";persist(data);},
    async saveSettings(settings){const data=db();data.admin.settings={...settings};persist(data);},
  },
};
