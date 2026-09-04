<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'

onShow(() => {
  uni.hideTabBar({ animation: false })
})
</script>

<template>
  <view class="page-placeholder">
    <view class="page-placeholder-inner">
      <text class="ph-badge">MODULE</text>
      <text class="ph-title">模块建设中</text>
      <text class="ph-desc">该模块将在下一阶段接入真实数据</text>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.page-placeholder {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.page-placeholder-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}
.ph-badge {
  font-family: $font-mono;
  font-size: 20rpx;
  letter-spacing: 0.2em;
  color: $brand;
  margin-bottom: 8rpx;
}
.ph-title { font-size: 34rpx; font-weight: 700; color: $text-1; }
.ph-desc { font-size: 24rpx; color: $text-3; }
</style>
