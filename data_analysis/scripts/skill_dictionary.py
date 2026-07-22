"""
技能标准词典——统一引用 backend 权威源。

本文件仅为桥接层，实际定义在 fyz-src/backend/app/domain/skill_dictionary.py。
修改技能时请编辑 backend 版本，不要编辑本文件。
"""

import sys
from pathlib import Path

# 自动添加 backend 路径
_BACKEND_DIR = Path(__file__).resolve().parents[2] / "fyz-src" / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.domain.skill_dictionary import (  # noqa: E402, F401
    SKILL_CATEGORIES,
    SKILL_DICT,
    SKILL_ALIASES,
    canonical_key,
    normalize_skill,
)
