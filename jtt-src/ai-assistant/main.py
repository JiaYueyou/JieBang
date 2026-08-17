"""
智联职引 — AI 助手独立服务
==========================
选项 A：独立的 LLM 代理服务，专为 JTT 求职端 AI 助手提供 DeepSeek 对话能力。
不依赖 MySQL / Neo4j / Redis，仅需 DeepSeek API Key 即可运行。

依赖: pip install fastapi uvicorn httpx pydantic python-dotenv
启动: uvicorn main:app --host 0.0.0.0 --port 8001 --reload
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

# Load .env from the same directory as this script
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

load_dotenv()

# ── Logging ──
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ai-assistant")

# ── Config ──
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "60"))
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8001"))

# ── App ──
app = FastAPI(title="JieBang AI Assistant", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ──

class PageContext(BaseModel):
    name: str = ""
    path: str = ""
    positionName: str | None = None
    positionId: str | None = None
    resumeId: str | None = None
    resumeData: dict[str, Any] | None = None
    matchData: dict[str, Any] | None = None

class ChatRequest(BaseModel):
    message: str = ""
    images: list[str] = Field(default_factory=list)
    pageContext: PageContext | None = None
    history: list[dict[str, str]] = Field(default_factory=list)

class OptimizeRequest(BaseModel):
    text: str
    style: str = "professional"

class LearningPathRequest(BaseModel):
    positionName: str

class GoalPathRequest(BaseModel):
    goal: str = Field(..., min_length=1, description="用户自然语言学习目标")


class ResumeOptimizeRequest(BaseModel):
    resume: dict[str, Any] = Field(..., description="简历全文")
    position: dict[str, Any] = Field(..., description="岗位上下文（名称+技能要求/差距）")

class ChatResponse(BaseModel):
    code: int = 200
    message: str = "ok"
    data: dict[str, Any] | None = None


# ── System Prompt ──

SYSTEM_PROMPT = """你是「智联职引」平台的 AI 职业助手，专业、耐心、实用。

## 核心能力

1. **简历分析** — 分析简历的技能、经验、教育，给出优化建议
2. **岗位匹配分析** — 分析简历与岗位的匹配度，指出差距和改进方向
3. **学习路径** — 根据目标岗位推荐学习路线、资源、周期
4. **职业咨询** — 解答转行、技能学习、职业规划等问题

## 回答风格

- 使用 Markdown 格式，适当使用 **加粗**、列表、引用
- 简洁明了，避免啰嗦
- 给出具体可操作的建议，不要空泛
- 涉及技能/岗位时，举具体的例子

## 输出格式

你**必须**输出 JSON（不要包含 Markdown 代码块标记），严格按此结构：
{
  "reply": "你的回答（Markdown 格式，纯文本）",
  "relatedConcepts": [{"name": "关联概念名", "nodeId": "", "relation": "关系描述"}],
  "suggestedResources": [{"title": "资源名", "type": "course|book|article|video|project", "url": "", "platform": "平台名"}],
  "followUpQuestions": ["建议追问1", "建议追问2", "建议追问3"],
  "actions": [{"label": "按钮文字", "to": "路由路径", "icon": "图标名"}]
}

actions 是可选的，当建议用户导航到某个功能页时使用。可用路径：
- /positions — 岗位探索
- /positions/:id — 岗位详情
- /graph — 知识图谱
- /match — 匹配诊断
- /resumes — 简历列表
- /resume/editor/:id — 编辑简历
- /resume/upload — 上传简历
- /learning — 学习路径

