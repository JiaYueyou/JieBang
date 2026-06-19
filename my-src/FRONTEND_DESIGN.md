# 智联职引 — 前端设计方案

> 基于 Element Plus + ECharts + AntV G6 的 HR 管理后台
> 设计体系: Refined Technica (轻量浅色主题)

---

## 一、组件框架

| 层级 | 选型 | 用途 |
|------|------|------|
| **主 UI** | Element Plus 2.7+ | 100% 业务组件 |
| **图表** | ECharts 5 + vue-echarts | 雷达/热力/折线/仪表/饼图/地图 |
| **图谱** | AntV G6 (按需引入) | 技能图谱模块 |
| **图标** | @element-plus/icons-vue | 菜单/按钮/标签图标 |

---

## 二、配色体系

```
品牌:   --color-brand:       #4f6ef6    主操作/链接/选中
成功:   --color-success:     #34b37e    匹配通过/已具备
警告:   --color-warning:     #f59e4b    待处理/需关注
危险:   --color-danger:      #e85d5d    未通过/缺失
信息:   --color-info:        #5b9df5    辅助提示

背景:   bg-base:    #f8f9fb   页面底
        bg-elevated:#ffffff   卡片/侧栏
        bg-muted:   #f2f4f7   输入框/tag/hover

文本:   text-primary:  #1a1d28   标题/正文
        text-secondary:#5a5f6e   副文本
        text-muted:    #989eae   辅助/禁用
```

**图表配色** (ECharts palette):
```
['#4f6ef6','#34b37e','#f59e4b','#7c6ff7','#5b9df5','#e85d5d']
```

**图谱配色** (G6 五层森林，同尺寸节点，蓝色深浅):
```
L1 Job:              #1a3a8a
L2 SkillArea:        #3d5bd9
L3 TechStack:        #4f6ef6
L4 TechPoint:        #8fa8f4
L5 KnowledgePoint:   #c8d6fb
```

---

## 三、字体层级

| 用途 | 大小 | 字重 | 字体 |
|------|------|------|------|
| 页面标题 | 22px | 700 | Plus Jakarta Sans |
| 卡片标题 | 15px | 600 | Plus Jakarta Sans |
| 正文/副文本 | 15px / 14px | 400 | Plus Jakarta Sans |
| 导航项 | 14px | 500 | Plus Jakarta Sans |
| 标签/徽章 | 13px | 500 | Plus Jakarta Sans |
| 统计数字 | 26px | 700 | Plus Jakarta Sans |
| 辅助信息 | 12px | 400 | Plus Jakarta Sans |
| 登录大标题 | 22px | 700 | Plus Jakarta Sans |
| 登录提示 | 13px | 400 | Plus Jakarta Sans |
| **时间/代码** | 13px | 400 | **JetBrains Mono** ← 保留 |

字体加载:
```css
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
```

---

## 四、字号调整方案

基准从 14px 上调至 15px，小号设 13px 底线。

| 元素 (CSS 选择器) | 当前 | 调整后 |
|---|---|---|
| `body` | 14px | **15px** |
| `.page-header p` | 13.5px | **14px** |
| `.stat-label` | 12.5px | **13px** |
| `.stat-change` | 11.5px | **13px** |
| `.nav-item` | 13.5px | **14px** |
| `.login-card .hint` | 12px | **13px** |
| `.dash-card-badge` | 11px | **12px** |
| `.flow-step-body h4` | 14px | **15px** |
| `.flow-step-body p` | 12.5px | **13px** |
| `.quick-entry` | 13.5px | **14px** |
| `.tag` | 12px | **13px** |
| `.sidebar-user-role` | 11px | **12px** |
| `.topbar-time` | 13px | **保留不变** |
| `.hint code` | 11px | **保留不变** |

---

## 五、动效与交互 (保持不变)

| 效果 | 实现 |
|------|------|
| 卡片 hover | `translateY(-1px)` + `box-shadow: var(--shadow-md)` |
| 按钮 hover | `box-shadow: 0 4px 14px rgba(79,110,246,.3)` |
| 输入聚焦 | `border-color: var(--color-brand)` + `box-shadow: 0 0 0 3px var(--color-brand-light)` |
| 导航选中 | 左侧蓝色竖线 + 背景 `var(--color-brand-light)` + 蓝色文字 |
| 页面入场 | `.anim-fade-up`, `.anim-fade-in`, `.anim-scale-in` + `.anim-delay-{1..4}` |

---

## 六、布局参数

```
侧边栏:     220px 固定
顶栏:       60px
内容区内距: 28px
内容区最大宽: 1400px
圆角:       sm=6px / md=10px / lg=14px / xl=20px
阴影密度:   xs → sm → md → lg → xl (五级递进)
```

响应式断点:
```
≥1200px:  正常布局
768-1200: 统计卡片 2 列，仪表盘 1 列
<768px:   隐藏侧栏，内边距缩小
```

---

## 七、页面级设计

### 7.1 登录/注册页

- 全屏居中布局，径向渐变背景装饰
- 白色卡片 `420px` 宽，`border-radius: 20px`
- 品牌色渐变 Logo 图标 + 项目名称 + 副标题
- Element Plus 表单组件（圆角输入框 + 全宽按钮）
- 底部提示文字：演示账号 + 注册链接

### 7.2 主布局

```
┌──────────────────────────────────────────┐
│ 侧栏 220px        │ 顶栏 60px            │
│ ┌──────────────┐  │ 面包屑 / 时间 / 退出  │
│ │ Logo + 品牌   │  ├─────────────────────│
│ ├──────────────┤  │                     │
│ │ 导航菜单      │  │  内容区             │
│ │ · 选中态蓝背景 │  │  padding: 28px     │
│ │ · 左侧指示条   │  │  max-width: 1400px │
│ │ · 图标+文字   │  │                     │
│ │              │  │                     │
│ ├──────────────┤  │                     │
│ │ 用户信息      │  │                     │
│ └──────────────┘  │                     │
└──────────────────────────────────────────┘
```

### 7.3 仪表盘 (旧版，待重造为工作台)

当前为占位版，后续按 FULLSTACK_PLAN.md 改造为工作台:
- 高匹配人才提醒卡片
- IT 热门岗位 Top10
- 团队招聘进度条
- 快速操作入口

### 7.4 占位页面 (7 个)

模块页面居中展示: 圆角图标(80px) + 标题 + 功能描述 + 标签列表。
不同模块用不同图标颜色区分: blue / green / amber / indigo / rose / cyan。

---

## 八、Element Plus 样式覆写

| 组件 | 覆写内容 |
|------|----------|
| `el-input__wrapper` | 圆角 md，背景 bg-muted，边框 border，聚焦蓝色光环 |
| `el-button--primary` | 品牌蓝色，hover 发光阴影，圆角 md，字重 600 |
| `el-card` | 圆角 lg，边框 border，去除默认阴影 |
| `el-menu` | 去除右边框 |
| `el-steps` | 连接线颜色改为 border |
| `el-form-item` | margin-bottom: 20px |

---

## 九、实现顺序

1. **global.css** — 应用字号调整 + ECharts/G6 色值变量注入
2. **AppLayout.vue** — 字体大小适配
3. **Login.vue / Register.vue** — 提示文字大小
4. **Dashboard.vue** — 标签/徽章/流程文字大小
5. **全部占位页面** — 标签大小
6. **router/index.ts** — 新增 ECharts + G6 依赖引入
7. **package.json** — 安装 echarts, vue-echarts, @antv/g6
