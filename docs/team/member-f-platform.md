# 成员 F：平台集成与质量保障

## 1. 职责

负责跨工作区平台能力和交付质量：

- MySQL/Alembic、Redis/Celery 和环境配置；
- CI、安全扫描、测试分层和发布验收；
- API 契约、错误码、任务状态和兼容性治理；
- 文档中心、联调环境和比赛交付清单。

成员 F 维护工程边界，不代替其他成员实现其业务功能。

## 2. 当前基线

- 已有四次 Alembic migration、80 项后端测试和 SQLite 测试环境。
- FYZ 有 14 项前端测试及构建，JTT 有类型检查与构建。
- GitHub Actions 已有 backend、FYZ、JTT 和 repository-security 四类检查。
- Gitleaks 和禁止文件检查已接入。
- 尚缺统一联调验收、覆盖率目标、发布版本和故障手册。

## 3. 上下游接口

- 为成员 A/B 提供稳定 API、认证、配置和联调规范。
- 为成员 C/E 提供任务、运行记录、migration 和测试框架。
- 为成员 D 提供数据协议、导入边界和质量检查。
- 对公共契约变更拥有阻止不兼容合并的质量职责。

## 4. 4 周 MVP

### 第 1 周：环境和数据库

- 验证新克隆可按 README 初始化。
- 固化 MySQL migration、管理员 bootstrap 和 Neo4j/Redis 检查。
- 增加配置缺失时的清晰失败信息。

### 第 2 周：接口治理

- 统一响应、错误码、认证、分页和任务状态。
- 建立 OpenAPI 变更检查和前端类型同步流程。
- 为占位接口建立完成定义。

### 第 3 周：自动化测试

- 分层整理 API、Service、Repository、集成和前端测试。
- 为导入、图谱、Agent 降级和上传流程建立关键回归。
- CI 使用测试环境变量，不依赖个人 `.env`。

### 第 4 周：集成验收

- 建立从空数据库到完整演示数据的验收脚本/清单。
- 验证两套前端、后端、Worker 和数据库组合。
- 输出 MVP 发布说明、已知问题和回滚方案。

## 5. 后 8 周优化

- W5-W6：覆盖率、慢测试、测试数据工厂和契约测试。
- W7-W8：性能基线、日志、任务指标和错误追踪。
- W9-W10：依赖审计、上传安全、权限和备份恢复演练。
- W11-W12：版本冻结、演示环境、答辩检查、最终安全扫描和材料归档。

## 6. 合并门槛

- PR 至少 1 人审核，所有对话解决。
- 四项 CI 通过。
- 数据库改动具有 migration 和回滚验证。
- API 改动同步 OpenAPI、静态文档和前端类型。
- 不包含 `.env`、依赖、构建产物、缓存和个人配置。
- Gitleaks 无泄露。

## 7. 验证

```powershell
cd fyz-src\backend
alembic history
python -m pytest test -q

cd ..\frontend
npm.cmd run test
npm.cmd run build

cd ..\..\jtt-src\frontend
npm.cmd run build
```

仓库检查：

```powershell
git diff --check
git ls-files | Select-String 'node_modules|/dist/|__pycache__|\.env$'
```

## 8. Git 建议

- 分支：`chore/f-ci-contract-check`、`test/f-import-regression`
- 提交：`chore(platform): enforce API contract checks`
- 工程改动与业务功能分开 PR，便于定位 CI 或环境回归。

## 9. 主要风险

- CI 只在本机通过或依赖个人环境；
- migration 版本与真实表结构不一致；
- 公共接口静默破坏另一套前端；
- 安全检查被临时关闭后忘记恢复；
- 临近比赛才发现无法从干净环境复现。