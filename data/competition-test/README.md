# 赛方测试数据与复现说明

本目录供赛方评委人工复现及 AI 自动测试使用。测试数据包含 1 个既有岗位的两个时间窗口数据，以及 1 个新岗位的多来源数据；同时提供结构化预期输出、图谱关系和页面参考截图。

## 一、数据内容

| 测试对象 | 时间窗口 | 数据条数 | 数据来源 | 输入文件 | 技能字段示例 |
| --- | --- | ---: | ---: | --- | --- |
| AI应用开发工程师 | 2026-05—2026-06 | 2 | 2 | `01_existing_job_baseline.json` | Python、FastAPI、MySQL |
| AI应用开发工程师 | 2026-07—2026-08 | 2 | 2 | `02_new_job_and_existing_update_v2.json` | Python、FastAPI、MySQL、LangChain、RAG |
| 大模型安全工程师 | 2026-07—2026-08 | 2 | 2 | `02_new_job_and_existing_update_v2.json` | Python、机器学习、大模型 |

每条输入记录均包含岗位名称、企业、地点、发布时间、JD 正文、职责、任职要求、来源标识、来源链接、采集时间和快照信息。

## 二、文件清单

| 文件 | 赛方用途 |
| --- | --- |
| `01_existing_job_baseline.json` | 第一步输入：既有岗位早期窗口数据 |
| `02_new_job_and_existing_update_v2.json` | 第二步输入：既有岗位后期窗口数据和新岗位数据 |
| `expected_output.json` | AI 测试使用的导入结果与岗位洞察字段 |
| `expected_graph.json` | AI 测试使用的岗位、技能节点及关系 |
| `test_cases.json` | 结构化测试步骤和页面/API 检查点 |
| `docker_verification.json` | Docker 页面查询结果参考值 |
| `evidence/` | 导入入口、岗位洞察和技能图谱页面参考截图 |

## 三、Docker 页面复现

1. 按作品部署说明启动 Docker 服务。
2. 打开管理端 `http://localhost:18080`。默认评测账号为 `admin`，密码为 `admin123`；如部署账号已调整，以作品账号信息文档为准。
3. 进入“系统管理”→“采集中心”→“赛方测试数据复现”。
4. 点击“导入第一时间窗口”，等待页面提示文件处理完成。
5. 点击“导入第二时间窗口并同步图谱”，等待导入任务和图谱同步任务完成。
6. 点击“查看岗位洞察”，搜索 `AI应用开发工程师` 或 `RAG`，查看两个时间窗口的岗位证据和技能变化字段。
7. 在同一页面搜索 `大模型安全工程师`，查看岗位名称、来源数量和技能标签。
8. 点击“查看技能图谱”，分别搜索两个岗位名称，查看岗位节点、技能节点及连线。

输入文件应按编号顺序导入。系统会校验数据源快照时间，拒绝用早期快照覆盖后期快照。

## 四、AI 自动测试接口

认证后依次提交：

```http
POST /api/v1/data-imports/jobs
Content-Type: application/json

{"files":["competition-test/01_existing_job_baseline.json"]}
```

```http
POST /api/v1/data-imports/jobs
Content-Type: application/json

{"files":["competition-test/02_new_job_and_existing_update_v2.json"]}
```

导入接口返回异步任务标识。通过以下接口轮询任务状态：

```http
GET /api/v1/tasks/{task_id}
```

任务成功时，AI 测试可读取 `result.total`、`result.imported`、`result.skill_facts`、`result.verified_skill_facts` 和 `result.affected_standard_job_ids`。字段参考值见 `expected_output.json`。

岗位洞察和图谱查询结果分别与 `expected_output.json`、`expected_graph.json` 对照。页面参考结果见 `docker_verification.json` 和 `evidence/`。

## 五、复现完成检查

| 检查位置 | 可读取信息 |
| --- | --- |
| 导入任务结果 | 文件名、总记录数、入库数、技能事实数、任务状态 |
| 岗位洞察—AI应用开发工程师 | 时间窗口、岗位证据数、技能变化字段 |
| 岗位洞察—大模型安全工程师 | 岗位名称、来源数、置信度、技能标签 |
| 技能图谱 | 岗位节点、技能领域节点、技术栈节点及关系边 |

测试数据使用 `competition.example.com` 保留域名，不依赖外部招聘网站。
