import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type { DashboardOverview } from "@/domain/types";

export const useDashboardStore = defineStore("dashboard", () => {
  const data = ref<DashboardOverview | null>(null);
  const loading = ref(false); const loaded = ref(false); const error = ref("");
  async function load(force=false){if(loaded.value&&!force)return;loading.value=true;error.value="";try{data.value=await dataProvider.dashboard.getOverview();loaded.value=true;}catch(e){error.value=e instanceof Error?e.message:"加载失败";}finally{loading.value=false;}}
  const refresh=()=>load(true);
  return {data,loading,loaded,error,load,refresh};
});
