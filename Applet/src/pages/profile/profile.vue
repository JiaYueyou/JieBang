<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiAdminCenter } from '@/api/admin'
import type { ReviewStat, ImportSource, SystemRow, AuditLog, AdminUser } from '@/mock/data'
import { useUserStore } from '@/stores/user'
import AppTabBar from '@/components/AppTabBar.vue'

const statusBarHeight = uni.getWindowInfo().statusBarHeight
const userStore = useUserStore()

const loading = ref(true)
const reviewStats = ref<ReviewStat[]>([])
const importSources = ref<ImportSource[]>([])
const systemStatus = ref<SystemRow[]>([])
const auditLogs = ref<AuditLog[]>([])
const users = ref<AdminUser[]>([])

onShow(() => {
  uni.hideTabBar({ animation: false })
  if (userStore.isLoggedIn) refresh()
})

async function refresh() {
  loading.value = true
  try {
    const d = await apiAdminCenter()
    reviewStats.value = d.reviewStats
    importSources.value = d.importSources
    systemStatus.value = d.systemStatus
    auditLogs.value = d.auditLogs
    users.value = d.users
  } catch {
    /* mock */
  } finally {
    loading.value = false
  }
}

function reviewTone(t: string) {
  if (t === 'warning') return 'warning'
  if (t === 'success') return 'success'
  return 'danger'
}

function importTone(s: ImportSource['status']) {
  if (s === '已入库') return 'success'
  if (s === '校验完成') return 'brand'
  return 'warning'
}

function goLogin() {
  uni.navigateTo({ url: '/pages-sub/login/login' })
}

function clearCache() {
  uni.showModal({
    title: '清除缓存',
    content: '将清除本地缓存数据（不影响账号信息），确定继续吗？',
    confirmColor: '#4f6ef6',
    success: (res) => {
      if (res.confirm) {
        uni.clearStorageSync()
        uni.showToast({ title: '已清除', icon: 'success' })
      }
    },
  })
}

function logout() {
  uni.showModal({
    title: '退出登录',
    content: '确定退出当前账号吗？',
    confirmColor: '#e85d5d',
    success: (res) => {
      if (res.confirm) {
        userStore.clear()
        uni.reLaunch({ url: '/pages-sub/login/login' })
      }
    },
  })
}
</script>

