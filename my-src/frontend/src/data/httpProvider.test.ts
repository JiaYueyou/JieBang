import { beforeEach, describe, expect, it, vi } from "vitest";
import request from "@/api/request";
import { httpDataProvider } from "./httpProvider";
import type { JobSummary } from "@/domain/types";

const job: JobSummary = {
  id: 12,
  title: "Java 平台工程师",
  department: "研发中心",
  headcount: 2,
  status: "open",
  created_at: "2026-06-20T10:00:00",
  level: "senior",
  salary_range: "25K-40K · 14薪",
  responsibilities: ["负责平台建设"],
  requirements: ["熟悉 Java"],
  bonus_skills: ["Kubernetes"],
  skills: ["Java", "Spring Boot"],
};

const response = <T>(data: T) => ({
  data: { code: 200, message: "success", data, meta: null },
});

describe("HTTP job provider contract", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("unwraps job list responses", async () => {
    vi.spyOn(request, "get").mockResolvedValue(response([job]) as never);
    await expect(httpDataProvider.jobs.list()).resolves.toEqual([job]);
    expect(request.get).toHaveBeenCalledWith("/jobs", { params: undefined });
  });

  it("uses server-returned entities for create, update, and status changes", async () => {
    const post = vi.spyOn(request, "post").mockResolvedValue(response(job) as never);
    const put = vi.spyOn(request, "put")
      .mockResolvedValueOnce(response({ ...job, title: "Java 架构师" }) as never)
      .mockResolvedValueOnce(response({ ...job, status: "closed" }) as never);

    await expect(httpDataProvider.jobs.create(job)).resolves.toEqual(job);
    await expect(httpDataProvider.jobs.update({ ...job, title: "Java 架构师" }))
      .resolves.toMatchObject({ title: "Java 架构师" });
    await expect(httpDataProvider.jobs.updateStatus(job.id, "closed"))
      .resolves.toMatchObject({ status: "closed" });

    expect(post).toHaveBeenCalledWith("/jobs", job);
    expect(put).toHaveBeenNthCalledWith(1, `/jobs/${job.id}`, { ...job, title: "Java 架构师" });
    expect(put).toHaveBeenNthCalledWith(2, `/jobs/${job.id}/status`, { status: "closed" });
  });

  it("calls the soft-delete endpoint", async () => {
    const remove = vi.spyOn(request, "delete").mockResolvedValue(response(null) as never);
    await httpDataProvider.jobs.remove(job.id);
    expect(remove).toHaveBeenCalledWith(`/jobs/${job.id}`);
  });

  it("maps graph filters and graph query endpoints", async () => {
    const graph = { nodes: [], edges: [] };
    const get = vi.spyOn(request, "get").mockResolvedValue(response(graph) as never);
    await httpDataProvider.graph.getPanorama({
      stack: "ai", level: "senior", nodeType: "Job", keyword: "大模型", limit: 100,
    });
    expect(get).toHaveBeenCalledWith("/graph/panorama", { params: {
      stack: "ai", level: "senior", node_type: "Job", keyword: "大模型", limit: 100,
    }});
    await httpDataProvider.graph.expand("job:1", 3);
    expect(get).toHaveBeenLastCalledWith("/graph/expand", { params: { node_id: "job:1", depth: 3 }});
  });
});
