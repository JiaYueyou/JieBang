# -*- coding: utf-8 -*-
"""
科大讯飞官网 — 爬虫

使用 BaseSpider 框架重构，配置驱动
配置：configs/iflytek.yaml
"""

import json
import datetime
import re
import os
import sys

# 把项目根目录加到 path，方便直接运行
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spider_framework import BaseSpider, SpiderConfig, validate_job_schema, validate_all


class IflytekSpider(BaseSpider):
    """科大讯飞官网社会化招聘爬虫"""

    name = "iflytek"
    source_name = "科大讯飞招聘"

    def __init__(self, config_path: str = None):
        # 加载配置
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "..", "configs", "iflytek.yaml"
            )
        self.config = SpiderConfig.load(config_path)

        # 设置默认配置（会被基类 __init__ 读取）
        self.default_config = self.config.to_dict()

        super().__init__()

        # 技能关键词（从配置中读取，也可以用统一词典）
        self.skill_keywords = [
            "Python", "Java", "Spark", "Flink", "LR", "GBDT", "DNN", "CNN", "RNN",
            "Transformer", "LLM", "NLP", "RAG", "Agent", "大模型", "机器学习",
            "深度学习", "算法", "数据分析", "数据挖掘", "大数据", "pipeline",
            "模型优化", "特征工程", "训练调优", "在线服务", "数据探查",
            "工程化部署", "预训练", "微调", "文本生成", "语义分析",
        ]

    # ============================================================
    # parse() — 解析单页数据
    # ============================================================

    def parse(self, page_num: int) -> list[dict]:
        """爬取指定页码的数据"""
        url = self.config.base_url
        body = dict(self.config.request_body_template)
        body["PageIndex"] = page_num - 1  # 讯飞从0开始

        resp = self.fetch(url, method="POST", json_data=body)
        res = resp.json()

        # 提取字段（根据配置中的 parse_rules）
        rules = self.config.parse_rules
        titles = self._jp(res, rules["title"]) or []
        cities = self._jp(res, rules["city"]) or []
        salaries = self._jp(res, rules["salary"]) or []
        duties = self._jp(res, rules["duty"]) or []
        requires = self._jp(res, rules["require"]) or []
        posted_dates = self._jp(res, rules["post_date"]) or []
        job_ids = self._jp(res, rules["job_id"]) or []

        records = []
        for i in range(len(titles)):
            title = titles[i] if i < len(titles) else ""
            if not title:
                continue

            duty = duties[i] if i < len(duties) else ""
            req = requires[i] if i < len(requires) else ""

            # 构建完整的 JD 文本
            jd_parts = []
            if duty:
                jd_parts.append("【工作职责】\n" + duty.strip())
            if req:
                jd_parts.append("【任职资格】\n" + req.strip())
            jd_text = "\n\n".join(jd_parts)

            # 提取关键词
            combined_text = f"{duty} {req}"
            keywords = self._extract_skills(combined_text)

            # 提取经验和学历
            experience = self._extract_experience(req)
            education = self._extract_education(req)

            # 城市
            city = cities[i] if i < len(cities) else ""
            if isinstance(city, list):
                city = "、".join(city)

            # URL
            job_id = job_ids[i] if i < len(job_ids) else ""
            url = f"https://iflytek.zhiye.com/social/detail?jobAdId={job_id}"

            # 发布时间
            post_date = posted_dates[i] if i < len(posted_dates) else ""

            record = {
                "title": title,
                "company": "科大讯飞",
                "city": city,
                "salary": salaries[i] if i < len(salaries) else None,
                "experience": experience,
                "education": education,
                "jd_text": jd_text,
                "duty": duty if duty else None,
                "require": req if req else None,
                "keywords": keywords,
                "post_date": post_date,
                "url": url,
                "source": self.source_name,
                "crawled_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            records.append(record)

        return records

    # ============================================================
    # 辅助方法
    # ============================================================

    @staticmethod
    def _jp(data, expr):
        """简易 jsonpath 实现（用递归+正则）"""
        # 处理 "$..Key" 和 "$.Data[*].Key" 格式
        if expr.startswith("$.."):
            key = expr[3:]
            return IflytekSpider._recursive_find(data, key)
        elif expr.startswith("$.Data[*]."):
            key = expr[11:]
            if isinstance(data, dict) and "Data" in data:
                items = data["Data"]
                if isinstance(items, list):
                    return [item.get(key) for item in items]
        return []

    @staticmethod
    def _recursive_find(obj, key):
        """递归查找所有匹配 key 的值"""
        results = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == key:
                    results.append(v)
                else:
                    results.extend(IflytekSpider._recursive_find(v, key))
        elif isinstance(obj, list):
            for item in obj:
                results.extend(IflytekSpider._recursive_find(item, key))
        return results

    def _extract_skills(self, text: str) -> list:
        """从文本中提取技能关键词"""
        found = []
        seen = set()
        pattern = re.compile(
            r"(" + "|".join(self.skill_keywords) + r")", re.IGNORECASE
        )
        for match in pattern.findall(text):
            key = match.lower()
            if key not in seen:
                seen.add(key)
                found.append(match)
        return found

    @staticmethod
    def _extract_experience(text: str) -> str:
        if not text:
            return "经验不限"
        patterns = [
            r"(\d+年及以上)", r"(\d+-\d+年)", r"(\d+年以上)",
            r"(\d+年)工作经验", r"(\d+年)", r"应届生", r"不限",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                raw = m.group(1) if m.groups() else m.group()
                return raw if raw != "不限" else "经验不限"
        return "经验不限"

    @staticmethod
    def _extract_education(text: str) -> str:
        if not text:
            return "学历不限"
        levels = ["高中", "中专", "大专", "专科", "本科", "学士",
                  "硕士", "研究生", "博士"]
        matches = []
        for level in levels:
            if re.search(level, text):
                matches.append(level)
        if not matches:
            return "学历不限"
        priority = {"博士": 6, "硕士": 5, "研究生": 5, "本科": 4,
                    "学士": 4, "大专": 3, "专科": 3, "中专": 2, "高中": 1}
        matches.sort(key=lambda x: priority.get(x, 0), reverse=True)
        return matches[0]


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    spider = IflytekSpider()
    filepath = spider.run()

    # 输出后自动校验 Schema
    if filepath and os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = validate_all(data)
        print(f"\nSchema 校验: 通过 {result['passed']}/{result['total']} 条"
              f" ({result['pass_rate']})")
        if result["failed"] > 0:
            print(f"失败 {result['failed']} 条，详情见日志")
