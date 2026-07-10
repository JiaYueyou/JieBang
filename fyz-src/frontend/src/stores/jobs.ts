import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type {
  AnalysisDataQuality,
  CapabilityChange,
  EmergingJob,
  GeneratedJDDraft,
  GenerateJDRequest,
  JobCreatePayload,
  JobSummary,
} from "@/domain/types";

export const useJobStore = defineStore("jobs", () => {
  const jobs = ref<JobSummary[]>([]);
  const emergingJobs = ref<EmergingJob[]>([]);
  const capabilityChanges = ref<CapabilityChange[]>([]);
  const insightQuality = ref<AnalysisDataQuality | null>(null);
  const insightLoading = ref(false);
  const insightError = ref("");
  const loading = ref(false);
  const loaded = ref(false);
  const error = ref("");

  async function load(force = false) {
    if (loaded.value && !force) return;
    loading.value = true;
    error.value = "";
    try {
      jobs.value = await dataProvider.jobs.list();
      loaded.value = true;
    } catch (exception) {
      error.value = exception instanceof Error ? exception.message : "加载失败";
    } finally {
      loading.value = false;
    }
  }

  async function loadInsights(skill = "") {
    insightLoading.value = true;
    insightError.value = "";
    try {
      const result = await dataProvider.jobs.getInsights(skill);
      emergingJobs.value = result.emergingJobs;
      capabilityChanges.value = result.capabilityChanges;
      insightQuality.value = result.dataQuality;
    } catch (exception) {
      insightError.value = exception instanceof Error ? exception.message : "洞察加载失败";
    } finally {
      insightLoading.value = false;
    }
  }

  async function decideInsight(
    id: number,
    decision: "confirmed" | "ignored" | "planned",
    note?: string,
  ) {
    await dataProvider.jobs.decideInsight(id, decision, note);
    const item = emergingJobs.value.find((job) => job.id === id);
    if (item) item.decision = decision;
  }

  async function generateJD(input: GenerateJDRequest): Promise<GeneratedJDDraft> {
    return dataProvider.jobs.generateJD(input);
  }

  async function create(job: JobCreatePayload) {
    const saved = await dataProvider.jobs.create(job);
    jobs.value.unshift(saved);
    return saved;
  }

  async function update(job: JobSummary) {
    const saved = await dataProvider.jobs.update(job);
    const index = jobs.value.findIndex((value) => value.id === saved.id);
    if (index >= 0) jobs.value[index] = saved;
  }

  async function remove(id: number) {
    await dataProvider.jobs.remove(id);
    jobs.value = jobs.value.filter((job) => job.id !== id);
  }

  async function updateStatus(id: number, status: JobSummary["status"]) {
    const saved = await dataProvider.jobs.updateStatus(id, status);
    const index = jobs.value.findIndex((job) => job.id === id);
    if (index >= 0) jobs.value[index] = saved;
  }

  return {
    jobs,
    emergingJobs,
    capabilityChanges,
    insightQuality,
    insightLoading,
    insightError,
    loading,
    loaded,
    error,
    load,
    loadInsights,
    decideInsight,
    refresh: () => load(true),
    generateJD,
    create,
    update,
    remove,
    updateStatus,
  };
});
