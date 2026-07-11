# 匹配解释与职业规划 Agent 开发计划

## 需求结论

当前 FYZ 前端“转岗指南”需要以下闭环：员工技能/简历输入、企业技术栈与内部需求岗位补充、岗位推荐、补课前后匹配度、学习路径、周期和实战项目。后端目前没有 `/career/analyses`、简历解析接口或职业规划模型，因此本阶段先建立可联调的文本分析闭环，不把文件原件或敏感简历全文写入日志。

## 业务边界

- 后端从技能文本和简历文本提取技能，并确定性计算岗位覆盖率、技能缺口和推荐排序。
- Agent 生成结构化员工画像、差距解释、学习顺序、周期、资源类型和实战项目。
- Agent 不能覆盖 `job_id`、岗位名、`current_match`、`after_match` 和排序分数。
- 内部技术栈、内部需求岗位和目标岗位均为可选输入；未提供时使用现有岗位数据。
- 首版支持 TXT/Markdown 文本上传；PDF/DOCX 解析通过可选依赖接入，解析失败返回明确错误，不静默生成空画像。

## 接口

1. `POST /api/v1/career/resume-extractions`：multipart 文件转文本，返回文件名、文本、字符数和警告。
2. `POST /api/v1/career/analyses`：接收 `skill_text`、`resume_text`、`enterprise_tech`、`internal_jobs[]`、`target_job_ids[]`、`time_budget_weeks`。
3. 响应包含 `resume_profile`、`recommendations[]`、`agent_run_id`、`warnings[]`。

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
