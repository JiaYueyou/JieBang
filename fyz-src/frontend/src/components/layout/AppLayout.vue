<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <aside class="app-sidebar">
      <div class="sidebar-header">
        <div class="sidebar-logo">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>
        </div>
        <span class="sidebar-brand">智联职引</span>
      </div>

      <nav class="sidebar-nav">
        <router-link v-for="item in menuItems" :key="item.path" :to="item.path" class="nav-item" :class="{ active: currentPath === item.path }">
          <span class="nav-icon"><el-icon><component :is="item.icon" /></el-icon></span>
          {{ item.title }}
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="sidebar-avatar">{{ userStore.username?.charAt(0)?.toUpperCase() }}</div>
        <div class="sidebar-user-info">
          <div class="sidebar-user-name">{{ userStore.username }}</div>
          <div class="sidebar-user-role">管理员</div>
        </div>
      </div>
    </aside>

    <!-- Main -->
    <div class="app-main">
      <header class="app-topbar">
        <div class="topbar-left">
          <div class="topbar-breadcrumb">
            <span>智联职引</span>
            <template v-for="(crumb, i) in breadcrumbs" :key="i">
              <span class="sep">/</span>
              <router-link
                v-if="i < breadcrumbs.length - 1 && crumb.path"
                :to="crumb.path"
                class="crumb-link"
              >{{ crumb.title }}</router-link>
              <span v-else :class="{ current: i === breadcrumbs.length - 1 }">{{ crumb.title }}</span>
            </template>
          </div>
        </div>
        <div class="topbar-right">
          <span class="topbar-time">{{ currentTime }}</span>
          <button class="topbar-btn" title="退出登录" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
          </button>
        </div>
      </header>

      <main class="app-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useUserStore } from "@/stores/user";
import { SwitchButton } from "@element-plus/icons-vue";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

userStore.restore();

const currentPath = computed(() => route.path);
const breadcrumbs = computed(() => {
  const crumbs: { title: string; path: string }[] = [];
  // 如果当前路由 meta 有 parentTitle，先加父级
  const pTitle = route.meta.parentTitle as string | undefined;
  const pPath = route.meta.parentPath as string | undefined;
  if (pTitle) crumbs.push({ title: pTitle, path: pPath || "" });
  // 当前页面标题
  const t = route.meta.title as string | undefined;
  if (t) crumbs.push({ title: t, path: route.path });
  return crumbs;
});
const currentTime = ref("");

let timer: number;
function updateTime() {
  currentTime.value = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}
onMounted(() => { updateTime(); timer = window.setInterval(updateTime, 30000); });
onUnmounted(() => clearInterval(timer));

const menuItems = [
  { path: "/dashboard", title: "工作台",   icon: "Odometer" },
  { path: "/jobs",      title: "岗位管理", icon: "Briefcase" },
  { path: "/matching",  title: "人才匹配", icon: "Connection" },
  { path: "/career",    title: "转岗指南", icon: "Guide" },
  { path: "/graph",     title: "技能图谱", icon: "Share" },
  { path: "/trends",    title: "趋势分析", icon: "TrendCharts" },
  { path: "/favorites", title: "我的收藏", icon: "Star" },
  { path: "/history",   title: "浏览足迹", icon: "Clock" },
  { path: "/admin",     title: "系统管理", icon: "Setting" },
];

function handleLogout() {
  userStore.logout();
  router.push("/login");
}
</script>
