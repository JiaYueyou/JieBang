# 数据源组 C 公开官网招聘采集报告

- 采集时间：2026-08-09T00:20:02+08:00
- 目标时间范围：2026-01-01 至采集时
- 可导入记录数：1182
- 已验证职位发布日期覆盖：2026-06-12 至 2026-08-07

## 合规与来源核验

| 公司 | 官方入口 | robots.txt | 条款 / 访问判断 | 结果 |
| --- | --- | --- | --- | --- |
| 幻方量化 | https://www.high-flyer.cn/join （该页官方链接到 Moka 职位页） | `https://www.high-flyer.cn/robots.txt`：`User-agent: *`、空 `Disallow`；Moka 的 `https://app.mokahr.com/robots.txt` 未禁止 high-flyer 租户 | 官网和公开职位页均无需登录或验证码。官网 /join 未发现公开使用条款链接；公开职位列表不展示单岗发布日期，无法证明其在指定时间窗内，未导入。 | 0 条（日期字段缺失） |
| 月之暗面（Moonshot AI） | https://careers.kimi.com/（页面 title/description 自称 Moonshot AI / 月之暗面官方招聘平台） | `https://careers.kimi.com/robots.txt`：`Allow: /`；`https://www.moonshot.cn/robots.txt` 返回 nginx 默认页，无法作为有效 robots 规则解释 | careers.kimi.com 页面和社会招聘展示无需登录或验证码；站点 sitemap 未列出 Terms/Privacy 页面。公开岗位展示与其链接的 Moka 列表均未展示单岗发布日期，无法验证时间范围，未导入。 | 0 条（日期字段缺失） |
| 长鑫存储 | https://www.cxmt.com/join.html → https://cxmt.zhiye.com/social/jobs | `https://www.cxmt.com/robots.txt`：`Allow: /`。官方招聘门户为公开只读访问。 | 官网使用条款：https://www.cxmt.com/terms_of_use.html；未发现禁止读取公开职位信息的条款。未登录、未处理验证码、未提交表单。仅使用招聘页在浏览器中公开请求的职位列表接口，且接口直接返回 JD、要求和发布日期。 | 1182 条 |

## 数据限制

- 仅导入了发布日期在 2026-01-01（含）之后、且门户明确公开的长鑫存储职位；保留的门户分类为研发技术、量产技术、生产运营、信息技术、电路设计，均属半导体/软硬件技术岗位。
- 幻方量化与月之暗面均有官方/官方标注的公开入口，但未公开每条岗位的发布日期；为避免把“当前仍展示”误当成“在本任务时间窗内发布”，保留入口与阻断原因而不伪造 `posted_at`。
- 没有绕过 robots 指令、登录、验证码、加密响应或其他访问控制。
