"""岗位标题确定性清洗、标准岗位身份与图谱展示维度推断。"""

from __future__ import annotations

from dataclasses import dataclass
import re

NORMALIZATION_VERSION = "job-title-v3"

_NOISE = (
    "急聘", "诚聘", "高薪", "双休", "五险一金", "接受应届", "校招", "社招",
    "外包", "驻场", "直招", "包吃住", "周末双休", "年底双薪",
)
_LEVEL_WORDS = (
    "初级", "中级", "高级", "资深", "专家", "首席", "助理", "实习生", "应届生",
    "junior", "middle", "mid-level", "senior",
)
_CITY_ALIASES = {
    "北京": "110000", "上海": "310000", "天津": "120000", "重庆": "500000",
    "广州": "440100", "深圳": "440300", "杭州": "330100", "南京": "320100",
    "苏州": "320500", "成都": "510100", "武汉": "420100", "西安": "610100",
    "合肥": "340100", "长沙": "430100", "郑州": "410100", "济南": "370100",
    "青岛": "370200", "厦门": "350200", "福州": "350100", "宁波": "330200",
    "无锡": "320200", "东莞": "441900", "佛山": "440600", "珠海": "440400",
    "大连": "210200", "沈阳": "210100", "长春": "220100", "哈尔滨": "230100",
    "石家庄": "130100", "太原": "140100", "南昌": "360100", "昆明": "530100",
    "贵阳": "520100", "南宁": "450100", "海口": "460100", "兰州": "620100",
    "乌鲁木齐": "650100", "呼和浩特": "150100", "银川": "640100", "西宁": "630100",
    "拉萨": "540100", "香港": "810000", "澳门": "820000", "全国": "000000",
    "远程": "REMOTE",
}
_TECH_CANONICAL = {
    "python": "Python", "java": "Java", "javascript": "JavaScript", "typescript": "TypeScript",
    "ai": "AI", "llm": "LLM", "nlp": "NLP", "c＋＋": "C++", "c#": "C#",
    "golang": "Go", "devops": "DevOps", "sre": "SRE",
}

# 企业招聘标题经常在连字符后拼接业务线、产品或公司内部组织。这些字段
# 只能作为岗位来源维度，不能参与跨企业岗位身份的 canonical key。
_BUSINESS_SUFFIX_MARKERS = (
    "抖音", "tiktok", "火山", "字节", "飞书", "lark", "今日头条",
    "西瓜", "生活服务", "tiktokshop", "芯片研发", "国际电商", "data",
)


@dataclass(frozen=True)
class JobTitleNormalization:
    name: str
    canonical_key: str
    level: str
    confidence: float
    role_family: str
    specialization_key: str
    occupation_code: str
    city_code: str | None
    company_key: str | None
    work_mode: str
    employment_type: str
    status: str
    version: str = NORMALIZATION_VERSION


def normalize_job_title(
    title: str,
    *,
    city: str | None = None,
    company: str | None = None,
    jd_text: str | None = None,
) -> JobTitleNormalization:
    """将易变的招聘标题拆成稳定岗位身份和独立业务维度。"""
    original = re.sub(r"\s+", " ", title or "").strip()
    level = infer_job_level(original)
    city_code = normalize_city_code(city) or _city_code_from_title(original)

    value = re.sub(r"[（(][^（）()]{0,40}[）)]", "", original)
    value = re.sub(r"【[^】]{0,40}】", "", value)
    city_pattern = "|".join(sorted(map(re.escape, _CITY_ALIASES), key=len, reverse=True))
    value = re.sub(rf"\s*[-—|·/]\s*(?:{city_pattern})(?:市|地区)?(?:.*)$", "", value, flags=re.IGNORECASE)
    value = re.sub(rf"^(?:{city_pattern})(?:市|地区)?\s*[-—|·/]\s*", "", value, flags=re.IGNORECASE)
    for word in _NOISE:
        value = value.replace(word, "")
    for word in _LEVEL_WORDS:
        value = re.sub(re.escape(word), "", value, flags=re.IGNORECASE)
    value = re.sub(r"\d+\s*[-~至]\s*\d+\s*年|\d+\s*年以上|经验不限", "", value)
    value = re.sub(r"\s+", "", value).strip("-—_|·/、")
    value = _strip_business_suffix(value)
    for raw, normalized in _TECH_CANONICAL.items():
        value = re.sub(raw, normalized, value, flags=re.IGNORECASE)
    value = value.replace("软件研发工程师", "软件开发工程师").replace("研发工程师", "开发工程师")
    value = re.sub(r"forwarddeployedengineer", "前置部署工程师", value, flags=re.IGNORECASE)
    value = re.sub(r"^后端[/、-]?后端开发工程师", "后端开发工程师", value)
    if not value:
        value = original or "未命名岗位"

    role_family = infer_role_family(value)
    base_key = _canonical_key(value)
    specialization_key = _specialization_key(value, role_family)
    # 地区、公司和用工形式不进入标准岗位身份；职级显式进入，避免不同能力层级误合并。
    canonical_key = f"{base_key}:{level}"
    occupation_code = f"{role_family}:{specialization_key}:{level}"
    confidence = 0.96
    status = "normalized"
    if value == "未命名岗位" or role_family == "general":
        confidence = 0.68
        status = "needs_review"
    if any(token in original for token in ("/", "兼", "及以上")):
        confidence = min(confidence, 0.82)

    combined = f"{original} {jd_text or ''}"
    return JobTitleNormalization(
        name=value[:180],
        canonical_key=canonical_key[:220],
        level=level,
        confidence=confidence,
        role_family=role_family,
        specialization_key=specialization_key[:160],
        occupation_code=occupation_code[:220],
        city_code=city_code,
        company_key=normalize_company_key(company),
        work_mode=infer_work_mode(combined),
        employment_type=infer_employment_type(combined),
        status=status,
    )


