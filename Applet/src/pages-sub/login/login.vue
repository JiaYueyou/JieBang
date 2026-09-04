<script setup lang="ts">
import { ref } from 'vue'
import { mockLogin } from '@/api/admin'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const mode = ref<'login' | 'register'>('login')
const username = ref('admin')
const password = ref('admin123')
const submitting = ref(false)
const agreed = ref(true)

/* 演示版仅开放管理员登录 */
function switchMode(m: 'login' | 'register') {
  if (m === 'register') {
    uni.showToast({ title: '演示版暂不开放注册', icon: 'none' })
    return
  }
  mode.value = m
}

async function submit() {
  if (submitting.value) return
  if (!username.value.trim() || !password.value) {
    uni.showToast({ title: '请输入账号和密码', icon: 'none' })
    return
  }
  if (!agreed.value) {
    uni.showToast({ title: '请先阅读并同意用户协议', icon: 'none' })
    return
  }
  submitting.value = true
  try {
    const { token, user } = await mockLogin(username.value.trim(), password.value)
    userStore.setAuth(token, user)
    uni.showToast({ title: '欢迎回来', icon: 'success' })
    setTimeout(() => uni.switchTab({ url: '/pages/home/home' }), 400)
  } catch (e) {
    uni.showToast({ title: e instanceof Error ? e.message : '登录失败', icon: 'none' })
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <view class="login-page">
    <view class="hero">
      <view class="hero-stars">
        <view v-for="i in 9" :key="i" class="star" :class="`s${i}`" />
      </view>
      <view class="brand-ring" />
      <text class="hero-title">智联职引</text>
      <text class="hero-sub">管理决策端 · 数据驱动的岗位智能平台</text>
    </view>

    <view class="form-card glass-card fade-up delay-2">
      <view class="mode-tabs">
        <text class="mode-tab active">管理员登录</text>
        <text class="mode-tab" @tap="switchMode('register')">注册</text>
      </view>

      <view class="field">
        <text class="field-label">账号</text>
        <input v-model="username" class="field-input" placeholder="请输入管理员账号" placeholder-class="input-placeholder" />
      </view>
      <view class="field">
        <text class="field-label">密码</text>
        <input v-model="password" class="field-input" password placeholder="请输入密码" placeholder-class="input-placeholder" />
      </view>

      <view class="agree-row" @tap="agreed = !agreed">
        <view class="agree-dot" :class="{ on: agreed }">
          <uni-icons v-if="agreed" type="checkmarkempty" size="12" color="#fff" />
        </view>
        <text class="agree-text">我已阅读并同意《用户协议》与《隐私政策》</text>
      </view>

      <view class="btn-primary submit-btn" :class="{ disabled: submitting }" @tap="submit">
        {{ submitting ? '登录中…' : '登 录' }}
      </view>

      <text class="hint">演示环境账号：admin / admin123</text>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(178deg, $ink 0%, $navy 46%, $brand 100%);
  padding-bottom: 80rpx;
}

.hero {
  position: relative;
  padding: calc(200rpx + env(safe-area-inset-top)) 0 70rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
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
    animation: twinkle 2.8s ease-in-out infinite;

    &.s1 { top: 18%; left: 14%; }
    &.s2 { top: 30%; left: 78%; animation-delay: 0.4s; }
    &.s3 { top: 12%; left: 52%; animation-delay: 0.9s; }
    &.s4 { top: 44%; left: 22%; animation-delay: 1.3s; }
    &.s5 { top: 52%; left: 86%; animation-delay: 0.2s; }
    &.s6 { top: 24%; left: 34%; animation-delay: 1.7s; }
    &.s7 { top: 60%; left: 60%; animation-delay: 1.1s; }
    &.s8 { top: 40%; left: 46%; animation-delay: 2.1s; }
    &.s9 { top: 66%; left: 12%; animation-delay: 0.6s; }
  }
}

@keyframes twinkle {
  0%, 100% { opacity: 0.25; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.25); }
}

.brand-ring {
  width: 128rpx;
  height: 128rpx;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #fff 0 10rpx, transparent 12rpx),
    conic-gradient(from 0deg, #fff 0 70deg, rgba(255, 255, 255, 0.25) 110deg 360deg);
  mask: radial-gradient(circle, transparent 0 34rpx, #000 35rpx);
  -webkit-mask: radial-gradient(circle, transparent 0 34rpx, #000 35rpx);
}

.hero-title {
  margin-top: 34rpx;
  font-size: 44rpx;
  font-weight: 800;
  color: #fff;
  letter-spacing: 0.04em;
}

.hero-sub {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.72);
  letter-spacing: 0.06em;
}

.form-card {
  margin: 0 44rpx;
  padding: 44rpx 40rpx 40rpx;
  border-radius: 32rpx;
}

.mode-tabs {
  display: flex;
  gap: 36rpx;
  margin-bottom: 36rpx;
}

.mode-tab {
  font-size: 32rpx;
  font-weight: 600;
  color: $text-3;
  padding-bottom: 10rpx;
  border-bottom: 4rpx solid transparent;

  &.active {
    color: $text-1;
    border-bottom-color: $brand;
  }
}

.field {
  margin-bottom: 28rpx;
}

.field-label {
  display: block;
  font-size: 24rpx;
  color: $text-2;
  margin-bottom: 12rpx;
}

.field-input {
  height: 92rpx;
  padding: 0 28rpx;
  border-radius: $radius-lg;
  background: $bg-muted;
  border: 1rpx solid $border-light;
  font-size: 28rpx;
  color: $text-1;
}

.input-placeholder {
  color: $placeholder;
}

.agree-row {
  display: flex;
  align-items: center;
  gap: 14rpx;
  margin: 8rpx 0 32rpx;
}

.agree-dot {
  width: 32rpx;
  height: 32rpx;
  border-radius: 50%;
  border: 2rpx solid $border;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &.on {
    background: $brand;
    border-color: $brand;
  }
}

.agree-text {
  font-size: 22rpx;
  color: $text-3;
}

.submit-btn {
  height: 92rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30rpx;

  &.disabled { opacity: 0.6; }
}

.hint {
  display: block;
  margin-top: 26rpx;
  text-align: center;
  font-size: 22rpx;
  color: $text-3;
  font-family: $font-mono;
}
</style>
