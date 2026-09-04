<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiTrendInsights } from '@/api/admin'
import type { SkillTrend } from '@/mock/data'
import BarRank from '@/components/BarRank.vue'
import AppTabBar from '@/components/AppTabBar.vue'

const statusBarHeight = uni.getWindowInfo().statusBarHeight
const loading = ref(true)

const skillTrends = ref<SkillTrend[]>([])
const cityHeat = ref<{ name: string; value: number }[]>([])
const donut = ref<{ name: string; value: number; color: string }[]>([])

onShow(() => {
  uni.hideTabBar({ animation: false })
  refresh()
})

async function refresh() {
  loading.value = true
  try {
    const d = await apiTrendInsights()
    skillTrends.value = d.skillTrends
    cityHeat.value = d.cityHeat
    donut.value = d.donut
  } catch {
    /* mock */
  } finally {
    loading.value = false
  }
}

/* donut conic-gradient */
const donutStyle = computed(() => {
  let acc = 0
  const stops = donut.value.map((d) => {
    const from = acc
    acc += d.value
    return `${d.color} ${from}% ${acc}%`
  })
  return `conic-gradient(${stops.join(', ')})`
})

const cityMax = computed(() => Math.max(...cityHeat.value.map((c) => c.value), 1))

const rising = computed(() => skillTrends.value.filter((s) => s.lifecycle === '上升期').length)
</script>

<template>
  <view class="insight-page">
    <view class="page-head" :style="{ paddingTop: statusBarHeight + 'px' }">
      <text class="page-title">趋势洞察</text>
      <text class="page-sub">技能热度 · 城市分布 · 岗位结构</text>
    </view>

    <view v-if="loading" class="loading-list">
      <view v-for="i in 3" :key="i" class="card" style="padding: 32rpx">
        <view class="skeleton" style="width: 50%; height: 32rpx" />
        <view class="skeleton" style="width: 85%; height: 24rpx; margin-top: 18rpx" />
      </view>
    </view>

    <template v-else>
      <!-- 概览 -->
      <view class="insight-hero fade-up">
        <view class="ih-stat">
          <text class="ih-num">{{ rising }}</text>
          <text class="ih-label">上升期技能</text>
        </view>
        <view class="ih-divider" />
        <view class="ih-stat">
          <text class="ih-num">+8.4%</text>
          <text class="ih-label">大模型应用 环比</text>
        </view>
        <view class="ih-divider" />
        <view class="ih-stat">
          <text class="ih-num">{{ cityHeat[0]?.name ?? '—' }}</text>
          <text class="ih-label">岗位热度城市</text>
        </view>
      </view>

      <!-- 技能热度榜 -->
      <view class="section-head">
        <text class="section-title">技能热度榜</text>
        <text class="section-sub">趋势评分 · 生命周期</text>
      </view>
      <view class="card rank-card fade-up">
        <BarRank
          :items="skillTrends.map((s) => ({ name: s.name, score: s.score, delta: s.delta, tag: s.lifecycle, sources: s.sources }))"
        />
      </view>

      <!-- 岗位结构 -->
      <view class="section-head">
        <text class="section-title">岗位结构</text>
        <text class="section-sub">新兴 vs 既有</text>
      </view>
      <view class="card donut-card fade-up">
        <view class="donut-ring" :style="{ background: donutStyle }">
          <view class="donut-hole">
            <text class="donut-total">1284</text>
            <text class="donut-unit">岗位总量</text>
          </view>
        </view>
        <view class="donut-legend">
          <view v-for="d in donut" :key="d.name" class="dl-item">
            <view class="dl-dot" :style="{ background: d.color }" />
            <text class="dl-name">{{ d.name }}</text>
            <text class="dl-value">{{ d.value }}%</text>
          </view>
        </view>
      </view>

      <!-- 城市热度 -->
      <view class="section-head">
        <text class="section-title">城市热度</text>
        <text class="section-sub">岗位快照数</text>
      </view>
      <view class="card city-card fade-up">
        <view v-for="c in cityHeat" :key="c.name" class="city-row">
          <text class="city-name">{{ c.name }}</text>
          <view class="city-track">
            <view class="city-bar" :style="{ width: Math.round((c.value / cityMax) * 100) + '%' }" />
          </view>
          <text class="city-value">{{ c.value }}</text>
        </view>
      </view>

      <text class="foot-note">数据说明：趋势评分综合独立来源数与岗位快照频次计算，每日滚动更新</text>
    </template>

    <AppTabBar current="match" />
  </view>
