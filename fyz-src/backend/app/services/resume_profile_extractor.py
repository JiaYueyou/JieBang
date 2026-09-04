from __future__ import annotations

import re
from hashlib import sha256


class ResumeProfileExtractor:
    """Deterministic, local extraction of basic resume profile fields."""

    _NAME_LABEL = re.compile(
        r"(?:姓名|姓[ \t]*名)[ \t]*[:：]?[ \t]*([\u3400-\u9fff·]{2,8})"
    )
    _POSITION = re.compile(
        r"(?:求职意向|期望职位|期望岗位|应聘职位|应聘岗位|目标岗位|目标职位|求职目标|求职岗位|意向岗位)\s*[:：]?\s*([^\n]{2,40})"
    )
    _ROLE = re.compile(
        r"算法工程师|软件工程师|开发工程师|测试工程师|数据工程师|运维工程师|"
        r"产品经理|项目经理|前端开发|后端开发|全栈开发|嵌入式开发|工程师"
    )
    _EXPERIENCE = re.compile(r"(\d{1,2})\s*年(?:以上)?(?:工作|项目)?经验")
    _PHONE_LABEL = re.compile(
        r"(?:手机|电话|联系电话|联系方式|Tel|Phone)\s*[:：]?\s*"
        r"((?:\+?86[-\s]?)?1[3-9]\d(?:[-\s]?\d){8}|(?:\+?\d{1,3}[-\s]?)?\d{3,4}[-\s]\d{6,8})",
        re.I,
    )
    _MOBILE = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?(1[3-9]\d(?:[-\s]?\d){8})(?!\d)")
    _EMAIL = re.compile(r"(?<![\w.+-])([\w.+-]+@[\w-]+(?:\.[\w-]+)+)(?![\w.-])", re.I)
    _DEGREE_ORDER = ("博士", "硕士", "本科", "大专", "专科")
    _INVALID_NAME_LINES = (
        "个人简历", "求职简历", "简历", "求职意向", "教育背景", "教育经历",
        "工作经历", "项目经历", "专业技能", "自我评价", "基本信息",
        "大学", "学院", "学校", "电话", "手机", "联系", "邮箱", "邮件",
        "年龄", "性别", "男岁", "女岁", "海外", "岗位", "职位", "工程师",
        "开发", "北京", "上海", "广州", "深圳", "徐汇", "教育", "测绘",
    )

    def extract(self, text: str) -> dict[str, str | None]:
        lines = [re.sub(r"\s+", " ", line).strip(" |｜") for line in text.splitlines()]
        lines = [line for line in lines if line]
        name = self._extract_name(text, lines)
        position_match = self._POSITION.search(text)
        position = self._clean_value(position_match.group(1)) if position_match else None
        if position is None:
            role_match = self._ROLE.search(text)
            position = role_match.group(0) if role_match else None
        experience_match = self._EXPERIENCE.search(text)
        experience = f"{experience_match.group(1)}年" if experience_match else None
        education = next((degree for degree in self._DEGREE_ORDER if degree in text), None)
        phone = self._extract_phone(text)
        email_match = self._EMAIL.search(text)
        return {
            "name": name,
            "current_position": position,
            "experience": experience,
            "education": education,
            "phone": phone,
            "email": email_match.group(1).lower() if email_match else None,
        }

    def _extract_phone(self, text: str) -> str | None:
        labelled = self._PHONE_LABEL.search(text)
        if labelled:
            return self._normalize_phone(labelled.group(1))
        mobile = self._MOBILE.search(text)
        return self._normalize_phone(mobile.group(0)) if mobile else None

    @staticmethod
    def _normalize_phone(value: str) -> str:
        compact = re.sub(r"[-\s]", "", value)
        return compact.removeprefix("+86") if compact.startswith("+86") else compact[2:] if compact.startswith("86") and len(compact) == 13 else compact

    def _extract_name(self, text: str, lines: list[str]) -> str | None:
        labelled = self._NAME_LABEL.search(text)
        if labelled:
            return self._clean_name(labelled.group(1))
        # An unlabelled name is accepted only when it is the first visible line.
        # Scanning deeper tends to misclassify schools, cities and contact labels.
        for line in lines[:1]:
            compact = re.sub(r"[^\u3400-\u9fff·]", "", line)
            if not 2 <= len(compact) <= 4:
                continue
            if any(marker in compact for marker in self._INVALID_NAME_LINES):
                continue
            return self._clean_name(compact)
        return None

    @staticmethod
    def _clean_name(value: str) -> str | None:
        cleaned = re.sub(r"[^\u3400-\u9fff·]", "", value).strip("·")
        return cleaned[:8] if 2 <= len(cleaned) <= 8 else None

    @staticmethod
    def _clean_value(value: str) -> str | None:
        cleaned = re.split(r"(?:电话|手机|邮箱|E-?mail)", value, maxsplit=1, flags=re.I)[0]
        cleaned = cleaned.strip(" ：:|｜,，;；")
        return cleaned[:40] or None

    @staticmethod
    def pseudonym(name: str | None, text: str) -> str:
        digest = sha256((name or text[:200]).encode("utf-8")).hexdigest()[:10]
        return f"candidate-{digest}"
