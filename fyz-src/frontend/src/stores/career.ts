import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type { CareerRecommendation } from "@/domain/types";

export const useCareerStore=defineStore("career",()=>{
  const data=ref<CareerRecommendation[]>([]),loading=ref(false),loaded=ref(false),error=ref("");
  async function analyze(input:{skillText:string;enterpriseTech:string;enterpriseJobs:string[];resumeFiles?:File[];enterpriseFiles?:File[]}){loading.value=true;error.value="";try{data.value=await dataProvider.career.analyze(input);loaded.value=true;}catch(e){error.value=e instanceof Error?e.message:"分析失败";}finally{loading.value=false;}}
  return {data,loading,loaded,error,analyze,refresh:()=>Promise.resolve()};
});
