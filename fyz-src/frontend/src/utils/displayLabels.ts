const LEVEL_LABELS: Record<string, string> = {
  intern: "实习生",
  junior: "初级",
  primary: "初级",
  mid: "中级",
  middle: "中级",
  senior: "高级",
  expert: "专家",
  lead: "负责人",
  principal: "资深专家",
};

const SKILL_CATEGORY_LABELS: Record<string, string> = {
  programming_language: "编程语言",
  framework: "开发框架",
  database: "数据库",
  tool: "开发工具",
  cloud: "云计算",
  ai_ml: "人工智能与机器学习",
  artificial_intelligence: "人工智能",
  machine_learning: "机器学习",
  ai: "人工智能",
  "ai/ml": "人工智能与机器学习",
  "ai/llm": "人工智能与大语言模型",
  "ai agent": "智能体技术",
  "ai application": "人工智能应用",
  "ai engineering": "人工智能工程",
  "cloud computing": "云计算",
  backend: "后端技术",
  frontend: "前端技术",
  "data analysis": "数据分析",
  "data engineering": "数据工程",
  "deep learning": "深度学习",
  llm: "大语言模型",
  mlops: "机器学习运维",
  nlp: "自然语言处理",
  devops: "开发运维",
  domain_knowledge: "领域知识",
  soft_skill: "通用能力",
  methodology: "工程方法",
  platform: "技术平台",
  library: "技术库",
  other: "其他技能",
};

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: "简单",
  medium: "中等",
  hard: "较难",
};

const CONTENT_TYPE_LABELS: Record<string, string> = {
  "image/png": "PNG 图片",
  "image/jpeg": "JPEG 图片",
  "image/jpg": "JPG 图片",
  "application/pdf": "PDF 文档",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word 文档",
  "application/msword": "Word 文档",
  "text/plain": "纯文本文档",
};

export function levelLabel(value?: string | null) {
  const normalized = value?.trim().toLowerCase() || "";
  return LEVEL_LABELS[normalized] || value || "职级待补充";
}

export function skillCategoryLabel(value?: string | null) {
  const normalized = value?.trim().toLowerCase() || "";
  return SKILL_CATEGORY_LABELS[normalized] || "其他技能";
}

export function skillSummaryLabel(value?: string | null) {
  if (!value) return "其他技能";
  const [category, ...details] = value.split("·");
  const suffix = details.map((item) => item.trim()).filter(Boolean);
  return [skillCategoryLabel(category), ...suffix].join(" · ");
}

export function difficultyLabel(value?: string | null) {
  const normalized = value?.trim().toLowerCase() || "";
  return DIFFICULTY_LABELS[normalized] || "未分级";
}

export function contentTypeLabel(value?: string | null) {
  const normalized = value?.trim().toLowerCase() || "";
  return CONTENT_TYPE_LABELS[normalized] || "其他文件";
}
