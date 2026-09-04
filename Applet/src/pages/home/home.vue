<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiOverview } from '@/api/admin'
import type { KpiItem, TodoItem, ActivityItem } from '@/mock/data'
import TrendChart from '@/components/TrendChart.vue'
import AppTabBar from '@/components/AppTabBar.vue'

const statusBarHeight = uni.getWindowInfo().statusBarHeight
const loading = ref(true)

const kpis = ref<KpiItem[]>([])
const trendDays = ref<string[]>([])
const trendJobs = ref<number[]>([])
const trendMatches = ref<number[]>([])
const todos = ref<TodoItem[]>([])
const activities = ref<ActivityItem[]>([])

const hour = new Date().getHours()
const greeting = hour < 6 ? '凌晨好' : hour < 12 ? '上午好' : hour < 14 ? '中午好' : hour < 18 ? '下午好' : '晚上好'
const today = new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })

onShow(() => {
  uni.hideTabBar({ animation: false })
  refresh()
})

async function refresh() {
  loading.value = true
  try {
    const d = await apiOverview()
    kpis.value = d.kpis
    trendDays.value = d.trendDays
    trendJobs.value = d.trendJobs
    trendMatches.value = d.trendMatches
    todos.value = d.todos
    activities.value = d.activities
  } catch {
    /* mock 数据不会失败 */
  } finally {
    loading.value = false
  }
}

function switchTab(url: string) {
  uni.switchTab({ url })
}

const quickEntries = [
  { key: 'jobs', text: '职位管理', icon: 'list', tint: 'brand', path: 'switch:/pages/positions/positions' },
  { key: 'graph', text: '技能图谱', icon: 'pyq', tint: 'info', path: 'switch:/pages/graph/graph' },
  { key: 'insight', text: '趋势洞察', icon: 'fire', tint: 'warning', path: 'switch:/pages/match/match' },
  { key: 'admin', text: '管理中心', icon: 'gear', tint: 'success', path: 'switch:/pages/profile/profile' },
]

function onEntry(path: string) {
  const [type, url] = path.split(':')
  if (type === 'switch') uni.switchTab({ url })
  else uni.navigateTo({ url })
}
</script>

<template>
  <view class="home-page">
    <!-- 星图 hero -->
    <view class="hero" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="hero-stars">
        <view v-for="i in 9" :key="i" class="star" :class="`s${i}`" />
        <view class="mesh-line l1" />
        <view class="mesh-line l2" />
        <view class="mesh-line l3" />
      </view>
      <view class="hero-inner">
        <text class="hero-date">{{ today }}</text>
        <text class="hero-title">{{ greeting }}，管理员</text>
        <text class="hero-sub">多源异构数据 · 岗位能力图谱 · 决策一览</text>

        <view class="hero-chips">
          <view v-for="k in kpis" :key="k.key" class="hero-chip glass-chip">
            <text class="chip-num">{{ k.value }}</text>
            <text class="chip-label">{{ k.label }}</text>
            <text class="chip-delta" :class="k.trend">{{ k.delta }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 待办 -->
    <view class="todo-row">
      <view
        v-for="(t, i) in todos"
        :key="t.key"
        class="todo-card card card-hover fade-up"
        :class="`delay-${i + 1}`"
        @tap="t.path && switchTab(t.path)"
      >
        <view class="todo-badge" :class="`tone-${t.tone}`">{{ t.count }}</view>
        <text class="todo-title">{{ t.title }}</text>
        <text class="todo-desc">{{ t.desc }}</text>
      </view>
    </view>

    <!-- 快捷入口 -->
    <view class="quick-grid fade-up">
      <view v-for="q in quickEntries" :key="q.key" class="quick-item" @tap="onEntry(q.path)">
        <view class="quick-icon" :class="`tint-${q.tint}`">
          <uni-icons :type="q.icon" size="22" color="#4f6ef6" />
        </view>
        <text class="quick-text">{{ q.text }}</text>
      </view>
    </view>

    <!-- 趋势 -->
    <view class="section-head fade-up">
      <text class="section-title">数据趋势</text>
      <text class="section-sub">近 30 天 · 岗位入库 / 匹配评估</text>
    </view>
    <view class="trend-card card fade-up delay-1">
      <view class="legend">
        <view class="legend-item">
          <view class="legend-dot" style="background: #4f6ef6" />
          <text>岗位入库</text>
        </view>
        <view class="legend-item">
          <view class="legend-dot" style="background: #34b37e" />
          <text>匹配评估</text>
        </view>
      </view>
      <TrendChart
        :labels="trendDays"
        :height="400"
        :series="[
          { name: '岗位入库', color: '#4f6ef6', data: trendJobs },
          { name: '匹配评估', color: '#34b37e', data: trendMatches },
        ]"
      />
    </view>

    <!-- 最近动态 -->
    <view class="section-head fade-up">
      <text class="section-title">最近动态</text>
      <text class="section-sub">系统与人工操作流水</text>
    </view>
    <view class="feed-card card fade-up delay-2">
      <view v-for="(a, i) in activities" :key="a.id" class="feed-item">
        <view class="feed-left">
          <view class="feed-dot" :class="`tone-${a.tone}`" />
          <view v-if="i !== activities.length - 1" class="feed-line" />
        </view>
        <view class="feed-body">
          <view class="feed-row">
            <text class="feed-action">{{ a.actor }} · {{ a.action }}</text>
            <text class="feed-time">{{ a.time }}</text>
          </view>
          <text class="feed-target">{{ a.target }}</text>
        </view>
      </view>
    </view>

    <AppTabBar current="home" />
  </view>
