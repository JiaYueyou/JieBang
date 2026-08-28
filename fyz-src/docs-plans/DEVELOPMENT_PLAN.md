# 基础框架开发方案

> 历史基线文档：仅记录早期项目骨架，不代表当前接口、目录或完成状态。请以根
> `README.md`、`docs/api-reference.md` 与后端运行说明为准。
> 2026-08-12 复核：继续保持只读历史归档，不再回填文末“待开发”清单。

> **项目**: IT 岗位人才洞察与决策辅助平台
> **技术栈**: 前端 Vue 3 + TypeScript + Vite | 后端 FastAPI (Python 3.10+) | 数据库 MySQL 8.0
> **阶段**: 基础框架搭建（登录 + 首页 + 模块页面骨架 + 路由跳转）

---

## 一、开发目标

搭建可运行的前后端分离基础框架，实现：
1. **登录页面** — 用户认证（JWT），登录后跳转首页
2. **首页仪表盘** — 顶部导航 + 侧边栏 + 统计卡片（占位数据）
3. **模块页面跳转** — 8 个功能模块页面，可正常路由切换，各页面显示标题和占位提示文字
4. **前后端通信** — axios 封装 + FastAPI CORS + 统一响应格式

---

## 二、项目目录结构

```
fyz-src/
├── backend/                          # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # 应用入口 + CORS + 路由注册
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py          # 登录/注册
│   │   │       ├── jobs.py          # 岗位（占位）
│   │   │       ├── changes.py       # 能力更新（占位）
│   │   │       ├── graph.py         # 图谱（占位）
│   │   │       ├── matching.py      # 匹配诊断（占位）
│   │   │       ├── analysis.py      # 趋势分析（当时占位，现已实现）
│   │   │       └── admin.py         # 管理（占位）
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # 环境变量配置
│   │   │   ├── security.py          # JWT 认证工具
│   │   │   └── database.py          # MySQL 连接 + Session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── user.py              # User 模型
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── auth.py              # 登录请求/响应 Schema
│   │       └── common.py            # 统一响应 Schema
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── main.ts                  # 入口
│   │   ├── App.vue                  # 根组件
│   │   ├── api/
│   │   │   ├── request.ts           # axios 封装（拦截器 + Token）
│   │   │   └── auth.ts              # 登录 API
│   │   ├── router/
│   │   │   └── index.ts             # 路由配置（含守卫）
│   │   ├── stores/
│   │   │   └── user.ts              # Pinia 用户状态
│   │   ├── views/
│   │   │   ├── Login.vue            # 登录页
│   │   │   ├── Dashboard.vue        # 首页仪表盘
│   │   │   ├── Discover.vue         # 新岗位发现（占位）
│   │   │   ├── Changes.vue          # 能力动态更新（占位）
│   │   │   ├── GraphView.vue        # 技能图谱（占位）
│   │   │   ├── Trends.vue           # 趋势分析（占位）
│   │   │   ├── Matching.vue         # 匹配诊断（占位）
│   │   │   ├── Learning.vue         # 学习路径（占位）
│   │   │   └── Admin.vue            # 系统管理（占位）
│   │   ├── components/
│   │   │   └── layout/
│   │   │       ├── AppLayout.vue    # 主布局（顶栏 + 侧栏 + 内容区）
│   │   │       ├── Navbar.vue       # 顶部导航栏
│   │   │       └── Sidebar.vue      # 侧边栏菜单
│   │   └── assets/
│   │       └── styles/
│   │           └── global.css       # 全局样式
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
└── DEVELOPMENT_PLAN.md              # 本文件
```

---

## 三、后端设计

### 3.1 FastAPI 入口 (`main.py`)

```
路由注册:
  /api/v1/auth/login      POST  → auth.router
  /api/v1/jobs/*          CRUD  → jobs.router
  /api/v1/changes/*       CRUD  → changes.router
  /api/v1/graph/*         CRUD  → graph.router
  /api/v1/matching/*      CRUD  → matching.router
  /api/v1/analysis/*      CRUD  → analysis.router
  /api/v1/admin/*         CRUD  → admin.router

CORS: 允许 origin http://localhost:5173
```

### 3.2 核心模块

| 文件 | 职责 |
|------|------|
| `core/config.py` | 读取 .env：DB_HOST, DB_PORT, DB_USER, DB_PWD, DB_NAME, JWT_SECRET, JWT_EXPIRE_MINUTES |
| `core/security.py` | `create_access_token()` / `verify_token()` / `get_current_user()` |
| `core/database.py` | SQLAlchemy async engine + `get_db()` dependency |
| `models/user.py` | User: id, username, password_hash, role, created_at |
| `schemas/auth.py` | LoginRequest(username, password), TokenResponse(access_token, token_type) |
| `schemas/common.py` | ApiResponse(code, message, data) |

### 3.3 认证接口 (`api/v1/auth.py`)

```python
POST /api/v1/auth/login
  Body:   {"username": "admin", "password": "admin123"}
  Return: {"code": 200, "message": "success", "data": {"access_token": "eyJ...", "token_type": "bearer"}}

POST /api/v1/auth/register  (简化，注册普通用户)
```

### 3.4 占位模块接口

每个模块路由文件提供一个 `GET /` 端点返回占位信息：

```python
# 示例: api/v1/jobs.py
@router.get("/")
async def jobs_home():
    return ApiResponse(data={"message": "岗位发现模块 — 开发中"})
```

### 3.5 依赖

```
fastapi>=0.110
uvicorn[standard]>=0.27
sqlalchemy>=2.0
aiomysql>=0.2
python-jose[cryptography]>=3.3
passlib[bcrypt]>=1.7
python-dotenv>=1.0
pydantic>=2.0
python-multipart>=0.0.9
```

