"""爬虫服务 — 管理爬虫脚本执行与数据采集"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AsyncTask, JobSkillFact, RawJobRecord, Skill, SourceDocument, User

logger = logging.getLogger(__name__)

# 项目根目录（JieBang/）
# 本文件位置: fyz-src/backend/app/services/crawler_service.py
# 上溯 5 层: services -> app -> backend -> fyz-src -> JieBang
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SPIDERS_DIR = SCRIPTS_DIR / "spiders"
DATA_DIR = PROJECT_ROOT / "data"


class SpiderMeta:
    """爬虫脚本的元信息"""

    def __init__(self, spider_id: int, module_name: str, name: str,
                 short: str, endpoint: str, tone: str = "brand",
                 schedule: str = "每小时"):
        self.id = spider_id
        self.module_name = module_name  # e.g. "zhaopin_spider"
        self.name = name
        self.short = short
        self.endpoint = endpoint
        self.tone = tone
        self.schedule = schedule

    @property
    def script_path(self) -> Path:
        return SPIDERS_DIR / f"{self.module_name}.py"

    def exists(self) -> bool:
        return self.script_path.exists()

    def to_dict(self, running: bool = False, progress: int = 0,
                enabled: bool = True) -> dict:
        # 读取最新输出统计
        today_count, success_rate, duration = self._collect_stats()
        return {
            "id": self.id,
            "name": self.name,
            "short": self.short,
            "endpoint": self.endpoint,
            "tone": self.tone,
            "enabled": enabled,
            "running": running,
            "today": today_count,
            "success": success_rate,
            "duration": duration,
            "progress": progress,
            "schedule": self.schedule,
            "nextRun": "运行中" if running else self._guess_next_run(),
        }

    def _collect_stats(self) -> tuple[str, float, str]:
        """从最新输出文件统计今日数据量和成功率"""
        latest = self._latest_output()
        if not latest:
            return "0", 100.0, "—"

        try:
            with open(latest, "r", encoding="utf-8") as f:
                records = json.load(f)
        except (json.JSONDecodeError, OSError):
            return "0", 100.0, "—"

        total = len(records)
        if total == 0:
            return "0", 100.0, "—"

        # 计算今日入库数
        today = datetime.date.today().isoformat()
        today_count = sum(
            1 for r in records
            if (r.get("crawled_at") or "").startswith(today)
        )

        # 统计有效数据率（有 jd_text 的视为有效）
        valid = sum(1 for r in records if r.get("jd_text"))
        success_rate = round(valid / total * 100, 1)

        return str(today_count), success_rate, "—"

    def _latest_output(self) -> Optional[Path]:
        """找到最新的输出 JSON 文件"""
        pattern = re.compile(rf"^{self.module_name.replace('_spider','')}_(\d+)\.json$")
        candidates = []
        for search_dir in [DATA_DIR, SCRIPTS_DIR]:
            if not search_dir.exists():
                continue
            for fname in os.listdir(search_dir):
                m = pattern.match(fname)
                if m:
                    candidates.append((search_dir / fname, int(m.group(1))))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    @staticmethod
    def _guess_next_run() -> str:
        now = datetime.datetime.now()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        return next_hour.strftime("%H:%M")


# 已注册的爬虫
REGISTERED_SPIDERS = [
    SpiderMeta(1, "zhaopin_spider", "智联招聘", "ZL", "zhaopin.com", "brand"),
    SpiderMeta(2, "iflytek_spider", "科大讯飞", "XF", "iflytek.com", "violet"),
]


class CrawlerService:
    """爬虫服务"""

    def __init__(self):
        self._running_tasks: dict[int, subprocess.Popen] = {}
        self._running_since: dict[int, float] = {}
        self._progress: dict[int, int] = {}
        self._progress_info: dict[int, str] = {}
        self._stderr: dict[int, list[str]] = {}
        self._stdout: dict[int, list[str]] = {}
        self._enabled: dict[int, bool] = {1: True, 2: True}  # 爬虫启停状态
        self._last_runs: dict[int, dict] = {}

    # ------------------------------------------------------------------
    # 后台线程：读取子进程输出
    # ------------------------------------------------------------------

    def _read_output(self, spider_id: int, proc: subprocess.Popen):
        """后台线程：读取 stderr（进度）+ stdout，全部缓存"""
        page_pattern = re.compile(r"正在采集第\s*(\d+)\s*/\s*(\d+)\s*页")
        stderr_lines = self._stderr.setdefault(spider_id, [])
        stdout_lines = self._stdout.setdefault(spider_id, [])
        try:
            for line in proc.stderr:
                stderr_lines.append(line)
                m = page_pattern.search(line)
                if m:
                    current = int(m.group(1))
                    total = int(m.group(2))
                    self._progress[spider_id] = min(int(current / total * 100), 95)
                    self._progress_info[spider_id] = f"第 {current}/{total} 页"
        except (ValueError, OSError):
            pass
        try:
            for line in proc.stdout:
                stdout_lines.append(line)
        except (ValueError, OSError):
            pass

    # ------------------------------------------------------------------
    # 数据总览
    # ------------------------------------------------------------------

    async def get_overview(self, db: AsyncSession) -> dict:
        """构造 AdminOverview 字典，与前端 AdminOverview 结构对齐"""
        crawlers = self._list_crawlers()
        pipeline_summary, qualities = await self._get_pipeline_summary(db)
        monitoring = await self._get_monitoring(db)
        return {
            "metrics": self._get_metrics(pipeline_summary),
            "services": self._get_services(),
            "resources": self._get_resources(),
            "recentTasks": self._get_recent_tasks(),
            "systemEvents": [],
            "crawlers": crawlers,
            "pipelineSummary": pipeline_summary,
            "qualities": qualities,
            "crawlerPolicy": self._get_policy(),
            **monitoring,
        }

    # ------------------------------------------------------------------
    # 爬虫控制
    # ------------------------------------------------------------------

    def run_spider(self, spider_id: int) -> dict:
        """启动爬虫（异步子进程）"""
        meta = self._find_spider(spider_id)
        if not meta:
            raise ValueError(f"未知爬虫 ID: {spider_id}")
        if not meta.exists():
            raise FileNotFoundError(f"爬虫脚本不存在: {meta.script_path}")
        if spider_id in self._running_tasks:
            proc = self._running_tasks[spider_id]
            if proc.poll() is None:
                raise RuntimeError(f"爬虫 {meta.name} 正在运行中")

        # 启动子进程（设置输出目录为 data/）
        logger.info("启动爬虫: %s (%s)", meta.name, meta.script_path)
        proc = subprocess.Popen(
            [
                sys.executable,
                str(meta.script_path.relative_to(SCRIPTS_DIR)),
                "--output-dir", str(DATA_DIR),
            ],
            cwd=str(SCRIPTS_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._running_tasks[spider_id] = proc
        self._running_since[spider_id] = time.time()
        self._progress.pop(spider_id, None)
        self._progress_info.pop(spider_id, None)

        # 启动后台线程读取子进程输出
        t = threading.Thread(
            target=self._read_output, args=(spider_id, proc),
            daemon=True,
        )
        t.start()

        return {
            "spider_id": spider_id,
            "name": meta.name,
            "status": "started",
            "pid": proc.pid,
        }

    def get_spider_status(self, spider_id: int) -> dict:
        """获取爬虫运行状态"""
        meta = self._find_spider(spider_id)
        if not meta:
            raise ValueError(f"未知爬虫 ID: {spider_id}")

        running = False
        progress = 0
        progress_info = ""
        enabled = self._enabled.get(spider_id, True)
        if spider_id in self._running_tasks:
            proc = self._running_tasks[spider_id]
            running = proc.poll() is None
            if running:
                if spider_id in self._progress:
                    progress = self._progress[spider_id]
                    progress_info = self._progress_info.get(spider_id, "")
                else:
                    elapsed = time.time() - self._running_since.get(spider_id, time.time())
                    progress = min(int(elapsed / 120 * 100), 20)

        result = meta.to_dict(running=running, progress=progress, enabled=enabled)
        if progress_info:
            result["progress_info"] = progress_info
        return result

    def poll_spider(self, spider_id: int) -> Optional[dict]:
        """轮询爬虫是否完成，完成则返回结果"""
        if spider_id not in self._running_tasks:
            return None

        proc = self._running_tasks[spider_id]
        if proc.poll() is None:
            return None  # 仍在运行

        # 已完成
        meta = self._find_spider(spider_id)
        started = self._running_since.pop(spider_id, time.time())
        proc_obj = self._running_tasks.pop(spider_id)
        self._progress.pop(spider_id, None)
        self._progress_info.pop(spider_id, None)
        elapsed = time.time() - started

        # 等待后台线程读完所有输出（最多等 3 秒）
        proc_obj.wait(timeout=3)

        # 从缓存取 stderr / stdout（避免与后台线程争抢管道）
        stderr_text = "".join(self._stderr.pop(spider_id, []))
        stdout_text = "".join(self._stdout.pop(spider_id, []))

        # 探测最新输出文件
        latest = meta._latest_output()
        records_count = 0
        if latest:
            try:
                with open(latest, "r", encoding="utf-8") as f:
                    records_count = len(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
        output_changed = bool(
            latest and latest.stat().st_mtime >= started - 1
        )
        self._last_runs[spider_id] = {
            "date": datetime.date.today().isoformat(),
            "records_count": records_count,
            "elapsed": round(elapsed, 1),
            "returncode": proc_obj.returncode,
        }

        return {
            "spider_id": spider_id,
            "name": meta.name,
            "records_count": records_count,
            "filepath": str(latest) if latest else "",
            "filename": latest.name if latest else "",
            "output_changed": output_changed,
            "elapsed": round(elapsed, 1),
            "returncode": proc_obj.returncode,
            "stdout": stdout_text[-500:] if stdout_text else "",
            "stderr": stderr_text[-500:] if stderr_text else "",
        }

    def toggle_crawler(self, spider_id: int) -> dict:
        """切换爬虫启停状态"""
        meta = self._find_spider(spider_id)
        if not meta:
            raise ValueError(f"未知爬虫 ID: {spider_id}")
        current = self._enabled.get(spider_id, True)
        self._enabled[spider_id] = not current
        return {"id": spider_id, "enabled": self._enabled[spider_id]}

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _list_crawlers(self) -> list[dict]:
        result = []
        for meta in REGISTERED_SPIDERS:
            running = meta.id in self._running_tasks and self._running_tasks[meta.id].poll() is None
            enabled = self._enabled.get(meta.id, True)
            progress = 0
            progress_info = ""
            if running:
                if meta.id in self._progress:
                    progress = self._progress[meta.id]
                    progress_info = self._progress_info.get(meta.id, "")
                else:
                    elapsed = time.time() - self._running_since.get(meta.id, time.time())
                    progress = min(int(elapsed / 120 * 100), 20)
            item = meta.to_dict(running=running, progress=progress, enabled=enabled)
            last_run = self._last_runs.get(meta.id)
            if last_run and last_run["date"] == datetime.date.today().isoformat():
                item["today"] = str(last_run["records_count"])
                item["success"] = 100.0 if last_run["returncode"] == 0 else 0.0
                item["duration"] = f"{last_run['elapsed']}s"
            if progress_info:
                item["progress_info"] = progress_info
            result.append(item)
        return result

    def _find_spider(self, spider_id: int) -> Optional[SpiderMeta]:
        for meta in REGISTERED_SPIDERS:
            if meta.id == spider_id:
                return meta
        return None

    # ------------------------------------------------------------------
    # 各模块的 Mock/静态数据（后续可替换为真实查询）
    # ------------------------------------------------------------------
    # 这些方法返回与前端 AdminOverview 结构匹配的静态数据，
    # 后续可逐步替换为来自数据库/监控系统的真实数据。

    def _get_metrics(self, summary: dict) -> list[dict]:
        return [
            {"label": "总岗位数", "value": str(summary["totalJobs"]), "trend": f"+{summary['todayImported']} 今日入库", "trendTone": "positive", "icon": "Document", "tone": "brand", "bars": [summary["totalJobs"] % 100]},
            {"label": "数据源", "value": str(summary["sourceCount"]), "trend": "来自真实入库记录", "trendTone": "positive", "icon": "Connection", "tone": "green", "bars": [summary["sourceCount"] * 20]},
            {"label": "有效数据率", "value": f"{summary['validRate']:.1f}%", "trend": f"{summary['validRecords']} / {summary['totalJobs']} 条正文有效", "trendTone": "positive", "icon": "Download", "tone": "violet", "bars": [summary["validRate"]]},
            {"label": "待验证事实", "value": str(summary["unverifiedFacts"]), "trend": f"{summary['verifiedFacts']} 条已验证", "trendTone": "warning" if summary["unverifiedFacts"] else "positive", "icon": "Monitor", "tone": "amber", "bars": [min(summary["unverifiedFacts"], 100)]},
        ]

    async def _get_pipeline_summary(
        self, db: AsyncSession
    ) -> tuple[dict, list[dict]]:
        today = datetime.date.today()
        today_start = datetime.datetime.combine(today, datetime.time.min)
        tomorrow_start = today_start + datetime.timedelta(days=1)

        rows = (
            await db.execute(
                select(
                    RawJobRecord.title,
                    RawJobRecord.company,
                    RawJobRecord.jd_text,
                    RawJobRecord.crawled_at_text,
                    SourceDocument.source,
                    SourceDocument.url,
                    SourceDocument.created_at,
                ).join(
                    SourceDocument,
                    RawJobRecord.source_document_id == SourceDocument.id,
                )
            )
        ).all()
        total = len(rows)
        valid = sum(1 for row in rows if len((row.jd_text or "").strip()) >= 10)
        complete = sum(
            1
            for row in rows
            if all(
                str(value or "").strip()
                for value in (
                    row.title,
                    row.company,
                    row.jd_text,
                    row.crawled_at_text,
                    row.source,
                    row.url,
                )
            )
        )
        today_imported = sum(
            1
            for row in rows
            if row.created_at and today_start <= row.created_at < tomorrow_start
        )
        source_count = len({row.source for row in rows if row.source})

        task_rows = (
            await db.execute(
                select(AsyncTask).where(
                    AsyncTask.task_type == "job_data_import",
                    AsyncTask.created_at >= today_start,
                    AsyncTask.created_at < tomorrow_start,
                )
            )
        ).scalars().all()
        failed_tasks = sum(1 for task in task_rows if task.status == "failed")
        processed = duplicates = 0
        for task in task_rows:
            if task.status != "succeeded" or not task.result:
                continue
            processed += int(task.result.get("total", 0))
            duplicates += int(task.result.get("duplicates", 0))

        fact_rows = (
            await db.execute(
                select(JobSkillFact.verification_status).where(
                    JobSkillFact.raw_job_record_id.is_not(None)
                )
            )
        ).scalars().all()
        verified = sum(1 for status in fact_rows if status == "verified")
        unverified = sum(1 for status in fact_rows if status == "unverified")

        valid_rate = round(valid * 100 / total, 1) if total else 0.0
        completeness_rate = round(complete * 100 / total, 1) if total else 0.0
        duplicate_rate = round(duplicates * 100 / processed, 1) if processed else 0.0
        dedup_valid_rate = round(100 - duplicate_rate, 1) if processed else 0.0
        overall_quality = (
            round(
                (valid_rate + completeness_rate + dedup_valid_rate + 100.0) / 4,
                1,
            )
            if total
            else 0.0
        )

        summary = {
            "totalJobs": total,
            "todayImported": today_imported,
            "sourceCount": source_count,
            "validRecords": valid,
            "validRate": valid_rate,
            "failedTasks": failed_tasks,
            "processedToday": processed,
            "duplicatesToday": duplicates,
            "verifiedFacts": verified,
            "unverifiedFacts": unverified,
            "overallQuality": overall_quality,
        }
        qualities = [
            {"label": "字段完整性", "value": f"{completeness_rate:.1f}%", "percent": round(completeness_rate), "color": "#34b37e", "note": f"{complete} / {total} 条核心字段完整"},
            {"label": "去重有效率", "value": f"{dedup_valid_rate:.1f}%", "percent": round(dedup_valid_rate), "color": "#4f6ef6", "note": f"今日识别重复 {duplicates} 条"},
            {"label": "文本有效", "value": f"{valid_rate:.1f}%", "percent": round(valid_rate), "color": "#34b37e", "note": f"{valid} / {total} 条 JD 正文有效"},
            {"label": "格式规范", "value": "100.0%" if total else "0.0%", "percent": 100 if total else 0, "color": "#34b37e", "note": "入库记录均已通过 job-v1"},
        ]
        return summary, qualities

    def _get_services(self) -> list[dict]:
        return [
            {"name": "MySQL", "desc": "主数据库", "icon": "Coin", "tone": "brand", "latency": "3ms"},
            {"name": "Neo4j", "desc": "技能图谱", "icon": "Share", "tone": "violet", "latency": "5ms"},
            {"name": "Redis", "desc": "缓存服务", "icon": "Clock", "tone": "amber", "latency": "1ms"},
            {"name": "Agent", "desc": "AI 任务引擎", "icon": "MagicStick", "tone": "green", "latency": "45ms"},
            {"name": "Crawler", "desc": "数据采集服务", "icon": "Download", "tone": "brand", "latency": "—"},
        ]

    def _get_resources(self) -> list[dict]:
        return [
            {"label": "CPU", "value": 23, "color": "#4f6ef6", "detail": "2.1 GHz"},
            {"label": "内存", "value": 47, "color": "#34b37e", "detail": "3.8 / 8 GB"},
            {"label": "磁盘", "value": 32, "color": "#f59e4b", "detail": "64 / 200 GB"},
        ]

    def _get_recent_tasks(self) -> list[dict]:
        now = datetime.datetime.now()
        tasks = []
        for meta in REGISTERED_SPIDERS:
            latest = meta._latest_output()
            count = 0
            if latest:
                try:
                    with open(latest, "r", encoding="utf-8") as f:
                        count = len(json.load(f))
                except (json.JSONDecodeError, OSError):
                    pass
            tasks.append({
                "name": meta.name,
                "source": meta.endpoint,
                "time": "刚刚" if meta.id in self._running_tasks else "上次运行",
                "count": f"{count} 条",
                "status": "running" if meta.id in self._running_tasks and self._running_tasks[meta.id].poll() is None else "success",
                "statusLabel": "采集中" if meta.id in self._running_tasks and self._running_tasks[meta.id].poll() is None else "已完成",
                "icon": "VideoPlay" if meta.id in self._running_tasks else "CircleCheck",
            })
        return tasks

    def _get_policy(self) -> dict:
        return {"concurrency": 4, "retries": 3, "interval": 5, "deduplicate": True}

    async def _get_monitoring(self, db: AsyncSession) -> dict:
        """从事实表和异步任务审计表构造监控数据，不返回演示型指标。"""
        status_rows = (
            await db.execute(
                select(
                    JobSkillFact.verification_status,
                    func.count(JobSkillFact.id),
                ).group_by(JobSkillFact.verification_status)
            )
        ).all()
        status_counts = {status: int(count) for status, count in status_rows}
        verified = status_counts.get("verified", 0)
        unverified = status_counts.get("unverified", 0)
        rejected = status_counts.get("rejected", 0)
        total = sum(status_counts.values())
        reviewed = verified + rejected
        verified_rate = round(verified * 100 / total, 1) if total else 0.0

        task_rows = (
            await db.execute(
                select(AsyncTask).order_by(AsyncTask.created_at.desc()).limit(20)
            )
        ).scalars().all()
        succeeded_tasks = sum(1 for task in task_rows if task.status == "succeeded")
        failed_tasks = sum(1 for task in task_rows if task.status == "failed")

        reviewed_rows = (
            await db.execute(
                select(JobSkillFact, Skill.name, User.username)
                .join(Skill, JobSkillFact.skill_id == Skill.id)
                .outerjoin(User, JobSkillFact.reviewed_by == User.id)
                .where(JobSkillFact.reviewed_at.is_not(None))
                .order_by(JobSkillFact.reviewed_at.desc())
                .limit(20)
            )
        ).all()

        logs: list[dict] = []
        for task in task_rows:
            result = task.result or {}
            if task.status == "failed":
                level = "ERROR"
                detail = task.error_message or task.error_code or "任务执行失败"
            elif task.status == "succeeded":
                level = "INFO"
                detail = (
                    f"处理 {int(result.get('total', 0))} 条，"
                    f"入库 {int(result.get('imported', 0))} 条，"
                    f"重复 {int(result.get('duplicates', 0))} 条"
                )
            else:
                level = "WARN"
                detail = f"进度 {task.progress}%"
            logs.append({
                "id": f"task-{task.id}",
                "timestamp": task.finished_at or task.started_at or task.created_at,
                "time": self._format_event_time(task.finished_at or task.started_at or task.created_at),
                "level": level,
                "service": f"task.{task.task_type}",
                "message": f"{task.status} · {detail}",
            })

        for fact, skill_name, reviewer_name in reviewed_rows:
            decision = "确认" if fact.verification_status == "verified" else "驳回"
            logs.append({
                "id": f"fact-{fact.id}",
                "timestamp": fact.reviewed_at,
                "time": self._format_event_time(fact.reviewed_at),
                "level": "INFO" if fact.verification_status == "verified" else "WARN",
                "service": "skill.fact.review",
                "message": (
                    f"{reviewer_name or '管理员'}{decision}事实 #{fact.id} "
                    f"{skill_name} · {fact.review_note or '未填写备注'}"
                ),
            })

        logs.sort(
            key=lambda item: item["timestamp"].timestamp() if item["timestamp"] else 0,
            reverse=True,
        )
        for item in logs:
            item.pop("timestamp", None)

        return {
            "performanceCards": [
                {"label": "技能事实总量", "value": str(total), "note": "MySQL 实时统计", "tone": "brand", "bars": [min(total, 100)]},
                {"label": "事实确认率", "value": f"{verified_rate:.1f}%", "note": f"{verified} 条已确认", "tone": "green", "bars": [verified_rate]},
                {"label": "待审核事实", "value": str(unverified), "note": "等待管理员处理", "tone": "amber", "bars": [min(unverified, 100)]},
                {"label": "已驳回事实", "value": str(rejected), "note": "保留审核证据", "tone": "rose", "bars": [min(rejected, 100)]},
            ],
            "endpoints": [
                {"method": "GET", "path": "/api/v1/skills/facts/reviews", "value": f"{total} 条", "percent": 100 if total else 0},
                {"method": "PATCH", "path": "/api/v1/skills/facts/{id}/review", "value": f"{reviewed} 条", "percent": round(reviewed * 100 / total) if total else 0},
                {"method": "POST", "path": "/api/v1/data-imports/jobs", "value": f"{len(task_rows)} 次", "percent": round(succeeded_tasks * 100 / len(task_rows)) if task_rows else 0},
                {"method": "GET", "path": "/api/v1/tasks/{id}", "value": f"{failed_tasks} 次失败", "percent": round(failed_tasks * 100 / len(task_rows)) if task_rows else 0},
            ],
            "logs": logs[:30],
        }

    @staticmethod
    def _format_event_time(value: datetime.datetime | None) -> str:
        return value.strftime("%m-%d %H:%M:%S") if value else "时间未知"
