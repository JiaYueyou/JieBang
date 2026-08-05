"""
技能标准词典——统一引用 backend 权威源。

本文件仅为桥接层，实际定义在 fyz-src/backend/app/domain/skill_dictionary.py。
修改技能时请编辑 backend 版本，不要编辑本文件。


## 后续变更记录

- **2026-07-22**: 新增别名 `.NET→C#`、`Node→Node.js`、`Pytorch→PyTorch`、`TF→TensorFlow`、`ES6→JavaScript`
- **2026-07-22**: 别名 `AI→大模型` 已回滚。理由：`AI` 含义过宽（可指人工智能领域、AI 算法岗、AI 工具等），不应硬映射到单一技能词条 `大模型`。
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
