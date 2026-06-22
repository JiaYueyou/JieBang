# 岗位数据处理与分析

对爬取的岗位招聘数据进行标准化处理，提取核心技能，构建岗位-技能参考数据集。

为后续的"既有岗位能力动态更新"和"新岗位发现"模块提供数据基础。

## 目录结构

```
data_analysis/
├── scripts/                  # 处理脚本
│   ├── 01_merge_clean.py     # Step 1: 数据合并与清洗
│   ├── 02_normalize_titles.py# Step 2: 岗位名称标准化
│   ├── 03_extract_skills.py  # Step 3: 技能提取
│   ├── 04_build_reference.py # Step 4: 构建参考数据集
│   └── utils.py              # 共用工具函数
├── outputs/                  # 输出数据
│   ├── merged_jobs.json      # 合并清洗后的全量数据
│   ├── skill_dict.json       # 技能词典
│   ├── job_skill_matrix.json# 岗位-技能关联矩阵
│   ├── title_mapping.json    # 岗位名标准化映射表
│   └── reference_dataset.json# 最终参考数据集
├── config.py                 # 全局配置
├── .env                      # API密钥（需自行填写）
├── .env.example              # .env 模板
├── requirements.txt          # Python依赖
└── README.md                 # 本文件
```

## 快速开始

### 1. 配置环境

```bash
conda activate jiebang
pip install -r requirements.txt
```

### 2. 配置 API Key（可选）

编辑 `.env` 文件，填入 DeepSeek API Key:

```
DEEPSEEK_API_KEY=sk-your-key-here
```

> 不配置 API Key 也可运行 Step 1 和 Step 4。Step 2/3 中的 DeepSeek 辅助部分会自动跳过，仅使用规则匹配。

> 安全提示：不要把真实密钥写入 `.env.example` 或提交到 Git。历史示例中曾出现疑似有效密钥，请在 DeepSeek 控制台立即吊销并轮换该密钥。

### 3. 运行 Pipeline

```bash
# Step 1: 数据合并与清洗（不需要 API）
python scripts/01_merge_clean.py

# Step 2: 岗位名称标准化（需要 API 获得最佳效果）
python scripts/02_normalize_titles.py

# Step 3: 技能提取（需要 API 获得最佳效果）
python scripts/03_extract_skills.py

# Step 4: 构建参考数据集（不需要 API）
python scripts/04_build_reference.py
```

或一键运行:

```bash
python scripts/01_merge_clean.py && \
python scripts/02_normalize_titles.py && \
python scripts/03_extract_skills.py && \
python scripts/04_build_reference.py
```

## 输出数据说明

### merged_jobs.json
合并清洗后的全量岗位数据，每条包含标准化字段和 `standardized_title`、`extracted_skills`。

### skill_dict.json
技能词典，包含所有提取到的技能及其分类、出现频率等。

### job_skill_matrix.json
岗位-技能关联矩阵，每岗位列出其核心技能和加分技能。

### reference_dataset.json
最终参考数据集，用于"既有岗位能力动态更新"和"新岗位发现"模块。格式:
```json
{
  "job_title": "Java开发工程师",
  "core_skills": [
    {"name": "Java", "category": "programming_language", "frequency": 1.0},
    {"name": "Spring Boot", "category": "framework", "frequency": 0.85}
  ],
  "bonus_skills": [
    {"name": "Docker", "category": "tool", "frequency": 0.35}
  ],
  "sample_requirements": {
    "education": "本科",
    "experience": "3-5年"
  },
  "data_sources": {
    "total_records": 12,
    "sources": ["科大讯飞招聘", "智联招聘"]
  }
}
```

## 技能提取策略

三层策略，逐级增强:

1. **预置词典匹配**: 200+ IT常见技能，覆盖编程语言、框架、工具、数据库、AI、云计算等
2. **正则模式补充**: 匹配特定格式的技术名词
3. **DeepSeek 辅助**: 调用 DeepSeek API 识别词典未覆盖的新兴技能（需 API Key）
