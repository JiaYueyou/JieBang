# spider_framework — 爬虫框架
# 成员 D 李亚铮：爬虫与数据标准化

from .base_spider import BaseSpider
from .schema import validate_job_schema, validate_all
from .config import SpiderConfig

__all__ = ["BaseSpider", "validate_job_schema", "validate_all", "SpiderConfig"]
