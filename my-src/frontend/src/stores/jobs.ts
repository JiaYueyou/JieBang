import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type { CapabilityChange, EmergingJob, JobSummary } from "@/domain/types";

export const useJobStore=defineStore("jobs",()=>{
  const jobs=ref<JobSummary[]>([]),emergingJobs=ref<EmergingJob[]>([]),capabilityChanges=ref<CapabilityChange[]>([]);
  const loading=ref(false),loaded=ref(false),error=ref("");
  async function load(force=false){if(loaded.value&&!force)return;loading.value=true;error.value="";try{const [list,insights]=await Promise.all([dataProvider.jobs.list(),dataProvider.jobs.getInsights()]);jobs.value=list;emergingJobs.value=insights.emergingJobs;capabilityChanges.value=insights.capabilityChanges;loaded.value=true;}catch(e){error.value=e instanceof Error?e.message:"加载失败";}finally{loading.value=false;}}
  async function generateJD(input:Record<string,string>){return dataProvider.jobs.generateJD(input);}
  async function create(job:JobSummary){const saved=await dataProvider.jobs.create(job);jobs.value.unshift(saved);}
  async function update(job:JobSummary){const saved=await dataProvider.jobs.update(job);const i=jobs.value.findIndex(v=>v.id===saved.id);if(i>=0)jobs.value[i]=saved;}
  async function remove(id:number){await dataProvider.jobs.remove(id);jobs.value=jobs.value.filter(v=>v.id!==id);}
  async function updateStatus(id:number,status:JobSummary["status"]){const saved=await dataProvider.jobs.updateStatus(id,status);const index=jobs.value.findIndex(v=>v.id===id);if(index>=0)jobs.value[index]=saved;}
  return {jobs,emergingJobs,capabilityChanges,loading,loaded,error,load,refresh:()=>load(true),generateJD,create,update,remove,updateStatus};
});
