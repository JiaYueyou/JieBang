<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const breadcrumbs = computed(() => {
  const matched = route.matched.filter((r) => r.meta.title)
  return matched.map((r) => ({
    title: r.meta.title as string,
    path: r.path,
  }))
})

const searchQuery = ref('')
const isSearchFocused = ref(false)

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    router.push({ path: '/positions', query: { keyword: searchQuery.value } })
  }
}

const displayName = computed(() => userStore.user?.nickname || userStore.user?.username || '求职者')
const currentCity = computed(() => userStore.user?.city || '')
const currentEducation = computed(() => userStore.user?.education || '')

const cityOptions = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京', '西安', '苏州']
const educationOptions = ['大专', '本科', '硕士', '博士', '不限']

const cityVisible = ref(false)
const educationVisible = ref(false)

const handleCityChange = async (val: string) => {
  try {
    await userStore.updateProfile({ city: val })
    cityVisible.value = false
  } catch { /* ignore */ }
}

const handleEducationChange = async (val: string) => {
  try {
    await userStore.updateProfile({ education: val })
    educationVisible.value = false
  } catch { /* ignore */ }
}
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
          <span class="breadcrumb-text">{{ item.title }}</span>
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="header-center">
      <el-input
        v-model="searchQuery"
        placeholder="搜索岗位、技能、简历…"
        :prefix-icon="'Search'"
        class="search-input"
        :class="{ focused: isSearchFocused }"
        @focus="isSearchFocused = true"
        @blur="isSearchFocused = false"
        @keyup.enter="handleSearch"
        clearable
      />
    </div>

    <div class="header-right">
      <!-- City tag -->
      <el-popover
        v-model:visible="cityVisible"
        placement="bottom"
        :width="180"
        trigger="click"
      >
        <template #reference>
          <span class="setting-tag">
            <el-icon :size="12"><Location /></el-icon>
            <span>{{ currentCity || '城市' }}</span>
            <el-icon :size="10"><ArrowDown /></el-icon>
          </span>
        </template>
        <div class="popover-content">
          <span class="popover-label">选择城市</span>
          <el-select
            :model-value="currentCity"
            placeholder="选择城市"
            size="small"
            style="width: 100%"
            @change="handleCityChange"
          >
            <el-option v-for="c in cityOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </div>
      </el-popover>

      <!-- Education tag -->
      <el-popover
        v-model:visible="educationVisible"
        placement="bottom"
        :width="180"
        trigger="click"
      >
        <template #reference>
          <span class="setting-tag">
            <el-icon :size="12"><School /></el-icon>
            <span>{{ currentEducation || '学历' }}</span>
            <el-icon :size="10"><ArrowDown /></el-icon>
          </span>
        </template>
        <div class="popover-content">
          <span class="popover-label">选择学历</span>
          <el-select
            :model-value="currentEducation"
            placeholder="选择学历"
            size="small"
            style="width: 100%"
            @change="handleEducationChange"
          >
            <el-option v-for="e in educationOptions" :key="e" :label="e" :value="e" />
          </el-select>
        </div>
      </el-popover>

      <el-badge :value="3" :max="99" class="notice-badge">
        <el-button :icon="'Bell'" circle text />
      </el-badge>

      <el-dropdown trigger="click">
        <span class="avatar-btn">
          <el-avatar :size="32" icon="UserFilled" />
          <span class="avatar-name">{{ displayName }}</span>
          <el-icon :size="14"><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="router.push('/profile')">
              <el-icon><User /></el-icon>个人中心
            </el-dropdown-item>
            <el-dropdown-item @click="router.push('/resumes')">
              <el-icon><Document /></el-icon>我的简历
            </el-dropdown-item>
            <el-dropdown-item divided @click="router.push('/login')">
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid var(--hairline);
  flex-shrink: 0;
}

.header-left {
  flex: 0 0 auto;
}

.breadcrumb-text {
  font-size: 13px;
  color: var(--muted);
}

.header-center {
  flex: 1;
  max-width: 420px;
  margin: 0 24px;
}

.search-input {
  --el-input-bg-color: var(--canvas);
  --el-input-border-color: transparent;
  --el-input-hover-border-color: var(--brand);
  --el-input-focus-border-color: var(--brand);
  border-radius: 20px;
  transition: all 0.2s ease;
}

.search-input.focused {
  --el-input-bg-color: #fff;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 20px;
  box-shadow: none;
  border: 1px solid var(--hairline);
  transition: all 0.2s ease;
}

.search-input.focused :deep(.el-input__wrapper) {
  border-color: var(--brand);
  box-shadow: 0 0 0 2px var(--brand-light);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.setting-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 14px;
  background: var(--canvas);
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.setting-tag:hover {
  background: var(--brand-light);
  color: var(--brand);
}

.popover-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.popover-label {
  font-size: 12px;
  color: var(--weak);
}

.notice-badge :deep(.el-badge__content) {
  background: var(--danger);
}

.avatar-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius);
  transition: background 0.15s ease;
}

.avatar-btn:hover {
  background: var(--canvas);
}

.avatar-name {
  font-size: 13px;
  color: var(--ink);
  white-space: nowrap;
}
</style>