<template>
  <view class="admin-page">
    <view class="page-head" :style="{ paddingTop: statusBarHeight + 'px' }">
      <text class="page-title">管理中心</text>
    </view>

    <template v-if="userStore.isLoggedIn && userStore.profile">
      <!-- 管理员卡 -->
      <view class="user-card card fade-up">
        <view class="user-row">
          <view class="user-avatar">{{ userStore.displayName.slice(0, 1) }}</view>
          <view class="user-info">
            <text class="user-name">{{ userStore.displayName }}</text>
            <view class="user-chips">
              <text class="chip brand">{{ userStore.roleLabel }}</text>
              <text v-if="userStore.profile.department" class="chip">{{ userStore.profile.department }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 运行总览 -->
      <view class="section-head fade-up delay-1">
        <text class="section-title">运行总览</text>
        <text class="section-sub">系统与数据管线状态</text>
      </view>
      <view class="card status-card fade-up delay-1">
        <view v-for="s in systemStatus" :key="s.label" class="status-row">
          <view class="status-ok" :class="{ bad: !s.ok }" />
          <text class="status-label">{{ s.label }}</text>
          <text class="status-value">{{ s.value }}</text>
        </view>
      </view>

      <!-- 图谱审核 -->
      <view class="section-head fade-up">
        <text class="section-title">图谱审核</text>
        <text class="section-sub">技能事实入图队列</text>
      </view>
      <view class="review-card card fade-up">
        <view v-for="r in reviewStats" :key="r.label" class="review-item" :class="reviewTone(r.tone)">
          <text class="review-num">{{ r.count }}</text>
          <text class="review-label">{{ r.label }}</text>
        </view>
      </view>

      <!-- 数据导入 -->
      <view class="section-head fade-up">
        <text class="section-title">数据导入</text>
        <text class="section-sub">白名单数据源同步状态</text>
      </view>
      <view class="card fade-up">
        <view v-for="src in importSources" :key="src.id" class="import-row">
          <view class="import-main">
            <text class="import-name">{{ src.name }}</text>
            <text class="import-file">{{ src.file }} · {{ src.records }} 条 · {{ src.time }}</text>
          </view>
          <text class="import-status" :class="importTone(src.status)">{{ src.status }}</text>
        </view>
      </view>

      <!-- 成员 -->
      <view class="section-head fade-up">
        <text class="section-title">成员管理</text>
        <text class="section-sub">{{ users.length }} 个账号</text>
      </view>
      <view class="card fade-up">
        <view v-for="u in users" :key="u.id" class="member-row">
          <view class="member-avatar">{{ u.username.slice(0, 1).toUpperCase() }}</view>
          <view class="member-main">
            <text class="member-name">{{ u.username }}</text>
            <text class="member-role">{{ u.role }} · {{ u.lastActive }}</text>
          </view>
          <view class="member-dot" :class="{ off: !u.active }" />
        </view>
      </view>

      <!-- 审计日志 -->
      <view class="section-head fade-up">
        <text class="section-title">审计日志</text>
        <text class="section-sub">最近操作流水</text>
      </view>
      <view class="card log-card fade-up">
        <view v-for="log in auditLogs" :key="log.id" class="log-item">
          <text class="log-time">{{ log.time }}</text>
          <view class="log-body">
            <text class="log-action">{{ log.user }} · {{ log.action }}</text>
            <text class="log-detail">{{ log.detail }}</text>
          </view>
        </view>
      </view>

      <!-- 设置 -->
      <view class="menu-card card fade-up">
        <view class="menu-item" @tap="clearCache">
          <view class="menu-icon tint-neutral">
            <uni-icons type="refreshempty" size="20" color="#5a5f6e" />
          </view>
          <view class="menu-body">
            <text class="menu-text">清除缓存</text>
          </view>
          <uni-icons type="right" size="14" color="#c4c8d0" />
        </view>
        <view class="menu-item" @tap="logout">
          <view class="menu-icon tint-danger">
            <uni-icons type="undo" size="20" color="#e85d5d" />
          </view>
          <view class="menu-body">
            <text class="menu-text danger">退出登录</text>
          </view>
        </view>
      </view>

      <text class="version">智联职引 · 管理决策端 v2.0.0-demo</text>
    </template>

    <view v-else class="login-guide card fade-up" @tap="goLogin">
      <view class="guide-ring" />
      <text class="guide-title">登录管理中心</text>
      <text class="guide-desc">审核队列 · 数据导入 · 审计日志</text>
      <view class="btn-primary guide-btn">管理员登录</view>
    </view>

    <AppTabBar current="profile" />
  </view>
</template>

<style lang="scss" scoped>
.admin-page {
  min-height: 100vh;
  padding-bottom: calc(180rpx + env(safe-area-inset-bottom));
}

.page-head {
  padding: 24rpx 32rpx 8rpx;
}

.page-title {
  font-size: 40rpx;
  font-weight: 700;
  color: $text-1;
  letter-spacing: -0.02em;
}

/* ── 管理员卡 ── */
.user-card {
  margin: 24rpx 32rpx 0;
  padding: 34rpx 36rpx;
}

.user-row {
  display: flex;
  align-items: center;
  gap: 24rpx;
}

.user-avatar {
  width: 104rpx;
  height: 104rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 42rpx;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, $brand, $violet);
  box-shadow: 0 8rpx 24rpx $brand-glow;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  display: block;
  font-size: 34rpx;
  font-weight: 700;
  color: $text-1;
}

.user-chips {
  display: flex;
  gap: 10rpx;
  margin-top: 12rpx;
}

/* ── 区块 ── */
.section-head {
  margin: 38rpx 40rpx 18rpx;
  display: flex;
  align-items: baseline;
  gap: 16rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: 700;
  color: $text-1;
}

.section-sub {
  font-size: 22rpx;
  color: $text-3;
}

.card {
  margin-left: 32rpx;
  margin-right: 32rpx;
}

/* ── 运行总览 ── */
.status-card {
  padding: 12rpx 32rpx;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 18rpx;
  padding: 24rpx 0;
  border-bottom: 1rpx solid $border-light;

  &:last-child { border-bottom: none; }
}

.status-ok {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
  background: $success;
  box-shadow: 0 0 0 6rpx $success-light;
  flex-shrink: 0;

  &.bad {
    background: $danger;
    box-shadow: 0 0 0 6rpx $danger-light;
  }
}

.status-label {
  font-size: 26rpx;
  font-weight: 600;
  color: $text-1;
}

.status-value {
  margin-left: auto;
  font-size: 23rpx;
  color: $text-3;
  font-family: $font-mono;
}

/* ── 审核队列 ── */
.review-card {
  padding: 34rpx 20rpx;
  display: flex;
}

