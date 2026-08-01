# 离线数据分析流水线

对爬取的半结构化职位数据（JSON）执行合并、清洗、标准化、技能抽取和岗位画像聚合，输出
5 个中间 JSON 文件。**本目录不连接 MySQL 或 Neo4j，所有结果均为文件输出。**
将离线分析结果导入数据库的入口在 `fyz-src/backend/scripts/`。

## 与后端的关系

| 维度 | `data_analysis/`（本目录） | `fyz-src/backend/` |
|---|---|---|
| 目的 | 离线探索、清洗、抽取、画像构建 | 在线服务、数据库写入、图谱同步 |
| 输出 | JSON 文件（`outputs/`） | MySQL + Neo4j |
| 技能词典 | `skill_dictionary.py`（自包含副本） | `app/services/skill_extractor.py`（主副本） |
| 可重复执行 | 是（幂等，覆盖输出文件） | 是（导入脚本支持 --replace） |

`data_analysis` 的抽取逻辑与后端领域层保持一致，但以自包含方式实现，不依赖数据库连接。

## 目录结构

```
data_analysis/
├── .env                        # 本地模型密钥（不提交 Git）
├── .env.example                # 密钥模板
├── config.py                   # 全局配置：输入路径、去重阈值、技能分类、标准字段
├── requirements.txt            # Python 依赖
├── README.md
├── scripts/
│   ├── __init__.py
│   ├── utils.py                # 共用工具：JSON 读写、文本清洗、去重指纹、薪资/经验/学历解析
│   ├── skill_dictionary.py     # 技能标准词典（8 大类约 180+ 技能 + 别名表）
│   ├── skill_extractor.py      # 规则优先技能抽取器 (RuleSkillExtractor)
│   ├── 01_merge_clean.py       # Step 1: 多源合并、清洗、去重、字段解析
│   ├── 02_normalize_titles.py  # Step 2: 岗位名称标准化、级别/技术栈推断
│   ├── 03_extract_skills.py    # Step 3: 规则技能抽取、技能词典与岗位-技能矩阵构建
│   ├── 04_build_reference.py   # Step 4: 按标准岗位聚合，输出参考数据集
│   ├── run_all.py              # 一键运行全部 4 步
│   └── verify_outputs.py       # 输出完整性验证
└── outputs/                    # 流水线产物（JSON）
    ├── merged_jobs.json
    ├── title_mapping.json
    ├── skill_dict.json
    ├── job_skill_matrix.json
    └── reference_dataset.json
```

## 快速开始

```bash
cd data_analysis

# 安装依赖
pip install -r requirements.txt

# 一键运行全部 4 步
python scripts/run_all.py

# 验证输出
python scripts/verify_outputs.py
```

## 四步流水线详解

### Step 1: 数据合并与清洗 (`01_merge_clean.py`)

读取 `data/` 目录下的多源 JSON 文件（`jd_crawl_ifly.json`、`jd_crawl_zl.json`、
`jd_crawl2.json`），执行字段统一、去重和结构化解析。

| 操作 | 说明 |
|---|---|
| 多源加载 | 读取所有输入 JSON，按 14 个标准字段归一化 |
| 丢弃空 JD | 移除 `jd_text` 为空的记录 |
| URL 去重 | 相同 URL 只保留第一条 |
| 内容指纹去重 | 对 `source\|url\|title\|company\|posted_at\|jd_text` 计算 SHA-256，相同指纹去重 |
| 相似度去重 | title + company 的 Jaccard 二元组相似度 ≥ 85% 视为重复 |
| 来源标注 | 根据 source 字段打标签：`iflytek` / `zhilian` / `unknown` |
| 薪资解析 | `"15K-25K"` → `{"min": 15000, "max": 25000}`；`"面议"` → `null` |
| 经验解析 | `"3-5年"` → `{"min": 3, "max": 5}`；`"经验不限"` → `null` |
| 学历解析 | `"本科及以上"` → `"bachelor"`；映射 8 种学历标签 |
| 质量评分 | 14 个标准字段的填充率，0~1，`jd_text` 为空直接 0 |

**输入：** `data/jd_crawl_ifly.json`, `data/jd_crawl_zl.json`, `data/jd_crawl2.json`
**输出：** `outputs/merged_jobs.json`

#### merged_jobs.json 字段说明

