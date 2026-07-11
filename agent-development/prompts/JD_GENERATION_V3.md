# JD Generation Prompt v3

运行时唯一实现位于 `agent-development/src/jiebang_agents/jd_generation/prompt.py`。本文件用于产品、后端和测试评审，不复制为第二个运行时 Prompt。

## 输入

`mode`、`title`、`level`、`department`、`skills_input`、`location`、`company`、`headcount`。

## 约束

- 只产出待人工审核的 JD 草稿，不发布岗位。
- 不编造薪资、福利、学历、工作年限、公司制度或合规承诺。
- 不覆盖系统传入的岗位名称、职级和部门。
- 未知信息进入 `assumptions` 或 `warnings`。
- 仅返回符合 `LLMGeneratedJDDraft` 的 JSON 对象。

## 输出

`standardized_title`、`responsibilities[]`、`requirements[]`、`skills[]`、`bonus_skills[]`、`jd_text`、`assumptions[]`、`warnings[]`。
