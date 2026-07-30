import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { HistoryRecord } from "@/domain/types";

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  record: vi.fn(),
  getInsights: vi.fn(),
}));

vi.mock("@/data", () => ({
  dataProvider: {
    history: {
      list: mocks.list,
      record: mocks.record,
      getInsights: mocks.getInsights,
      remove: vi.fn(),
      clear: vi.fn(),
    },
  },
}));

import { useHistoryStore } from "./history";

const candidateRecord: HistoryRecord = {
  id: 1,
  type: "resume",
  targetId: 1,
  title: "候选人 A",
  description: "候选人详情",
  source: "人才匹配",
  dateKey: "today",
  date: "2026-07-30",
  time: "16:00",
  tags: ["Python"],
  url: "/matching/1",
};

const searchRecord: HistoryRecord = {
  id: 2,
  type: "search",
  title: "岗位洞察：Python",
  description: "搜索岗位洞察",
  source: "岗位管理",
  dateKey: "today",
  date: "2026-07-30",
  time: "16:01",
  tags: ["Python"],
  url: "/jobs?tab=insight",
};

describe("history store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.record.mockResolvedValue(searchRecord);
    mocks.list.mockResolvedValue([searchRecord, candidateRecord]);
    mocks.getInsights.mockResolvedValue({ focusStats: [], frequentRecords: [] });
  });

  it("refreshes persisted history after recording from a fresh page", async () => {
    const store = useHistoryStore();

    await store.record({
      type: "search",
      title: searchRecord.title,
      description: searchRecord.description,
      source: searchRecord.source,
      tags: searchRecord.tags,
      url: searchRecord.url,
    });

    expect(mocks.list).toHaveBeenCalledOnce();
    expect(store.records).toEqual([searchRecord, candidateRecord]);
  });
});
