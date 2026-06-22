# 智联职引（JieBang）

多源异构数据驱动的岗位与能力图谱构建平台。仓库按成员交付边界划分工作区，
公共数据、分析流水线和项目文档保留在根目录。

## 目录结构

```text
JieBang/
├── fyz-src/                 # FYZ 主工作区：FastAPI 后端 + 管理/决策端 Vue 3
│   ├── backend/
│   └── frontend/
├── jtt-src/                 # JTT 工作区
│   ├── frontend/            # 求职者端 Vue 3
│   └── docs/                # JTT 数据提取说明与参考材料
├── data/                    # 原始岗位数据
├── data_analysis/           # 数据清洗、标准化与技能抽取流水线
├── docs/                    # 需求、规范和仓库安全文档
└── AGENTS.md                # 仓库级开发约定
```

## 快速验证

```bash
# FYZ 后端
cd fyz-src/backend
pytest test/ -v

# FYZ 管理/决策端
cd fyz-src/frontend
npm ci
npm run test
npm run build

# JTT 求职者端
cd jtt-src/frontend
npm ci
npm run build
```

本地密钥只允许写入被忽略的 `.env`。请从各工作区的 `.env.example`
复制配置，禁止提交依赖目录、构建产物、缓存或个人工具配置。