每条记录包含以下字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `title` | string | 原始职位名称 |
| `company` | string | 公司名称 |
| `city` | string | 工作城市 |
| `salary` | string | 原始薪资文本 |
| `experience` | string | 原始经验要求文本 |
| `education` | string | 原始学历要求文本 |
| `jd_text` | string | 完整职位描述 |
| `responsibilities` | string | 岗位职责 |
| `requirements` | string | 任职要求 |
| `keywords` | string | 关键词标签 |
| `posted_at` | string | 发布时间 |
| `url` | string | 原始链接 |
| `source` | string | 来源标识 |
| `crawled_at` | string | 爬取时间 |
| `source_tag` | string | 标准化来源标签：`iflytek` / `zhilian` / `unknown` |
| `parsed` | object | 结构化解析结果 |
| `parsed.salary` | object\|null | `{"min": int, "max": int}` 或 null |
| `parsed.experience` | object\|null | `{"min": int, "max": int}` 或 null |
| `parsed.education` | string\|null | `bachelor` / `master` / `college` / `phd` 等 |
| `quality` | float | 字段完整率 0~1 |

---

### Step 2: 岗位名称标准化 (`02_normalize_titles.py`)

复用后端 `app.domain.job_standardizer` 模块，将原始职位标题清洗为统一的标准名称，
并推断级别与技术方向。处理后回写 `merged_jobs.json`，新增标准化字段。

| 清洗规则 | 示例 |
|---|---|
| 去除括号内容 | `"Python开发（高级）"` → `"Python开发"` |
| 去除校招/实习标记 | `"[校招] Java工程师"` → `"Java工程师"` |
| 去除城市后缀 | `"前端开发-北京"` → `"前端开发"` |
| 去除薪资噪音 | `"急聘 Python 15K"` → `"Python"` |
| 统一技术写法 | `"Python后端工程师"` 与 `"Python服务端开发"` 归入同一标准岗位 |

**级别推断：** `junior` / `middle` / `senior`
**技术栈推断：** `backend` / `frontend` / `ai` / `data` / `devops` / `mobile` / `embedded` / `fullstack` / `unknown`

**输入：** `outputs/merged_jobs.json`
**输出：** `outputs/merged_jobs.json`（回写，增加以下字段） + `outputs/title_mapping.json`

#### 新增字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `standardized_title` | string | 标准化后的岗位名称 |
| `canonical_key` | string | 标准化岗位的规范键（去空格、小写），用于聚合 |
| `level` | string | 级别：`junior` / `middle` / `senior` |
| `stack` | string | 技术方向：`backend` / `frontend` / `ai` / `data` / `devops` 等 |
| `title_confidence` | float | 标准化置信度 0~1 |

#### title_mapping.json 字段说明

原始标题 → 标准标题的单向映射表，key 为原始标题字符串：

| 字段 | 类型 | 说明 |
|---|---|---|
| `standardized` | string | 标准岗位名 |
| `canonical_key` | string | 规范键 |
| `level` | string | 推断级别 |
| `stack` | string | 推断技术方向 |
| `confidence` | float | 映射置信度 |
| `sample_company` | string | 示例公司名 |

---

### Step 3: 技能提取 (`03_extract_skills.py`)

使用自包含的 `RuleSkillExtractor`，以 8 大类约 180+ 技能词典 + 别名表对
`jd_text`、`responsibilities`、`requirements` 三个文本区段做正则匹配，
输出唯一技能词典和岗位-技能关联矩阵。

#### 技能分类（8 大类）

| 分类键 | 中文名 | 示例 |
|---|---|---|
| `programming_language` | 编程语言 | Python, Java, Go, TypeScript, C++ |
| `framework` | 框架 | Spring Boot, Django, Vue, React, PyTorch |
| `tool` | 工具/平台 | Docker, Git, Jenkins, Kubernetes, Nginx |
| `database` | 数据库 | MySQL, Redis, MongoDB, Elasticsearch, Neo4j |
| `cloud` | 云计算 | AWS, 阿里云, 微服务, DevOps, 云原生 |
| `ai_ml` | AI/机器学习 | 大模型, RAG, NLP, 深度学习, 知识图谱 |
| `domain_knowledge` | 领域知识 | 大数据, Kafka, Spark, 物联网, 网络安全 |
| `soft_skill` | 软技能 | 团队管理, 项目管理, 沟通能力, 需求分析 |

#### 抽取规则

- **必要技能 (required):** 正则命中且上下文不含"优先""加分""bonus""者优先"等标记
- **加分技能 (preferred):** 正则命中且上下文中含加分标记
- **证据保留:** 每个命中技能保留匹配位置前后 55 字符的原文片段作为 `evidence`
- **置信度:** 标准名命中 0.96，别名命中 0.92

**输入：** `outputs/merged_jobs.json`
**输出：** `outputs/skill_dict.json` + `outputs/job_skill_matrix.json`

#### skill_dict.json 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `total_skills` | int | 去重后的唯一技能数 |
| `total_mentions` | int | 所有技能在所有岗位中的总提及次数 |
| `category_distribution` | object | 各分类的去重技能数分布 |
| `skills` | array | 技能列表，按总提及次数降序 |
| `skills[].name` | string | 标准技能名 |
| `skills[].category` | string | 所属分类（英文键） |
| `skills[].total_mentions` | int | 总提及次数 |
| `skills[].job_count` | int | 覆盖的标准化岗位数 |
| `skills[].as_core` | int | 作为必要技能出现的次数 |
| `skills[].as_bonus` | int | 作为加分技能出现的次数 |
| `skills[].sources` | array | 来源平台列表 |
| `skills[].avg_confidence` | float | 平均置信度 |

