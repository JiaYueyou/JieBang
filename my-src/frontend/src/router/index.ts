import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "Login",
      component: () => import("@/views/Login.vue"),
      meta: { title: "登录", noAuth: true },
    },
    {
      path: "/register",
      name: "Register",
      component: () => import("@/views/Register.vue"),
      meta: { title: "注册", noAuth: true },
    },
    {
      path: "/",
      component: () => import("@/components/layout/AppLayout.vue"),
      redirect: "/dashboard",
      children: [
        {
          path: "dashboard",
          name: "Dashboard",
          component: () => import("@/views/Dashboard.vue"),
          meta: { title: "首页仪表盘", icon: "Odometer" },
        },
        {
          path: "discover",
          name: "Discover",
          component: () => import("@/views/Discover.vue"),
          meta: { title: "新岗位发现", icon: "Aim" },
        },
        {
          path: "changes",
          name: "Changes",
          component: () => import("@/views/Changes.vue"),
          meta: { title: "能力动态更新", icon: "Refresh" },
        },
        {
          path: "graph",
          name: "GraphView",
          component: () => import("@/views/GraphView.vue"),
          meta: { title: "技能图谱", icon: "Share" },
        },
        {
          path: "trends",
          name: "Trends",
          component: () => import("@/views/Trends.vue"),
          meta: { title: "趋势分析", icon: "TrendCharts" },
        },
        {
          path: "matching",
          name: "Matching",
          component: () => import("@/views/Matching.vue"),
          meta: { title: "匹配诊断", icon: "Connection" },
        },
        {
          path: "learning",
          name: "Learning",
          component: () => import("@/views/Learning.vue"),
          meta: { title: "学习路径", icon: "Guide" },
        },
        {
          path: "admin",
          name: "Admin",
          component: () => import("@/views/Admin.vue"),
          meta: { title: "系统管理", icon: "Setting" },
        },
      ],
    },
  ],
});

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || ""} - IT 岗位人才洞察平台`;
  const token = localStorage.getItem("token");
  if (!to.meta.noAuth && !token) {
    next("/login");
  } else if ((to.path === "/login" || to.path === "/register") && token) {
    next("/dashboard");
  } else {
    next();
  }
});

export default router;
