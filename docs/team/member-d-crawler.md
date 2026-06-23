# 成员 D：爬虫与数据标准化

## 1. 职责

负责多源岗位采集、固定爬虫模板、字段协议、清洗、去重、质量评分、
增量采集和后端导入适配。

不负责管理端页面、Agent 推理、图谱查询实现和生产数据库迁移审批。

## 2. 当前基线

- `data/` 已有讯飞、智联等岗位 JSON。
- 后端 ImportService 只允许三份固定文件，使用 `job-v1` 语义导入。
- 已有标题标准化、内容指纹去重、来源记录和技能抽取。
- `data_analysis` 已有四步清洗与参考数据构建流水线。
- 尚无统一爬虫工程模板和持续增量调度。

## 3. 标准数据协议

每条岗位至少包含：

```json
{
  "source": "来源名称",
  "url": "来源URL",
  "title": "岗位名称",
  "company": "公司",
  "city": "城市",
  "salary": "薪资原文",
  "experience": "经验原文",
  "education": "学历原文",
  "jd_text": "完整JD",
  "responsibilities": "职责",
  "requirements": "要求",
  "keywords": "来源关键词",
  "posted_at": "发布时间",
  "crawled_at": "采集时间"
}
```

不得在缺少来源 URL、采集时间或正文时伪造字段。无法获得的值使用空值，
并在质量报告中说明。

## 4. 4 周 MVP

### 第 1 周：模板与协议

- 建立 crawler 基类、请求配置、解析器、限速、重试和输出校验模板。
- 固化 `job-v1` JSON Schema 和样例。
- 为已有三份数据生成字段完整率和异常报告。

### 第 2 周：两个来源

- 完成讯飞与一个招聘平台的可复用采集器。
- 支持分页、详情、增量时间窗口和失败重试。
- 保存原始响应摘要，不在清洗阶段覆盖来源事实。

### 第 3 周：标准化

- 公司、城市、薪资、学历、经验和岗位名标准化。
- 内容指纹、URL/外部 ID 去重和跨源近似重复检测。
- 质量评分包含完整性、时效性、可追溯性和重复度。

### 第 4 周：导入适配

- 产出可被后端白名单机制安全导入的数据。
- 建立采集 → 校验 → 导入 → 抽样复核脚本和文档。
- 提供至少 100 条可复现 MVP 数据集和统计报告。

## 5. 后 8 周优化

- W5-W6：第三来源、行业报告/政策文件模板和解析失败样本库。
- W7-W8：定时增量、断点续爬、代理/频控策略和合规审查。
- W9-W10：跨源实体对齐、异常检测和数据漂移监控。
- W11-W12：规模测试、数据质量报告、比赛数据快照和复现说明。

## 6. 交付与验收

- 同类网站通过配置和解析器扩展，不复制整套爬虫。
- 每条数据可追溯到来源和采集时间。
- 重复运行不会无限增加重复数据。
- 输出通过 JSON Schema，能够被 ImportService 处理。
- 遵守网站服务条款、robots、频率限制和个人信息最小化要求。

## 7. 验证

```powershell
cd data_analysis
python scripts\01_merge_clean.py
python scripts\02_normalize_titles.py
python scripts\03_extract_skills.py
python scripts\04_build_reference.py
```

涉及后端导入时：

```powershell
cd fyz-src\backend
python -m pytest test\services\test_import_service.py -q
```

## 8. Git 建议

- 分支：`feat/d-crawler-template`、`fix/d-job-dedup`
- 提交：`feat(crawler): add validated job-v1 export`
- 原始大文件、Cookie、代理凭据、抓包和日志不得提交。

## 9. 主要风险

- 违反来源网站条款或过高频率；
- 字段表面完整但内容不可追溯；
- 清洗覆盖原始事实；
- 数据文件体积失控；
- 爬虫输出与后端允许字段逐渐漂移。