</template>

<style lang="scss" scoped>
.insight-page {
  min-height: 100vh;
  padding-bottom: calc(180rpx + env(safe-area-inset-bottom));
}

.page-head {
  padding: 24rpx 40rpx 8rpx;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.page-title {
  font-size: 40rpx;
  font-weight: 700;
  color: $text-1;
  letter-spacing: -0.02em;
}

.page-sub {
  font-size: 23rpx;
  color: $text-3;
}

.loading-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
  margin: 24rpx 32rpx 0;
}

/* ── 概览 hero ── */
.insight-hero {
  display: flex;
  align-items: center;
  margin: 24rpx 32rpx 0;
  padding: 34rpx 20rpx;
  border-radius: $radius-lg;
  background: linear-gradient(160deg, $ink 0%, $navy 55%, $brand 100%);
  box-shadow: $shadow-md;
}

.ih-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.ih-num {
  font-family: $font-mono;
  font-size: 38rpx;
  font-weight: 700;
  color: #fff;
}

.ih-label {
  font-size: 21rpx;
  color: rgba(255, 255, 255, 0.68);
}

.ih-divider {
  width: 1rpx;
  height: 56rpx;
  background: rgba(255, 255, 255, 0.18);
}

/* ── 区块 ── */
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
}

.section-sub {
  font-size: 22rpx;
  color: $text-3;
}

.rank-card {
  margin: 0 32rpx;
  padding: 34rpx 32rpx;
}

/* ── donut ── */
.donut-card {
  margin: 0 32rpx;
  padding: 40rpx 36rpx;
  display: flex;
  align-items: center;
  gap: 44rpx;
}

.donut-ring {
  width: 220rpx;
  height: 220rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: $shadow-md;
}

.donut-hole {
  width: 148rpx;
  height: 148rpx;
  border-radius: 50%;
  background: $card;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.donut-total {
  font-family: $font-mono;
  font-size: 34rpx;
  font-weight: 700;
  color: $text-1;
}

.donut-unit {
  margin-top: 2rpx;
  font-size: 19rpx;
  color: $text-3;
}

.donut-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.dl-item {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.dl-dot {
  width: 18rpx;
  height: 18rpx;
  border-radius: 6rpx;
}

.dl-name {
  font-size: 26rpx;
  color: $text-1;
}

.dl-value {
  margin-left: auto;
  font-family: $font-mono;
  font-size: 28rpx;
  font-weight: 700;
  color: $text-1;
}

/* ── 城市热度 ── */
.city-card {
  margin: 0 32rpx;
  padding: 36rpx 34rpx;
  display: flex;
  flex-direction: column;
  gap: 28rpx;
}

.city-row {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.city-name {
  width: 88rpx;
  font-size: 25rpx;
  color: $text-1;
  font-weight: 600;
  flex-shrink: 0;
}

.city-track {
  flex: 1;
  height: 18rpx;
  border-radius: $radius-full;
  background: $bg-muted;
  overflow: hidden;
}

.city-bar {
  height: 100%;
  border-radius: $radius-full;
  background: linear-gradient(90deg, $navy, $brand 70%, #7b8ff7);
  transition: width 0.6s $ease;
}

.city-value {
  width: 76rpx;
  text-align: right;
  font-family: $font-mono;
  font-size: 25rpx;
  font-weight: 700;
  color: $text-2;
  flex-shrink: 0;
}

.foot-note {
  display: block;
  margin: 36rpx 44rpx 0;
  font-size: 21rpx;
  color: $placeholder;
  line-height: 1.6;
}
</style>
