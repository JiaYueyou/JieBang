<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { MatchResult } from '@/types'
import { mockResumes } from '@/mock/data/resume'
import { matchApi } from '@/api/match'

const props = withDefaults(
  defineProps<{
    mode: 'list' | 'detail'
    positionId?: string
    allPositionIds?: string[]
  }>(),
  { positionId: '', allPositionIds: () => [] },
)

const router = useRouter()
const visible = ref(false)
const dialogVisible = ref(false)
const batchLoading = ref(false)
const batchResults = ref<MatchResult[]>([])

const popoverTitle = props.mode === 'detail' ? '选择简历开始匹配诊断' : '选择简历发起匹配'

const handleSelectResume = async (resumeId: string) => {
  visible.value = false

  if (props.mode === 'detail' && props.positionId) {
    router.push(`/diagnosis`)
    return
  }

  // List mode: batch match
  if (props.allPositionIds && props.allPositionIds.length > 0) {
    batchLoading.value = true
    try {
      const res: any = await matchApi.matchBatch({
        resumeId,
        positionIds: props.allPositionIds,
      })
      batchResults.value = res.data.sort((a: MatchResult, b: MatchResult) => b.totalScore - a.totalScore)
      dialogVisible.value = true
    } catch {
      ElMessage.error('匹配失败，请重试')
    } finally {
      batchLoading.value = false
    }
  }
}

const goDetail = (positionId: string) => {
  dialogVisible.value = false
  router.push(`/positions/${positionId}`)
}

const getScoreColor = (score: number) => {
  if (score >= 80) return 'var(--success)'
  if (score >= 50) return 'var(--warning)'
  return 'var(--danger)'
}
</script>

<template>
  <div class="fab-wrapper">
    <!-- Popover above the button -->
    <transition name="pop">
      <div v-if="visible" class="fab-popover">
        <div class="popover-title">{{ popoverTitle }}</div>
        <div class="resume-options">
          <div
            v-for="r in mockResumes"
            :key="r.id"
            class="resume-option"
            :class="{ loading: batchLoading }"
            @click="!batchLoading && handleSelectResume(r.id)"
          >
            <div class="option-left">
              <el-icon :size="18"><Document /></el-icon>
              <span>{{ r.name }}</span>
            </div>
            <el-icon v-if="!batchLoading" :size="16"><ArrowRight /></el-icon>
            <el-icon v-else class="loading-spin" :size="16"><Loading /></el-icon>
          </div>
        </div>
        <div class="popover-footer">
          <el-button text size="small" @click="router.push('/resume/upload')">上传新简历</el-button>
        </div>
      </div>
    </transition>

    <!-- FAB button -->
    <button class="fab-btn" @click="visible = !visible">
      <el-icon :size="24"><Plus /></el-icon>
    </button>
  </div>

  <!-- Batch match results dialog -->
  <el-dialog
    v-model="dialogVisible"
    title="匹配结果"
    width="560px"
    top="8vh"
    :close-on-click-modal="true"
  >
    <div class="batch-results">
      <div
        v-for="r in batchResults"
        :key="`${r.resumeId}_${r.positionId}`"
        class="batch-item"
        @click="goDetail(r.positionId)"
      >
        <div class="batch-left">
          <span class="batch-pos-name">{{ r.positionName }}</span>
          <el-tag size="small" effect="plain" type="info">
            {{ mockResumes.find((rr) => rr.id === r.resumeId)?.name || '未知简历' }}
          </el-tag>
        </div>
        <div class="batch-score" :style="{ color: getScoreColor(r.totalScore) }">
          {{ r.totalScore }}<span class="score-unit">分</span>
        </div>
      </div>
    </div>
    <div v-if="batchResults.length === 0" class="batch-empty">
      <el-empty description="暂无匹配结果" />
    </div>
  </el-dialog>
</template>

<style scoped>
.fab-wrapper {
  position: fixed;
  right: 24px;
  bottom: 100px;
  z-index: 998;
}

.fab-btn {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #fff;
  color: var(--brand);
  border: 2px solid var(--brand);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
}

.fab-btn:hover {
  background: var(--brand);
  color: #fff;
}

.fab-popover {
  position: absolute;
  bottom: 60px;
  right: 0;
  width: 280px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  padding: 16px;
}

.popover-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 12px;
}

.resume-options {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.resume-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background 0.15s;
}

.resume-option:hover {
  background: var(--canvas);
}

.resume-option.loading {
  cursor: not-allowed;
  opacity: 0.6;
}

.option-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ink);
}

.popover-footer {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--hairline);
}

.loading-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Transition */
.pop-enter-active,
.pop-leave-active {
  transition: all 0.2s ease;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.95);
}

/* Dialog content */
.batch-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 480px;
  overflow-y: auto;
}

.batch-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-radius: var(--radius);
  border: 1px solid var(--hairline);
  cursor: pointer;
  transition: all 0.15s;
}

.batch-item:hover {
  background: var(--canvas);
  border-color: var(--brand);
}

.batch-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.batch-pos-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.batch-score {
  font-size: 24px;
  font-weight: 800;
  flex-shrink: 0;
}

.score-unit {
  font-size: 12px;
  font-weight: 400;
}

.batch-empty {
  padding: 20px 0;
}
</style>
