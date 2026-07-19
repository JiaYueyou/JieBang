<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useMatchStore } from '@/stores/match'

const router = useRouter()
const userStore = useUserStore()
const matchStore = useMatchStore()

const profileFormRef = ref()
const passwordFormRef = ref()

const profileForm = reactive({
  nickname: '',
  email: '',
  phone: '',
  city: '',
  education: '',
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const saving = ref(false)
const changingPassword = ref(false)

const cityOptions = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京', '西安', '苏州']
const educationOptions = ['大专', '本科', '硕士', '博士', '不限']

const validateConfirmPassword = (_rule: any, value: string, callback: any) => {
  if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

onMounted(async () => {
  if (userStore.isLoggedIn) {
    await userStore.fetchProfile()
  }
  await matchStore.fetchHistory()
  if (userStore.user) {
    profileForm.nickname = userStore.user.nickname || ''
    profileForm.email = userStore.user.email || ''
    profileForm.phone = userStore.user.phone || ''
    profileForm.city = userStore.user.city || ''
    profileForm.education = userStore.user.education || ''
  }
})

const handleSaveProfile = async () => {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await userStore.updateProfile({ ...profileForm })
    ElMessage.success('个人信息已更新')
  } catch {
    ElMessage.error('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

const handleChangePassword = async () => {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  changingPassword.value = true
  try {
    await userStore.changePassword({
      oldPassword: passwordForm.oldPassword,
      newPassword: passwordForm.newPassword,
    })
    ElMessage.success('密码修改成功')
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    passwordFormRef.value?.resetFields()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '密码修改失败')
  } finally {
    changingPassword.value = false
  }
}

const getScoreColor = (score: number) => {
  if (score >= 80) return 'var(--success)'
  if (score >= 50) return 'var(--warning)'
  return 'var(--danger)'
}
</script>

<template>
  <div class="profile-page">
    <!-- 个人信息编辑 -->
    <el-card class="section-card">
      <template #header><span class="card-title">个人信息</span></template>
      <el-form
        ref="profileFormRef"
        :model="profileForm"
        label-width="80px"
        label-position="left"
        class="profile-form"
      >
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="昵称">
              <el-input v-model="profileForm.nickname" placeholder="输入显示昵称" maxlength="20" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="账号">
              <el-input :model-value="userStore.user?.username" disabled />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="邮箱" :rules="[{ type: 'email', message: '请输入有效邮箱', trigger: 'blur' }]">
              <el-input v-model="profileForm.email" placeholder="输入邮箱" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="手机号">
              <el-input v-model="profileForm.phone" placeholder="输入手机号" maxlength="11" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="所在城市">
              <el-select v-model="profileForm.city" placeholder="选择城市" clearable style="width: 100%">
                <el-option v-for="c in cityOptions" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学历">
              <el-select v-model="profileForm.education" placeholder="选择学历" clearable style="width: 100%">
                <el-option v-for="e in educationOptions" :key="e" :label="e" :value="e" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSaveProfile">保存修改</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 修改密码 -->
    <el-card class="section-card">
      <template #header><span class="card-title">修改密码</span></template>
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        label-width="80px"
        label-position="left"
        class="profile-form"
      >
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="原密码" prop="oldPassword" :rules="[{ required: true, message: '请输入原密码', trigger: 'blur' }]">
              <el-input v-model="passwordForm.oldPassword" type="password" placeholder="输入原密码" show-password />
            </el-form-item>
          </el-col>
          <el-col :span="12" />
        </el-row>
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="新密码" prop="newPassword" :rules="[{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, message: '密码至少6位', trigger: 'blur' }]">
              <el-input v-model="passwordForm.newPassword" type="password" placeholder="输入新密码" show-password />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="确认密码" prop="confirmPassword" :rules="[{ required: true, message: '请确认新密码', trigger: 'blur' }, { validator: validateConfirmPassword, trigger: 'blur' }]">
              <el-input v-model="passwordForm.confirmPassword" type="password" placeholder="再次输入新密码" show-password />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" :loading="changingPassword" @click="handleChangePassword">修改密码</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 快捷入口 -->
    <div class="quick-links">
      <el-card class="link-card" @click="router.push('/diagnosis')">
        <el-icon :size="24"><Document /></el-icon>
        <span>简历诊断</span>
      </el-card>
      <el-card class="link-card" @click="router.push('/favorites')">
        <el-icon :size="24"><Star /></el-icon>
        <span>我的收藏</span>
      </el-card>
      <el-card class="link-card" @click="router.push('/learning')">
        <el-icon :size="24"><Guide /></el-icon>
        <span>学习路径</span>
      </el-card>
      <el-card class="link-card" @click="router.push('/career')">
        <el-icon :size="24"><TrendCharts /></el-icon>
        <span>职业发展</span>
      </el-card>
    </div>

    <!-- 匹配历史 -->
    <el-card class="history-card">
      <template #header><span class="card-title">匹配历史</span></template>
      <div v-if="matchStore.history.length === 0" class="no-history">
        <el-empty description="暂无匹配记录" />
      </div>
      <div v-else class="history-list">
        <div
          v-for="m in matchStore.history"
          :key="m.id"
          class="history-item"
          @click="router.push(`/diagnosis/${m.resumeId}`)"
        >
          <div class="h-left">
            <h5>{{ m.resumeName }} → {{ m.positionName }}</h5>
            <span class="h-date">{{ m.matchDate }}</span>
          </div>
          <div class="h-score" :style="{ color: getScoreColor(m.totalScore) }">
            {{ m.totalScore }}
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.profile-page { max-width: 800px; margin: 0 auto; }

.section-card { margin-bottom: 20px; }
.card-title { font-size: 15px; font-weight: 600; }

.profile-form {
  padding: 8px 0;
}

.profile-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.quick-links {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.link-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.link-card:hover {
  box-shadow: var(--shadow-hover);
  color: var(--brand);
}

.link-card span { font-size: 14px; font-weight: 500; }

.history-card { margin-bottom: 20px; }

.no-history { padding: 20px 0; }

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
  border-bottom: 1px solid var(--hairline);
  cursor: pointer;
  transition: background 0.15s;
}

.history-item:hover { background: var(--canvas); margin: 0 -20px; padding: 14px 20px; }
.history-item:last-child { border-bottom: none; }

.h-left h5 { font-size: 14px; font-weight: 600; margin: 0 0 4px; }
.h-date { font-size: 12px; color: var(--muted); }

.h-score { font-size: 24px; font-weight: 800; }
</style>
