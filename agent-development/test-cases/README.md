# Agent 测试样例约定

这里存放不含个人信息的固定 Provider Mock 输入、预期 JSON 与回归场景说明。独立 Agent 单元测试位于 `agent-development/tests/`，后端接入回归测试位于 `fyz-src/backend/test/`。

JD Generation 至少覆盖：正常结构化输出、字段别名/异常形状、模型不可用模板降级、非法 JSON、超时、鉴权和人工发布边界。
