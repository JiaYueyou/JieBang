# 后端测试目录

测试按照被测代码职责组织：

```text
test/
├── conftest.py          # 全局数据库、客户端和认证 fixture
├── api/                 # HTTP 路由、认证、状态码和响应协议
├── core/                # 安全、异常处理、启动与基础设施逻辑
├── services/            # 领域服务和事务规则
├── repositories/        # SQLAlchemy 查询、写入和约束行为
├── schemas/             # Pydantic 模型与通用响应结构
└── integrations/        # Neo4j 等外部服务集成
```

新增测试应放入与被测代码层级对应的目录。跨越多个层级、通过 HTTP
验证完整业务链路的测试统一放入 `api/`；依赖真实外部服务且允许跳过的
测试放入 `integrations/`。

常用命令：

```powershell
# 全部测试
pytest test/ -v

# 按层执行
pytest test/api/ -v
pytest test/services/ test/repositories/ -v
pytest test/integrations/ -v

# 单个业务模块
pytest test/api/test_jobs.py -v
```
