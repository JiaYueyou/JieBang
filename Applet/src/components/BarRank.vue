<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    items: { name: string; score: number; delta?: number; tag?: string; sources?: number }[]
    /** 数值单位 */
    unit?: string
  }>(),
  { unit: '' },
)

function widthOf(score: number, items: { score: number }[]) {
  const max = Math.max(...items.map((i) => i.score), 1)
  return Math.max(6, Math.round((score / max) * 100))
}

function deltaClass(delta?: number) {
  if (delta == null) return ''
  return delta >= 0 ? 'up' : 'down'
}

function deltaText(delta?: number) {
  if (delta == null) return ''
  return `${delta >= 0 ? '▲' : '▼'} ${Math.abs(delta).toFixed(1)}`
}
</script>

<template>
  <view class="rank-list">
    <view v-for="(item, i) in items" :key="item.name" class="rank-row fade-up" :style="{ animationDelay: `${i * 45}ms` }">
      <text class="rank-index" :class="{ top: i < 3 }">{{ i + 1 }}</text>
      <view class="rank-main">
        <view class="rank-head">
          <text class="rank-name">{{ item.name }}</text>
          <text v-if="item.tag" class="rank-tag">{{ item.tag }}</text>
          <text class="rank-value">{{ item.score }}{{ unit }}</text>
        </view>
        <view class="rank-track">
          <view class="rank-bar" :style="{ width: widthOf(item.score, items) + '%' }" />
        </view>
        <view v-if="item.delta != null || item.sources != null" class="rank-meta">
          <text v-if="item.delta != null" class="rank-delta" :class="deltaClass(item.delta)">
            {{ deltaText(item.delta) }}
          </text>
          <text v-if="item.sources != null" class="rank-src">{{ item.sources }} 个独立来源</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.rank-list {
  display: flex;
  flex-direction: column;
  gap: 26rpx;
}

.rank-row {
  display: flex;
  gap: 20rpx;
  align-items: flex-start;
}

.rank-index {
  width: 40rpx;
  height: 40rpx;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: $font-mono;
  font-size: 20rpx;
  font-weight: 700;
  background: $bg-muted;
  color: $text-3;
  flex-shrink: 0;
  margin-top: 2rpx;

  &.top {
    background: $brand-light;
    color: $brand;
  }
}

.rank-main {
  flex: 1;
  min-width: 0;
}

.rank-head {
  display: flex;
  align-items: baseline;
  gap: 12rpx;
}

.rank-name {
  font-size: 27rpx;
  font-weight: 600;
  color: $text-1;
}

.rank-tag {
  padding: 2rpx 12rpx;
  border-radius: $radius-full;
  background: $bg-muted;
  font-size: 19rpx;
  color: $text-2;
}

.rank-value {
  margin-left: auto;
  font-family: $font-mono;
  font-size: 26rpx;
  font-weight: 700;
  color: $text-1;
}

.rank-track {
  margin-top: 12rpx;
  height: 14rpx;
  border-radius: $radius-full;
  background: $bg-muted;
  overflow: hidden;
}

.rank-bar {
  height: 100%;
  border-radius: $radius-full;
  background: linear-gradient(90deg, $navy, $brand 60%, #7b8ff7);
  transition: width 0.6s $ease;
}

.rank-meta {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-top: 8rpx;
}

.rank-delta {
  font-family: $font-mono;
  font-size: 20rpx;

  &.up { color: $success; }
  &.down { color: $danger; }
}

.rank-src {
  font-size: 20rpx;
  color: $text-3;
}
</style>
