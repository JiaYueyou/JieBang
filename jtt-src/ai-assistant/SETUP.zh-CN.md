# AI 助手独立服务 — 配置说明

## 1. 获取 DeepSeek API Key

1. 访问 https://platform.deepseek.com/
2. 注册账号并登录
3. 进入 API Keys 页面
4. 点击「创建 API Key」
5. 复制生成的 Key（格式：`sk-xxxxxxxxxxxxxxxx`）

## 2. 配置

```bash
cd D:\contest\little challenge\JieBang\jtt-src\ai-assistant

# 复制配置文件
copy .env.example .env
```

编辑 `.env`，将 `DEEPSEEK_API_KEY` 替换为你的 Key：

```
DEEPSEEK_API_KEY=sk-your-actual-key-here
```

## 3. 安装依赖

```bash
# 推荐在项目 Conda 环境中
conda activate jiebang
pip install -r requirements.txt
```

## 4. 启动

```bash
cd D:\contest\little challenge\JieBang\jtt-src\ai-assistant
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

看到以下输出说明启动成功：

```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

## 5. 验证

浏览器打开 http://localhost:8001/health

预期返回：

```json
{"status":"ok","config":{"model":"deepseek-chat","api_key_configured":true}}
```

## 6. 启动前端并连接

在另一个终端：

```bash
cd D:\contest\little challenge\JieBang\jtt-src\frontend
npm run dev
```

前端的 AI 助手会自动通过 Vite 代理请求本服务。打开 http://localhost:5173 即可体验真实大模型回复。

## 常见问题

**Q: 启动后 AI 回复还是 Mock 内容？**
A: 确认 http://localhost:8001/health 返回 `api_key_configured: true`。MSW mock 已禁用 `/api/assistant/chat` 路径，请求会透传到本服务。

**Q: DeepSeek API 调用报错 401？**
A: 检查 `.env` 中的 `DEEPSEEK_API_KEY` 是否正确，确保没有多余空格。

**Q: 可以用其他大模型吗？**
A: 可以。修改 `.env` 中的 `DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL` 指向任意 OpenAI 兼容接口（如阿里通义千问、百度文心、智谱 GLM 等）。
