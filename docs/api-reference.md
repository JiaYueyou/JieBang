# API 参考

基础地址：`http://localhost:8000/api/v1`

- Swagger：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`
- OpenAPI：`http://localhost:8000/openapi.json`

本文记录当前代码中的真实接口。运行时 OpenAPI 是参数和 Schema 的最终来源。

## 1. 统一响应

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "meta": null
}
```

分页响应的 `meta`：

```json
{
  "page": 1,
  "page_size": 20,
  "total": 100,
  "total_pages": 5
}
```

除登录和注册外，业务接口需要：

```http
Authorization: Bearer <access_token>
```

## 2. PowerShell 登录示例

```powershell
$base = "http://localhost:8000/api/v1"
$login = Invoke-RestMethod `
  -Method Post `
  -Uri "$base/auth/login" `
  -ContentType "application/json" `
  -Body (@{
    username = "admin"
    password = "你的本地密码"
  } | ConvertTo-Json)

$token = $login.data.access_token
$headers = @{ Authorization = "Bearer $token" }
```

## 3. 认证

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/register` | 注册用户 |
| POST | `/auth/login` | 登录并返回 JWT |

认证失败、资源冲突和参数校验分别通过 HTTP 401、409、422 返回统一错误结构。

## 4. 岗位

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/jobs` | 分页查询岗位，可按状态和关键词过滤 |
| POST | `/jobs` | 创建岗位 |
| GET | `/jobs/{job_id}` | 岗位详情 |
| PUT | `/jobs/{job_id}` | 更新岗位并记录版本 |
| DELETE | `/jobs/{job_id}` | 删除岗位 |
| PUT | `/jobs/{job_id}/status` | 更新岗位状态 |
| GET | `/jobs/{job_id}/versions` | 查看版本列表 |
| GET | `/jobs/{job_id}/versions/{version_id}` | 查看指定版本 |
| POST | `/jobs/{job_id}/extract-skills` | 对岗位执行技能抽取 |
| GET | `/jobs/{job_id}/skill-facts` | 查看岗位技能事实 |

分页示例：

```powershell
Invoke-RestMethod `
  -Uri "$base/jobs?page=1&page_size=20&keyword=Java" `
  -Headers $headers
```

## 5. 标准技能

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/skills` | 分页查询技能，可按关键词和分类过滤 |
| GET | `/skills/{skill_id}` | 技能详情 |

技能事实具有 `required/preferred` 类型和 `verified/unverified` 验证状态。

## 6. 数据导入与异步任务

创建导入任务：

```powershell
$body = @{
  files = @(
    "jd_crawl_ifly.json",
    "jd_crawl_zl.json",
    "jd_crawl2.json"
  )
} | ConvertTo-Json

$task = Invoke-RestMethod `
  -Method Post `
  -Uri "$base/data-imports/jobs" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body

$taskId = $task.data.task_id
```

查询任务：

```powershell
Invoke-RestMethod -Uri "$base/tasks/$taskId" -Headers $headers
```

任务结果包含 `status`、`progress`、`result`、`error_code` 和
`error_message`。只有 `succeeded` 表示完成。

## 7. 图谱

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/graph/` | 图谱模块兼容入口 |
| POST | `/graph/sync` | 创建全量或增量同步任务 |
| GET | `/graph/snapshots` | 快照列表 |
| GET | `/graph/snapshots/{snapshot_id}` | 快照详情 |
| GET | `/graph/panorama` | 图谱全景及筛选 |
| GET | `/graph/nodes/{node_id}` | 节点详情子图 |
| GET | `/graph/expand` | 按深度展开节点 |
| GET | `/graph/search` | 搜索节点 |
| GET | `/graph/path` | 查询两节点路径 |
| GET | `/graph/jobs/{job_id}/tree` | 标准岗位五级能力树 |

创建同步任务：

```powershell
$sync = Invoke-RestMethod `
  -Method Post `
  -Uri "$base/graph/sync" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body (@{
    mode = "full"
    enrich_top_skills = $true
  } | ConvertTo-Json)
```

日常更新使用 `incremental`；需要从 MySQL 事实重建时使用 `full`。

## 8. JD 生成 Agent

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/agents/jd-generations` | 创建异步 JD 草稿生成任务 |
| GET | `/agents/runs/{agent_run_id}` | 查看 Agent 运行审计记录 |

请求示例：

```powershell
$task = Invoke-RestMethod `
  -Method Post `
  -Uri "$base/agents/jd-generations" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body (@{
    mode = "requirements"
    title = "Java 后端工程师"
    level = "高级"
    department = "研发中心"
    skills_input = "Java, Spring Boot, MySQL"
  } | ConvertTo-Json)
```

生成结果通过通用 `/tasks/{task_id}` 查询。结果是可编辑草稿，前端确认后再调用
`POST /jobs` 发布；模型调用失败时服务会返回可编辑模板草稿。

## 9. 岗位洞察与趋势分析

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/analysis/` | 模块状态入口 |
| GET | `/analysis/overview` | 趋势概览；支持 `months`、`keyword`、`city` 筛选 |
| GET | `/analysis/job-insights` | 新兴岗位与能力变化；支持 `skill`、`limit` 筛选 |
| PUT | `/analysis/emerging-jobs/{standard_job_id}/decision` | 保存用户洞察决策 |

洞察决策请求：

```json
{
  "decision": "planned",
  "note": "纳入下季度招聘计划"
}
```

决策值为 `confirmed`、`planned` 或 `ignored`，并按当前登录用户隔离。趋势结果包含
数据覆盖范围和质量提示，前端不应将数据不足视为零需求。

## 10. 当前占位接口

以下模块已经注册并受认证保护，但目前只返回占位信息：

| 路径前缀 | 规划能力 |
| --- | --- |
| `/changes` | 既有岗位能力动态更新 |
| `/matching` | 人岗匹配度诊断 |
| `/admin` | 系统管理 |

在实现真实逻辑前，不得将这些模块标记为“后端已完成”。新增接口时必须同步：

1. Pydantic Schema；
2. FastAPI OpenAPI；
3. 本文档；
4. 前端 TypeScript 类型和请求封装；
5. API/服务测试。
