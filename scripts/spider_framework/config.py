# -*- coding: utf-8 -*-
"""
数据源配置加载器

将爬虫配置从代码中抽离到 YAML/JSON 配置文件，实现"配置化"。
每个数据源一份配置文件，不硬编码爬取逻辑。
"""

import json
import os
import logging
from typing import Optional

logger = logging.getLogger("config")


class SpiderConfig:
    """
    数据源配置

    支持从 YAML 或 JSON 文件加载。
    如果 pyyaml 不可用，自动降级为 JSON。
    """

    # ============================================================
    # 标准字段 —— 所有配置文件应包含
    # ============================================================
    REQUIRED_KEYS = ["name", "source_name", "base_url"]

    def __init__(self, data: dict):
        self._data = data

        # 基础信息
        self.name: str = data.get("name", "")
        self.source_name: str = data.get("source_name", "")
        self.base_url: str = data.get("base_url", "")

        # 请求配置
        self.method: str = data.get("method", "GET")
        self.request_interval: float = data.get("request_interval", 1.0)
        self.retry_times: int = data.get("retry_times", 3)
        self.retry_delay: int = data.get("retry_delay", 2)
        self.timeout: int = data.get("timeout", 30)

        # 分页
        self.page_start: int = data.get("page_start", 0)
        self.total_pages: int = data.get("total_pages", 5)
        self.page_size: int = data.get("page_size", 20)

        # 请求体模板（POST 用）
        self.request_body_template: Optional[dict] = data.get("request_body_template")

        # 额外请求头
        self.headers: dict = data.get("headers", {})

        # 解析规则（由具体爬虫使用）
        self.parse_rules: dict = data.get("parse_rules", {})

        # 过滤条件
        self.filters: dict = data.get("filters", {})

        # 其他自定义配置
        self.extra: dict = {k: v for k, v in data.items()
                           if k not in self._std_keys()}

    def _std_keys(self) -> set:
        return {
            "name", "source_name", "base_url", "method",
            "request_interval", "retry_times", "retry_delay", "timeout",
            "page_start", "total_pages", "page_size",
            "request_body_template", "headers", "parse_rules", "filters",
        }

    # ============================================================
    # 工厂方法
    # ============================================================

    @classmethod
    def load(cls, filepath: str) -> "SpiderConfig":
        """
        从文件加载配置

        支持 .yaml / .yml / .json 格式
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"配置文件不存在: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()

        if ext in (".yaml", ".yml"):
            return cls._load_yaml(filepath)
        elif ext == ".json":
            return cls._load_json(filepath)
        else:
            raise ValueError(f"不支持的配置文件格式: {ext}（支持 yaml/json）")

    @classmethod
    def _load_json(cls, filepath: str) -> "SpiderConfig":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls._validate(data, filepath)

    @classmethod
    def _load_yaml(cls, filepath: str) -> "SpiderConfig":
        try:
            import yaml
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return cls._validate(data, filepath)
        except ImportError:
            logger.warning("pyyaml 未安装，尝试用 JSON 解析 %s", filepath)
            # 尝试用 JSON 解析 yaml（简单情况能工作）
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            import json as _json
            data = _json.loads(content)
            return cls._validate(data, filepath)

    @classmethod
    def _validate(cls, data: dict, filepath: str) -> "SpiderConfig":
        """校验必填字段"""
        for key in cls.REQUIRED_KEYS:
            if key not in data:
                raise ValueError(f"配置缺少必填字段 '{key}': {filepath}")
        logger.info("已加载配置: %s (name=%s)", filepath, data["name"])
        return cls(data)

    def to_dict(self) -> dict:
        """转为普通字典"""
        return dict(self._data)
