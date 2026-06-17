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
            智联职引 <span class="sep">/</span> <span class="current">{{ pageTitle }}</span>
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
const pageTitle = computed(() => (route.meta.title as string) || "");
const currentTime = ref("");

let timer: number;
function updateTime() {
  currentTime.value = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}
onMounted(() => { updateTime(); timer = window.setInterval(updateTime, 30000); });
onUnmounted(() => clearInterval(timer));

const menuItems = [
  { path: "/dashboard", title: "首页仪表盘", icon: "Odometer" },
  { path: "/discover",  title: "新岗位发现", icon: "Aim" },
  { path: "/changes",   title: "能力动态更新", icon: "Refresh" },
  { path: "/graph",     title: "技能图谱", icon: "Share" },
  { path: "/trends",    title: "趋势分析", icon: "TrendCharts" },
  { path: "/matching",  title: "匹配诊断", icon: "Connection" },
  { path: "/learning",  title: "学习路径", icon: "Guide" },
  { path: "/admin",     title: "系统管理", icon: "Setting" },
];

function handleLogout() {
  userStore.logout();
  router.push("/login");
}
</script>
