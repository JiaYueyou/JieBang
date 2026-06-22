import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import request from "@/api/request";
import { dataProvider, providerMode } from "@/data";
import { loadMockDatabase, MOCK_DB_KEY, resetMockDatabase } from "./mockDatabase";
import { mockDataProvider } from "./mockProvider";
import { useDashboardStore } from "@/stores/dashboard";
import { useFavoriteStore } from "@/stores/favorites";

describe("unified mock data provider", () => {
  beforeEach(() => {
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

  it("propagates a job edit to dashboard aggregates and favorite details", async () => {
    const jobs = await mockDataProvider.jobs.list();
    const edited = { ...jobs.find((job) => job.id === 4)!, title: "企业级 Agent 工程师" };
    await mockDataProvider.jobs.update(edited);

    const [overview, favorites] = await Promise.all([
      mockDataProvider.dashboard.getOverview(),
      mockDataProvider.favorites.list(),
    ]);
    expect(overview.hotJobs.find((job) => job.job_id === 4)?.title).toBe(edited.title);
    expect(favorites.find((item) => item.target_type === "job" && item.target_id === 4)?.title).toBe(edited.title);
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

  it("defaults to mock mode and does not issue business HTTP requests", async () => {
    const getSpy = vi.spyOn(request, "get");
    expect(providerMode).toBe("mock");
    await dataProvider.dashboard.getOverview();
    expect(getSpy).not.toHaveBeenCalled();
  });

  it("tracks loading, loaded, refresh, and duplicate load behavior", async () => {
    const store = useDashboardStore();
    const spy = vi.spyOn(dataProvider.dashboard, "getOverview");
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
      .mockRejectedValueOnce(new Error("服务暂不可用"));
    await store.load();
    expect(store.loaded).toBe(false);
    expect(store.error).toBe("服务暂不可用");
    await store.refresh();
    expect(store.loaded).toBe(true);
    expect(store.error).toBe("");
  });
});