如果没有合适的 actions，返回空数组[]。"""


# ── Build Messages ──

def build_messages(req: ChatRequest) -> list[dict[str, str]]:
    """构建发送给 LLM 的消息列表。"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject page context as context
    context_parts = []
    if req.pageContext:
        pc = req.pageContext
        context_parts.append(f"用户当前页面：{pc.name}（路径：{pc.path}）")
        if pc.positionName:
            context_parts.append(f"当前岗位：{pc.positionName}")
        if pc.resumeData:
            rd = pc.resumeData
            skills = ", ".join(s.get("name", "") for s in (rd.get("skills") or []))
            latest_work = (rd.get("workExperience") or [None])[0]
            context_parts.append(
                f"用户简历：{rd.get('name', '未知')}"
                f"{'，目标：' + rd.get('targetPosition', '') if rd.get('targetPosition') else ''}"
                f"{'，技能：' + skills if skills else ''}"
                f"{'，最近工作：' + latest_work.get('company', '') if latest_work else ''}"
            )
        if pc.matchData:
            md = pc.matchData
            dims = " | ".join(f"{d.get('name','')}:{d.get('score','')}分" for d in (md.get("dimensions") or []))
            context_parts.append(
                f"匹配结果：{md.get('positionName', '')} — {md.get('totalScore', '')}分"
                f"{'，缺失技能：' + ', '.join(md.get('missingSkills', []) or []) if md.get('missingSkills') else ''}"
                f"{' | ' + dims if dims else ''}"
            )

    if context_parts:
        messages.append({"role": "system", "content": "### 当前页面上下文\n" + "\n".join(context_parts)})

    # Conversation history (last 10 messages)
    for h in (req.history or [])[-10:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    # Current user message
    user_content = req.message
    if req.images:
        user_content += "\n\n[用户上传了 {} 张图片，请根据文字描述回答]".format(len(req.images))
    messages.append({"role": "user", "content": user_content})

    return messages


# ── Call DeepSeek ──

async def call_deepseek(messages: list[dict[str, str]]) -> str:
    """调用 DeepSeek API，返回原始回复文本。"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置")

    async with httpx.AsyncClient(timeout=httpx.Timeout(DEEPSEEK_TIMEOUT)) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": messages,
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
                "max_tokens": 8192,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        # 思考型模型可能把结论放在 reasoning_content，content 为空时兜底取它
        content = msg.get("content") or msg.get("reasoning_content") or ""
        return content


def parse_llm_response(content: str) -> dict[str, Any]:
    """解析 LLM 的 JSON 回复，含重试逻辑。"""
    # Try direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    import re
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Fallback: return content as plain reply
    return {"reply": content, "followUpQuestions": [], "relatedConcepts": [], "suggestedResources": [], "actions": []}


# ── Routes ──

@app.get("/health")
async def health():
    return {"status": "ok", "config": {
        "model": DEEPSEEK_MODEL,
        "base_url": DEEPSEEK_BASE_URL,
        "api_key_configured": bool(DEEPSEEK_API_KEY),
    }}


# ══════════════════ [P1] Agent 工具调用循环 ══════════════════

# 工具注册表：LLM 按名称自主选择调用，执行真实数据源
AGENT_TOOLS: dict[str, dict] = {
    "query_skill_graph": {
        "desc": "查询知识图谱中某岗位的技能树（技能域→技术栈→技术点）。参数: position(岗位名)",
        "func": "tool_query_graph",
    },
    "search_web": {
        "desc": "联网搜索最新信息（招聘要求/技术趋势/学习资源）。参数: query(搜索词)",
        "func": "tool_search_web",
    },
    "analyze_skill_gap": {
        "desc": "对比用户简历技能与目标岗位技能，找出缺失项。参数: position(岗位名)。需用户简历上下文",
        "func": "tool_gap",
    },
}


def tool_query_graph(position: str) -> str:
    """工具：查知识图谱技能树（复用 P0-2 的查询）"""
    result = query_graph_skill_tree(position)
    return result if result else f"知识图谱暂未收录岗位「{position}」的技能树"


async def tool_search_web(query: str) -> str:
    """工具：联网搜索（复用既有 search_web，截取摘要）"""
    results = await search_web(query, max_results=5)
    if not results:
        return f"搜索「{query}」无结果（网络不可用）"
    lines = [f"[{i+1}] {r['title']}: {r['snippet'][:100]}" for i, r in enumerate(results[:5])]
    return "\n".join(lines)


def tool_gap(position: str, resume_data: dict | None) -> str:
    """工具：技能差距分析（基于用户简历 vs 图谱技能树）"""
    if not resume_data or not resume_data.get("skills"):
        return "用户简历上下文缺失，无法分析差距"
    tree_text = query_graph_skill_tree(position)
    if not tree_text:
        return f"图谱无「{position}」技能树，建议先用 search_web 查岗位要求"
    import re as _re
    graph_skills = {m.group(0).strip() for m in _re.finditer(r"[\w一-鿿 .#+/-]+", tree_text)}
    graph_skills = {g for g in graph_skills if 2 <= len(g) <= 30}
    user_skills = {s.get("name", "") for s in resume_data["skills"] if s.get("name")}
    matched = {g for g in graph_skills if any(u.lower() in g.lower() or g.lower() in u.lower() for u in user_skills)}
    missing = sorted(graph_skills - matched)[:10]
    return (f"用户技能：{'、'.join(sorted(user_skills))}\n"
            f"图谱技能树命中 {len(matched)} 项\n"
            f"缺失（建议学习）：{'、'.join(missing) if missing else '无明显缺失'}")


@app.post("/api/assistant/agent-chat")
async def agent_chat(req: ChatRequest):
    """[P1] Agent 循环：LLM 自主规划工具调用 → 执行真实工具 → 综合作答"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail={"code": 503, "message": "DEEPSEEK_API_KEY not configured", "data": None})

    rd = req.pageContext.resumeData if req.pageContext else None
    thinking: list[dict] = [{"icon": "🤖", "text": "分析你的问题，规划工具调用…"}]

    # ── 第 1 步：LLM 规划要调用哪些工具 ──
    tools_desc = "\n".join(f"- {name}: {t['desc']}" for name, t in AGENT_TOOLS.items())
    plan_prompt = (
        "你是任务规划器。根据用户问题，决定需要调用哪些工具来获取真实数据。\n"
        f"可用工具：\n{tools_desc}\n\n"
        f"用户问题：{req.message}\n\n"
        + (f"用户简历技能：{', '.join(s.get('name','') for s in rd['skills'])}\n" if rd else "")
        + '输出 JSON：{"tools": [{"name": "工具名", "args": {"参数名": "值"}}], "reason": "为什么调这些"}\n'
        "最多 3 个工具。如果不需要工具（纯常识问答），返回 {\"tools\": []}"
    )
    try:
        raw = await call_deepseek([{"role": "system", "content": plan_prompt}])
        plan = parse_llm_response(raw)
        tool_calls = plan.get("tools", [])[:3]
    except Exception:
        tool_calls = []

    # ── 第 2 步：执行工具（真实数据源）──
    tool_results: list[str] = []
    for tc in tool_calls:
        name, args = tc.get("name", ""), tc.get("args", {}) or {}
        if name not in AGENT_TOOLS:
            continue
        thinking.append({"icon": "🔧", "text": f"调用工具 {name}({args})…"})
        try:
            if name == "query_skill_graph":
                r = tool_query_graph(str(args.get("position", "")))
            elif name == "search_web":
                r = await tool_search_web(str(args.get("query", req.message)))
            elif name == "analyze_skill_gap":
                r = tool_gap(str(args.get("position", "")), rd)
            else:
                r = "未知工具"
            tool_results.append(f"[工具 {name} 结果]\n{r}")
            thinking.append({"icon": "📊", "text": f"{name} 返回 {len(r)} 字符数据"})
        except Exception as e:
            tool_results.append(f"[工具 {name} 失败]: {e}")
            thinking.append({"icon": "⚠️", "text": f"{name} 调用失败，跳过"})

    # ── 第 3 步：LLM 综合工具结果作答 ──
    thinking.append({"icon": "🧠", "text": f"综合 {len(tool_results)} 份工具结果生成回答…"})
    final_sys = (
        "你是智联职引的 AI 职业助手。基于工具返回的真实数据回答用户问题。\n"
        "要求：优先引用工具数据（标注来源），工具没覆盖的才用自身知识；输出 JSON：\n"
        '{"reply": "Markdown 回答", "followUpQuestions": ["追问1", "追问2"]}'
    )
    ctx = ""
    if rd:
        ctx = f"\n用户简历：目标{rd.get('targetPosition','')}，技能{'、'.join(s.get('name','') for s in rd.get('skills',[]))}\n"
    final_user = f"用户问题：{req.message}\n{ctx}\n工具结果：\n" + ("\n\n".join(tool_results) if tool_results else "（无工具调用，直接回答）")

    try:
        raw = await call_deepseek([
            {"role": "system", "content": final_sys},
            {"role": "user", "content": final_user},
        ])
        parsed = parse_llm_response(raw)
        reply = parsed.get("reply") or raw
        follow_ups = parsed.get("followUpQuestions", [])
    except Exception:
        reply, follow_ups = "综合回答生成失败，请稍后重试", []

    thinking.append({"icon": "✅", "text": f"完成（调用 {len(tool_results)} 个工具）"})

    return {"code": 200, "message": "ok", "data": {
        "reply": reply,
        "thinkingSteps": thinking,
        "toolsCalled": [tc.get("name") for tc in tool_calls],
        "followUpQuestions": follow_ups,
    }}


@app.post("/api/assistant/chat")
async def chat(req: ChatRequest):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail={
            "code": 503,
            "message": "DEEPSEEK_API_KEY not configured",
            "data": None,
        })

    try:
        messages = build_messages(req)
        raw = await call_deepseek(messages)
        parsed = parse_llm_response(raw)

        return {
            "code": 200,
            "message": "ok",
            "data": {
                "reply": parsed.get("reply", ""),
                "relatedConcepts": parsed.get("relatedConcepts", []),
                "suggestedResources": parsed.get("suggestedResources", []),
                "followUpQuestions": parsed.get("followUpQuestions", []),
                "actions": parsed.get("actions", []),
            },
        }
    except httpx.HTTPStatusError as e:
        log.error(f"DeepSeek API error: {e.response.status_code} {e.response.text[:200]}")
        raise HTTPException(status_code=502, detail={
            "code": 502, "message": f"LLM 服务暂不可用（{e.response.status_code}）", "data": None,
        })
    except httpx.TimeoutException:
        log.error("DeepSeek API timeout")
        raise HTTPException(status_code=504, detail={
            "code": 504, "message": "LLM 响应超时，请稍后重试", "data": None,
        })
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail={
            "code": 500, "message": "AI 助手内部错误", "data": None,
        })


