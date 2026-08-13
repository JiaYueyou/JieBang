export type CrawlerFailureStage = "采集启动失败" | "采集失败" | "校验失败" | "导入失败" | "任务超时" | "状态轮询失败";

export function errorMessage(error: unknown, fallback = "未知错误"): string {
  if (error instanceof Error && error.message.trim()) return error.message.trim();
  if (typeof error === "string" && error.trim()) return error.trim();
  return fallback;
}

export function classifyImportFailure(error: unknown): CrawlerFailureStage {
  const message = errorMessage(error).toLowerCase();
  if (message.includes("job-v1") || message.includes("校验")) return "校验失败";
  if (message.includes("未在预期时间内") || message.includes("超时") || message.includes("queued")) {
    return "任务超时";
  }
  return "导入失败";
}
