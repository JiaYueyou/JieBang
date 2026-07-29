import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type { AdminOverview } from "@/domain/types";

export const useAdminStore=defineStore("admin",()=>{
  const data=ref<AdminOverview|null>(null),loading=ref(false),loaded=ref(false),error=ref("");
  async function load(force=false){if(loaded.value&&!force)return;loading.value=true;error.value="";try{data.value=await dataProvider.admin.getOverview();loaded.value=true;}catch(e){error.value=e instanceof Error?e.message:"加载失败";}finally{loading.value=false;}}
  async function toggleCrawler(id:number){await dataProvider.admin.toggleCrawler(id);await load(true);}
  async function runCrawler(id:number){await dataProvider.admin.runCrawler(id);await load(true);}
  async function pollCrawler(id:number){return dataProvider.admin.pollCrawler(id);}
  async function importCrawlerOutput(filename:string){return dataProvider.admin.importCrawlerOutput(filename);}
  async function toggleUser(id:number){await dataProvider.admin.toggleUser(id);await load(true);}
  async function saveSettings(settings:Record<string,any>){await dataProvider.admin.saveSettings(settings);await load(true);}
  return {data,loading,loaded,error,load,refresh:()=>load(true),toggleCrawler,runCrawler,pollCrawler,importCrawlerOutput,toggleUser,saveSettings};
});
