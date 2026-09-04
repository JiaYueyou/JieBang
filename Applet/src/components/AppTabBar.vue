<script setup lang="ts">
defineProps<{ current: string }>()

const tabs = [
  { key: 'home', text: '工作台', icon: 'home', path: '/pages/home/home' },
  { key: 'positions', text: '职位', icon: 'list', path: '/pages/positions/positions' },
  { key: 'graph', text: '图谱', icon: 'link', path: '/pages/graph/graph' },
  { key: 'match', text: '洞察', icon: 'fire', path: '/pages/match/match' },
  { key: 'profile', text: '管理', icon: 'gear', path: '/pages/profile/profile' },
]

function go(path: string) {
  uni.switchTab({ url: path })
}
</script>

<template>
  <view class="tabbar glass-card">
    <view
      v-for="t in tabs"
      :key="t.key"
      class="tabbar-item"
      :class="{ active: t.key === current }"
      @tap="go(t.path)"
    >
      <view class="tabbar-icon-wrap">
        <uni-icons
          :type="t.icon"
          size="22"
          :color="t.key === current ? '#4f6ef6' : '#989eae'"
        />
      </view>
      <text class="tabbar-label">{{ t.text }}</text>
      <view class="tabbar-dot" />
    </view>
  </view>
</template>

<style lang="scss" scoped>
.tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  display: flex;
  align-items: stretch;
  height: calc(104rpx + env(safe-area-inset-bottom));
  padding-bottom: env(safe-area-inset-bottom);
  border-top: 1rpx solid rgba(232, 235, 240, 0.9);
  box-shadow: 0 -8rpx 32rpx rgba(18, 45, 110, 0.06);
}

.tabbar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2rpx;
  position: relative;
  transition: transform $duration-fast $ease;

  &:active { transform: scale(0.92); }
}

.tabbar-label {
  font-size: 20rpx;
  font-weight: 500;
  color: $text-3;
  transition: color $duration-fast $ease;
}

.tabbar-item.active .tabbar-label {
  color: $brand;
  font-weight: 700;
}

.tabbar-dot {
  position: absolute;
  top: 10rpx;
  width: 32rpx;
  height: 6rpx;
  border-radius: $radius-full;
  background: linear-gradient(90deg, $brand, $violet);
  opacity: 0;
  transform: scaleX(0.3);
  transition: all $duration-normal $ease;
}

.tabbar-item.active .tabbar-dot {
  opacity: 1;
  transform: scaleX(1);
}
</style>
