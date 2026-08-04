# FYZ 优化窗口交接：Phase 3 后续与管理端 UI 修复

> 交接日期：2026-08-01
> 工作目录：`E:\Project\JieBang`
> 交接目的：供新 Codex 对话直接恢复上下文、保护未提交修改并继续开发
> 重要状态：Phase 0–3 已通过 PR #28 合并；本窗口后续 UI/图谱修复尚未提交、尚未推送

## 1. 新窗口先读什么

请按以下顺序完整阅读，不要直接开始修改：

1. `AGENTS.md`
2. 本文档
3. `docs/git-workflow.md`
4. `docs/dev-prompt-tmp/FYZ数据链路图谱Agent防幻觉与RAG优化计划.md`
5. `docs/dev-prompt-tmp/FYZ优化Phase3Agent防幻觉门禁实施记录.md`
6. 与待开发阶段对应的 Phase 0、1、2、2.1 实施记录

新窗口应先执行只读状态检查，再决定分支处理方式。

## 2. 当前 Git 与 PR 状态

### 2.1 当前分支

```text
branch: feat/fyz-rag-evidence
HEAD:   e7f10fd5 feat(agent): 完成Phase3图谱与匹配解释防幻觉门禁
track:  origin/feat/fyz-rag-evidence
```

最近提交：

```text
e7f10fd5 feat(agent): 完成Phase3图谱与匹配解释防幻觉门禁
143b0780 feat(rag): 完成Phase2证据检索与工程评测
698d004f feat(data): 完成FYZ数据质量与事实认证链路
2c6ae324 feat(fyz): 接入用户行为与真实工作台数据 (#27)
e1b9b9d3 feat(fyz): 完成 Agent MVP 与 Admin 真实数据接入 (#26)
```

### 2.2 PR #28

- PR：`https://github.com/JiaYueyou/JieBang/pull/28`
- 标题：`feat(fyz): 完成数据质量、RAG 检索与 Agent 防幻觉闭环`
- 状态：`MERGED`
- Base：`main`
- Head：`feat/fyz-rag-evidence`
- `backend-tests`、`fyz-frontend`、`jtt-frontend`、`repository-security` 均成功

因此，当前分支已经完成其原始使命。不要把本窗口新修复继续直接推到这个已合并分支。

### 2.3 未提交修改

当前暂存区为空，以下代码修改仍在工作区：

```text
fyz-src/backend/app/api/v1/internal_transfer.py
fyz-src/backend/app/repositories/graph_repository.py
fyz-src/backend/app/services/graph_service.py
fyz-src/backend/app/services/internal_transfer_service.py
fyz-src/backend/test/api/test_internal_transfer.py
fyz-src/backend/test/repositories/test_graph_repository.py
fyz-src/frontend/src/components/graph/Graph3DCanvas.vue
fyz-src/frontend/src/data/graphBuilder.ts
fyz-src/frontend/src/data/httpProvider.test.ts
fyz-src/frontend/src/data/httpProvider.ts
fyz-src/frontend/src/data/provider.ts
fyz-src/frontend/src/domain/types.ts
fyz-src/frontend/src/stores/jobs.ts
fyz-src/frontend/src/views/GraphView.vue
fyz-src/frontend/src/views/JobManagement.vue
```

加上本文档后，本文档也是一个新的未跟踪/未提交交接文件。不要使用 `git add -A`。

当前代码差异规模（生成本文档前）：

```text
15 files changed, 402 insertions(+), 85 deletions(-)
```

## 3. 本次长对话已经完成的专项内容

### 3.1 总体规划与 Phase 0

- 分析 FYZ 管理端项目结构，形成数据链路、图谱、Agent 防幻觉和 RAG 总体优化计划。
- 计划文档位于：
  - `docs/dev-prompt-tmp/FYZ数据链路图谱Agent防幻觉与RAG优化计划.md`
- 固化 Phase 0 契约、运行基线、质量指标和评测种子集。
- 形成实施记录：
  - `docs/dev-prompt-tmp/FYZ优化Phase0契约与基线实施记录.md`
- Phase 0 运行产物位于：
  - `docs/dev-prompt-tmp/phase0-runtime/`
- 对评测种子集进行了审核填充，并建立后续扩充原则。

### 3.2 MySQL 数据与共享快照

- 梳理了 MySQL 全库和单库备份方式。
- 项目当前存在共享 SQL 快照：

```text
fyz-src/backend/scripts/mysql_snapshot.sql
size:   1,280,392 bytes
mtime:  2026-07-11 18:04:33
sha256: 8401FADAB7788D36463912C9C1B18C0A641AE24DFD693175545A96ECE3EF1FBA
```

