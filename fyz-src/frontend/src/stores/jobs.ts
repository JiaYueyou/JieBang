import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type {
  AnalysisDataQuality,
  CapabilityChange,
  EmergingJob,
  GeneratedJDDraft,
  GenerateJDRequest,
  JDInputSuggestion,
  JDInputSuggestionRequest,
  JobCreatePayload,
  JobSummary,
  InternalPosition,
  InternalPositionCreate,
} from "@/domain/types";

export const useJobStore = defineStore("jobs", () => {
  const jobs = ref<JobSummary[]>([]);
  const internalPositions = ref<InternalPosition[]>([]);
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
      const [publicResult, internalResult] = await Promise.allSettled([
        dataProvider.jobs.list(),
        dataProvider.internalTransfer.listPositions(),
      ]);
      if (publicResult.status === "fulfilled") jobs.value = publicResult.value;
      if (internalResult.status === "fulfilled") internalPositions.value = internalResult.value;
      if (publicResult.status === "rejected" && internalResult.status === "rejected") {
        throw publicResult.reason;
      }
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

  async function suggestJDInput(input: JDInputSuggestionRequest): Promise<JDInputSuggestion> {
    return dataProvider.jobs.suggestJDInput(input);
  }

  async function create(job: JobCreatePayload) {
    const saved = await dataProvider.jobs.create(job);
    jobs.value.unshift(saved);
    return saved;
  }

  async function createInternalPosition(input: InternalPositionCreate) {
    const saved = await dataProvider.internalTransfer.createPosition(input);
    internalPositions.value.unshift(saved);
    return saved;
  }

  async function updateInternalPositionStatus(id: number, status: InternalPosition["status"]) {
    const saved = await dataProvider.internalTransfer.updatePositionStatus(id, status);
    const index = internalPositions.value.findIndex((position) => position.id === id);
    if (index >= 0) internalPositions.value[index] = saved;
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
    internalPositions,
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
    suggestJDInput,
    generateJD,
    create,
    createInternalPosition,
    updateInternalPositionStatus,
    update,
    remove,
    updateStatus,
  };
});