# ── Learning Assistant alias (same as chat) ──

@app.post("/api/learning/assistant/chat")
async def learning_chat(req: ChatRequest):
    return await chat(req)


QUIZ_PROMPT = """你是技术面试官，针对给定的学习路径步骤生成5道多选题。
每道题4个选项，标记正确答案。
输出 JSON 严格格式，不要包含 markdown 代码块标记：
{"questions": [{"id": "q-编号", "type": "choice", "question": "题目", "options": ["A", "B", "C", "D"], "correctAnswer": 索引(0-3), "explanation": "解析"}]}
题目要有实际考察价值，覆盖核心概念和易错点。"""

RESOURCE_PROMPT = """你是学习资源推荐专家。根据用户提供的技能名称，为每个技能推荐3个高质量学习资源。
输出 JSON 严格格式：
{"skills": {"技能名": [{"title": "资源标题", "type": "course|book|video|article|project", "url": "", "platform": "平台名"}]}}
资源类型包括：course(课程), book(书籍), video(视频), article(文章), project(项目)。
平台如：慕课网、B站、Coursera、京东、GitHub 等。"""


@app.post("/api/learning/assistant/generate-path")
async def learning_generate_path(req: ChatRequest):
    """Alias: uses the same generate-learning-path endpoint."""
    pos = req.pageContext.positionName if req.pageContext and req.pageContext.positionName else (req.message or "Java开发工程师")
    return await generate_learning_path(LearningPathRequest(positionName=pos))


