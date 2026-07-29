# -*- coding: utf-8 -*-
"""
job-v1 Schema 校验器

所有爬虫输出必须通过此 Schema 校验，确保数据格式统一，
后端 ImportService 能直接消费。

字段定义（14个标准字段）：
  title        — 岗位名称（必填）
  company      — 公司名称（必填）
  city         — 工作城市（必填）
  salary       — 薪资文本（可空）
  experience   — 经验要求（必填）
  education    — 学历要求（必填）
  jd_text      — JD 全文（必填，≥10字符）
  responsibilities — 工作职责（可空）
  requirements — 任职要求（可空）
  keywords     — 关键词列表（必填，列表）
  posted_at    — 发布时间（源站未提供时允许为空）
  url          — 岗位链接（必填）
  source       — 数据来源（必填）
  crawled_at   — 爬取时间（必填）
"""

import json
import logging

logger = logging.getLogger("schema")

REQUIRED_FIELDS = [
    "title", "company", "city", "salary", "experience",
    "education", "jd_text", "responsibilities", "requirements", "keywords",
    "posted_at", "url", "source", "crawled_at",
]

TEXT_FIELDS_NONEMPTY = ["title", "company", "jd_text", "source"]
LIST_FIELDS = ["keywords"]


def validate_job_schema(record: dict, verbose: bool = True) -> list[str]:
    """
    校验单条记录是否符合 job-v1 schema

    参数：
      record: 待校验的字典
      verbose: 是否打印详细错误

    返回：
      错误信息列表（空列表表示校验通过）
    """
    errors = []

    # 1. 检查必需字段是否存在
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"缺少字段: {field}")

    if errors:
        return errors

    # 2. 非空文本字段不能为 None / 空字符串
    for field in TEXT_FIELDS_NONEMPTY:
        val = record.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"字段不能为空: {field}")

    # 3. jd_text 至少 10 个字符
    jd = record.get("jd_text", "") or ""
    if isinstance(jd, str) and len(jd.strip()) < 10:
        errors.append(f"jd_text 过短 ({len(jd.strip())} 字符，需要 ≥10)")

    # 4. keywords 必须是列表
    kw = record.get("keywords")
    if not isinstance(kw, list):
        errors.append(f"keywords 必须是列表，得到 {type(kw).__name__}")

    # 5. url 必须非空
    url = record.get("url", "") or ""
    if not url.strip():
        errors.append("url 不能为空")

    # 6. source 不能为空
    src = record.get("source", "") or ""
    if not src.strip():
        errors.append("source 不能为空")

    if errors and verbose:
        title = record.get("title", "未知")
        logger.warning("  Schema 校验失败 [%s]: %s", title, "; ".join(errors))

    return errors


def validate_all(data: list[dict], verbose: bool = True) -> dict:
    """
    校验整个数据集

    返回：{ "total": N, "passed": N, "failed": N, "errors": [...] }
    """
    total = len(data)
    passed = 0
    failed = 0
    all_errors = []

    for i, record in enumerate(data):
        errs = validate_job_schema(record, verbose=verbose)
        if errs:
            failed += 1
            all_errors.append({"index": i, "title": record.get("title", ""), "errors": errs})
        else:
            passed += 1

    result = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed / max(total, 1) * 100:.1f}%",
        "errors": all_errors,
    }

    return result