---

## 四、前端设计

### 4.1 路由表

| 路径 | 页面 | 组件 | 需登录 |
|------|------|------|--------|
| `/login` | 登录页 | `Login.vue` | 否 |
| `/` | 首页仪表盘 | `Dashboard.vue` | 是 |
| `/discover` | 新岗位发现 | `Discover.vue` | 是 |
| `/changes` | 能力动态更新 | `Changes.vue` | 是 |
| `/graph` | 技能图谱 | `GraphView.vue` | 是 |
| `/trends` | 趋势分析 | `Trends.vue` | 是 |
| `/matching` | 匹配诊断 | `Matching.vue` | 是 |
| `/learning` | 学习路径 | `Learning.vue` | 是 |
| `/admin` | 系统管理 | `Admin.vue` | 是 |

### 4.2 路由守卫

```typescript
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  if (to.path !== '/login' && !userStore.token) {
    next('/login')
  } else if (to.path === '/login' && userStore.token) {
    next('/')
  } else {
    next()
  }
})
```

### 4.3 布局结构 (AppLayout.vue)

```
┌─────────────────────────────────────────────┐
│  Navbar: Logo | 首页 | 用户头像 | 退出        │
├──────────┬──────────────────────────────────┤
│ Sidebar  │  <router-view />                 │
│ ──────── │  各模块页面内容                   │
│ 仪表盘    │                                  │
│ 新岗位发现 │                                  │
│ 能力更新   │                                  │
│ 技能图谱   │                                  │
│ 趋势分析   │                                  │
│ 匹配诊断   │                                  │
│ 学习路径   │                                  │
│ 系统管理   │                                  │
└──────────┴──────────────────────────────────┘
```

### 4.4 登录页 (Login.vue)

- 居中卡片式登录表单
- 输入：用户名 + 密码
- 登录按钮 → 调用 `/api/v1/auth/login` → 存储 token → 跳转首页
- 错误提示：用户名或密码错误

### 4.5 首页仪表盘 (Dashboard.vue)

- 4 张统计卡片（岗位总数、技能总数、本周新增、待处理匹配）
- 卡片数据暂用占位数字
- 欢迎标题 + 项目简介

### 4.6 占位页面模板

每个模块页面（Discover/Changes/GraphView/Trends/Matching/Learning/Admin）：
```vue
<template>
  <div class="page-container">
    <h1>{{ pageTitle }}</h1>
    <el-card>
      <p>{{ placeholder }}</p>
    </el-card>
  </div>
</template>
```

### 4.7 依赖

```json
{
  "vue": "^3.4",
  "vue-router": "^4.3",
  "pinia": "^2.1",
  "axios": "^1.7",
  "element-plus": "^2.7",
  "@element-plus/icons-vue": "^2.3",
  "typescript": "^5.4",
  "vite": "^5.2",
  "vue-tsc": "^2.0"
}
```

---

## 五、数据库

### 5.1 MySQL 初始化

```sql
CREATE DATABASE IF NOT EXISTS jie_bang DEFAULT CHARSET utf8mb4;

CREATE TABLE IF NOT EXISTS user (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 初始管理员账号: admin / admin123（密码由后端 bcrypt 加密写入）
INSERT INTO user (username, password_hash, role) VALUES ('admin', '<bcrypt_hash>', 'admin');
```

### 5.2 连接配置 (`.env`)

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=jie_bang
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=120
```

---

## 六、统一响应格式

所有后端 API 遵循 `dev-spec.md` 规范：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

| code | 含义 |
|------|------|
| 200 | 成功 |
| 40001 | 用户名或密码错误 |
| 40100 | 未认证（Token 无效/过期） |
| 50000 | 服务器内部错误 |

前端 axios 拦截器：
- 请求拦截：自动附加 `Authorization: Bearer <token>`
- 响应拦截：`code !== 200` 时 toast 提示错误；`401` 时跳转登录页

---

## 七、开发步骤

### Step 1：后端基础（优先）
1. 创建目录结构，初始化 `requirements.txt`
2. 编写 `core/config.py` + `core/database.py`
3. 编写 `models/user.py` + `core/security.py`
4. 编写 `schemas/auth.py` + `schemas/common.py`
5. 编写 `api/v1/auth.py`（登录 + 注册）
6. 编写 6 个占位路由文件（jobs/changes/graph/matching/analysis/admin）
7. 编写 `main.py`：创建表 + 注册路由 + CORS + 种子管理员账号
8. 启动验证：`uvicorn app.main:app --reload`

### Step 2：前端基础
1. 初始化 Vite + Vue 3 + TS 项目
2. 安装依赖：vue-router, pinia, axios, element-plus
3. 创建 `api/request.ts`（axios 封装）
4. 创建 `router/index.ts`（路由表 + 守卫）
5. 创建 `stores/user.ts`（Pinia 状态）
6. 编写 `Login.vue`
7. 编写布局组件：`AppLayout.vue` + `Navbar.vue` + `Sidebar.vue`
8. 编写 `Dashboard.vue`（首页）
9. 编写 7 个占位页面
10. 编写 `App.vue` + `main.ts`
11. `vite.config.ts` 配置代理

### Step 3：联调验证
1. 启动后端（端口 8000）
2. 启动前端（端口 5173），代理到后端
3. 验证：访问 `/login` → 登录 → 跳转首页 → 侧边栏切换各模块页面
4. 验证：未登录直接访问 `/` 自动跳转 `/login`
5. 验证：Token 过期处理

---

## 八、启动命令

```bash
# 后端
cd fyz-src/backend
conda activate jiebang
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端
cd fyz-src/frontend
npm install
npm run dev
```

---

> **版本**: v1.0
> **创建日期**: 2026-06-14
> **状态**: 待开发
