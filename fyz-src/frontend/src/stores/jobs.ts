import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type {
  AnalysisBaseline,
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
  ObservedJobDetail,
  ObservedJobSummary,
} from "@/domain/types";

export const useJobStore = defineStore("jobs", () => {
  const jobs = ref<JobSummary[]>([]);
  const publicTotal = ref(0);
  const internalPositions = ref<InternalPosition[]>([]);
  const internalTotal = ref(0);
  const emergingJobs = ref<EmergingJob[]>([]);
  const capabilityChanges = ref<CapabilityChange[]>([]);
  const insightQuality = ref<AnalysisDataQuality | null>(null);
  const insightBaseline = ref<AnalysisBaseline | null>(null);
  const insightLoading = ref(false);
  const insightError = ref("");
  const loading = ref(false);
  const loaded = ref(false);
  const error = ref("");
  const observedJobs = ref<ObservedJobSummary[]>([]);
  const observedTotal = ref(0);
  const observedLoading = ref(false);
  const observedError = ref("");

  async function loadPublic(query = { page: 1, pageSize: 6 } as {
    page: number;
    pageSize: number;
    status?: JobSummary["status"];
    keyword?: string;
  }) {
    const result = await dataProvider.jobs.list(query);
    jobs.value = result.items;
    publicTotal.value = result.total;
    return result;
  }

  async function loadInternal(query = { page: 1, pageSize: 6 } as {
    page: number;
    pageSize: number;
    status?: InternalPosition["status"];
    keyword?: string;
  }) {
    const result = await dataProvider.internalTransfer.listPositionsPage(query);
    internalPositions.value = result.items;
    internalTotal.value = result.total;
    return result;
  }

  async function load(force = false) {
    if (loaded.value && !force) return;
    loading.value = true;
    error.value = "";
    try {
      const [publicResult, internalResult] = await Promise.allSettled([
        loadPublic(),
        loadInternal(),
      ]);
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
      insightBaseline.value = result.baseline;
    } catch (exception) {
      insightError.value = exception instanceof Error ? exception.message : "洞察加载失败";
    } finally {
      insightLoading.value = false;
    }
  }

  async function loadObserved(query: {
    page: number;
    pageSize: number;
    keyword?: string;
    city?: string;
    source?: string;
  }) {
    observedLoading.value = true;
    observedError.value = "";
    try {
      const result = await dataProvider.jobs.listObserved(query);
      observedJobs.value = result.items;
      observedTotal.value = result.total;
      return result;
    } catch (exception) {
      observedError.value = exception instanceof Error ? exception.message : "采集岗位加载失败";
      throw exception;
    } finally {
      observedLoading.value = false;
    }
  }

  async function getObserved(id: number): Promise<ObservedJobDetail> {
    return dataProvider.jobs.getObserved(id);
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
    publicTotal.value += 1;
    return saved;
  }

  async function createInternalPosition(input: InternalPositionCreate) {
    const saved = await dataProvider.internalTransfer.createPosition(input);
    internalPositions.value.unshift(saved);
    internalTotal.value += 1;
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
    publicTotal.value = Math.max(0, publicTotal.value - 1);
  }

  async function updateStatus(id: number, status: JobSummary["status"]) {
    const saved = await dataProvider.jobs.updateStatus(id, status);
    const index = jobs.value.findIndex((job) => job.id === id);
    if (index >= 0) jobs.value[index] = saved;
  }

  return {
    jobs,
    publicTotal,
    internalPositions,
    internalTotal,
    emergingJobs,
    capabilityChanges,
    insightQuality,
    insightBaseline,
    insightLoading,
    insightError,
    loading,
    loaded,
    error,
    observedJobs,
    observedTotal,
    observedLoading,
    observedError,
    load,
    loadPublic,
    loadInternal,
    loadInsights,
    loadObserved,
    getObserved,
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
