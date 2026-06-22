import type { DataProvider } from "./provider";
import { httpDataProvider } from "./httpProvider";
import { mockDataProvider } from "./mockProvider";

export const providerMode =
  import.meta.env.VITE_DATA_PROVIDER === "http"
    ? "http"
    : import.meta.env.VITE_DATA_PROVIDER === "hybrid"
      ? "hybrid"
      : "mock";

const hybridDataProvider: DataProvider = {
  ...mockDataProvider,
  jobs: {
    ...httpDataProvider.jobs,
    // 第一阶段联调：CRUD 使用真实 MySQL，Agent 与洞察仍使用统一 Mock。
    generateJD: mockDataProvider.jobs.generateJD,
    getInsights: mockDataProvider.jobs.getInsights,
  },
  graph: httpDataProvider.graph,
};

export const dataProvider: DataProvider =
  providerMode === "http"
    ? httpDataProvider
    : providerMode === "hybrid"
      ? hybridDataProvider
      : mockDataProvider;
