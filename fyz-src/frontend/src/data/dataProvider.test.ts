import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import request from "@/api/request";
import { dataProvider, providerMode } from "@/data";
import { loadMockDatabase, MOCK_DB_KEY, resetMockDatabase } from "./mockDatabase";
import { mockDataProvider } from "./mockProvider";
import { useDashboardStore } from "@/stores/dashboard";
import { useFavoriteStore } from "@/stores/favorites";

const dashboardOverview = {
  heroCards: [],
  kanban: [],
  highMatches: [],
  hotJobs: [],
  emergingSkills: [],
};

describe("unified mock data provider", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    resetMockDatabase();
    setActivePinia(createPinia());
  });

  it("resets invalid or outdated persisted data to the fixed v1 seed", () => {
    localStorage.setItem(MOCK_DB_KEY, JSON.stringify({ version: 0, jobs: [] }));
    const database = loadMockDatabase();
    expect(database.version).toBe(1);
    expect(database.jobs.length).toBeGreaterThan(0);
  });

  it("migrates legacy job names and talent ids to stable job/resume ids", () => {
    localStorage.removeItem(MOCK_DB_KEY);
    localStorage.setItem("jiebang:favorites", JSON.stringify([
      { type: "job", targetId: "Java 高级开发工程师", title: "Java 高级开发工程师", createdAt: "2026-06-20T00:00:00Z" },
      { type: "talent", targetId: "2", title: "王语晴", createdAt: "2026-06-20T00:00:00Z" },
    ]));

    const database = loadMockDatabase();
    expect(database.favorites).toEqual(expect.arrayContaining([
      expect.objectContaining({ target_type: "job", target_id: 1 }),
      expect.objectContaining({ target_type: "resume", target_id: 2 }),
    ]));
    expect(localStorage.getItem("jiebang:favorites")).toBeNull();
    expect(database.favorites.every((item) => item.target_type !== ("talent" as never))).toBe(true);
  });

  it("builds dashboard talent data from the same normalized talent entities", async () => {
    const [overview, talents] = await Promise.all([
      mockDataProvider.dashboard.getOverview(),
      mockDataProvider.talents.list(),
    ]);
    expect(overview.highMatches[0]).toEqual(
      [...talents].sort((a, b) => b.score - a.score)[0],
    );
  });

  it("keeps favorites unique and persists batch removal and notes", async () => {
    await mockDataProvider.favorites.toggle("job", 1);
    let favorites = await mockDataProvider.favorites.list();
    expect(favorites.filter((item) => item.target_type === "job" && item.target_id === 1)).toHaveLength(1);

    const favorite = favorites.find((item) => item.target_type === "job" && item.target_id === 1)!;
    await mockDataProvider.favorites.updateNote(favorite.id, "安排技术面");
    expect((await mockDataProvider.favorites.list()).find((item) => item.id === favorite.id)?.note).toBe("安排技术面");

    await mockDataProvider.favorites.removeMany([favorite.id]);
    favorites = await mockDataProvider.favorites.list();
    expect(favorites.some((item) => item.id === favorite.id)).toBe(false);
    expect(loadMockDatabase().favorites.some((item) => item.id === favorite.id)).toBe(false);
  });

  it("synchronizes favorite button state and list through one Pinia store", async () => {
    const favorite = {
      id: 8, target_type: "job" as const, target_id: 1, title: "Java 高级开发工程师",
      subtitle: "研发中心", company: "示例企业", location: "合肥", salary: "25K-40K",
      experience: "5年", education: "本科", skills: ["Java"], match: 90,
      savedAt: "2026-07-30T10:00:00", savedOrder: 1785405600, note: "",
    };
    vi.spyOn(request, "get")
      .mockResolvedValueOnce({ data: { code: 200, message: "success", data: [], meta: null } } as never)
      .mockResolvedValueOnce({ data: { code: 200, message: "success", data: [favorite], meta: null } } as never);
    vi.spyOn(request, "post").mockResolvedValue({
      data: { code: 200, message: "已收藏", data: { active: true }, meta: null },
    } as never);
    const store = useFavoriteStore();
    await store.load();
    expect(store.isFavorite("job", 1)).toBe(false);
    await store.toggle("job", 1);
    expect(store.isFavorite("job", 1)).toBe(true);
    expect(store.records.some((item) => item.target_type === "job" && item.target_id === 1)).toBe(true);
  });

  it("deletes and clears history in memory and persisted storage", async () => {
    const records = await mockDataProvider.history.list();
    await mockDataProvider.history.remove(records[0].id);
    expect((await mockDataProvider.history.list()).some((item) => item.id === records[0].id)).toBe(false);
    await mockDataProvider.history.clear();
    expect(await mockDataProvider.history.list()).toEqual([]);
    expect(loadMockDatabase().history).toEqual([]);
  });

  it("always uses the real dashboard HTTP endpoint at runtime", async () => {
    const getSpy = vi.spyOn(request, "get").mockResolvedValue({
      data: { code: 200, message: "success", data: dashboardOverview, meta: null },
    } as never);
    expect(providerMode).toBe("http");
    await expect(dataProvider.dashboard.getOverview()).resolves.toEqual(dashboardOverview);
    expect(getSpy).toHaveBeenCalledWith("/dashboard/overview", { params: undefined });
  });

  it("always loads admin monitoring from the real backend even in mock mode", async () => {
    const overview = {
      metrics: [], services: [], resources: [], recentTasks: [], systemEvents: [],
      crawlers: [], pipelineSummary: {
        totalJobs: 0, todayImported: 0, sourceCount: 0, validRecords: 0,
        validRate: 0, failedTasks: 0, processedToday: 0, duplicatesToday: 0,
        verifiedFacts: 0, unverifiedFacts: 0, overallQuality: 0,
      },
      qualities: [], crawlerPolicy: {
        concurrency: 4, retries: 3, interval: 5, deduplicate: true,
      },
      performanceCards: [], endpoints: [], logs: [],
    };
    const getSpy = vi.spyOn(request, "get").mockResolvedValue({
      data: { code: 200, message: "success", data: overview, meta: null },
    } as never);

    await expect(dataProvider.admin.getOverview()).resolves.toEqual(overview);
    expect(getSpy).toHaveBeenCalledWith("/admin/overview", { params: undefined });
  });

  it("tracks loading, loaded, refresh, and duplicate load behavior", async () => {
    const store = useDashboardStore();
    const spy = vi.spyOn(dataProvider.dashboard, "getOverview").mockResolvedValue(dashboardOverview);
    const firstLoad = store.load();
    expect(store.loading).toBe(true);
    await firstLoad;
    expect(store.loading).toBe(false);
    expect(store.loaded).toBe(true);
    await store.load();
    expect(spy).toHaveBeenCalledTimes(1);
    await store.refresh();
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it("exposes provider errors and recovers on refresh", async () => {
    const store = useDashboardStore();
    vi.spyOn(dataProvider.dashboard, "getOverview")
      .mockRejectedValueOnce(new Error("服务暂不可用"))
      .mockResolvedValueOnce(dashboardOverview);
    await store.load();
    expect(store.loaded).toBe(false);
    expect(store.error).toBe("服务暂不可用");
    await store.refresh();
    expect(store.loaded).toBe(true);
    expect(store.error).toBe("");
  });
});
