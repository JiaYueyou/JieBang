<script setup lang="ts">
import { ref } from 'vue'

const visible = ref(false)
const inputText = ref('')

const presetCommands = [
  { label: '帮我看看这个岗位适合我吗', icon: 'Search' },
  { label: '生成学习路径', icon: 'Guide' },
  { label: '优化我的简历', icon: 'Edit' },
]

const toggle = () => {
  visible.value = !visible.value
}

const sendPreset = (cmd: string) => {
  inputText.value = cmd
}

const handleSend = () => {
  if (inputText.value.trim()) {
    inputText.value = ''
  }
}
</script>

<template>
  <div class="ai-float-wrapper">
    <transition name="slide-up">
      <div v-if="visible" class="ai-panel">
        <div class="ai-panel-header">
          <div class="ai-panel-title">
            <span class="ai-dot"></span>
            AI 助手
          </div>
          <el-button :icon="'Close'" text circle size="small" @click="visible = false" />
        </div>
        <div class="ai-panel-body">
          <div class="chat-placeholder">
            <p>你好！我可以帮你：</p>
          </div>
          <div class="preset-list">
            <div
              v-for="cmd in presetCommands"
              :key="cmd.label"
              class="preset-item"
              @click="sendPreset(cmd.label)"
            >
              <el-icon :size="16"><component :is="cmd.icon" /></el-icon>
              <span>{{ cmd.label }}</span>
            </div>
          </div>
        </div>
        <div class="ai-panel-footer">
          <el-input
            v-model="inputText"
            placeholder="输入你的问题…"
            class="chat-input"
            @keyup.enter="handleSend"
          >
            <template #suffix>
              <el-button :icon="'Promotion'" text size="small" @click="handleSend" />
            </template>
          </el-input>
        </div>
      </div>
    </transition>

    <button class="ai-fab" :class="{ active: visible }" @click="toggle">
      <el-icon :size="28">
        <component :is="visible ? 'Close' : 'ChatDotRound'" />
      </el-icon>
    </button>
  </div>
</template>

<style scoped>
.ai-float-wrapper {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 999;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.ai-fab {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--brand);
  color: #fff;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(0, 199, 129, 0.35);
  cursor: pointer;
  transition: all 0.25s ease;
}

.ai-fab:hover {
  background: var(--brand-dark);
  transform: scale(1.08);
  box-shadow: 0 6px 20px rgba(0, 199, 129, 0.45);
}

.ai-fab.active {
  background: #fff;
  color: var(--ink);
  box-shadow: var(--shadow-hover);
}

.ai-panel {
  width: 380px;
  height: 500px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ai-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--hairline);
}

.ai-panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
}

.ai-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--brand);
}

.ai-panel-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.chat-placeholder {
  margin-bottom: 16px;
}

.chat-placeholder p {
  font-size: 13px;
  color: var(--muted);
}

.preset-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preset-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--canvas);
  border-radius: var(--radius);
  font-size: 13px;
  color: var(--ink);
  cursor: pointer;
  transition: all 0.15s ease;
}

.preset-item:hover {
  background: var(--brand-light);
  color: var(--brand);
}

.ai-panel-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--hairline);
}

.chat-input :deep(.el-input__wrapper) {
  border-radius: 20px;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}
</style>
