# 官方招聘数据源组 A 采集报告

采集日期：2026-08-09（Asia/Shanghai）
目标时间范围：2026-01-01 至 2026-08-09
目标范围：互联网、AI、软件与硬件相关岗位；不限地区。
结果文件：`data/official_group_a_20260809.json`
规范化职位记录数：**0**

本次只检查各公司的公开官方招聘入口、robots.txt 和可公开取得的招聘条款；未登录、未提交简历、未调用隐藏接口，未尝试绕过访问控制、验证码或重定向。

| 公司 | 官方招聘入口 | robots.txt / 条款核验 | 合规结论 | 采集记录数 | 日期覆盖 |
| --- | --- | --- | --- | ---: | --- |
| 特斯拉（Tesla） | https://www.tesla.com/careers | `https://www.tesla.com/robots.txt` 对普通 GET 返回 HTTP 403，无法读取适用爬取规则。 | 无法确认自动采集许可；按保守原则停止。 | 0 | 无可验证职位发布日期 |
| 腾讯 | https://careers.tencent.com/ | `https://careers.tencent.com/robots.txt` 返回招聘站 404 页（未提供 robots 规则）；但官方[服务条款](https://careers.tencent.com/m/zh-cn/termsservice.html)第 7.2.4 条明确禁止通过程序、软件等抓取平台或服务相关信息、数据。 | 条款明确禁止自动采集；停止。 | 0 | 无可验证职位发布日期 |
| 阿里巴巴 | https://talent.alibaba.com/ | `https://talent.alibaba.com/robots.txt` 返回 404（未提供 robots 规则）。公开职位列表入口 `https://talent.alibaba.com/off-campus/position-list` 在未登录的普通访问中发生循环重定向；本次未找到可公开核验、允许自动采集的招聘专用条款。 | 公开职位页不可稳定访问，且没有正向采集许可；不跟进接口或规避重定向。 | 0 | 无可验证职位发布日期 |
| 拼多多集团（PDD） | https://careers.pddglobalhr.com/campus/ | `https://careers.pddglobalhr.com/robots.txt` 对普通 GET 返回 HTTP 403，无法读取适用爬取规则。官网公开入口为校园招聘页，包含登录/注册入口。 | 无法确认自动采集许可；不登录、不采集。 | 0 | 无可验证职位发布日期 |

## 说明

1. JSON 文件保留为合法的空数组，避免把来源页、阻断说明或推测数据伪装成可导入职位记录。因而不存在 `source`、`url`、`title`、`company`、JD/requirements、`posted_at` 或 `crawled_at` 字段缺失的职位对象。
2. 对 robots.txt 的 HTTP 403 仅记录为“无法核验”，并不将其误报为某条明确的 robots 规则；但它不足以构成自动化采集许可。
3. 腾讯的阻断依据为官方明示条款，而非技术限制。其他三个来源的阻断均未绕过访问控制。后续如取得网站方书面授权或提供允许机器读取的公开 API/数据导出，可在授权范围内重新采集。