- MySQL 仍是唯一事实源；Neo4j 和向量索引均为可重建读模型/派生物。
- 数据导入与 Neo4j 重建说明：
  - `fyz-src/backend/scripts/DATABASE_TRANSFER.md`

### 3.3 Phase 1：数据质量与事实认证

- 完成招聘数据质量、时间、近重复、来源和事实审核链路。
- 完成岗位与技能数据补齐及相应测试。
- 实施记录：
  - `docs/dev-prompt-tmp/FYZ优化Phase1数据质量与事实认证实施记录.md`
- 对应提交：`698d004f`

### 3.4 Phase 2 / 2.1：Evidence、Embedding 与 RAG

- 接入 `text-embedding-3-large` 配置契约。
- `base_url` 使用 `https://api.openai-proxy.org`，API Key 由用户在本地环境补充。
- 对 FAISS、ChromaDB、Milvus 进行选型比较，当前 MVP 采用本地可重建方案，MySQL 保存 Evidence 与索引版本元数据。
- 完成 Evidence Chunk、索引版本、混合检索、引用回链和评测脚本。
- 相关文档：
  - `docs/dev-prompt-tmp/FYZ优化Phase2.1Embedding与向量数据库选型补充.md`
  - `docs/dev-prompt-tmp/FYZ优化Phase2评测集补充与审核方案.md`
  - `docs/dev-prompt-tmp/FYZ优化Phase2证据层与混合检索MVP实施记录.md`
- 对应提交：`143b0780`

### 3.5 Phase 3：Agent 防幻觉门禁

- Graph Enrichment 和 Match Explanation 已接入统一证据门禁。
- 建立 Evidence ID / MatchEvidence 引用、引用有效性、来源数、质量、时效和语义一致性验证。
- 所有声明失败时确定性拒答或模板降级，不允许自由文本绕过门禁。
- 持久化 `agent_claim_citation`，保留原始候选、过滤后结果和 fallback reason。
- `machine_validated` 候选仍不能自动进入正式图谱。
- 实施记录：
  - `docs/dev-prompt-tmp/FYZ优化Phase3Agent防幻觉门禁实施记录.md`
- 对应提交：`e7f10fd5`

### 3.6 Phase 0–3 Git/PR 结果

- Phase 0–3 代码已经通过 PR #28 合并。
- PR #28 所有要求的 CI 检查均成功。
- 这部分不需要在新窗口重复提交。

## 4. PR #28 合并后、本窗口新完成但未提交的修复

### 4.1 技能图谱 500 修复

根因：

- RAG 将 `EvidenceChunk` 写入 Neo4j 的 `namespace=jiebang`。
- 图谱 Panorama 查询也按同一 namespace 读取，但此前没有限制五层图谱标签。
- 查询读到 `EvidenceChunk` 后，`GraphNode` 无法接受该类型，且部分节点缺少 `id/name`，最终触发 Pydantic 500。

已完成：

- `Neo4jGraphRepository.query_nodes()` 只读取 `GRAPH_LABELS` 支持的五层节点。
- 排除空 `id` 节点，并稳定选择允许的标签作为节点类型。
- 节点名称为空时回退到稳定节点 ID。
- 增加 Repository 回归测试，确保 `EvidenceChunk` 不进入图谱 Panorama。

真实 Neo4j 验证结果：

```text
144 nodes
14 edges
types: Job, SkillArea, TechStack
```

### 4.2 图谱前端请求与查询修复

- `GraphView.vue` 将关键词、方向、级别、节点类型传给后端。
- `buildGraphFromBackend()` 支持明确查询参数。
- 删除对所有孤立岗位的并行 `/graph/expand` 请求。
- 修复前每次加载会对 129 个孤立岗位并发请求；修复后只调用一次 Panorama。

### 4.3 长内容内部滚动

- 岗位核心技能、人才画像、岗位技能列表、技能变化标签使用内部滚动。
- 图谱右侧节点说明和关联节点列表使用内部滚动。
- 长内容不再拉长另一侧卡片或制造大量空白。
- 移动端恢复自然高度，避免小屏被固定高度限制。

### 4.4 岗位发布交互优化

- “智能岗位发布”和“公开 JD 预览”实际高度由约 858px 降到约 718px。
- 核心技能输入区空状态高度提升到 112px，最大高度 176px。
- 卡片内部没有可滚动内容时，滚轮会继续传递给外层 `.app-content`。
- Playwright 验证外层滚动位置从 `0` 变化到 `396`，内部滚动位置仍为 `0`。

