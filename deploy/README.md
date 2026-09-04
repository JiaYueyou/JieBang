# FYZ Docker 部署

> 文档类型：现行部署说明
> 状态：首版已实现，未在 2026-08-12 文档审计中执行完整容器启动验收
> 核验提交：`c995a09e`
> 当前编排覆盖 MySQL、Neo4j、Celery Redis、缓存 Redis、迁移、API、worker/beat 和 Nginx。

本次部署仅包含 FYZ 管理前台与后端。JTT 不参与构建、迁移或启动。

## 服务

- `nginx`：托管 Vue 生产构建产物，并将 `/api/*` 代理到 FYZ。
- `fyz-api`：单 Uvicorn worker。Agent 与 Pipeline 恢复仍在 API 进程内运行，因此保持单副本。
- `celery-worker`：消费数据导入与图谱同步长任务。
- `celery-cache-worker`：独立消费轻量缓存预热任务，避免被长任务阻塞。
- `celery-beat`：默认每分钟刷新热门岗位、趋势分析和图谱首页缓存。
- `fyz-migrate`：执行 FYZ Alembic 迁移链后退出。
- `fyz-bootstrap-snapshot`：仅在空库时导入比赛脱敏快照，恢复 Chroma、重建 Neo4j，
  三库验收通过后写入快照指纹；普通重启不会覆盖后续增量数据。
- `mysql`、`neo4j`、`redis`：持久化依赖；`redis` 专用于 Celery 队列和结果。
- `redis-cache`：独立的非持久化 LRU 缓存，用于任务状态投影和高成本查询；不可用时自动回退 MySQL/Neo4j。

基础 Compose 文件仅暴露 Nginx。`compose.local.yml` 额外将依赖服务端口发布在 `127.0.0.1`，用于本地诊断。

## 首次本地启动（PowerShell 7）

创建本地环境文件，并替换所有 `change_*` 占位值：

```powershell
Copy-Item deploy\.env.example deploy\.env
```

如有需要，生成 JWT 密钥：

```powershell
& 'E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe' -c "import secrets; print(secrets.token_urlsafe(48))"
```

校验、构建并启动完整服务栈：

```powershell
docker compose --env-file deploy\.env `
  -f deploy\compose.yml `
  -f deploy\compose.local.yml config

docker compose --env-file deploy\.env `
  -f deploy\compose.yml `
  -f deploy\compose.local.yml build

docker compose --env-file deploy\.env `
  -f deploy\compose.yml `
  -f deploy\compose.local.yml up -d
```

如果 Docker Desktop 报告容器健康但 `docker compose ps` 未显示任何已发布端口，可使用内置的本地边缘回退方案。它会以相同的已构建 Nginx 镜像启动容器，使用 Docker 原生端口发布器，并将其加入现有 Compose 网络：

```powershell
.\deploy\Start-FyzLocalEdge.ps1 -HttpPort 18080
```

此回退方案仅适用于本地 Docker Desktop 端口发布问题。正常的 Linux/Compose 部署应继续使用 `compose.yml` 中的 `nginx` 服务。

迁移容器先把空库升级到当前版本；随后 bootstrap 容器导入仓库内经过校验的比赛
快照。若数据库已有数据但缺少匹配的 ready marker，启动会失败关闭，默认不会覆盖。
只有显式设置 `FYZ_SNAPSHOT_BOOTSTRAP_MODE=force` 才执行重置。

## 验证

查看服务与健康状态：

```powershell
docker compose --env-file deploy\.env `
  -f deploy\compose.yml `
  -f deploy\compose.local.yml ps
```

验证 Nginx、代理 API、两个 Redis、Alembic 与 Celery：

```powershell
Invoke-WebRequest http://localhost:18080/nginx-health
Invoke-WebRequest http://localhost:18080/api/v1/health

docker compose --env-file deploy\.env `
  -f deploy\compose.yml `
  -f deploy\compose.local.yml exec redis `
  redis-cli --no-auth-warning -a '<REDIS_PASSWORD>' ping

docker compose --env-file deploy\.env `
  -f deploy\compose.yml `
  -f deploy\compose.local.yml exec redis-cache `
  redis-cli --no-auth-warning -a '<REDIS_CACHE_PASSWORD>' ping

docker compose --env-file deploy\.env `
  -f deploy\compose.yml `
  -f deploy\compose.local.yml run --rm fyz-migrate alembic current

docker compose --env-file deploy\.env `
  -f deploy\compose.yml `
  -f deploy\compose.local.yml exec celery-worker `
  celery -A app.core.celery_app.celery_app inspect ping --timeout=10
```

预期 Alembic 版本：`20260820_0025`。

本地诊断端点默认地址：

| 组件 | 地址 |
| --- | --- |
| Nginx | `http://localhost:18080` |
| FYZ API 直连 | `http://127.0.0.1:18000` |
| Redis | `127.0.0.1:16379` |
| Redis 缓存 | `127.0.0.1:16380` |
| MySQL | `127.0.0.1:23306` |
| Neo4j HTTP | `http://127.0.0.1:17474` |
| Neo4j Bolt | `bolt://127.0.0.1:17687` |

## 日志与关闭

```powershell
docker compose --env-file deploy\.env `
  -f deploy\compose.yml `
  -f deploy\compose.local.yml logs -f nginx fyz-api celery-worker celery-cache-worker celery-beat

docker compose --env-file deploy\.env `
  -f deploy\compose.yml `
  -f deploy\compose.local.yml down

docker rm -f jiebang-fyz-nginx-local 2>$null
```

`down` 保留命名卷。`down -v` 将永久删除 Docker MySQL、Neo4j、Redis 及私有存储卷，仅在需要完全重置本地环境时使用。

## 部署注意事项

- 基础 Compose 对 JWT、MySQL、Neo4j、Celery Redis 和缓存 Redis 密码使用必填校验；缺失时会直接拒绝启动，不再使用可预测默认密码。
- 在服务器上仅使用 `deploy/compose.yml`，确保 MySQL、Neo4j、Redis 和 API 不会发布到宿主机。
- 设置 `HTTP_PORT=80`，替换所有密码，并在此 Nginx 容器或受信任的上游负载均衡器中终止 TLS。
- 放在 Redis URL 中的密码必须为 URL 安全字符或进行百分号编码。
- Celery Redis 使用 AOF 与 `noeviction`；独立缓存 Redis 使用 256 MiB `volatile-lru` 且不持久化，因此缓存淘汰不会影响队列任务，且不会淘汰无 TTL 的 generation key。业务状态仍以 MySQL 为准。
- 任务轮询优先读取 Redis 且继续校验任务归属；运行态使用短 TTL，终态缓存 24 小时。
- Analysis、Dashboard 和 Graph 使用 generation 版本失效；业务写入成功后递增版本，不扫描删除参数化 key。Redis 故障恢复时会先统一推进三个查询代际，避免故障期间的旧缓存重新生效。单条查询结果超过约 1 MiB 时不缓存。
- 首次部署时 `AUTO_PIPELINE_ENABLED` 为禁用状态。当前调度器与 Agent 恢复为进程内运行，因此暂不要将 `fyz-api` 扩容超过一个副本。
- Chroma 嵌入在 `fyz-storage` 中以嵌入式模式运行。不要对该卷运行多个写入者。在横向扩容之前，应先将 Chroma 迁移至其 HTTP 服务。
- 镜像只包含 `competition-sanitized-v1` 正式包；原始开发数据不进入镜像。
  `INITIAL_ADMIN_PASSWORD` 为必填项，并仅在首次快照导入后写入容器数据库。
