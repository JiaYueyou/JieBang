"""爬虫服务 — 管理爬虫脚本执行与数据采集"""

from __future__ import annotations

import asyncio
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

import psutil
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DEEPSEEK_API_KEY, TESTING
from app.core.neo4j import health_check as neo4j_health_check
from app.models import (
    AgentRun,
    AsyncTask,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    User,
)

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
                 schedule: str = "手动触发"):
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
            "nextRun": "运行中" if running else "等待手动触发",
        }

    def _collect_stats(self) -> tuple[str, float | None, str]:
        """从最新输出文件统计今日数据量和成功率"""
        latest = self._latest_output()
        if not latest:
            return "0", None, "—"

        try:
            with open(latest, "r", encoding="utf-8") as f:
                records = json.load(f)
        except (json.JSONDecodeError, OSError):
            return "0", None, "—"

        total = len(records)
        if total == 0:
            return "0", None, "—"

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

# 已注册的爬虫
REGISTERED_SPIDERS = [
    SpiderMeta(1, "zhaopin_spider", "智联招聘", "ZL", "zhaopin.com", "brand"),
    SpiderMeta(2, "iflytek_spider", "科大讯飞", "XF", "iflytek.com", "violet"),
]

# 采集结果分类（poll_spider 返回的 error_category）
CRAWLER_STATUS_OK = "ok"            # 采集成功且生成新数据
CRAWLER_STATUS_NO_DATA = "no_data"  # 采集完成但未产生新数据（反爬/超时/内容无变化等）
CRAWLER_STATUS_RUN_FAILED = "run_failed"  # 采集脚本异常退出


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
        self._network_sample: tuple[float, int, int] | None = None

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
        services = await self._get_services(db)
        resources, traffic = await asyncio.to_thread(self._get_resources)
        recent_tasks = await self._get_recent_tasks(db)
        system_events = await self._get_system_events(
            db,
            services=services,
            unverified_facts=pipeline_summary["unverifiedFacts"],
        )
        return {
            "metrics": self._get_metrics(pipeline_summary),
            "services": services,
            "resources": resources,
            "traffic": traffic,
            "recentTasks": recent_tasks,
            "systemEvents": system_events,
            "crawlers": crawlers,
            "pipelineSummary": pipeline_summary,
            "qualities": qualities,
            "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
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
        stats = self._parse_spider_stats(stderr_text)
        returncode = proc_obj.returncode

        # 结构化采集结果分类，供前端给出友好提示（而非静默失败）
        if returncode != 0:
            error_category = CRAWLER_STATUS_RUN_FAILED
            error_reason = "exception"
            message = (
                f"{meta.name}采集脚本异常退出（退出码 {returncode}），"
                "请查看下方日志与网络环境后重试"
            )
        elif output_changed and records_count > 0:
            error_category = CRAWLER_STATUS_OK
            error_reason = ""
            message = f"采集完成，共 {records_count} 条记录"
        else:
            error_category = CRAWLER_STATUS_NO_DATA
            if stats["fetched"] == 0 and stats["errors"] > 0:
                error_reason = "network"
                message = (
                    f"未采集到有效数据：请求错误 {stats['errors']} 次。"
                    "可能是目标站点网络不通、访问超时或被反爬拦截，请检查网络后重试"
                )
            elif stats["fetched"] == 0:
                error_reason = "no_response"
                message = (
                    "未采集到有效数据。可能是站点页面结构变更、需要登录或验证码，"
                    "导致数据接口未被触发，请人工确认站点可访问性"
                )
            else:
                error_reason = "unchanged"
                message = (
                    f"本次采集到 {stats['fetched']} 条，但与最近快照业务内容一致，"
                    "未生成新数据文件"
                )

        self._last_runs[spider_id] = {
            "date": datetime.date.today().isoformat(),
            "records_count": records_count,
            "elapsed": round(elapsed, 1),
            "returncode": returncode,
            "error_category": error_category,
        }

        return {
            "spider_id": spider_id,
            "name": meta.name,
            "records_count": records_count,
            "filepath": str(latest) if latest else "",
            "filename": latest.name if latest else "",
            "output_changed": output_changed,
            "elapsed": round(elapsed, 1),
            "returncode": returncode,
            "stdout": stdout_text[-500:] if stdout_text else "",
            "stderr": stderr_text[-500:] if stderr_text else "",
            "error_category": error_category,
            "error_reason": error_reason,
            "message": message,
            "stats": stats,
        }

    @staticmethod
    def _parse_spider_stats(stderr_text: str) -> dict:
        """从爬虫脚本 print_stats 输出（写入 stderr）解析采集统计。

        spider 框架的 print_stats 通过 logging 输出：
          抓取成功: N 条 / 去重跳过: N 条 / 错误次数: N 次 / 已爬页数: N 页
        """
        stats = {"fetched": 0, "duplicates": 0, "errors": 0, "pages": 0}
        if not stderr_text:
            return stats
        patterns = {
            "fetched": r"抓取成功[:：]\s*(\d+)\s*条",
            "duplicates": r"去重跳过[:：]\s*(\d+)\s*条",
            "errors": r"错误次数[:：]\s*(\d+)\s*次",
            "pages": r"已爬页数[:：]\s*(\d+)\s*页",
        }
        for key, pattern in patterns.items():
            m = re.search(pattern, stderr_text)
            if m:
                stats[key] = int(m.group(1))
        return stats

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
                select(JobSkillFact.verification_status)
            )
        ).scalars().all()
        verified = sum(1 for status in fact_rows if status == "verified")
        unverified = sum(1 for status in fact_rows if status == "unverified")

        valid_rate = round(valid * 100 / total, 1) if total else 0.0
        completeness_rate = round(complete * 100 / total, 1) if total else 0.0
        duplicate_rate = round(duplicates * 100 / processed, 1) if processed else 0.0
        dedup_valid_rate = round(100 - duplicate_rate, 1) if processed else None
        quality_values = [valid_rate, completeness_rate, 100.0]
        if dedup_valid_rate is not None:
            quality_values.append(dedup_valid_rate)
        overall_quality = round(sum(quality_values) / len(quality_values), 1) if total else 0.0

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
            {
                "label": "去重有效率",
                "value": f"{dedup_valid_rate:.1f}%" if dedup_valid_rate is not None else "—",
                "percent": round(dedup_valid_rate) if dedup_valid_rate is not None else 0,
                "color": "#4f6ef6",
                "note": (
                    f"今日识别重复 {duplicates} 条"
                    if processed
                    else "今日暂无岗位导入任务"
                ),
            },
            {"label": "文本有效", "value": f"{valid_rate:.1f}%", "percent": round(valid_rate), "color": "#34b37e", "note": f"{valid} / {total} 条 JD 正文有效"},
            {"label": "格式规范", "value": "100.0%" if total else "0.0%", "percent": 100 if total else 0, "color": "#34b37e", "note": "入库记录均已通过 job-v1"},
        ]
        return summary, qualities

    async def _get_services(self, db: AsyncSession) -> list[dict]:
        """实时探测实际依赖；不调用付费模型，仅读取 Agent 配置与最近运行。"""
        services: list[dict] = []

        mysql_started = time.perf_counter()
        try:
            await db.execute(text("SELECT 1"))
            mysql_status = "healthy"
            mysql_label = "正常"
        except Exception:
            mysql_status = "unavailable"
            mysql_label = "不可用"
        mysql_latency = round((time.perf_counter() - mysql_started) * 1000)
        services.append({
            "name": "MySQL",
            "desc": "业务事实数据库",
            "icon": "Coin",
            "tone": "brand",
            "latency": f"{mysql_latency}ms",
            "status": mysql_status,
            "statusLabel": mysql_label,
        })

        if TESTING:
            neo4j_ok = False
            neo4j_latency = None
            neo4j_label = "测试环境未连接"
        else:
            neo4j_started = time.perf_counter()
            neo4j_ok = await asyncio.to_thread(neo4j_health_check)
            neo4j_latency = round((time.perf_counter() - neo4j_started) * 1000)
            neo4j_label = "正常" if neo4j_ok else "不可用"
        services.append({
            "name": "Neo4j",
            "desc": "技能图谱读模型",
            "icon": "Share",
            "tone": "violet",
            "latency": f"{neo4j_latency}ms" if neo4j_latency is not None else "—",
            "status": "healthy" if neo4j_ok else "unavailable",
            "statusLabel": neo4j_label,
        })

        latest_agent = (
            await db.execute(
                select(AgentRun).order_by(AgentRun.created_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        agent_configured = bool(DEEPSEEK_API_KEY)
        if latest_agent and latest_agent.status == "failed":
            agent_status = "degraded"
            agent_label = "最近运行失败"
        elif agent_configured:
            agent_status = "healthy"
            agent_label = "已配置"
        else:
            agent_status = "degraded"
            agent_label = "模板降级模式"
        services.append({
            "name": "Agent",
            "desc": (
                f"最近运行：{latest_agent.agent_type}"
                if latest_agent
                else "尚无运行记录"
            ),
            "icon": "MagicStick",
            "tone": "green",
            "latency": (
                f"{latest_agent.duration_ms}ms"
                if latest_agent and latest_agent.duration_ms is not None
                else "—"
            ),
            "status": agent_status,
            "statusLabel": agent_label,
        })

        available_spiders = sum(1 for meta in REGISTERED_SPIDERS if meta.exists())
        running_spiders = sum(
            1
            for meta in REGISTERED_SPIDERS
            if meta.id in self._running_tasks
            and self._running_tasks[meta.id].poll() is None
        )
        crawler_ok = available_spiders == len(REGISTERED_SPIDERS)
        services.append({
            "name": "Crawler",
            "desc": f"{available_spiders}/{len(REGISTERED_SPIDERS)} 个采集脚本可用",
            "icon": "Download",
            "tone": "brand",
            "latency": f"{running_spiders} 个运行中",
            "status": "healthy" if crawler_ok else "unavailable",
            "statusLabel": "正常" if crawler_ok else "脚本缺失",
        })
        return services

    def _get_resources(self) -> tuple[list[dict], dict]:
        """读取当前宿主机 CPU、内存、磁盘和网络吞吐。"""
        cpu_value = round(psutil.cpu_percent(interval=0.05), 1)
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(PROJECT_ROOT.anchor or PROJECT_ROOT))
        counters = psutil.net_io_counters()
        now = time.monotonic()

        inbound = outbound = 0.0
        if self._network_sample is not None:
            previous_at, previous_recv, previous_sent = self._network_sample
            elapsed = max(now - previous_at, 0.001)
            inbound = max(counters.bytes_recv - previous_recv, 0) / elapsed
            outbound = max(counters.bytes_sent - previous_sent, 0) / elapsed
        self._network_sample = (now, counters.bytes_recv, counters.bytes_sent)

        resources = [
            {
                "label": "CPU",
                "value": cpu_value,
                "color": "#4f6ef6",
                "detail": (
                    f"{cpu_freq.current / 1000:.2f} GHz · {psutil.cpu_count()} 线程"
                    if cpu_freq
                    else f"{psutil.cpu_count()} 线程"
                ),
            },
            {
                "label": "内存",
                "value": round(memory.percent, 1),
                "color": "#34b37e",
                "detail": (
                    f"{self._format_bytes(memory.used)} / "
                    f"{self._format_bytes(memory.total)}"
                ),
            },
            {
                "label": "磁盘",
                "value": round(disk.percent, 1),
                "color": "#f59e4b",
                "detail": (
                    f"{self._format_bytes(disk.used)} / "
                    f"{self._format_bytes(disk.total)}"
                ),
            },
        ]
        traffic = {
            "inbound": self._format_rate(inbound),
            "outbound": self._format_rate(outbound),
            "receivedTotal": self._format_bytes(counters.bytes_recv),
            "sentTotal": self._format_bytes(counters.bytes_sent),
        }
        return resources, traffic

    def get_resources_snapshot(self) -> dict:
        """Return a lightweight host-resource sample for foreground polling."""
        resources, traffic = self._get_resources()
        return {
            "resources": resources,
            "traffic": traffic,
            "sampledAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    async def _get_recent_tasks(self, db: AsyncSession) -> list[dict]:
        task_rows = (
            await db.execute(
                select(AsyncTask)
                .where(AsyncTask.task_type == "job_data_import")
                .order_by(AsyncTask.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        result: list[dict] = []
        for task in task_rows:
            task_result = task.result or {}
            files = (task.request_data or {}).get("files") or []
            source = "、".join(str(item) for item in files) or "数据库导入"
            status = {
                "queued": "warning",
                "running": "running",
                "succeeded": "success",
                "degraded": "warning",
                "failed": "warning",
                "cancelled": "warning",
            }.get(task.status, "warning")
            status_label = {
                "queued": "排队中",
                "running": "运行中",
                "succeeded": "已完成",
                "degraded": "降级完成",
                "failed": "失败",
                "cancelled": "已取消",
            }.get(task.status, task.status)
            result.append({
                "id": task.id,
                "name": "岗位数据导入",
                "source": source,
                "time": self._format_event_time(
                    task.finished_at or task.started_at or task.created_at
                ),
                "count": f"{int(task_result.get('total', 0))} 条",
                "status": status,
                "statusLabel": status_label,
                "icon": "CircleCheck" if task.status == "succeeded" else "Warning",
            })
        return result

    async def _get_system_events(
        self,
        db: AsyncSession,
        *,
        services: list[dict],
        unverified_facts: int,
    ) -> list[dict]:
        """根据服务探测、待审核事实和任务状态生成需要关注的真实事件。"""
        events: list[dict] = []
        for service in services:
            if service["status"] == "healthy":
                continue
            events.append({
                "title": f"{service['name']}：{service['statusLabel']}",
                "desc": service["desc"],
                "time": "本次巡检",
                "level": (
                    "danger"
                    if service["status"] == "unavailable"
                    else "warning"
                ),
                "icon": "Warning",
                "target": "overview",
            })

        if unverified_facts:
            events.append({
                "title": f"{unverified_facts} 条技能事实待审核",
                "desc": "审核后才会进入正式技能图谱",
                "time": "数据库实时统计",
                "level": "warning",
                "icon": "DocumentChecked",
                "target": "review",
            })

        active_tasks = (
            await db.execute(
                select(func.count(AsyncTask.id)).where(
                    AsyncTask.status.in_(("queued", "running"))
                )
            )
        ).scalar_one()
        failed_tasks = (
            await db.execute(
                select(func.count(AsyncTask.id)).where(
                    AsyncTask.status == "failed"
                )
            )
        ).scalar_one()
        if active_tasks:
            events.append({
                "title": f"{int(active_tasks)} 个异步任务处理中",
                "desc": "可在日志与性能中查看实时状态",
                "time": "数据库实时统计",
                "level": "info",
                "icon": "Clock",
                "target": "monitor",
            })
        if failed_tasks:
            events.append({
                "title": f"{int(failed_tasks)} 个异步任务失败",
                "desc": "请在应用事件流中检查错误信息",
                "time": "数据库累计统计",
                "level": "danger",
                "icon": "Warning",
                "target": "monitor",
            })
        return events[:6]

    @staticmethod
    def _format_bytes(value: float) -> str:
        size = float(value)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @classmethod
    def _format_rate(cls, value: float) -> str:
        return f"{cls._format_bytes(value)}/s"

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
                {"key": "skill_facts", "title": "技能事实总量", "description": "系统已沉淀、可追溯的岗位技能事实", "value": f"{total} 条", "percent": 100 if total else 0},
                {"key": "fact_review", "title": "技能事实审核进度", "description": "已由管理员确认或驳回的事实占比", "value": f"{reviewed} 条", "percent": round(reviewed * 100 / total) if total else 0},
                {"key": "job_import", "title": "岗位数据导入任务", "description": "最近异步任务窗口内的岗位清洗与入库任务", "value": f"{len(task_rows)} 次", "percent": round(succeeded_tasks * 100 / len(task_rows)) if task_rows else 0},
                {"key": "task_failure", "title": "异步任务失败", "description": "最近任务窗口内需要排查的失败记录", "value": f"{failed_tasks} 次", "percent": round(failed_tasks * 100 / len(task_rows)) if task_rows else 0},
            ],
            "logs": logs[:30],
        }

    @staticmethod
    def _format_event_time(value: datetime.datetime | None) -> str:
        return value.strftime("%m-%d %H:%M:%S") if value else "时间未知"