#### job_skill_matrix.json 字段说明

每条记录对应一个岗位的技能抽取结果：

| 字段 | 类型 | 说明 |
|---|---|---|
| `original_title` | string | 原始职位名称 |
| `standardized_title` | string | 标准化岗位名称 |
| `canonical_key` | string | 标准岗位规范键 |
| `company` | string | 公司名称 |
| `source_tag` | string | 来源标签 |
| `level` | string | 岗位级别 |
| `stack` | string | 技术方向 |
| `core_skills` | array | 必要技能列表 |
| `core_skills[].name` | string | 技能名 |
| `core_skills[].category` | string | 分类 |
| `core_skills[].kind` | string | `"required"` |
| `core_skills[].confidence` | float | 置信度 |
| `core_skills[].evidence` | string | 原文证据片段（≤200 字符） |
| `bonus_skills` | array | 加分技能列表（字段同上，kind=`"preferred"`） |
| `total_skills` | int | 该岗位技能总数（核心+加分） |

---

### Step 4: 构建参考数据集 (`04_build_reference.py`)

按 `standardized_title` 聚合所有岗位记录，为每个标准岗位生成一份完整画像，
包含技能频次分布、样本需求和来源覆盖。

**输入：** `outputs/merged_jobs.json` + `outputs/job_skill_matrix.json`
**输出：** `outputs/reference_dataset.json`

#### reference_dataset.json 字段说明

数组，每个元素为一个标准岗位画像，按覆盖记录数降序排列：

| 字段 | 类型 | 说明 |
|---|---|---|
| `job_title` | string | 标准化岗位名称 |
| `canonical_key` | string | 规范键 |
| `level` | string | 主流级别（出现最多的） |
| `stack` | string | 主流技术方向（出现最多的） |
| `total_records` | int | 聚合的原始记录数 |
| `sources` | array | 覆盖的来源平台列表 |
| `core_skills` | array | 必要技能列表，按频次降序 |
| `core_skills[].name` | string | 技能名 |
| `core_skills[].category` | string | 分类 |
| `core_skills[].frequency` | float | 出现频次 (count / total_records) |
| `core_skills[].avg_confidence` | float | 平均置信度 |
| `core_skills[].sources` | array | 来源平台列表 |
| `bonus_skills` | array | 加分技能列表（字段同上） |
| `sample_requirements` | object | 样本需求统计 |
| `sample_requirements.education` | string | 众数学历要求 |
| `sample_requirements.experience` | object | 中位数经验范围 `{"min": int, "max": int}` |
| `sample_requirements.salary` | object | 中位数薪资范围 `{"min": int, "max": int}` |

---

## 配置

`.env` 仅用于本地可选模型配置，不能提交到 Git：

```dotenv
DEEPSEEK_API_KEY=replace-with-local-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

当前流水线为规则抽取，不依赖大模型。DeepSeek 密钥仅预留给后续可能的 LLM 辅助抽取场景。

`config.py` 中定义了：

| 配置项 | 说明 |
|---|---|
| `DATA_FILES` | 输入 JSON 文件路径列表 |
| `DEDUP_THRESHOLD` | title+company 相似度去重阈值（默认 85） |
| `STANDARD_FIELDS` | 14 个标准化字段 |
| `SKILL_CATEGORIES` | 8 大技能分类 |
| `SKILL_DICT` | 180+ 预设技能词典 |
| `TITLE_NORMALIZE_PATTERNS` | 标题标准化正则规则 |

## 验证输出

```bash
python scripts/verify_outputs.py
```

验证项包括：记录数阈值、字段完整性、级别/技术栈值合法性、技能覆盖率、
岗位画像去重数、多源交叉覆盖等。

## 进入数据库的路径

本流水线不写入数据库。将清洗结果或参考数据集导入 MySQL、同步 Neo4j 的入口在：

```bash
cd fyz-src/backend
conda activate jiebang

# 导入团队数据库快照（MySQL → ChromaDB → Neo4j → 一致性校验）
.\scripts\Import-TeamDatabase.ps1 -Replace

# 或分步执行
python scripts/01_prepare_mysql_schema.py
python scripts/02_import_mysql_snapshot.py --replace
python scripts/restore_chroma_from_mysql.py --replace
python scripts/03_rebuild_neo4j.py
python scripts/04_verify_database_import.py
```

完整说明见 [数据库迁移文档](../fyz-src/backend/scripts/DATABASE_TRANSFER.md)
和 [知识图谱数据链路说明](知识图谱数据链路说明.md)。
