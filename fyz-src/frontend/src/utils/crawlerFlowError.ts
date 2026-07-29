export type CrawlerFailureStage = "采集启动失败" | "采集失败" | "校验失败" | "导入失败" | "状态轮询失败";

export function errorMessage(error: unknown, fallback = "未知错误"): string {
  if (error instanceof Error && error.message.trim()) return error.message.trim();
  if (typeof error === "string" && error.trim()) return error.trim();
  return fallback;
}

export function classifyImportFailure(error: unknown): CrawlerFailureStage {
  const message = errorMessage(error).toLowerCase();
  return message.includes("job-v1") || message.includes("校验")
    ? "校验失败"
    : "导入失败";
}
