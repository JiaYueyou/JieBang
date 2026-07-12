import { beforeEach, describe, expect, it, vi } from "vitest";
import request from "@/api/request";
import { httpDataProvider } from "./httpProvider";
import type { GeneratedJDDraft, JobCreatePayload, JobSummary } from "@/domain/types";

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
  jd_text: "完整 JD",
};

const createPayload: JobCreatePayload = {
  title: job.title,
  level: job.level,
  department: job.department,
  headcount: job.headcount,
  responsibilities: job.responsibilities,
  requirements: job.requirements,
  skills: job.skills || [],
  bonus_skills: job.bonus_skills,
  jd_text: job.jd_text || "",
  status: "open",
};

const draft: GeneratedJDDraft = {
  title: "Java 平台工程师",
  standardized_title: "Java 工程师",
  level: "senior",
  department: "研发中心",
  responsibilities: ["负责平台建设"],
  requirements: ["熟悉 Java"],
  skills: ["Java", "Spring Boot"],
  bonus_skills: ["Kubernetes"],
  jd_text: "完整 JD 草稿",
  assumptions: [],
  warnings: [],
  generation_mode: "llm",
};

const response = <T>(data: T) => ({
  data: { code: 200, message: "success", data, meta: null },
});

describe("HTTP job and JD Agent provider contract", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("unwraps job list responses", async () => {
    vi.spyOn(request, "get").mockResolvedValue(response([job]) as never);
    await expect(httpDataProvider.jobs.list()).resolves.toEqual([job]);
    expect(request.get).toHaveBeenCalledWith("/jobs", { params: undefined });
  });

  it("does not send FormData with the global application/json content type", async () => {
    const form = new FormData();
    form.append("file", new Blob(["Python"]), "resume.txt");
    let contentType = "";
    await request.post("/multipart-probe", form, {
      adapter: async (config) => {
        contentType = String(config.headers.get("Content-Type") || "");
        return { data: response({ ok: true }).data, status: 200, statusText: "OK", headers: {}, config };
      },
    });
    expect(contentType).not.toBe("application/json");
  });

  it("creates an Agent task, reads its completed draft, then uses server entities for publishing", async () => {
    const post = vi.spyOn(request, "post")
      .mockResolvedValueOnce(response({
        task: { task_id: "task-1", status: "queued", progress: 0, result: null, error_message: null },
        agent_run_id: "run-1",
      }) as never)
      .mockResolvedValueOnce(response(job) as never);
    const get = vi.spyOn(request, "get").mockResolvedValueOnce(response({
      task_id: "task-1", status: "succeeded", progress: 100, result: draft, error_message: null,
    }) as never);

    await expect(httpDataProvider.jobs.generateJD({
      mode: "requirements", title: job.title, level: job.level,
      department: job.department, skills_input: "Java, Spring Boot",
    })).resolves.toEqual(draft);
    await expect(httpDataProvider.jobs.create(createPayload)).resolves.toEqual(job);

    expect(post).toHaveBeenNthCalledWith(1, "/agents/jd-generations", {
      mode: "requirements", title: job.title, level: job.level,
      department: job.department, skills_input: "Java, Spring Boot",
    });
    expect(get).toHaveBeenCalledWith("/tasks/task-1", { params: undefined });
    expect(post).toHaveBeenNthCalledWith(2, "/jobs", createPayload);
  });

  it("calls the real update, status and soft-delete endpoints", async () => {
    const put = vi.spyOn(request, "put")
      .mockResolvedValueOnce(response({ ...job, title: "Java 架构师" }) as never)
      .mockResolvedValueOnce(response({ ...job, status: "closed" }) as never);
    const remove = vi.spyOn(request, "delete").mockResolvedValue(response(null) as never);

    await httpDataProvider.jobs.update({ ...job, title: "Java 架构师" });
    await httpDataProvider.jobs.updateStatus(job.id, "closed");
    await httpDataProvider.jobs.remove(job.id);

    expect(put).toHaveBeenNthCalledWith(1, `/jobs/${job.id}`, { ...job, title: "Java 架构师" });
    expect(put).toHaveBeenNthCalledWith(2, `/jobs/${job.id}/status`, { status: "closed" });
    expect(remove).toHaveBeenCalledWith(`/jobs/${job.id}`);
  });

  it("uses async Agent tasks and preserves degraded career metadata", async () => {
    const result = {
      recommendations: [{
        rank: 1, job_id: 7, job: "Python 工程师", recommend_score: 80,
        current_match: 50, after_match: 80, existing: ["Python"], gaps: ["Redis"],
        learning_plan: [], suggested_project: "缓存实践", total_time: "2 周",
        internal: false, explanation: "模板解释",
      }],
      agent_run_id: "career-run", agent_status: "degraded", warnings: ["模型不可用"],
    };
    const post = vi.spyOn(request, "post").mockResolvedValue(response({
      task: { task_id: "career-task", status: "succeeded", progress: 100, result, error_message: null },
      agent_run_id: "career-run",
    }) as never);

    await expect(httpDataProvider.career.analyze({
      skillText: "Python", enterpriseTech: "", enterpriseJobs: [],
    })).resolves.toEqual(expect.objectContaining({
      agentRunId: "career-run", agentStatus: "degraded", warnings: ["模型不可用"],
    }));
    expect(post).toHaveBeenCalledWith("/agents/career-plannings", expect.objectContaining({
      skill_text: "Python",
    }), { timeout: 60000 });
  });

  it("creates an async match explanation task with an AI-specific timeout", async () => {
    const result = {
      match_id: 3, score: 50, summary: "匹配说明", strengths: [], gaps: [], risks: [],
      interview_suggestions: [], generation_mode: "template", warnings: ["模板"], agent_run_id: "match-run",
    };
    const post = vi.spyOn(request, "post").mockResolvedValue(response({
      task: { task_id: "match-task", status: "succeeded", progress: 100, result, error_message: null },
      agent_run_id: "match-run",
    }) as never);
    await expect(httpDataProvider.talents.explain(3)).resolves.toEqual(result);
    expect(post).toHaveBeenCalledWith(
      "/agents/match-explanations", { match_id: 3 }, { timeout: 60000 },
    );
  });

  it("maps the real analysis overview response and forwards trend filters", async () => {
    const dataQuality = {
      total_records: 18,
      valid_time_records: 15,
      fallback_time_records: 3,
      valid_salary_records: 12,
      verified_skill_facts: 28,
      observed_months: 6,
      coverage_start: "2026-01",
      coverage_end: "2026-06",
      insufficient_data: false,
      notes: [],
    };
    const get = vi.spyOn(request, "get").mockResolvedValue(response({
      stats: { total_jobs: 18, new_skills: 2, average_salary_k: 27.5, active_cities: 3 },
      months: ["2026-05", "2026-06"],
      job_demand: [{ name: "Java", values: [7, 11] }],
      salary: [{ name: "Java", values: [25, 27.5] }],
      heatmap_skills: ["Java"],
      heatmap: [{ x: 0, y: 0, value: 11 }],
      locations: [{ city: "Hangzhou", value: 8 }],
      emerging_skills: [{ id: 1, skill: "LangChain", category: "AI", growth: 35, stage: "emerging", sparkline: [2, 5] }],
      data_quality: dataQuality,
    }) as never);

    await expect(httpDataProvider.trends.getOverview({
      months: 6,
      keyword: "Java",
      city: "Hangzhou",
    })).resolves.toEqual(expect.objectContaining({
      stats: { totalJobs: "18", newSkills: 2, avgSalary: "27.5K", activeCities: 3 },
      jobDemand: [{ name: "Java", values: [7, 11] }],
      dataQuality,
    }));
    expect(get).toHaveBeenCalledWith("/analysis/overview", {
      params: { months: 6, keyword: "Java", city: "Hangzhou" },
    });
  });

  it("loads job insights and persists an emerging-job decision", async () => {
    const dataQuality = {
      total_records: 4,
      valid_time_records: 4,
      fallback_time_records: 0,
      valid_salary_records: 3,
      verified_skill_facts: 6,
      observed_months: 2,
      coverage_start: "2026-05",
      coverage_end: "2026-06",
      insufficient_data: false,
      notes: [],
    };
    const insight = {
      id: 9,
      name: "AI Platform Engineer",
      core_skills: ["Python", "LangChain"],
      description: "Growing demand",
      confidence: 0.82,
      decision: null,
    };
    const get = vi.spyOn(request, "get").mockResolvedValue(response({
      emerging_jobs: [insight],
      capability_changes: [],
      data_quality: dataQuality,
    }) as never);
    const put = vi.spyOn(request, "put").mockResolvedValue(response({
      standard_job_id: 9,
      decision: "confirmed",
      note: "Review this week",
    }) as never);

    await expect(httpDataProvider.jobs.getInsights("Python")).resolves.toEqual({
      emergingJobs: [insight],
      capabilityChanges: [],
      dataQuality,
    });
    await expect(httpDataProvider.jobs.decideInsight(9, "confirmed", "Review this week")).resolves.toBeUndefined();

    expect(get).toHaveBeenCalledWith("/analysis/job-insights", { params: { skill: "Python" } });
    expect(put).toHaveBeenCalledWith("/analysis/emerging-jobs/9/decision", {
      decision: "confirmed",
      note: "Review this week",
    });
  });
});
