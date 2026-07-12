import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type { CareerRecommendation } from "@/domain/types";

export const useCareerStore=defineStore("career",()=>{
  const data=ref<CareerRecommendation[]>([]),loading=ref(false),loaded=ref(false),error=ref("");
  const warnings=ref<string[]>([]),agentStatus=ref(""),agentRunId=ref("");
  async function analyze(input:{skillText:string;enterpriseTech:string;enterpriseJobs:string[];resumeFiles?:File[];enterpriseFiles?:File[]}){
    if(loading.value)return;
    loading.value=true;error.value="";warnings.value=[];
    try{const result=await dataProvider.career.analyze(input);data.value=result.recommendations;warnings.value=result.warnings;agentStatus.value=result.agentStatus;agentRunId.value=result.agentRunId;loaded.value=true;}
    catch(e){error.value=e instanceof Error?e.message:"分析失败";}finally{loading.value=false;}
  }
  return {data,loading,loaded,error,warnings,agentStatus,agentRunId,analyze,refresh:()=>Promise.resolve()};
});
