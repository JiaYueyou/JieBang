<script setup lang="ts">
import { useRouter } from 'vue-router'
import { mockHistoryMatches } from '@/mock/data/match'
import { mockPositions } from '@/mock/data/positions'

const router = useRouter()

const goResult = (resumeId: string, positionId: string) => {
  router.push(`/match/result/${resumeId}/${positionId}`)
}

const getScoreColor = (score: number) => {
  if (score >= 80) return 'var(--success)'
  if (score >= 50) return 'var(--warning)'
  return 'var(--danger)'
}

const getCategoryTag = (positionId: string) => {
  const pos = mockPositions.find((p) => p.id === positionId)
  if (!pos) return ''
  return pos.category === 'new' ? '新兴岗位' : '既有岗位'
}

const getCategoryTagType = (positionId: string): 'success' | '' => {
  const pos = mockPositions.find((p) => p.id === positionId)
  return pos?.category === 'new' ? 'success' : ''
}
</script>

<template>
  <div class="match-page">
    <div class="page-header">
      <h2>匹配诊断</h2>
      <p class="header-sub">共 {{ mockHistoryMatches.length }} 条匹配记录</p>
    </div>

    <div v-if="mockHistoryMatches.length > 0" class="match-list">
      <div
        v-for="m in mockHistoryMatches"
        :key="m.id"
        class="match-item"
        @click="goResult(m.resumeId, m.positionId)"
      >
        <div class="match-left">
          <div class="match-path">
            <span class="resume-name">{{ m.resumeName }}</span>
            <el-icon :size="16" class="arrow-icon"><ArrowRight /></el-icon>
            <span class="pos-name">{{ m.positionName }}</span>
          </div>
          <div class="match-meta">
            <el-tag size="small" :type="getCategoryTagType(m.positionId)" effect="plain">
              {{ getCategoryTag(m.positionId) }}
            </el-tag>
            <span class="match-date">{{ m.matchDate }}</span>
          </div>
        </div>
        <div class="match-score" :style="{ color: getScoreColor(m.totalScore) }">
          {{ m.totalScore }}<span class="score-unit">分</span>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <el-empty description="暂无匹配记录">
        <el-button type="primary" @click="router.push('/positions')">去探索岗位</el-button>
      </el-empty>
    </div>
  </div>
</template>

<style scoped>
.match-page { max-width: 800px; margin: 0 auto; }

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
}

.header-sub {
  font-size: 13px;
  color: var(--muted);
}

.match-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.match-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  padding: 20px 24px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  cursor: pointer;
  transition: all 0.15s ease;
}

.match-item:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-1px);
}

.match-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.match-path {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.arrow-icon {
  color: var(--brand);
  flex-shrink: 0;
}

.resume-name {
  color: var(--ink);
}

.pos-name {
  color: var(--brand);
}

.match-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.match-date {
  font-size: 12px;
  color: var(--muted);
}

.match-score {
  font-size: 32px;
  font-weight: 800;
  flex-shrink: 0;
}

.score-unit {
  font-size: 14px;
  font-weight: 400;
}

.empty-state {
  padding: 80px 0;
}
</style>
