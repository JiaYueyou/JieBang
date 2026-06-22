import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type { TalentSummary } from "@/domain/types";

export const useTalentStore=defineStore("talents",()=>{
  const talents=ref<TalentSummary[]>([]),loading=ref(false),loaded=ref(false),error=ref("");
  async function load(force=false){if(loaded.value&&!force)return;loading.value=true;error.value="";try{talents.value=await dataProvider.talents.list();loaded.value=true;}catch(e){error.value=e instanceof Error?e.message:"加载失败";}finally{loading.value=false;}}
  async function getByResumeId(id:number){const cached=talents.value.find(v=>v.resume_id===id);return cached||dataProvider.talents.get(id);}
  return {talents,loading,loaded,error,load,refresh:()=>load(true),getByResumeId};
});