### 4.5 公开/内部岗位真实服务端分页

- 公开岗位原后端已支持分页，但前端曾丢弃 `meta`；现已保留分页元数据。
- 内部岗位新增后端分页、关键词和状态筛选。
- 管理页面每页固定查询 6 条，不再一次加载全部岗位。
- 两个岗位列表卡片固定为 560px 高，并在底部显示分页器。
- 关键词筛选覆盖标题、部门和内部岗位负责人。

真实请求：

```text
GET /api/v1/jobs?page=1&page_size=6
GET /api/v1/internal-transfer/positions?page=1&page_size=6
```

### 4.6 图谱布局与全画布交互

- 左侧五层模型、中间画布、右侧节点详情固定为同高，三栏底边坐标完全一致。
- ECharts 默认按“节点数据包围盒”限制 roam 命中范围，宽画布两侧因此无法缩放/拖拽。
- 当前实现保留 ECharts 原生 roam，只将 `coordinateSystem.containPoint` 命中范围扩展到完整画布，不拉伸节点坐标。
- Playwright 分别在左上、右上、左下、右下四角验证，四处滚轮均由图谱处理，外层页面滚动保持 `0`。

## 5. 当前变更文件职责

| 文件 | 作用 |
|---|---|
| `fyz-src/backend/app/repositories/graph_repository.py` | 限制 Panorama 只读取五层图谱节点 |
| `fyz-src/backend/app/services/graph_service.py` | 空节点名稳定回退 |
| `fyz-src/backend/test/repositories/test_graph_repository.py` | 非图谱标签隔离回归测试 |
| `fyz-src/backend/app/api/v1/internal_transfer.py` | 内部岗位分页、关键词和状态参数 |
| `fyz-src/backend/app/services/internal_transfer_service.py` | 内部岗位分页查询和 PageMeta |
| `fyz-src/backend/test/api/test_internal_transfer.py` | 内部岗位分页/筛选 API 测试 |
| `fyz-src/frontend/src/domain/types.ts` | 通用 `PageResult<T>` |
| `fyz-src/frontend/src/data/provider.ts` | 公开/内部岗位分页 Provider 契约 |
| `fyz-src/frontend/src/data/httpProvider.ts` | 真实 HTTP 分页实现 |
| `fyz-src/frontend/src/data/httpProvider.test.ts` | 分页参数与元数据测试 |
| `fyz-src/frontend/src/stores/jobs.ts` | 分页数据、总数和加载方法 |
| `fyz-src/frontend/src/views/JobManagement.vue` | 高度、滚轮传递、分页和长内容滚动 |
| `fyz-src/frontend/src/data/graphBuilder.ts` | 查询参数和移除孤立岗位 N+1 请求 |
| `fyz-src/frontend/src/views/GraphView.vue` | 图谱筛选、三栏同高、详情内部滚动 |
| `fyz-src/frontend/src/components/graph/Graph3DCanvas.vue` | 全画布拖拽/缩放命中范围 |

## 6. 已完成验证

### 6.1 当前未提交修复

最后一次验证结果：

```text
Backend targeted: 16 passed
Frontend Vitest:   32 passed
Frontend build:    passed
git diff --check:  passed
```

后端命令：

```powershell
Set-Location E:\Project\JieBang\fyz-src\backend
& 'E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe' -m pytest `
  test/api/test_internal_transfer.py `
  test/repositories/test_graph_repository.py `
  test/services/test_graph_service.py `
  test/api/test_graph.py -q
```

前端命令：

```powershell
Set-Location E:\Project\JieBang\fyz-src\frontend
& 'E:\Computer_tools\Nodejs\download\npm.cmd' run test
& 'E:\Computer_tools\Nodejs\download\npm.cmd' run build
```

### 6.2 Playwright 证据

```text
.playwright-cli/page-2026-08-01T04-57-25-676Z.png  岗位管理高度和分页布局
.playwright-cli/page-2026-08-01T05-01-50-399Z.png  图谱三栏对齐和完整画布
```

这些是本地测试证据，`.playwright-cli` 和 `output/playwright` 不得提交。

### 6.3 构建警告

- 构建仍有既存的 ECharts/主包大于 500KB 警告。
- `@vueuse/core` 的 PURE 注释位置会被 Rollup 移除。
- 当前均不是构建失败，但 Phase 5 可单独安排图谱懒加载和 manualChunks 优化。

## 7. 当前运行状态

