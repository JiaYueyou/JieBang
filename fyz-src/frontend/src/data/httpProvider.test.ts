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
  target: "public",
  standardized_title: "Java 工程师",
  level: "senior",
  department: "研发中心",
  responsibilities: ["负责平台建设"],
  requirements: ["熟悉 Java"],
  skills: ["Java", "Spring Boot"],
  bonus_skills: ["Kubernetes"],
  trainable_skills: [],
  transfer_profile: [],
  manager_confirmations: [],
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

  it("loads public jobs with server pagination metadata", async () => {
    vi.spyOn(request, "get").mockResolvedValue({
      data: {
        code: 200,
        message: "success",
        data: [job],
        meta: { page: 2, page_size: 6, total: 13, total_pages: 3 },
      },
    } as never);
    await expect(httpDataProvider.jobs.list({ page: 2, pageSize: 6, status: "open", keyword: "Java" })).resolves.toEqual({
      items: [job],
      page: 2,
      pageSize: 6,
      total: 13,
      totalPages: 3,
    });
    expect(request.get).toHaveBeenCalledWith("/jobs", {
      params: { page: 2, page_size: 6, status: "open", keyword: "Java" },
    });
  });

  it("loads internal positions with server pagination metadata", async () => {
    vi.spyOn(request, "get").mockResolvedValue({
      data: {
        code: 200,
        message: "success",
        data: [],
        meta: { page: 1, page_size: 6, total: 0, total_pages: 0 },
      },
    } as never);
    await expect(httpDataProvider.internalTransfer.listPositionsPage({
      page: 1,
      pageSize: 6,
      status: "draft",
      keyword: "平台",
    })).resolves.toEqual({ items: [], page: 1, pageSize: 6, total: 0, totalPages: 0 });
    expect(request.get).toHaveBeenCalledWith("/internal-transfer/positions", {
      params: { page: 1, page_size: 6, status: "draft", keyword: "平台" },
    });
  });

  it("loads paged observed jobs and their source evidence", async () => {
    const observed = {
      id: 7,
      title: "Python 数据工程师",
      standardized_title: "数据工程师",
      company: "示例科技",
      city: "合肥",
      salary_text: "20K-30K",
      experience_text: "3-5年",
      education_text: "本科",
      source: "zhaopin",
      source_url: "https://example.test/jobs/7",
      posted_at: "2026-07-01",
      crawled_at: "2026-07-02",
      dedup_status: "unique",
      verified_skill_count: 1,
      pending_skill_count: 0,
    };
    const get = vi.spyOn(request, "get")
      .mockResolvedValueOnce({
        data: {
          code: 200,
          message: "success",
          data: [observed],
          meta: { page: 1, page_size: 20, total: 1, total_pages: 1 },
        },
      } as never)
      .mockResolvedValueOnce(response({
        ...observed,
        jd_text: "Python 数据处理",
        responsibilities: "数据管道",
        requirements: "熟悉 Python",
        skills: [{
          fact_id: 9,
          skill_id: 3,
          skill_name: "Python",
          category: "backend",
          kind: "required",
          confidence: 0.95,
          evidence_text: "熟悉 Python",
          verification_status: "verified",
          extraction_method: "rule",
          source_count: 2,
        }],
      }) as never);

    await expect(httpDataProvider.jobs.listObserved({
      page: 1,
      pageSize: 20,
      keyword: "Python",
      city: "合肥",
    })).resolves.toEqual(expect.objectContaining({
      items: [observed],
      total: 1,
      totalPages: 1,
    }));
    await expect(httpDataProvider.jobs.getObserved(7)).resolves.toEqual(
      expect.objectContaining({ id: 7, skills: [expect.objectContaining({ skill_name: "Python" })] }),
    );
    expect(get).toHaveBeenNthCalledWith(1, "/jobs/observed", {
      params: {
        page: 1,
        page_size: 20,
        keyword: "Python",
        city: "合肥",
        source: undefined,
      },
    });
    expect(get).toHaveBeenNthCalledWith(2, "/jobs/observed/7", { params: undefined });
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
      target: "public", mode: "requirements", title: job.title, level: job.level,
      department: job.department, skills_input: "Java, Spring Boot",
    })).resolves.toEqual(draft);
    await expect(httpDataProvider.jobs.create(createPayload)).resolves.toEqual(job);

    expect(post).toHaveBeenNthCalledWith(1, "/agents/jd-generations", {
      target: "public", mode: "requirements", title: job.title, level: job.level,
      department: job.department, skills_input: "Java, Spring Boot",
    });
    expect(get).toHaveBeenCalledWith("/tasks/task-1", { params: undefined });
    expect(post).toHaveBeenNthCalledWith(2, "/jobs", createPayload);
  });

  it("creates and resolves a JD input suggestion task", async () => {
    const result = {
      title: "Java 开发工程师",
      target: "public" as const,
      mode: "requirements" as const,
      suggestions: ["Java", "Spring Boot", "MySQL"],
      generation_mode: "template" as const,
      warnings: ["请人工核对"],
    };
    const post = vi.spyOn(request, "post").mockResolvedValue(response({
      task: { task_id: "suggestion-task", status: "succeeded", progress: 100, result, error_message: null },
      agent_run_id: "suggestion-run",
    }) as never);

    await expect(httpDataProvider.jobs.suggestJDInput({
      target: "public",
      mode: "requirements",
      title: "Java 开发工程师",
      level: "senior",
      department: "后台开发组",
    })).resolves.toEqual(result);
    expect(post).toHaveBeenCalledWith("/agents/jd-input-suggestions", {
      target: "public",
      mode: "requirements",
      title: "Java 开发工程师",
      level: "senior",
      department: "后台开发组",
    });
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

  it("uses real favorite toggle state and persists browsing history", async () => {
    const favorite = {
      id: 4,
      target_type: "job" as const,
      target_id: job.id,
      title: job.title,
      subtitle: "研发中心 · senior",
      company: "智联职引",
      location: "合肥",
      salary: job.salary_range,
      experience: "3-5年",
      education: "本科",
      skills: job.skills || [],
      match: 88,
      savedAt: "2026-07-30T10:00:00",
      savedOrder: 1785405600,
      note: "",
    };
    const historyInput = {
      type: "job" as const,
      targetId: job.id,
      title: job.title,
      description: "岗位详情",
      source: "岗位管理",
      tags: ["Java"],
      url: `/jobs?record=${job.id}`,
    };
    const history = {
      ...historyInput,
      id: 6,
      dateKey: "today" as const,
      date: "2026-07-30",
      time: "10:00",
    };
    const post = vi.spyOn(request, "post")
      .mockResolvedValueOnce(response({ active: true }) as never)
      .mockResolvedValueOnce(response(history) as never);
    const get = vi.spyOn(request, "get").mockResolvedValueOnce(response([favorite]) as never);

    await expect(httpDataProvider.favorites.toggle("job", job.id, job.title)).resolves.toBe(true);
    await expect(httpDataProvider.favorites.list()).resolves.toEqual([favorite]);
    await expect(httpDataProvider.history.record(historyInput)).resolves.toEqual(history);

    expect(post).toHaveBeenNthCalledWith(1, "/favorites", {
      target_type: "job",
      target_id: job.id,
      title: job.title,
    });
    expect(get).toHaveBeenCalledWith("/favorites", { params: undefined });
    expect(post).toHaveBeenNthCalledWith(2, "/history", historyInput);
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

  it("runs a full graph sync without LLM enrichment and returns persisted counts", async () => {
    const result = { node_count: 120, edge_count: 240, fact_count: 80 };
    const post = vi.spyOn(request, "post").mockResolvedValue(response({
      task_id: "graph-task",
      status: "succeeded",
      progress: 100,
      result,
      error_message: null,
    }) as never);

    await expect(httpDataProvider.graph.sync()).resolves.toEqual(result);
    expect(post).toHaveBeenCalledWith("/graph/sync", {
      mode: "full",
      enrich_top_skills: false,
    });
  });

  it("surfaces the backend failure reason for an Agent task", async () => {
    vi.spyOn(request, "post").mockResolvedValue(response({
      task: { task_id: "match-task", status: "queued", progress: 0, result: null, error_message: null },
      agent_run_id: "match-run",
    }) as never);
    vi.spyOn(request, "get").mockResolvedValue(response({
      task_id: "match-task", status: "failed", progress: 100, result: null,
      error_message: "模型服务限流，请稍后重试",
    }) as never);

    await expect(httpDataProvider.talents.explain(3)).rejects.toThrow("模型服务限流，请稍后重试");
  });

  it("loads and reviews skill facts through the real review endpoints", async () => {
    const fact = {
      id: 31, skill_id: 8, skill_name: "Python", category: "programming",
      kind: "required", importance: 0.9, frequency: 1, confidence: 0.88,
      evidence_text: "熟练使用 Python", verification_status: "unverified",
      extraction_method: "rule", source_count: 1, job_id: null,
      raw_job_record_id: 12, job_title: "AI 工程师", company: "示例企业",
      source: "智联招聘", source_url: "https://example.com/job/1",
      reviewed_by: null, reviewer_name: null, reviewed_at: null,
      review_note: null, created_at: "2026-07-29T10:00:00",
    };
    const get = vi.spyOn(request, "get").mockResolvedValue({
      data: {
        code: 200, message: "success",
        data: {
          items: [fact],
          summary: { all: 1, unverified: 1, verified: 0, rejected: 0 },
        },
        meta: { page: 1, page_size: 12, total: 1, total_pages: 1 },
      },
    } as never);
    const patch = vi.spyOn(request, "patch").mockResolvedValue(response({
      ...fact,
      verification_status: "verified",
      reviewed_by: 1,
      reviewer_name: "admin",
      reviewed_at: "2026-07-29T11:00:00Z",
      review_note: "证据充分",
    }) as never);

    await expect(httpDataProvider.skillReviews.list({
      page: 1,
      pageSize: 12,
      status: "unverified",
      keyword: "Python",
    })).resolves.toEqual(expect.objectContaining({
      items: [fact],
      meta: { page: 1, page_size: 12, total: 1, total_pages: 1 },
    }));
    await expect(
      httpDataProvider.skillReviews.review(31, "verified", "证据充分"),
    ).resolves.toEqual(expect.objectContaining({ verification_status: "verified" }));

    expect(get).toHaveBeenCalledWith("/skills/facts/reviews", {
      params: { page: 1, page_size: 12, status: "unverified", keyword: "Python" },
    });
    expect(patch).toHaveBeenCalledWith(
      "/skills/facts/31/review",
      { decision: "verified", note: "证据充分" },
    );
  });

  it("reports a completed Agent task without a result as an invalid response", async () => {
    vi.spyOn(request, "post").mockResolvedValue(response({
      task: { task_id: "career-task", status: "succeeded", progress: 100, result: null, error_message: null },
      agent_run_id: "career-run",
    }) as never);

    await expect(httpDataProvider.career.analyze({
      skillText: "Python", enterpriseTech: "", enterpriseJobs: [],
    })).rejects.toThrow("AI 任务已完成，但未返回可用结果");
  });

  it("maps the real analysis overview response and forwards trend filters", async () => {
    const baseline = {
      version: "standard-job-v1",
      source_note: "MySQL baseline",
      minimum_source_count: 2,
      standard_job_count: 1,
      technology_stack_count: 1,
      verified_skill_count: 2,
      verified_fact_count: 8,
      baseline_at: "2026-06-30",
      technology_stacks: [{ key: "backend", label: "后端开发", standard_job_count: 1, source_count: 4, top_skills: ["Java"] }],
      job_standards: [],
    };
    const dataQuality = {
      total_records: 18,
      deduplicated_records: 16,
      duplicate_records: 2,
      independent_job_clusters: 5,
      independent_companies: 8,
      valid_time_records: 15,
      fallback_time_records: 3,
      valid_salary_records: 12,
      verified_skill_facts: 28,
      observed_months: 6,
      observed_periods: 6,
      period_unit: "month",
      coverage_start: "2026-01",
      coverage_end: "2026-06",
      insufficient_data: false,
      notes: [],
    };
    const get = vi.spyOn(request, "get").mockResolvedValue(response({
      window: "6m",
      window_label: "近 6 个月",
      granularity: "month",
      stats: { total_jobs: 18, new_skills: 2, average_salary_k: 27.5, active_cities: 3 },
      months: ["2026-05", "2026-06"],
      job_demand: [{ name: "Java", values: [7, 11] }],
      salary: [{ name: "Java", values: [25, 27.5] }],
      heatmap_skills: ["Java"],
      heatmap: [{ x: 0, y: 0, value: 11 }],
      locations: [{ city: "Hangzhou", value: 8 }],
      emerging_skills: [{ id: 1, skill: "LangChain", category: "AI", growth: 35, stage: "emerging", sparkline: [2, 5] }],
      data_quality: dataQuality,
      baseline,
    }) as never);

    await expect(httpDataProvider.trends.getOverview({
      window: "6m",
      keyword: "Java",
      city: "Hangzhou",
    })).resolves.toEqual(expect.objectContaining({
      stats: { totalJobs: "18", newSkills: 2, avgSalary: "27.5K", activeCities: 3 },
      jobDemand: [{ name: "Java", values: [7, 11] }],
      dataQuality,
      baseline,
      window: "6m",
      windowLabel: "近 6 个月",
    }));
    expect(get).toHaveBeenCalledWith("/analysis/overview", {
      params: {
        window: "6m",
        keyword: "Java",
        city: "Hangzhou",
        emerging_page: 1,
        emerging_page_size: 10,
        new_job_page: 1,
        new_job_page_size: 10,
        new_job_keyword: undefined,
      },
    });
  });

  it("loads job insights and persists an emerging-job decision", async () => {
    const baseline = {
      version: "standard-job-v1",
      source_note: "MySQL baseline",
      minimum_source_count: 2,
      standard_job_count: 1,
      technology_stack_count: 1,
      verified_skill_count: 2,
      verified_fact_count: 6,
      baseline_at: "2026-06-30",
      technology_stacks: [],
      job_standards: [],
    };
    const dataQuality = {
      total_records: 4,
      deduplicated_records: 4,
      duplicate_records: 0,
      independent_job_clusters: 1,
      independent_companies: 2,
      valid_time_records: 4,
      fallback_time_records: 0,
      valid_salary_records: 3,
      verified_skill_facts: 6,
      observed_months: 2,
      observed_periods: 2,
      period_unit: "month",
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
      baseline,
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
      baseline,
    });
    await expect(httpDataProvider.jobs.decideInsight(9, "confirmed", "Review this week")).resolves.toBeUndefined();

    expect(get).toHaveBeenCalledWith("/analysis/job-insights", { params: { skill: "Python" } });
    expect(put).toHaveBeenCalledWith("/analysis/emerging-jobs/9/decision", {
      decision: "confirmed",
      note: "Review this week",
    });
  });

  it("searches the employee directory by partial number and adds the selected employee", async () => {
    const employee = {
      id: 18,
      employee_no: "20260715018",
      name: "李然",
      department: "数据平台部",
      current_position: "数据开发工程师",
      level: "senior",
      location: "合肥",
      tenure_months: 26,
      position_tenure_months: 14,
      skills: ["Python", "Spark"],
      project_highlights: [],
      status: "active" as const,
      source: "hr_sync",
      in_talent_pool: false,
      synced_at: "2026-07-15T10:00:00",
    };
    const talent = {
      ...employee,
      id: 7,
      status: "active" as const,
      created_at: "2026-07-15T10:01:00",
      updated_at: "2026-07-15T10:01:00",
    };
    const get = vi.spyOn(request, "get").mockResolvedValue(response([employee]) as never);
    const post = vi.spyOn(request, "post").mockResolvedValue(response(talent) as never);

    await expect(httpDataProvider.internalTransfer.searchEmployeeDirectory("15018")).resolves.toEqual([employee]);
    await expect(httpDataProvider.internalTransfer.createTalentFromDirectory(18)).resolves.toEqual(talent);

    expect(get).toHaveBeenCalledWith("/internal-transfer/employee-directory", { params: { keyword: "15018", limit: 10 } });
    expect(post).toHaveBeenCalledWith("/internal-transfer/talents/from-directory/18", {});
  });

  it("maps the admin data-quality list and reversible decision contracts", async () => {
    const item = {
      id: 31,
      title: "Java 平台工程师",
      standard_job_id: 8,
      standardized_title: "Java 工程师",
      company: "示例科技",
      source: "zhaopin",
      source_url: "https://example.test/jobs/31",
      posted_at: "2026-07-20T00:00:00Z",
      crawled_at: "2026-07-21T00:00:00Z",
      posted_at_text: "2026-07-20",
      crawled_at_text: "2026-07-21",
      quality_score: 0.71,
      freshness_score: 0.9,
      source_trust_score: 0.85,
      quality_status: "warning" as const,
      quality_flags: ["near_duplicate"],
      dedup_status: "near_duplicate",
      near_duplicate_group_id: "ndg-123",
      near_duplicate_score: 0.94,
      is_excluded: false,
      exclusion_reason: null,
      quality_evaluated_at: "2026-07-30T00:00:00Z",
    };
    const get = vi.spyOn(request, "get").mockResolvedValue({
      data: {
        code: 200,
        message: "success",
        data: {
          items: [item],
          summary: {
            total: 1,
            accepted: 0,
            warning: 1,
            rejected: 0,
            pending: 0,
            near_duplicates: 1,
            excluded: 0,
            average_quality_score: 0.71,
            flag_counts: { near_duplicate: 1 },
          },
        },
        meta: { page: 1, page_size: 20, total: 1, total_pages: 1 },
      },
    } as never);
    const patch = vi.spyOn(request, "patch").mockResolvedValue(response({
      ...item,
      is_excluded: true,
      exclusion_reason: "正文与同岗位记录高度重复",
    }) as never);

    await expect(httpDataProvider.admin.listQuality({
      page: 1,
      pageSize: 20,
      qualityStatus: "warning",
      source: "zhaopin",
      excluded: false,
    })).resolves.toEqual(expect.objectContaining({
      items: [item],
      meta: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    }));
    await expect(httpDataProvider.admin.decideQuality(
      31,
      "exclude",
      "正文与同岗位记录高度重复",
    )).resolves.toEqual(expect.objectContaining({ is_excluded: true }));

    expect(get).toHaveBeenCalledWith("/admin/data-quality/records", {
      params: {
        page: 1,
        page_size: 20,
        source: "zhaopin",
        quality_status: "warning",
        quality_flag: undefined,
        near_duplicate_group_id: undefined,
        excluded: false,
      },
    });
    expect(patch).toHaveBeenCalledWith("/admin/data-quality/records/31", {
      action: "exclude",
      reason: "正文与同岗位记录高度重复",
    });
  });
});
