<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiListAdminJobs } from '@/api/admin'
import type { AdminJob } from '@/mock/data'
import EmptyState from '@/components/EmptyState.vue'
import AppTabBar from '@/components/AppTabBar.vue'

const statusBarHeight = uni.getWindowInfo().statusBarHeight

const keyword = ref('')
const segment = ref<'all' | 'emerging' | 'existing'>('all')
const jobs = ref<AdminJob[]>([])
const loading = ref(true)
const firstLoaded = ref(false)

async function reload() {
  loading.value = true
  try {
    jobs.value = await apiListAdminJobs({ keyword: keyword.value, category: segment.value })
  } catch {
    /* mock */
  } finally {
    loading.value = false
    firstLoaded.value = true
  }
}

onShow(() => {
  uni.hideTabBar({ animation: false })
  reload()
})

const segments = [
  { key: 'all', text: '全部' },
  { key: 'emerging', text: '新兴岗位' },
  { key: 'existing', text: '既有岗位' },
] as const

function pickSegment(key: 'all' | 'emerging' | 'existing') {
  segment.value = key
  reload()
}

function onSearch() {
  reload()
}

function statusClass(s: AdminJob['status']) {
  if (s === '急缺') return 'danger'
  if (s === '在招') return 'success'
  if (s === '评估中') return 'warning'
  return 'neutral'
}

const summary = computed(() => {
  const urgent = jobs.value.filter((j) => j.status === '急缺').length
  return `${jobs.value.length} 个岗位 · ${urgent} 个急缺`
})

function goDetail(id: string) {
  uni.navigateTo({ url: `/pages-sub/position/detail?id=${id}` })
}
</script>

<template>
  <view class="jobs-page">
    <view class="page-head" :style="{ paddingTop: statusBarHeight + 'px' }">
      <text class="page-title">职位管理</text>
      <text class="page-sub">{{ summary }}</text>
    </view>

    <view class="search-wrap fade-up">
      <view class="search-box">
        <uni-icons type="search" size="18" color="#989eae" />
        <input
          v-model="keyword"
          class="search-input"
          placeholder="搜索岗位名称 / 描述"
          placeholder-class="input-placeholder"
          confirm-type="search"
          @confirm="onSearch"
        />
        <text v-if="keyword" class="search-clear" @tap="keyword = ''; onSearch()">清除</text>
      </view>
    </view>

    <view class="segment fade-up delay-1">
      <text
        v-for="s in segments"
        :key="s.key"
        class="segment-item"
        :class="{ active: segment === s.key }"
        @tap="pickSegment(s.key)"
      >
        {{ s.text }}
      </text>
    </view>

    <view v-if="loading && !firstLoaded" class="list">
      <view v-for="i in 4" :key="i" class="card job-card">
        <view class="skeleton" style="width: 55%; height: 32rpx" />
        <view class="skeleton" style="width: 90%; height: 24rpx; margin-top: 18rpx" />
        <view class="skeleton" style="width: 40%; height: 24rpx; margin-top: 14rpx" />
      </view>
    </view>

    <view v-else-if="jobs.length" class="list">
      <view
        v-for="(j, i) in jobs"
        :key="j.id"
        class="card card-hover job-card fade-up"
        :style="{ animationDelay: `${Math.min(i, 6) * 50}ms` }"
        @tap="goDetail(j.id)"
      >
        <view class="job-head">
          <text class="job-name">{{ j.name }}</text>
          <text class="job-status" :class="statusClass(j.status)">{{ j.status }}</text>
        </view>
        <text class="job-salary">{{ j.salary }}</text>
        <text class="job-summary clamp-2">{{ j.summary }}</text>
        <view class="job-stats">
          <view class="job-stat">
            <text class="js-num">{{ j.seats }}</text>
            <text class="js-label">需求席位</text>
          </view>
          <view class="job-stat">
            <text class="js-num">{{ j.talentPool }}</text>
            <text class="js-label">人才池</text>
          </view>
          <view class="job-stat">
            <text class="js-num">{{ j.sources }}</text>
            <text class="js-label">独立来源</text>
          </view>
          <view class="job-stat">
            <text class="js-num" style="font-size: 22rpx; padding-top: 6rpx">{{ j.city }}</text>
            <text class="js-label">城市</text>
          </view>
        </view>
        <view class="job-skill-row">
          <text v-for="s in j.skills.slice(0, 4)" :key="s.name" class="skill-chip">{{ s.name }}</text>
          <text v-if="j.skills.length > 4" class="skill-chip more">+{{ j.skills.length - 4 }}</text>
        </view>
      </view>
    </view>

    <EmptyState
      v-else
      icon="search"
      title="没有匹配的岗位"
      desc="换个关键词或切换分类试试"
    />

    <AppTabBar current="positions" />
  </view>