@app.post("/api/learning/assistant/recommend-resources")
async def recommend_resources(req: ChatRequest):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail={"code": 503, "message": "DEEPSEEK_API_KEY not configured", "data": None})
    skill_names = [req.message] if req.message else ["Java"]
    try:
        raw = await call_deepseek([
            {"role": "system", "content": RESOURCE_PROMPT},
            {"role": "user", "content": "技能：" + ", ".join(skill_names)},
        ])
        parsed = parse_llm_response(raw)
        return {"code": 200, "message": "ok", "data": {"skills": parsed.get("skills", {})}}
    except Exception as e:
        log.error(f"Recommend resources error: {e}")
        raise HTTPException(status_code=500, detail={"code": 500, "message": "推荐失败", "data": None})


async def _url_alive(url: str) -> bool:
    """[防幻觉] 探活单个 URL：2xx/3xx 视为可达；超时/4xx/5xx/异常视为不可达。"""
    if not url or not url.startswith(("http://", "https://")):
        return not url  # 空链接（平台搜索页占位）保留，非 http 编造链接丢弃
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 (compatibility)"}) as client:
            resp = await client.head(url)
            # 部分站点不支持 HEAD，退回 GET 取 headers
            if resp.status_code == 405:
                resp = await client.get(url)
            return resp.status_code < 400
    except Exception:
        return False


async def filter_alive_urls(resources: list[dict]) -> list[dict]:
    """[防幻觉] 并发探活全部 URL，只保留真实可达的资源；全挂时返回 B站搜索页兜底。"""
    if not resources:
        return resources
    results = await asyncio.gather(*(_url_alive(str(r.get("url", ""))) for r in resources))
    alive = [r for r, ok in zip(resources, results) if ok]
    dropped = len(resources) - len(alive)
    if dropped:
        log.info(f"[防幻觉] 探活丢弃 {dropped} 个不可达链接")
    if not alive:
        # 全部失效：退回平台搜索页（保证功能不空手而归）
        from urllib.parse import quote
        kw = quote(resources[0].get("title", "编程")[:20])
        alive = [{"title": "哔哩哔哩搜索：" + resources[0].get("title", "")[:20],
                  "type": "video", "url": f"https://search.bilibili.com/all?keyword={kw}", "platform": "哔哩哔哩"}]
    return alive


