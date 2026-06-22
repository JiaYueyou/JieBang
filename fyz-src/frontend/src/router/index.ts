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
          meta: { title: "工作台" },
        },
        {
          path: "jobs",
          name: "JobManagement",
          component: () => import("@/views/JobManagement.vue"),
          meta: { title: "岗位管理" },
        },
        {
          path: "matching",
          name: "Matching",
          component: () => import("@/views/Matching.vue"),
          meta: { title: "人才匹配" },
        },
        {
          path: "matching/:resumeId",
          name: "MatchingDetail",
          component: () => import("@/views/MatchingDetail.vue"),
          meta: { title: "人才详情", parentTitle: "人才匹配", parentPath: "/matching" },
        },
        {
          path: "career",
          name: "CareerGuide",
          component: () => import("@/views/CareerGuide.vue"),
          meta: { title: "转岗指南" },
        },
        {
          path: "graph",
          name: "GraphView",
          component: () => import("@/views/GraphView.vue"),
          meta: { title: "技能图谱" },
        },
        {
          path: "trends",
          name: "Trends",
          component: () => import("@/views/Trends.vue"),
          meta: { title: "趋势分析" },
        },
        {
          path: "favorites",
          name: "Favorites",
          component: () => import("@/views/Favorites.vue"),
          meta: { title: "我的收藏" },
        },
        {
          path: "history",
          name: "History",
          component: () => import("@/views/History.vue"),
          meta: { title: "浏览足迹" },
        },
        {
          path: "admin",
          name: "Admin",
          component: () => import("@/views/Admin.vue"),
          meta: { title: "系统管理" },
        },
      ],
    },
  ],
});

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || ""} - 智联职引`;
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