交接时检测到用户原有进程：

```text
127.0.0.1:8000 -> PID 16996 (Python/Uvicorn)
::1:5173      -> PID 3540  (Node/Vite)
```

注意：

- 这两个进程在本窗口测试前已经存在，因此没有终止。
- 后端 PID 16996 未开启 reload，可能仍运行修改前代码。
- 本窗口真实分页回归使用过临时 8001 后端和 127.0.0.1:5173 前端；临时进程已经关闭。
- 新窗口重启服务前必须先核对 PID、启动时间和命令行，不能直接杀死用户进程。

## 8. 新窗口第一步：保护修改并迁移到最新 main

因为 PR #28 已合并，而当前未提交修改仍在旧的已合并分支上，推荐流程如下。

### 8.1 只读确认

```powershell
Set-Location E:\Project\JieBang
git status --short --branch
git diff --stat
git diff --check
git diff --cached --stat
gh pr view 28 --json state,isDraft,url,headRefName,baseRefName
Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,OwningProcess
```

### 8.2 推荐分支迁移方式

先把包括本文档在内的工作区安全保存，再从最新主分支创建短期修复分支：

```powershell
git stash push -u -m 'WIP: FYZ graph and job interaction fixes after PR28'
git fetch origin
git switch -c fix/fyz-job-graph-interaction origin/main
git stash pop
git status --short --branch
git diff --check
```

如果 `stash pop` 出现冲突，先停止后续操作，逐文件对照 `origin/main` 和本交接文档处理；不要整文件选择 ours/theirs。

### 8.3 提交范围

只暂存第 5 节列出的功能文件、测试文件和本文档。禁止暂存：

```text
.playwright-cli/
output/
dist/
node_modules/
.env
本地缓存和 IDE 配置
```

建议提交：

```text
fix(fyz): 修复图谱加载并优化岗位分页交互
```

提交前必须运行：

```powershell
git diff --cached --stat
git diff --cached --check
git diff --cached
```

## 9. 后续开发安排

### 优先级 P0：完成当前修复的独立 PR

1. 按第 8 节把差异迁移到最新 `origin/main` 新分支。
2. 重新运行后端全量测试，而不只运行当前 16 项定向测试。
3. 运行 FYZ 前端完整 Vitest 和生产构建。
4. 在确认可重启的前提下，用正常 8000/5173 链路重新跑一次 Playwright。
5. 检查分页在大于 6 条数据时的第二页、筛选后页码回到 1、最后一页删除等边界。
6. 检查 Repository Security，不提交截图和运行日志。
7. 提交、推送并创建新的独立 PR，不复用已合并的 PR #28。

### 优先级 P1：Phase 4 设计评审

按照“先规划、后开发”，先输出 Phase 4 可评审设计，不要直接改业务代码。必须确认：

1. 图谱候选是全部人工审核，还是只审核高影响/低置信候选。
2. 发布是管理员手动批次触发，还是批准后自动进入下一批次。
3. 并发审核采用版本号、更新时间还是 ETag/If-Match。
4. 审核、发布、回滚和快照失败的状态机。
5. `machine_validation_status`、`review_status`、`publication_status` 的兼容迁移方案。

设计稿至少包含：

- 数据模型与 Alembic 迁移范围
- API 契约和权限
- 并发冲突处理
- 发布事务和 Neo4j 失败策略
- 快照 diff 定义
- Admin 页面范围
- 测试、回滚和验收标准

### 优先级 P2：Phase 4 分片实施

评审通过后建议按以下顺序：

1. **状态模型与迁移**
   拆分机器校验、人工审核和发布状态，保留旧字段兼容周期。
2. **候选审核 API**
   候选分页、证据详情、批准、驳回、审核意见、管理员权限和并发保护。
3. **发布与快照**
   发布批次、稳定 ID、正式节点证据属性、失败保留上一成功快照。
4. **快照差异**
   新增、删除、更新、降权、审核发布差异。
5. **Admin 审核页面**
   候选、父节点、Evidence Chunk、来源、质量和机器门禁结果。
6. **真实闭环验证**
   MySQL -> 审核 -> 发布 -> Neo4j -> GraphView -> 证据回查。

### 优先级 P3：Phase 5 剩余图谱能力

本窗口已提前完成 Phase 5 的部分基础工作：查询参数、移除孤立岗位 N+1、三栏稳定布局、内部滚动和全画布交互。仍需：

