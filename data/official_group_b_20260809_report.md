# 官方招聘数据源组 B 采集报告

- 执行时间：2026-08-09 00:17:34（Asia/Shanghai）
- 范围：2026-01-01 至采集时公开可见的互联网 / AI / 软件 / 硬件相关岗位；不限地区。
- 输出：[official_group_b_20260809.json](official_group_b_20260809.json)
- 规范化记录数：110（均为智谱）。字段为 `source`、`url`、`title`、`company`、`jd_requirements`、`posted_at`、`crawled_at`。
- 数据质量检查：110 个唯一 URL；所有记录均有 JD/任职要求文本和发布日期；日期覆盖为 2026-01-30 至 2026-08-07。

## 合规核验与结果

| 公司 | 官方入口 / robots 核验 | 条款核验与访问结果 | 处理结果 |
| --- | --- | --- | --- |
| 智谱 | 官网 [加入我们](https://www.zhipuai.cn/zh/joinus) 明确将社会招聘跳转到 [Moka 招聘站](https://app.mokahr.com/social-recruitment/zphz/148983?locale=zh-CN#/jobs)。`https://www.zhipuai.cn/robots.txt` 返回 `User-Agent: * / Allow: /`；`https://app.mokahr.com/robots.txt` 仅禁止两个与智谱无关的指定路径，未禁止 `social-recruitment/zphz/148983`。 | 官网加入我们页和公开招聘页未要求登录或验证码即可浏览岗位与完整 JD；页面可见“登录/立即投递”功能未被触发。公开页面未提供可供核验的独立通用服务条款链接，未发现对该公开列表的自动访问禁令。仅以低频只读方式读取正常渲染的公开职位卡，不提交申请、不读取候选人数据。 | 已采集。公开列表显示 147 个在招岗位；按题定岗位范围筛除人力、财务、采购等非互联网/AI/软硬件职能，保留 110 条。 |
| 美团 | 官方入口：[美团招聘社会招聘](https://zhaopin.meituan.com/web/social)。请求 `https://zhaopin.meituan.com/robots.txt` 返回 200 但重定向至招聘前端页面，而非 robots 策略文件。 | 在公共招聘入口未取得可用于自动化采集的 robots 策略或明确适用的公开服务条款；未尝试接口探测、登录或绕过前端限制。 | 未采集；报告保留官方入口和阻断原因。 |
| 京东 | 官方入口：[京东招聘社会招聘](https://zhaopin.jd.com/web/job/job_info_list/3?jobSearch=&jobTypeJson=&workCityJson=11)。请求 `https://zhaopin.jd.com/robots.txt` 被重定向至 `passport.jd.com` 登录页。 | robots 核验本身需要登录，无法完成自动化采集许可判断；未登录、未绕过。 | 未采集；报告保留官方入口和阻断原因。 |
| 高德 / 阿里地图 | 高德官网入口：[关于高德](https://map.amap.com/about/index.html)；`https://www.amap.com/robots.txt` 为地图产品路由策略，未提供招聘列表路径。阿里人才域 `https://talent.alibaba.com/robots.txt` 返回 404。 | 本次未定位到由高德或阿里地图明确归属、无需登录且可核验 robots 与条款的公开岗位列表；不把第三方转载、公众号或搜索摘要当作官方职位来源。 | 未采集；报告保留官方入口和未能完成来源核验的原因。 |

## 日期分布（已入库的 110 条）

| 发布月份 | 记录数 |
| --- | ---: |
| 2026-01 | 8 |
| 2026-03 | 18 |
| 2026-04 | 29 |
| 2026-05 | 27 |
| 2026-06 | 5 |
| 2026-07 | 14 |
| 2026-08 | 9 |

## 采集边界

1. 未使用登录账号、验证码处理、反爬绕过、内部接口或投递功能。
2. `jd_requirements` 保存公开职位卡呈现的职位描述与任职要求原文，供后续导入与技能抽取；不含求职者个人信息。
3. 本报告中的“未采集”并不代表公司没有岗位，仅表示在本轮约束下未获得可合规自动采集的公开来源。
