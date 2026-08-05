import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type {
  AdminOverview,
  AdminResourceSnapshot,
  AgentRunAudit,
  AgentRunStatus,
  DataQualityPage,
  DataQualityQuery,
} from "@/domain/types";

export const useAdminStore=defineStore("admin",()=>{
  const data=ref<AdminOverview|null>(null),loading=ref(false),loaded=ref(false),error=ref("");
  const agentRuns=ref<AgentRunAudit[]>([]),agentRunsLoading=ref(false),agentRunsTotal=ref(0);
  const agentRunPage=ref(1),agentRunPageSize=ref(10);
  const agentRunStatus=ref<AgentRunStatus|undefined>(),agentRunType=ref("");
  const qualityPage=ref<DataQualityPage|null>(null),qualityLoading=ref(false),qualityError=ref("");
  async function load(force=false){if(loaded.value&&!force)return;loading.value=true;error.value="";try{data.value=await dataProvider.admin.getOverview();loaded.value=true;}catch(e){error.value=e instanceof Error?e.message:"加载失败";}finally{loading.value=false;}}
  async function refreshResources():Promise<AdminResourceSnapshot>{
    const snapshot=await dataProvider.admin.getResources();
    if(data.value){
      data.value={...data.value,resources:snapshot.resources,traffic:snapshot.traffic};
    }
    return snapshot;
  }
  async function loadQuality(query:DataQualityQuery){
    qualityLoading.value=true;qualityError.value="";
    try{qualityPage.value=await dataProvider.admin.listQuality(query);}
    catch(e){qualityError.value=e instanceof Error?e.message:"数据质量记录加载失败";}
    finally{qualityLoading.value=false;}
  }
  async function decideQuality(id:number,action:"exclude"|"restore",reason?:string){
    await dataProvider.admin.decideQuality(id,action,reason);
  }
  async function toggleCrawler(id:number){await dataProvider.admin.toggleCrawler(id);await load(true);}
  async function runCrawler(id:number){await dataProvider.admin.runCrawler(id);await load(true);}
  async function pollCrawler(id:number){return dataProvider.admin.pollCrawler(id);}
  async function importCrawlerOutput(filename:string){return dataProvider.admin.importCrawlerOutput(filename);}
  async function loadAgentRuns(){
    agentRunsLoading.value=true;
    try{
      const result=await dataProvider.admin.listAgentRuns({
        page:agentRunPage.value,pageSize:agentRunPageSize.value,
        status:agentRunStatus.value,agentType:agentRunType.value||undefined,
      });
      agentRuns.value=result.items;agentRunsTotal.value=result.total;
    }finally{agentRunsLoading.value=false;}
  }
  return {
    data,loading,loaded,error,qualityPage,qualityLoading,qualityError,
    load,refresh:()=>load(true),loadQuality,decideQuality,toggleCrawler,runCrawler,
    pollCrawler,importCrawlerOutput,agentRuns,agentRunsLoading,agentRunsTotal,
    agentRunPage,agentRunPageSize,agentRunStatus,agentRunType,loadAgentRuns,refreshResources,
  };
});