@app.post("/api/assistant/generate-links")
async def generate_links(req: ChatRequest):
    """按主题联网搜索学习资源，返回带 URL 的链接列表。"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail={"code": 503, "message": "DEEPSEEK_API_KEY not configured", "data": None})
    topic = req.message or "Java 开发"
    max_results = 6

    # 优先搜索 B站 / 抖音网课视频
    queries = [
        topic + " 哔哩哔哩 教程",
        topic + " bilibili 入门 课程",
        topic + " 抖音 网课 教学",
        topic + " 视频教程 从入门到精通",
    ]
    all_results: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for q in queries:
        results = await search_web(q, max_results=3)
        for r in results:
            if r["url"] and r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_results.append(r)
        if len(all_results) >= max_results:
            break

    # LLM 重排序 + 结构化（优先视频网课）
    system_prompt = (
        "你是学习资源推荐专家。根据搜索到的信息，为主题推荐 3-5 个网课视频链接。\n"
        "**优先选择哔哩哔哩(bilibili)、抖音的网课/教学视频**，其次才是其他视频平台。\n"
        "只使用搜索结果中真实存在的资源，不要编造 URL。\n"
        "输出严格的 JSON 格式：\n"
        '{"resources": [{"title": "视频/课程标题", "type": "video", "url": "https://...", "platform": "哔哩哔哩|抖音|其他平台"}]}'
    )
    search_context = ""
    for i, r in enumerate(all_results[:8]):
        search_context += f"[{i+1}] {r['title']}: {r['snippet']}\n{r['url']}\n\n"
    user_prompt = "主题：" + topic + "\n\n搜索结果：\n" + search_context

    try:
        if all_results:
            raw = await call_deepseek([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
            parsed = parse_llm_response(raw)
            resources = parsed.get("resources", [])
        else:
            # 搜索不可用：直接生成 B站/抖音搜索页真实链接 + LLM 补充具体课程
            from urllib.parse import quote
            kw = quote(topic)
            resources = [
                {"title": f"哔哩哔哩搜索：{topic}", "type": "video", "url": f"https://search.bilibili.com/all?keyword={kw}", "platform": "哔哩哔哩"},
                {"title": f"抖音搜索：{topic}", "type": "video", "url": f"https://www.douyin.com/search/{kw}", "platform": "抖音"},
                {"title": f"哔哩哔哩·知识区：{topic}", "type": "video", "url": f"https://www.bilibili.com/v/knowledge", "platform": "哔哩哔哩"},
            ]
            try:
                raw = await call_deepseek([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "主题：" + topic + "\n（搜索不可用，请基于知识推荐哔哩哔哩/抖音的知名网课视频，URL 用真实的视频链接或平台搜索页链接）"},
                ])
                parsed = parse_llm_response(raw)
                extra = parsed.get("resources", [])
                for e in extra:
                    if e.get("url") and not any(r["url"] == e["url"] for r in resources):
                        resources.append(e)
            except Exception:
                pass

        if not resources:
            resources = [{"title": topic + " 网课视频", "type": "video", "url": "", "platform": "哔哩哔哩"}]

        # [防幻觉] URL 探活：只保留真实可达（2xx/3xx）的链接，编造/失效链接静默丢弃
        resources = await filter_alive_urls(resources)

        return {"code": 200, "message": "ok", "data": {"resources": resources}}
    except Exception as e:
        log.error(f"Generate links error: {e}")
        raise HTTPException(status_code=500, detail={"code": 500, "message": "生成学习链接失败", "data": None})


@app.post("/api/learning/assistant/quiz")
async def generate_quiz(req: ChatRequest):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail={"code": 503, "message": "DEEPSEEK_API_KEY not configured", "data": None})
    path_context = req.message or "Java开发"
    try:
        raw = await call_deepseek([
            {"role": "system", "content": QUIZ_PROMPT},
            {"role": "user", "content": "学习路径主题：" + path_context},
        ])
        parsed = parse_llm_response(raw)
        questions = parsed.get("questions", [])
        if not questions:
            questions = [{"id": "q-1", "type": "choice", "question": "Java 中 String 是不可变的吗？", "options": ["是", "否", "不确定", "取决于版本"], "correctAnswer": 0, "explanation": "String 在 Java 中是不可变的"}]
        return {"code": 200, "message": "ok", "data": {"questions": questions}}
    except Exception as e:
        log.error(f"Quiz generation error: {e}")
        raise HTTPException(status_code=500, detail={"code": 500, "message": "题目生成失败", "data": None})


@app.post("/api/tailor/optimize-phrase")
async def tailor_optimize(req: OptimizeRequest):
    """Alias for the assistant optimize-phrase endpoint."""
    return await optimize_phrase(req)


# ── Web Search ──

async def search_web(query: str, max_results: int = 10) -> list[dict[str, str]]:
    """搜索网络，返回标题+摘要列表。如不可用返回空列表。"""
    # Proxy settings (for users behind firewall)
    proxy_url = os.getenv("SEARCH_PROXY", "")
    ddgs_kwargs = {"proxies": proxy_url} if proxy_url else {}

    try:
        from duckduckgo_search import DDGS
        with DDGS(**ddgs_kwargs) as ddgs:
            results = []
            for r in ddgs.text(query, max_results=max_results):
                results.append({"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")})
            if results:
                return results
            log.warning("DuckDuckGo returned 0 results, trying fallback...")
    except Exception as e:
        log.warning(f"DuckDuckGo unavailable: {e}")
    # Fallback: try Bing API if configured
    bing_key = os.getenv("BING_SEARCH_API_KEY", "")
    if bing_key:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.bing.microsoft.com/v7.0/search",
                    headers={"Ocp-Apim-Subscription-Key": bing_key},
                    params={"q": query, "count": max_results, "freshness": "Year", "mkt": "zh-CN"},
                )
                if resp.status_code == 200:
                    results = []
                    for r in resp.json().get("webPages", {}).get("value", []):
                        results.append({"title": r.get("name", ""), "snippet": r.get("snippet", ""), "url": r.get("url", "")})
                    return results
        except Exception as e2:
            log.warning(f"Bing search unavailable: {e2}")
    return []


def rerank_skills(search_results: list[dict[str, str]], position: str) -> str:
    """将搜索结果拼成上下文供 LLM 提取技能。"""
    snippets = []
    for i, r in enumerate(search_results[:8]):  # top 8
        snippets.append(f"[{i+1}] {r['title']}: {r['snippet']}")
    return "以下是从网络搜索到的关于「" + position + "」的最新信息：\n\n" + "\n\n".join(snippets)


# ── Generate Learning Path (search + rerank + structure) ──

# ── [Agent 2] 知识图谱技能树查询 ──

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

def query_graph_skill_tree(position_name: str) -> str:
    """
    查询 Neo4j 知识图谱中该岗位的技能树（SkillArea→TechStack→TechPoint），
    返回可注入 prompt 的文本。图谱不可用/无该岗位返回空串。
    """
    if not NEO4J_PASSWORD:
        return ""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), connection_timeout=5)
        with driver.session() as s:
            rows = s.run(
                "MATCH (j:Job {name: $job})-[:REQUIRES_AREA]->(sa:SkillArea)-[:CONTAINS]->(ts:TechStack) "
                "OPTIONAL MATCH (ts)-[:SUPPORTS]->(tp:TechPoint) "
                "RETURN sa.name AS area, ts.name AS stack, collect(tp.name) AS points "
                "ORDER BY area, stack",
                {"job": position_name},
            ).data()
        driver.close()
        if not rows:
            return ""
        lines = []
        for r in rows:
            pts = "、".join(p for p in (r["points"] or []) if p)
            lines.append(f"- {r['area']} / {r['stack']}" + (f"（知识点：{pts}）" if pts else ""))
        return "知识图谱中该岗位的技能树（按此结构排学习步骤，基础技能域在前）：\n" + "\n".join(lines)
    except Exception:
        return ""


@app.post("/api/assistant/generate-learning-path")
async def generate_learning_path(req: LearningPathRequest):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail={"code": 503, "message": "DEEPSEEK_API_KEY not configured", "data": None})

    position = req.positionName.strip()
    if not position:
        raise HTTPException(status_code=400, detail={"code": 400, "message": "请输入岗位名称", "data": None})

    # Step 1: Search web for current skills
    search_queries = [
        position + " 技能要求 2026",
        position + " 岗位职责 技术栈",
        position + " 招聘要求 必备技能",
        position + " skill requirements 2025 2026",
    ]
    all_results: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for q in search_queries:
        results = await search_web(q, max_results=5)
        for r in results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_results.append(r)

    # Step 2: Build search context
    search_available = len(all_results) > 0
    search_context = rerank_skills(all_results, position) if search_available else ""
    source_note = "（基于2025-2026年网络招聘信息）" if search_available else "（基于知识库，建议联网获取最新信息）"

    # Step 3: LLM generates structured learning path with reranking
    system_prompt = (
        "你是一个专业的学习路径设计师。根据用户的目标岗位，生成一份详细、可执行的学习路径。\n"
        "要求：\n"
        "1. 技能必须来自搜索结果（如提供），不要编造\n"
        "2. 按基础→进阶排序，标注每个技能的前置依赖\n"
        "3. 每个步骤包含：标题、描述、预计学习周期、推荐学习资源\n"
        "4. 总步骤 5-7 步，总时长合理\n"
        "5. 输出严格的 JSON 格式：\n"
        "{\n"
        '  "pathName": "路径名称（含岗位名）",\n'
        '  "steps": [\n'
        '    {\n'
        '      "title": "步骤标题",\n'
        '      "description": "详细描述要学什么、学到什么程度",\n'
        '      "duration": "X-Y周",\n'
        '      "resources": [\n'
        '        {"title": "资源名", "type": "course|book|video|article", "platform": "平台名"}\n'
        '      ]\n'
        '    }\n'
        "  ],\n"
        '  "totalDuration": "总时长",\n'
        '  "sourceNote": "信息来源说明"\n'
        "}"
    )

    user_prompt = "目标岗位：" + position + "\n\n"
    # [Agent 2] 注入知识图谱技能树 —— 路径排序以图谱依赖结构为准（防幻觉）
    graph_tree = query_graph_skill_tree(position)
    if graph_tree:
        user_prompt += graph_tree + "\n\n"
    if search_context:
        user_prompt += search_context + "\n\n请根据知识图谱技能树和搜索结果生成学习路径：图谱中列出的技能必须覆盖，顺序遵循图谱的技能域结构（基础在前）；搜索结果补充最新趋势，注意筛选近一年的信息。"
    else:
        user_prompt += "请根据知识图谱技能树" + ("和你的知识" if graph_tree else "你的知识") + "生成学习路径，优先使用图谱中列出的技能，标注哪些是你确定的最新要求。"

    # [P3] Agent 推理步骤记录（前端逐步展示思考过程）
    graph_skill_count = graph_tree.count("\n") if graph_tree else 0
    thinking_steps = [
        {"icon": "🎯", "text": f"分析目标岗位「{position}」的技能要求"},
        {"icon": "🔍", "text": ("查询知识图谱：获取技能树结构" if graph_tree else "知识图谱暂未收录该岗位，将基于联网信息") ,
         "detail": f"图谱返回 {graph_skill_count} 个技能条目" if graph_tree else None},
        {"icon": "🌐", "text": f"联网搜索最新招聘信息（{len(all_results)} 条结果）" if search_available else "联网搜索不可用，使用模型知识生成"},
        {"icon": "🧠", "text": "综合图谱技能树与搜索结果，规划学习路径"},
        {"icon": "✅", "text": "生成完成，路径已按图谱依赖结构排序"},
    ]

    try:
        raw = await call_deepseek([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        parsed = parse_llm_response(raw)
        steps = parsed.get("steps", [])
        if not steps:
            raise ValueError("No steps generated")

        return {
            "code": 200,
            "message": "ok",
            "data": {
                "pathName": parsed.get("pathName", position + "学习路径"),
                "positionName": position,
                "steps": steps,
                "totalDuration": parsed.get("totalDuration", ""),
                "sourceNote": source_note,
                "searchResultsCount": len(all_results),
                "thinkingSteps": thinking_steps,
            },
        }
    except Exception as e:
        log.error(f"Generate learning path error: {e}")
        raise HTTPException(status_code=500, detail={"code": 500, "message": "生成失败：" + str(e), "data": None})


# ── Generate Learning Path from Goal (自然语言学习目标 → 个性化路径) ──

@app.post("/api/assistant/generate-learning-path-from-goal")
async def generate_learning_path_from_goal(req: GoalPathRequest):
    """根据用户自然语言描述的学习目标，AI 分析后生成从基础到进阶的个性化学习路径"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail={"code": 503, "message": "DEEPSEEK_API_KEY not configured", "data": None})

    goal = req.goal.strip()
    if not goal:
        raise HTTPException(status_code=400, detail={"code": 400, "message": "请输入学习目标", "data": None})

    system_prompt = (
        "你是一个专业的学习路径设计师。根据用户描述的学习目标，"
        "分析其真实需求，生成一条从基础到进阶的具体学习路径。\n\n"
        "要求：\n"
        "1. 先分析用户的学习目标，确定需要覆盖的知识领域和技能树\n"
        "2. 按基础→进阶的顺序组织，每个步骤标注前置依赖关系\n"
        "3. 每个步骤包含：标题、详细描述（含关键知识点和应达到的程度）、预计学习周期、推荐学习资源\n"
        "4. 总步骤 5-7 步，总时长合理（4-16 周）\n"
        "5. 内容要具体可执行，不要泛泛而谈；资源推荐要真实存在的平台或书籍\n"
        "6. 输出严格的 JSON 格式：\n"
        "{\n"
        '  "pathName": "路径名称（简洁概括学习目标，10字以内）",\n'
        '  "goalAnalysis": "一句话概括你对用户学习目标的理解",\n'
        '  "steps": [\n'
        '    {\n'
        '      "title": "步骤标题",\n'
        '      "description": "详细描述要学什么、关键知识点、应达到的程度",\n'
        '      "duration": "X-Y周",\n'
        '      "resources": [{"title": "资源名", "type": "course|book|video|article|project", "platform": "平台名"}]\n'
        '    }\n'
        "  ],\n"
        '  "totalDuration": "总时长（如 8周）",\n'
        '  "sourceNote": "基于 AI 知识库生成"\n'
        "}"
    )

    try:
        raw = await call_deepseek([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用户的学习目标：{goal}\n\n请分析目标并生成学习路径。"},
        ])
        parsed = parse_llm_response(raw)
        steps = parsed.get("steps", [])
        if not steps:
            raise ValueError("No steps generated")

        return {
            "code": 200,
            "message": "ok",
            "data": {
                "pathName": parsed.get("pathName", "学习路径"),
                "goalAnalysis": parsed.get("goalAnalysis", ""),
                "steps": steps,
                "totalDuration": parsed.get("totalDuration", ""),
                "sourceNote": parsed.get("sourceNote", "基于 AI 知识库生成"),
            },
        }
    except Exception as e:
        log.error(f"Generate learning path from goal error: {e}")
        raise HTTPException(status_code=500, detail={"code": 500, "message": "生成失败：" + str(e), "data": None})