- 接入按需 `/expand`，而不是页面加载时批量展开。
- 接入 `/search`、`/path` 和岗位树。
- 显示 `truncated`、快照版本和查询范围。
- 增加证据抽屉、审核状态和来源信息。
- 确定性布局种子，减少刷新跳动。
- 节点较多时动态隐藏标签，降低 ECharts 压力。
- 同步按钮管理员权限和异步进度。
- 评估 ECharts 私有坐标系统接口升级风险，并增加组件测试或封装适配层。

### 优先级 P4：其余 Agent 门禁

Phase 3 尚未覆盖：

1. JD Generation 字段级来源、建议标记和发布前门禁。
2. Career Planning 的 `provided / inferred / unknown` 和差距映射。
3. Skill Extraction 的原文位置、别名和候选池门禁。
4. 使用离线评测判断是否需要引入独立 NLI 模型，不能仅凭主观感觉放宽门禁。

## 10. 当前已知风险与注意事项

1. **当前差异未提交**：新窗口首要任务是保护工作区，不能切换/重置导致丢失。
2. **当前分支 PR 已合并**：必须迁移到最新 main 的新短期分支。
3. **ECharts 命中范围**：当前通过 `coordinateSystem.containPoint` 扩展全画布交互；ECharts 大版本升级后需回归。
4. **CareerGuide 全量内部岗位**：兼容入口当前最多读取 100 条；后续应评估改为搜索式选择器。
5. **分页边界**：当前管理页每页 6 条，需用更大真实数据验证翻页和删除后的页码修正。
6. **后端全量回归**：本窗口最后只跑了受影响的 16 项后端测试；PR 前必须跑 `test/` 全量。
7. **用户运行进程**：8000/5173 是用户已有进程，重启前先确认，不得误杀。
8. **敏感配置**：API Key 只允许在本地 `.env`，不要把用户填写内容写入文档、日志或提交。
9. **图谱数据边界**：不要删除 `EvidenceChunk` 来修复 Panorama；正确边界是查询时只读取五层正式图谱标签。
10. **发布边界**：`machine_validated` 不能等同于人工批准，更不能直接同步到正式 Neo4j L4/L5。

## 11. PR 前完整验收建议

```powershell
# Backend full suite
Set-Location E:\Project\JieBang\fyz-src\backend
& 'E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe' -m pytest test -q

# FYZ frontend
Set-Location E:\Project\JieBang\fyz-src\frontend
& 'E:\Computer_tools\Nodejs\download\npm.cmd' run test
& 'E:\Computer_tools\Nodejs\download\npm.cmd' run build

# Repository checks
Set-Location E:\Project\JieBang
git diff --check
git status --short --ignored
git diff --cached --stat
git diff --cached --check
git ls-files |
  Select-String 'node_modules|(^|/)dist/|__pycache__|\.pyc$|(^|/)\.env$|\.npm-cache|\.idea|\.vscode'
```
页面验收：

- 图谱真实返回节点/边且无 500。
- 页面加载只有一次 Panorama，不出现大量孤立岗位 expand 请求。
- 图谱四角均能滚轮缩放、空白处拖拽。
- 左中右底边一致。
- 岗位顶部双卡同高且无过量空白。
- 双卡无内部溢出时滚轮滚动外层页面。
- 核心技能较多时只滚动输入区。
- 公开/内部岗位均为服务端分页，筛选参数进入请求。
- 大于一页时分页器、总数、最后一页和筛选重置正确。

## 12. 可直接复制给新对话的启动提示

```text
请先不要修改代码。当前工作目录是 E:\Project\JieBang。

请完整阅读：
1. AGENTS.md
2. docs/dev-prompt-tmp/FYZ优化窗口交接-Phase3后续与UI修复-20260801.md
3. docs/git-workflow.md
4. docs/dev-prompt-tmp/FYZ数据链路图谱Agent防幻觉与RAG优化计划.md

然后只读检查当前 branch/status/log、PR #28、未提交差异、8000/5173 监听进程。
PR #28 已合并，但图谱 500 修复、岗位服务端分页、滚轮传递和全画布交互仍是未提交工作区修改。

第一步请保护现有差异，将其迁移到基于最新 origin/main 的短期 fix 分支；不要使用 git add -A，不要提交 .playwright-cli、output、dist、缓存或 .env。迁移后先复核差异和定向测试，再运行后端全量、前端测试/构建和真实 Playwright。完成后汇报并等待我确认是否提交和创建新 PR。

当前修复 PR 完成后，再按“先规划、后开发”输出 Phase 4 图谱候选审核与发布的评审方案，未经确认不要直接实施 Phase 4 业务代码。
```
