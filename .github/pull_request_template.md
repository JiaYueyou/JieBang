## 改动说明

<!-- 说明问题、方案和用户可见结果。一个 PR 只处理一个明确任务。 -->

## 影响范围

- [ ] FYZ 后端：`fyz-src/backend`
- [ ] FYZ 管理/决策端：`fyz-src/frontend`
- [ ] JTT 求职者端：`jtt-src/frontend`
- [ ] 数据或分析流水线：`data` / `data_analysis`
- [ ] 公共文档、配置或 CI

## 验证结果

- [ ] 后端 `pytest test -q`
- [ ] FYZ 前端 `npm run test`
- [ ] FYZ 前端 `npm run build`
- [ ] JTT 前端 `npm run build`
- [ ] 仅文档改动，不适用上述测试

请粘贴关键测试结果或说明未运行原因：

```text

```

## 兼容性与风险

- [ ] 未修改公共 API、数据库结构、环境变量或共享类型
- [ ] API 变更已附请求/响应示例并同步前端类型
- [ ] 数据库变更包含 Alembic migration 和回滚验证
- [ ] 新增配置已更新 `.env.example`，且没有默认生产密钥
- [ ] 已考虑空数据、错误、权限和重试场景

## 仓库安全

- [ ] 未提交真实 `.env`、Token、密码、API Key 或私钥
- [ ] 未提交 `node_modules`、`dist`、缓存、数据库或个人配置
- [ ] `git diff --cached --check` 通过
- [ ] Gitleaks / Repository Security 检查通过

## 截图或接口示例

<!-- UI 改动附截图；API 改动附示例。无可视化变化时填写“不适用”。 -->

## Reviewer 验收

- [ ] 改动与 PR 描述一致，没有混入无关修改
- [ ] 测试和 CI 完整且通过
- [ ] API、数据库、配置和共享类型兼容性已确认
- [ ] 错误处理和边界场景合理
- [ ] 所有审查对话已解决
