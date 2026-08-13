"""Read-only collector for the official-source group C assignment.

It only calls the public, unauthenticated CXMT recruitment endpoint observed in
the official careers page.  It does not attempt to solve challenges, log in, or
submit applications.  The other two companies are reported rather than scraped
because their public job pages do not expose an individual posting date.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "data" / "official_group_c_20260809.json"
OUT_REPORT = ROOT / "data" / "official_group_c_20260809_report.md"
CXMT_API = "https://cxmt.zhiye.com/api/Jobad/GetJobAdPageList"
CXMT_LIST = "https://cxmt.zhiye.com/social/jobs"
START = datetime(2026, 1, 1)
TECHNICAL_CATEGORIES = {"研发技术类", "量产技术类", "生产运营类", "信息技术类", "电路设计类"}


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "OfficialRecruitmentResearch/1.0 (read-only)",
        },
        method="POST",
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed public HTTPS endpoint
        return json.load(response)


def parse_portal_datetime(value: Any) -> datetime | None:
    """Parse ISO-ish timestamps, including the portal's seven-digit fractions."""
    if not isinstance(value, str):
        return None
    main, dot, fraction = value.partition(".")
    normalized = main + (dot + fraction[:6] if dot else "")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def collect_cxmt(crawled_at: str) -> list[dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    # The official portal exposes social, campus, and intern categories publicly.
    for category in ("1", "2", "3"):
        for page_index in range(100):
            result = post_json(
                CXMT_API,
                {
                    "PageIndex": page_index,
                    "PageSize": 100,
                    "Category": [category],
                    "KeyWords": "",
                    "SpecialType": 0,
                    "PortalId": "",
                    "DisplayFields": [
                        "Category", "Kind", "LocId", "PostDate", "Degree",
                        "YearsOfWorking", "ClassificationOne", "WorkWeChatQrCode",
                    ],
                },
            )
            if result.get("Code") != 200:
                raise RuntimeError(f"CXMT endpoint returned {result.get('Code')}: {result.get('Message')}")
            data = result.get("Data") or []
            if not data:
                break
            for item in data:
                posted_text = item.get("PostDate")
                posted = parse_portal_datetime(posted_text)
                if posted is None:
                    continue
                if posted < START:
                    continue
                if item.get("ClassificationOne") not in TECHNICAL_CATEGORIES:
                    continue
                if not (item.get("Duty") or "").strip() or not (item.get("Require") or "").strip():
                    # The deliverable requires both an actual JD and requirements.
                    continue
                job_id = item.get("JobAdId")
                if not isinstance(job_id, int) or job_id in rows:
                    continue
                location = "、".join(item.get("LocNames") or [])
                rows[job_id] = {
                    "source": "长鑫存储官方招聘门户（北森；由 cxmt.com/join.html 链接）",
                    "url": f"{CXMT_LIST}?jobAdId={job_id}&businessType={item.get('CategoryId', category)}",
                    "title": item.get("JobAdName") or "",
                    "company": "长鑫存储",
                    "jd": item.get("Duty") or "",
                    "requirements": item.get("Require") or "",
                    "posted_at": posted.isoformat(timespec="seconds"),
                    "crawled_at": crawled_at,
                    "location": location,
                    "employment_type": item.get("Kind") or "",
                    "job_category": item.get("ClassificationOne") or "",
                    "official_job_id": job_id,
                }
            # The portal returns newest first.  Do not assume the full Count is
            # stable, but stop once an entire page has no in-scope records.
            if all(
                (posted := parse_portal_datetime(item.get("PostDate"))) is None
                or posted < START
                for item in data
            ):
                break
    return sorted(rows.values(), key=lambda row: (row["posted_at"], row["official_job_id"]), reverse=True)


def write_report(records: list[dict[str, Any]], crawled_at: str) -> None:
    dates = [row["posted_at"][:10] for row in records]
    coverage = f"{min(dates)} 至 {max(dates)}" if dates else "无可验证的在范围内职位"
    report = f"""# 数据源组 C 公开官网招聘采集报告

- 采集时间：{crawled_at}
- 目标时间范围：2026-01-01 至采集时
- 可导入记录数：{len(records)}
- 已验证职位发布日期覆盖：{coverage}

## 合规与来源核验

| 公司 | 官方入口 | robots.txt | 条款 / 访问判断 | 结果 |
| --- | --- | --- | --- | --- |
| 幻方量化 | https://www.high-flyer.cn/join （该页官方链接到 Moka 职位页） | `https://www.high-flyer.cn/robots.txt`：`User-agent: *`、空 `Disallow`；Moka 的 `https://app.mokahr.com/robots.txt` 未禁止 high-flyer 租户 | 官网和公开职位页均无需登录或验证码。官网 /join 未发现公开使用条款链接；公开职位列表不展示单岗发布日期，无法证明其在指定时间窗内，未导入。 | 0 条（日期字段缺失） |
| 月之暗面（Moonshot AI） | https://careers.kimi.com/（页面 title/description 自称 Moonshot AI / 月之暗面官方招聘平台） | `https://careers.kimi.com/robots.txt`：`Allow: /`；`https://www.moonshot.cn/robots.txt` 返回 nginx 默认页，无法作为有效 robots 规则解释 | careers.kimi.com 页面和社会招聘展示无需登录或验证码；站点 sitemap 未列出 Terms/Privacy 页面。公开岗位展示与其链接的 Moka 列表均未展示单岗发布日期，无法验证时间范围，未导入。 | 0 条（日期字段缺失） |
| 长鑫存储 | https://www.cxmt.com/join.html → https://cxmt.zhiye.com/social/jobs | `https://www.cxmt.com/robots.txt`：`Allow: /`。官方招聘门户为公开只读访问。 | 官网使用条款：https://www.cxmt.com/terms_of_use.html；未发现禁止读取公开职位信息的条款。未登录、未处理验证码、未提交表单。仅使用招聘页在浏览器中公开请求的职位列表接口，且接口直接返回 JD、要求和发布日期。 | {len(records)} 条 |

## 数据限制

- 仅导入了发布日期在 2026-01-01（含）之后、且门户明确公开的长鑫存储职位；保留的门户分类为研发技术、量产技术、生产运营、信息技术、电路设计，均属半导体/软硬件技术岗位。
- 幻方量化与月之暗面均有官方/官方标注的公开入口，但未公开每条岗位的发布日期；为避免把“当前仍展示”误当成“在本任务时间窗内发布”，保留入口与阻断原因而不伪造 `posted_at`。
- 没有绕过 robots 指令、登录、验证码、加密响应或其他访问控制。
"""
    OUT_REPORT.write_text(report, encoding="utf-8")


def main() -> None:
    crawled_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    records = collect_cxmt(crawled_at)
    OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(records, crawled_at)
    print(f"Wrote {len(records)} records to {OUT_JSON}")


if __name__ == "__main__":
    main()
