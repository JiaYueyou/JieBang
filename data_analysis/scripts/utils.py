"""清洗流水线共用工具函数。"""

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 将后端源码加入 import 路径，复用领域层代码
_BACKEND_SRC = Path(__file__).resolve().parents[2] / "fyz-src" / "backend"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

# ── 路径配置 ──────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT.parent / "data"
OUTPUT_DIR = ROOT / "outputs"

DATA_FILES = [
    DATA_DIR / "jd_crawl_ifly.json",
    DATA_DIR / "jd_crawl_zl.json",
    DATA_DIR / "jd_crawl2.json",
]

OUTPUT_MERGED = OUTPUT_DIR / "merged_jobs.json"
OUTPUT_TITLE_MAP = OUTPUT_DIR / "title_mapping.json"
OUTPUT_SKILL_DICT = OUTPUT_DIR / "skill_dict.json"
OUTPUT_JOB_SKILL_MATRIX = OUTPUT_DIR / "job_skill_matrix.json"
OUTPUT_REFERENCE = OUTPUT_DIR / "reference_dataset.json"

DEDUP_THRESHOLD = 85  # title+company 相似度阈值


# ── JSON 读写 ─────────────────────────────────────────

def read_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 日志 ──────────────────────────────────────────────

def log(step: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{step}] {msg}")


def log_sep(title: str = "") -> None:
    sep = "=" * 60
    print(f"\n{sep}")
    if title:
        print(f"  {title}")
        print(sep)


# ── 文本清洗（复用后端逻辑的简化版）──────────────────

def normalize_text(value: str | list | None) -> str:
    if isinstance(value, list):
        value = "\n".join(str(item) for item in value)
    return re.sub(r"\s+", " ", str(value or "")).strip()


def content_fingerprint(record: dict) -> str:
    """基于 source+url+title+company+posted_at+jd_text 生成去重指纹。"""
    payload = "|".join(
        normalize_text(record.get(key)).casefold()
        for key in ("source", "url", "title", "company", "posted_at", "jd_text")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── 字符串相似度（用于标题去重）──────────────────────

def text_similarity(a: str, b: str) -> float:
    """简化的 Jaccard 字符二元组相似度。"""
    if not a or not b:
        return 0.0
    a, b = a.casefold().strip(), b.casefold().strip()
    if a == b:
        return 100.0
    pairs_a = {a[i:i+2] for i in range(len(a) - 1)}
    pairs_b = {b[i:i+2] for i in range(len(b) - 1)}
    if not pairs_a or not pairs_b:
        return 0.0
    intersection = pairs_a & pairs_b
    union = pairs_a | pairs_b
    return round(len(intersection) / len(union) * 100, 1)


# ── 薪资解析 ──────────────────────────────────────────

def parse_salary(raw: str) -> dict | None:
    """'15K-25K' → {'min': 15000, 'max': 25000} | None"""
    if not raw or raw in ("面议", "薪资面议"):
        return None
    raw = raw.replace(" ", "").upper()
    unit = 1
    if "K" in raw or "K" in raw:
        unit = 1000
    raw = raw.replace("K", "").replace("K", "")
    nums = re.findall(r"\d+", raw)
    if not nums:
        return None
    nums = [int(n) * unit for n in nums]
    if len(nums) == 1:
        return {"min": nums[0], "max": nums[0]}
    return {"min": nums[0], "max": nums[1]}


# ── 经验解析 ──────────────────────────────────────────

def parse_experience(raw: str) -> dict | None:
    """'3-5年' → {'min': 3, 'max': 5} | '经验不限' → None"""
    if not raw or "不限" in raw or "无要求" in raw:
        return None
    nums = [int(n) for n in re.findall(r"\d+", raw)]
    if not nums:
        return None
    if len(nums) == 1:
        return {"min": nums[0], "max": nums[0]}
    return {"min": nums[0], "max": nums[1]}


# ── 学历解析 ──────────────────────────────────────────

EDUCATION_MAP = {
    "大专": "college",
    "本科": "bachelor",
    "硕士": "master",
    "博士": "phd",
    "MBA": "mba",
    "EMBA": "emba",
    "中专": "secondary",
    "高中": "high_school",
}


def parse_education(raw: str) -> str | None:
    """'本科及以上' → 'bachelor' | None"""
    if not raw or "不限" in raw:
        return None
    for cn, en in sorted(EDUCATION_MAP.items(), key=lambda x: -len(x[0])):
        if cn in raw:
            return en
    return None


# ── 字段统一（jd_crawl2 的 key 名不同）────────────────

FIELD_ALIAS_MAP = {
    "keyword": "keywords",
}

STANDARD_FIELDS = [
    "title", "company", "city", "salary", "experience", "education",
    "jd_text", "responsibilities", "requirements", "keywords",
    "posted_at", "url", "source", "crawled_at",
]


def normalize_record(record: dict) -> dict:
    """统一字段名、填充缺失字段、清洗空值。"""
    out = {}
    for field in STANDARD_FIELDS:
        val = record.get(field)
        # 处理别名
        if val is None and field in FIELD_ALIAS_MAP.values():
            for alias, target in FIELD_ALIAS_MAP.items():
                if target == field and alias in record:
                    val = record[alias]
                    break
        out[field] = normalize_text(val) if isinstance(val, (str, list)) else val
    return out


def quality_score(record: dict) -> float:
    """计算字段完整率（0~1），jd_text 为空直接返回 0。"""
    if not record.get("jd_text"):
        return 0.0
    filled = sum(1 for field in STANDARD_FIELDS if record.get(field))
    return round(filled / len(STANDARD_FIELDS), 2)
