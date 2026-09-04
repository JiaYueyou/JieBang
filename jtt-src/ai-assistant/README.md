# AI 助手独立服务

> 文档类型：模块运行草案
> 状态：部分现行；开发代理已对接，生产部署与自动化测试缺失
> 核验日期：2026-08-28（`28a4cc5b`）
> 当前 Vite 开发代理已经覆盖本服务的主要端点；`VITE_AI_BASE_URL` 仍未被前端请求层消费，
> 生产构建也不携带 Vite proxy。现状见 [前端 README](../frontend/README.md)。

JTT 求职端 AI 助手的 LLM 代理服务。不依赖 MySQL/Neo4j/Redis，仅需 DeepSeek API Key。

## 快速启动

### 1. 配置

```bash
cd jtt-src/ai-assistant
cp .env.example .env
```

编辑 `.env`，填入你的 DeepSeek API Key：

```
DEEPSEEK_API_KEY=sk-your-key-here
```

> 没有 Key？去 [DeepSeek Platform](https://platform.deepseek.com/) 注册获取。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

建议在 Conda 环境 `jiebang` 中安装：

```bash
conda activate jiebang
pip install -r requirements.txt
```

### 3. 启动服务

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

启动后访问 http://localhost:8001/health 确认：

```json
{"status":"ok","config":{"model":"deepseek-chat","api_key_configured":true}}
```

## 与前端对接

### 方式 A：Vite 开发代理

`jtt-src/frontend/vite.config.ts` 当前按 `/api/v1` 请求前缀分流：

```ts
proxy: {
  '/api/v1/assistant': {                  // AI 助手 → 本服务
    target: 'http://localhost:8001',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/v1/, '/api'),
  },
  '/api': {                               // 其他 API → 主后端
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
}
```

启动前端后，前端 `/api/assistant/chat` 请求自动代理到本服务的 `8001` 端口。

### 生产连接

前端目前使用共享 Axios 实例，没有消费 `VITE_AI_BASE_URL`。生产环境应由 Nginx/网关将
AI 路径转发到 8001、其余 `/api/v1/*` 转发到 JTT 主后端。仓库尚未提供 JTT 专用的
Dockerfile、Compose 或 Nginx 配置，不能直接沿用 FYZ `deploy/`。

## 验证边界

- 当前未配置本服务的 pytest 或接口测试。
- `/health` 只能说明进程和配置加载正常，不证明 DeepSeek 或外部搜索真实可用。
- CORS 当前只允许 5173 的 localhost/127.0.0.1，生产域名需要显式配置。

## API 文档

### POST `/api/assistant/chat`

**请求体：**

```json
{
  "message": "分析我的简历",
  "images": [],
  "pageContext": {
    "name": "resume-detail",
    "path": "/resume/r-1",
    "resumeData": {
      "name": "Java开发简历",
      "targetPosition": "Java后端工程师",
      "skills": [{"name": "Java", "level": "advanced", "category": "编程语言"}],
      "workExperience": [
        {"company": "某科技公司", "position": "后端开发", "description": "负责系统设计"}
      ],
      "education": [{"school": "某某大学", "degree": "硕士", "major": "软件工程"}]
    }
  },
  "history": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮你的？"}
  ]
}
```

**响应体：**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "reply": "Markdown 格式的回答文本",
    "relatedConcepts": [{"name": "Spring Boot", "nodeId": "", "relation": "核心框架"}],
    "suggestedResources": [{"title": "Spring Boot 实战", "type": "course", "url": "", "platform": "慕课网"}],
    "followUpQuestions": ["学习周期多久？", "需要哪些前置知识？"],
    "actions": [{"label": "查看学习路径", "to": "/learning", "icon": "Guide"}]
  }
}
```

### GET `/health`

健康检查。返回 LLM 配置状态。

## 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `DEEPSEEK_API_KEY` | **是** | — | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | 否 | `https://api.deepseek.com` | API 地址 |
| `DEEPSEEK_MODEL` | 否 | `deepseek-chat` | 模型名 |
| `DEEPSEEK_TIMEOUT_SECONDS` | 否 | `60` | 请求超时（秒） |
| `SERVICE_PORT` | 否 | `8001` | 服务端口 |

## 支持的模型

- `deepseek-chat` — DeepSeek V3（默认，性价比高）
- `deepseek-reasoner` — DeepSeek R1（推理更强，速度较慢）
- `deepseek-v4-flash` — 项目后端使用的型号

在 `.env` 中修改 `DEEPSEEK_MODEL` 即可切换。

## 目录结构

```
jtt-src/ai-assistant/
├── main.py              # FastAPI 应用
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量模板
└── README.md            # 本文件
```
