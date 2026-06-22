<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ username: '', email: '', password: '', confirmPassword: '' })

const validateConfirm = (_rule: any, value: string, callback: any) => {
  if (value !== form.password) callback(new Error('两次密码输入不一致'))
  else callback()
}

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效邮箱', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

const handleRegister = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await userStore.register(form.username, form.email, form.password)
    router.push('/home')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-panel">
      <div class="auth-header">
        <div class="logo">
          <div class="logo-icon"><el-icon :size="22"><Connection /></el-icon></div>
          <span class="logo-text">智联职引</span>
        </div>
        <h2>创建账号</h2>
        <p class="subtitle">注册后即可使用智能简历分析与岗位匹配</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="auth-form">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="输入用户名" prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="输入邮箱" prefix-icon="Message" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="至少6位密码" prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="再次输入密码" prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleRegister">
            注 册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        <span>已有账号？</span>
        <router-link to="/login" class="link">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-panel {
  width: 420px;
  padding: 40px 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.auth-header {
  text-align: center;
  margin-bottom: 28px;
}

.logo { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 16px; }
.logo-icon { width: 36px; height: 36px; background: var(--brand); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; }
.logo-text { font-size: 20px; font-weight: 700; color: var(--ink); }
.auth-header h2 { font-size: 22px; font-weight: 700; color: var(--ink); margin-bottom: 8px; }
.subtitle { font-size: 13px; color: var(--muted); }

.auth-form { margin-bottom: 16px; }

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  border-radius: var(--radius);
  background: var(--brand);
  border-color: var(--brand);
}
.submit-btn:hover { background: var(--brand-dark); border-color: var(--brand-dark); }

.auth-footer { text-align: center; font-size: 13px; color: var(--muted); }
.link { color: var(--brand); text-decoration: none; margin-left: 4px; font-weight: 500; }
.link:hover { color: var(--brand-dark); }
</style>
