# JTT 评测方案

本目录用于 JTT 求职端的可复现实验，不包含真实简历或未脱敏数据。

## 目录

- `datasets/`：固定版本的人工标注数据（Gold Set）
- `templates/`：人工标注模板
- `scripts/`：指标计算和报告生成脚本
- `private_resumes/`：本地私有 PDF/DOCX，已加入 `.gitignore`

## 指标口径

- 岗位数据解析/读取准确率：岗位名称、公司、城市、学历、经验、薪资等字段的宏平均准确率。
- 简历提取准确率：关键字段精确匹配率与技能集合 F1 的宏平均。
- 人岗匹配准确率：人工标注的推荐/不推荐二分类准确率，同时报告 Top-3 命中率。
- 防幻觉：正确拒答率、证据支持率、引用有效率。

目标均为 90% 以上（引用有效率要求 100%），pytest 业务覆盖率要求 60% 以上。

## 使用

```powershell
cd jtt-src/backend
python evaluation/scripts/build_jd_candidate_set.py --limit 120
python evaluation/scripts/evaluate_jd.py --gold evaluation/datasets/jd_gold.json
python evaluation/scripts/evaluate_resume.py --gold evaluation/datasets/resume_gold.json
python evaluation/scripts/evaluate_resume_api.py --token "$JTT_TOKEN"
python evaluation/scripts/evaluate_matching.py --gold evaluation/datasets/match_gold.json
python evaluation/scripts/evaluate_hallucination.py --gold evaluation/datasets/hallucination_cases.json
```

评测脚本不会调用模型，也不会修改业务数据库；没有标注数据时会明确报告 `status=pending`，不会伪造准确率。

## 当前数据与复现状态

截至 2026-08-28，仓库提交了 120 条 JD、10 条简历、100 条匹配和 20 条防幻觉样本；四组数据
均属于自动规则生成的 `pseudo_gold`，不是人工独立金标。`evaluation/reports/` 和私有简历文件
被 `.gitignore` 排除，旧报告引用的覆盖率、JUnit 和接口结果无法仅凭仓库复现。

当前 `pytest.ini` 要求 `pytest-cov`，但 `requirements.txt` 尚未包含 pytest、pytest-asyncio、
pytest-cov、aiosqlite；简历解析运行时使用的 python-docx、pdfplumber 也未列入依赖。补齐依赖并
修复学习路径 `position_id` 契约前，测试门禁状态为未通过。
