import { describe, expect, it } from "vitest";

import { classifyImportFailure, errorMessage } from "./crawlerFlowError";

describe("crawler flow error classification", () => {
  it("distinguishes job-v1 validation errors", () => {
    expect(classifyImportFailure(new Error("job-v1 校验失败：缺少 url"))).toBe("校验失败");
  });

  it("treats task and persistence errors as import failures", () => {
    expect(classifyImportFailure(new Error("数据库写入失败"))).toBe("导入失败");
  });

  it("classifies polling timeout as task timeout (Celery/Redis likely down)", () => {
    expect(classifyImportFailure(new Error("导入任务未在预期时间内完成，请稍后重试"))).toBe("任务超时");
    expect(classifyImportFailure(new Error("task still queued"))).toBe("任务超时");
  });

  it("normalizes unknown errors", () => {
    expect(errorMessage(null, "状态不可用")).toBe("状态不可用");
  });
});
