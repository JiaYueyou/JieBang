# 技能词典迁移说明（面向成员 D）

## 背景

技能词典此前存在三处副本：

- `fyz-src/backend/app/domain/skill_dictionary.py`（后端领域层）
- `data_analysis/scripts/skill_dictionary.py`（数据分析离线管线）
- 部分抽取器中零散内嵌

这三处副本的内容已出现**不一致**（别名表互有缺失），修改一处后其余两处无法自动同步。

本次重构将 **`fyz-src/backend/app/domain/skill_dictionary.py` 定为唯一权威来源**，其余副本改为导入桥接层，不再独立维护。

## 权威词典路径

```
fyz-src/backend/app/domain/skill_dictionary.py
```

导出的公开符号：

| 符号 | 类型 | 说明 |
|:-----|:-----|:-----|
| `SKILL_CATEGORIES` | dict | 8 大技能分类的中文映射 |
| `SKILL_DICT` | dict | 146 个标准技能名 → 分类 |
| `SKILL_ALIASES` | dict | 25 个别名 → 标准技能名 |
| `canonical_key(name)` | function | 技能名 → 规范 key（去空格、小写字母数字） |
| `normalize_skill(name)` | function | 技能名 → (标准名, 分类) 或 None |

## 如果你的爬虫管线要引用

在脚本头部添加路径，然后直接 import：

```python
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "fyz-src" / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.domain.skill_dictionary import SKILL_DICT, SKILL_ALIASES, normalize_skill
```

**不要**在 `scripts/` 下创建独立的 `skill_dictionary.py` 副本。

## 本次改动范围

| 文件 | 改动 |
|:-----|:------|
| `fyz-src/backend/app/domain/skill_dictionary.py` | **权威源**，新增 6 个别名（`.NET→C#`、`Node→Node.js`、`Pytorch→PyTorch`、`TF→TensorFlow`、`ES6→JavaScript`、`AI→大模型`）**【注：`AI→大模型` 已回滚，见下方说明】** |
| `data_analysis/scripts/skill_dictionary.py` | 原独立副本 → 改为导入桥接层，实际定义指向 backend |
| `data_analysis/scripts/skill_extractor.py` | 导入来源不变（`from skill_dictionary import ...`），因上层已是桥接，自动指向权威源 |
| `scripts/clean_kdxf.py` | **未改动**（见下节说明） |
| `scripts/import_mysql.py` | **未改动** |
| `scripts/spider.py` | **未改动** |

## 关于成员 D 的爬虫管线

**`scripts/` 目录下的 `clean_kdxf.py`、`import_mysql.py`、`spider.py` 本次未做任何修改。**

原因是：

1. 这三个脚本中**未发现直接引用 `SKILL_DICT` 或 `skill_dictionary`**，不依赖词典副本，因此不受本次重构影响
2. 按团队约定，各成员负责各自模块的迁移时机，不由本次重构代为修改

后续若你的脚本需要引用技能词典，请按上文"如果要引用"一节的方式导入权威源，**不要创建新的独立副本**。
