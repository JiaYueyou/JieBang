# L4/L5 外部模型稳定性与审核验收

## 自动化门槛

L4/L5 发布链路现在分成三道门槛：

1. Provider 对连接/读取超时、429 和暂时性 5xx 做最多 3 次的有界指数退避；认证、权限和请求错误不重试。
2. 机器验收要求每条 L4/L5 陈述置信度不低于 `0.75`、引用至少两条已检索证据，且引用 ID 不得越界。
3. 人工批准时服务端重新校验 Schema、L4/L5 完整性、证据覆盖、置信度和机器拒绝数，并要求至少 4 个字符的审核说明。失败候选不能进入发布状态。

每次 Provider 调用在 `AgentRun.structured_output.provider_diagnostics` 中记录总尝试数、重试数、耗时、稳定错误码和逐次结果；`AgentRun.retry_count` 保存实际重试次数。日志和审计不保存 API Key 或完整 Prompt。

## 离线回归与压测

默认模式完全确定，不访问外部模型，适合 CI 和提交前验收。该模式只替换
HTTP transport，按 `--fail-every` 真实抛出 `httpx.ReadTimeout`，继续经过生产
Provider 的错误分类、指数退避和有界重试循环：

```powershell
Set-Location E:\Project\JieBang
E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe agent-development\scripts\stress_l45.py `
  --runs 100 --concurrency 8 --fail-every 5 `
  --output output\l45-stability-simulation.json
```

默认验收线为成功率 `>= 98%`、质量通过率 `>= 95%`、P95 `<= 120000ms`。未达标时脚本退出码为 2；报告包含错误码、重试数和质量问题分布。

## 真实模型压测

仅在受控测试环境执行，避免将竞赛数据或个人信息发往外部服务：

```powershell
$env:DEEPSEEK_API_KEY='<test-key>'
$env:DEEPSEEK_BASE_URL='https://api.deepseek.com'
$env:DEEPSEEK_MODEL='deepseek-v4-flash'
$env:DEEPSEEK_CONNECT_TIMEOUT_SECONDS='10'
E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe agent-development\scripts\stress_l45.py `
  --live --runs 30 --concurrency 2 --max-attempts 3 `
  --output output\l45-stability-live.json
```

上线前至少执行三轮（低并发 1、中并发 2、目标并发），对比成功率、质量通过率、P95、429/5xx 分布和实际重试数。真实调用可能产生费用，报告只保存聚合指标，不保存模型原文。

## 稳定错误码

| 错误码 | 是否重试 | 含义 |
| --- | --- | --- |
| `provider_connect_timeout` | 是 | 建连或 TLS 握手超时 |
| `provider_read_timeout` / `provider_timeout` | 是 | 响应或请求超时 |
| `provider_rate_limited` | 是 | HTTP 429 |
| `provider_server_error` | 是 | 可恢复的 5xx |
| `provider_transport_error` | 是 | 网络传输失败 |
| `provider_invalid_output` | 是 | JSON 或 Schema 无效，可用修复 Prompt 再试 |
| `provider_auth_error` | 否 | HTTP 401/403，应修复配置 |
| `provider_request_rejected` | 否 | 其他 4xx，应修复请求 |
