import { describe, expect, it } from "vitest";
import {
  contentTypeLabel,
  difficultyLabel,
  levelLabel,
  skillCategoryLabel,
  skillSummaryLabel,
} from "./displayLabels";

describe("displayLabels", () => {
  it("将职级字段转换为中文业务文案", () => {
    expect(levelLabel("junior")).toBe("初级");
    expect(levelLabel("mid")).toBe("中级");
    expect(levelLabel("senior")).toBe("高级");
  });

  it("不向用户展示技能分类字段名", () => {
    expect(skillCategoryLabel("programming_language")).toBe("编程语言");
    expect(skillCategoryLabel("domain_knowledge")).toBe("领域知识");
    expect(skillCategoryLabel(" AI_ML ")).toBe("人工智能与机器学习");
    expect(skillCategoryLabel("Cloud")).toBe("云计算");
    expect(skillCategoryLabel("soft_skill")).toBe("通用能力");
    expect(skillCategoryLabel("unknown")).toBe("其他技能");
    expect(skillSummaryLabel("programming_language · 60 条事实 · 138 条来源"))
      .toBe("编程语言 · 60 条事实 · 138 条来源");
  });

  it("不向用户展示知识难度枚举", () => {
    expect(difficultyLabel("easy")).toBe("简单");
    expect(difficultyLabel(" MEDIUM ")).toBe("中等");
    expect(difficultyLabel("hard")).toBe("较难");
    expect(difficultyLabel("unknown")).toBe("未分级");
  });

  it("以可读名称展示文件格式", () => {
    expect(contentTypeLabel("image/png")).toBe("PNG 图片");
    expect(contentTypeLabel("application/pdf")).toBe("PDF 文档");
  });
});
