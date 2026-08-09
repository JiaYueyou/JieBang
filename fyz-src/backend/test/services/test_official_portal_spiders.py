import json
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from spiders.deepseek_spider import DeepSeekSpider, extract_embedded_snapshot
from spiders.jd_spider import JdSpider
from spiders.meituan_spider import MeituanSpider
from spiders.pdd_spider import PddSpider


CRAWLED_AT = "2026-08-09T12:00:00+08:00"


def test_jd_normalizes_published_technical_job():
    spider = JdSpider(start_date=date(2024, 1, 1), end_date=date(2026, 12, 31))
    record = spider.normalize_job(
        {
            "positionId": 221613,
            "positionCode": "00880532",
            "positionNameOpen": "BMS电池软件开发岗",
            "positionDeptName": "京东零售",
            "jobType": "研发类",
            "workCity": "北京市",
            "publishTime": 1786032000000,
            "workContent": "负责BMS软件系统设计、开发与维护。",
            "qualification": "精通C/C++/Python，熟悉嵌入式系统和硬件驱动开发。",
        },
        crawled_at=CRAWLED_AT,
    )

    assert record is not None
    assert record["external_id"] == "221613"
    assert record["posted_at"].startswith("2026-08-07")
    assert record["source_meta"]["date_semantics"] == "published_at"


def test_meituan_uses_first_post_time_not_refresh_time():
    spider = MeituanSpider(start_date=date(2024, 1, 1), end_date=date(2026, 12, 31))
    record = spider.normalize_job(
        {
            "jobUnionId": "3057805095",
            "name": "LongCat - 基座大模型评测分析算法研究员",
            "jobFamily": "技术类",
            "jobFamilyGroup": "算法",
            "cityList": [{"name": "北京市"}],
            "department": [{"name": "基础研发平台"}],
            "jobDuty": "负责大模型评测、训练数据分析和算法研究。",
            "jobRequirement": "熟悉 Python、C++ 和深度学习框架。",
            "firstPostTime": 1739531850000,
            "refreshTime": 1786269602000,
        },
        crawled_at=CRAWLED_AT,
    )

    assert record is not None
    assert record["posted_at"].startswith("2025-02-14")
    assert record["source_meta"]["source_updated_at"].startswith("2026-08-09")


def test_pdd_keeps_update_time_out_of_posted_at():
    spider = PddSpider(start_date=date(2024, 1, 1), end_date=date(2026, 12, 31))
    record = spider.normalize_job(
        {
            "code": "T024503",
            "name": "服务端研发工程师",
            "job": "technology",
            "workLocation": ["上海"],
            "jobDuty": "<p>负责分布式服务端系统开发。</p>",
            "serveRequirement": "<p>熟悉 Java、Redis 和 Kafka。</p>",
            "updateTime": "2025-10-07",
        },
        crawled_at=CRAWLED_AT,
        detail_url="https://careers.pddglobalhr.com/jobs/detail?code=T024503",
    )

    assert record is not None
    assert record["posted_at"] is None
    assert record["source_meta"]["date_semantics"] == "updated_at"
    assert record["source_meta"]["source_updated_at"].startswith("2025-10-07")


def test_deepseek_extracts_bundle_snapshot_and_filters_hr():
    payload = {
        "crawledAt": "2026-07-29T13:59:33.692Z",
        "sourceUrl": "https://app.mokahr.com/social-recruitment/high-flyer/140576#/",
        "total": 1,
        "functionCategories": [],
        "jobs": [{"id": "job-1"}],
    }
    literal = repr(json.dumps(payload, ensure_ascii=False))
    snapshot = extract_embedded_snapshot(f"var x=JSON.parse({literal});")
    assert snapshot["jobs"][0]["id"] == "job-1"

    spider = DeepSeekSpider()
    technical = spider.normalize_job(
        {
            "id": "tech-1",
            "title": "Agent Infra 研发工程师",
            "functionName": "全栈开发/算法",
            "locations": ["北京市"],
            "descriptionHtml": "<p>负责 Python、Linux 和 Kubernetes 基础设施研发。</p>",
            "detailUrl": "https://talent.deepseek.com/#tech-1",
        },
        crawled_at=CRAWLED_AT,
        snapshot_at="2026-07-29T13:59:33.692Z",
        bundle_url="https://talent.deepseek.com/static/main.example.js",
    )
    hr = spider.normalize_job(
        {
            "id": "hr-1",
            "title": "HR 团队",
            "functionName": "职能部门",
            "locations": ["北京市"],
            "descriptionHtml": "<p>负责招聘与人力资源工作。</p>",
            "detailUrl": "https://talent.deepseek.com/#hr-1",
        },
        crawled_at=CRAWLED_AT,
        snapshot_at="2026-07-29T13:59:33.692Z",
        bundle_url="https://talent.deepseek.com/static/main.example.js",
    )

    assert technical is not None
    assert technical["posted_at"] is None
    assert hr is None