</template>

<style lang="scss" scoped>
.home-page {
  min-height: 100vh;
  padding-bottom: calc(180rpx + env(safe-area-inset-bottom));
}

/* ── hero ── */
.hero {
  position: relative;
  background: linear-gradient(165deg, $ink 0%, $navy 52%, $brand 100%);
  padding-bottom: 44rpx;
  overflow: hidden;
}

.hero-stars {
  position: absolute;
  inset: 0;

  .star {
    position: absolute;
    width: 5rpx;
    height: 5rpx;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.85);
    animation: twinkle 3s ease-in-out infinite;

    &.s1 { top: 12%; left: 10%; }
    &.s2 { top: 22%; left: 80%; animation-delay: 0.5s; }
    &.s3 { top: 8%; left: 55%; animation-delay: 1s; }
    &.s4 { top: 36%; left: 25%; animation-delay: 1.4s; }
    &.s5 { top: 30%; left: 90%; animation-delay: 0.2s; }
    &.s6 { top: 18%; left: 38%; animation-delay: 1.8s; }
    &.s7 { top: 46%; left: 65%; animation-delay: 1.2s; }
    &.s8 { top: 55%; left: 8%; animation-delay: 2.2s; }
    &.s9 { top: 60%; left: 88%; animation-delay: 0.7s; }
  }

  .mesh-line {
    position: absolute;
    height: 1rpx;
    background: linear-gradient(90deg, transparent, rgba(160, 180, 255, 0.35), transparent);

    &.l1 { top: 24%; left: -10%; width: 70%; transform: rotate(14deg); }
    &.l2 { top: 40%; left: 40%; width: 75%; transform: rotate(-10deg); }
    &.l3 { top: 58%; left: -5%; width: 60%; transform: rotate(6deg); }
  }
}

@keyframes twinkle {
  0%, 100% { opacity: 0.2; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.3); }
}

.hero-inner {
  position: relative;
  padding: 32rpx 40rpx 0;
}

.hero-date {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.6);
  font-family: $font-mono;
  letter-spacing: 0.08em;
}

.hero-title {
  display: block;
  margin-top: 10rpx;
  font-size: 44rpx;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.01em;
}

.hero-sub {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.65);
  letter-spacing: 0.04em;
}

.hero-chips {
  display: flex;
  gap: 16rpx;
  margin-top: 40rpx;
}

.glass-chip {
  flex: 1;
  padding: 22rpx 18rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.1);
  border: 1rpx solid rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.chip-num {
  font-family: $font-mono;
  font-size: 34rpx;
  font-weight: 700;
  color: #fff;
}

