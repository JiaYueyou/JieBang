<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { apiAdminJobDetail, apiToggleJobStatus } from '@/api/admin'
import type { AdminJob } from '@/mock/data'

const job = ref<AdminJob | null>(null)
const loading = ref(true)
const toggling = ref(false)
let jobId = ''

onLoad((opts) => {
  jobId = opts?.id ?? ''
})

onShow(() => {
  fetchDetail()
})

async function fetchDetail() {
  loading.value = true
  try {
    job.value = await apiAdminJobDetail(jobId)
  } catch (e) {
    uni.showToast({ title: e instanceof Error ? e.message : '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function levelClass(level: string) {
  if (level === '必备') return 'required'
  if (level === '精通') return 'advanced'
  return 'preferred'
}

async function toggleStatus() {
  if (!job.value || toggling.value) return
  toggling.value = true
  try {
    const r = await apiToggleJobStatus(job.value.id)
    job.value.status = r.status as AdminJob['status']
    uni.showToast({ title: r.status === '已下线' ? '已下线该岗位' : '已重新上架', icon: 'success' })
  } catch (e) {
    uni.showToast({ title: e instanceof Error ? e.message : '操作失败', icon: 'none' })
  } finally {
    toggling.value = false
  }
}

function copyLink() {
  uni.setClipboardData({
    data: `智联职引 · ${job.value?.name ?? ''}（${job.value?.id ?? ''}）`,
    success: () => uni.showToast({ title: '岗位标识已复制', icon: 'success' }),
  })
}
</script>

<template>
  <view class="detail-page">
    <view v-if="loading" class="loading-wrap">
      <view class="skeleton" style="width: 60%; height: 36rpx" />
      <view class="skeleton" style="width: 90%; height: 24rpx; margin-top: 20rpx" />
      <view class="skeleton" style="width: 80%; height: 24rpx; margin-top: 14rpx" />
    </view>

    <template v-else-if="job">
      <!-- 头部 -->
      <view class="head fade-up">
        <view class="head-top">
          <text class="job-name">{{ job.name }}</text>
          <text class="job-status" :class="job.status === '急缺' ? 'danger' : job.status === '在招' ? 'success' : job.status === '评估中' ? 'warning' : 'neutral'">
            {{ job.status }}
          </text>
        </view>
        <text class="job-salary">{{ job.salary }}</text>
        <view class="head-chips">
          <text class="h-chip" :class="job.category === 'emerging' ? 'violet' : ''">
            {{ job.category === 'emerging' ? '新兴岗位' : '既有岗位' }}
          </text>
          <text class="h-chip">{{ job.city }}</text>
          <text class="h-chip">{{ job.sources }} 个独立来源</text>
        </view>

        <view class="head-stats">
          <view class="stat">
            <text class="stat-num">{{ job.seats }}</text>
            <text class="stat-label">需求席位</text>
          </view>
          <view class="stat">
            <text class="stat-num">{{ job.talentPool }}</text>
            <text class="stat-label">人才池</text>
          </view>
          <view class="stat">
            <text class="stat-num">{{ Math.round((job.talentPool / Math.max(job.seats, 1)) * 10) / 10 }}</text>
            <text class="stat-label">人才/席位</text>
          </view>
          <view class="stat">
            <text class="stat-num" style="font-size: 26rpx; padding-top: 8rpx">{{ job.updatedAt }}</text>
            <text class="stat-label">最近更新</text>
          </view>
        </view>
      </view>

      <!-- 岗位摘要 -->
      <view class="block card fade-up delay-1">
        <text class="block-title">岗位摘要</text>
        <text class="summary">{{ job.summary }}</text>
      </view>

      <!-- 核心技能 -->
      <view class="block card fade-up delay-2">
        <text class="block-title">核心技能要求</text>
        <view class="skill-list">
          <view v-for="s in job.skills" :key="s.name" class="skill-item">
            <text class="skill-name">{{ s.name }}</text>
            <text class="skill-level" :class="levelClass(s.level)">{{ s.level }}</text>
          </view>
        </view>
      </view>

      <!-- 岗位职责 -->
      <view class="block card fade-up delay-3">
        <text class="block-title">岗位职责</text>
        <view class="duty-item" v-for="(d, i) in job.duties" :key="i">
          <text class="duty-index">{{ i + 1 }}</text>
          <text class="duty-text">{{ d }}</text>
        </view>
      </view>

      <text class="update-time">数据更新于 {{ job.updatedAt }} · 来源聚合快照</text>

      <!-- 底部操作 -->
      <view class="action-bar glass-card">
        <view class="action-secondary" @tap="copyLink">
          <uni-icons type="copy" size="18" color="#4f6ef6" />
          <text>复制</text>
        </view>
        <view class="btn-primary action-main" :class="{ disabled: toggling }" @tap="toggleStatus">
          {{ job.status === '已下线' ? '重新上架' : '下线岗位' }}
        </view>
      </view>
    </template>

    <view v-else class="loading-wrap">
      <text style="color: #989eae">职位不存在或已删除</text>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  padding: 24rpx 32rpx calc(200rpx + env(safe-area-inset-bottom));
}

.loading-wrap {
  padding: 80rpx 40rpx;
}

.head {
  padding: 36rpx 36rpx 30rpx;
  border-radius: $radius-lg;
  background: linear-gradient(160deg, $ink 0%, $navy 55%, $brand 100%);
  box-shadow: $shadow-md;
}

.head-top {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.job-name {
  font-size: 38rpx;
  font-weight: 800;
  color: #fff;
  flex: 1;
  min-width: 0;
}

.job-status {
  padding: 6rpx 18rpx;
  border-radius: $radius-full;
  font-size: 21rpx;
  flex-shrink: 0;

  &.danger { background: rgba(232, 93, 93, 0.25); color: #ffb3b3; }
  &.success { background: rgba(52, 179, 126, 0.25); color: #9bf0cd; }
  &.warning { background: rgba(245, 158, 75, 0.25); color: #ffd9ad; }
  &.neutral { background: rgba(255, 255, 255, 0.18); color: rgba(255, 255, 255, 0.8); }
}

.job-salary {
  display: block;
  margin-top: 14rpx;
  font-family: $font-mono;
  font-size: 32rpx;
  font-weight: 700;
  color: #aef0d6;
}

.head-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 22rpx;
}

.h-chip {
  padding: 6rpx 20rpx;
  border-radius: $radius-full;
  background: rgba(255, 255, 255, 0.14);
  border: 1rpx solid rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.88);
  font-size: 21rpx;

  &.violet {
    background: rgba(124, 111, 247, 0.4);
    border-color: rgba(255, 255, 255, 0.3);
  }
}

.head-stats {
  display: flex;
  margin-top: 30rpx;
  padding-top: 26rpx;
  border-top: 1rpx solid rgba(255, 255, 255, 0.16);
}

.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
}

.stat-num {
  font-family: $font-mono;
  font-size: 32rpx;
  font-weight: 700;
  color: #fff;
}

.stat-label {
  font-size: 20rpx;
  color: rgba(255, 255, 255, 0.65);
}

.block {
  margin-top: 24rpx;
  padding: 32rpx 34rpx;
}

.block-title {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  color: $text-1;
  margin-bottom: 22rpx;
}

.summary {
  font-size: 26rpx;
  color: $text-2;
  line-height: 1.75;
}

.skill-list {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.skill-item {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 12rpx 20rpx;
  border-radius: $radius-full;
  background: $bg-muted;
  border: 1rpx solid $border-light;
}

.skill-name {
  font-size: 24rpx;
  color: $text-1;
  font-weight: 500;
}

.skill-level {
  font-size: 19rpx;

  &.required { color: $brand; }
  &.preferred { color: $warning; }
  &.advanced { color: $violet; }
}

.duty-item {
  display: flex;
  gap: 18rpx;
  margin-bottom: 20rpx;

  &:last-child { margin-bottom: 0; }
}

.duty-index {
  width: 38rpx;
  height: 38rpx;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $brand-light;
  color: $brand;
  font-family: $font-mono;
  font-size: 19rpx;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 2rpx;
}

.duty-text {
  font-size: 26rpx;
  color: $text-2;
  line-height: 1.7;
}

.update-time {
  display: block;
  margin-top: 32rpx;
  text-align: center;
  font-size: 21rpx;
  color: $placeholder;
  font-family: $font-mono;
}

.action-bar {
  position: fixed;
  left: 32rpx;
  right: 32rpx;
  bottom: calc(24rpx + env(safe-area-inset-bottom));
  display: flex;
  gap: 18rpx;
  padding: 20rpx;
  border-radius: 28rpx;
  box-shadow: $shadow-lg;
  z-index: 50;
}

.action-secondary {
  width: 120rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4rpx;
  border-radius: 20rpx;
  background: $brand-light;
  color: $brand;
  font-size: 20rpx;

  &:active { opacity: 0.8; }
}

.action-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;

  &.disabled { opacity: 0.6; }
}
</style>
