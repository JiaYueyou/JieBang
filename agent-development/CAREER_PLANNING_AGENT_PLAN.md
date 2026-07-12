# 匹配解释与职业规划 Agent 开发计划

> 状态：持久化简历、确定性匹配快照和独立匹配解释已完成；职业规划即时文本分析保持兼容，下一阶段让职业规划优先消费 `match_record` 与 `match_evidence`。

## 需求结论

当前 FYZ 前端“转岗指南”需要以下闭环：员工技能/简历输入、企业技术栈与内部需求岗位补充、岗位推荐、补课前后匹配度、学习路径、周期和实战项目。`/career/analyses` 与简历解析接口已可用；文本分析不记录原始简历全文到日志，原文件仅由简历匹配模块私有保存。

## 业务边界

- 后端从技能文本和简历文本提取技能，并确定性计算岗位覆盖率、技能缺口和推荐排序。
- Agent 生成结构化员工画像、差距解释、学习顺序、周期、资源类型和实战项目。
- Agent 不能覆盖 `job_id`、岗位名、`current_match`、`after_match` 和排序分数。
- 内部技术栈、内部需求岗位和目标岗位均为可选输入；未提供时使用现有岗位数据。
- 支持 TXT/Markdown/PDF/DOCX 上传；前端必须以 `multipart/form-data` 提交 `file`，由浏览器生成 boundary。技能文本和简历至少提供一项，解析失败返回明确错误，不静默生成空画像。

## 接口

1. `POST /api/v1/career/resume-extractions`：multipart 文件转文本，返回文件名、文本、字符数和警告。
2. `POST /api/v1/agents/career-plannings`：创建异步转岗规划任务；接收 `skill_text`、`resume_text`、`enterprise_tech`、`internal_jobs[]`、`target_job_ids[]`、`time_budget_weeks`。
3. `GET /api/v1/tasks/{task_id}`：轮询任务，终态结果包含 `resume_profile`、`recommendations[]`、`agent_run_id`、`agent_status`、`warnings[]`。
4. `POST /api/v1/career/analyses`：保留为同步兼容入口，FYZ 页面不再直接调用。

## 实现顺序

1. 独立包新增 `career_planning` 的 Schema、Prompt 和 Agent。
2. 后端新增文件文本提取、技能抽取、岗位候选与确定性评分 Service。
3. 新增 Career API 并注册路由，记录 `AgentRun`。
4. 更新前端 Provider、Store 和上传交互，保持现有推荐卡字段可用。
5. 增加 Agent、Service、API 和前端构建验证。

## 验收标准

- 只有技能文本也能分析；简历和企业信息均可选。
- 上传文本能实际进入分析请求，不能只停留在浏览器文件列表。
- 推荐结果中的岗位 ID 和分数来自后端确定性数据。
- 模型不可用时返回模板化但可用的学习路径，并将 AgentRun 标记为 `degraded`。
- 空输入、空岗位、非法文件、未认证和模型失败均有明确状态。
- 模型超过普通 HTTP 超时时间时，页面仍可通过任务轮询获得模型结果或模板降级结果。

## 下一步衔接

当前 `/career/analyses` 仍使用请求内文本即时计算岗位覆盖率，尚未接收可复用的 `match_id`。`resume`、`match_record`、算法快照与证据已由 `20260712_0006` 建立；下一阶段让职业规划优先消费已保存的匹配结果，当前接口保留为无需持久化的兼容入口。
