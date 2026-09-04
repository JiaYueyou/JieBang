# 赛方测试原始数据说明

本目录保存《智联职引—比赛测试报告》引用的逐例输入、预期字段和系统输出，供赛方评委查阅及 AI 自动测试使用。

## 核心原始输入

| 文件或目录 | 数据规模 | 内容 |
| --- | ---: | --- |
| `competition_jd_200_cases.json` | 200 条 JD | 8 个招聘来源的 JD 原文、岗位字段、来源 URL、内容哈希、标准岗位映射、技能事实及逐项检查结果 |
| `competition_rag_golden_set.json` | 135 条检索样本、50 组近重复负例 | 查询文本、检索目标、证据标识、数据集划分及预期结果 |
| `hallucination_control_report.json` | 24 条 | 输入问题、证据条件和系统响应结果 |
| `resume_skill_100_cases.json` | 100 条 | 简历技能提取输入文本及预期技能集合 |
| `matching_100_cases.json` | 100 条 | 岗位文本、简历文本、预期岗位技能和预期简历技能 |
| `resume_format_cases.json` | 10 个档案 | 多格式简历的文本原文、岗位类型和预期技能 |
| `resume-format-files/` | 50 个文件 | 10 个档案分别生成 PDF、DOCX、PNG、JPG、JPEG，用于多格式解析测试 |

## 逐例输出与计算材料

| 文件 | 用途 |
| --- | --- |
| `graph_job_fit_200_report.json` | 200 条 JD、1081 条技能事实的图谱贴合度结果 |
| `competition_rag_report.json`、`competition_rag_report.md` | RAG 检索逐例输出和指标汇总 |
| `resume_format_metrics.json` | 50 个多格式简历文件的解析结果 |
| `collected_resume_metrics.json` | 脱敏简历样本的逐文件解析明细 |
| `collected_resume_import_report.json` | 简历导入任务结果 |
| `fyz_quality_metrics.json` | JD、简历技能提取和人岗匹配指标汇总 |
| `fyz_interface_test_calculation_logic.md` | 接口、样本及指标计算方法 |
| `fyz_pytest_results.xml`、`fyz_coverage.json` | 后端测试结果与覆盖率数据 |
| `competition_readiness_report.json` | 各质量门禁的结构化结果 |
| `docker_deployment_evidence.json` | Docker 服务与部署校验结果 |
| `browser-evidence/` | 管理端主要测试页面截图 |

## 读取顺序

1. 使用 `competition_jd_200_cases.json` 的 `cases[].input` 读取 200 条 JD 原文。
2. 使用各数据文件中的 `cases`、`retrieval_cases` 或 `duplicate_negative_cases` 读取逐例测试输入。
3. 将系统输出与同一条记录中的预期字段，或对应的指标报告进行比较。
4. 多格式简历测试直接上传 `resume-format-files/` 中的文件；文件名与 `resume_format_cases.json` 中的档案编号一致。

所有简历均为虚构、模板或脱敏数据，不包含用于联系真实个人的信息。
