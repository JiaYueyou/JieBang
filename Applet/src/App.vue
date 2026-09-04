<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'

onLaunch(() => {
  console.log('智联职引小程序启动')
})
</script>

<style lang="scss">
@import '@/styles/common.scss';

page {
  /* 设计令牌 → CSS 自定义属性（供模板内联样式使用） */
  --brand: #{$brand};
  --brand-light: #{$brand-light};
  --ink: #{$ink};
  --navy: #{$navy};
  --violet: #{$violet};
  --success: #{$success};
  --warning: #{$warning};
  --danger: #{$danger};
  --text-1: #{$text-1};
  --text-2: #{$text-2};
  --text-3: #{$text-3};
  --bg: #{$bg};
  --card: #{$card};
  --border: #{$border};

  background: $bg;
  color: $text-1;
  font-family: $font-sans;
  font-size: 28rpx;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
</style>
