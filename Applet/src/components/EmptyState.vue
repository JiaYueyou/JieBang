<script setup lang="ts">
defineProps<{
  icon?: string
  title: string
  desc?: string
}>()
</script>

<template>
  <view class="empty">
    <view class="empty-icon">
      <uni-icons :type="icon || 'info'" size="30" color="#b4c2f2" />
    </view>
    <text class="empty-title">{{ title }}</text>
    <text v-if="desc" class="empty-desc">{{ desc }}</text>
    <slot />
  </view>
</template>

<style lang="scss" scoped>
.empty-icon {
  width: 108rpx;
  height: 108rpx;
  border-radius: 36rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $brand-light;
}
</style>
