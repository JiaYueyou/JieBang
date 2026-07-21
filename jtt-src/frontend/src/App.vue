<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import FloatingAIButton from '@/components/common/FloatingAIButton.vue'

const route = useRoute()

const isFullPage = computed(() => ['Login', 'Register'].includes(route.name as string))
</script>

<template>
  <div v-if="isFullPage" class="full-page">
    <router-view />
  </div>
  <div v-else class="app-layout">
    <AppSidebar />
    <div class="main-area">
      <AppHeader />
      <main class="content">
        <router-view />
      </main>
    </div>
    <FloatingAIButton />
  </div>
</template>

<style>
:root {
  --brand: #4f6ef6;
  --brand-dark: #3d5bd9;
  --brand-light: #eef1fe;
  --ink: #1a1d28;
  --muted: #989eae;
  --weak: #c4c8d0;
  --canvas: #f8f9fb;
  --card: #FFFFFF;
  --hairline: #e8ebf0;
  --success: #34b37e;
  --warning: #f59e4b;
  --danger: #e85d5d;
  --shadow: 0 1px 3px rgba(0,0,0,.05), 0 1px 2px rgba(0,0,0,.04);
  --shadow-hover: 0 4px 12px rgba(0,0,0,.06), 0 1px 3px rgba(0,0,0,.04);
  --radius: 10px;
  --radius-sm: 6px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  min-width: 1280px;
  color: var(--ink);
  background: var(--canvas);
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

button, input, textarea, select {
  font: inherit;
}

button {
  cursor: pointer;
}

.app-layout {
  display: flex;
  min-height: 100vh;
}

.main-area {
  flex: 1;
  margin-left: 220px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.content {
  flex: 1;
  padding: 20px 24px;
  background: var(--canvas);
}

.full-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef1fe 0%, #f8f9fb 50%, #FFFFFF 100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
