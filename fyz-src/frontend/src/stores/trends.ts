import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type { TrendOverview, TrendQuery } from "@/domain/types";

export const useTrendStore = defineStore("trends", () => {
  const data = ref<TrendOverview | null>(null);
  const loading = ref(false);
  const error = ref("");
  const lastQuery = ref<TrendQuery>({ months: 12 });

  async function load(query: TrendQuery = lastQuery.value) {
    loading.value = true;
    error.value = "";
    lastQuery.value = { ...query };
    try {
      data.value = await dataProvider.trends.getOverview(query);
    } catch (exception) {
      error.value = exception instanceof Error ? exception.message : "加载失败";
    } finally {
      loading.value = false;
    }
  }

  return {
    data,
    loading,
    error,
    load,
    refresh: () => load(lastQuery.value),
  };
});
