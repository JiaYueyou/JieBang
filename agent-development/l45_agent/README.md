# L4-L5 智能体补全模块

基于 DeepSeek 大模型，为 L1-L3 知识图谱自动补全技术点 (TechPoint) 和知识点 (KnowledgePoint)。

## 整体流程

```
MySQL 事实数据 → 自动筛选 Top 技能（动态 95% 覆盖）
  → 按来源比例抽取证据文本 → DeepSeek 分析生成
  → 置信度验证过滤 → 写入 Neo4j
```

## 目录结构

```
agent-development/l45_agent/       ← 智能体核心模块
├── schema.py                      数据模型定义
├── prompt.py                      Prompt 模板
├── agent.py                       DeepSeek API 调用
├── verify.py                      置信度计算与验证过滤
└── runner.py                      独立运行入口

fyz-src/backend/scripts/           ← 流水线集成
├── 05_enrich_l45.py               流水线第 5 步
├── run_all_l45.py                 一键运行（测试→补全）
├── tests/
│   ├── run_l45_tests.py           14 个测试用例
│   └── test_l45_enrich.py         详细测试文件
└── l45_output.json                最近一次运行结果
```

## 前置条件

1. **L1-L3 已入库**：确保先运行 `03_rebuild_neo4j.py` 完成 L1-L3 图谱构建
2. **DeepSeek API Key**：配置在 `fyz-src/backend/.env` 中：
   ```
   DEEPSEEK_API_KEY=你的key
   DEEPSEEK_BASE_URL=https://api.deepseek.com
   DEEPSEEK_MODEL=deepseek-v4-flash
   ```
3. MySQL 和 Neo4j 服务运行中

## 使用方法

### 完整流程（测试 + 补全）

```bash
cd fyz-src/backend/scripts
set PYTHONPATH=D:\JieBang\agent-development
python run_all_l45.py
```

### 仅跑测试

```bash
python run_all_l45.py --test
```

### 仅跑补全（跳过测试）

```bash
python run_all_l45.py --skip-test
```

### 独立运行补全

```bash
python 05_enrich_l45.py
```

## 核心参数

| 参数 | 默认值 | 说明 |
|:-----|:------:|:-----|
| `COVERAGE_THRESHOLD` | 0.95 | 动态截止：累计覆盖 XX% 证据量时停止纳入新技能 |
| `EVIDENCE_CAP` | 20 | 每技能送大模型的证据上限 |
| `MIN_CONFIDENCE` | 0.75 | 置信度阈值，低于此值的技术点/知识点被过滤 |

## 置信度公式

```
置信度 = log2(evidence_count + 1) / log2(category_max + 1) × 0.5 + 0.5
```

- **按类别分别算 max**：编程语言类的 max 是 117，云原生的 max 是 5，各自独立计算
- **log 压缩**：防止单技能拉高整个类别的分母
- **边界保护**：证据数=0 或 max=0 时返回 0.5，max=1 时退化为线性公式

## 证据选择策略

```
按来源比例分配，每来源至少保底 1 条
  例：智联招聘 87 条 + 科大讯飞 30 条，EVIDENCE_CAP=20
  → 各自保底 1 条 + 按比例分剩余 18 条
  → 智联 14 条，科大 6 条（不是字母序优先！）
```

## 测试覆盖（14 个用例）

| 类 | 用例数 | 验证点 |
|:---|:------:|:-------|
| Schema 模型 | 2 | 数据模型创建、输入拼装 |
| Log 边界 | 4 | count=0, max=1, max=0, max=1+高证据 |
| Log 正常 | 3 | 正常通过、来源不足过滤、空输出过滤 |
| 按类别 | 2 | 同证据不同 max 置信度不同、边界通过/过滤 |
| 证据选择 | 3 | 比例分配、来源悬殊保底、来源超 cap 截断 |

## 运行结果示例

```
[5/5] Total skills: 57, selected 43 (cover 95% evidence)
[5/5] Real max evidence sources per category (unlimited):
      programming_language: 117
      ai_ml: 39
      database: 33
      ...
[5/5] Done: 39 written, 4 skipped, 0 failed
```
