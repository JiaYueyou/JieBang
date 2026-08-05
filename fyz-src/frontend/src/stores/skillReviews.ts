import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { dataProvider } from "@/data";
import type {
  SkillFactReviewItem,
  SkillFactReviewSummary,
  SkillFactVerificationStatus,
} from "@/domain/types";

export const useSkillReviewsStore = defineStore("skill-reviews", () => {
  const items = ref<SkillFactReviewItem[]>([]);
  const summary = ref<SkillFactReviewSummary>({
    all: 0,
    unverified: 0,
    verified: 0,
    rejected: 0,
  });
  const status = ref<SkillFactVerificationStatus | "all">("unverified");
  const keyword = ref("");
  const page = ref(1);
  const pageSize = ref(12);
  const total = ref(0);
  const totalPages = ref(0);
  const loading = ref(false);
  const error = ref("");

  const hasFilters = computed(() => status.value !== "unverified" || Boolean(keyword.value.trim()));

  async function load(resetPage = false) {
    if (resetPage) page.value = 1;
    loading.value = true;
    error.value = "";
    try {
      const result = await dataProvider.skillReviews.list({
        page: page.value,
        pageSize: pageSize.value,
        status: status.value === "all" ? undefined : status.value,
        keyword: keyword.value.trim() || undefined,
      });
      items.value = result.items;
      summary.value = result.summary;
      total.value = result.meta.total;
      totalPages.value = result.meta.total_pages;
    } catch (value) {
      error.value = value instanceof Error ? value.message : "技能事实加载失败";
    } finally {
      loading.value = false;
    }
  }

  async function review(
    item: SkillFactReviewItem,
    decision: "verified" | "rejected",
    note?: string,
  ) {
    await dataProvider.skillReviews.review(item.id, decision, note);
    await load();
  }

  async function reviewBatch(
    factIds: number[],
    decision: "verified" | "rejected",
    note?: string,
  ) {
    const result = await dataProvider.skillReviews.reviewBatch(factIds, decision, note);
    await load();
    return result;
  }

  async function approveAll() {
    const result = await dataProvider.skillReviews.approveAll(keyword.value.trim() || undefined);
    await load(true);
    return result;
  }

  function resetFilters() {
    status.value = "unverified";
    keyword.value = "";
    page.value = 1;
  }

  return {
    items,
    summary,
    status,
    keyword,
    page,
    pageSize,
    total,
    totalPages,
    loading,
    error,
    hasFilters,
    load,
    review,
    reviewBatch,
    approveAll,
    resetFilters,
  };
});
