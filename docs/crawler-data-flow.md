# 爬取数据入库数据流说明

> 回答"爬取的数据是直接入库，还是事实确认后才标准化入库？"

**结论：爬取数据是"直接入库"——导入任务内同步完成去重、质量评估、岗位名标准化与技能抽取；人工事实审核是入库之后的可选确认环节，决定图谱资格。**

## 一、完整数据流

```
① 爬取（人工触发）
   Admin「采集中心」→ POST /admin/data-sources/{id}/run
   → CrawlerService.run_spider 以 subprocess 启动 scripts/spiders/{module}.py
   → spider 采集并写 JSON 到 data/{name}_{n}.json
   → 前端轮询 /admin/data-sources/{id}/poll 拿到 filename

② 导入（前端自动衔接）
   前端自动调 POST /data-imports/jobs {files:[filename]}
   → TaskService.create_import → Celery skill_import（eager 时进程内）
   → ImportService.import_files（fyz-src/backend/app/services/import_service.py:80-224）

③ 入库与标准化（ImportService 内同步完成）
   1. 白名单 + job-v1 Schema 校验          （import_service.py:65-101）
   2. 内容指纹 / external_id 幂等去重       （import_service.py:113-123）
   3. 质量评估 → quality_status=accepted/warning/rejected
   4. 岗位名标准化 normalize_job_title → 聚合到 StandardJob
      （_ensure_standard_job，import_service.py:256-344；
       写 StandardJobAlias / StandardJobSource，回填 raw 的
       standard_job_id、normalization_status=normalized）
   5. simhash 近重复检测 → JobDuplicateCluster
   6. 技能抽取（规则 + 可选 DeepSeek 补全）→ JobSkillFact
      （skill_service.py:191-300，初始 verification_status=unverified）
   7. 跨来源自动验证 → 同(标准岗位, 技能) ≥2 独立来源且置信度≥0.75
      自动置 verified（_cross_validate_facts，import_service.py:419-494）

④ 事实确认（入库后，决定图谱资格）
   人工：Admin「事实审核」→ PATCH /skills/facts/{fact_id}/review
   自动：步骤 ③-7 的跨来源验证
   只有 verification_status=verified 的事实才进入正式图谱与检索
   （graph_service.py:92-93 / retrieval_service.py:115-118）
```

## 二、状态字段变化

| 字段 | 初始 | 变化 |
|---|---|---|
| `RawJobRecord.quality_status` | pending | 入库时 → accepted/warning/rejected |
| `RawJobRecord.normalization_status` | pending | 标准化后 → normalized |
| `RawJobRecord.dedup_status` | unique | 近重复 → near_duplicate |
| `RawJobRecord.is_excluded` | False | 人工排除 → True |
| `JobSkillFact.verification_status` | unverified | 跨源验证/人工 → verified；人工 → rejected |
| `Skill.validation_status` | approved | LLM 抽取 → pending_review（需人工批准） |

## 三、关键结论

1. **标准化不是事实确认的前置/后置环节，而是导入流程内的同步步骤**——岗位名归一在入库时即完成。
2. **事实审核是"图谱资格"门槛而非"入库"门槛**——未审核的事实已入库（可查、可审计），只是不进正式图谱。
3. 当前链路不写 `JobPosting` 表（外键 `job_id` 为空），图谱/检索/分析均基于 `RawJobRecord` + `JobSkillFact`。

## 四、相关代码索引

- 爬虫触发与轮询：`app/services/crawler_service.py:214-338`、`app/api/v1/admin.py:75-115`
- 导入编排：`app/services/task_service.py:22-42`、`app/tasks/skill_import.py:47-57`
- 导入主流程：`app/services/import_service.py:80-494`
- 技能抽取：`app/services/skill_service.py:191-300`
- 前端衔接：`fyz-src/frontend/src/views/Admin.vue:904-951`、`src/data/httpProvider.ts:526-531`
