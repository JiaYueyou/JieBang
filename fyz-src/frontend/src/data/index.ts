import type { DataProvider } from "./provider";
import { httpDataProvider } from "./httpProvider";
import { mockDataProvider } from "./mockProvider";

export const providerMode =
  import.meta.env.VITE_DATA_PROVIDER === "http"
    ? "http"
    : import.meta.env.VITE_DATA_PROVIDER === "hybrid"
      ? "hybrid"
      : "mock";

// 岗位 CRUD 和智能 JD Agent 不再使用任何本地 Mock 数据。
const mockBackedDataProvider: DataProvider = {
  ...mockDataProvider,
  jobs: httpDataProvider.jobs,
  talents: httpDataProvider.talents,
  career: httpDataProvider.career,
  trends: httpDataProvider.trends,
};

const hybridDataProvider: DataProvider = {
  ...mockDataProvider,
  jobs: httpDataProvider.jobs,
  talents: httpDataProvider.talents,
  career: httpDataProvider.career,
  graph: httpDataProvider.graph,
  trends: httpDataProvider.trends,
};

export const dataProvider: DataProvider =
  providerMode === "http"
    ? httpDataProvider
    : providerMode === "hybrid"
      ? hybridDataProvider
      : mockBackedDataProvider;