.chip-label {
  margin-top: 4rpx;
  font-size: 20rpx;
  color: rgba(255, 255, 255, 0.7);
}

.chip-delta {
  margin-top: 4rpx;
  font-family: $font-mono;
  font-size: 19rpx;

  &.up { color: #7ef0c0; }
  &.down { color: #ffb3b3; }
}

/* ── 待办 ── */
.todo-row {
  display: flex;
  gap: 18rpx;
  margin: 28rpx 32rpx 0;
}

.todo-card {
  flex: 1;
  padding: 24rpx 22rpx;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.todo-badge {
  width: 56rpx;
  height: 56rpx;
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: $font-mono;
  font-size: 24rpx;
  font-weight: 700;

  &.tone-danger { background: $danger-light; color: $danger; }
  &.tone-warning { background: $warning-light; color: $warning; }
  &.tone-brand { background: $brand-light; color: $brand; }
  &.tone-success { background: $success-light; color: $success; }
}

.todo-title {
  font-size: 26rpx;
  font-weight: 700;
  color: $text-1;
}

.todo-desc {
  font-size: 20rpx;
  color: $text-3;
  line-height: 1.5;
}

/* ── 快捷入口 ── */
.quick-grid {
  display: flex;
  margin: 24rpx 32rpx 0;
  padding: 30rpx 10rpx;
  background: $card;
  border-radius: $radius-lg;
  border: 1rpx solid rgba(232, 235, 240, 0.7);
  box-shadow: $shadow-sm;
}

.quick-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;

  &:active { opacity: 0.7; }
}

.quick-icon {
  width: 84rpx;
  height: 84rpx;
  border-radius: 26rpx;
  display: flex;
  align-items: center;
  justify-content: center;

  &.tint-brand { background: $brand-light; }
  &.tint-info { background: $info-light; }
  &.tint-warning { background: $warning-light; }
  &.tint-success { background: $success-light; }
}

.quick-text {
  font-size: 23rpx;
  color: $text-2;
}

/* ── 区块通用 ── */
.section-head {
  margin: 40rpx 40rpx 20rpx;
  display: flex;
  align-items: baseline;
  gap: 16rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: 700;
  color: $text-1;
  letter-spacing: -0.01em;
}

.section-sub {
  font-size: 22rpx;
  color: $text-3;
}

/* ── 趋势卡 ── */
.trend-card {
  margin: 0 32rpx;
  padding: 30rpx 24rpx 20rpx;
}

.legend {
  display: flex;
  gap: 28rpx;
  margin-bottom: 8rpx;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10rpx;
  font-size: 22rpx;
  color: $text-2;
}

.legend-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 6rpx;
}

/* ── 动态流 ── */
.feed-card {
  margin: 0 32rpx;
  padding: 14rpx 30rpx;
}

.feed-item {
  display: flex;
  gap: 22rpx;
}

.feed-left {
  width: 20rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 34rpx;
}

.feed-dot {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
  flex-shrink: 0;

  &.tone-brand { background: $brand; box-shadow: 0 0 0 6rpx $brand-light; }
  &.tone-success { background: $success; box-shadow: 0 0 0 6rpx $success-light; }
  &.tone-warning { background: $warning; box-shadow: 0 0 0 6rpx $warning-light; }
}

.feed-line {
  width: 2rpx;
  flex: 1;
  background: $border-light;
  margin-top: 6rpx;
}

.feed-body {
  flex: 1;
  padding: 26rpx 0;
  min-width: 0;
}

.feed-item:last-child .feed-body {
  padding-bottom: 34rpx;
}

.feed-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12rpx;
}

.feed-action {
  font-size: 26rpx;
  font-weight: 600;
  color: $text-1;
}

.feed-time {
  font-family: $font-mono;
  font-size: 20rpx;
  color: $text-3;
  flex-shrink: 0;
}

.feed-target {
  display: block;
  margin-top: 6rpx;
  font-size: 23rpx;
  color: $text-2;
}
</style>