.review-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;

  &.warning .review-num { color: $warning; }
  &.success .review-num { color: $success; }
  &.danger .review-num { color: $danger; }
}

.review-num {
  font-family: $font-mono;
  font-size: 44rpx;
  font-weight: 700;
  color: $text-1;
}

.review-label {
  font-size: 22rpx;
  color: $text-3;
}

/* ── 导入 ── */
.import-row {
  display: flex;
  align-items: center;
  gap: 18rpx;
  padding: 24rpx 32rpx;
  border-bottom: 1rpx solid $border-light;

  &:last-child { border-bottom: none; }
}

.import-main {
  flex: 1;
  min-width: 0;
}

.import-name {
  display: block;
  font-size: 27rpx;
  font-weight: 600;
  color: $text-1;
}

.import-file {
  display: block;
  margin-top: 4rpx;
  font-size: 21rpx;
  color: $text-3;
  font-family: $font-mono;
}

.import-status {
  padding: 6rpx 18rpx;
  border-radius: $radius-full;
  font-size: 20rpx;
  flex-shrink: 0;

  &.success { background: $success-light; color: $success; }
  &.brand { background: $brand-light; color: $brand; }
  &.warning { background: $warning-light; color: $warning; }
}

/* ── 成员 ── */
.member-row {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 22rpx 32rpx;
  border-bottom: 1rpx solid $border-light;

  &:last-child { border-bottom: none; }
}

.member-avatar {
  width: 68rpx;
  height: 68rpx;
  border-radius: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $brand-light;
  color: $brand;
  font-size: 26rpx;
  font-weight: 700;
  flex-shrink: 0;
}

.member-main {
  flex: 1;
  min-width: 0;
}

.member-name {
  display: block;
  font-size: 27rpx;
  font-weight: 600;
  color: $text-1;
  font-family: $font-mono;
}

.member-role {
  display: block;
  margin-top: 2rpx;
  font-size: 21rpx;
  color: $text-3;
}

.member-dot {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
  background: $success;

  &.off { background: $border; }
}

/* ── 审计日志 ── */
.log-card {
  padding: 10rpx 32rpx;
}

.log-item {
  display: flex;
  gap: 22rpx;
  padding: 24rpx 0;
  border-bottom: 1rpx solid $border-light;

  &:last-child { border-bottom: none; }
}

.log-time {
  font-family: $font-mono;
  font-size: 20rpx;
  color: $text-3;
  padding-top: 4rpx;
  flex-shrink: 0;
}

.log-body {
  flex: 1;
  min-width: 0;
}

.log-action {
  display: block;
  font-size: 25rpx;
  font-weight: 600;
  color: $text-1;
}

.log-detail {
  display: block;
  margin-top: 4rpx;
  font-size: 22rpx;
  color: $text-2;
  line-height: 1.6;
}

/* ── 设置菜单 ── */
.menu-card {
  margin-top: 40rpx;
  padding: 8rpx 0;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 24rpx;
  padding: 26rpx 32rpx;

  &:active { background: $bg-muted; }
}

.menu-icon {
  width: 72rpx;
  height: 72rpx;
  border-radius: 22rpx;
  display: flex;
  align-items: center;
  justify-content: center;

  &.tint-neutral { background: $bg-muted; }
  &.tint-danger { background: $danger-light; }
}

.menu-body {
  flex: 1;
  min-width: 0;
}

.menu-text {
  display: block;
  font-size: 28rpx;
  font-weight: 600;
  color: $text-1;

  &.danger { color: $danger; }
}

.login-guide {
  margin: 60rpx 32rpx 0;
  padding: 72rpx 40rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.guide-ring {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, $brand 0 12rpx, transparent 14rpx),
    conic-gradient(from 0deg, $brand 0 60deg, $brand-light 90deg 360deg);
  mask: radial-gradient(circle, transparent 0 30rpx, #000 31rpx);
  -webkit-mask: radial-gradient(circle, transparent 0 30rpx, #000 31rpx);
}

.guide-title {
  margin-top: 28rpx;
  font-size: 34rpx;
  font-weight: 700;
  color: $text-1;
}

.guide-desc {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: $text-3;
}

.guide-btn {
  width: 100%;
  margin-top: 40rpx;
}

.version {
  display: block;
  text-align: center;
  margin-top: 48rpx;
  font-size: 20rpx;
  color: $placeholder;
  font-family: $font-mono;
  letter-spacing: 0.08em;
}
</style>