# ── Optimize Phrase ──

OPTIMIZE_PROMPTS = {
    "professional": "将以下文本改写得更专业、正式，用词精准，句式完整。",
    "concise": "将以下文本改写得更简洁精炼，去掉冗余词，保留核心信息。",
    "match": "将以下文本改写得更匹配目标岗位要求，突出技能关键词和项目成果。",
    "impact": "将以下文本改写得更具冲击力和说服力，用量化数据、结果导向的方式表达。",
}

@app.post("/api/assistant/optimize-phrase")
async def optimize_phrase(req: OptimizeRequest):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail={"code": 503, "message": "DEEPSEEK_API_KEY not configured", "data": None})

    style_desc = OPTIMIZE_PROMPTS.get(req.style, OPTIMIZE_PROMPTS["professional"])
    system_prompt = (
        "你是简历文字润色专家。根据要求将用户提供的文本改写为3个不同版本。\n"
        f"{style_desc}\n"
        "输出 JSON，严格格式：{\"suggestions\": [\"版本1\", \"版本2\", \"版本3\"]}\n"
        "每个版本不超过50字，保持原意但表达更精炼专业。"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.text},
    ]

    try:
        raw = await call_deepseek(messages)
        parsed = parse_llm_response(raw)
        suggestions = parsed.get("suggestions", [])
        if not suggestions:
            suggestions = [req.text] * 3
        return {"code": 200, "message": "ok", "data": {"suggestions": suggestions}}
    except Exception as e:
        log.error(f"Optimize error: {e}")
        raise HTTPException(status_code=500, detail={"code": 500, "message": "优化失败", "data": None})