</template>

<style lang="scss" scoped>
.jobs-page {
  min-height: 100vh;
  padding-bottom: calc(180rpx + env(safe-area-inset-bottom));
}

.page-head {
  padding: 24rpx 40rpx 8rpx;
  display: flex;
  align-items: baseline;
  gap: 18rpx;
}

.page-title {
  font-size: 40rpx;
  font-weight: 700;
  color: $text-1;
  letter-spacing: -0.02em;
}

.page-sub {
  font-size: 22rpx;
  color: $text-3;
  font-family: $font-mono;
}

.search-wrap {
  margin: 20rpx 32rpx 0;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 16rpx;
  height: 84rpx;
  padding: 0 28rpx;
  border-radius: $radius-full;
  background: $card;
  border: 1rpx solid rgba(232, 235, 240, 0.7);
  box-shadow: $shadow-sm;
}

.search-input {
  flex: 1;
  font-size: 27rpx;
  color: $text-1;
}

.input-placeholder {
  color: $placeholder;
}

.search-clear {
  font-size: 22rpx;
  color: $brand;
}

.segment {
  display: flex;
  gap: 14rpx;
  margin: 22rpx 32rpx 0;
}

.segment-item {
  padding: 12rpx 30rpx;
  border-radius: $radius-full;
  background: $card;
  border: 1rpx solid rgba(232, 235, 240, 0.7);
  font-size: 25rpx;
  color: $text-2;
  transition: all $duration-fast $ease;

  &.active {
    background: $brand;
    border-color: $brand;
    color: #fff;
    font-weight: 600;
    box-shadow: 0 6rpx 18rpx $brand-glow;
  }
}

.list {
  display: flex;
  flex-direction: column;
  gap: 22rpx;
  margin: 24rpx 32rpx 0;
}

.job-card {
  padding: 30rpx 32rpx;
}

.job-head {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.job-name {
  font-size: 31rpx;
  font-weight: 700;
  color: $text-1;
  flex: 1;
  min-width: 0;
}

.job-status {
  padding: 4rpx 16rpx;
  border-radius: $radius-full;
  font-size: 20rpx;
  flex-shrink: 0;

  &.danger { background: $danger-light; color: $danger; }
  &.success { background: $success-light; color: $success; }
  &.warning { background: $warning-light; color: $warning; }
  &.neutral { background: $bg-muted; color: $text-3; }
}

.job-salary {
  display: block;
  margin-top: 10rpx;
  font-family: $font-mono;
  font-size: 26rpx;
  font-weight: 700;
  color: $brand;
}

.job-summary {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: $text-2;
  line-height: 1.65;
}

.job-stats {
  display: flex;
  margin-top: 22rpx;
  padding: 20rpx 0;
  border-top: 1rpx solid $border-light;
  border-bottom: 1rpx solid $border-light;
}

.job-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4rpx;
}

.js-num {
  font-family: $font-mono;
  font-size: 28rpx;
  font-weight: 700;
  color: $text-1;
}

.js-label {
  font-size: 20rpx;
  color: $text-3;
}

.job-skill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-top: 20rpx;
}

.skill-chip {
  padding: 6rpx 18rpx;
  border-radius: $radius-full;
  background: $brand-subtle;
  color: $brand;
  font-size: 21rpx;

  &.more {
    background: $bg-muted;
    color: $text-3;
  }
}
</style>
