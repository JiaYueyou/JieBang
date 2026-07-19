<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

interface MenuItem {
  key: string
  label: string
  icon: string
  path: string
}

const menuItems: MenuItem[] = [
  { key: 'home', label: '首页', icon: 'HomeFilled', path: '/home' },
  { key: 'positions', label: '岗位探索', icon: 'Compass', path: '/positions' },
  { key: 'graph', label: '知识图谱', icon: 'Share', path: '/graph' },
  { key: 'favorites', label: '我的收藏', icon: 'Star', path: '/favorites' },
  { key: 'diagnosis', label: '简历诊断', icon: 'Document', path: '/diagnosis' },
  { key: 'learning', label: '学习路径', icon: 'Guide', path: '/learning' },
  { key: 'career', label: '职业发展', icon: 'TrendCharts', path: '/career' },
]

const activeKey = computed(() => {
  const name = route.name as string
  if (['Home'].includes(name)) return 'home'
  if (['Positions', 'PositionDetail'].includes(name)) return 'positions'
  if (['Graph'].includes(name)) return 'graph'
  if (['Favorites'].includes(name)) return 'favorites'
  if (['DiagnosisIndex', 'DiagnosisDetail'].includes(name)) return 'diagnosis'
  if (['Career'].includes(name)) return 'career'
  if (['Learning'].includes(name)) return 'learning'
  if (['Career'].includes(name)) return 'career'
  return 'home'
})

const navigate = (item: MenuItem) => {
  router.push(item.path)
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-logo" @click="router.push('/home')">
      <div class="logo-icon">
        <el-icon :size="24"><Connection /></el-icon>
      </div>
      <span class="logo-text">智联职引</span>
    </div>

    <nav class="sidebar-nav">
      <div
        v-for="item in menuItems"
        :key="item.key"
        class="nav-item"
        :class="{ active: activeKey === item.key }"
        @click="navigate(item)"
      >
        <el-icon :size="20"><component :is="item.icon" /></el-icon>
        <span class="nav-label">{{ item.label }}</span>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="user-card" @click="router.push('/profile')">
        <el-avatar :size="36" icon="UserFilled" />
        <div class="user-info">
          <span class="user-name">求职者</span>
          <span class="user-meta">个人中心</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 220px;
  background: #fff;
  border-right: 1px solid var(--hairline);
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px 24px;
  cursor: pointer;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: var(--brand);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
}

.sidebar-nav {
  flex: 1;
  padding: 0 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 4px;
  border-radius: var(--radius);
  color: var(--ink);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s ease;
}

.nav-item:hover {
  background: var(--brand-light);
  color: var(--brand);
}

.nav-item.active {
  background: var(--brand-light);
  color: var(--brand);
  font-weight: 600;
}

.nav-label {
  white-space: nowrap;
}

.sidebar-footer {
  padding: 16px 12px;
  border-top: 1px solid var(--hairline);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background 0.15s ease;
}

.user-card:hover {
  background: var(--canvas);
}

.user-info {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.user-meta {
  font-size: 12px;
  color: var(--muted);
}
</style>