# ── Optimize Resume（简历优化建议：向目标岗位靠齐）──

RESUME_OPTIMIZE_PROMPT = """你是资深简历优化专家。根据目标岗位要求，对求职者简历给出具体、可落地的修改建议，目标是让简历尽可能向岗位靠齐。

改写原则：
1. 突出与岗位匹配的技能与成果，用数据量化（如"提升 30%"、"支撑 10 万 QPS"）
2. 动词开头、结果导向，避免空泛描述
3. 复用岗位 JD 中的关键词和术语，让表述贴合岗位风格
4. 只改技能、工作经历、自我评价中可以对照岗位优化的部分，不要编造不存在的技能或经历

输出严格 JSON（不要包含 Markdown 代码块标记）：
{"suggestions": [{"id": "sg-1", "section": "skills|workExperience|selfEvaluation", "field": "具体字段", "original": "原文", "suggested": "优化后", "reason": "理由", "changeType": "small|large"}]}"""


@app.post("/api/assistant/optimize-resume")
async def optimize_resume(req: ResumeOptimizeRequest):
    """根据简历 + 目标岗位，AI 生成向岗位靠齐的优化建议"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail={"code": 503, "message": "DEEPSEEK_API_KEY not configured", "data": None})

    resume = req.resume or {}
    position = req.position or {}
    if not resume and not position:
        raise HTTPException(status_code=400, detail={"code": 400, "message": "简历或岗位信息为空", "data": None})

    pos_name = position.get("name", "")
    pos_required = position.get("requiredSkills") or []
    pos_preferred = position.get("preferredSkills") or []
    pos_missing = position.get("missingSkills") or []
    pos_weak = position.get("weakSkills") or []
    pos_match = position.get("matchSkills") or []

    user_prompt = (
        f"目标岗位: {pos_name}\n"
        f"必备技能: {pos_required}\n"
        f"加分技能: {pos_preferred}\n"
        f"缺失技能: {pos_missing}\n"
        f"薄弱技能: {pos_weak}\n"
        f"已匹配技能: {pos_match}\n\n"
        f"=== 简历内容 ===\n"
        f"技能: {resume.get('skills') or []}\n"
        f"工作经历: {resume.get('workExperience') or []}\n"
        f"项目经历: {resume.get('projects') or []}\n"
        f"自我评价: {resume.get('selfEvaluation') or ''}\n\n"
        f"请逐条给出向岗位靠齐的具体修改建议。"
    )

    try:
        raw = await call_deepseek([
            {"role": "system", "content": RESUME_OPTIMIZE_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
        parsed = parse_llm_response(raw)
        suggestions = parsed.get("suggestions", [])
        if not isinstance(suggestions, list):
            suggestions = []
    except Exception as e:
        log.error(f"Optimize resume error: {e}")
        suggestions = []

    return {"code": 200, "message": "ok", "data": {"suggestions": suggestions}}


# ── Main ──

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=SERVICE_PORT, reload=True)