def standardize_job_title(title: str) -> tuple[str, str, str, float]:
    """兼容旧调用方；新代码优先使用 :func:`normalize_job_title`."""
    result = normalize_job_title(title)
    return result.name, result.canonical_key, result.level, result.confidence


def normalize_city_code(city: str | None) -> str | None:
    compact = re.sub(r"\s+", "", city or "")
    if not compact:
        return None
    for alias, code in _CITY_ALIASES.items():
        if alias in compact:
            return code
    return f"OTHER:{_canonical_key(compact)[:32]}"


def normalize_company_key(company: str | None) -> str | None:
    value = re.sub(r"[（(].*?[）)]", "", company or "")
    value = re.sub(r"有限责任公司|股份有限公司|有限公司|集团|公司", "", value)
    key = _canonical_key(value)
    return key[:160] or None


def infer_job_level(title: str) -> str:
    lowered = (title or "").casefold()
    if any(word in lowered for word in ("资深", "高级", "专家", "首席", "架构", "senior")):
        return "senior"
    if any(word in lowered for word in ("初级", "助理", "实习", "应届", "junior")):
        return "junior"
    return "middle"


def infer_role_family(title: str) -> str:
    lowered = (title or "").casefold()
    rules = (
        ("algorithm", ("算法", "大模型", "机器学习", "人工智能", "ai", "nlp", "视觉", "语音")),
        ("data", ("数据", "数仓", "大数据", "flink", "spark", "bi")),
        ("devops", ("运维", "devops", "云平台", "sre", "网络", "安全", "部署工程师")),
        ("test", ("测试", "质量", "qa")),
        ("frontend", ("前端", "web", "javascript", "vue", "react")),
        ("backend", ("后端", "服务端", "开发工程师", "软件工程师", "java", "python", "golang")),
        ("product", ("产品经理", "产品运营")),
        ("design", ("设计师", "交互", "ui", "ux")),
        ("sales", ("销售", "客户经理", "商务")),
        ("operations", ("运营", "招商主管", "商家")),
    )
    for family, words in rules:
        if any(word in lowered for word in words):
            return family
    return "general"


def infer_job_stack(title: str) -> str:
    family = infer_role_family(title)
    return {"algorithm": "ai", "data": "data", "devops": "devops"}.get(family, "backend")


def infer_work_mode(text: str) -> str:
    lowered = (text or "").casefold()
    if any(word in lowered for word in ("远程", "remote", "居家办公")):
        return "remote"
    if any(word in lowered for word in ("混合办公", "hybrid")):
        return "hybrid"
    return "onsite"


def infer_employment_type(text: str) -> str:
    lowered = (text or "").casefold()
    if any(word in lowered for word in ("实习", "intern")):
        return "internship"
    if any(word in lowered for word in ("兼职", "part-time")):
        return "part_time"
    if any(word in lowered for word in ("外包", "合同工", "contract")):
        return "contract"
    return "full_time"


def _city_code_from_title(title: str) -> str | None:
    for alias, code in _CITY_ALIASES.items():
        if re.search(rf"(?:^|[-—|·/（(])\s*{re.escape(alias)}(?:市|地区)?(?:$|[-—|·/）)])", title):
            return code
    return None


def _canonical_key(value: str) -> str:
    return "".join(ch for ch in (value or "").casefold() if ch.isalnum())


def _specialization_key(value: str, role_family: str) -> str:
    compact = re.sub(r"工程师|开发|经理|专员|顾问|设计师|研究员|架构师", "", value)
    return _canonical_key(compact) or role_family


def _strip_business_suffix(value: str) -> str:
    """Remove only known company/product suffixes, never arbitrary specialties."""
    parts = re.split(r"[-—|·]", value, maxsplit=1)
    if len(parts) != 2:
        return value
    role, suffix = (part.strip() for part in parts)
    if not role or not suffix:
        return value
    lowered = suffix.casefold()
    if any(marker in lowered for marker in _BUSINESS_SUFFIX_MARKERS):
        return role
    return value


CATEGORY_STACK = {
    "ai_ml": "ai", "cloud": "devops", "database": "data", "domain_knowledge": "data",
    "programming_language": "backend", "framework": "backend", "tool": "devops",
    "soft_skill": "backend",
}
