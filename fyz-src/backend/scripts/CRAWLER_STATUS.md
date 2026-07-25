# 爬虫功能实现状态

## 一、已完成

### 1. 爬虫脚本层

| 文件 | 状态 | 说明 |
|------|------|------|
| `scripts/spider_framework/base_spider.py` | 已完成 | 爬虫基类：配置加载、请求管理、数据校验、JSON 输出、自动编号、去重保存 |
| `scripts/spiders/zhaopin_spider.py` | 已完成 | 智联招聘爬虫：Playwright 浏览器自动化，拦截 `/c/i/search/positions` API，最多 5 页 |
| `scripts/spiders/iflytek_spider.py` | 已完成 | 科大讯飞爬虫：requests POST 请求讯飞招聘 API，最多 5 页 |
| `scripts/configs/zhaopin.yaml` | 已完成 | 智联爬虫配置：URL、关键词、页数、时间范围、请求间隔 |
| `scripts/configs/iflytek.yaml` | 已完成 | 讯飞爬虫配置：URL、关键词、页数、请求间隔 |

### 2. 后端服务层

| 文件 | 状态 | 说明 |
|------|------|------|
| `app/services/crawler_service.py` | 已完成 | 爬虫服务：子进程启动/监控、后台线程读取 stderr 提取进度、状态轮询、数据总览构造、启停状态跟踪 |
| `app/schemas/crawler.py` | 已完成 | Pydantic 模型：`SpiderInfo`、`AdminOverview`、`CrawlerPolicy`、`CrawlerRunResult` |
| `app/api/v1/admin.py` | 已完成 | 6 个 API 端点：总览、启停、执行、状态、轮询、用户管理、系统设置 |
| `app/main.py` | 已完成 | admin_router 从占位路由替换为真实路由 |

### 3. 前端 UI 层

| 文件 | 状态 | 说明 |
|------|------|------|
| `Admin.vue` | 已完成 | 采集中心 UI：数据源卡片、启停开关、立即执行、进度条、全局策略弹窗、数据质量面板、日志面板 |
| `stores/admin.ts` | 已完成 | Pinia store：`toggleCrawler`、`runCrawler`、`pollCrawler` |
| `data/httpProvider.ts` | 已完成 | HTTP 数据提供者：对接后端 admin API |
| `data/provider.ts` | 已完成 | DataProvider 接口声明：包含 `pollCrawler` |
| `data/index.ts` | 已完成 | hybrid 模式支持：admin 模块走 HTTP，其他模块走 mock |

### 4. 数据输出

| 功能 | 状态 | 说明 |
|------|------|------|
| JSON 文件输出 | 已完成 | 爬虫数据保存到 `data/` 目录，自动编号（`zhaopin_1.json`、`iflytek_1.json`） |
| 重复数据跳过 | 已完成 | 条数相同时跳过保存，避免产生重复文件 |
| 进度实时显示 | 已完成 | 后台线程读取子进程 stderr，匹配"正在采集第 X/Y 页"，前端每 2 秒轮询刷新 |

---

## 二、未实现 / 待完善

### 1. 数据入库（重要）

| 项目 | 说明 |
|------|------|
| 爬虫数据未写入 MySQL | 爬虫输出只保存在 `data/*.json`，不会自动进入数据库 |
| 新文件不在导入白名单 | `import_service.py` 的 `ALLOWED_FILES` 只有 6 个旧文件，新爬的 `zhaopin_1.json`、`iflytek_1.json` 无法通过 API 导入 |
| 缺少自动入库脚本 | 需要写一个脚本或后端接口，将爬虫 JSON 导入 `job_postings` 表 |

### 2. 定时调度

| 项目 | 说明 |
|------|------|
| 无定时任务 | 目前只能手动点击"立即执行"，没有 APScheduler 或 Celery Beat 定时调度 |
| 无采集频率配置 | 全局策略中的"采集频率"字段（每日/每周/每月）目前只是 UI 展示，无实际逻辑 |

### 3. 用户管理 & 系统设置

| 项目 | 说明 |
|------|------|
| 用户启停 | `toggleUser` 是桩实现，未接入数据库 |
| 系统设置保存 | `saveSettings` 是桩实现，未持久化 |

### 4. 日志管理

| 项目 | 说明 |
|------|------|
| 日志面板 | UI 已做好，但日志数据来自 mock，未对接后端真实日志 |
| 运行日志存储 | 爬虫执行日志（stdout/stderr）只在内存中缓存，未持久化到文件或数据库 |

### 5. 数据质量面板

| 项目 | 说明 |
|------|------|
| 质量分析 | 面板展示的数据来自后端 `CrawlerService` 的统计，但字段完整度分析逻辑较简单 |

### 6. 爬虫扩展

| 项目 | 说明 |
|------|------|
| 新数据源接入 | 需要在 `REGISTERED_SPIDERS` 注册 + 编写新爬虫脚本 + 前端卡片配置 |
| 增量采集 | 目前每次全量采集，没有基于上次采集时间的增量逻辑 |

---

## 三、文件清单

```
后端：
  app/services/crawler_service.py      # 爬虫服务（已完成）
  app/schemas/crawler.py               # Schema 定义（已完成）
  app/api/v1/admin.py                  # API 路由（已完成）
  app/main.py                          # 路由注册（已修改）
  scripts/import_data.py               # 数据导入脚本（已完成，仅导入旧文件）

前端：
  views/Admin.vue                      # 系统管理页面（已完成）
  stores/admin.ts                      # Pinia store（已完成）
  data/httpProvider.ts                 # HTTP 数据提供者（已完成）
  data/provider.ts                     # 接口声明（已完成）
  data/index.ts                        # hybrid 模式（已完成）

爬虫脚本：
  scripts/spider_framework/base_spider.py  # 爬虫基类（已完成）
  scripts/spiders/zhaopin_spider.py        # 智联爬虫（已完成）
  scripts/spiders/iflytek_spider.py        # 讯飞爬虫（已完成）
  scripts/configs/zhaopin.yaml             # 智联配置（已完成）
  scripts/configs/iflytek.yaml             # 讯飞配置（已完成）

数据输出：
  data/zhaopin_1.json                  # 智联采集结果
  data/iflytek_1.json                  # 讯飞采集结果
```
