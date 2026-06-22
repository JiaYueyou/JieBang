import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type { TrendOverview } from "@/domain/types";

export const useTrendStore=defineStore("trends",()=>{
  const data=ref<TrendOverview|null>(null),loading=ref(false),loaded=ref(false),error=ref("");
  async function load(force=false){if(loaded.value&&!force)return;loading.value=true;error.value="";try{data.value=await dataProvider.trends.getOverview();loaded.value=true;}catch(e){error.value=e instanceof Error?e.message:"加载失败";}finally{loading.value=false;}}
  return {data,loading,loaded,error,load,refresh:()=>load(true)};
});
