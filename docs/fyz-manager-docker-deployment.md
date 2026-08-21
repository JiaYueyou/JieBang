# FYZ 管理端独立 Docker 部署说明

## 1. 部署目录与边界

独立部署目录为 `E:\Project\jiebang-manager`。该目录只包含 FYZ 管理/决策端运行所需的后端、前端、Agent、数据和部署编排文件；启动、迁移、快照恢复和后续运维均从此目录执行，不依赖开发仓库工作目录。

已有 `deploy\.env` 与 `fyz-src\backend\.env` 已原样复制。部署过程不会要求重新填写配置，也不得把真实 `.env` 提交到 Git。

## 2. 启动

在 PowerShell 7 中执行：

```powershell
Set-Location E:\Project\jiebang-manager
docker compose --env-file deploy\.env -f deploy\compose.yml -f deploy\compose.local.yml config --quiet
docker compose --env-file deploy\.env -f deploy\compose.yml -f deploy\compose.local.yml build
docker compose --env-file deploy\.env -f deploy\compose.yml -f deploy\compose.local.yml up -d
```

首次启动会依次完成 Alembic 迁移、MySQL 竞赛快照恢复、离线检索索引重建、Neo4j 读模型重建和完整性校验。后续启动检测到已验证标记后会保留现有业务数据。

## 3. 访问地址

| 服务 | 地址 | 用途 |
| --- | --- | --- |
| 管理端 | `http://localhost:18080` | 统一入口 |
| 后端 API | `http://localhost:18000` | 仅本机调试 |
| MySQL | `127.0.0.1:23306` | 仅本机维护 |
| Neo4j Browser | `http://127.0.0.1:17474` | 图数据检查 |

演示登录账号显示在登录页。生产或答辩网络环境中应在部署前完成密码轮换。

## 4. 验证

```powershell
docker compose --env-file deploy\.env -f deploy\compose.yml -f deploy\compose.local.yml ps
curl.exe -sS -o NUL -w "%{http_code} %{time_total}" http://localhost:18080/health
docker compose --env-file deploy\.env -f deploy\compose.yml -f deploy\compose.local.yml logs --no-color --tail 100 fyz-bootstrap-snapshot fyz-api nginx
```

通过条件：核心常驻服务为 `Up`/`healthy`，`fyz-migrate` 与 `fyz-bootstrap-snapshot` 正常以 0 退出，健康检查返回 HTTP 200。

RAG 复核：

```powershell
docker compose --env-file deploy\.env -f deploy\compose.yml -f deploy\compose.local.yml exec -T fyz-api python scripts/evaluate_phase2_retrieval.py --golden evaluation/competition_rag_golden_set.json --report-json evaluation/competition_rag_report.json --report-markdown evaluation/competition_rag_report.md
```

## 5. 快照完整性

源快照 `fyz-src\backend\scripts\mysql_snapshot.sql` 不被部署脚本改写。若快照中的脱敏标记破坏了 JSON 向量小数，导入器仅在内存中把受损分量置零，完成关系数据导入后立即从 MySQL 权威证据重建 `signed-token-hash-v1` 离线索引。该处理不改变源文件及其 SHA-256。

不要使用 `docker compose down -v`，除非明确要删除 MySQL、Neo4j、Redis 与本地存储卷。普通停止使用：

```powershell
docker compose --env-file deploy\.env -f deploy\compose.yml -f deploy\compose.local.yml stop
```
