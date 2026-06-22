import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type { HistoryInsights, HistoryRecord } from "@/domain/types";

export const useHistoryStore=defineStore("history",()=>{
  const records=ref<HistoryRecord[]>([]),insights=ref<HistoryInsights>({focusStats:[],frequentRecords:[]}),loading=ref(false),loaded=ref(false),error=ref("");
  async function load(force=false){if(loaded.value&&!force)return;loading.value=true;error.value="";try{[records.value,insights.value]=await Promise.all([dataProvider.history.list(),dataProvider.history.getInsights()]);loaded.value=true;}catch(e){error.value=e instanceof Error?e.message:"加载失败";}finally{loading.value=false;}}
  async function remove(id:number){await dataProvider.history.remove(id);records.value=records.value.filter(v=>v.id!==id);}
  async function clear(){await dataProvider.history.clear();records.value=[];}
  return {records,insights,loading,loaded,error,load,refresh:()=>load(true),remove,clear};
});
